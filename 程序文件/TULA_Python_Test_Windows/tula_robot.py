from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Union

from tula_motor_bus import TULAMotor, TULAMotorCalibration, TULAMotorsBus


Numeric = Union[int, float]


@dataclass
class TULARobotConfig:
    """Small standalone robot config that mirrors LeRobot's robot config shape."""

    port: str
    motors: Dict[str, TULAMotor] = field(
        default_factory=lambda: {
            "joint_1": TULAMotor(id=1),
            "joint_2": TULAMotor(id=2),
        }
    )
    calibration: Optional[Dict[str, TULAMotorCalibration]] = None
    disable_torque_on_disconnect: bool = True
    max_relative_target: Optional[Union[float, Dict[str, float]]] = None
    auto_home_on_connect: bool = False


class TULARobot:
    """Standalone LeRobot-shaped robot wrapper for TULA actuators.

    Observation/action keys follow the LeRobot convention used by follower arms:
    `joint_name.pos`.
    """

    name = "tula_robot"

    def __init__(self, config: TULARobotConfig) -> None:
        self.config = config
        self.bus = TULAMotorsBus(
            port=config.port,
            motors=config.motors,
            calibration=config.calibration,
        )

    @property
    def observation_features(self) -> Dict[str, type]:
        return {f"{motor}.pos": float for motor in self.bus.motors}

    @property
    def action_features(self) -> Dict[str, type]:
        return self.observation_features

    @property
    def is_connected(self) -> bool:
        return self.bus.is_connected

    @property
    def is_calibrated(self) -> bool:
        return self.bus.is_calibrated

    def connect(self, calibrate: bool = True) -> None:
        self.bus.connect(handshake=True)
        if calibrate and not self.is_calibrated:
            self.calibrate()
        self.configure()

        if self.config.auto_home_on_connect:
            for motor in self.bus.motors:
                self.bus.write("Home", motor, 1, normalize=False)

    def calibrate(self) -> None:
        self.bus.read_calibration()

    def configure(self) -> None:
        self.bus.configure_motors()

    def get_observation(self) -> Dict[str, Numeric]:
        positions = self.bus.sync_read("Present_Position", normalize=True)
        return {f"{motor}.pos": float(value) for motor, value in positions.items()}

    def send_action(self, action: Dict[str, Numeric]) -> Dict[str, Numeric]:
        goal_pos = {
            key.removesuffix(".pos"): float(value)
            for key, value in action.items()
            if key.endswith(".pos")
        }

        if self.config.max_relative_target is not None:
            goal_pos = self._clip_goal_position(goal_pos)

        self.bus.sync_write("Goal_Position", goal_pos, normalize=True)
        return {f"{motor}.pos": float(value) for motor, value in goal_pos.items()}

    def stop(self) -> None:
        self.bus.disable_torque()

    def disconnect(self) -> None:
        self.bus.disconnect(disable_torque=self.config.disable_torque_on_disconnect)

    def _clip_goal_position(self, goal_pos: Dict[str, float]) -> Dict[str, float]:
        present_pos = self.bus.sync_read("Present_Position", normalize=True)
        clipped = {}

        for motor, target in goal_pos.items():
            present = float(present_pos[motor])
            limit_cfg = self.config.max_relative_target
            limit = limit_cfg[motor] if isinstance(limit_cfg, dict) else limit_cfg

            if limit is None:
                clipped[motor] = target
                continue

            delta = target - present
            if delta > limit:
                clipped[motor] = present + limit
            elif delta < -limit:
                clipped[motor] = present - limit
            else:
                clipped[motor] = target

        return clipped
