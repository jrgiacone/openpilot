import contextlib
import io
import math
from types import SimpleNamespace
from unittest import mock
import sys
import unittest
from pathlib import Path

from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.steering_learner import RACK_MOTION_DEADBAND, HondaSteeringModel, HondaSteerSample, _smooth_sign

# tools/car_porting is not a package and is not mirrored under openpilot/, so the sibling
# module is imported by path rather than through the openpilot.* namespace. That also means
# this file is outside tools/test_runner.py's default discovery root: run it explicitly,
# with `python -m unittest` from this directory or
# `tools/test_runner.py tools/car_porting/test_honda_shadow_compare.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import honda_shadow_compare
from honda_shadow_compare import DT, _Scorer, _Stage, _ground_truth_lat_accel, compare_route, freeze_table


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


  def test_the_roll_term_follows_the_target(self):
    """Each target must move the scored truth the way its own name says.

    This asserted `banked < flat` unconditionally, which stopped being true when the roll
    compensation was turned off and the test was left failing rather than updated. The
    point it was making is real, so it is made per target instead of globally.
    """
    def truth(roll, target):
      return _ground_truth_lat_accel(v_ego=20.0, yaw_rate=0.1, roll=roll, steering_angle_deg=0.0,
                                     steer_ratio=15.0, wheelbase=2.7, target=target)

    for target, expected in (("raw", 0.0), ("roll", -math.sin(0.05) * 9.81),
                             ("roll_flipped", math.sin(0.05) * 9.81)):
      with self.subTest(target=target):
        assert abs((truth(0.05, target) - truth(0.0, target)) - expected) < 1e-9


class _XYZ:
  """Duck type of ``DeviceMotion.XYZMeasurement``, which is all ``Measurement`` reads."""
  def __init__(self, x=0.0, y=0.0, z=0.0):
    self.x, self.y, self.z = x, y, z
    self.xStd = self.yStd = self.zStd = 0.0


def _synthetic_route(CP, seconds: float, v: float, amp: float, t0: float = 100.0, dt: float = 0.01):
  """A fake route: the messages ``compare_route`` reads, duck typed rather than capnp.

  Only the fields the tool touches exist. The yaw rate is generated from a fixed gain so
  every sample is eligible and the learner's point count grows at a predictable rate,
  which is what the freeze-order assertions below are about.
  """
  t = t0
  yield SimpleNamespace(which=lambda: "carParams", logMonoTime=int(t * 1e9), carParams=CP)
  i = 0
  while t < t0 + seconds:
    u = amp * math.sin(2 * math.pi * (t - t0) / 7.0)
    a = 2.0 * u
    # YAW_SIGN is -1: the calibrated frame is z-down, the command is positive-left
    yaw = SimpleNamespace(angularVelocityDevice=_XYZ(z=-a / v), orientationNED=_XYZ(),
                          velocityDevice=_XYZ(), accelerationDevice=_XYZ(),
                          inputsOK=True, sensorsOK=True)
    yaw.angularVelocityDevice.valid = True
    yaw.orientationNED.valid = True
    yield SimpleNamespace(which=lambda: "deviceMotion", logMonoTime=int(t * 1e9), deviceMotion=yaw)
    yield SimpleNamespace(which=lambda: "carOutput", logMonoTime=int(t * 1e9),
                          carOutput=SimpleNamespace(actuatorsOutput=SimpleNamespace(
                            torque=u, torqueOutputCan=-u * float(CP.lateralParams.torqueV[-1]))))
    yield SimpleNamespace(which=lambda: "carControl", logMonoTime=int(t * 1e9),
                          carControl=SimpleNamespace(latActive=True))
    yield SimpleNamespace(which=lambda: "carState", logMonoTime=int(t * 1e9),
                          carState=SimpleNamespace(vEgo=v, steeringAngleDeg=0.0, steeringRateDeg=0.0,
                                                   steeringTorque=0.0, steeringPressed=False))
    i += 1
    t += dt


class TestFreezeOrder(unittest.TestCase):
  """The methodology trap, pinned.

  ``--split`` freezes the model **once**, during the *first* route, and scores every later
  route against that one frozen model. So the route order on the command line decides both
  when the freeze happens and which samples are held out. An experiment whose effect only
  shows up after some event - a gain reset, say - is invisible if the first route never has
  that event. These tests fail if that ever silently changes.
  """

  def _run(self, routes):
    CP = CarInterface.get_non_essential_params(next(iter(HONDA)))
    data = {name: (secs, v, amp) for name, secs, v, amp in routes}
    stage = _Stage(None, _Scorer(DT), split=0.5)
    learner = None
    with mock.patch.object(honda_shadow_compare, "iter_route",
                           lambda r: _synthetic_route(CP, *data[r])):
      for name in data:
        learner = compare_route(name, learner, [stage], False, "raw")
    return stage, learner

  def test_the_freeze_happens_during_the_first_route(self):
    routes = [("a", 40.0, 22.0, 0.3), ("b", 40.0, 22.0, 0.3)]
    stage, learner = self._run(routes)
    assert stage.frozen is not None
    # frozen part way through route "a", not at the end of the pool
    assert 0 < stage.frozen.points < learner.points / 2 + 1
    assert stage.scorer.n > 0

  def test_swapping_route_order_changes_the_held_out_set(self):
    """Two routes of different length: whichever goes first sets the freeze time, so the
    scored sample count moves. This is why any experiment about reset behaviour must put a
    reset-heavy route first."""
    short = ("a", 20.0, 22.0, 0.3)
    long = ("b", 60.0, 22.0, 0.3)
    first_short, _ = self._run([short, long])
    first_long, _ = self._run([long, short])
    assert first_short.scorer.n != first_long.scorer.n
    # the shorter first route freezes earlier, so more of the pool is held out
    assert first_short.scorer.n > first_long.scorer.n

  def test_a_reset_free_first_route_warns(self):
    """The trap has to be loud. A synthetic route never resets the gain, so freezing on it
    must produce the warning that says the held-out score contains nothing about reset
    behaviour."""
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
      self._run([("a", 40.0, 22.0, 0.3), ("b", 40.0, 22.0, 0.3)])
    assert "zero gain resets" in err.getvalue()
    # only the route the freeze happened on is warned about, once
    assert err.getvalue().count("WARNING") == 1


class TestFreezeTable(unittest.TestCase):
  def test_one_row_per_frozen_stage(self):
    """The convergence table is the readout for "which bucket is still wandering", so it
    must carry every freeze point that produced a model, and skip the ones that did not."""
    frozen = HondaSteeringModel(lat_accel_factor_bp=[8.0, 35.0], lat_accel_factor_v=[2.4, 2.4],
                                points=1234, valid=True)
    stages = [_Stage(1000, _Scorer(DT), frozen=frozen), _Stage(999999, _Scorer(DT))]
    table = freeze_table(stages)
    assert len([ln for ln in table.splitlines() if ln.strip()]) == 2  # header + one row
    assert "1234" in table
