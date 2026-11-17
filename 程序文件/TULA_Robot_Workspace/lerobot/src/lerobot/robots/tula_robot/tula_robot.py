import time
import logging
import numpy as np
from typing import Dict, List

# 核心修改：去掉了这里的点号，允许当前脚本直接作为主程序运行
from td201_motor import TD201MotorBus, TD201Motor

# 模块级日志记录器
_logger = logging.getLogger(__name__)

class TulaRobot:
    def __init__(self, port: str = "COM5", baudrate: int = 115200, active_axes: List[int] = None):
        if active_axes is None:
            active_axes = [1] 
            
        self.port = port
        self.baudrate = baudrate
        self.active_axes = active_axes
        
        self.bus = TD201MotorBus(port=self.port, baudrate=self.baudrate)
        self.motors: Dict[int, TD201Motor] = {}
        
        for axis_id in self.active_axes:
            self.motors[axis_id] = TD201Motor(bus=self.bus, axis_id=axis_id)
            
        self.is_connected = False

    def connect(self):
        print(f"[TulaRobot] 正在连接主总线 {self.port} ...")
        self.bus.connect()

        # 等待硬件初始化完成。大多数 TD201 驱动器在串口上电后需要
        # 1~2 秒完成内部自检与通信就绪，若在此期间发送运动指令极易
        # 被硬件拒绝 (错误码5: TD201_ERR_PROTOCOL)。
        print("[TulaRobot] 等待硬件初始化 (1.5s) ...")
        time.sleep(1.5)

        for axis_id, motor in self.motors.items():
            print(f"[TulaRobot] 正在绑定轴 {axis_id} ...")
            motor.setup()

        # ================================================================
        # 🔴 安全警告：回零操作
        # TD201 驱动器在上电后处于 HOME_MISSING (0x1000) 状态，会拒绝
        # ma/mr 等绝对/相对运动指令。必须先完成回零建立绝对坐标参考。
        #
        # 回零过程中电机将自动运动至限位/原点传感器位置！
        # 请确保机械行程内无障碍物，且电机线缆不会缠绕。
        #
        # 如果你的电机已经在零点或者不需要绝对定位（仅做开环测试），
        # 可以将 self.skip_home = True 或注释掉下方的 home 循环。
        # ================================================================
        if not getattr(self, 'skip_home', False):
            print("[TulaRobot] ⚠ 开始执行各轴回零，请确保机械安全...")
            for axis_id, motor in self.motors.items():
                motor.home(timeout_ms=6000)
        else:
            print("[TulaRobot] ⚠ 跳过回零（skip_home=True），请确认驱动器状态允许运动！")

        self.is_connected = True
        print("[TulaRobot] 机器人硬件已全部就绪！")

    def disconnect(self):
        if not self.is_connected:
            return
        print("[TulaRobot] 正在安全断开机器人...")
        for axis_id, motor in self.motors.items():
            motor.cleanup()
        self.bus.disconnect()
        self.is_connected = False

    def read(self) -> Dict[str, np.ndarray]:
        if not self.is_connected:
            raise RuntimeError("机器人未连接，无法读取状态！")
        positions = []
        for axis_id in self.active_axes:
            # 高频模式下直接读取物理脉冲数，省去 C 层角度换算开销，
            # 随后在 Python 侧统一转换为度，避免总线串扰。
            pos_counts = self.motors[axis_id].get_position()
            pos_deg = pos_counts / self.motors[axis_id].PULSES_PER_DEGREE
            positions.append(pos_deg)
        return {
            "observation.state": np.array(positions, dtype=np.float32)
        }

    # ==========================================================================
    # 多轴并行同步控制 (Fire-and-Forget + 统一轮询到位)
    # ==========================================================================

    def set_angles(self, target_angles: Dict[int, float],
                   timeout: float = 30.0,
                   tolerance_counts: int = 15,
                   poll_hz: float = 50.0) -> bool:
        """多轴同步绝对角度控制 — 工业级「瞬间群发 + 统一轮询」状态机。

        彻底替代旧式 for 循环中逐轴阻塞等待的串行模式，将所有参与运动的轴
        在同一帧内瞬间下发非阻塞指令，随后以固定频率统一轮询各轴物理到位状态，
        达成真正的多轴并行同动。

        **工作流程:**
          1. 第一阶段（瞬间下发）: 遍历 target_angles 中所有轴，依次调用
             set_angle_async() 下发目标角度。全部指令在极短时间内 (<1ms/轴)
             发出，驱动器收到后各自独立执行。
          2. 第二阶段（统一轮询）: 以 poll_hz 的频率轮询所有运动轴的物理脉冲
             位置。当所有参与轴的 |current_counts - target_counts| <= tolerance
             时判定全部到位，立即退出。若超时则记录 Warning 后退出。

        Args:
            target_angles: {轴ID: 目标角度(度)} 字典。仅下发字典中存在的轴，
                           未包含的轴保持当前位置不变。
            timeout: 总超时时间（秒），默认 5.0 秒。超时后记录 Warning 并返回。
            tolerance_counts: 到位容忍脉冲数，默认 15 counts (约 0.075°)。
                              可根据实际机械特性微调。
            poll_hz: 轮询频率，默认 50Hz。对应 time.sleep(0.02)。

        Returns:
            bool: True 表示所有轴在超时前全部到位，False 表示超时退出。
        """
        if not self.is_connected:
            raise RuntimeError("机器人未连接，无法执行动作！")

        involved_axes = set(target_angles.keys())
        unknown = involved_axes - set(self.motors.keys())
        if unknown:
            raise ValueError(f"目标角度包含未注册的轴: {sorted(unknown)}")

        # ---- 第一阶段：瞬间下发所有轴的 Fire-and-Forget 指令 ----
        target_counts: Dict[int, int] = {}
        for axis_id in involved_axes:
            angle_deg = float(target_angles[axis_id])
            motor = self.motors[axis_id]
            # 预计算目标脉冲数（用于后续到位比对）
            target_counts[axis_id] = motor.angle_to_counts(angle_deg)
            # 非阻塞下发 → 返回后电机已开始运动
            err = motor.set_angle_async(angle_deg)
            if err != 0:
                raise IOError(
                    f"轴 {axis_id} 异步指令下发失败，错误码: {err}"
                )
            # 1ms 物理呼吸间隔：让 RS-485 总线电平稳定，消除轴间数据串扰
            time.sleep(0.001)

        # ---- 第二阶段：统一轮询到位 ----
        poll_interval = 1.0 / poll_hz
        deadline = time.monotonic() + timeout
        all_arrived = False

        while time.monotonic() < deadline:
            all_arrived = True  # 先假设全部到位

            for axis_id in involved_axes:
                # 已到位的轴跳过后续轮询，节省总线带宽
                if axis_id not in target_counts:
                    continue

                current_pos = self.motors[axis_id].get_position()
                error = abs(current_pos - target_counts[axis_id])

                if error <= tolerance_counts:
                    # 该轴到位，从待检集合中移除
                    del target_counts[axis_id]
                else:
                    all_arrived = False

            if all_arrived:
                break

            time.sleep(poll_interval)

        if not all_arrived:
            remaining = {ax: self.motors[ax].get_position() for ax in target_counts}
            _logger.warning(
                f"[TulaRobot.set_angles] 多轴到位超时 (>{timeout}s)！"
                f" 未到位轴数: {len(target_counts)}, "
                f" 当前脉冲 vs 目标脉冲: { {ax: (remaining[ax], target_counts[ax]) for ax in target_counts} }"
            )
            return False

        return True

    # ==========================================================================
    # 标准写入接口 — 保持与 LeRobot Gym 环境完全兼容
    # ==========================================================================

    def write(self, action: np.ndarray):
        """下发动作数组到各轴 (非阻塞模式)。

        映射关系: action[i] → self.active_axes[i]。
        每个轴调用 write_position 即 fire-and-forget，不等待到位。

        Args:
            action: 形状 (num_dofs,) 的目标角度数组，单位: 度 (°)。
        """
        if not self.is_connected:
            raise RuntimeError("机器人未连接，无法执行动作！")
        if len(action) != len(self.active_axes):
            raise ValueError(f"动作维度不匹配！期望 {len(self.active_axes)}，实际收到 {len(action)}")

        for i, axis_id in enumerate(self.active_axes):
            target_deg = float(action[i])
            self.motors[axis_id].write_position(target_deg, timeout_ms=5000)
            # 1ms 物理呼吸间隔：让 RS-485 总线电平稳定，消除轴间数据串扰
            time.sleep(0.001)

