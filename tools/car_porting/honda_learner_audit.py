#!/usr/bin/env python3
"""Pull the evidence the Honda steering learner's design decisions were made on.

This does not fit anything. It replays a route with exactly the gating
``learn_honda_steering.py`` uses and reports the measurements that decide two open
questions the simulation tests cannot answer, because a simulated plant is built with the
model's own structure:

  1. **Which target should be fitted?** ``hondasteerd.py`` flips yaw into a positive-left
     frame (``YAW_SIGN = -1``), so a roll term subtracted in the unflipped frame enters
     with the wrong sign. Commit 41d060f measured corr(roll comp, target) = -0.44 and
     variance up 1.43x when subtracting, and turned the compensation off on that basis -
     which is also exactly what a frame error looks like. This scores all three candidate
     targets (raw, roll subtracted, roll added) against the same command so the question is
     settled by which one the command actually explains.

  2. **Is the delay bank measuring dead time, or duplicating lagd?** The bank races static
     models over all samples, so its winner absorbs delay + tau together, which is why
     ``responseTau`` reads 0. ``lagd.py`` already publishes ``lateralDelay`` on every car.
     This prints them side by side.

  3. **What are the ``resets``?** ``--replay`` runs the route through a real learner and
     logs every divergence reset with which fit and which term tripped it. The published
     counter sums three unrelated events - a full gain reset, a railed secondary term, and
     a railed steer ratio - and only the first is a failure signal. The same pass prints
     each speed bucket's occupancy against ``MIN_POINTS_PER_BUCKET``, which says whether a
     bucket's published gain is its own fit or the steady fit it falls back to.

Also reports the learner's own published output over the drive (resets, divergence, delay)
next to ``vehicleParameters.steerRatio``, the independent reference in the same log.

Usage::

  ./honda_learner_audit.py 729a2e65b1f6201d/00000012--48f682b2ff
  ./honda_learner_audit.py --replay 729a2e65b1f6201d/00000012--48f682b2ff
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from openpilot.common.constants import CV

from opendbc.car.honda.steering_learner import (
  LAT_ACCEL_BUCKET_EDGES,
  MAX_DELAY,
  MAX_LAT_ACCEL,
  MIN_LEARN_SPEED,
  MIN_POINTS_PER_BUCKET,
  SPEED_BUCKET_EDGES,
  normalized_command,
  speed_bucket_centres,
)

# hondasteerd feeds the learner every other carState, so the rate the model is actually fit
# at on the car is 50 Hz, not the 100 Hz carState is logged at - see learn_honda_steering.py.
DECIMATION = 2
DT = 0.01 * DECIMATION
# The calibrated frame is z-down, so a positive yaw rate is a right hand turn, while steering
# angle and the torque command are both positive-left - see hondasteerd.py.
YAW_SIGN = -1.0
MAX_YAW_AGE = 0.1
G = 9.81
# selfdrive/locationd/lagd.py MIN_VEGO, spelled the same way it is there - lagd ignores
# everything slower, which is the first thing to check when its validBlocks never leaves 1
LAGD_MIN_VEGO = 50.0 * CV.MPH_TO_MS


def collect(route: str) -> dict:
  """Every gated sample of the route, plus whatever the daemon published alongside it."""
  from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator
  from openpilot.tools.lib.logreader import LogReader

  calibrator = PoseCalibrator()
  CP = None
  CC = None
  torque = 0.0
  torque_can = 0.0
  yaw_rate = None
  yaw_rate_t = 0.0
  roll = 0.0
  frame = 0

  u, a_raw, rolls, vs = [], [], [], []
  lagd_eligible = [0]
  lagd = {"delay": None, "valid_blocks": 0}
  ref_steer_ratio = None
  published = []

  for msg in LogReader(route, sort_by_time=True):
    which = msg.which()
    t = msg.logMonoTime * 1e-9

    if which == "carParams" and CP is None:
      CP = msg.carParams
    elif which == "extrinsicsCalibration":
      calibrator.feed_extrinsics_calibration(msg.extrinsicsCalibration)
    elif which == "vehicleParameters":
      roll = msg.vehicleParameters.roll
      if msg.vehicleParameters.steerRatioValid:
        ref_steer_ratio = msg.vehicleParameters.steerRatio
    elif which == "lateralDelay":
      lagd = {"delay": msg.lateralDelay.lateralDelay, "valid_blocks": msg.lateralDelay.validBlocks}
    elif which == "hondaSteeringParameters":
      p = msg.hondaSteeringParameters
      published.append({
        "t": t, "actuator_delay": p.actuatorDelay, "effective_lag": p.effectiveLag,
        "response_tau": p.responseTau, "delay_learned": p.delayLearned,
        "delay_railed": p.delayRailed,
        "resets": p.resets, "diverged": p.diverged, "steer_ratio": p.steerRatio,
        "points": p.points, "valid": p.valid,
      })
    elif which == "deviceMotion":
      dm = msg.deviceMotion
      if dm.angularVelocityDevice.valid and dm.orientationNED.valid and dm.inputsOK and dm.sensorsOK:
        yaw_rate = YAW_SIGN * calibrator.build_calibrated_pose(Pose.from_device_motion(dm)).angular_velocity.yaw
        yaw_rate_t = t
      else:
        yaw_rate = None
    elif which == "carOutput":
      torque_raw = msg.carOutput.actuatorsOutput.torque
      torque_can = msg.carOutput.actuatorsOutput.torqueOutputCan
      torque = normalized_command(torque_raw, torque_can, CP) if CP is not None else torque_raw
    elif which == "carControl":
      CC = msg.carControl
    elif which == "carState" and CC is not None:
      frame += 1
      if frame % DECIMATION:
        continue
      CS = msg.carState
      # the learner's own gate: engaged, hands off, unsaturated, fast enough, fresh yaw
      if not CC.latActive or CS.steeringPressed:
        continue
      if yaw_rate is None or (t - yaw_rate_t) > MAX_YAW_AGE:
        continue
      if CS.vEgo < MIN_LEARN_SPEED or abs(torque) >= 0.99:
        continue
      u.append(torque)
      a_raw.append(yaw_rate * CS.vEgo)
      rolls.append(roll)
      vs.append(CS.vEgo)
      # lagd only accumulates blocks above MIN_VEGO (22.35 m/s), so the reason it reports
      # a default 0.300 s here may simply be that this drive has no highway in it
      if CS.vEgo >= LAGD_MIN_VEGO:
        lagd_eligible[0] += 1

  return {
    "route": route, "CP": CP, "u": np.array(u), "a_raw": np.array(a_raw),
    "roll": np.array(rolls), "v": np.array(vs), "lagd": lagd,
    "ref_steer_ratio": ref_steer_ratio, "published": published,
    "lagd_eligible_s": lagd_eligible[0] * DT,
    "torque_can_seen": torque_can,
  }


def _corr(x, y) -> float:
  if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
    return float("nan")
  return float(np.corrcoef(x, y)[0, 1])


def report(d: dict) -> None:
  u, a_raw, roll, v = d["u"], d["a_raw"], d["roll"], d["v"]
  print(f"\n{'=' * 100}\n{d['route']}   {d['CP'].carFingerprint if d['CP'] else '?'}   "
        f"{len(u)} gated samples\n{'=' * 100}")
  if len(u) < 100:
    print("  too few gated samples to say anything")
    return

  comp = G * np.sin(roll)
  targets = {"raw": a_raw, "a - g*sin(roll)": a_raw - comp, "a + g*sin(roll)": a_raw + comp}

  edges = list(SPEED_BUCKET_EDGES)
  labels = [f"{edges[i]:.0f}-{edges[i+1]:.0f}" if edges[i + 1] < 100 else f"{edges[i]:.0f}+"
            for i in range(len(edges) - 1)]

  print(f"\n  roll: std {np.std(comp):.3f} m/s^2 vs target std {np.std(a_raw):.3f} "
        f"({np.std(comp) / max(np.std(a_raw), 1e-9):.2f}x)")
  print(f"\n  {'target':<18} {'corr(u,tgt)':>12} {'sigma(tgt)':>11} {'corr(comp,a_raw)':>17}   "
        + "  ".join(f"K[{l}]".rjust(11) for l in labels))
  for name, tgt in targets.items():
    gains = []
    for i in range(len(edges) - 1):
      m = (v >= edges[i]) & (v < edges[i + 1]) & (np.abs(tgt) <= MAX_LAT_ACCEL)
      gains.append(f"{np.polyfit(u[m], tgt[m], 1)[0]:11.3f}" if m.sum() >= 50 else f"{'-':>11}")
    print(f"  {name:<18} {_corr(u, tgt):12.3f} {np.std(tgt):11.3f} {_corr(comp, a_raw):17.3f}   "
          + "  ".join(gains))

  best = max(targets, key=lambda k: _corr(u, targets[k]))
  print(f"\n  --> highest corr(u, target): {best}   (corr(comp, a_raw) = {_corr(comp, a_raw):+.3f})")

  # -- delay: the bank vs lagd ------------------------------------------------------------
  lagd = d["lagd"]
  prior_delay = float(d["CP"].steerActuatorDelay) if d["CP"] else float("nan")
  print(f"\n  delay   lagd {lagd['delay'] if lagd['delay'] is not None else float('nan'):.3f} s "
        f"(validBlocks {lagd['valid_blocks']})   CP.steerActuatorDelay {prior_delay:.3f} s")
  print(f"          lat_active time above lagd's MIN_VEGO ({LAGD_MIN_VEGO:.1f} m/s): "
        f"{d['lagd_eligible_s']:.0f} s of {len(u) * DT:.0f} s gated")
  pub = d["published"]
  if pub:
    last = pub[-1]
    print(f"          bank actuatorDelay {last['actuator_delay']:.3f} s   "
          f"responseTau {last['response_tau']:.3f} s   effectiveLag {last['effective_lag']:.3f} s   "
          f"delayLearned {last['delay_learned']}   delayRailed {last['delay_railed']} "
          f"(grid tops out at MAX_DELAY {MAX_DELAY:.3f} s)")
    railed_n = sum(1 for p in pub if p["delay_railed"])
    print(f"          delayRailed on {railed_n}/{len(pub)} publishes")
    if lagd["delay"] is not None:
      print(f"          |bank - lagd| = {abs(last['actuator_delay'] - lagd['delay']):.3f} s   "
            f"|effectiveLag - lagd| = {abs(last['effective_lag'] - lagd['delay']):.3f} s")
    learned = sum(1 for p in pub if p["delay_learned"])
    print(f"          delayLearned on {learned}/{len(pub)} publishes")

    # -- the learner's own health over the drive -----------------------------------------
    print(f"\n  published   resets {last['resets']}   diverged {last['diverged']}   "
          f"valid {last['valid']}   points {last['points']}")
    print(f"              steerRatio {last['steer_ratio']:.2f}  vs  vehicleParameters "
          f"{d['ref_steer_ratio'] if d['ref_steer_ratio'] is not None else float('nan'):.2f}")
    diverged_n = sum(1 for p in pub if p["diverged"])
    print(f"              diverged on {diverged_n}/{len(pub)} publishes")
  else:
    print("          no hondaSteeringParameters in this log (daemon not running this branch)")


def _speed_labels() -> list[str]:
  edges = list(SPEED_BUCKET_EDGES)
  return [f"{edges[i]:.0f}-{edges[i+1]:.0f}" if edges[i + 1] < 100 else f"{edges[i]:.0f}+"
          for i in range(len(edges) - 1)]


def replay_report(route: str) -> dict:
  """Run the route through a real learner and report what reset, and where the points went.

  The published ``hondaSteeringParameters`` only carries counts, and a count cannot
  distinguish a gain reset from a railed offset. This is the pass that can.
  """
  # tools/car_porting is not a package and is not mirrored under openpilot/, so the
  # sibling module is imported by path, the same way test_honda_shadow_compare.py does it
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from learn_honda_steering import learn_route

  events: list = []
  learner = learn_route(route, on_reset=events.append)
  model = learner.model()

  print(f"\n{'-' * 100}\n  RESETS   {route}\n{'-' * 100}")
  by_kind: dict[str, int] = defaultdict(int)
  for e in events:
    by_kind[e.kind] += 1
  print(f"  gain {by_kind['gain']}   term {by_kind['term']}   steer_ratio {by_kind['steer_ratio']}"
        f"   (published resets {learner.resets})")

  if events:
    print(f"\n  {'t [s]':>8} {'v_ego':>7} {'kind':>11} {'fit':>11} {'term':>11} "
          f"{'value':>10} {'points':>8}")
    for e in events:
      print(f"  {e.t:8.1f} {e.v_ego:7.1f} {e.kind:>11} {e.fit:>11} {e.term:>11} "
            f"{e.value:10.3f} {e.points:8d}")

    # a term that always rails at the same bound is the bound acting as a prior, not a
    # fit wandering: report where each one landed relative to its range
    print(f"\n  {'term':>11} {'n':>5} {'min':>10} {'max':>10} {'mean':>10}")
    per_term: dict[str, list] = defaultdict(list)
    for e in events:
      per_term[e.term].append(e.value)
    for term, vals in sorted(per_term.items()):
      print(f"  {term:>11} {len(vals):5d} {min(vals):10.3f} {max(vals):10.3f} "
            f"{float(np.mean(vals)):10.3f}")

  # -- where the points actually went, per speed bucket -------------------------------
  counts = np.asarray(learner.bucket_counts)
  labels = _speed_labels()
  a_edges = list(LAT_ACCEL_BUCKET_EDGES)
  a_labels = [f"{a_edges[i]:+.1f}" for i in range(len(a_edges) - 1)]
  print(f"\n{'-' * 100}\n  BUCKET OCCUPANCY   (cell needs {MIN_POINTS_PER_BUCKET} points; a "
        f"bucket needs 2 filled cells + excitation)\n{'-' * 100}")
  print(f"  {'speed':>8} {'centre':>7} {'total':>8} {'cells>=min':>11} {'own fit?':>9}   "
        + "  ".join(a.rjust(7) for a in a_labels))
  centres = speed_bucket_centres()
  own_fit = []
  for i, label in enumerate(labels):
    row = counts[i]
    filled = int((row >= MIN_POINTS_PER_BUCKET).sum())
    gain = learner._bucket_gain(i)
    own_fit.append(gain is not None)
    print(f"  {label:>8} {centres[i]:7.1f} {int(row.sum()):8d} {filled:11d} "
          f"{('yes' if gain is not None else 'NO -> steady'):>9}   "
          + "  ".join(f"{int(c):7d}" for c in row))
  print("\n  published latAccelFactorV: "
        + "  ".join(f"{v:.3f}@{bp:.0f}" for bp, v in
                    zip(model.lat_accel_factor_bp, model.lat_accel_factor_v, strict=True)))
  print(f"  learned_buckets {model.learned_buckets}   points {model.points}   "
        f"valid {model.valid}")

  return {"route": route, "events": events, "counts": counts, "own_fit": own_fit,
          "model": model, "learner": learner}


def lagd_report(route: str) -> dict:
  """Replay openpilot's own ``LateralLagEstimator`` over a route and say which gate stops it.

  Routes 00000012 and 00000030 both spend over 200 s above lagd's ``MIN_VEGO`` yet publish
  ``validBlocks 1``, so speed alone does not explain why the delay estimate never converges.
  The published message carries only the outcome, and the deliverable here is the *reason*:
  every sample rejected by ``update_points`` is attributed to whichever of its gates was
  false, and every early return from ``update_estimate`` to the check that took it.

  This settles whether the learner's delay bank could ever be retired in favour of lagd.
  """
  sys.path.insert(0, str(Path(__file__).resolve().parent))
  from learn_honda_steering import iter_route

  from openpilot.cereal.services import SERVICE_LIST
  from openpilot.selfdrive.locationd.lagd import (
    MIN_LAT_ACCEL_RANGE,
    MAX_YAW_RATE_SANITY_CHECK,
    SMOOTH_K,
    SMOOTH_SIGMA,
    MIN_LAG,
    MAX_LAG,
    LateralLagEstimator,
    masked_symmetric_moving_average,
  )

  class _Attributed(LateralLagEstimator):
    """The estimator, unchanged, with every rejection recorded.

    ``update_points`` builds its gates as locals, so they are recomputed here from the
    estimator's own public attributes rather than intercepted. ``update_estimate`` is
    mirrored rather than wrapped: calling ``super()`` and then re-deriving why it returned
    would run the cross-correlation twice on every call.
    """

    def __init__(self, *a, **kw):
      super().__init__(*a, **kw)
      self.point_gates: dict[str, int] = defaultdict(int)
      self.estimate_gates: dict[str, int] = defaultdict(int)
      self.n_points = 0
      self.n_estimates = 0
      self.accepted_lags: list[float] = []

    def update_points(self):
      self.n_points += 1
      la_desired = self.desired_curvature * self.v_ego * self.v_ego
      la_actual = self.yaw_rate * self.v_ego
      gates = {
        "fast": self.v_ego > self.min_vego,
        "turning": abs(self.yaw_rate) >= self.min_yr,
        "sensors_valid": bool(self.pose_valid and abs(self.yaw_rate) < MAX_YAW_RATE_SANITY_CHECK
                              and self.yaw_rate_std < MAX_YAW_RATE_SANITY_CHECK),
        "la_valid": bool(abs(la_actual) <= self.max_lat_accel
                         and abs(la_desired - la_actual) <= self.max_lat_accel_diff),
        "calib_valid": bool(self.calibrator.calib_valid),
        "lat_active": bool(self.lat_active),
        "not_steering_pressed": not self.steering_pressed,
        "not_steering_saturated": not self.steering_saturated,
      }
      # has_recovered is a function of the four "last bad" timestamps *after* this sample
      # has updated them, so apply those updates here first. They are idempotent, so the
      # super() call below repeats them and arrives at the same answer.
      if not self.lat_active:
        self.last_lat_inactive_t = self.t
      if self.steering_pressed:
        self.last_steering_pressed_t = self.t
      if self.steering_saturated:
        self.last_steering_saturated_t = self.t
      if not gates["sensors_valid"] or not gates["la_valid"]:
        self.last_pose_invalid_t = self.t
      gates["has_recovered"] = all(
        self.t - last_t >= self.min_recovery_buffer_sec
        for last_t in (self.last_lat_inactive_t, self.last_steering_pressed_t,
                       self.last_steering_saturated_t, self.last_pose_invalid_t))
      super().update_points()
      for name, ok in gates.items():
        if not ok:
          self.point_gates[name] += 1
      if all(gates.values()):
        self.point_gates["okay"] += 1

    def update_estimate(self):
      self.n_estimates += 1
      if not self.points_enough():
        self.estimate_gates["points_enough"] += 1
        return

      times, desired, actual, okay = self.points.get()
      if not self.points_valid():
        self.estimate_gates["points_valid"] += 1
        return
      if actual.max() - actual.min() < MIN_LAT_ACCEL_RANGE:
        self.estimate_gates["lat_accel_range"] += 1
        return
      if self.last_estimate_t != 0 and times[0] <= self.last_estimate_t:
        start = next(-i for i, t in enumerate(reversed(times)) if t <= self.last_estimate_t)
        if start == 0 or not np.any(okay[start:]):
          self.estimate_gates["no_new_okay_points"] += 1
          return

      desired = masked_symmetric_moving_average(desired, okay, SMOOTH_K, SMOOTH_SIGMA)
      actual = masked_symmetric_moving_average(actual, okay, SMOOTH_K, SMOOTH_SIGMA)
      delay, corr, confidence = self.actuator_delay(desired, actual, okay, self.dt, MIN_LAG, MAX_LAG)
      if corr < self.min_ncc:
        self.estimate_gates["corr_below_min_ncc"] += 1
        return
      if confidence < self.min_confidence:
        self.estimate_gates["confidence_below_min"] += 1
        return

      self.block_avg.update(delay)
      self.last_estimate_t = self.t
      self.estimate_gates["accepted"] += 1
      self.accepted_lags.append(float(delay))

  dt = 1.0 / SERVICE_LIST["deviceMotion"].frequency
  est = None
  frame = 0
  t_above_min_vego = 0.0
  last_cs_t = None
  status = valid_blocks = None

  for msg in iter_route(route):
    which = msg.which()
    if which == "carParams" and est is None:
      est = _Attributed(msg.carParams, dt)
      continue
    if est is None:
      continue
    t = msg.logMonoTime * 1e-9
    if which == "carState":
      # qlogs have no controlsState, and without desiredCurvature the estimator can only
      # ever report "no lateral accel range" - refuse to produce a misleading table
      if last_cs_t is not None and msg.carState.vEgo > est.min_vego:
        t_above_min_vego += t - last_cs_t
      last_cs_t = t
    if which in LateralLagEstimator.inputs:
      est.handle_log(t, which, getattr(msg, which))
    if which == "deviceMotion":
      est.update_points()
      frame += 1
      if frame % 5 == 0:
        est.update_estimate()
        m = est.get_msg(True).lateralDelay
        status, valid_blocks = str(m.status), m.validBlocks

  if est is None:
    raise ValueError(f"{route}: no carParams in log")
  if not est.n_estimates:
    raise ValueError(f"{route}: no deviceMotion - is this a qlog? --lagd needs rlogs")

  print(f"\n{'-' * 100}\n  LAGD REPLAY   {route}\n{'-' * 100}")
  print(f"  initial lag {est.initial_lag:.3f}s   final status {status}   "
        f"validBlocks {valid_blocks}   accepted estimates {len(est.accepted_lags)}")
  if est.accepted_lags:
    print(f"  accepted lag: mean {np.mean(est.accepted_lags):.3f}s  "
          f"std {np.std(est.accepted_lags):.3f}s  "
          f"min {min(est.accepted_lags):.3f}s  max {max(est.accepted_lags):.3f}s")
  print(f"  time above lagd MIN_VEGO ({est.min_vego:.1f} m/s): {t_above_min_vego:.0f}s")

  print(f"\n  update_points: {est.n_points} samples, {est.point_gates['okay']} okay")
  print(f"  {'gate':>24} {'n false':>9} {'% of samples':>13}")
  for name, n in sorted(est.point_gates.items(), key=lambda kv: -kv[1]):
    if name == "okay":
      continue
    print(f"  {name:>24} {n:9d} {100.0 * n / est.n_points:12.1f}%")

  print(f"\n  update_estimate: {est.n_estimates} calls")
  print(f"  {'returned because':>24} {'n':>9} {'% of calls':>13}")
  for name, n in sorted(est.estimate_gates.items(), key=lambda kv: -kv[1]):
    print(f"  {name:>24} {n:9d} {100.0 * n / est.n_estimates:12.1f}%")

  return {"route": route, "valid_blocks": valid_blocks, "status": status,
          "accepted": est.accepted_lags, "point_gates": dict(est.point_gates),
          "estimate_gates": dict(est.estimate_gates), "t_above_min_vego": t_above_min_vego}


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("route", nargs="+")
  p.add_argument("--replay", action="store_true",
                 help="also run each route through a real learner and report resets and "
                      "bucket occupancy (slower: this refits the whole drive)")
  p.add_argument("--lagd", action="store_true",
                 help="also replay openpilot's LateralLagEstimator over each route and "
                      "report which gate rejects each sample and each estimate. Needs "
                      "rlogs: qlogs carry no controlsState")
  args = p.parse_args()

  summary = defaultdict(list)
  for route in args.route:
    try:
      d = collect(route)
      report(d)
      if len(d["u"]) >= 100:
        comp = G * np.sin(d["roll"])
        for name, tgt in (("raw", d["a_raw"]), ("a - g*sin(roll)", d["a_raw"] - comp),
                          ("a + g*sin(roll)", d["a_raw"] + comp)):
          summary[name].append(_corr(d["u"], tgt))
      if args.replay:
        d = None
        replay_report(route)
      if args.lagd:
        d = None
        lagd_report(route)
    except Exception as e:
      print(f"{route}: {type(e).__name__}: {e}", file=sys.stderr)

  if len(args.route) > 1 and summary:
    print(f"\n{'=' * 100}\nACROSS ROUTES: mean corr(u, target)\n{'=' * 100}")
    for name, vals in summary.items():
      wins = sum(1 for i in range(len(vals))
                 if vals[i] == max(summary[k][i] for k in summary))
      print(f"  {name:<18} mean {np.mean(vals):+.3f}   wins {wins}/{len(vals)} routes")
  return 0


if __name__ == "__main__":
  sys.exit(main())
