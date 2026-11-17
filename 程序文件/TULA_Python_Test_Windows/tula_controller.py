from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None  # type: ignore[assignment]

from tula_commands import COMMAND_SPECS, ERROR_STATUS_BITS, STATUS_BITS, get_command_spec


AxisLike = Union[int, str]
ValueLike = Union[int, float, str]


class TULAError(Exception):
    """Base exception for TULA controller errors."""


class TULAUnits(str, Enum):
    COUNTS = "counts"
    DEG = "deg"
    RAD = "rad"
    MM = "mm"
    UM = "um"


class TULAStageKind(str, Enum):
    ROTARY = "rotary"
    LINEAR = "linear"


@dataclass(frozen=True)
class TULAStage:
    """Physical actuator description, inspired by Xeryon's Stage objects.

    Current rotary TULA documentation gives 0.005 deg/count. Linear models are
    intentionally configurable because their final encoder resolution is not in
    the current handoff documents yet.
    """

    model: str
    kind: TULAStageKind
    controller_model: str = "TD-201"
    counts_per_degree: Optional[float] = None
    counts_per_mm: Optional[float] = None
    min_counts: Optional[int] = None
    max_counts: Optional[int] = None

    @property
    def default_unit(self) -> TULAUnits:
        if self.kind is TULAStageKind.ROTARY:
            return TULAUnits.DEG if self.counts_per_degree is not None else TULAUnits.COUNTS
        return TULAUnits.MM if self.counts_per_mm is not None else TULAUnits.COUNTS

    @property
    def unit_label(self) -> str:
        if self.default_unit is TULAUnits.DEG:
            return "deg"
        if self.default_unit is TULAUnits.MM:
            return "mm"
        return "counts"

    def to_counts(self, value: ValueLike, unit: TULAUnits | str | None = None) -> int:
        selected_unit = self.default_unit if unit is None else TULAUnits(unit)
        number = float(value)

        if selected_unit is TULAUnits.COUNTS:
            counts = round(number)
        elif selected_unit is TULAUnits.DEG:
            if self.counts_per_degree is None:
                raise TULAError(f"Stage {self.model} has no degree conversion")
            counts = round(number * self.counts_per_degree)
        elif selected_unit is TULAUnits.RAD:
            if self.counts_per_degree is None:
                raise TULAError(f"Stage {self.model} has no radian conversion")
            counts = round(math.degrees(number) * self.counts_per_degree)
        elif selected_unit is TULAUnits.MM:
            if self.counts_per_mm is None:
                raise TULAError(f"Stage {self.model} has no millimeter conversion")
            counts = round(number * self.counts_per_mm)
        elif selected_unit is TULAUnits.UM:
            if self.counts_per_mm is None:
                raise TULAError(f"Stage {self.model} has no micrometer conversion")
            counts = round((number / 1000.0) * self.counts_per_mm)
        else:
            raise TULAError(f"Unsupported unit: {selected_unit}")

        if self.min_counts is not None and counts < self.min_counts:
            raise TULAError(f"{counts} counts is below {self.model} min {self.min_counts}")
        if self.max_counts is not None and counts > self.max_counts:
            raise TULAError(f"{counts} counts is above {self.model} max {self.max_counts}")
        return int(counts)

    def from_counts(self, counts: int, unit: TULAUnits | str | None = None) -> float:
        selected_unit = self.default_unit if unit is None else TULAUnits(unit)

        if selected_unit is TULAUnits.COUNTS:
            return float(counts)
        if selected_unit is TULAUnits.DEG:
            if self.counts_per_degree is None:
                raise TULAError(f"Stage {self.model} has no degree conversion")
            return counts / self.counts_per_degree
        if selected_unit is TULAUnits.RAD:
            if self.counts_per_degree is None:
                raise TULAError(f"Stage {self.model} has no radian conversion")
            return math.radians(counts / self.counts_per_degree)
        if selected_unit is TULAUnits.MM:
            if self.counts_per_mm is None:
                raise TULAError(f"Stage {self.model} has no millimeter conversion")
            return counts / self.counts_per_mm
        if selected_unit is TULAUnits.UM:
            if self.counts_per_mm is None:
                raise TULAError(f"Stage {self.model} has no micrometer conversion")
            return (counts / self.counts_per_mm) * 1000.0
        raise TULAError(f"Unsupported unit: {selected_unit}")