# ==============================================================================
# 交互式测试终端 (CLI)
# ==============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*40)
    print("   TulaRobot 交互式单轴调试工具")
    print("="*40)
    
    port_input = input("请输入串口号 [直接回车默认 COM5]: ").strip()
    port = port_input if port_input else "COM5"
    
    axis_input = input("请输入要绑定的电机轴号 [直接回车默认 1]: ").strip()
    axis_id = int(axis_input) if axis_input else 1
    
    robot = TulaRobot(port=port, active_axes=[axis_id])
    
    try:
        robot.connect()
        print("\n--- 进入交互模式 (输入 'q' 退出) ---")
        
        while True:
            obs = robot.read()
            current_deg = obs["observation.state"][0]
            print(f"\n[状态] 电机 {axis_id} 当前角度: {current_deg:.2f} °")
            
            target_input = input(f"请输入电机 {axis_id} 的目标角度 (当前 {current_deg:.2f}°) > ").strip()
            
            if target_input.lower() == 'q':
                break
                
            try:
                target_deg = float(target_input)
                action = np.array([target_deg], dtype=np.float32)
                
                print(f"[执行] 正在驱动电机 {axis_id} 旋转至 {target_deg} ° ...")
                robot.write(action)
                
                time.sleep(0.5) 
                
            except ValueError:
                print("[错误] 非法输入！请输入有效的数字角度，或输入 'q' 退出。")
                
    except KeyboardInterrupt:
        print("\n[中断] 接收到 Ctrl+C，正在终止测试...")
    except Exception as e:
        print(f"\n[系统错误] {e}")
    finally:
        robot.disconnect()
        print("已安全释放总线资源，退出程序。")
        