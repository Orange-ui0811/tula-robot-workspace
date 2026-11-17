import ctypes
import os
import sys

class _TD201AxisStruct(ctypes.Structure):
    _fields_ = [
        ("axis_id", ctypes.c_uint8),
        ("dev", ctypes.c_void_p)
    ]

def _load_td201_lib():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if sys.platform.startswith('win'):
        lib_name = "td201.dll"
    else:
        lib_name = "td201.so"
        
    lib_path = os.path.abspath(os.path.join(current_dir, "libs", lib_name))
    
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"找不到底层驱动库，请确认路径: {lib_path}")

    lib = ctypes.CDLL(lib_path)
    lib.td201_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    lib.td201_open.restype = ctypes.c_int
    lib.td201_close.argtypes = [ctypes.c_void_p]
    lib.td201_close.restype = None
    lib.td201_axis_bind.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.POINTER(_TD201AxisStruct)]
    lib.td201_axis_bind.restype = ctypes.c_int
    lib.td201_axis_unbind.argtypes = [ctypes.POINTER(_TD201AxisStruct)]
    lib.td201_axis_unbind.restype = None
    lib.tula50_get_angle.argtypes = [ctypes.POINTER(_TD201AxisStruct), ctypes.POINTER(ctypes.c_double)]
    lib.tula50_get_angle.restype = ctypes.c_int
    # ---------- 阻塞版：下发绝对角度后原地等待电机到位 ----------
    lib.tula50_set_angle_wait.argtypes = [ctypes.POINTER(_TD201AxisStruct), ctypes.c_double, ctypes.c_long]
    lib.tula50_set_angle_wait.restype = ctypes.c_int
    # ---------- 非阻塞版：下发绝对角度指令后立即返回 (Fire-and-Forget) ----------
    lib.tula50_set_angle.argtypes = [ctypes.POINTER(_TD201AxisStruct), ctypes.c_double]
    lib.tula50_set_angle.restype = ctypes.c_int
    # ---------- 读取物理脉冲计数值 (用于轮询到位检测) ----------
    lib.td201_get_position.argtypes = [ctypes.POINTER(_TD201AxisStruct), ctypes.POINTER(ctypes.c_long)]
    lib.td201_get_position.restype = ctypes.c_int
    lib.td201_home_wait.argtypes = [ctypes.POINTER(_TD201AxisStruct), ctypes.c_long]
    lib.td201_home_wait.restype = ctypes.c_int
    return lib

_LIB = _load_td201_lib()

class TD201MotorBus:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port.encode('utf-8')
        self.baudrate = baudrate
        self.dev_ptr = ctypes.c_void_p()
        self.is_connected = False

    def connect(self):
        if self.is_connected: return
        err = _LIB.td201_open(self.port, self.baudrate, ctypes.byref(self.dev_ptr))
        if err != 0: raise ConnectionError(f"TD201总线连接失败！错误码: {err}")
        self.is_connected = True

    def disconnect(self):
        if self.is_connected and self.dev_ptr:
            _LIB.td201_close(self.dev_ptr)
            self.is_connected = False
            self.dev_ptr = ctypes.c_void_p()

