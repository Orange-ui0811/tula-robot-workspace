from __future__ import annotations

import unittest

import tula_controller
from tests.fake_serial import FakeSerial
from tula_controller import make_tula_linear_stage
from tula_motor_bus import TULAMotor, TULAMotorsBus, TULANormMode
from tula_robot import TULARobot, TULARobotConfig


class TULARobotFakeSerialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeSerial()
        self.original_serial_factory = tula_controller.serial.Serial
        tula_controller.serial.Serial = lambda **_: self.fake

    def tearDown(self) -> None:
        tula_controller.serial.Serial = self.original_serial_factory

    def test_observation_and_action_use_lerobot_style_keys(self) -> None:
        robot = TULARobot(TULARobotConfig(port="FAKE"))
        robot.connect()
        self.addCleanup(robot.disconnect)

        sent = robot.send_action({"joint_1.pos": 2.5, "joint_2.pos": 4.0})
        observation = robot.get_observation()

        self.assertEqual(sent, {"joint_1.pos": 2.5, "joint_2.pos": 4.0})
        self.assertEqual(observation, {"joint_1.pos": 2.5, "joint_2.pos": 4.0})

    def test_max_relative_target_clips_robot_action(self) -> None:
        robot = TULARobot(TULARobotConfig(port="FAKE", max_relative_target=1.0))
        robot.connect()
        self.addCleanup(robot.disconnect)

        sent = robot.send_action({"joint_1.pos": 5.0, "joint_2.pos": -5.0})

        self.assertEqual(sent, {"joint_1.pos": 1.0, "joint_2.pos": -1.0})

    def test_linear_motor_bus_normalizes_millimeters(self) -> None:
        stage = make_tula_linear_stage("TULA_LINEAR_TEST", counts_per_mm=1000)
        bus = TULAMotorsBus(
            port="FAKE",
            motors={
                "slide_1": TULAMotor(
                    id=1,
                    model="tula_linear_test",
                    stage=stage,
                    norm_mode=TULANormMode.MILLIMETERS,
                )
            },
        )
        bus.connect()
        self.addCleanup(bus.disconnect)

        bus.write("Goal_Position", "slide_1", 1.25, normalize=True)

        self.assertEqual(bus.read("Present_Position", "slide_1", normalize=False), 1250)
        self.assertEqual(bus.read("Present_Position", "slide_1", normalize=True), 1.25)

    def test_linear_motor_bus_explicit_micrometer_data_names(self) -> None:
        stage = make_tula_linear_stage("TULA_LINEAR_TEST", counts_per_mm=1000)
        bus = TULAMotorsBus(
            port="FAKE",
            motors={"slide_1": TULAMotor(id=1, model="tula_linear_test", stage=stage)},
        )
        bus.connect()
        self.addCleanup(bus.disconnect)

        bus.write("Goal_Position_Micrometers", "slide_1", 2500)

        self.assertEqual(bus.read("Present_Position", "slide_1", normalize=False), 2500)
        self.assertEqual(bus.read("Present_Position_Millimeters", "slide_1"), 2.5)


if __name__ == "__main__":
    unittest.main()
