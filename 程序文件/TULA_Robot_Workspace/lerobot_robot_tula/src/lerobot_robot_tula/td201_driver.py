"""Private ctypes bridge; no DLL is loaded until connect()."""
import ctypes as c
import platform
import sys
from pathlib import Path

PULSES_PER_DEGREE = 200.0
MAX_TARGET_COUNTS = 2_147_000_000  # TULA50_MAX_PULSES in the shipped SDK.
HOME_MISSING = 0x1000
FATAL_MASK = 0x0010 | 0x0004 | 0x0001


class TD201Error(OSError):
    def __init__(self, operation: str, code: int, axis: int | None = None):
        self.operation, self.code, self.axis = operation, code, axis
        super().__init__(f"{operation} failed (axis={axis}, TD-201 code={code})")


class _Axis(c.Structure):
    _fields_ = [("axis_id", c.c_uint8), ("dev", c.c_void_p)]


class _Alarm(c.Structure):
    _fields_ = [("alarm_code", c.c_int), ("alarm_hex", c.c_uint)]


def angle_to_counts(degrees: float) -> int:
    counts = degrees * PULSES_PER_DEGREE
    return int(counts + 0.5 if counts >= 0 else counts - 0.5)


def _load_library():
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"} or c.sizeof(c.c_void_p) != 8:
        raise OSError("TD-201 requires Windows x86-64 with 64-bit Python; Linux is not packaged.")
    path = Path(__file__).resolve().parent / "libs" / "windows-x86_64" / "td201.dll"
    if not path.is_file():
        raise FileNotFoundError(f"Missing packaged TD-201 library: {path}")
    lib = c.CDLL(str(path))
    axis = c.POINTER(_Axis)
    signatures = {
        "td201_open": ([c.c_char_p, c.c_int, c.POINTER(c.c_void_p)], c.c_int),
        "td201_close": ([c.c_void_p], None),
        "td201_axis_bind": ([c.c_void_p, c.c_uint8, axis], c.c_int),
        "td201_axis_unbind": ([axis], None),
        "tula50_get_angle": ([axis, c.POINTER(c.c_double)], c.c_int),
        "tula50_set_angle_wait": ([axis, c.c_double, c.c_long], c.c_int),
        "tula50_set_angle": ([axis, c.c_double], c.c_int),
        "td201_get_position": ([axis, c.POINTER(c.c_long)], c.c_int),
        "td201_home_wait": ([axis, c.c_long], c.c_int),
        "td201_get_alarm": ([axis, c.POINTER(_Alarm)], c.c_int),
        "td201_stop": ([axis], c.c_int),
    }
    for name, (args, result) in signatures.items():
        function = getattr(lib, name)
        function.argtypes = args
        function.restype = result
    return lib


class TD201Driver:
    """One TD-201 device handle and its bound axes."""

    def __init__(self, port: str, baudrate: int):
        self.port, self.baudrate = port, baudrate
        self._lib = None
        self._device = c.c_void_p()
        self._axes: dict[int, _Axis] = {}

    @staticmethod
    def _check(name: str, code: int, axis: int | None = None) -> None:
        if code:
            raise TD201Error(name, code, axis)

    def connect(self) -> None:
        if self._device:
            raise RuntimeError("TD-201 device already open.")
        self._lib = _load_library()
        self._check("td201_open", self._lib.td201_open(
            self.port.encode("utf-8"), self.baudrate, c.byref(self._device)
        ))

    def bind(self, axis_id: int) -> None:
        axis = _Axis()
        self._check("td201_axis_bind", self._lib.td201_axis_bind(self._device, axis_id, c.byref(axis)), axis_id)
        self._axes[axis_id] = axis

    def unbind(self, axis_id: int) -> None:
        axis = self._axes.pop(axis_id, None)
        if axis is not None:
            self._lib.td201_axis_unbind(c.byref(axis))

    def close(self) -> None:
        try:
            if self._device:
                self._lib.td201_close(self._device)
        finally:
            self._device = c.c_void_p()
            self._axes.clear()
            self._lib = None

    def read_counts(self, axis_id: int) -> int:
        value = c.c_long()
        self._check("td201_get_position", self._lib.td201_get_position(
            c.byref(self._axes[axis_id]), c.byref(value)
        ), axis_id)
        return value.value

    def read_degrees(self, axis_id: int) -> float:
        value = c.c_double()
        self._check("tula50_get_angle", self._lib.tula50_get_angle(
            c.byref(self._axes[axis_id]), c.byref(value)
        ), axis_id)
        return value.value

    def read_status(self, axis_id: int) -> int:
        value = _Alarm()
        self._check("td201_get_alarm", self._lib.td201_get_alarm(
            c.byref(self._axes[axis_id]), c.byref(value)
        ), axis_id)
        return value.alarm_hex

    def write_degrees(self, axis_id: int, degrees: float) -> None:
        self._check("tula50_set_angle", self._lib.tula50_set_angle(
            c.byref(self._axes[axis_id]), degrees
        ), axis_id)

    def home(self, axis_id: int, timeout_ms: int) -> None:
        self._check("td201_home_wait", self._lib.td201_home_wait(
            c.byref(self._axes[axis_id]), timeout_ms
        ), axis_id)

    def stop(self, axis_id: int) -> None:
        self._check("td201_stop", self._lib.td201_stop(c.byref(self._axes[axis_id])), axis_id)
