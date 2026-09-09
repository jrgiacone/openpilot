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

Also reports the learner's own published output over the drive (resets, divergence, delay)
next to ``vehicleParameters.steerRatio``, the independent reference in the same log.

Usage::

  ./honda_learner_audit.py 729a2e65b1f6201d/00000012--48f682b2ff
"""

import argparse
import sys
from collections import defaultdict

import numpy as np

from opendbc.car.honda.steering_learner import (
  MAX_LAT_ACCEL,
  MIN_LEARN_SPEED,
  SPEED_BUCKET_EDGES,
  normalized_command,
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

  return {
    "route": route, "CP": CP, "u": np.array(u), "a_raw": np.array(a_raw),
    "roll": np.array(rolls), "v": np.array(vs), "lagd": lagd,
    "ref_steer_ratio": ref_steer_ratio, "published": published,
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
  pub = d["published"]
  if pub:
    last = pub[-1]
    print(f"          bank actuatorDelay {last['actuator_delay']:.3f} s   "
          f"responseTau {last['response_tau']:.3f} s   effectiveLag {last['effective_lag']:.3f} s   "
          f"delayLearned {last['delay_learned']}")
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


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("route", nargs="+")
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
    except Exception as e:
      print(f"{route}: {e}", file=sys.stderr)

  if len(args.route) > 1 and summary:
    print(f"\n{'=' * 100}\nACROSS ROUTES: mean corr(u, target)\n{'=' * 100}")
    for name, vals in summary.items():
      wins = sum(1 for i in range(len(vals))
                 if vals[i] == max(summary[k][i] for k in summary))
      print(f"  {name:<18} mean {np.mean(vals):+.3f}   wins {wins}/{len(vals)} routes")
  return 0


if __name__ == "__main__":
  sys.exit(main())
