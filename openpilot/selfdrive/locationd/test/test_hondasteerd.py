import json
import math
import pathlib
import unittest

import numpy as np

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.steering_learner import (
  MODEL_VERSION,
  HondaSteeringLearner,
  HondaSteerSample,
  prior_from_car_params,
)
from opendbc.car.honda.values import CAR
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.locationd.hondasteerd import DT, PARAMS_KEY, YAW_SIGN, fill_msg, parse_cached


def a_model(fingerprint=CAR.HONDA_CIVIC_2022, valid=True):
  m = prior_from_car_params(CarInterface.get_non_essential_params(fingerprint))
  m.valid = valid
  m.points = 5000
  return m


class ApproxMixin:
  """``pytest.approx``'s default tolerance (rel=1e-6, abs=1e-12), for a unittest TestCase.

  These assertions mostly compare a Float32 read back out of capnp against the Python
  float that went in, so they need a relative tolerance rather than a fixed number of
  decimal places: ``driverTorqueThreshold`` is O(1e3) and ``friction`` is O(1e-2).
  """

  def assertClose(self, actual, expected, rel=1e-6, msg=None):
    if isinstance(expected, list | tuple):
      self.assertEqual(len(actual), len(expected), msg)
      for a, e in zip(actual, expected, strict=True):
        self.assertClose(a, e, rel=rel, msg=msg)
      return
    self.assertAlmostEqual(actual, expected, delta=abs(expected) * rel + 1e-12, msg=msg)


class TestHondaSteerdParamsKey(unittest.TestCase):
  def test_the_cache_key_is_registered(self):
    """Params.get raises on any key missing from params_keys.h.

    An unregistered key is not a silent no-op: it takes the daemon down on its first
    read, before the learner is even constructed, and the only visible symptom is
    process_not_running.
    """
    registry = pathlib.Path(__file__).parents[3] / "common" / "params_keys.h"
    assert f'"{PARAMS_KEY}"' in registry.read_text(), \
      f"{PARAMS_KEY} must be registered in {registry}"


class TestHondaSteerdCache(OpenpilotTestCase):
  # test_round_trips_through_params writes to Params, so this class takes the per-test
  # OpenpilotPrefix isolation the sibling locationd tests use
  def test_round_trips(self):
    m = a_model()
    assert parse_cached(m.to_json(), m.fingerprint) == m

  def test_round_trips_through_params(self):
    """The write path, which the earlier tests never touched.

    Params.put casts by (python type, key type): a JSON-typed key takes a dict and
    rejects a str, and Params.get on that key hands back a parsed dict rather than text.
    Both halves have to agree, and only an end-to-end round trip catches it.
    """
    from openpilot.common.params import Params
    m = a_model()
    params = Params()
    params.put(PARAMS_KEY, m.to_dict())
    assert parse_cached(params.get(PARAMS_KEY), m.fingerprint) == m

  def test_accepts_a_parsed_dict(self):
    m = a_model()
    assert parse_cached(m.to_dict(), m.fingerprint) == m

  def test_rejects_another_car(self):
    """A cache must never seed a car it was not measured on."""
    m = a_model(CAR.HONDA_CIVIC_2022)
    assert parse_cached(m.to_json(), str(CAR.HONDA_PILOT)) is None

  def test_rejects_an_older_model_version(self):
    """A learner whose model has changed shape starts over rather than misreading a cache."""
    d = a_model().to_dict()
    d["version"] = MODEL_VERSION + 1
    assert parse_cached(json.dumps(d), d["fingerprint"]) is None

  def test_survives_a_damaged_cache(self):
    """Whatever is in the key, the daemon must start; the worst case is starting fresh."""
    for raw in (None, "", "{", b"not json", json.dumps({"version": MODEL_VERSION})):
      with self.subTest(raw=raw):
        assert parse_cached(raw, str(CAR.HONDA_CIVIC_2022)) is None

  def test_ignores_an_unconverged_cache(self):
    assert parse_cached(a_model(valid=False).to_json(), str(CAR.HONDA_CIVIC_2022)) is None


class TestHondaSteerdMsg(ApproxMixin, unittest.TestCase):
  def test_carries_every_learned_field(self):
    m = a_model()
    m.friction, m.offset, m.asymmetry = 0.041, -0.017, 0.008
    m.actuator_delay, m.response_tau = 0.183, 0.072
    m.roll_comp_fraction, m.lat_accel_torque_corr, m.lat_accel_torque_corr_raw = 0.93, 0.21, 0.14
    m.delay_learned, m.delay_railed = True, False
    m.saturated_fraction = 0.06
    p = fill_msg(m, valid=True).hondaSteeringParameters

    assert p.valid and p.carFingerprint == m.fingerprint
    self.assertClose(list(p.latAccelFactorBP), m.lat_accel_factor_bp)
    self.assertClose(list(p.latAccelFactorV), m.lat_accel_factor_v)
    self.assertClose(p.friction, m.friction)
    self.assertClose(p.offset, m.offset)
    self.assertClose(p.asymmetry, m.asymmetry)
    self.assertClose(p.actuatorDelay, m.actuator_delay)
    self.assertClose(p.responseTau, m.response_tau)
    # the only lag figure with evidence behind it, and whether the dead time beside it is
    # a measurement or the prior it started from
    self.assertClose(p.effectiveLag, m.actuator_delay + m.response_tau)
    assert p.delayLearned == m.delay_learned
    assert p.delayRailed == m.delay_railed
    self.assertClose(p.steerRatio, m.steer_ratio)
    self.assertClose(p.driverTorqueThreshold, m.driver_torque_threshold)
    assert p.points == m.points
    assert p.modelVersion == MODEL_VERSION
    # the roll compensation evidence: without it a log cannot say whether removing the
    # roll estimate helped the fit or hurt it
    self.assertClose(p.rollCompFraction, m.roll_comp_fraction)
    self.assertClose(p.latAccelTorqueCorr, m.lat_accel_torque_corr)
    self.assertClose(p.latAccelTorqueCorrRaw, m.lat_accel_torque_corr_raw)
    # maxUsefulTorque is carried from the prior, not learned; this is the evidence for
    # whether that ceiling is actually limiting real driving on this car
    self.assertClose(p.saturatedFraction, m.saturated_fraction)


