from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional, Sequence, Union

from tula_controller import (
    TULAController,
    TULAError,
    TULAStage,
    TULAStatus,
    TULAUnits,
    TULA_ROTARY_0005_DEG,
)


NameOrID = Union[str, int]
Value = Union[int, float, str]


class TULANormMode(str, Enum):
    """LeRobot-compatible normalization modes plus a raw counts mode."""

    RANGE_0_100 = "range_0_100"
    RANGE_M100_100 = "range_m100_100"
    DEGREES = "degrees"
    MILLIMETERS = "millimeters"
    MICROMETERS = "micrometers"
    COUNTS = "counts"


@dataclass
class TULAMotor:
    """LeRobot-style motor descriptor for a TULA axis."""

    id: int
    model: str = "tula_rotary_0005_deg"
    stage: TULAStage = TULA_ROTARY_0005_DEG
    unit: TULAUnits = TULAUnits.COUNTS
    norm_mode: TULANormMode = TULANormMode.DEGREES


@dataclass
class TULAMotorCalibration:
    """Small calibration record compatible in spirit with LeRobot motor calibration."""

    id: int
    drive_mode: int = 0
    homing_offset: int = 0
    range_min: int = -2147000000
    range_max: int = 2147000000


class TULAMotorsBus:
    """LeRobot-shaped bus wrapper for TULA piezo actuators.

    This intentionally mirrors the methods exposed by LeRobot's serial motor
    buses while keeping the implementation independent from LeRobot.  The TULA
    actuator is not a torque servo, so torque calls are mapped to safe no-op /
    stop semantics rather than real current-holding control.
    """

    normalized_data = {
        "Goal_Position",
        "Present_Position",
        "Goal_Position_Degrees",
        "Present_Position_Degrees",
        "Goal_Position_Millimeters",
        "Present_Position_Millimeters",
        "Goal_Position_Micrometers",
        "Present_Position_Micrometers",
    }

    def __init__(
        self,
        port: str,
        motors: Dict[str, TULAMotor],
        calibration: Optional[Dict[str, TULAMotorCalibration]] = None,
        controller: Optional[TULAController] = None,
    ) -> None:
        self.port = port
        self.motors = motors
        self.calibration = calibration if calibration else {}
        self.controller = controller or TULAController(port=port)

    def __len__(self) -> int:
        return len(self.motors)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(port={self.port!r}, motors={self.motors!r})"

    @property
    def is_connected(self) -> bool:
        return self.controller.is_connected

    @property
    def ids(self) -> list[int]:
        return [motor.id for motor in self.motors.values()]

    @property
    def models(self) -> list[str]:
        return [motor.model for motor in self.motors.values()]

    @property
    def is_calibrated(self) -> bool:
        return set(self.calibration) == set(self.motors)

    def _get_motor_name(self, motor: NameOrID) -> str:
        if isinstance(motor, str):
            if motor not in self.motors:
                raise KeyError(f"Unknown TULA motor: {motor}")
            return motor
        for name, cfg in self.motors.items():
            if cfg.id == motor:
                return name
        raise KeyError(f"Unknown TULA motor id: {motor}")

    def _get_motor_names(self, motors: NameOrID | Sequence[NameOrID] | None = None) -> list[str]:
        if motors is None:
            return list(self.motors)
        if isinstance(motors, (str, int)):
            return [self._get_motor_name(motors)]
        return [self._get_motor_name(motor) for motor in motors]

    def _axis(self, motor: NameOrID):
        name = self._get_motor_name(motor)
        return self.controller.get_axis(self.motors[name].id)

    def _ensure_calibration(self, motor: str) -> TULAMotorCalibration:
        cfg = self.motors[motor]
        calibration = self.calibration.get(motor)
        if calibration is not None:
            return calibration

        range_min = cfg.stage.min_counts if cfg.stage.min_counts is not None else -2147000000
        range_max = cfg.stage.max_counts if cfg.stage.max_counts is not None else 2147000000
        calibration = TULAMotorCalibration(id=cfg.id, range_min=range_min, range_max=range_max)
        self.calibration[motor] = calibration
        return calibration

    def _normalize_position(self, motor: str, counts: int) -> float:
        cfg = self.motors[motor]
        calibration = self._ensure_calibration(motor)
        range_min = calibration.range_min
        range_max = calibration.range_max

        if cfg.norm_mode is TULANormMode.COUNTS:
            return float(counts)
        if cfg.norm_mode is TULANormMode.DEGREES:
            return cfg.stage.from_counts(counts, TULAUnits.DEG)
        if cfg.norm_mode is TULANormMode.MILLIMETERS:
            return cfg.stage.from_counts(counts, TULAUnits.MM)
        if cfg.norm_mode is TULANormMode.MICROMETERS:
            return cfg.stage.from_counts(counts, TULAUnits.UM)

        if range_min == range_max:
            raise TULAError(f"Invalid calibration for {motor}: min and max are equal")

        bounded = min(range_max, max(range_min, counts))
        if cfg.norm_mode is TULANormMode.RANGE_0_100:
            value = ((bounded - range_min) / (range_max - range_min)) * 100.0
            return 100.0 - value if calibration.drive_mode else value
        if cfg.norm_mode is TULANormMode.RANGE_M100_100:
            value = (((bounded - range_min) / (range_max - range_min)) * 200.0) - 100.0
            return -value if calibration.drive_mode else value

        raise TULAError(f"Unsupported TULA norm mode: {cfg.norm_mode}")

    def _unnormalize_position(self, motor: str, value: Value) -> int:
        cfg = self.motors[motor]
        calibration = self._ensure_calibration(motor)
        number = float(value)
        range_min = calibration.range_min
        range_max = calibration.range_max

        if cfg.norm_mode is TULANormMode.COUNTS:
            return int(round(number))
        if cfg.norm_mode is TULANormMode.DEGREES:
            return cfg.stage.to_counts(number, TULAUnits.DEG)
        if cfg.norm_mode is TULANormMode.MILLIMETERS:
            return cfg.stage.to_counts(number, TULAUnits.MM)
        if cfg.norm_mode is TULANormMode.MICROMETERS:
            return cfg.stage.to_counts(number, TULAUnits.UM)

        if range_min == range_max:
            raise TULAError(f"Invalid calibration for {motor}: min and max are equal")

        if cfg.norm_mode is TULANormMode.RANGE_0_100:
            bounded = min(100.0, max(0.0, number))
            bounded = 100.0 - bounded if calibration.drive_mode else bounded
            return int((bounded / 100.0) * (range_max - range_min) + range_min)
        if cfg.norm_mode is TULANormMode.RANGE_M100_100:
            bounded = min(100.0, max(-100.0, number))
            bounded = -bounded if calibration.drive_mode else bounded
            return int(((bounded + 100.0) / 200.0) * (range_max - range_min) + range_min)

        raise TULAError(f"Unsupported TULA norm mode: {cfg.norm_mode}")

    def connect(self, handshake: bool = True) -> None:
        if self.is_connected:
            return

        for name, motor in self.motors.items():
            self.controller.add_axis(motor.id, stage=motor.stage, name=name)
        self.controller.open()

        if handshake:
            for name in self.motors:
                axis = self._axis(name)
                axis.get_version()
                axis.get_status()

    def configure_motors(self) -> None:
        """LeRobot hook. Current TD-201 flow has no persistent bus-wide config."""
        for name in self.motors:
            self._axis(name).get_status()

    def disconnect(self, disable_torque: bool = True) -> None:
        if disable_torque and self.is_connected:
            self.disable_torque()
        self.controller.close()

    def read(self, data_name: str, motor: str, *, normalize: bool = True, num_retry: int = 0) -> Value:
        del num_retry
        axis = self._axis(motor)

        if data_name in {"Present_Position", "Position"}:
            counts = axis.get_position_counts()
            return self._normalize_position(motor, counts) if normalize else counts
        if data_name == "Present_Position_Degrees":
            return axis.get_position("deg")
        if data_name == "Present_Position_Millimeters":
            return axis.get_position("mm")
        if data_name == "Present_Position_Micrometers":
            return axis.get_position("um")
        if data_name == "Status":
            return axis.get_status().value
        if data_name == "Status_Names":
            return ",".join(axis.get_status().names)
        if data_name == "Moving":
            return int(axis.get_status().is_running)
        if data_name == "Homed":
            return int(axis.get_status().is_homed)
        if data_name == "Model":
            return self.motors[motor].model
        if data_name == "ID":
            return self.motors[motor].id
        if data_name == "Homing_Offset":
            return self._ensure_calibration(motor).homing_offset
        if data_name == "Min_Position_Limit":
            return self._ensure_calibration(motor).range_min
        if data_name == "Max_Position_Limit":
            return self._ensure_calibration(motor).range_max
        if data_name == "Drive_Mode":
            return self._ensure_calibration(motor).drive_mode

        raise KeyError(f"Unsupported TULA read data_name: {data_name}")

    def write(self, data_name: str, motor: str, value: Value, *, normalize: bool = True, num_retry: int = 0) -> None:
        del num_retry
        axis = self._axis(motor)

        if data_name in {"Goal_Position", "Position"}:
            counts = self._unnormalize_position(motor, value) if normalize else int(value)
            axis.move_absolute(counts, unit="counts", wait=False)
            return
        if data_name == "Goal_Position_Degrees":
            axis.move_absolute(float(value), unit="deg", wait=False)
            return
        if data_name == "Goal_Position_Millimeters":
            axis.move_absolute(float(value), unit="mm", wait=False)
            return
        if data_name == "Goal_Position_Micrometers":
            axis.move_absolute(float(value), unit="um", wait=False)
            return
        if data_name == "Relative_Position":
            axis.move_relative(int(value), unit="counts", wait=True)
            return
        if data_name == "Relative_Position_Degrees":
            axis.move_relative(float(value), unit="deg", wait=True)
            return
        if data_name == "Relative_Position_Millimeters":
            axis.move_relative(float(value), unit="mm", wait=True)
            return
        if data_name == "Relative_Position_Micrometers":
            axis.move_relative(float(value), unit="um", wait=True)
            return
        if data_name == "Velocity":
            axis.set_velocity(int(value))
            return
        if data_name == "Stop":
            axis.stop()
            return
        if data_name == "Home":
            axis.home_and_wait()
            return
        if data_name == "Open_Loop_Forward":
            axis.open_loop_forward_once()
            return
        if data_name == "Open_Loop_Reverse":
            axis.open_loop_reverse_once()
            return
        if data_name == "Open_Loop_Bi":
            axis.open_loop_bi_once()
            return
        if data_name == "Homing_Offset":
            self._ensure_calibration(motor).homing_offset = int(value)
            return
        if data_name == "Min_Position_Limit":
            self._ensure_calibration(motor).range_min = int(value)
            return
        if data_name == "Max_Position_Limit":
            self._ensure_calibration(motor).range_max = int(value)
            return
        if data_name == "Drive_Mode":
            self._ensure_calibration(motor).drive_mode = int(value)
            return

        raise KeyError(f"Unsupported TULA write data_name: {data_name}")

    def sync_read(
        self,
        data_name: str,
        motors: NameOrID | Sequence[NameOrID] | None = None,
        *,
        normalize: bool = True,
        num_retry: int = 0,
    ) -> Dict[str, Value]:
        return {
            name: self.read(data_name, name, normalize=normalize, num_retry=num_retry)
            for name in self._get_motor_names(motors)
        }

    def sync_write(
        self,
        data_name: str,
        values: Value | Dict[str, Value],
        *,
        normalize: bool = True,
        num_retry: int = 0,
    ) -> None:
        del num_retry

        if isinstance(values, (int, float, str)):
            values = {name: values for name in self.motors}

        if data_name in {"Goal_Position", "Position"}:
            commands = []
            for name, value in values.items():
                motor = self.motors[name]
                counts = self._unnormalize_position(name, value) if normalize else int(value)
                commands.append(self.controller.build_command(motor.id, "ma", counts))
            self.controller.send_many(commands, total_timeout=0.8)
            return

        if data_name == "Goal_Position_Degrees":
            commands = []
            for name, value in values.items():
                motor = self.motors[name]
                counts = motor.stage.to_counts(float(value), TULAUnits.DEG)
                commands.append(self.controller.build_command(motor.id, "ma", counts))
            self.controller.send_many(commands, total_timeout=0.8)
            return

        if data_name == "Goal_Position_Millimeters":
            commands = []
            for name, value in values.items():
                motor = self.motors[name]
                counts = motor.stage.to_counts(float(value), TULAUnits.MM)
                commands.append(self.controller.build_command(motor.id, "ma", counts))
            self.controller.send_many(commands, total_timeout=0.8)
            return

        if data_name == "Goal_Position_Micrometers":
            commands = []
            for name, value in values.items():
                motor = self.motors[name]
                counts = motor.stage.to_counts(float(value), TULAUnits.UM)
                commands.append(self.controller.build_command(motor.id, "ma", counts))
            self.controller.send_many(commands, total_timeout=0.8)
            return

        if data_name == "Relative_Position":
            commands = []
            for name, value in values.items():
                motor = self.motors[name]
                counts = int(value)
                commands.append(self.controller.build_command(motor.id, "mr", counts))
            self.controller.send_many(commands, total_timeout=0.8)
            return

        for name, value in values.items():
            self.write(data_name, name, value)

    def enable_torque(self, motors: NameOrID | Sequence[NameOrID] | None = None, num_retry: int = 0) -> None:
        del motors, num_retry
        # Piezo TULA axes do not expose servo-style torque enable in the current protocol.
        return None

    def disable_torque(self, motors: NameOrID | Sequence[NameOrID] | None = None, num_retry: int = 0) -> None:
        del num_retry
        for name in self._get_motor_names(motors):
            self._axis(name).stop()

    def read_calibration(self) -> Dict[str, TULAMotorCalibration]:
        for name in self.motors:
            self._ensure_calibration(name)
        return self.calibration

    def write_calibration(self, calibration_dict: Dict[str, TULAMotorCalibration], cache: bool = True) -> None:
        if cache:
            self.calibration = calibration_dict

    def reset_calibration(self, motors: NameOrID | Sequence[NameOrID] | None = None) -> None:
        for name in self._get_motor_names(motors):
            cfg = self.motors[name]
            range_min = cfg.stage.min_counts if cfg.stage.min_counts is not None else -2147000000
            range_max = cfg.stage.max_counts if cfg.stage.max_counts is not None else 2147000000
            self.calibration[name] = TULAMotorCalibration(id=cfg.id, range_min=range_min, range_max=range_max)

    def set_half_turn_homings(self, motors: NameOrID | Sequence[NameOrID] | None = None) -> Dict[str, int]:
        homings: Dict[str, int] = {}
        for name in self._get_motor_names(motors):
            current = int(self.read("Present_Position", name, normalize=False))
            calibration = self._ensure_calibration(name)
            midpoint = int((calibration.range_min + calibration.range_max) / 2)
            calibration.homing_offset = midpoint - current
            homings[name] = calibration.homing_offset
        return homings

    def record_ranges_of_motion(
        self,
        motors: NameOrID | Sequence[NameOrID] | None = None,
        display_values: bool = True,
    ) -> tuple[Dict[str, int], Dict[str, int]]:
        names = self._get_motor_names(motors)
        start_positions = {name: int(self.read("Present_Position", name, normalize=False)) for name in names}
        mins = start_positions.copy()
        maxes = start_positions.copy()

        input("Move the selected TULA axes through their safe range, then press ENTER to record the final limits.")
        for name in names:
            current = int(self.read("Present_Position", name, normalize=False))
            mins[name] = min(mins[name], current)
            maxes[name] = max(maxes[name], current)
            calibration = self._ensure_calibration(name)
            calibration.range_min = mins[name]
            calibration.range_max = maxes[name]

        if display_values:
            for name in names:
                print(f"{name}: min={mins[name]}, max={maxes[name]}")

        return mins, maxes

    @contextmanager
    def torque_disabled(self, motors: NameOrID | Sequence[NameOrID] | None = None):
        self.disable_torque(motors)
        yield

    def broadcast_ping(self, num_retry: int = 0, raise_on_error: bool = False) -> Dict[int, int] | None:
        del num_retry
        found: Dict[int, int] = {}
        try:
            for name, motor in self.motors.items():
                self._axis(name).get_version()
                found[motor.id] = 201
        except Exception:
            if raise_on_error:
                raise
            return None
        return found

    def status_summary(self, motors: Iterable[NameOrID] | None = None) -> Dict[str, TULAStatus]:
        names = self._get_motor_names(None if motors is None else list(motors))
        return {name: self._axis(name).get_status() for name in names}