def make_tula_rotary_stage(
    model: str,
    counts_per_degree: float,
    *,
    controller_model: str = "TD-201",
    min_deg: Optional[float] = None,
    max_deg: Optional[float] = None,
) -> TULAStage:
    """Create a rotary TULA stage with optional degree limits."""

    min_counts = None if min_deg is None else round(float(min_deg) * counts_per_degree)
    max_counts = None if max_deg is None else round(float(max_deg) * counts_per_degree)
    return TULAStage(
        model=model,
        kind=TULAStageKind.ROTARY,
        controller_model=controller_model,
        counts_per_degree=float(counts_per_degree),
        min_counts=min_counts,
        max_counts=max_counts,
    )


def make_tula_linear_stage(
    model: str,
    *,
    counts_per_mm: Optional[float] = None,
    controller_model: str = "TD-201",
    min_mm: Optional[float] = None,
    max_mm: Optional[float] = None,
    min_counts: Optional[int] = None,
    max_counts: Optional[int] = None,
) -> TULAStage:
    """Create a linear TULA stage.

    If the linear resolution is still unknown, leave counts_per_mm as None and
    use raw counts for smoke tests. Once the platform resolution is measured,
    pass counts_per_mm to enable mm/um conversion.
    """

    if counts_per_mm is None and (min_mm is not None or max_mm is not None):
        raise TULAError("Linear mm limits require counts_per_mm")

    resolved_min_counts = min_counts
    resolved_max_counts = max_counts
    if counts_per_mm is not None:
        if min_mm is not None:
            resolved_min_counts = round(float(min_mm) * counts_per_mm)
        if max_mm is not None:
            resolved_max_counts = round(float(max_mm) * counts_per_mm)

    return TULAStage(
        model=model,
        kind=TULAStageKind.LINEAR,
        controller_model=controller_model,
        counts_per_mm=None if counts_per_mm is None else float(counts_per_mm),
        min_counts=resolved_min_counts,
        max_counts=resolved_max_counts,
    )


# Present hardware examples. 0.005 deg/count => 200 counts/degree.
TULA_ROTARY_0005_DEG = make_tula_rotary_stage(
    model="TULA_ROTARY_0005_DEG",
    counts_per_degree=200.0,
)
TULA_LINEAR_COUNTS_ONLY = make_tula_linear_stage(
    model="TULA_LINEAR_COUNTS_ONLY",
)


@dataclass
class TULAStatus:
    value: int
    names: List[str]
    frames: List[str]

    @property
    def is_running(self) -> bool:
        return "MOTOR_RUNNING" in self.names

    @property
    def is_homed(self) -> bool:
        return "HOME_MISSING" not in self.names

    @property
    def has_error(self) -> bool:
        return any(name in self.names for name in {"AUTO_TUNING", "ILLEGAL_CMD", "PARAMETER_ERR", "ENCODER_ERR", "POSITION_ERR", "ENCODER_Z_ERR", "OVER_TEMP"})


@dataclass(frozen=True)
class TULASafetyLimits:
    """Runtime movement guardrails for engineering tests and robot policies."""

    require_homed: bool = True
    max_relative_counts: Optional[int] = 2000
    min_counts: Optional[int] = None
    max_counts: Optional[int] = None
    timeout: float = 5.0
    tolerance_counts: int = 3
    stop_on_error: bool = True

    def resolved_for_stage(self, stage: TULAStage) -> "TULASafetyLimits":
        return TULASafetyLimits(
            require_homed=self.require_homed,
            max_relative_counts=self.max_relative_counts,
            min_counts=stage.min_counts if self.min_counts is None else self.min_counts,
            max_counts=stage.max_counts if self.max_counts is None else self.max_counts,
            timeout=self.timeout,
            tolerance_counts=self.tolerance_counts,
            stop_on_error=self.stop_on_error,
        )


