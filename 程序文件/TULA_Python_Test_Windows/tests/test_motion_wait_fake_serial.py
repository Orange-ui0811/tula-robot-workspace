from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tests.fake_serial import FakeSerial
from tula_commands import ERROR_STATUS_BITS
from tula_controller import TULAController, TULAError, TULASafetyLimits
from tula_windows_menu import safe_rotary_absolute


class MotionWaitFakeSerialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeSerial()
        serial_patch = patch("tula_controller.serial.Serial", return_value=self.fake)
        serial_patch.start()
        self.addCleanup(serial_patch.stop)
        self.controller = TULAController(port="FAKE", verbose=False)
        self.controller.add_axis(1)
        self.controller.add_axis(2)
        self.controller.open()
        self.addCleanup(self.controller.close)

    def script_statuses(self, axis: int, *values: int) -> None:
        for value in values:
            self.fake.script_once(
                f">{axis:02d}al", f"<{axis:02d}status {value} ({value:x})"
            )

    def test_single_wait_allows_position_error_only_while_running(self) -> None:
        self.script_statuses(1, 0x8008, 0x8000, 0)

        self.controller.wait_until_idle(1)

        self.assertEqual(self.fake.writes, [">01al", ">01al", ">01al"])

    def test_single_wait_stops_for_position_error_after_motion(self) -> None:
        self.script_statuses(1, 0x8008, 0x0008)

        with self.assertRaisesRegex(TULAError, "error status 8:"):
            self.controller.wait_until_idle(1)

        self.assertEqual(self.fake.writes, [">01al", ">01al", ">01st"])

    def test_single_wait_stops_for_other_errors_even_with_position_error(self) -> None:
        for bit in ERROR_STATUS_BITS:
            if bit == 0x0008:
                continue
            with self.subTest(error_bit=hex(bit)):
                self.fake.writes.clear()
                self.fake.statuses["01"] = 0x8008 | bit

                with self.assertRaisesRegex(TULAError, "has error status"):
                    self.controller.wait_until_idle(1)

                self.assertEqual(self.fake.writes, [">01al", ">01st"])

    def test_single_wait_still_checks_errors_when_already_idle(self) -> None:
        for bit in ERROR_STATUS_BITS:
            with self.subTest(error_bit=hex(bit)):
                self.fake.writes.clear()
                self.fake.statuses["01"] = bit

                with self.assertRaisesRegex(TULAError, "has error status"):
                    self.controller.wait_until_idle(1)

                self.assertEqual(self.fake.writes, [">01al", ">01st"])

    def test_single_wait_times_out_if_running_position_error_never_clears(self) -> None:
        self.fake.statuses["01"] = 0x8008

        with self.assertRaisesRegex(TULAError, "did not become idle within"):
            self.controller.wait_until_idle(1, timeout=0.2)

        self.assertIn(">01al", self.fake.writes)
        self.assertEqual(self.fake.writes[-1], ">01st")

    def test_dual_wait_allows_each_axis_to_finish_separately(self) -> None:
        self.script_statuses(1, 0x8008, 0, 0)
        self.script_statuses(2, 0x8008, 0x8008, 0)

        self.controller.wait_both_until_idle()

        self.assertEqual(self.fake.writes, [">01al", ">02al"] * 3)

    def test_running_axis_does_not_hide_stopped_axis_position_error(self) -> None:
        for stopped_axis in (1, 2):
            with self.subTest(stopped_axis=stopped_axis):
                self.fake.writes.clear()
                self.fake.statuses["01"] = 0x8008
                self.fake.statuses["02"] = 0x8008
                self.fake.statuses[f"{stopped_axis:02d}"] = 0x0008

                with self.assertRaisesRegex(
                    TULAError, f"Axis {stopped_axis:02d} has error status 8:"
                ):
                    self.controller.wait_both_until_idle()

                self.assertEqual(self.fake.writes[-2:], [">01st", ">02st"])

    def test_dual_wait_stops_both_axes_for_any_other_error(self) -> None:
        for axis in (1, 2):
            for bit in ERROR_STATUS_BITS:
                if bit == 0x0008:
                    continue
                with self.subTest(axis=axis, error_bit=hex(bit)):
                    self.fake.writes.clear()
                    self.fake.statuses["01"] = 0x8008
                    self.fake.statuses["02"] = 0x8008
                    self.fake.statuses[f"{axis:02d}"] |= bit

                    with self.assertRaisesRegex(
                        TULAError, f"Axis {axis:02d} has error status"
                    ):
                        self.controller.wait_both_until_idle()

                    self.assertEqual(self.fake.writes[-2:], [">01st", ">02st"])

    def test_dual_wait_times_out_if_position_error_never_clears(self) -> None:
        self.fake.statuses["01"] = 0x8008
        self.fake.statuses["02"] = 0x8008

        with self.assertRaisesRegex(TULAError, "did not become idle within"):
            self.controller.wait_both_until_idle(timeout=0.2)

        self.assertEqual(self.fake.writes[-2:], [">01st", ">02st"])

    def test_safe_move_still_refuses_position_error_before_motion(self) -> None:
        self.fake.statuses["01"] = 0x0008

        with self.assertRaisesRegex(TULAError, "error status 8:"):
            self.controller.safe_move_absolute_counts(1, 100)

        self.assertEqual(self.fake.writes, [">01al", ">01st"])

    def test_safe_absolute_checked_reaches_30_degrees_after_transient_error(self) -> None:
        self.script_statuses(1, 0, 0x8008, 0)
        limits = TULASafetyLimits(max_relative_counts=7000, tolerance_counts=10)

        passed, actual = self.controller.get_axis(1).safe_move_absolute_checked(
            30, unit="deg", limits=limits
        )

        self.assertTrue(passed)
        self.assertEqual(actual, 6000)
        self.assertIn(">01ma 6000", self.fake.writes)
        self.assertNotIn(">01st", self.fake.writes)

    def test_safe_absolute_final_position_tolerance_is_not_relaxed(self) -> None:
        for actual, accepted in ((6010, True), (6011, False)):
            with self.subTest(actual=actual):
                self.fake.writes.clear()
                self.fake.scripted.clear()
                self.fake.positions["01"] = 0
                self.script_statuses(1, 0, 0x8008, 0)
                self.fake.script_once(">01cp", "<01cp 0")
                self.fake.script_once(">01cp", f"<01cp {actual}")
                limits = TULASafetyLimits(max_relative_counts=7000, tolerance_counts=10)

                if accepted:
                    target = self.controller.safe_move_absolute_counts(1, 6000, limits=limits)
                    self.assertEqual(target, 6000)
                else:
                    with self.assertRaisesRegex(
                        TULAError, "missed target: target=6000, actual=6011"
                    ):
                        self.controller.safe_move_absolute_counts(1, 6000, limits=limits)

    def test_safe_relative_checked_also_allows_transient_position_error(self) -> None:
        self.fake.positions["01"] = 100
        self.script_statuses(1, 0, 0x8008, 0)
        limits = TULASafetyLimits(max_relative_counts=200, tolerance_counts=10)

        passed, start, actual = self.controller.get_axis(1).safe_move_relative_checked(
            0.5, unit="deg", limits=limits
        )

        self.assertTrue(passed)
        self.assertEqual((start, actual), (100, 200))
        self.assertNotIn(">01st", self.fake.writes)

    def test_menu_5_completes_original_inputs_after_transient_error(self) -> None:
        # The menu first displays status, then safe movement performs its own precheck.
        self.script_statuses(1, 0, 0, 0x8008, 0)
        output = io.StringIO()
        with patch("builtins.input", side_effect=["1", "30", "35", "10", "n"]):
            with redirect_stdout(output):
                safe_rotary_absolute("FAKE")

        self.assertIn("passed=True", output.getvalue())
        self.assertIn("6000 counts = 30.0000°", output.getvalue())
        self.assertEqual(self.fake.writes.count(">01ma 6000"), 1)
        self.assertNotIn(">01ma 0", self.fake.writes)
        self.assertNotIn(">01st", self.fake.writes)
        self.assertFalse(self.fake.is_open)


if __name__ == "__main__":
    unittest.main()
