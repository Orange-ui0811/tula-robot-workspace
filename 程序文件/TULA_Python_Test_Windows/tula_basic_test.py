from __future__ import annotations

import argparse

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def test_one_axis(controller: TULAController, axis_id: int, do_home: bool = True) -> None:
    axis = controller.get_axis(axis_id)
    axis_label = axis.axis_id
    print(f"\n========== TULA basic test axis {axis_label} ==========")

    axis.get_version()

    info = axis.get_info()
    print(f"Axis {axis_label} info: {info}")

    status = axis.get_status()
    print(f"Axis {axis_label} status: {status.value} {status.names}")

    if do_home and not status.is_homed:
        axis.home_and_wait()
    elif not status.is_homed:
        print(f"Axis {axis_label} HOME_MISSING is present, but homing was skipped.")

    status = axis.get_status()
    print(f"Axis {axis_label} status after home check: {status.value} {status.names}")

    pos_counts = axis.get_position_counts()
    pos_deg = axis.get_position("deg")
    print(f"Axis {axis_label} position: {pos_counts} counts ({pos_deg:.4f} deg)")

    axis.move_relative_checked(100, unit="counts")
    axis.move_relative_checked(-100, unit="counts")
    axis.move_absolute_checked(1000, unit="counts")
    axis.move_absolute_checked(0, unit="counts")

    print(f"========== TULA basic test axis {axis_label} done ==========")


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA basic closed-loop test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axes", nargs="+", type=int, default=[1, 2], help="Axes to test")
    parser.add_argument("--skip-home", action="store_true", help="Do not run hm even if HOME_MISSING is set")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    for axis_id in args.axes:
        controller.add_axis(axis_id, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()
        for axis_id in args.axes:
            test_one_axis(controller, axis_id, do_home=not args.skip_home)
    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
