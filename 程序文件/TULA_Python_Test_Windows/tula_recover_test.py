from __future__ import annotations

import argparse
import time

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover TULA axes after manual movement or POSITION_ERR")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axes", type=int, nargs="+", default=[1, 2], help="Axis IDs to recover")
    parser.add_argument("--home", action="store_true", help="Run home after stop/status check")
    parser.add_argument("--home-timeout", type=float, default=15.0, help="Maximum home wait time in seconds")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    for axis_id in args.axes:
        controller.add_axis(axis_id, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()

        print("\n--- Stop selected TULA axes ---")
        for axis_id in args.axes:
            controller.stop(axis_id)
        time.sleep(0.2)

        for axis_id in args.axes:
            status = controller.get_status(axis_id)
            position = controller.get_position_counts(axis_id)
            print(f"Axis {axis_id:02d} after stop: status={status.value} {status.names}, position={position} counts")

        if not args.home:
            print("\nRecovery stop/status check done. If POSITION_ERR remains, re-run with --home.")
            return

        print("\n--- Home selected TULA axes ---")
        for axis_id in args.axes:
            controller.home_and_wait(axis_id, timeout=args.home_timeout)
            status = controller.get_status(axis_id)
            position = controller.get_position_counts(axis_id)
            print(f"Axis {axis_id:02d} after home: status={status.value} {status.names}, position={position} counts")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
