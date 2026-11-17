from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, List

from tula_controller import (
    TULAController,
    TULAError,
    TULASafetyLimits,
    TULA_ROTARY_0005_DEG,
)


def counts_to_deg(counts: int) -> float:
    return TULA_ROTARY_0005_DEG.from_counts(counts, "deg")


def deg_to_counts(degrees: float) -> int:
    return TULA_ROTARY_0005_DEG.to_counts(degrees, "deg")


def check_or_home_axes(controller: TULAController, home: bool) -> None:
    for axis_id in (1, 2):
        status = controller.get_status(axis_id)
        print(f"Axis {axis_id:02d} status before repeatability test: {status.value} {status.names}")
        if status.has_error:
            controller.stop(axis_id)
            raise TULAError(
                f"Axis {axis_id:02d} has error status {status.value} {status.names}. "
                "Run tula_recover_test.py for this axis before repeatability testing."
            )
        if not status.is_homed:
            if not home:
                raise TULAError(
                    f"Axis {axis_id:02d} is not homed. Re-run with --home after checking the mechanism is safe."
                )
            controller.home_and_wait(axis_id)
            status = controller.get_status(axis_id)
            print(f"Axis {axis_id:02d} status after auto-home: {status.value} {status.names}")
            if status.has_error:
                controller.stop(axis_id)
                raise TULAError(
                    f"Axis {axis_id:02d} auto-home ended with error status {status.value} {status.names}."
                )


def move_pair_checked(
    controller: TULAController,
    cycle: int,
    step_name: str,
    target_axis_01_deg: float,
    target_axis_02_deg: float,
    limits: TULASafetyLimits,
) -> Dict[str, object]:
    target_01_counts = deg_to_counts(target_axis_01_deg)
    target_02_counts = deg_to_counts(target_axis_02_deg)

    start_01_counts = controller.validate_safe_target_counts(1, target_01_counts, limits=limits)
    start_02_counts = controller.validate_safe_target_counts(2, target_02_counts, limits=limits)

    started_at = time.time()
    controller.move_both_absolute_counts(target_01_counts, target_02_counts)
    controller.wait_both_until_idle(timeout=limits.timeout)
    elapsed = time.time() - started_at

    actual = controller.get_positions_counts()
    actual_01_counts = actual["axis_01"]
    actual_02_counts = actual["axis_02"]
    error_01_counts = actual_01_counts - target_01_counts
    error_02_counts = actual_02_counts - target_02_counts
    passed = (
        abs(error_01_counts) <= limits.tolerance_counts
        and abs(error_02_counts) <= limits.tolerance_counts
    )

    print(
        f"Cycle {cycle:02d} {step_name}: "
        f"target=({target_axis_01_deg:.4f}, {target_axis_02_deg:.4f}) deg, "
        f"actual=({counts_to_deg(actual_01_counts):.4f}, {counts_to_deg(actual_02_counts):.4f}) deg, "
        f"error=({error_01_counts}, {error_02_counts}) counts, passed={passed}"
    )

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cycle": cycle,
        "step": step_name,
        "start_axis_01_counts": start_01_counts,
        "start_axis_02_counts": start_02_counts,
        "target_axis_01_counts": target_01_counts,
        "target_axis_02_counts": target_02_counts,
        "actual_axis_01_counts": actual_01_counts,
        "actual_axis_02_counts": actual_02_counts,
        "error_axis_01_counts": error_01_counts,
        "error_axis_02_counts": error_02_counts,
        "actual_axis_01_deg": counts_to_deg(actual_01_counts),
        "actual_axis_02_deg": counts_to_deg(actual_02_counts),
        "duration_sec": round(elapsed, 4),
        "passed": passed,
    }


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV report written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="TULA conservative dual-axis repeatability test")
    parser.add_argument("--port", default="COM4", help="Serial port, for example COM4 or COM5")
    parser.add_argument("--cycles", type=int, default=5, help="Number of repeatability cycles")
    parser.add_argument("--target-deg", type=float, default=1.0, help="Small target angle used by the test")
    parser.add_argument("--max-relative-deg", type=float, default=2.0, help="Maximum allowed single move")
    parser.add_argument("--max-abs-deg", type=float, default=5.0, help="Absolute software limit for this test")
    parser.add_argument("--tolerance-counts", type=int, default=3, help="Allowed final position error in counts")
    parser.add_argument("--timeout", type=float, default=5.0, help="Motion timeout per step")
    parser.add_argument("--settle-sec", type=float, default=0.15, help="Delay between steps")
    parser.add_argument("--home", action="store_true", help="Home axes first if HOME_MISSING is set")
    parser.add_argument("--csv", default=None, help="Optional CSV report path")
    args = parser.parse_args()

    max_relative_counts = deg_to_counts(args.max_relative_deg)
    max_abs_counts = deg_to_counts(args.max_abs_deg)
    limits = TULASafetyLimits(
        require_homed=True,
        max_relative_counts=max_relative_counts,
        min_counts=-max_abs_counts,
        max_counts=max_abs_counts,
        timeout=args.timeout,
        tolerance_counts=args.tolerance_counts,
    )

    controller = TULAController(port=args.port)
    controller.add_axis(1, stage=TULA_ROTARY_0005_DEG)
    controller.add_axis(2, stage=TULA_ROTARY_0005_DEG)
    rows: List[Dict[str, object]] = []

    try:
        controller.open()
        check_or_home_axes(controller, home=args.home)

        print("\n========== TULA repeatability test start ==========")
        print(
            f"cycles={args.cycles}, target={args.target_deg} deg, "
            f"max_relative={args.max_relative_deg} deg, max_abs={args.max_abs_deg} deg"
        )

        for cycle in range(1, args.cycles + 1):
            rows.append(move_pair_checked(controller, cycle, "same_positive", args.target_deg, args.target_deg, limits))
            time.sleep(args.settle_sec)
            rows.append(move_pair_checked(controller, cycle, "return_zero_a", 0.0, 0.0, limits))
            time.sleep(args.settle_sec)
            rows.append(move_pair_checked(controller, cycle, "opposite", args.target_deg, -args.target_deg, limits))
            time.sleep(args.settle_sec)
            rows.append(move_pair_checked(controller, cycle, "return_zero_b", 0.0, 0.0, limits))
            time.sleep(args.settle_sec)

        passed_steps = sum(1 for row in rows if row["passed"])
        print(f"\nRepeatability summary: {passed_steps}/{len(rows)} steps passed")
        if passed_steps != len(rows):
            raise TULAError("Repeatability test failed; inspect the step errors above.")

    except TULAError as exc:
        print(f"TULA error: {exc}")
    except Exception as exc:
        print(f"Unexpected error: {exc}")
    finally:
        if args.csv:
            write_csv(Path(args.csv), rows)
        if controller.is_connected:
            controller.stop_all()
        controller.close()


if __name__ == "__main__":
    main()
