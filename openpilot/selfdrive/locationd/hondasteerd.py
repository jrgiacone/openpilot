#!/usr/bin/env python3
"""Observe-only identification of Honda steering.

Runs the learner in ``opendbc/car/honda/steering_learner.py`` alongside whatever is
actually steering the car, publishes what it has learned as ``hondaSteeringParameters``,
and caches it in ``Params`` so it survives ignition cycles.

Nothing in the control path reads any of this. The point is to collect real per-car
models - EPS gain against speed, friction, bias, asymmetry, lag, steer ratio, driver
override threshold - across real Hondas and compare them against the hand tuned tables
in ``opendbc/car/honda`` before deciding whether an adaptive controller should ever get
the wheel.

The cache is keyed by fingerprint and model version: a different car, or a learner whose
model has changed shape, starts over rather than inheriting someone else's numbers.
"""

import openpilot.cereal.messaging as messaging
from opendbc.car.structs import car
from opendbc.car.honda.steering_learner import (
  MODEL_VERSION,
  HondaSteeringLearner,
  HondaSteeringModel,
  HondaSteerSample,
)
from openpilot.common.params import Params
from openpilot.common.realtime import config_realtime_process
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.locationd.helpers import Pose, PoseCalibrator

PARAMS_KEY = "HondaSteeringParameters"

# carState arrives at 100 Hz. The learner is rate independent and costs about 76 us per
# update, so running it at every other message keeps it under half a percent of a core
# while staying fine enough for the delay bank, whose candidates are 30 ms apart.
DECIMATION = 2
DT = 0.01 * DECIMATION

PUBLISH_DECIMATION = 25    # ~4 Hz relative to the decimated rate
CACHE_DECIMATION = 3000    # ~60 s


def is_honda(CP) -> bool:
  return CP.brand == "honda"


def load_cached(fingerprint: str) -> HondaSteeringModel | None:
  """The model from a previous ignition, if it belongs to this car and this learner."""
  raw = Params().get(PARAMS_KEY)
  if raw is None:
    return None
  try:
    model = HondaSteeringModel.from_json(raw)
  except (ValueError, TypeError) as e:
    cloudlog.warning(f"hondasteerd: discarding unreadable cache: {e}")
    return None

  if model.fingerprint != fingerprint:
    cloudlog.warning(f"hondasteerd: cache is for {model.fingerprint}, this is {fingerprint}; starting over")
    return None
  if not model.valid:
    return None
  cloudlog.info(f"hondasteerd: resuming {fingerprint} from cache, {model.points} points")
  return model


def fill_msg(model: HondaSteeringModel, valid: bool):
  msg = messaging.new_message('hondaSteeringParameters')
  msg.valid = valid
  p = msg.hondaSteeringParameters
  p.valid = model.valid
  p.carFingerprint = model.fingerprint
  p.latAccelFactorBP = [float(v) for v in model.lat_accel_factor_bp]
  p.latAccelFactorV = [float(v) for v in model.lat_accel_factor_v]
  p.friction = float(model.friction)
  p.offset = float(model.offset)
  p.asymmetry = float(model.asymmetry)
  p.actuatorDelay = float(model.actuator_delay)
  p.responseTau = float(model.response_tau)
  p.maxUsefulTorque = float(model.max_useful_torque)
  p.steerRatio = float(model.steer_ratio)
  p.understeerGradient = float(model.understeer_gradient)
  p.driverTorqueThreshold = float(model.driver_torque_threshold)
  p.points = int(model.points)
  p.learnedBuckets = int(model.learned_buckets)
  p.modelVersion = MODEL_VERSION
  return msg


def main():
  config_realtime_process([0, 1, 2, 3], 5)

  params = Params()
  CP = messaging.log_from_bytes(params.get("CarParams", block=True), car.CarParams)
  if not is_honda(CP):
    cloudlog.info(f"hondasteerd: {CP.carFingerprint} is not a Honda, exiting")
    return

  fingerprint = str(CP.carFingerprint)
  learner = HondaSteeringLearner(CP, dt=DT, learned=load_cached(fingerprint))
  calibrator = PoseCalibrator()

  pm = messaging.PubMaster(['hondaSteeringParameters'])
  sm = messaging.SubMaster(['carControl', 'carOutput', 'carState', 'deviceMotion',
                            'extrinsicsCalibration', 'vehicleParameters'], poll='carState')

  # deviceMotion runs at 20 Hz against the learner's 50 Hz, so yaw rate is held between
  # updates. The learner differentiates lateral acceleration over 0.1 s, which spans two
  # updates, so the staircase is smoothed rather than differentiated.
  yaw_rate = None
  roll = 0.0
  t0 = None
  frame = 0

  while True:
    sm.update()
    if not sm.updated['carState']:
      continue

    if sm.updated['extrinsicsCalibration']:
      calibrator.feed_extrinsics_calibration(sm['extrinsicsCalibration'])
    if sm.updated['vehicleParameters']:
      roll = sm['vehicleParameters'].roll
    if sm.updated['deviceMotion']:
      dm = sm['deviceMotion']
      if dm.angularVelocityDevice.valid and dm.orientationNED.valid and dm.inputsOK and dm.sensorsOK:
        yaw_rate = calibrator.build_calibrated_pose(Pose.from_device_motion(dm)).angular_velocity.yaw
      else:
        yaw_rate = None

    if sm.frame % DECIMATION:
      continue
    frame += 1

    CS, CC = sm['carState'], sm['carControl']
    torque = sm['carOutput'].actuatorsOutput.torque
    t = sm.logMonoTime['carState'] * 1e-9
    t0 = t if t0 is None else t0

    # Everything below only reads. A bad sample can bias a model; it cannot move the car.
    learner.update(HondaSteerSample(
      t=t - t0,
      v_ego=CS.vEgo,
      torque_cmd=torque,
      steering_angle_deg=CS.steeringAngleDeg,
      steering_rate_deg=CS.steeringRateDeg,
      driver_torque=CS.steeringTorque,
      lat_active=CC.latActive and sm.all_checks(),
      steering_pressed=CS.steeringPressed,
      # controlsState carries the authoritative saturation flag but is decimated in
      # qlogs; the command itself is the reliable signal that the rack ran out of room
      saturated=abs(torque) > 0.99,
      yaw_rate=yaw_rate,
      roll=roll,
    ))

    if frame % PUBLISH_DECIMATION == 0:
      pm.send('hondaSteeringParameters', fill_msg(learner.model(), sm.all_checks()))

    if frame % CACHE_DECIMATION == 0:
      model = learner.model()
      if model.valid:
        params.put(PARAMS_KEY, model.to_json())


if __name__ == "__main__":
  main()
