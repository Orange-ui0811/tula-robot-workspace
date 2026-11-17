import ctypes
import sys
from pathlib import Path

# ==============================================================================
# 1. 结构体映射 (与 C 语言头文件完全对齐)
# ==============================================================================
class TD201Axis(ctypes.Structure):
    """映射 C 语言中的 td201_axis_t 结构体"""
    _fields_ = [
        ("axis_id", ctypes.c_uint8),
        ("dev", ctypes.c_void_p)  # opaque pointer (td201_dev_t *)
    ]

# ==============================================================================
# 2. 动态库加载与接口规范 (FFI - Foreign Function Interface)
# ==============================================================================
def load_td201_library():
    """健壮地加载底层驱动 DLL/SO"""
    # 从脚本位置定位项目，不依赖当前 shell 工作目录。
    project_root = Path(__file__).resolve().parents[1]
    # 组合出底层库的绝对路径 (跨平台兼容写法)
    if sys.platform.startswith('win'):
        lib_name = "td201.dll"
    else:
        lib_name = "libtd201.so"
        
    lib_path = project_root / "hardware" / "libs" / lib_name
    
    if not lib_path.is_file():
        raise FileNotFoundError(f"找不到底层驱动库！请确认已编译成功：{lib_path}")

    # 加载动态链接库
    lib = ctypes.CDLL(str(lib_path))

    # -------- 核心函数签名注册 --------
    # 注册 td201_open: td201_err_t td201_open(const char *port, int baud, td201_dev_t **out_dev)
    lib.td201_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    lib.td201_open.restype = ctypes.c_int

    # 注册 td201_close: void td201_close(td201_dev_t *dev)
    lib.td201_close.argtypes = [ctypes.c_void_p]
    lib.td201_close.restype = None

    # 注册 td201_axis_bind: td201_err_t td201_axis_bind(td201_dev_t *dev, uint8_t axis_id, td201_axis_t *axis)
    lib.td201_axis_bind.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.POINTER(TD201Axis)]
    lib.td201_axis_bind.restype = ctypes.c_int

    # 注册 tula50_get_angle: td201_err_t tula50_get_angle(td201_axis_t *axis, double *current_deg)
    lib.tula50_get_angle.argtypes = [ctypes.POINTER(TD201Axis), ctypes.POINTER(ctypes.c_double)]
    lib.tula50_get_angle.restype = ctypes.c_int

    return lib

# ==============================================================================
# 3. 业务逻辑验证
# ==============================================================================
def main():
    print("--- 正在初始化 Python-C FFI 桥接层 ---")
    try:
        lib = load_td201_library()
        print("[成功] 底层动态库加载完毕")
    except Exception as e:
        print(f"[错误] {e}")
        return

    # TODO: 请修改为你在设备管理器中看到的实际串口号
    PORT_NAME = b"COM5"  
    BAUDRATE = 115200
    AXIS_ID = 1

    dev_ptr = ctypes.c_void_p()
    axis = TD201Axis()

    # 1. 打开设备
    print(f"尝试连接串口 {PORT_NAME.decode()} ...")
    err = lib.td201_open(PORT_NAME, BAUDRATE, ctypes.byref(dev_ptr))
    if err != 0:
        print(f"[失败] 串口打开失败，错误码: {err}")
        return
    print("[成功] 串口已连接")

    # 2. 绑定轴
    err = lib.td201_axis_bind(dev_ptr, AXIS_ID, ctypes.byref(axis))
    if err != 0:
        print(f"[失败] 轴绑定失败，错误码: {err}")
        lib.td201_close(dev_ptr)
        return

    # 3. 读取角度
    current_deg = ctypes.c_double()
    err = lib.tula50_get_angle(ctypes.byref(axis), ctypes.byref(current_deg))
    if err == 0:
        print(f"\n>>>> [通信成功] 当前电机真实角度为: {current_deg.value:.2f} ° <<<<\n")
    else:
        print(f"\n[警告] 读取角度失败，超时或协议错误，错误码: {err}\n")

    # 4. 安全关闭
    lib.td201_close(dev_ptr)
    print("底层硬件连接已安全关闭。")

if __name__ == "__main__":
    main()
