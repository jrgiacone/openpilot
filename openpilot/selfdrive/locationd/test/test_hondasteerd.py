import json
import pathlib

import pytest

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.steering_learner import MODEL_VERSION, prior_from_car_params
from opendbc.car.honda.values import CAR
from openpilot.selfdrive.locationd.hondasteerd import PARAMS_KEY, fill_msg, parse_cached


def a_model(fingerprint=CAR.HONDA_CIVIC_2022, valid=True):
  m = prior_from_car_params(CarInterface.get_non_essential_params(fingerprint))
  m.valid = valid
  m.points = 5000
  return m


class TestHondaSteerdParamsKey:
  def test_the_cache_key_is_registered(self):
    """Params.get raises on any key missing from params_keys.h.

    An unregistered key is not a silent no-op: it takes the daemon down on its first
    read, before the learner is even constructed, and the only visible symptom is
    process_not_running.
    """
    registry = pathlib.Path(__file__).parents[3] / "common" / "params_keys.h"
    assert f'"{PARAMS_KEY}"' in registry.read_text(), \
      f"{PARAMS_KEY} must be registered in {registry}"


class TestHondaSteerdCache:
  def test_round_trips(self):
    m = a_model()
    assert parse_cached(m.to_json(), m.fingerprint) == m

  def test_rejects_another_car(self):
    """A cache must never seed a car it was not measured on."""
    m = a_model(CAR.HONDA_CIVIC_2022)
    assert parse_cached(m.to_json(), str(CAR.HONDA_PILOT)) is None

  def test_rejects_an_older_model_version(self):
    """A learner whose model has changed shape starts over rather than misreading a cache."""
    d = a_model().to_dict()
    d["version"] = MODEL_VERSION + 1
    assert parse_cached(json.dumps(d), d["fingerprint"]) is None

  @pytest.mark.parametrize("raw", [None, "", "{", b"not json", json.dumps({"version": MODEL_VERSION})])
  def test_survives_a_damaged_cache(self, raw):
    """Whatever is in the key, the daemon must start; the worst case is starting fresh."""
    assert parse_cached(raw, str(CAR.HONDA_CIVIC_2022)) is None

  def test_ignores_an_unconverged_cache(self):
    assert parse_cached(a_model(valid=False).to_json(), str(CAR.HONDA_CIVIC_2022)) is None


class TestHondaSteerdMsg:
  def test_carries_every_learned_field(self):
    m = a_model()
    m.friction, m.offset, m.asymmetry = 0.041, -0.017, 0.008
    m.actuator_delay, m.response_tau = 0.183, 0.072
    p = fill_msg(m, valid=True).hondaSteeringParameters

    assert p.valid and p.carFingerprint == m.fingerprint
    assert list(p.latAccelFactorBP) == pytest.approx(m.lat_accel_factor_bp)
    assert list(p.latAccelFactorV) == pytest.approx(m.lat_accel_factor_v)
    assert p.friction == pytest.approx(m.friction)
    assert p.offset == pytest.approx(m.offset)
    assert p.asymmetry == pytest.approx(m.asymmetry)
    assert p.actuatorDelay == pytest.approx(m.actuator_delay)
    assert p.responseTau == pytest.approx(m.response_tau)
    assert p.steerRatio == pytest.approx(m.steer_ratio)
    assert p.driverTorqueThreshold == pytest.approx(m.driver_torque_threshold)
    assert p.points == m.points
    assert p.modelVersion == MODEL_VERSION
