

from __future__ import annotations

import os
import re
import sys
from typing import Callable, Iterable

from tula_controller import (
    TULAController,
    TULAError,
    TULASafetyLimits,
    TULAUnits,
    TULA_ROTARY_0005_DEG,
    make_tula_linear_stage,
)


DEFAULT_PORT = "COM4"
ROTARY_COUNTS_PER_DEG = 200.0


def configure_windows_console() -> None:
    """Reduce Chinese mojibake when launched from cmd.exe on Windows."""

    if os.name != "nt":
        return
    os.system("chcp 65001 >nul")
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def normalize_user_port(port: str) -> str:
    port_text = str(port).strip().upper()
    if not port_text:
        raise TULAError("串口号不能为空。")
    if " " in port_text or "," in port_text or "，" in port_text:
        raise TULAError("一次只能输入一个串口号，例如 COM4。不要输入 COM4 COM5。")
    if port_text.startswith("\\\\.\\COM"):
        return port_text
    if re.fullmatch(r"COM\d+", port_text):
        return port_text
    raise TULAError("串口号格式不正确。Windows 下请输入 COM4、COM5、COM15 这种格式。")


def pause() -> None:
    input("\n按回车返回菜单...")


def ask_text(prompt: str, default: str | None = None) -> str:
    suffix = f"（默认 {default}）" if default is not None else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if not value and default is not None:
        return default
    return value


def ask_int(prompt: str, default: int | None = None) -> int:
    while True:
        value = ask_text(prompt, None if default is None else str(default))
        try:
            return int(value)
        except ValueError:
            print("输入无效，请输入整数。")


def ask_float(prompt: str, default: float | None = None) -> float:
    while True:
        value = ask_text(prompt, None if default is None else str(default))
        try:
            return float(value)
        except ValueError:
            print("输入无效，请输入数字。")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_text = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({default_text}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "是"}


def axis_label(axis: int) -> str:
    return f"{axis:02d}"


def format_rotary_position(counts: int) -> str:
    return f"{counts} counts = {counts / ROTARY_COUNTS_PER_DEG:.4f}°"


def print_axis_status(controller: TULAController, axis: int, *, rotary: bool = True) -> None:
    status = controller.get_status(axis)
    counts = controller.get_position_counts(axis)
    if rotary:
        pos_text = format_rotary_position(counts)
    else:
        pos_text = f"{counts} counts"
    print(f"轴 {axis_label(axis)}：状态={status.value} {status.names}，位置={pos_text}")


def with_controller(port: str, axes: Iterable[int], work: Callable[[TULAController], None]) -> None:
    controller = TULAController(port=port)
    for axis in axes:
        controller.add_axis(axis, stage=TULA_ROTARY_0005_DEG)
    try:
        controller.open()
        work(controller)
    finally:
        controller.close()


def set_port(current_port: str) -> str:
    port = normalize_user_port(ask_text("请输入 Windows 串口号，例如 COM4", current_port))
    print(f"本次运行使用串口号：{port}")
    return port


def read_rotary_status(port: str) -> None:
    def work(controller: TULAController) -> None:
        controller.get_version(1)
        print_axis_status(controller, 1)
        controller.get_version(2)
        print_axis_status(controller, 2)

    with_controller(port, (1, 2), work)


def home_one_rotary(port: str) -> None:
    axis = ask_int("请输入要回零的旋转轴号 1/2", 1)

    def work(controller: TULAController) -> None:
        print_axis_status(controller, axis)
        if ask_yes_no(f"确认轴 {axis_label(axis)} 可以安全回零？", False):
            controller.home_and_wait(axis, timeout=20.0)
            print_axis_status(controller, axis)
        else:
            print("已取消。")

    with_controller(port, (axis,), work)


def home_both_rotary(port: str) -> None:
    def work(controller: TULAController) -> None:
        print_axis_status(controller, 1)
        print_axis_status(controller, 2)
        if ask_yes_no("确认两轴都可以安全回零？", False):
            controller.home_all((1, 2), timeout=20.0)
            print_axis_status(controller, 1)
            print_axis_status(controller, 2)
        else:
            print("已取消。")

    with_controller(port, (1, 2), work)


def make_rotary_limits(max_relative_deg: float, tolerance_counts: int, timeout: float) -> TULASafetyLimits:
    return TULASafetyLimits(
        require_homed=True,
        max_relative_counts=round(max_relative_deg * ROTARY_COUNTS_PER_DEG),
        timeout=timeout,
        tolerance_counts=tolerance_counts,
    )


def safe_rotary_absolute(port: str) -> None:
    axis = ask_int("请输入旋转轴号 1/2", 1)
    target_deg = ask_float("请输入目标角度，例如 0.5 表示转到 0.5°", 0.5)
    max_relative_deg = ask_float("请输入本次最大允许角度变化", 2.0)
    tolerance_counts = ask_int("请输入到位容差 counts", 10)
    return_zero = ask_yes_no("测试后是否回到 0°？", True)
    limits = make_rotary_limits(max_relative_deg, tolerance_counts, timeout=8.0)

    def work(controller: TULAController) -> None:
        axis_obj = controller.get_axis(axis)
        print_axis_status(controller, axis)
        ok, actual = axis_obj.safe_move_absolute_checked(target_deg, unit=TULAUnits.DEG, limits=limits)
        print(f"结果：passed={ok}，当前位置={format_rotary_position(actual)}")
        if return_zero:
            ok, actual = axis_obj.safe_move_absolute_checked(0, unit=TULAUnits.DEG, limits=limits)
            print(f"回零结果：passed={ok}，当前位置={format_rotary_position(actual)}")

    with_controller(port, (axis,), work)


