"""Ordered multi-axis operations, independent of LeRobot and the native loader."""
import math
import time
from typing import Protocol

from .td201_driver import FATAL_MASK, HOME_MISSING, MAX_TARGET_COUNTS, PULSES_PER_DEGREE, angle_to_counts


class Driver(Protocol):
    def connect(self) -> None: ...
    def bind(self, axis_id: int) -> None: ...
    def unbind(self, axis_id: int) -> None: ...
    def close(self) -> None: ...
    def read_counts(self, axis_id: int) -> int: ...
    def read_status(self, axis_id: int) -> int: ...
    def write_degrees(self, axis_id: int, degrees: float) -> None: ...
    def home(self, axis_id: int, timeout_ms: int) -> None: ...
    def stop(self, axis_id: int) -> None: ...


class TulaController:
    def __init__(self, driver: Driver, axes: tuple[int, ...]):
        self.driver, self.axes = driver, axes
        self.connected = False
        self.status: dict[int, int] = {}
        self._bound: list[int] = []

    def connect(self) -> None:
        if self.connected:
            raise RuntimeError("Tula is already connected.")
        try:
            self.driver.connect()
            time.sleep(1.5)  # Keep the original device startup delay.
            for axis in self.axes:
                self.driver.bind(axis)
                self._bound.append(axis)
            self.refresh_status()
            self.connected = True
        except BaseException as exc:
            self.close_after_failure(exc)
            raise

    def disconnect(self) -> None:
        errors = []
        try:
            for axis in reversed(self._bound):
                try:
                    self.driver.unbind(axis)
                except Exception as exc:
                    errors.append(exc)
        finally:
            try:
                self.driver.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                self.connected = False
                self._bound.clear()
                self.status.clear()
        if errors:
            raise ExceptionGroup("Tula resource cleanup failed", errors)

    def close_after_failure(self, exc: BaseException) -> None:
        exc.add_note("Closing the serial connection does not stop an axis; a command may already have been sent.")
        try:
            self.disconnect()
        except Exception as cleanup:
            exc.add_note(f"Additional cleanup failure: {cleanup!r}")

    def refresh_status(self) -> None:
        self.status = {axis: self.driver.read_status(axis) for axis in self.axes}

    @property
    def is_homed(self) -> bool:
        return self.connected and all(
            axis in self.status and not self.status[axis] & HOME_MISSING for axis in self.axes
        )

    def read(self) -> dict[int, float]:
        self.require_connection()
        try:
            return {axis: self.driver.read_counts(axis) / PULSES_PER_DEGREE for axis in self.axes}
        except BaseException as exc:
            self.close_after_failure(exc)
            raise

    def require_connection(self) -> None:
        if not self.connected:
            raise ConnectionError("Tula is not connected.")

    def write(self, goals: dict[int, float]) -> None:
        self.require_connection()
        if not goals or any(axis not in self.axes or not math.isfinite(v) for axis, v in goals.items()):
            raise ValueError("Expected finite goals for configured axes.")
        if any(abs(value * PULSES_PER_DEGREE) > MAX_TARGET_COUNTS for value in goals.values()):
            raise ValueError("Goal exceeds the TD-201 SDK count range.")
        try:
            self.refresh_status()
        except BaseException as exc:
            self.close_after_failure(exc)
            raise
        for axis, status in self.status.items():
            if status & (HOME_MISSING | FATAL_MASK):
                raise RuntimeError(f"TD-201 axis {axis} is not ready for motion (status=0x{status:04x}).")
        try:
            for axis in self.axes:
                if axis in goals:
                    self.driver.write_degrees(axis, goals[axis])
                    time.sleep(0.001)  # Preserve the original inter-command delay.
        except BaseException as exc:
            self.close_after_failure(exc)
            raise

    def set_angles(self, goals: dict[int, float], timeout: float = 30.0,
                   tolerance_counts: int = 15, poll_hz: float = 50.0) -> bool:
        """Legacy arrival polling, separate from the cycle control path."""
        if not (math.isfinite(timeout) and timeout > 0 and math.isfinite(poll_hz)
                and poll_hz > 0 and tolerance_counts >= 0):
            raise ValueError("Invalid arrival polling parameters.")
        self.write(goals)
        pending = {axis: angle_to_counts(value) for axis, value in goals.items()}
        deadline = time.monotonic() + timeout
        try:
            while pending and time.monotonic() < deadline:
                for axis, target in list(pending.items()):
                    if abs(self.driver.read_counts(axis) - target) <= tolerance_counts:
                        del pending[axis]
                if pending:
                    time.sleep(1.0 / poll_hz)
        except BaseException as exc:
            self.close_after_failure(exc)
            raise
        return not pending
