from __future__ import annotations

import unittest

import tula_controller
from tests.fake_serial import FakeSerial
from tula_controller import (
    TULAController,
    TULAError,
    TULA_LINEAR_COUNTS_ONLY,
    TULASafetyLimits,
    TULAUnits,
    TULA_ROTARY_0005_DEG,
    make_tula_linear_stage,
)


class TULAControllerFakeSerialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeSerial()
        self.original_serial_factory = tula_controller.serial.Serial
        tula_controller.serial.Serial = lambda **_: self.fake

    def tearDown(self) -> None:
        tula_controller.serial.Serial = self.original_serial_factory

    def make_controller(self) -> TULAController:
        controller = TULAController(port="FAKE", verbose=False)
        controller.add_axis(1, stage=TULA_ROTARY_0005_DEG)
        controller.add_axis(2, stage=TULA_ROTARY_0005_DEG)
        controller.open()
        self.addCleanup(controller.close)
        return controller

    def test_build_command_formats_axis_and_parameters(self) -> None:
        controller = TULAController(port="FAKE", verbose=False)

        self.assertEqual(controller.build_command(1, "cp"), ">01cp")
        self.assertEqual(controller.build_command("2", "ma", 100), ">02ma 100")

        with self.assertRaises(TULAError):
            controller.build_command(1, "ma")

    def test_windows_high_com_port_is_normalized(self) -> None:
        original_os_name = tula_controller.os.name
        try:
            tula_controller.os.name = "nt"
            self.assertEqual(TULAController.normalize_serial_port("COM4"), "COM4")
            self.assertEqual(TULAController.normalize_serial_port("COM15"), "\\\\.\\COM15")
            self.assertEqual(TULAController.normalize_serial_port("\\\\.\\COM15"), "\\\\.\\COM15")
        finally:
            tula_controller.os.name = original_os_name

    def test_status_parser_uses_last_status_frame(self) -> None:
        controller = self.make_controller()
        self.fake.script_once(">01al", "<01status 32776 (8008)<01status 0 (0)")

        status = controller.get_status(1)

        self.assertEqual(status.value, 0)
        self.assertEqual(status.names, [])

    def test_position_parser_uses_last_position_frame(self) -> None:
        controller = self.make_controller()
        self.fake.script_once(">01cp", "<01cp 1<01cp 42")

        self.assertEqual(controller.get_position_counts(1), 42)

    def test_motion_and_unit_conversion(self) -> None:
        controller = self.make_controller()
        axis = controller.get_axis(1)

        axis.move_absolute(2.5, unit="deg")

        self.assertEqual(axis.get_position_counts(), 500)
        self.assertEqual(axis.get_position("deg"), 2.5)

    def test_linear_stage_mm_and_um_conversion(self) -> None:
        stage = make_tula_linear_stage(
            "TULA_LINEAR_TEST",
            counts_per_mm=10000,
            min_mm=-2.0,
            max_mm=2.0,
        )

        self.assertEqual(stage.default_unit, TULAUnits.MM)
        self.assertEqual(stage.to_counts(1.5, "mm"), 15000)
        self.assertEqual(stage.to_counts(500, "um"), 5000)
        self.assertEqual(stage.from_counts(2500, "mm"), 0.25)
        self.assertEqual(stage.from_counts(2500, "um"), 250.0)

        with self.assertRaisesRegex(TULAError, "above"):
            stage.to_counts(3.0, "mm")

    def test_counts_only_linear_stage_defaults_to_counts(self) -> None:
        self.assertEqual(TULA_LINEAR_COUNTS_ONLY.default_unit, TULAUnits.COUNTS)
        self.assertEqual(TULA_LINEAR_COUNTS_ONLY.to_counts(123), 123)
        self.assertEqual(TULA_LINEAR_COUNTS_ONLY.from_counts(123), 123.0)

        with self.assertRaisesRegex(TULAError, "no millimeter conversion"):
            TULA_LINEAR_COUNTS_ONLY.to_counts(1.0, "mm")

    def test_safe_move_refuses_unhomed_axis(self) -> None:
        controller = self.make_controller()
        self.fake.statuses["01"] = 0x1000

        with self.assertRaisesRegex(TULAError, "not homed"):
            controller.safe_move_absolute_counts(1, 100)

    def test_safe_move_refuses_large_delta(self) -> None:
        controller = self.make_controller()
        limits = TULASafetyLimits(max_relative_counts=100)

        with self.assertRaisesRegex(TULAError, "exceeds max_relative_counts"):
            controller.safe_move_absolute_counts(1, 200, limits=limits)

    def test_safe_move_absolute_counts(self) -> None:
        controller = self.make_controller()
        limits = TULASafetyLimits(max_relative_counts=100, tolerance_counts=0)

        target = controller.safe_move_absolute_counts(1, 50, limits=limits)

        self.assertEqual(target, 50)
        self.assertEqual(controller.get_position_counts(1), 50)


if __name__ == "__main__":
    unittest.main()
