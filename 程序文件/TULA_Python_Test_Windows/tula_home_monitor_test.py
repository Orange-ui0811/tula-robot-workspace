from __future__ import annotations

import argparse
import time

from tula_controller import TULAController, TULAError, TULA_ROTARY_0005_DEG


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor one TULA axis while running home")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axis", type=int, default=1, help="Axis ID to monitor")
    parser.add_argument("--timeout", type=float, default=8.0, help="Maximum monitor time in seconds")
    parser.add_argument("--interval", type=float, default=0.5, help="Status/position sampling interval")
    args = parser.parse_args()

    controller = TULAController(port=args.port)
    controller.add_axis(args.axis, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()
        print(f"\n--- Stop axis {args.axis:02d} before monitored home ---")
        controller.stop(args.axis)
        time.sleep(0.2)

        status = controller.get_status(args.axis)
        position = controller.get_position_counts(args.axis)
        print(f"Before home: status={status.value} {status.names}, position={position} counts")

        print(f"\n--- Start monitored home axis {args.axis:02d} ---")
        controller.home(args.axis)

        started_at = time.time()
        while time.time() - started_at < args.timeout:
            status = controller.get_status(args.axis)
            position = controller.get_position_counts(args.axis)
            elapsed = time.time() - started_at
            print(f"t={elapsed:05.2f}s status={status.value} {status.names}, position={position} counts")

            if not status.is_running:
                if status.is_homed and not status.has_error:
                    print(f"Axis {args.axis:02d} home finished normally.")
                    return
                print(f"Axis {args.axis:02d} home stopped with status={status.value} {status.names}.")
                return

            time.sleep(args.interval)

        print(f"Home monitor timeout after {args.timeout} seconds; sending stop.")
        controller.stop(args.axis)
        status = controller.get_status(args.axis)
        position = controller.get_position_counts(args.axis)
        print(f"After stop: status={status.value} {status.names}, position={position} counts")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
