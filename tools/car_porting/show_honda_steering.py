#!/usr/bin/env python3
"""Show what the Honda steering learner has worked out about a car.

Three sources, in the order you are likely to want them:

  # what the car has learned so far, on the device
  ./show_honda_steering.py

  # what it had learned by the end of a drive, from the route's logs
  ./show_honda_steering.py --route <dongle>/<route>

  # how it converged across a drive, one line per publish
  ./show_honda_steering.py --route <dongle>/<route> --history

Every learned value is printed next to the value the platform is hardcoded with today,
which is the whole point: the gap is the argument for or against the tables.
"""

import argparse
import sys

from opendbc.car.honda.steering_learner import HondaSteeringModel, prior_from_car_params

PARAMS_KEY = "HondaSteeringParameters"


def model_from_msg(p) -> HondaSteeringModel:
  return HondaSteeringModel(
    fingerprint=p.carFingerprint,
    lat_accel_factor_bp=list(p.latAccelFactorBP),
    lat_accel_factor_v=list(p.latAccelFactorV),
    friction=p.friction,
    offset=p.offset,
    asymmetry=p.asymmetry,
    actuator_delay=p.actuatorDelay,
    response_tau=p.responseTau,
    max_useful_torque=p.maxUsefulTorque,
    steer_ratio=p.steerRatio,
    understeer_gradient=p.understeerGradient,
    driver_torque_threshold=p.driverTorqueThreshold,
    points=p.points,
    learned_buckets=p.learnedBuckets,
    valid=p.valid,
    diverged=p.diverged,
    resets=p.resets,
    asymmetry_learned=p.asymmetryLearned,
  )


def report(model: HondaSteeringModel, prior: HondaSteeringModel | None) -> str:
  def vs(learned: float, prior_value: float | None, fmt: str = "{:.3f}") -> str:
    if prior_value is None:
      return fmt.format(learned)
    return f"{fmt.format(learned)}  (hardcoded {fmt.format(prior_value)})"

  sched = "  ".join(f"{v:.2f} @ {bp:.0f} m/s" for bp, v in
                    zip(model.lat_accel_factor_bp, model.lat_accel_factor_v, strict=True))
  lines = [
    f"{model.fingerprint}   {model.points} points, "
    f"{model.learned_buckets} speed buckets learned, "
    f"{'converged' if model.valid else 'DIVERGED - fit reset' if model.diverged else 'NOT CONVERGED - keep driving'}"
    + (f", {model.resets} reset(s)" if model.resets else ""),
    "",
    f"  EPS gain     {sched}",
    f"               m/s^2 of lateral acceleration per unit of steer command"
    + (f"; every Honda's prior is {prior.lat_accel_factor(20.0):.2f}" if prior else ""),
    f"  friction     {vs(model.friction, prior.friction if prior else None)}",
    f"  offset       {model.offset:+.3f}   road crown, alignment and EPS trim",
    f"  asymmetry    {model.asymmetry:+.3f}   right gain minus left"
    + ("" if model.asymmetry_learned else "   (not yet excited both ways)"),
    f"  lag          {vs(model.effective_lag, prior.effective_lag if prior else None)} s"
    f"   = dead time {model.actuator_delay:.3f} + rack tau {model.response_tau:.3f}",
    f"  steer ratio  {vs(model.steer_ratio, prior.steer_ratio if prior else None, '{:.2f}')}",
    f"  understeer   {model.understeer_gradient:+.4f} rad per m/s^2",
    f"  override     {model.driver_torque_threshold:.0f}"
    + (f"  (values.py STEER_THRESHOLD {prior.driver_torque_threshold:.0f})" if prior else ""),
  ]
  return "\n".join(lines)


def prior_for(fingerprint: str) -> HondaSteeringModel | None:
  """The platform's hand tuned starting point, for comparison."""
  try:
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR
    return prior_from_car_params(CarInterface.get_non_essential_params(CAR(fingerprint)))
  except Exception:  # noqa: BLE001 - a fork's platform may not resolve; the report still works
    return None


def from_device() -> int:
  from openpilot.common.params import Params
  raw = Params().get(PARAMS_KEY)
  if raw is None:
    print("nothing learned yet: no cached model on this device.\n"
          "hondasteerd caches once the model converges, about a minute of usable driving "
          "after it does.", file=sys.stderr)
    return 1
  model = HondaSteeringModel.from_json(raw)
  print(report(model, prior_for(model.fingerprint)))
  return 0


def from_route(route: str, history: bool) -> int:
  from openpilot.tools.lib.logreader import LogReader

  last = None
  n = 0
  for msg in LogReader(route, sort_by_time=True):
    if msg.which() != "hondaSteeringParameters":
      continue
    last = msg.hondaSteeringParameters
    n += 1
    if history:
      m = model_from_msg(last)
      print(f"{n:5d}  {m.points:7d} pts  gain {m.lat_accel_factor(20.0):5.2f}  "
            f"friction {m.friction:6.3f}  offset {m.offset:+6.3f}  "
            f"lag {m.effective_lag:5.3f}s  {'valid' if m.valid else ''}")

  if last is None:
    print(f"{route}: no hondaSteeringParameters in this route.\n"
          "Either the route predates hondasteerd, or the car is not a Honda.", file=sys.stderr)
    return 1

  model = model_from_msg(last)
  if history:
    print()
  print(report(model, prior_for(model.fingerprint)))
  return 0


def main() -> int:
  p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  p.add_argument("--route", help="read from a route's logs instead of this device")
  p.add_argument("--history", action="store_true", help="print every publish, not just the last")
  args = p.parse_args()

  if args.route:
    return from_route(args.route, args.history)
  if args.history:
    p.error("--history needs --route")
  return from_device()


if __name__ == "__main__":
  sys.exit(main())