def safe_rotary_relative(port: str) -> None:
    axis = ask_int("请输入旋转轴号 1/2", 1)
    delta_deg = ask_float("请输入相对旋转角度，例如 0.5 或 -0.5", 0.5)
    max_relative_deg = ask_float("请输入本次最大允许角度变化", 2.0)
    tolerance_counts = ask_int("请输入到位容差 counts", 10)
    limits = make_rotary_limits(max_relative_deg, tolerance_counts, timeout=8.0)

    def work(controller: TULAController) -> None:
        axis_obj = controller.get_axis(axis)
        print_axis_status(controller, axis)
        ok, start, actual = axis_obj.safe_move_relative_checked(delta_deg, unit=TULAUnits.DEG, limits=limits)
        print(f"结果：passed={ok}，起点={format_rotary_position(start)}，当前位置={format_rotary_position(actual)}")

    with_controller(port, (axis,), work)


def dual_rotary_absolute(port: str) -> None:
    deg_1 = ask_float("请输入轴 01 目标角度", 0.5)
    deg_2 = ask_float("请输入轴 02 目标角度", 0.5)
    max_relative_deg = ask_float("请输入每轴最大允许角度变化", 2.0)
    tolerance_counts = ask_int("请输入到位容差 counts", 10)
    counts_1 = round(deg_1 * ROTARY_COUNTS_PER_DEG)
    counts_2 = round(deg_2 * ROTARY_COUNTS_PER_DEG)
    limits = make_rotary_limits(max_relative_deg, tolerance_counts, timeout=8.0)

    def work(controller: TULAController) -> None:
        print_axis_status(controller, 1)
        print_axis_status(controller, 2)
        controller.validate_safe_target_counts(1, counts_1, limits=limits)
        controller.validate_safe_target_counts(2, counts_2, limits=limits)
        ok, end_pos = controller.move_both_absolute_checked(counts_1, counts_2, tolerance_counts=tolerance_counts)
        print(f"结果：passed={ok}")
        print(f"轴 01：{format_rotary_position(end_pos['axis_01'])}")
        print(f"轴 02：{format_rotary_position(end_pos['axis_02'])}")

    with_controller(port, (1, 2), work)


def segmented_rotary_absolute(port: str) -> None:
    axis = ask_int("请输入旋转轴号 1/2", 1)
    target_deg = ask_float("请输入目标角度，例如 90 或 -90", 10.0)
    step_deg = abs(ask_float("请输入每段最大角度，建议 5 或 10", 5.0))
    tolerance_counts = ask_int("请输入到位容差 counts", 20)
    if step_deg <= 0:
        print("每段角度必须大于 0。")
        return

    def work(controller: TULAController) -> None:
        axis_obj = controller.get_axis(axis)
        current_counts = axis_obj.get_position_counts()
        current_deg = current_counts / ROTARY_COUNTS_PER_DEG
        direction = 1 if target_deg >= current_deg else -1
        print(f"当前位置：{current_deg:.4f}°，目标：{target_deg:.4f}°")
        while (direction > 0 and current_deg < target_deg) or (direction < 0 and current_deg > target_deg):
            next_deg = current_deg + direction * step_deg
            if direction > 0:
                next_deg = min(next_deg, target_deg)
            else:
                next_deg = max(next_deg, target_deg)
            max_relative_deg = abs(next_deg - current_deg) + 0.2
            limits = make_rotary_limits(max_relative_deg, tolerance_counts, timeout=12.0)
            print(f"分段移动：{current_deg:.4f}° -> {next_deg:.4f}°")
            axis_obj.safe_move_absolute_checked(next_deg, unit=TULAUnits.DEG, limits=limits)
            current_counts = axis_obj.get_position_counts()
            current_deg = current_counts / ROTARY_COUNTS_PER_DEG
        print_axis_status(controller, axis)

    with_controller(port, (axis,), work)


def stop_axes(port: str) -> None:
    axes_text = ask_text("请输入要停止的轴号，例如 1、2、1 2，或 all", "all").lower()
    axes = (1, 2) if axes_text == "all" else tuple(int(x) for x in axes_text.split())

    def work(controller: TULAController) -> None:
        controller.stop_all(axes)
        for axis in axes:
            print_axis_status(controller, axis)

    with_controller(port, axes, work)


