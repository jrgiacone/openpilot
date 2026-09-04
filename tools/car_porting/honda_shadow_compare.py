#!/usr/bin/env python3
"""Shadow-mode comparison: does the learned Honda steering model predict the car's actual
behavior better than the hand-tuned prior it started from?

This is the gate before anything in ``steering_learner.py`` is worth wiring into control.
Nothing here touches the control path - it is a pure open-loop, out-of-sample comparison:

  1. A learner is fit causally over the first ``--split`` fraction of a route (or, with
     ``--all``, every route the fleet already has for a platform - more coverage before the
     split means a fairer test of what the model has actually learned).
  2. Its model is *frozen* at that point.
  3. Over the rest of the route - data the frozen model never saw - every steady-state
     sample (active, hands-off, settled, unsaturated, |lat_jerk| <= STEADY_JERK: the same
     gating ``steering_learner.py`` scores its own fit on) is used to ask both the frozen
     learned model and the platform's unlearned prior to predict the lateral acceleration
     the command *actually sent* produced, using the same forward equation ``steady_rls``
     fits (see ``steering_learner.py``'s module docstring):

       a_pred = K(v)*(u - offset - friction*sign(rate) - asymmetry*max(u, 0))

  4. Whichever model's prediction is closer to the real, roll-compensated, yaw-derived
     lateral acceleration - RMS over the held-out portion - is the one that actually
     explains this car, not just the one with more confident-looking numbers.

A model that does not beat its own prior here has no business informing a tune change,
whatever ``model().valid`` says: ``valid`` only means enough was measured to have an
opinion, not that the opinion is a better one than not measuring at all.

Examples::

  # one route, holding out the last half for scoring
  ./honda_shadow_compare.py 729a2e65b1f6201d/00000011--a13bdcf90d

  # every Honda/Acura route in opendbc/car/tests/routes.py, one line per platform
  ./honda_shadow_compare.py --all --table

  # fit on the first quarter, score the rest - a harsher test of early convergence
  ./honda_shadow_compare.py --all --split 0.25 --table
"""

import argparse
import math
import sys
from collections import defaultdict, deque

from opendbc.car.honda.steering_learner import (
  MAX_LAT_ACCEL,
  MIN_LEARN_SPEED,
  RACK_MOTION_DEADBAND,
  RACK_RATE_TAU,
  SPEED_BUCKET_EDGES,
  STEADY_JERK,
  HondaSteeringLearner,
  HondaSteeringModel,
  HondaSteerSample,
  _bucket_index,
  _smooth_sign,
  speed_bucket_centres,
)
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.tests.routes import routes as CAR_TEST_ROUTES
# deferred: openpilot.selfdrive.locationd.helpers and openpilot.tools.lib.logreader need the
# full build (capnp-generated messaging bindings) that a plain opendbc checkout does not have.
# Importing them lazily, only where a route is actually read, keeps the scoring logic in this
# file - _predict/_Scorer/_ground_truth_lat_accel - importable and unit-testable without it.

# hondasteerd decimates carState by 2 before feeding the learner, so the fit and the
# scoring both have to run at 50 Hz to be the estimator that actually runs on the car.
DECIMATION = 2
DT = 0.01 * DECIMATION
# The calibrated frame is z-down, so a positive yaw rate is a right hand turn, while
# steering angle and the torque command are both positive-left - see hondasteerd.py.
YAW_SIGN = -1.0
MAX_YAW_AGE = 0.1
JERK_WINDOW_S = 0.1


def honda_routes() -> dict[str, list[str]]:
  """Every Honda/Acura route the car test suite knows about, grouped by platform."""
  out: dict[str, list[str]] = defaultdict(list)
  honda = {str(c) for c in HONDA}
  for r in CAR_TEST_ROUTES:
    if str(r.car_model) in honda:
      out[str(r.car_model)].append(r.route)
  return dict(out)


def _predict(model: HondaSteeringModel, v_ego: float, u: float, rate_filt: float) -> float:
  """The lateral acceleration this model predicts for a command already sent.

  a = K(v)*(u - offset - friction*sign(rate) - asymmetry*max(u, 0)): the same forward
  equation ``HondaSteeringLearner``'s ``steady_rls`` fits, evaluated forward instead of
  fit backward. The lag term is left out deliberately - it needs history the split point
  does not have a clean way to hand across, and the static terms are what this tool exists
  to check.
  """
  k = model.lat_accel_factor(v_ego)
  sign = _smooth_sign(rate_filt, RACK_MOTION_DEADBAND)
  asym = model.asymmetry * max(u, 0.0)
  return k * (u - model.offset - model.friction * sign - asym)


