from __future__ import annotations

import argparse

from tula_controller import (
    TULAController,
    TULAError,
    TULASafetyLimits,
    TULAUnits,
    make_tula_linear_stage,
)


def print_position(axis, label: str) -> None:
    counts = axis.get_position_counts()
    if axis.stage.counts_per_mm is None:
        print(f"{label}: {counts} counts")
        return

    mm = axis.stage.from_counts(counts, TULAUnits.MM)
    um = axis.stage.from_counts(counts, TULAUnits.UM)
    print(f"{label}: {counts} counts = {mm:.6f} mm = {um:.3f} um")


def build_limits(args, stage) -> TULASafetyLimits:
    max_relative_counts = args.max_relative_counts
    if args.max_relative_mm is not None:
        max_relative_counts = stage.to_counts(args.max_relative_mm, TULAUnits.MM)

    min_counts = args.min_counts
    max_counts = args.max_counts
    if args.min_mm is not None:
        min_counts = stage.to_counts(args.min_mm, TULAUnits.MM)
    if args.max_mm is not None:
        max_counts = stage.to_counts(args.max_mm, TULAUnits.MM)

    return TULASafetyLimits(
        require_homed=True,
        max_relative_counts=max_relative_counts,
        min_counts=min_counts,
        max_counts=max_counts,
        timeout=args.timeout,
        tolerance_counts=args.tolerance_counts,
    )


def resolve_target(args, stage) -> tuple[float, TULAUnits]:
    provided = [
        args.target_counts is not None,
        args.target_mm is not None,
        args.target_um is not None,
    ]
    if sum(provided) != 1:
        raise TULAError("Provide exactly one of --target-counts, --target-mm, or --target-um")

    if args.target_counts is not None:
        return float(args.target_counts), TULAUnits.COUNTS
    if args.target_mm is not None:
        if stage.counts_per_mm is None:
            raise TULAError("--target-mm requires --counts-per-mm")
        return float(args.target_mm), TULAUnits.MM
    if stage.counts_per_mm is None:
        raise TULAError("--target-um requires --counts-per-mm")
    return float(args.target_um), TULAUnits.UM


def format_target(value: float, unit: TULAUnits) -> str:
    if unit is TULAUnits.COUNTS:
        return f"{int(round(value))} counts"
    return f"{value:g} {unit.value}"


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA guarded linear-axis movement test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--axis", type=int, default=1, help="Linear axis id")
    parser.add_argument(
        "--counts-per-mm",
        type=float,
        default=None,
        help="Linear resolution. Leave unset to test in raw counts only.",
    )
    parser.add_argument("--target-counts", type=int, default=None, help="Absolute target in raw counts")
    parser.add_argument("--target-mm", type=float, default=None, help="Absolute target in millimeters")
    parser.add_argument("--target-um", type=float, default=None, help="Absolute target in micrometers")
    parser.add_argument("--max-relative-counts", type=int, default=1000, help="Maximum allowed single move in counts")
    parser.add_argument("--max-relative-mm", type=float, default=None, help="Maximum allowed single move in mm")
    parser.add_argument("--min-counts", type=int, default=None, help="Software lower limit in counts")
    parser.add_argument("--max-counts", type=int, default=None, help="Software upper limit in counts")
    parser.add_argument("--min-mm", type=float, default=None, help="Software lower limit in mm")
    parser.add_argument("--max-mm", type=float, default=None, help="Software upper limit in mm")
    parser.add_argument("--tolerance-counts", type=int, default=3, help="Allowed final position error in counts")
    parser.add_argument("--timeout", type=float, default=5.0, help="Motion timeout per move")
    parser.add_argument("--home", action="store_true", help="Home the axis first if HOME_MISSING is set")
    parser.add_argument("--return-zero", action="store_true", help="Return the axis to zero after the test")
    args = parser.parse_args()

    stage = make_tula_linear_stage(
        "TULA_LINEAR_CONFIGURED" if args.counts_per_mm is not None else "TULA_LINEAR_COUNTS_ONLY",
        counts_per_mm=args.counts_per_mm,
        min_counts=args.min_counts,
        max_counts=args.max_counts,
        min_mm=args.min_mm,
        max_mm=args.max_mm,
    )
    target_value, target_unit = resolve_target(args, stage)
    target_counts = stage.to_counts(target_value, target_unit)
    limits = build_limits(args, stage)

    controller = TULAController(port=args.port)
    axis = controller.add_axis(args.axis, stage=stage)

    try:
        controller.open()
        status = axis.get_status()
        print(f"Axis {axis.axis_id} status before linear test: {status.value} {status.names}")

        if status.has_error:
            axis.stop()
            raise TULAError(
                f"Axis {axis.axis_id} has error status {status.value} {status.names}. "
                "Recover or home it before linear testing."
            )
        if not status.is_homed:
            if args.home:
                axis.home_and_wait()
            else:
                raise TULAError("Axis is not homed. Re-run with --home after checking the mechanism is safe.")

        print_position(axis, f"Axis {axis.axis_id} position before linear move")
        print(
            f"Axis {axis.axis_id} linear target: {format_target(target_value, target_unit)} "
            f"= {target_counts} counts"
        )

        ok, actual_counts = axis.safe_move_absolute_checked(target_value, unit=target_unit, limits=limits)
        print(f"Linear move passed: {ok}")
        print_position(axis, f"Axis {axis.axis_id} position after linear move")

        if args.return_zero:
            ok, actual_counts = axis.safe_move_absolute_checked(0, unit=TULAUnits.COUNTS, limits=limits)
            print(f"Linear return passed: {ok}")
            print_position(axis, f"Axis {axis.axis_id} position after return")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        controller.close()


if __name__ == "__main__":
    main()