class TULAAxis:
    """Axis-level API, following the spirit of Xeryon's Axis class."""

    def __init__(
        self,
        controller: "TULAController",
        axis_id: AxisLike,
        stage: TULAStage = TULA_ROTARY_0005_DEG,
        name: Optional[str] = None,
    ) -> None:
        self.controller = controller
        self.axis_id = controller.axis_str(axis_id)
        self.stage = stage
        self.name = name or f"axis_{self.axis_id}"
        self.was_valid_target_counts = False
        self.last_target_counts: Optional[int] = None
        self.settings: Dict[str, int] = {}

    def get_version(self) -> List[str]:
        return self.controller.get_version(self.axis_id)

    def get_info(self) -> Dict[str, int]:
        info = self.controller.get_info(self.axis_id)
        self.settings.update(info)
        return info

    def get_status(self) -> TULAStatus:
        return self.controller.get_status(self.axis_id)

    def get_position_counts(self) -> int:
        return self.controller.get_position_counts(self.axis_id)

    def get_position(self, unit: TULAUnits | str | None = None) -> float:
        return self.stage.from_counts(self.get_position_counts(), unit)

    def home(self) -> List[str]:
        self.was_valid_target_counts = False
        self.last_target_counts = None
        return self.controller.home(self.axis_id)

    def home_and_wait(self, timeout: float = 10.0) -> None:
        self.controller.home_and_wait(self.axis_id, timeout=timeout)
        self.was_valid_target_counts = False
        self.last_target_counts = self.get_position_counts()

    def stop(self) -> List[str]:
        self.was_valid_target_counts = False
        return self.controller.stop(self.axis_id)

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        self.controller.wait_until_idle(self.axis_id, timeout=timeout)

    def move_absolute(self, value: ValueLike, unit: TULAUnits | str | None = None, wait: bool = True) -> int:
        target_counts = self.stage.to_counts(value, unit)
        self.controller.move_absolute_counts(self.axis_id, target_counts)
        self.was_valid_target_counts = True
        self.last_target_counts = target_counts
        if wait:
            self.wait_until_idle()
        return target_counts

    def move_relative(self, value: ValueLike, unit: TULAUnits | str | None = None, wait: bool = True) -> int:
        delta_counts = self.stage.to_counts(value, unit)
        if self.was_valid_target_counts and self.last_target_counts is not None:
            self.last_target_counts += delta_counts
        else:
            self.last_target_counts = self.get_position_counts() + delta_counts
        self.controller.move_relative_counts(self.axis_id, delta_counts)
        self.was_valid_target_counts = True
        if wait:
            self.wait_until_idle()
        return delta_counts

    def move_absolute_checked(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        tolerance_counts: int = 3,
    ) -> Tuple[bool, int]:
        target_counts = self.move_absolute(value, unit=unit, wait=True)
        actual_counts = self.get_position_counts()
        ok = abs(actual_counts - target_counts) <= tolerance_counts
        self.controller._log(f"Axis {self.axis_id} target={target_counts}, actual={actual_counts}, passed={ok}")
        return ok, actual_counts

    def move_relative_checked(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        tolerance_counts: int = 3,
    ) -> Tuple[bool, int, int]:
        start_counts = self.get_position_counts()
        delta_counts = self.move_relative(value, unit=unit, wait=True)
        actual_counts = self.get_position_counts()
        target_counts = start_counts + delta_counts
        ok = abs(actual_counts - target_counts) <= tolerance_counts
        self.controller._log(f"Axis {self.axis_id} target={target_counts}, actual={actual_counts}, passed={ok}")
        return ok, start_counts, actual_counts

    def safe_move_absolute(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        limits: Optional[TULASafetyLimits] = None,
        wait: bool = True,
    ) -> int:
        target_counts = self.stage.to_counts(value, unit)
        self.controller.safe_move_absolute_counts(self.axis_id, target_counts, limits=limits, wait=wait)
        self.was_valid_target_counts = True
        self.last_target_counts = target_counts
        return target_counts

    def safe_move_relative(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        limits: Optional[TULASafetyLimits] = None,
        wait: bool = True,
    ) -> int:
        delta_counts = self.stage.to_counts(value, unit)
        target_counts = self.controller.safe_move_relative_counts(self.axis_id, delta_counts, limits=limits, wait=wait)
        self.was_valid_target_counts = True
        self.last_target_counts = target_counts
        return target_counts

    def safe_move_absolute_checked(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        limits: Optional[TULASafetyLimits] = None,
    ) -> Tuple[bool, int]:
        target_counts = self.safe_move_absolute(value, unit=unit, limits=limits, wait=True)
        active_limits = (limits or TULASafetyLimits()).resolved_for_stage(self.stage)
        actual_counts = self.get_position_counts()
        ok = abs(actual_counts - target_counts) <= active_limits.tolerance_counts
        self.controller._log(f"Axis {self.axis_id} safe target={target_counts}, actual={actual_counts}, passed={ok}")
        return ok, actual_counts

    def safe_move_relative_checked(
        self,
        value: ValueLike,
        unit: TULAUnits | str | None = None,
        limits: Optional[TULASafetyLimits] = None,
    ) -> Tuple[bool, int, int]:
        start_counts = self.get_position_counts()
        target_counts = self.safe_move_relative(value, unit=unit, limits=limits, wait=True)
        active_limits = (limits or TULASafetyLimits()).resolved_for_stage(self.stage)
        actual_counts = self.get_position_counts()
        ok = abs(actual_counts - target_counts) <= active_limits.tolerance_counts
        self.controller._log(f"Axis {self.axis_id} safe target={target_counts}, actual={actual_counts}, passed={ok}")
        return ok, start_counts, actual_counts

    def set_velocity(self, value: int) -> None:
        self.settings["vel"] = int(value)
        self.controller.command(self.axis_id, "vel", int(value), total_timeout=0.8)

    def set_open_loop_params(self, on_time: int, off_time: int, cycles: int) -> None:
        self.controller.set_open_loop_params(self.axis_id, on_time, off_time, cycles)

    def open_loop_forward_once(self, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0) -> None:
        self.controller.open_loop_forward_once(self.axis_id, on_time, off_time, cycles, wait_time)

    def open_loop_reverse_once(self, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0) -> None:
        self.controller.open_loop_reverse_once(self.axis_id, on_time, off_time, cycles, wait_time)

    def open_loop_bi_once(self, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0) -> None:
        self.controller.open_loop_bi_once(self.axis_id, on_time, off_time, cycles, wait_time)