class _Scorer:
  """Held-out RMS prediction error for the frozen learned model and the prior, together."""

  def __init__(self, dt: float):
    self.dt = dt
    self._jerk_window = max(1, int(round(JERK_WINDOW_S / dt)))
    self._accel_hist: deque[float] = deque(maxlen=self._jerk_window + 1)
    self._rate_filt = 0.0
    self.n = 0
    self._sq_learned = 0.0
    self._sq_prior = 0.0
    self.buckets = defaultdict(lambda: {"n": 0, "learned": 0.0, "prior": 0.0})

  def reset(self) -> None:
    """Same disengage/override reset ``HondaSteeringLearner.update`` does: a gap in active
    control breaks the jerk window and the friction-sign filter, same as it would for the
    learner fitting live."""
    self._accel_hist.clear()
    self._rate_filt = 0.0

  def update_rate(self, rate_deg: float) -> None:
    self._rate_filt += (rate_deg - self._rate_filt) * self.dt / RACK_RATE_TAU

  def score(self, s: HondaSteerSample, a: float, frozen: HondaSteeringModel,
            prior: HondaSteeringModel) -> None:
    self._accel_hist.append(a)
    if len(self._accel_hist) < self._accel_hist.maxlen:
      return
    lat_jerk = (self._accel_hist[-1] - self._accel_hist[0]) / (self._jerk_window * self.dt)
    if abs(lat_jerk) > STEADY_JERK or s.saturated or abs(s.torque_cmd) >= 0.99:
      return

    pred_learned = _predict(frozen, s.v_ego, s.torque_cmd, self._rate_filt)
    pred_prior = _predict(prior, s.v_ego, s.torque_cmd, self._rate_filt)
    self.n += 1
    self._sq_learned += (a - pred_learned) ** 2
    self._sq_prior += (a - pred_prior) ** 2

    i = _bucket_index(s.v_ego, SPEED_BUCKET_EDGES)
    if i >= 0:
      b = self.buckets[i]
      b["n"] += 1
      b["learned"] += (a - pred_learned) ** 2
      b["prior"] += (a - pred_prior) ** 2

  def rms(self, which: str) -> float:
    sq = self._sq_learned if which == "learned" else self._sq_prior
    return math.sqrt(sq / self.n) if self.n else float("nan")

  def bucket_rms(self, i: int, which: str) -> tuple[float, int]:
    b = self.buckets[i]
    n = b["n"]
    return (math.sqrt(b[which] / n) if n else float("nan")), n


def _ground_truth_lat_accel(v_ego: float, yaw_rate: float | None, roll: float,
                             steering_angle_deg: float, steer_ratio: float, wheelbase: float) -> float:
  """What the car actually did, independent of either model under test.

  Yaw rate when available, the same kinematic fallback ``steering_learner.py`` uses
  otherwise - fixed against the platform's own ``CarParams.steerRatio``, not either model's
  fitted one, so the ground truth does not itself depend on which model is being scored.
  """
  a = yaw_rate * v_ego if yaw_rate is not None else (
    math.radians(steering_angle_deg) / (steer_ratio * wheelbase) * v_ego ** 2)
  return a - math.sin(roll) * 9.81


def compare_route(route: str, split: float, learner: HondaSteeringLearner | None,
                   scorer: _Scorer, verbose: bool = False) -> tuple[HondaSteeringLearner, HondaSteeringModel]:
  """Fit ``learner`` causally over the first ``split`` fraction of a route, freeze its model
  there, and score the frozen model plus the prior on every steady-state sample after it."""
  from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator
  from openpilot.tools.lib.logreader import LogReader

  lr = LogReader(route, sort_by_time=True)
  msgs = list(lr)

  times = [m.logMonoTime * 1e-9 for m in msgs if m.which() == "carState"]
  if not times:
    raise ValueError(f"{route}: no carState")
  t0, t1 = times[0], times[-1]
  split_t = t0 + split * (t1 - t0)

  CP = None
  CC = None
  torque = 0.0
  calibrator = PoseCalibrator()
  yaw_rate = None
  yaw_rate_t = 0.0
  roll = 0.0
  frozen: HondaSteeringModel | None = None
  n_scored_before = scorer.n
  frame = 0

  for msg in msgs:
    which = msg.which()
    if which == "carParams" and CP is None:
      CP = msg.carParams
      if not str(CP.carFingerprint).startswith(("HONDA", "ACURA")):
        raise ValueError(f"{route}: not a Honda ({CP.carFingerprint})")
      learner = learner or HondaSteeringLearner(CP, dt=DT)
    elif which == "extrinsicsCalibration":
      calibrator.feed_extrinsics_calibration(msg.extrinsicsCalibration)
    elif which == "vehicleParameters":
      roll = msg.vehicleParameters.roll
    elif which == "deviceMotion":
      dm = msg.deviceMotion
      if dm.angularVelocityDevice.valid and dm.orientationNED.valid and dm.inputsOK and dm.sensorsOK:
        yaw_rate = YAW_SIGN * calibrator.build_calibrated_pose(Pose.from_device_motion(dm)).angular_velocity.yaw
        yaw_rate_t = msg.logMonoTime * 1e-9
      else:
        yaw_rate = None
    elif which == "carOutput":
      torque = msg.carOutput.actuatorsOutput.torque
    elif which == "carControl":
      CC = msg.carControl
    elif which == "carState" and learner is not None and CC is not None:
      frame += 1
      if frame % DECIMATION:
        continue
      CS = msg.carState
      t = msg.logMonoTime * 1e-9

      sample = HondaSteerSample(
        t=t - t0, v_ego=CS.vEgo, torque_cmd=torque, steering_angle_deg=CS.steeringAngleDeg,
        steering_rate_deg=CS.steeringRateDeg, driver_torque=CS.steeringTorque,
        lat_active=CC.latActive, steering_pressed=CS.steeringPressed,
        saturated=abs(torque) > 0.99, yaw_rate=yaw_rate, roll=roll,
        lat_accel_valid=yaw_rate is not None and (t - yaw_rate_t) <= MAX_YAW_AGE,
      )

      if frozen is None and t >= split_t:
        frozen = learner.model()

      if frozen is not None:
        if not sample.lat_active or sample.steering_pressed or not sample.lat_accel_valid \
           or sample.v_ego < MIN_LEARN_SPEED:
          scorer.reset()
        else:
          scorer.update_rate(sample.steering_rate_deg)
          a = _ground_truth_lat_accel(sample.v_ego, yaw_rate, roll, sample.steering_angle_deg,
                                      learner.prior.steer_ratio, learner.wheelbase)
          if abs(a) <= MAX_LAT_ACCEL:
            scorer.score(sample, a, frozen, learner.prior)

      learner.update(sample)

  if frozen is None:
    raise ValueError(f"{route}: never reached the split point")
  if verbose:
    print(f"  {route}: froze at {frozen.points} pts (valid={frozen.valid}), "
          f"{scorer.n - n_scored_before} held-out samples scored", file=sys.stderr)
  return learner, frozen