class TD201Motor:
    # TULA50 编码器物理分辨率: 200 脉冲/度 (即 0.005°/脉冲)
    PULSES_PER_DEGREE = 200.0

    def __init__(self, bus: TD201MotorBus, axis_id: int):
        self.bus = bus
        self.axis_id = axis_id
        self.axis_struct = _TD201AxisStruct()
        self.is_bound = False

    def setup(self):
        if not self.bus.is_connected: raise RuntimeError("总线未连接！")
        err = _LIB.td201_axis_bind(self.bus.dev_ptr, self.axis_id, ctypes.byref(self.axis_struct))
        if err != 0: raise RuntimeError(f"轴绑定失败，错误码: {err}")
        self.is_bound = True

    # ==========================================================================
    # 角度读取
    # ==========================================================================

    def read_position(self) -> float:
        """读取当前角度（度），阻塞等待硬件应答后返回。"""
        if not self.is_bound: raise RuntimeError("轴未绑定！")
        current_deg = ctypes.c_double()
        err = _LIB.tula50_get_angle(ctypes.byref(self.axis_struct), ctypes.byref(current_deg))
        if err != 0: raise IOError(f"读取角度失败，错误码: {err}")
        return current_deg.value

    # ==========================================================================
    # 物理脉冲读取 (用于高频轮询到位检测)
    # ==========================================================================

    def get_position(self) -> int:
        """获取当前编码器反馈的物理脉冲计数值。

        与 read_position() 不同，此方法直接返回底层脉冲数，
        省去角度换算开销，适合 50Hz 轮询到位检测场景。

        Returns:
            int: 编码器脉冲计数 (200 pulses/deg)
        """
        if not self.is_bound:
            raise RuntimeError("轴未绑定！")
        pos = ctypes.c_long()
        err = _LIB.td201_get_position(ctypes.byref(self.axis_struct), ctypes.byref(pos))
        if err != 0:
            raise IOError(f"读取物理位置失败，错误码: {err}")
        return pos.value

    # ==========================================================================
    # 角度 ↔ 脉冲换算
    # ==========================================================================

    @staticmethod
    def angle_to_counts(angle_deg: float) -> int:
        """将目标角度（度）转换为编码器脉冲计数值。

        换算公式: counts = angle_deg × 200 pulses/deg
        四舍五入取整，与 C 层 tula50.c 中的转换逻辑完全一致。

        Args:
            angle_deg: 目标角度 (度)

        Returns:
            int: 等效的脉冲计数值
        """
        pulses = angle_deg * TD201Motor.PULSES_PER_DEGREE
        # 与 tula50.c 中 floor/ceil 四舍五入逻辑一致
        return int(pulses + 0.5) if pulses >= 0.0 else int(pulses - 0.5)

    # ==========================================================================
    # 非阻塞绝对角度下发 (Fire-and-Forget) —— 多轴并行核心入口
    # ==========================================================================

    def set_angle_async(self, angle_deg: float) -> int:
        """非阻塞的 Fire-and-Forget 绝对角度下发方法。

        调用底层 tula50_set_angle 指令后立即返回，不等待电机到位。
        这是实现"多轴并行控制"的核心入口：
          1. 对每个参与运动的轴连续调用此方法，瞬间完成全部指令下发
          2. 随后通过 get_position() + angle_to_counts() 统一轮询，
             等待所有轴同步到位

        Args:
            angle_deg: 目标绝对角度 (度)

        Returns:
            int: 底层错误码。0 (TD201_OK) 表示指令成功下发，
                 非 0 需要通过 td201_strerror 查询具体原因。
        """
        if not self.is_bound:
            raise RuntimeError("轴未绑定！")
        return _LIB.tula50_set_angle(ctypes.byref(self.axis_struct), float(angle_deg))

    # ==========================================================================
    # 兼容 Duck Typing 的标准写入口 (保持与 LeRobot Gym 环境兼容)
    # ==========================================================================

    def write_position(self, target_deg: float, timeout_ms: int = 500):
        """非阻塞下发绝对角度指令（Fire-and-Forget）。

        timeout_ms 参数仅保留用于兼容上层鸭子类型，内部不再进行阻塞等待。
        调用后电机开始运动，但本方法立即返回。
        """
        if not self.is_bound:
            raise RuntimeError("轴未绑定！")
        err = _LIB.tula50_set_angle(ctypes.byref(self.axis_struct), float(target_deg))
        if err != 0:
            raise IOError(f"写入角度失败，错误码: {err}")

    # ==========================================================================
    # 回零
    # ==========================================================================

    def home(self, timeout_ms: int = 30000):
        """
        执行硬件回零操作并阻塞等待完成。
        
        回零是绝对定位的前提：驱动器在上电后处于 HOME_MISSING 状态，
        会拒绝 ma/mr 等闭环运动指令。必须先完成回零建立绝对坐标参考。
        
        WARNING: 回零过程中电机将自动运动至限位/原点传感器位置。
        请确保机械行程内无障碍物。
        """
        if not self.is_bound:
            raise RuntimeError("轴未绑定，无法回零！")
        print(f"[TD201Motor] 轴 {self.axis_id} 正在回零（最长等待 {timeout_ms}ms）...")
        err = _LIB.td201_home_wait(ctypes.byref(self.axis_struct), int(timeout_ms))
        if err != 0:
            raise IOError(f"轴 {self.axis_id} 回零失败，错误码: {err}")
        print(f"[TD201Motor] 轴 {self.axis_id} 回零完成。")

    def cleanup(self):
        if self.is_bound:
            _LIB.td201_axis_unbind(ctypes.byref(self.axis_struct))
            self.is_bound = False
            