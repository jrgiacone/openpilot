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

  4. Whichever model's prediction is closer to the real, yaw-derived lateral acceleration -
     RMS over the held-out portion - is the one that actually explains this car, not just
     the one with more confident-looking numbers. The target follows
     ``APPLY_ROLL_COMPENSATION``, so what is scored is what is fitted.

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

  # several splits, or several freeze points, swept on a single pass over the data.
  # Both take a list, so give the routes *first* or argparse reads them as more values:
  ./honda_shadow_compare.py ROUTE_A ROUTE_B --split 0.5 0.25
  ./honda_shadow_compare.py ROUTE_A ROUTE_B --freeze-points 600 5000 40000
"""

import argparse
import math
import sys
from collections import defaultdict, deque
from dataclasses import dataclass

from opendbc.car.honda.steering_learner import (
  DEFAULT_TARGET,
  MAX_LAT_ACCEL,
  MIN_LEARN_SPEED,
  RACK_MOTION_DEADBAND,
  RACK_RATE_TAU,
  SPEED_BUCKET_EDGES,
  STEADY_JERK,
  TARGETS,
  HondaSteeringLearner,
  HondaSteeringModel,
  HondaSteerSample,
  _bucket_index,
  _smooth_sign,
  normalized_command,
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
    # the target's own spread, so RMS can be read on a scale free basis. Absolute RMS is
    # not comparable between targets: each candidate target has a different variance, so a
    # noisier target inflates every model's RMS on it, learned and prior alike.
    self._sum_a = 0.0
    self._sq_a = 0.0
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
    self._sum_a += a
    self._sq_a += a * a

    i = _bucket_index(s.v_ego, SPEED_BUCKET_EDGES)
    if i >= 0:
      b = self.buckets[i]
      b["n"] += 1
      b["learned"] += (a - pred_learned) ** 2
      b["prior"] += (a - pred_prior) ** 2

  def rms(self, which: str) -> float:
    sq = self._sq_learned if which == "learned" else self._sq_prior
    return math.sqrt(sq / self.n) if self.n else float("nan")

  def target_sigma(self) -> float:
    """Spread of the target actually scored, for comparing across candidate targets."""
    if self.n < 2:
      return float("nan")
    return math.sqrt(max(self._sq_a / self.n - (self._sum_a / self.n) ** 2, 0.0))

  def bucket_rms(self, i: int, which: str) -> tuple[float, int]:
    b = self.buckets[i]
    n = b["n"]
    return (math.sqrt(b[which] / n) if n else float("nan")), n


def iter_route(route: str):
  """Every message of ``route`` in time order, one segment held in memory at a time.

  ``LogReader`` caches each decoded segment in ``MultiLogIterator.__lrs`` and never drops
  it, so iterating a 29 segment route holds all 29 decoded at once, and pooling several
  routes holds every segment of every route. That reached 12.7 GB on a 7 route pool and
  OOM'd the machine; the routes that "failed" with an empty error message were MemoryError.
  Sorting is per segment, which is all ``sort_by_time`` does here anyway - segments do not
  overlap in time.
  """
  from openpilot.tools.lib.logreader import LogReader, _LogFileReader

  for ident in LogReader(route).logreader_identifiers:
    yield from _LogFileReader(ident, sort_by_time=True)


def _ground_truth_lat_accel(v_ego: float, yaw_rate: float | None, roll: float,
                             steering_angle_deg: float, steer_ratio: float, wheelbase: float,
                             target: str = DEFAULT_TARGET) -> float:
  """What the car actually did, independent of either model under test.

  Yaw rate when available, the same kinematic fallback ``steering_learner.py`` uses
  otherwise - fixed against the platform's own ``CarParams.steerRatio``, not either model's
  fitted one, so the ground truth does not itself depend on which model is being scored.

  The roll term follows ``target``, because the target scored against has
  to be the target fitted. This subtracted roll unconditionally until the compensation was
  turned off in the learner and this tool was not moved with it, which scored both models
  against a target neither was fitted on. That is not a penalty applied evenly to both: road
  roll enters as sin(roll)*9.81, and on the gentle lane keeping this scores, that estimate
  had a standard deviation 1.07x the lateral acceleration signal itself - enough noise in
  the target to hide a real difference between the two models being compared. Fixing it took
  route 729a2e65b1f6201d/0000001e from "learned beats prior by 23%" to 60%, and a candidate
  extra model term from looking like a wash to visibly making held-out prediction worse -
  which is the whole job of this tool, and it could not do it while scoring the wrong target.
  """
  a = yaw_rate * v_ego if yaw_rate is not None else (
    math.radians(steering_angle_deg) / (steer_ratio * wheelbase) * v_ego ** 2)
  comp = math.sin(roll) * 9.81
  return float({"raw": a, "roll": a - comp, "roll_flipped": a + comp}[target])


@dataclass
class _Stage:
  """One freeze threshold, the model frozen at it, and the scorer holding it out.

  A convergence curve wants several thresholds over the *same* data. Running the tool once
  per threshold re-decodes every segment each time - about ten minutes per pooled pass over
  seven routes - so a list of these rides along on one pass instead: each stage freezes its
  own copy of the model when the learner reaches its own threshold, and scores every sample
  after that into its own scorer. The stages are independent; sharing the pass costs only
  the extra ``model()`` calls.
  """
  freeze_points: int | None  # None: freeze at ``split`` through the route instead
  scorer: _Scorer
  split: float = 0.5
  frozen: HondaSteeringModel | None = None

  @property
  def label(self) -> str:
    return f"@{self.freeze_points}pts" if self.freeze_points is not None else f"@split{self.split:g}"


def compare_route(route: str, learner: HondaSteeringLearner | None,
                   stages: list[_Stage], verbose: bool = False,
                   target: str = DEFAULT_TARGET,
                   ) -> HondaSteeringLearner:
  """Fit ``learner`` causally, freeze its model, and score it and the prior on what follows.

  Two ways to choose the freeze point:

  * ``split`` - a fraction of the *first* route's duration. A stage freezes once and keeps
    that model for every later route; it does **not** re-freeze per route, whatever the
    fraction is nominally of. That makes it a fine A/B harness and a useless convergence
    curve: sweeping ``--split`` from 0.05 to 0.5 over seven routes moved the point count at
    freeze only from 160146 to 181043.

    The corollary is a trap worth stating, because it silently produced a null result:
    **whatever happens on the first route decides what is scored.** Comparing a change that
    only bites after some event - a gain reset, say - against a route order whose first
    route never has that event gives two byte-identical runs and no warning. Order a route
    that exercises the change first.

    This changed silently in `221115603`, which moved `frozen` from a local in this
    function onto the shared stage: before it, every route re-froze at its own split and
    only its own second half was scored. That is why pooled numbers recorded before
    2026-09-10 do not match new ones - the same 7 route pool at split 0.5 reads
    n=110395, normalized 0.900 under the old semantics and n=189473, normalized 0.928
    under these (both measured 2026-09-10, route 00000012 first). Neither is wrong; they
    hold out different sets. Do not compare across the boundary.

  * ``freeze_points`` - freeze once, globally, the first time the learner reaches this many
    points, and keep that model for every later route. This is the one that answers "how
    much data does the learner need before it beats the prior", because the point count at
    freeze is the independent variable rather than an accident of route ordering.

  Each element of ``stages`` picks one of the two, and they are advanced together over a
  single pass of the route.
  """
  from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator

  # Two streaming passes rather than one materialized one. The split point needs the *last*
  # carState time, which is only known at the end of the route, and collecting every message
  # to get it held the whole decoded route in memory: 3.7 GB on route 00000012 alone, and
  # 11 GB part way through a 7 route pool - enough to OOM a 14 GB machine. The first pass
  # keeps two floats. Re-reading costs decode time only; the segment files are already on
  # disk from the first pass.
  split_t: dict[int, float] = {}
  if any(st.freeze_points is None for st in stages):
    t0 = t1 = None
    for m in iter_route(route):
      if m.which() == "carState":
        t = m.logMonoTime * 1e-9
        t0 = t if t0 is None else t0
        t1 = t
    if t0 is None:
      raise ValueError(f"{route}: no carState")
    # several split fractions ride along on the same pass, each with its own freeze time
    split_t = {id(st): t0 + st.split * (t1 - t0) for st in stages if st.freeze_points is None}

  CP = None
  CC = None
  torque_raw = 0.0
  torque_can = 0.0
  calibrator = PoseCalibrator()
  yaw_rate = None
  yaw_rate_t = 0.0
  roll = 0.0
  n_scored_before = [st.scorer.n for st in stages]
  froze_before = [st.frozen is not None for st in stages]
  gain_resets_before = learner.gain_resets if learner is not None else 0
  route_t0 = None
  frame = 0

  for msg in iter_route(route):
    which = msg.which()
    if which == "carParams" and CP is None:
      CP = msg.carParams
      if not str(CP.carFingerprint).startswith(("HONDA", "ACURA")):
        raise ValueError(f"{route}: not a Honda ({CP.carFingerprint})")
      learner = learner or HondaSteeringLearner(CP, dt=DT, target=target)
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
      torque_raw = msg.carOutput.actuatorsOutput.torque
      torque_can = msg.carOutput.actuatorsOutput.torqueOutputCan
    elif which == "carControl":
      CC = msg.carControl
    elif which == "carState" and learner is not None and CC is not None:
      frame += 1
      if frame % DECIMATION:
        continue
      CS = msg.carState
      t = msg.logMonoTime * 1e-9
      route_t0 = t if route_t0 is None else route_t0
      # normalized here rather than at carOutput: CP is only known once carParams has been
      # seen, and this branch cannot run before that
      torque = normalized_command(torque_raw, torque_can, CP)

      sample = HondaSteerSample(
        t=t - route_t0, v_ego=CS.vEgo, torque_cmd=torque, steering_angle_deg=CS.steeringAngleDeg,
        steering_rate_deg=CS.steeringRateDeg, driver_torque=CS.steeringTorque,
        lat_active=CC.latActive, steering_pressed=CS.steeringPressed,
        saturated=abs(torque) > 0.99, yaw_rate=yaw_rate, roll=roll,
        lat_accel_valid=yaw_rate is not None and (t - yaw_rate_t) <= MAX_YAW_AGE,
      )

      # the ground truth does not depend on which stage is scoring, so compute it once
      eligible = (sample.lat_active and not sample.steering_pressed and sample.lat_accel_valid
                  and sample.v_ego >= MIN_LEARN_SPEED)
      a = _ground_truth_lat_accel(sample.v_ego, yaw_rate, roll, sample.steering_angle_deg,
                                  learner.prior.steer_ratio, learner.wheelbase,
                                  target) if eligible else 0.0

      for st in stages:
        if st.frozen is None and (learner.points >= st.freeze_points
                                  if st.freeze_points is not None
                                  else t >= split_t[id(st)]):
          st.frozen = learner.model()
        if st.frozen is None:
          continue
        if not eligible:
          st.scorer.reset()
        else:
          st.scorer.update_rate(sample.steering_rate_deg)
          if abs(a) <= MAX_LAT_ACCEL:
            st.scorer.score(sample, a, st.frozen, learner.prior)

      learner.update(sample)

  for st in stages:
    if st.frozen is None and st.freeze_points is None:
      raise ValueError(f"{route}: never reached the split point")
  # The freeze is global and happens on one route, so that route decides what is held
  # out. A change that only bites after a gain reset, scored against a first route that
  # never resets, gives a byte-identical run and no warning - that has already produced a
  # null result once. Say so rather than letting it pass silently.
  if learner is not None and learner.gain_resets == gain_resets_before:
    for st, before in zip(stages, froze_before, strict=True):
      if not before and st.frozen is not None and st.freeze_points is None:
        print(f"WARNING: {route} {st.label}: the model froze on a route with zero gain "
              "resets, so nothing about reset or recovery behaviour is in the held-out "
              "score. Put a reset-heavy route first.", file=sys.stderr)
  if verbose:
    for st, before in zip(stages, n_scored_before, strict=True):
      if st.frozen is not None:
        print(f"  {route} {st.label}: froze at {st.frozen.points} pts "
              f"(valid={st.frozen.valid}), {st.scorer.n - before} held-out samples scored",
              file=sys.stderr)
  return learner


def _rel_std(cov, gain: float) -> float:
  """Standard error of a fit's gain column as a fraction of the gain itself.

  ``covariance`` is already serialised on every published model, so a gate built on this
  needs no new state and survives a resume - unlike a drift measure, which would need its
  own EMA and a ``MODEL_VERSION`` bump. ``FORGETTING_FACTOR`` and ``P_MAX_SCALE`` put a
  floor and a ceiling under P, so this reads as *current* information about the gain rather
  than everything the fit has ever seen, which is the right thing for "has it settled".
  """
  try:
    var = float(cov[0][0])
  except (TypeError, IndexError, KeyError):
    return float("nan")
  if not (var >= 0.0) or not gain:
    return float("nan")
  return math.sqrt(var) / abs(gain)


def _settledness(m: HondaSteeringModel) -> str:
  """How settled the published gains are, next to the schedule they produced."""
  cov = m.covariance if isinstance(m.covariance, dict) else {}
  vs = m.lat_accel_factor_v or []
  # the steady fit is what every bucket without its own answer falls back to, so score it
  # against the schedule at the reference speed the prior is quoted at
  steady = _rel_std(cov.get("steady"), m.lat_accel_factor(20.0))
  schedule = f"    schedule {[round(v, 3) for v in vs]}  learned_buckets {m.learned_buckets}  points {m.points}"
  out = [schedule, f"    rel std of steady gain {steady:.4f}   per bucket:"]
  per = []
  speed_cov = cov.get("speed") or []
  for i, center in enumerate(speed_bucket_centres()):
    c = speed_cov[i] if i < len(speed_cov) else None
    g = vs[i] if i < len(vs) else 0.0
    per.append(f"~{center:.0f} m/s {_rel_std(c, g):.4f}")
  out[-1] += " " + "  ".join(per)
  return "\n".join(out)


def describe(scorer: _Scorer, frozen: HondaSteeringModel) -> str:
  learned_rms, prior_rms = scorer.rms("learned"), scorer.rms("prior")
  verdict = "NO HELD-OUT DATA" if scorer.n == 0 else (
    f"learned {'BEATS' if learned_rms < prior_rms else 'LOSES TO'} prior by "
    f"{abs(1 - learned_rms / prior_rms) * 100:.0f}%" if prior_rms else "prior RMS is zero")
  sigma = scorer.target_sigma()
  headline = (f"held-out RMS lat accel error: learned {learned_rms:.3f} m/s^2  "
              f"prior {prior_rms:.3f} m/s^2  n={scorer.n}  [{verdict}]  "
              f"(froze {'valid' if frozen.valid else 'NOT CONVERGED'} @ {frozen.points} pts)")
  # RMS is not comparable across targets - each has its own variance - so normalize by it
  normalized = (f"  target sigma {sigma:.3f} m/s^2   normalized: learned {learned_rms / sigma:.3f}  "
                f"prior {prior_rms / sigma:.3f}  (RMS/sigma, <1 beats predicting the mean; "
                f"this is the number to compare across --target)")
  lines = [headline, normalized, _settledness(frozen)]
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
  p.add_argument("--split", type=float, nargs="+", default=[0.5], metavar="F",
                 help="fraction of each platform's combined routes to fit on before freezing "
                      "and scoring the rest (default 0.5). Several values are swept together "
                      "on a single pass over the data")
  p.add_argument("--freeze-points", type=int, nargs="+", default=None, metavar="N",
                 help="freeze the model once, globally, at this many learner points and "
                      "score every sample after it. Use this for a convergence curve; "
                      "--split cannot produce one (see compare_route). Several values are "
                      "swept together on a single pass over the data")
  p.add_argument("--table", action="store_true", help="one line per platform")
  p.add_argument("--target", choices=TARGETS, default=DEFAULT_TARGET,
                 help="which lateral acceleration target to fit and score against "
                      f"(default {DEFAULT_TARGET})")
  p.add_argument("-v", "--verbose", action="store_true")
  args = p.parse_args()

  if any(not 0.0 < f < 1.0 for f in args.split):
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
    stages = ([_Stage(n, _Scorer(DT)) for n in args.freeze_points] if args.freeze_points
              else [_Stage(None, _Scorer(DT), split=f) for f in args.split])
    for route in routes:
      try:
        # routes for one platform share a learner and their scorers: the split applies
        # across the platform's whole route set, not each route individually
        learner = compare_route(route, learner, stages, args.verbose, args.target)
      except Exception as e:  # one bad route must not sink the sweep
        print(f"{car}: {route}: {type(e).__name__}: {e}", file=sys.stderr)
    if learner is None:
      continue

    for st in stages:
      if st.frozen is None:
        print(f"{car}: never reached {st.freeze_points} points", file=sys.stderr)
        continue
      any_scored = True
      label = f"{st.frozen.fingerprint or car} {st.label}"
      if args.table:
        print(f"{label:<26} {describe(st.scorer, st.frozen)}")
      else:
        print(f"\n{label}\n  {describe(st.scorer, st.frozen)}")

  return 0 if any_scored else 1


if __name__ == "__main__":
  sys.exit(main())