def linear_stage_from_user() -> tuple[int, object, TULAUnits | None]:
    axis = ask_int("请输入直线轴号", 3)
    use_mm = ask_yes_no("是否已知直线轴 counts_per_mm 并使用 mm 测试？", False)
    if use_mm:
        counts_per_mm = ask_float("请输入 counts_per_mm，例如 50000", 50000.0)
        min_mm = ask_float("请输入软件最小行程 mm", 0.0)
        max_mm = ask_float("请输入软件最大行程 mm", 15.0)
        stage = make_tula_linear_stage(
            "TULA_LINEAR_MM",
            counts_per_mm=counts_per_mm,
            min_mm=min_mm,
            max_mm=max_mm,
        )
        return axis, stage, TULAUnits.MM
    stage = make_tula_linear_stage("TULA_LINEAR_COUNTS_ONLY")
    return axis, stage, TULAUnits.COUNTS


def with_linear_controller(port: str, axis: int, stage, work: Callable[[TULAController], None]) -> None:
    controller = TULAController(port=port)
    controller.add_axis(axis, stage=stage)
    try:
        controller.open()
        work(controller)
    finally:
        controller.close()


def linear_status(port: str) -> None:
    axis, stage, _ = linear_stage_from_user()

    def work(controller: TULAController) -> None:
        print_axis_status(controller, axis, rotary=False)

    with_linear_controller(port, axis, stage, work)


def linear_home(port: str) -> None:
    axis, stage, _ = linear_stage_from_user()

    def work(controller: TULAController) -> None:
        print_axis_status(controller, axis, rotary=False)
        if ask_yes_no(f"确认直线轴 {axis_label(axis)} 可以安全回零？", False):
            controller.home_and_wait(axis, timeout=20.0)
            print_axis_status(controller, axis, rotary=False)
        else:
            print("已取消。")

    with_linear_controller(port, axis, stage, work)


def linear_move(port: str) -> None:
    axis, stage, unit = linear_stage_from_user()
    if unit is TULAUnits.MM:
        target = ask_float("请输入直线轴目标位置 mm", 1.0)
        max_relative = ask_float("请输入本次最大允许移动 mm", 2.0)
        max_relative_counts = stage.to_counts(max_relative, TULAUnits.MM)
    else:
        target = ask_int("请输入直线轴目标位置 counts", 100)
        max_relative_counts = ask_int("请输入本次最大允许移动 counts", 200)
    tolerance_counts = ask_int("请输入到位容差 counts", 10)
    return_zero = ask_yes_no("测试后是否回到 0？", True)
    limits = TULASafetyLimits(
        require_homed=True,
        max_relative_counts=max_relative_counts,
        timeout=8.0,
        tolerance_counts=tolerance_counts,
    )

    def work(controller: TULAController) -> None:
        axis_obj = controller.get_axis(axis)
        status = axis_obj.get_status()
        print_axis_status(controller, axis, rotary=False)
        if not status.is_homed:
            raise TULAError("直线轴尚未回零，请先执行直线轴回零。")
        ok, actual = axis_obj.safe_move_absolute_checked(target, unit=unit, limits=limits)
        print(f"直线轴移动结果：passed={ok}，当前位置={actual} counts")
        if return_zero:
            ok, actual = axis_obj.safe_move_absolute_checked(0, unit=TULAUnits.COUNTS, limits=limits)
            print(f"直线轴回到 0 结果：passed={ok}，当前位置={actual} counts")

    with_linear_controller(port, axis, stage, work)


def print_menu(port: str) -> None:
    print(
        f"""
================ TULA Windows 中文测试菜单 ================
当前串口号：{port}

1. 输入/修改串口号
2. 查看旋转两轴状态（只读，不运动）
3. 单个旋转轴回零
4. 旋转两轴回零
5. 单个旋转轴绝对移动到指定角度
6. 单个旋转轴相对移动指定角度
7. 旋转两轴绝对移动到指定角度
8. 单个旋转轴分段大角度移动
9. 停止指定轴或全部轴
10. 查看直线轴状态
11. 直线轴回零
12. 直线轴安全移动（counts 或 mm）
q. 退出
==========================================================
"""
    )

def main() -> None:
    configure_windows_console()
    port = DEFAULT_PORT
    print("TULA Windows 中文测试程序")
    print("首次使用请先选择 1 输入串口号，例如 COM4。")

    actions = {
        "2": lambda: read_rotary_status(port),
        "3": lambda: home_one_rotary(port),
        "4": lambda: home_both_rotary(port),
        "5": lambda: safe_rotary_absolute(port),
        "6": lambda: safe_rotary_relative(port),
        "7": lambda: dual_rotary_absolute(port),
        "8": lambda: segmented_rotary_absolute(port),
        "9": lambda: stop_axes(port),
        "10": lambda: linear_status(port),
        "11": lambda: linear_home(port),
        "12": lambda: linear_move(port),
    }

    while True:
        print_menu(port)
        choice = input("请选择功能: ").strip().lower()
        if choice == "q":
            print("退出。")
            break
        try:
            if choice == "1":
                port = set_port(port)
            elif choice in actions:
                actions[choice]()
            else:
                print("无效选择。")
        except TULAError as exc:
            print(f"\nTULA 错误：{exc}")
        except KeyboardInterrupt:
            print("\n用户中断。")
        except Exception as exc:
            print(f"\n程序错误：{exc}")
        pause()


if __name__ == "__main__":
    main()
     
