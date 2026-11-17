import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lerobot_robot_tula import TulaRobot, TulaRobotConfig
from lerobot_robot_tula.td201_driver import HOME_MISSING, angle_to_counts


class FakeDriver:
    def __init__(self):
        self.events = []
        self.open = False
        self.bound = set()
        self.status = {1: 0, 2: 0}
        self.counts = {1: 200, 2: -450}
        self.fail_at = None
        self.fail_unbind = False

    def _event(self, *event):
        self.events.append(event)
        if event[:2] == self.fail_at:
            raise OSError(f"Injected failure: {event}")

    def connect(self):
        self.open = True
        self._event("connect")

    def bind(self, axis):
        self._event("bind", axis)
        self.bound.add(axis)

    def unbind(self, axis):
        self._event("unbind", axis)
        if self.fail_unbind:
            raise OSError("Injected unbind failure")
        self.bound.remove(axis)

    def close(self):
        self._event("close")
        self.open = False
        self.bound.clear()

    def read_status(self, axis):
        self._event("status", axis)
        return self.status[axis]

    def read_counts(self, axis):
        self._event("read", axis)
        return self.counts[axis]

    def write_degrees(self, axis, value):
        self._event("write", axis, value)
        self.counts[axis] = angle_to_counts(value)

    def home(self, axis, timeout_ms):
        self._event("home", axis, timeout_ms)
        self.status[axis] = 0

    def stop(self, axis):
        self._event("stop", axis)


class RobotTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cfg = TulaRobotConfig(
            port="MOCK", calibration_dir=Path(tmp.name),
            action_limits_deg={"joint_1": (-10.0, 10.0), "joint_2": (-20.0, 20.0)},
        )
        self.driver = FakeDriver()
        self.sleep = self.enterContext(patch("lerobot_robot_tula.controller.time.sleep"))
        self.enterContext(patch("lerobot_robot_tula.td201_driver._load_library", side_effect=AssertionError("Native DLL forbidden")))
        self.robot = TulaRobot(self.cfg, driver=self.driver)
        self.addCleanup(self.robot.disconnect)
        self.action = {"joint_2.pos": -3.5, "joint_1.pos": 2.0}

    def writes(self):
        return [event for event in self.driver.events if event[0] == "write"]

    def test_mock_lifecycle_axis_order_and_no_arrival_wait(self):
        expected = {"joint_1.pos": float, "joint_2.pos": float}
        self.assertEqual(self.robot.observation_features, expected)
        self.assertEqual(self.robot.action_features, expected)
        self.robot.connect()
        self.assertTrue(self.robot.is_connected)
        self.assertEqual(self.robot.get_observation(), {"joint_1.pos": 1.0, "joint_2.pos": -2.25})
        self.driver.events.clear()
        self.assertEqual(self.robot.send_action(self.action), self.action)
        self.assertEqual(self.driver.events, [
            ("status", 1), ("status", 2), ("write", 1, 2.0), ("write", 2, -3.5),
        ])
        self.assertEqual([c.args for c in self.sleep.call_args_list], [(1.5,), (0.001,), (0.001,)])
        self.robot.disconnect()
        self.assertFalse(self.driver.open)
        self.assertFalse(self.robot.is_connected)
        self.assertNotIn("stop", [e[0] for e in self.driver.events])

    def test_calibration_is_not_homing_and_unhomed_action_rejected(self):
        self.driver.status[2] = HOME_MISSING
        self.robot.connect(calibrate=False)
        self.robot.calibrate()
        self.assertTrue(self.robot.is_calibrated)
        self.assertFalse(self.robot.is_homed)
        self.assertNotIn("home", [e[0] for e in self.driver.events])
        with self.assertRaisesRegex(RuntimeError, "not ready"):
            self.robot.send_action(self.action)
        self.assertEqual(self.writes(), [])

    def test_fault_or_loss_of_reference_after_connect(self):
        self.robot.connect()
        for state in (HOME_MISSING, 0x0004):
            with self.subTest(state=state):
                self.driver.status[1] = state
                with self.assertRaisesRegex(RuntimeError, "not ready"):
                    self.robot.send_action(self.action)
        self.assertEqual(self.writes(), [])

    def test_explicit_mock_home(self):
        self.driver.status[2] = HOME_MISSING
        self.robot.connect()
        self.robot.home(timeout_ms=123)
        self.assertTrue(self.robot.is_homed)
        self.assertEqual([e for e in self.driver.events if e[0] == "home"], [
            ("home", 1, 123), ("home", 2, 123),
        ])

    def test_bad_frame_has_no_partial_write(self):
        self.robot.connect()
        for bad in (float("nan"), float("inf"), -float("inf"), 21.0, True, "1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.robot.send_action({**self.action, "joint_2.pos": bad})
        with self.assertRaises(ValueError):
            self.robot.send_action({"joint_1.pos": 1.0})
        with self.assertRaises(ValueError):
            self.robot.send_action({**self.action, "extra.pos": 1.0})
        self.assertEqual(self.writes(), [])
        self.assertTrue(self.robot.is_connected)

    def test_limits_not_configured_disables_motion(self):
        self.cfg.action_limits_deg.clear()
        robot = TulaRobot(self.cfg, driver=self.driver)
        self.addCleanup(robot.disconnect)
        robot.connect()
        with self.assertRaisesRegex(RuntimeError, "Motion disabled"):
            robot.send_action(self.action)
        self.assertEqual(self.writes(), [])

    def test_sdk_range_rejects_entire_frame_before_writes(self):
        self.cfg.action_limits_deg["joint_2"] = (-1e9, 1e9)
        robot = TulaRobot(self.cfg, driver=self.driver)
        self.addCleanup(robot.disconnect)
        robot.connect()
        with self.assertRaisesRegex(ValueError, "SDK count range"):
            robot.send_action({**self.action, "joint_2.pos": 1e8})
        self.assertEqual(self.writes(), [])

    def test_second_axis_bind_failure_rolls_back(self):
        self.driver.fail_at = ("bind", 2)
        with self.assertRaises(OSError):
            self.robot.connect()
        self.assertIn(("unbind", 1), self.driver.events)
        self.assertFalse(self.driver.open)
        self.assertFalse(self.robot.is_connected)

    def test_second_axis_write_failure_preserves_error_and_closes(self):
        self.robot.connect()
        self.driver.fail_at = ("write", 2)
        with self.assertRaises(OSError) as failure:
            self.robot.send_action(self.action)
        self.assertIn("does not stop", failure.exception.__notes__[0])
        self.assertIn(("write", 1, 2.0), self.writes())
        self.assertFalse(self.driver.open)
        self.assertFalse(self.robot.is_connected)

    def test_read_failure_closes(self):
        self.robot.connect()
        self.driver.fail_at = ("read", 2)
        with self.assertRaises(OSError):
            self.robot.get_observation()
        self.assertFalse(self.driver.open)

    def test_unbind_failure_still_closes(self):
        self.robot.connect()
        self.driver.fail_unbind = True
        with self.assertRaises(ExceptionGroup):
            self.robot.disconnect()
        self.assertFalse(self.driver.open)
        self.assertFalse(self.robot.is_connected)

    def test_legacy_arrival_poll_is_explicit(self):
        self.robot.connect()
        self.assertTrue(self.robot.move_and_wait(self.action))
        self.assertIn(("read", 2), self.driver.events)
        self.assertEqual(angle_to_counts(0.0025), 1)
        self.assertEqual(angle_to_counts(-0.0025), -1)
