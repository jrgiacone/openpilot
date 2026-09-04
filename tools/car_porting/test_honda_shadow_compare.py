import math
import sys
import unittest
from pathlib import Path

from opendbc.car.honda.steering_learner import RACK_MOTION_DEADBAND, HondaSteeringModel, HondaSteerSample, _smooth_sign

# tools/car_porting is not a package and is not mirrored under openpilot/, so the sibling
# module is imported by path rather than through the openpilot.* namespace. That also means
# this file is outside tools/test_runner.py's default discovery root: run it explicitly,
# with `python -m unittest` from this directory or
# `tools/test_runner.py tools/car_porting/test_honda_shadow_compare.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from honda_shadow_compare import _Scorer, _ground_truth_lat_accel


def _drive_scorer(scorer: _Scorer, model: HondaSteeringModel, scored_against: HondaSteeringModel,
                   v: float = 22.0, seconds: float = 10.0, dt: float = 0.02) -> None:
  """Feed synthetic steady-state samples whose ground truth is generated *exactly* from
  ``model``'s own forward equation, so a scorer comparing ``model`` against itself must
  read (near) zero error - this is what makes the sanity checks below meaningful."""
  t = 0.0
  while t < seconds:
    u = 0.3 * math.sin(2 * math.pi * t / 9.0)
    rate = math.degrees(0.3 * 2 * math.pi / 9.0 * math.cos(2 * math.pi * t / 9.0))
    scorer.update_rate(rate)
    sign = _smooth_sign(scorer._rate_filt, RACK_MOTION_DEADBAND)
    a = model.lat_accel_factor(v) * (u - model.offset - model.friction * sign)
    s = HondaSteerSample(t=t, v_ego=v, torque_cmd=u, steering_angle_deg=0.0, steering_rate_deg=rate,
                          lat_active=True)
    scorer.score(s, a, model, scored_against)
    t += dt


class TestShadowCompare(unittest.TestCase):
  def test_a_model_scores_itself_near_zero(self):
    """The scoring machinery must recover the truth: a model given its own forward equation's
    output back as ground truth should show ~zero prediction error against itself."""
    truth = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[2.4, 2.4],
                                friction=0.05, offset=0.02, asymmetry=0.0)
    scorer = _Scorer(0.02)
    _drive_scorer(scorer, truth, truth)
    assert scorer.n > 0
    assert scorer.rms("learned") < 1e-6
    assert scorer.rms("prior") < 1e-6


  def test_a_wrong_model_scores_worse_than_the_truth(self):
    """The whole point of the tool: a deliberately wrong model must read worse than the one
    that actually matches what happened."""
    truth = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[2.4, 2.4],
                                friction=0.05, offset=0.02, asymmetry=0.0)
    wrong = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[1.5, 1.5],
                                friction=0.0, offset=0.0, asymmetry=0.0)
    scorer = _Scorer(0.02)
    _drive_scorer(scorer, truth, wrong)
    learned_rms, prior_rms = scorer.rms("learned"), scorer.rms("prior")
    assert learned_rms < 1e-6
    assert prior_rms > 0.1
    assert learned_rms < prior_rms


  def test_bucket_rms_matches_overall_when_one_speed(self):
    """A drive confined to one speed bucket should show the same error there as overall -
    the per-bucket breakdown must not silently drop or duplicate samples."""
    truth = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[2.4, 2.4],
                                friction=0.05, offset=0.02, asymmetry=0.0)
    scorer = _Scorer(0.02)
    _drive_scorer(scorer, truth, truth, v=22.0)
    total_n = scorer.n
    bucket_n = sum(scorer.buckets[i]["n"] for i in scorer.buckets)
    assert bucket_n == total_n


  def test_a_saturated_sample_is_not_scored(self):
    """A command the rack could not actually follow tells us nothing about either model -
    the same reasoning steering_learner.py itself excludes saturated samples for."""
    truth = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[2.4, 2.4])
    scorer = _Scorer(0.02)
    for _ in range(20):
      scorer.update_rate(0.0)
    s = HondaSteerSample(t=0.0, v_ego=22.0, torque_cmd=1.0, steering_angle_deg=0.0,
                         steering_rate_deg=0.0, lat_active=True, saturated=True)
    scorer.score(s, 2.0, truth, truth)
    assert scorer.n == 0


  def test_ground_truth_prefers_yaw_over_kinematic(self):
    a_yaw = _ground_truth_lat_accel(v_ego=20.0, yaw_rate=0.1, roll=0.0, steering_angle_deg=999.0,
                                    steer_ratio=15.0, wheelbase=2.7)
    assert a_yaw == 0.1 * 20.0

    a_kinematic = _ground_truth_lat_accel(v_ego=20.0, yaw_rate=None, roll=0.0, steering_angle_deg=10.0,
                                          steer_ratio=15.0, wheelbase=2.7)
    expected = math.radians(10.0) / (15.0 * 2.7) * 20.0 ** 2
    assert a_kinematic == expected


  def test_ground_truth_removes_road_roll(self):
    flat = _ground_truth_lat_accel(v_ego=20.0, yaw_rate=0.1, roll=0.0, steering_angle_deg=0.0,
                                   steer_ratio=15.0, wheelbase=2.7)
    banked = _ground_truth_lat_accel(v_ego=20.0, yaw_rate=0.1, roll=0.05, steering_angle_deg=0.0,
                                     steer_ratio=15.0, wheelbase=2.7)
    assert banked < flat
