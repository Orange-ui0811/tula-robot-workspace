from dataclasses import dataclass, field
from math import isfinite

from lerobot.robots import RobotConfig


@RobotConfig.register_subclass("tula_robot")
@dataclass(kw_only=True)
class TulaRobotConfig(RobotConfig):
    port: str
    baudrate: int = 115200
    axes: dict[str, int] = field(default_factory=lambda: {"joint_1": 1, "joint_2": 2})
    # No default mechanical range: without verified bounds, motion is disabled.
    action_limits_deg: dict[str, tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.port.strip() or self.baudrate <= 0:
            raise ValueError("A serial port and a positive baud rate are required.")
        if not self.axes or any(not name or "." in name for name in self.axes):
            raise ValueError("Use nonempty joint names without periods.")
        ids = list(self.axes.values())
        if any(type(axis) is not int or not 1 <= axis <= 32 for axis in ids) or len(ids) != len(set(ids)):
            raise ValueError("TD-201 axis addresses must be unique integers in 1..32.")
        if self.action_limits_deg and set(self.action_limits_deg) != set(self.axes):
            raise ValueError("Supply verified degree limits for every configured joint, or none.")
        for joint, (low, high) in self.action_limits_deg.items():
            if not (isfinite(low) and isfinite(high) and low < high):
                raise ValueError(f"{joint}: limits must be finite and strictly increasing.")