class TULAController:
    """Serial controller for TULA piezo actuators.

    The current controller protocol is the TD-201 ASCII protocol:
    - 115200 bps, ASCII, 8 data bits, no parity, 1 stop bit.
    - Commands are sent as: >{axis}{command} {optional_param}\r
    - Replies normally start with: <{axis}{command}
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.05, verbose: bool = True) -> None:
        self.port = str(port).strip()
        self.baudrate = baudrate
        self.timeout = timeout
        self.verbose = verbose
        self.ser = None
        self.axes: Dict[str, TULAAxis] = {}

    def __enter__(self) -> "TULAController":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def list_ports() -> List[str]:
        return [device for device, _, _ in TULAController.list_port_infos()]

    @staticmethod
    def list_port_infos() -> List[Tuple[str, str, str]]:
        if serial is None:
            raise TULAError("pyserial 未安装。请先双击 install_deps.bat，或在命令行运行：python -m pip install -r requirements.txt")
        try:
            infos = []
            for port_info in serial.tools.list_ports.comports():
                device = str(getattr(port_info, "device", "") or "").strip()
                description = str(getattr(port_info, "description", "") or "").strip()
                hwid = str(getattr(port_info, "hwid", "") or "").strip()
                if device:
                    infos.append((device, description, hwid))
            return infos
        except Exception as exc:
            raise TULAError(
                "Cannot read serial ports. Check USB-serial driver installation, device power, and whether another program is using the port."
            ) from exc

    @staticmethod
    def normalize_serial_port(port: str) -> str:
        r"""Return a pyserial-compatible port name.

        Windows ports COM10 and above are safest when opened as \\.\COM10.
        Users can still type COM15 in the menu; the SDK converts it internally.
        """

        port_text = str(port).strip()
        if os.name == "nt":
            if port_text.startswith("\\\\.\\"):
                return port_text
            match = re.fullmatch(r"COM(\d+)", port_text, flags=re.IGNORECASE)
            if match and int(match.group(1)) >= 10:
                return "\\\\.\\COM" + match.group(1)
        return port_text

    def add_axis(
        self,
        axis_id: AxisLike,
        stage: TULAStage = TULA_ROTARY_0005_DEG,
        name: Optional[str] = None,
    ) -> TULAAxis:
        axis = TULAAxis(self, axis_id=axis_id, stage=stage, name=name)
        self.axes[axis.axis_id] = axis
        return axis

    def get_axis(self, axis_id: AxisLike) -> TULAAxis:
        axis_text = self.axis_str(axis_id)
        if axis_text not in self.axes:
            return self.add_axis(axis_text)
        return self.axes[axis_text]

    def get_all_axes(self) -> List[TULAAxis]:
        return list(self.axes.values())

    def open(self) -> None:
        if serial is None:
            raise TULAError("pyserial 未安装。请先双击 install_deps.bat，或在命令行运行：python -m pip install -r requirements.txt")
        resolved_port = self.normalize_serial_port(self.port)
        try:
            self.ser = serial.Serial(
                port=resolved_port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout,
            )
        except Exception as exc:
            raise TULAError(
                f"Cannot open serial port {self.port}. Actual port used: {resolved_port}. "
                "Check Device Manager port number, close serial assistant/PC Manager, and confirm the USB-serial driver is installed."
            ) from exc
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        if resolved_port == self.port:
            self._log(f"TULA serial opened: {self.port}")
        else:
            self._log(f"TULA serial opened: {self.port} ({resolved_port})")

    def close(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log("TULA serial closed")

    @property
    def is_connected(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _ensure_open(self) -> None:
        if not self.is_connected:
            raise TULAError("TULA serial port is not open")

    def axis_str(self, axis: AxisLike) -> str:
        if isinstance(axis, int):
            axis_id = axis
        else:
            text = str(axis).strip()
            if not text.isdigit():
                raise TULAError(f"Invalid axis: {axis}")
            axis_id = int(text)
        if axis_id < 1 or axis_id > 32:
            raise TULAError(f"Axis must be in 1..32, got {axis_id}")
        return f"{axis_id:02d}"

    def build_command(self, axis: AxisLike, code: str, *params: Union[int, str]) -> str:
        axis_text = self.axis_str(axis)
        spec = get_command_spec(code)
        if len(params) != spec.params:
            raise TULAError(f"Command {code} expects {spec.params} parameter(s), got {len(params)}")
        payload = f">{axis_text}{spec.code}"
        if params:
            payload += " " + " ".join(str(p) for p in params)
        return payload

    def _extract_frames(self, raw_text: str) -> List[str]:
        text = raw_text.replace("\r", "").replace("\n", "")
        parts = re.split(r"(?=<\d{2}[A-Za-z]+)", text)
        return [part.strip() for part in parts if part.strip()]

    def _read_frames(self, total_timeout: float = 1.0, idle_timeout: float = 0.08) -> List[str]:
        self._ensure_open()
        end_time = time.time() + total_timeout
        last_data_time: Optional[float] = None
        data = b""

        while time.time() < end_time:
            waiting = self.ser.in_waiting
            if waiting > 0:
                data += self.ser.read(waiting)
                last_data_time = time.time()
            else:
                if last_data_time is not None and (time.time() - last_data_time) > idle_timeout:
                    break
                time.sleep(0.01)

        return self._extract_frames(data.decode("ascii", errors="ignore"))

    def _write_raw(self, cmd: str) -> None:
        self._ensure_open()
        full_cmd = cmd.rstrip("\r\n") + "\r"
        self._log(f"\nSEND: {full_cmd!r}")
        self.ser.write(full_cmd.encode("ascii"))

    def query(
        self,
        cmd: str,
        total_timeout: float = 1.0,
        idle_timeout: float = 0.08,
        reset_input: bool = True,
    ) -> List[str]:
        self._ensure_open()
        if reset_input:
            self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self._write_raw(cmd)
        self.ser.flush()

        frames = self._read_frames(total_timeout=total_timeout, idle_timeout=idle_timeout)
        if frames:
            for frame in frames:
                self._log(f"RECV: {frame}")
        else:
            self._log("RECV: <no data>")
        return frames

    def command(
        self,
        axis: AxisLike,
        code: str,
        *params: Union[int, str],
        total_timeout: float = 1.0,
        idle_timeout: float = 0.08,
    ) -> List[str]:
        return self.query(
            self.build_command(axis, code, *params),
            total_timeout=total_timeout,
            idle_timeout=idle_timeout,
        )

    def send_many(self, commands: Sequence[str], total_timeout: float = 1.0, idle_timeout: float = 0.08) -> List[str]:
        self._ensure_open()
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        for cmd in commands:
            self._write_raw(cmd)
        self.ser.flush()

        frames = self._read_frames(total_timeout=total_timeout, idle_timeout=idle_timeout)
        if frames:
            for frame in frames:
                self._log(f"RECV: {frame}")
        else:
            self._log("RECV: <no data>")
        return frames

    def decode_status(self, status_value: int) -> List[str]:
        return [name for bitmask, name in STATUS_BITS.items() if status_value & bitmask]

    def get_status(self, axis: AxisLike) -> TULAStatus:
        axis_text = self.axis_str(axis)
        frames = self.command(axis_text, "al", total_timeout=1.0)
        status_value: Optional[int] = None

        for frame in frames:
            match = re.search(rf"<{axis_text}status\s+(-?\d+)", frame)
            if match:
                status_value = int(match.group(1))
        if status_value is None:
            raise TULAError(f"Could not parse TULA status response for axis {axis_text}: {frames}")
        return TULAStatus(status_value, self.decode_status(status_value), frames)

    def has_error_status(self, status_value: int) -> bool:
        return any(status_value & bitmask for bitmask in ERROR_STATUS_BITS)

    def _has_motion_wait_error(self, status: TULAStatus) -> bool:
        """Allow following error only while this axis is still moving."""
        status_value = status.value
        if status.is_running:
            # TD-201 may report POSITION_ERR (0x0008) before reaching the target.
            # Keep every other error active, and check POSITION_ERR again at idle.
            status_value &= ~0x0008
        return self.has_error_status(status_value)

    def assert_no_error_status(self, axis: AxisLike) -> None:
        status = self.get_status(axis)
        if self.has_error_status(status.value):
            raise TULAError(f"Axis {self.axis_str(axis)} has error status {status.value}: {status.names}")

    def get_position_counts(self, axis: AxisLike) -> int:
        axis_text = self.axis_str(axis)
        frames = self.command(axis_text, "cp", total_timeout=1.0)
        position: Optional[int] = None
        for frame in frames:
            match = re.search(rf"<{axis_text}cp\s+(-?\d+)", frame)
            if match:
                position = int(match.group(1))
        if position is not None:
            return position
        raise TULAError(f"Could not parse TULA position response for axis {axis_text}: {frames}")

    def get_version(self, axis: AxisLike) -> List[str]:
        return self.command(axis, "ver", total_timeout=1.0)

    def get_info(self, axis: AxisLike) -> Dict[str, int]:
        axis_text = self.axis_str(axis)
        frames = self.command(axis_text, "info", total_timeout=1.5, idle_timeout=0.12)
        info: Dict[str, int] = {}
        for frame in frames:
            match = re.search(rf"<{axis_text}([A-Za-z]+)\s+(-?\d+)", frame)
            if match:
                info[match.group(1).lower()] = int(match.group(2))
        return info

    def home(self, axis: AxisLike) -> List[str]:
        return self.command(axis, "hm", total_timeout=0.8)

    def home_and_wait(self, axis: AxisLike, timeout: float = 10.0) -> None:
        axis_text = self.axis_str(axis)
        self._log(f"\n--- Axis {axis_text} home ---")
        self.home(axis_text)

        end_time = time.time() + timeout
        while time.time() < end_time:
            status = self.get_status(axis_text)
            if not status.is_running and status.is_homed:
                if self.has_error_status(status.value):
                    raise TULAError(f"Axis {axis_text} home ended with error status {status.value}: {status.names}")
                self._log(f"Axis {axis_text} homed. Status={status.value}, decoded={status.names}")
                return
            time.sleep(0.1)
        self.stop(axis_text)
        raise TULAError(f"Axis {axis_text} home timeout after {timeout} seconds")

    def wait_until_idle(self, axis: AxisLike, timeout: float = 5.0) -> None:
        axis_text = self.axis_str(axis)
        end_time = time.time() + timeout
        while time.time() < end_time:
            status = self.get_status(axis_text)
            if self._has_motion_wait_error(status):
                self.stop(axis_text)
                raise TULAError(f"Axis {axis_text} has error status {status.value}: {status.names}")
            if not status.is_running:
                return
            time.sleep(0.05)
        self.stop(axis_text)
        raise TULAError(f"Axis {axis_text} did not become idle within {timeout} seconds")

    def validate_safe_target_counts(
        self,
        axis: AxisLike,
        target_counts: int,
        limits: Optional[TULASafetyLimits] = None,
        current_counts: Optional[int] = None,
    ) -> int:
        axis_text = self.axis_str(axis)
        axis_obj = self.get_axis(axis_text)
        active_limits = (limits or TULASafetyLimits()).resolved_for_stage(axis_obj.stage)

        status = self.get_status(axis_text)
        if status.is_running:
            raise TULAError(f"Axis {axis_text} is still running; refusing safe move")
        if self.has_error_status(status.value):
            if active_limits.stop_on_error:
                self.stop(axis_text)
            raise TULAError(f"Axis {axis_text} has error status {status.value}: {status.names}")
        if active_limits.require_homed and not status.is_homed:
            raise TULAError(f"Axis {axis_text} is not homed; run home before safe movement")

        if current_counts is None:
            current_counts = self.get_position_counts(axis_text)
        delta_counts = int(target_counts) - current_counts

        if active_limits.max_relative_counts is not None and abs(delta_counts) > active_limits.max_relative_counts:
            raise TULAError(
                f"Axis {axis_text} requested delta {delta_counts} counts exceeds "
                f"max_relative_counts={active_limits.max_relative_counts}"
            )
        if active_limits.min_counts is not None and target_counts < active_limits.min_counts:
            raise TULAError(f"Axis {axis_text} target {target_counts} is below safe min {active_limits.min_counts}")
        if active_limits.max_counts is not None and target_counts > active_limits.max_counts:
            raise TULAError(f"Axis {axis_text} target {target_counts} is above safe max {active_limits.max_counts}")

        return current_counts

    def safe_move_absolute_counts(
        self,
        axis: AxisLike,
        counts: int,
        limits: Optional[TULASafetyLimits] = None,
        wait: bool = True,
    ) -> int:
        axis_text = self.axis_str(axis)
        target_counts = int(counts)
        active_limits = (limits or TULASafetyLimits()).resolved_for_stage(self.get_axis(axis_text).stage)
        self.validate_safe_target_counts(axis_text, target_counts, limits=active_limits)
        self.move_absolute_counts(axis_text, target_counts)

        if wait:
            self.wait_until_idle(axis_text, timeout=active_limits.timeout)
            actual_counts = self.get_position_counts(axis_text)
            if abs(actual_counts - target_counts) > active_limits.tolerance_counts:
                raise TULAError(
                    f"Axis {axis_text} safe absolute move missed target: "
                    f"target={target_counts}, actual={actual_counts}"
                )

        return target_counts

    def safe_move_relative_counts(
        self,
        axis: AxisLike,
        counts: int,
        limits: Optional[TULASafetyLimits] = None,
        wait: bool = True,
    ) -> int:
        axis_text = self.axis_str(axis)
        delta_counts = int(counts)
        active_limits = (limits or TULASafetyLimits()).resolved_for_stage(self.get_axis(axis_text).stage)
        current_counts = self.get_position_counts(axis_text)
        target_counts = current_counts + delta_counts
        self.validate_safe_target_counts(
            axis_text,
            target_counts,
            limits=active_limits,
            current_counts=current_counts,
        )
        self.move_relative_counts(axis_text, delta_counts)

        if wait:
            self.wait_until_idle(axis_text, timeout=active_limits.timeout)
            actual_counts = self.get_position_counts(axis_text)
            if abs(actual_counts - target_counts) > active_limits.tolerance_counts:
                raise TULAError(
                    f"Axis {axis_text} safe relative move missed target: "
                    f"target={target_counts}, actual={actual_counts}"
                )

        return target_counts

    def move_relative_counts(self, axis: AxisLike, counts: int) -> List[str]:
        return self.command(axis, "mr", int(counts), total_timeout=0.8)

    def move_absolute_counts(self, axis: AxisLike, counts: int) -> List[str]:
        return self.command(axis, "ma", int(counts), total_timeout=0.8)

    def stop(self, axis: AxisLike) -> List[str]:
        return self.command(axis, "st", total_timeout=0.5)

    def set_config(self, axis: AxisLike, code: str, value: int) -> List[str]:
        if code.lower() not in COMMAND_SPECS:
            raise TULAError(f"Unknown TULA config command: {code}")
        return self.command(axis, code, int(value), total_timeout=0.8)

    def set_open_loop_params(self, axis: AxisLike, on_time: int, off_time: int, cycles: int) -> None:
        axis_text = self.axis_str(axis)
        self._log(f"\n--- Axis {axis_text} set open-loop params ---")
        self.command(axis_text, "on", int(on_time), total_timeout=0.6)
        self.command(axis_text, "off", int(off_time), total_timeout=0.6)
        self.command(axis_text, "cy", int(cycles), total_timeout=0.6)

    def open_loop_forward(self, axis: AxisLike) -> None:
        self.command(axis, "fo", total_timeout=0.6)

    def open_loop_reverse(self, axis: AxisLike) -> None:
        self.command(axis, "re", total_timeout=0.6)

    def open_loop_bi(self, axis: AxisLike) -> None:
        self.command(axis, "bi", total_timeout=0.6)

    def open_loop_forward_once(
        self, axis: AxisLike, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0
    ) -> None:
        axis_text = self.axis_str(axis)
        self.set_open_loop_params(axis_text, on_time, off_time, cycles)
        self._log(f"\n--- Axis {axis_text} open-loop forward ---")
        self.open_loop_forward(axis_text)
        time.sleep(wait_time)
        self.stop(axis_text)

    def open_loop_reverse_once(
        self, axis: AxisLike, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0
    ) -> None:
        axis_text = self.axis_str(axis)
        self.set_open_loop_params(axis_text, on_time, off_time, cycles)
        self._log(f"\n--- Axis {axis_text} open-loop reverse ---")
        self.open_loop_reverse(axis_text)
        time.sleep(wait_time)
        self.stop(axis_text)

    def open_loop_bi_once(
        self, axis: AxisLike, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0
    ) -> None:
        axis_text = self.axis_str(axis)
        self.set_open_loop_params(axis_text, on_time, off_time, cycles)
        self._log(f"\n--- Axis {axis_text} open-loop both directions ---")
        self.open_loop_bi(axis_text)
        time.sleep(wait_time)
        self.stop(axis_text)

    def stop_all(self, axes: Iterable[AxisLike] = (1, 2)) -> None:
        self._log("\n--- Stop all TULA axes ---")
        for axis in axes:
            self.stop(axis)

    def home_all(self, axes: Iterable[AxisLike] = (1, 2), timeout: float = 15.0) -> None:
        self._log("\n--- Home all TULA axes ---")
        for axis in axes:
            self.home_and_wait(axis, timeout=timeout)

    def get_positions_counts(self, axes: Iterable[AxisLike] = (1, 2)) -> Dict[str, int]:
        return {f"axis_{self.axis_str(axis)}": self.get_position_counts(axis) for axis in axes}

    def wait_both_until_idle(self, timeout: float = 8.0) -> None:
        end_time = time.time() + timeout
        while time.time() < end_time:
            status_1 = self.get_status(1)
            status_2 = self.get_status(2)
            if self._has_motion_wait_error(status_1):
                self.stop_all()
                raise TULAError(f"Axis 01 has error status {status_1.value}: {status_1.names}")
            if self._has_motion_wait_error(status_2):
                self.stop_all()
                raise TULAError(f"Axis 02 has error status {status_2.value}: {status_2.names}")
            if not status_1.is_running and not status_2.is_running:
                return
            time.sleep(0.05)
        self.stop_all()
        raise TULAError(f"Both axes did not become idle within {timeout} seconds")

    def move_both_relative_counts(self, counts_1: int, counts_2: int) -> List[str]:
        self._log(f"\n--- Dual-axis relative move: axis01={counts_1}, axis02={counts_2} ---")
        return self.send_many(
            [self.build_command(1, "mr", int(counts_1)), self.build_command(2, "mr", int(counts_2))],
            total_timeout=0.8,
        )

    def move_both_absolute_counts(self, counts_1: int, counts_2: int) -> List[str]:
        self._log(f"\n--- Dual-axis absolute move: axis01={counts_1}, axis02={counts_2} ---")
        return self.send_many(
            [self.build_command(1, "ma", int(counts_1)), self.build_command(2, "ma", int(counts_2))],
            total_timeout=0.8,
        )

    def move_both_relative_checked(
        self, counts_1: int, counts_2: int, tolerance_counts: int = 3
    ) -> Tuple[bool, Dict[str, int], Dict[str, int]]:
        start_pos = self.get_positions_counts()
        target_pos = {"axis_01": start_pos["axis_01"] + counts_1, "axis_02": start_pos["axis_02"] + counts_2}
        self.move_both_relative_counts(counts_1, counts_2)
        self.wait_both_until_idle(timeout=8.0)
        end_pos = self.get_positions_counts()
        ok = (
            abs(end_pos["axis_01"] - target_pos["axis_01"]) <= tolerance_counts
            and abs(end_pos["axis_02"] - target_pos["axis_02"]) <= tolerance_counts
        )
        self._log(f"Dual relative target: {target_pos}")
        self._log(f"Dual relative actual: {end_pos}")
        self._log(f"Dual relative passed: {ok}")
        return ok, start_pos, end_pos

    def move_both_absolute_checked(
        self, counts_1: int, counts_2: int, tolerance_counts: int = 3
    ) -> Tuple[bool, Dict[str, int]]:
        target_pos = {"axis_01": counts_1, "axis_02": counts_2}
        self.move_both_absolute_counts(counts_1, counts_2)
        self.wait_both_until_idle(timeout=8.0)
        end_pos = self.get_positions_counts()
        ok = (
            abs(end_pos["axis_01"] - counts_1) <= tolerance_counts
            and abs(end_pos["axis_02"] - counts_2) <= tolerance_counts
        )
        self._log(f"Dual absolute target: {target_pos}")
        self._log(f"Dual absolute actual: {end_pos}")
        self._log(f"Dual absolute passed: {ok}")
        return ok, end_pos

    def open_loop_forward_both(self, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0) -> None:
        self._log("\n--- Dual-axis open-loop forward ---")
        self.set_open_loop_params(1, on_time, off_time, cycles)
        self.set_open_loop_params(2, on_time, off_time, cycles)
        self.send_many([self.build_command(1, "fo"), self.build_command(2, "fo")], total_timeout=0.8)
        time.sleep(wait_time)
        self.stop_all()

    def open_loop_reverse_both(self, on_time: int = 200, off_time: int = 500, cycles: int = 1, wait_time: float = 1.0) -> None:
        self._log("\n--- Dual-axis open-loop reverse ---")
        self.set_open_loop_params(1, on_time, off_time, cycles)
        self.set_open_loop_params(2, on_time, off_time, cycles)
        self.send_many([self.build_command(1, "re"), self.build_command(2, "re")], total_timeout=0.8)
        time.sleep(wait_time)
        self.stop_all()
