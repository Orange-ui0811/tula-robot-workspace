from __future__ import annotations

import argparse
import time

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA dual-axis test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--skip-home", action="store_true", help="Do not home axes even if HOME_MISSING is set")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    controller.add_axis(1, stage=TULA_ROTARY_0005_DEG, name="left_rotary")
    controller.add_axis(2, stage=TULA_ROTARY_0005_DEG, name="right_rotary")

    try:
        controller.open()

        print("\n========== TULA dual-axis test start ==========")
        controller.stop_all()
        time.sleep(0.3)

        status_1 = controller.get_axis(1).get_status()
        status_2 = controller.get_axis(2).get_status()
        print(f"Axis 01 status: {status_1.value} {status_1.names}")
        print(f"Axis 02 status: {status_2.value} {status_2.names}")

        if not args.skip_home and (not status_1.is_homed or not status_2.is_homed):
            controller.home_all(timeout=15.0)

        positions = controller.get_positions_counts()
        print(f"Initial positions: {positions}")

        print("\n===== Test 1: dual relative move =====")
        controller.move_both_relative_checked(100, 100)
        controller.move_both_relative_checked(-100, -100)

        print("\n===== Test 2: dual absolute move =====")
        controller.move_both_absolute_checked(500, 800)
        controller.move_both_absolute_checked(0, 0)

        print("\n===== Test 3: opposite-direction relative move =====")
        controller.move_both_relative_checked(100, -100)
        controller.move_both_relative_checked(-100, 100)

        print("\n===== Test 4: dual open-loop forward =====")
        print(f"Open-loop positions before: {controller.get_positions_counts()}")
        controller.open_loop_forward_both(on_time=200, off_time=500, cycles=1, wait_time=1.0)
        print(f"Open-loop positions after forward: {controller.get_positions_counts()}")

        print("\n===== Test 5: dual open-loop reverse =====")
        controller.open_loop_reverse_both(on_time=200, off_time=500, cycles=1, wait_time=1.0)
        print(f"Open-loop positions after reverse: {controller.get_positions_counts()}")

        print("\n========== TULA dual-axis test done ==========")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
