#!/usr/bin/env python3
"""Identify a Honda's steering from logs.

Replays one or more routes through :class:`opendbc.car.honda.steering_learner.HondaSteeringLearner`
and prints what it learned: the EPS gain schedule, friction, bias, command-to-motion lag,
usable torque range and driver override threshold, next to the values the platform is
currently hardcoded with in ``opendbc/car/honda``.

Examples::

  # one route
  ./learn_honda_steering.py a74b011b32b51b56/2020-07-26--17-09-36

  # every Honda/Acura route in opendbc/car/tests/routes.py, one line per platform
  ./learn_honda_steering.py --all --table

  # write the models out so they can be shipped as per-platform defaults
  ./learn_honda_steering.py --all --out honda_steering_models.json
"""

import argparse
import json
import sys
from collections import defaultdict

from opendbc.car.honda.steering_learner import HondaSteeringLearner, HondaSteerSample, prior_from_car_params
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.tests.routes import routes as CAR_TEST_ROUTES
from openpilot.tools.lib.logreader import LogReader

DT = 0.01


def honda_routes() -> dict[str, list[str]]:
  """Every Honda/Acura route the car test suite knows about, grouped by platform."""
  out: dict[str, list[str]] = defaultdict(list)
  honda = {str(c) for c in HONDA}
  for r in CAR_TEST_ROUTES:
    if str(r.car_model) in honda:
      out[str(r.car_model)].append(r.route)
  return dict(out)


def learn_route(route: str, learner: HondaSteeringLearner | None = None, verbose: bool = False):
  """Feed one route to a learner, creating one from the route's own carParams if needed."""
  lr = LogReader(route, sort_by_time=True)

  CS = CC = None
  torque = 0.0
  yaw_rate = None
  roll = 0.0
  t0 = None
  n = 0

  for msg in lr:
    which = msg.which()
    if which == "carParams" and learner is None:
      CP = msg.carParams
      if not str(CP.carFingerprint).startswith(("HONDA", "ACURA")):
        raise ValueError(f"{route}: not a Honda ({CP.carFingerprint})")
      learner = HondaSteeringLearner(CP, dt=DT)
    elif which == "deviceMotion":
      yaw_rate = msg.deviceMotion.angularVelocityDevice.z
    elif which == "vehicleParameters":
      roll = msg.vehicleParameters.roll
    elif which == "carOutput":
      torque = msg.carOutput.actuatorsOutput.torque
    elif which == "carControl":
      CC = msg.carControl
    elif which == "carState" and learner is not None and CC is not None:
      CS = msg.carState
      t = msg.logMonoTime * 1e-9
      t0 = t if t0 is None else t0
      learner.update(HondaSteerSample(
        t=t - t0,
        v_ego=CS.vEgo,
        torque_cmd=torque,
        steering_angle_deg=CS.steeringAngleDeg,
        steering_rate_deg=CS.steeringRateDeg,
        driver_torque=CS.steeringTorque,
        lat_active=CC.latActive,
        steering_pressed=CS.steeringPressed,
        # openpilot reports lateral saturation on controlsState, which is decimated in
        # qlogs; the command itself is the reliable signal that the rack ran out of room
        saturated=abs(torque) > 0.99,
        yaw_rate=yaw_rate,
        roll=roll,
      ))
      n += 1

  if learner is None:
    raise ValueError(f"{route}: no carParams in log")
  if verbose:
    print(f"  {route}: {n} samples, {learner.points} usable", file=sys.stderr)
  return learner


def describe(model, prior) -> str:
  sched = " ".join(f"{v:.2f}@{bp:.0f}" for bp, v in zip(model.lat_accel_factor_bp,
                                                        model.lat_accel_factor_v, strict=True))
  return (f"gain[m/s^2 per unit torque] {sched} (prior {prior.lat_accel_factor(20.0):.2f})  "
          f"friction {model.friction:.3f}  offset {model.offset:+.3f}  "
          f"asym {model.asymmetry:+.3f}  lag {model.effective_lag:.3f}s "
          f"(delay {model.actuator_delay:.3f} + tau {model.response_tau:.3f}, "
          f"prior {prior.actuator_delay:.3f})  "
          f"usable torque {model.deadzone:.2f}..{model.max_useful_torque:.2f}  "
          f"steer ratio {model.steer_ratio:.2f} (prior {prior.steer_ratio:.2f})  "
          f"override {model.driver_torque_threshold:.0f}  "
          f"[{model.points} pts, {'valid' if model.valid else 'NOT CONVERGED'}]")


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("route", nargs="*", help="route name(s), e.g. a74b011b32b51b56/2020-07-26--17-09-36")
  p.add_argument("--all", action="store_true", help="every Honda route in opendbc/car/tests/routes.py")
  p.add_argument("--car", action="append", help="limit --all to these platforms")
  p.add_argument("--table", action="store_true", help="one line per platform")
  p.add_argument("--out", help="write the learned models to this JSON file")
  p.add_argument("-v", "--verbose", action="store_true")
  args = p.parse_args()

  jobs: dict[str, list[str]] = {}
  if args.all:
    jobs = honda_routes()
    if args.car:
      jobs = {k: v for k, v in jobs.items() if k in set(args.car)}
  for r in args.route:
    jobs.setdefault("(route)", []).append(r)
  if not jobs:
    p.error("give a route or --all")

  models = {}
  for car, routes in sorted(jobs.items()):
    learner = None
    for route in routes:
      try:
        # routes for one platform share a learner: more of the speed and curvature range
        # gets covered, which is exactly what the bucket gating is waiting for
        learner = learn_route(route, learner, args.verbose)
      except Exception as e:  # noqa: BLE001 - one bad route must not sink the sweep
        print(f"{car}: {route}: {e}", file=sys.stderr)
    if learner is None:
      continue

    model = learner.model()
    models[model.fingerprint or car] = model.to_dict()
    prior = learner.prior
    if args.table:
      print(f"{model.fingerprint or car:<26} {describe(model, prior)}")
    else:
      print(f"\n{model.fingerprint or car}\n  {describe(model, prior)}")

  if args.out:
    with open(args.out, "w") as f:
      json.dump(models, f, indent=2, sort_keys=True)
    print(f"\nwrote {len(models)} models to {args.out}", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main())