class TestYawSignConvention(ApproxMixin, unittest.TestCase):
  """The two lateral acceleration sources have to agree on which way is positive.

  ``_lat_accel`` prefers the yaw rate and falls back to the steering angle, so a sign
  disagreement between them is not a constant error the fit can absorb: the learner
  silently changes convention whenever deviceMotion goes stale, and while the yaw path
  is live it fits a gain of the wrong sign against a positive-left torque command.
  """

  @staticmethod
  def _learner():
    CP = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC_2022)
    return HondaSteeringLearner(CP, dt=DT, learned=None)

  def _lat_accel(self, learner, *, yaw_rate, steering_angle_deg):
    return learner._lat_accel(HondaSteerSample(
      t=0.0, v_ego=20.0, torque_cmd=0.0,
      steering_angle_deg=steering_angle_deg, steering_rate_deg=0.0,
      driver_torque=0.0, lat_active=True, steering_pressed=False, saturated=False,
      yaw_rate=yaw_rate, roll=0.0, lat_accel_valid=True,
    ))

  def test_both_branches_agree_on_a_right_hand_turn(self):
    """A steady right hand turn, fed through the yaw path and the kinematic fallback."""
    learner = self._learner()
    v_ego, angle = 20.0, -5.0                       # negative steering angle is a right turn
    curvature = math.radians(angle) / (learner.steer_ratio * learner.wheelbase)
    # the calibrated frame is z-down, so the turn shows up as a positive raw yaw rate;
    # hondasteerd flips it before the learner ever sees it
    yaw_rate = YAW_SIGN * -(curvature * v_ego)

    from_yaw = self._lat_accel(learner, yaw_rate=yaw_rate, steering_angle_deg=angle)
    from_angle = self._lat_accel(learner, yaw_rate=None, steering_angle_deg=angle)

    assert from_yaw < 0.0, "a right hand turn must make negative lateral acceleration"
    assert math.copysign(1.0, from_yaw) == math.copysign(1.0, from_angle)
    self.assertClose(from_yaw, from_angle)

  def test_both_branches_agree_on_a_left_hand_turn(self):
    learner = self._learner()
    v_ego, angle = 20.0, 5.0
    curvature = math.radians(angle) / (learner.steer_ratio * learner.wheelbase)
    yaw_rate = YAW_SIGN * -(curvature * v_ego)

    from_yaw = self._lat_accel(learner, yaw_rate=yaw_rate, steering_angle_deg=angle)
    from_angle = self._lat_accel(learner, yaw_rate=None, steering_angle_deg=angle)

    assert from_yaw > 0.0, "a left hand turn must make positive lateral acceleration"
    assert math.copysign(1.0, from_yaw) == math.copysign(1.0, from_angle)
    self.assertClose(from_yaw, from_angle)

  def test_the_identified_gain_matches_the_truth_it_was_driven_with(self):
    """The end to end symptom, on a synthetic car whose gain we know.

    A correctly signed fit recovers the gain it was driven with and never diverges. With
    the flip removed the same drive fits the wrong number and trips ``_check_divergence``
    repeatedly, which is what route 729a2e65b1f6201d did 224 times in 18 minutes.
    """
    learner = self._learner()
    gain, v_ego = 2.0, 20.0
    rng = np.random.default_rng(0)
    cmd = 0.0
    for i in range(20000):
      # a slow random walk, so the command is excited in both directions
      cmd = float(np.clip(cmd + (rng.normal(0.0, 0.25) - cmd) * 0.01, -0.6, 0.6))
      lat_accel = gain * cmd
      yaw_rate = YAW_SIGN * -(lat_accel / v_ego)
      learner.update(HondaSteerSample(
        t=i * DT, v_ego=v_ego, torque_cmd=cmd,
        steering_angle_deg=math.degrees(lat_accel / v_ego ** 2 * learner.steer_ratio * learner.wheelbase),
        steering_rate_deg=0.0, driver_torque=0.0, lat_active=True,
        steering_pressed=False, saturated=False,
        yaw_rate=yaw_rate, roll=0.0, lat_accel_valid=True,
      ))

    model = learner.model()
    assert model.resets == 0, "a correctly signed fit must not diverge"
    self.assertClose(model.lat_accel_factor_v[0], gain, rel=0.05)
