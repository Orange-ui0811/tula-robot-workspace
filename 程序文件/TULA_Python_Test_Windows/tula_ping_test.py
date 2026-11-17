from __future__ import annotations

import argparse

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA read-only serial smoke test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axes", nargs="+", type=int, default=[1, 2], help="Axes to query")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    for axis_id in args.axes:
        controller.add_axis(axis_id, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()
        for axis_id in args.axes:
            axis = controller.get_axis(axis_id)
            print(f"\n========== TULA ping axis {axis.axis_id} ==========")
            axis.get_version()
            status = axis.get_status()
            print(f"Axis {axis.axis_id} status: {status.value} {status.names}")
            position = axis.get_position_counts()
            print(f"Axis {axis.axis_id} position: {position} counts")
    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
