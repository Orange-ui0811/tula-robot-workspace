from __future__ import annotations

import argparse
import time

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def test_open_loop_axis(controller: TULAController, axis_id: int) -> None:
    axis = controller.get_axis(axis_id)
    axis_label = axis.axis_id
    print(f"\n========== TULA open-loop test axis {axis_label} ==========")

    axis.stop()
    time.sleep(0.3)

    status = axis.get_status()
    print(f"Axis {axis_label} status: {status.value} {status.names}")

    pos_before = axis.get_position_counts()
    print(f"Axis {axis_label} position before open-loop: {pos_before}")

    axis.open_loop_forward_once(on_time=200, off_time=500, cycles=1, wait_time=1.0)
    pos_after_forward = axis.get_position_counts()
    print(f"Axis {axis_label} position after forward: {pos_after_forward}")

    axis.open_loop_reverse_once(on_time=200, off_time=500, cycles=1, wait_time=1.0)
    pos_after_reverse = axis.get_position_counts()
    print(f"Axis {axis_label} position after reverse: {pos_after_reverse}")

    axis.open_loop_bi_once(on_time=200, off_time=500, cycles=1, wait_time=1.0)
    pos_after_bi = axis.get_position_counts()
    print(f"Axis {axis_label} position after bi: {pos_after_bi}")

    print(f"========== TULA open-loop test axis {axis_label} done ==========")


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA open-loop test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axes", nargs="+", type=int, default=[1, 2], help="Axes to test")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    for axis_id in args.axes:
        controller.add_axis(axis_id, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()
        for axis_id in args.axes:
            test_open_loop_axis(controller, axis_id)
    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
