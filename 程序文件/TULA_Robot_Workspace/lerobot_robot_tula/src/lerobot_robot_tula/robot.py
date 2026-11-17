from math import isfinite
from numbers import Real
from threading import RLock

from lerobot.robots import Robot

from .config import TulaRobotConfig
from .controller import Driver, TulaController
from .td201_driver import FATAL_MASK, HOME_MISSING, TD201Driver


class TulaRobot(Robot):
    config_class = TulaRobotConfig
    name = "tula_robot"
    supports_position_hold = False

    def __init__(self, config: TulaRobotConfig, *, driver: Driver | None = None):
        super().__init__(config)
        self.config = config
        self.cameras = {}
        self._axes = dict(config.axes)
        self._limits = {joint: tuple(bounds) for joint, bounds in config.action_limits_deg.items()}
        self._controller = TulaController(
            driver if driver is not None else TD201Driver(config.port, config.baudrate),
            tuple(self._axes.values()),
        )
        self._lock = RLock()

    @property
    def observation_features(self) -> dict[str, type]:
        return {f"{joint}.pos": float for joint in self._axes}

    @property
    def action_features(self) -> dict[str, type]:
        return self.observation_features

    @property
    def is_connected(self) -> bool:
        return self._controller.connected

    @property
    def is_calibrated(self) -> bool:
        # No host calibration implemented; physical readiness is checked separately.
        return True

    @property
    def is_homed(self) -> bool:
        """Last successful status snapshot, not a fresh hardware query."""
        return self._controller.is_homed

    def calibrate(self) -> None:
        """No host calibration; deliberately does not home the device."""

    def configure(self) -> None:
        """Preserve the controller's existing firmware settings."""

    def connect(self, calibrate: bool = True) -> None:
        with self._lock:
            self._controller.connect()
            try:
                if calibrate and not self.is_calibrated:
                    self.calibrate()
                self.configure()
            except BaseException as exc:
                self._controller.close_after_failure(exc)
                raise

    def disconnect(self) -> None:
        """Release software resources; never interpreted as stopping motion."""
        with self._lock:
            self._controller.disconnect()

    def get_observation(self) -> dict[str, float]:
        with self._lock:
            positions = self._controller.read()
            return {f"{joint}.pos": positions[axis] for joint, axis in self._axes.items()}

    def _validate_action(self, action: dict[str, float]) -> tuple[dict[str, float], dict[int, float]]:
        if not isinstance(action, dict) or set(action) != set(self.action_features):
            raise ValueError("Action must contain exactly the configured .pos keys.")
        if not self._limits:
            raise RuntimeError("Motion disabled: set verified action_limits_deg for every joint.")
        accepted = {}
        goals = {}
        for joint, axis in self._axes.items():
            key = f"{joint}.pos"
            value = action[key]
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
                raise ValueError(f"{key} must be a finite real scalar in degrees.")
            low, high = self._limits[joint]
            if not low <= value <= high:
                raise ValueError(f"{key}={value} is outside the configured degree range [{low}, {high}].")
            accepted[key] = goals[axis] = float(value)
        return accepted, goals

    def send_action(self, action: dict[str, float]) -> dict[str, float]:
        with self._lock:
            self._controller.require_connection()
            accepted, goals = self._validate_action(action)
            self._controller.write(goals)
            return accepted

    def move_and_wait(self, action: dict[str, float], *, timeout: float = 30.0,
                      tolerance_counts: int = 15, poll_hz: float = 50.0) -> bool:
        """Explicit legacy-style arrival polling, never used by send_action()."""
        with self._lock:
            self._controller.require_connection()
            _, goals = self._validate_action(action)
            return self._controller.set_angles(goals, timeout, tolerance_counts, poll_hz)

    def home(self, *, timeout_ms: int) -> None:
        """Explicit physical motion. Call only under an approved homing procedure."""
        if type(timeout_ms) is not int or not 0 < timeout_ms <= 2_147_483_647:
            raise ValueError("A positive Windows C long timeout_ms is required.")
        with self._lock:
            controller = self._controller
            controller.require_connection()
            try:
                controller.refresh_status()
                for axis in controller.axes:
                    if controller.status[axis] & FATAL_MASK:
                        raise RuntimeError(f"TD-201 axis {axis} reports a fatal alarm.")
                for axis in controller.axes:
                    controller.driver.home(axis, timeout_ms)
                controller.refresh_status()
                if any(status & (HOME_MISSING | FATAL_MASK) for status in controller.status.values()):
                    raise RuntimeError("TD-201 did not report healthy homed axes.")
            except BaseException as exc:
                controller.close_after_failure(exc)
                raise

    def stop(self) -> None:
        """Explicit software stop attempt, not an emergency-stop guarantee."""
        with self._lock:
            controller = self._controller
            controller.require_connection()
            errors = []
            for axis in controller.axes:
                try:
                    controller.driver.stop(axis)
                except Exception as exc:
                    errors.append(exc)
            if errors:
                error = ExceptionGroup("TD-201 stop failed on one or more axes", errors)
                controller.close_after_failure(error)
                raise error