def describe(scorer: _Scorer, frozen: HondaSteeringModel) -> str:
  learned_rms, prior_rms = scorer.rms("learned"), scorer.rms("prior")
  verdict = "NO HELD-OUT DATA" if scorer.n == 0 else (
    f"learned {'BEATS' if learned_rms < prior_rms else 'LOSES TO'} prior by "
    f"{abs(1 - learned_rms / prior_rms) * 100:.0f}%" if prior_rms else "prior RMS is zero")
  lines = [f"held-out RMS lat accel error: learned {learned_rms:.3f} m/s^2  "
           f"prior {prior_rms:.3f} m/s^2  n={scorer.n}  [{verdict}]  "
           f"(froze {'valid' if frozen.valid else 'NOT CONVERGED'} @ {frozen.points} pts)"]
  for i, center in enumerate(speed_bucket_centres()):
    lr, n = scorer.bucket_rms(i, "learned")
    pr, _ = scorer.bucket_rms(i, "prior")
    if n:
      lines.append(f"    ~{center:>4.0f} m/s: learned {lr:.3f}  prior {pr:.3f}  n={n}")
  return "\n".join(lines)


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("route", nargs="*", help="route name(s), e.g. 729a2e65b1f6201d/00000011--a13bdcf90d")
  p.add_argument("--all", action="store_true", help="every Honda route in opendbc/car/tests/routes.py")
  p.add_argument("--car", action="append", help="limit --all to these platforms")
  p.add_argument("--split", type=float, default=0.5,
                 help="fraction of each platform's combined routes to fit on before freezing "
                      "and scoring the rest (default 0.5)")
  p.add_argument("--table", action="store_true", help="one line per platform")
  p.add_argument("-v", "--verbose", action="store_true")
  args = p.parse_args()

  if not 0.0 < args.split < 1.0:
    p.error("--split must be between 0 and 1")

  jobs: dict[str, list[str]] = {}
  if args.all:
    jobs = honda_routes()
    if args.car:
      jobs = {k: v for k, v in jobs.items() if k in set(args.car)}
  for r in args.route:
    jobs.setdefault("(route)", []).append(r)
  if not jobs:
    p.error("give a route or --all")

  any_scored = False
  for car, routes in sorted(jobs.items()):
    learner = None
    scorer = _Scorer(DT)
    frozen = None
    for route in routes:
      try:
        # routes for one platform share a learner and a scorer: the split applies across
        # the platform's whole route set, not each route individually
        learner, frozen = compare_route(route, args.split, learner, scorer, args.verbose)
      except Exception as e:  # one bad route must not sink the sweep
        print(f"{car}: {route}: {e}", file=sys.stderr)
    if learner is None or frozen is None:
      continue

    any_scored = True
    label = frozen.fingerprint or car
    if args.table:
      print(f"{label:<26} {describe(scorer, frozen)}")
    else:
      print(f"\n{label}\n  {describe(scorer, frozen)}")

  return 0 if any_scored else 1


if __name__ == "__main__":
  sys.exit(main())
