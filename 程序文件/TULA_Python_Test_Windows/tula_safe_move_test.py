from __future__ import annotations

import argparse

from tula_controller import (
    TULAController,
    TULAError,
    TULASafetyLimits,
    TULA_ROTARY_0005_DEG,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA guarded movement test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axis", type=int, default=1, help="Axis to test")
    parser.add_argument("--target-deg", type=float, default=1.0, help="Absolute target in degrees")
    parser.add_argument("--max-relative-deg", type=float, default=2.0, help="Maximum allowed single move in degrees")
    parser.add_argument("--home", action="store_true", help="Home the axis first if HOME_MISSING is set")
    parser.add_argument("--return-zero", action="store_true", help="Return the axis to 0 degrees after the test")
    args = parser.parse_args()

    max_relative_counts = TULA_ROTARY_0005_DEG.to_counts(args.max_relative_deg, "deg")
    limits = TULASafetyLimits(
        require_homed=True,
        max_relative_counts=max_relative_counts,
        timeout=5.0,
        tolerance_counts=3,
    )

    controller = TULAController(port=args.port)
    axis = controller.add_axis(args.axis, stage=TULA_ROTARY_0005_DEG)

    try:
        controller.open()
        status = axis.get_status()
        print(f"Axis {axis.axis_id} status before safe test: {status.value} {status.names}")

        if not status.is_homed:
            if args.home:
                axis.home_and_wait()
            else:
                raise TULAError("Axis is not homed. Re-run with --home after checking the mechanism is safe.")

        before = axis.get_position("deg")
        print(f"Axis {axis.axis_id} position before safe move: {before:.4f} deg")

        ok, actual_counts = axis.safe_move_absolute_checked(args.target_deg, unit="deg", limits=limits)
        print(f"Safe move passed: {ok}, actual={axis.stage.from_counts(actual_counts, 'deg'):.4f} deg")

        if args.return_zero:
            ok, actual_counts = axis.safe_move_absolute_checked(0.0, unit="deg", limits=limits)
            print(f"Safe return passed: {ok}, actual={axis.stage.from_counts(actual_counts, 'deg'):.4f} deg")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
