"""=============================================================================
TulaRobot LeRobot 适配器 (tula_lerobot_env.py)

本模块提供 TulaRobot (TD-201 / TULA50) 到 LeRobot 标准工具链的桥接层。

核心职责:
  1. 将 TulaRobot 的 Duck Typing 接口 (read/write) 封装为 LeRobot 期望的
     Robot 形态 (leader_arms / follower_arms / cameras / is_connected)。
  2. 提供动作空间与观测空间的维度描述，供遥操作、录制、训练流水线读取。
  3. 解析 tula_config.yaml 配置文件，为 LeRobot 工具链提供即插即用的体验。

架构说明:
  - TulaLeRobot 不强制继承 lerobot.common.robot_devices.robots.robot.Robot，
    而是采用 Duck Typing 方式匹配其接口。这避免了对 LeRobot 版本强依赖，
    同时保证所有核心属性与方法签名完全兼容。
  - 如果运行环境中已安装 LeRobot，可通过可选继承获得类型检查等额外好处；
    未安装时降级为纯 Duck Typing 适配器，不影响基础功能。
============================================================================="""
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# 确保可以导入本目录下的硬件模块 (不考虑相对导入的包上下文)
# ---------------------------------------------------------------------------
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from tula_robot import TulaRobot

# ---------------------------------------------------------------------------
# 可选: 尝试继承 LeRobot 官方 Robot 基类
# ---------------------------------------------------------------------------
_ROBOT_BASE = object  # 默认退化
try:
    from lerobot.common.robot_devices.robots.robot import Robot as _LeRobotBase
    _ROBOT_BASE = _LeRobotBase
except ImportError:
    pass  # LeRobot 未安装，降级为普通 object


class TulaLeRobot(_ROBOT_BASE):
    """LeRobot 标准兼容的 TulaRobot 包装器。

    对外暴露的接口严格匹配 LeRobot Robot 基类规范:
      - leader_arms: Dict[str, Any]  主端(示教端)臂字典，无主端时为空
      - follower_arms: Dict[str, Any]  从端(执行端)臂字典
      - cameras: Dict[str, Any]       相机字典，当前无相机
      - is_connected: bool            连接状态
      - connect() / disconnect()      生命周期管理
      - send_action(action)           下发动作 (匹配 LeRobot 录制管道的调用约定)
      - capture_observation()         采集观测 (返回 LeRobot 标准观测字典)

    Parameters
    ----------
    port : str
        串口号，默认 "COM5"。
    baudrate : int
        波特率，默认 115200。
    active_axes : List[int] or None
        启用的轴 ID 列表，默认 [1]。
    config_path : str or None
        可选，YAML 配置文件路径。提供时从中读取参数。
    """

    def __init__(
        self,
        port: str = "COM5",
        baudrate: int = 115200,
        active_axes: Optional[List[int]] = None,
        config_path: Optional[str] = None,
    ):
        # -- 如果提供了 YAML 配置文件，优先从文件加载参数 --
        if config_path is not None:
            cfg = _load_config(config_path)
            port = cfg.get("port", port)
            baudrate = cfg.get("baudrate", baudrate)
            active_axes = cfg.get("active_axes", active_axes)

        if active_axes is None:
            active_axes = [1]

        # -- 调用 LeRobot 基类初始化 (如果是真实基类则有效，否则无害) --
        if _ROBOT_BASE is not object:
            super().__init__()

        # -- 底层硬件实例 --
        self._hardware = TulaRobot(
            port=port,
            baudrate=baudrate,
            active_axes=active_axes,
        )

        self._active_axes = active_axes
        self._num_dofs = len(active_axes)

        # -- LeRobot 规范属性 --
        self.leader_arms: Dict[str, Any] = {}
        self.follower_arms: Dict[str, Any] = {
            "tula_arm": self._hardware  # 将整机作为单个 arm 注册
        }
        self.cameras: Dict[str, Any] = {}

    # ==========================================================================
    # LeRobot 核心生命周期
    # ==========================================================================

    @property
    def is_connected(self) -> bool:
        return self._hardware.is_connected

    def connect(self) -> None:
        self._hardware.connect()

    def disconnect(self) -> None:
        self._hardware.disconnect()

    # ==========================================================================
    # LeRobot 标准观测 / 动作接口
    # ==========================================================================

    def send_action(self, action: np.ndarray) -> None:
        """下发动作到从臂 — 对应 LeRobot 录制 / 复现管线的调用入口。

        Parameters
        ----------
        action : np.ndarray
            形状 (num_dofs,) 的目标角度数组，单位: 度 (°)。
        """
        self._hardware.write(action)

    def capture_observation(self) -> Dict[str, np.ndarray]:
        """采集当前观测 — 返回 LeRobot 标准观测字典。

        Returns
        -------
        Dict[str, np.ndarray]
            格式: {
                "observation.state":      np.ndarray (num_dofs,),   关节位置 (°)
                "observation.state.leader": np.ndarray (0,) 或 实际主端位置,
                "action":                 np.ndarray (num_dofs,),   当前动作(复现用)
            }
        """
        raw = self._hardware.read()
        state = raw["observation.state"]  # shape (num_dofs,)
        return {
            "observation.state": state,
            "observation.state.leader": np.zeros((0,), dtype=np.float32),
            "action": state.copy(),  # 默认 action = 当前状态 (无害恒等)
        }

    def read(self) -> Dict[str, np.ndarray]:
        """直接透传硬件 read()，兼容低层调用习惯。"""
        return self._hardware.read()

    def write(self, action: np.ndarray) -> None:
        """直接透传硬件 write()，兼容低层调用习惯。"""
        self._hardware.write(action)

    # ==========================================================================
    # 空间描述: 动作空间 / 观测空间
    # ==========================================================================

    @property
    def num_dofs(self) -> int:
        """自由度数量 (轴数)。"""
        return self._num_dofs

    @property
    def dof_names(self) -> List[str]:
        """每个自由度的可读名称。"""
        return [f"joint_{i}" for i in self._active_axes]

    def get_action_space_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """返回动作空间的 (low, high) 边界，单位: 度。

        默认使用 ±90° 安全限位，实际部署前需根据硬件手册校准。
        """
        low = np.full(self._num_dofs, -90.0, dtype=np.float32)
        high = np.full(self._num_dofs, 90.0, dtype=np.float32)
        return low, high

    def get_observation_space_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """返回观测空间的 (low, high) 边界，与动作空间一致。"""
        return self.get_action_space_bounds()

    # ==========================================================================
    # LeRobot 规范: robot_type 和 features (供 dataset 元数据使用)
    # ==========================================================================

    @property
    def robot_type(self) -> str:
        """机器人类型标识，写入数据集的 metadata。"""
        return "tula_robot"

    @property
    def features(self) -> Dict[str, Any]:
        """LeRobot 数据集 feature 描述。

        返回一个字典，其结构遵循 LeRobot datasets 的 feature schema。
        如果环境中安装了 `datasets` 库，建议在此返回对应的 Features 对象；
        未安装时降级为纯 dict。
        """
        try:
            from datasets import Features, Value, Array2D
            return Features({
                "observation.state": Array2D(shape=(self._num_dofs,), dtype="float32"),
                "action": Array2D(shape=(self._num_dofs,), dtype="float32"),
                "observation.state.leader": Array2D(shape=(0,), dtype="float32"),
            })
        except ImportError:
            return {
                "observation.state": {"shape": (self._num_dofs,), "dtype": "float32"},
                "action": {"shape": (self._num_dofs,), "dtype": "float32"},
                "observation.state.leader": {"shape": (0,), "dtype": "float32"},
            }

    def __repr__(self) -> str:
        return (
            f"<TulaLeRobot robot_type='{self.robot_type}' "
            f"num_dofs={self._num_dofs} "
            f"connected={self.is_connected}>"
        )


# ==============================================================================
# YAML 配置加载工具
# ==============================================================================

def _load_config(config_path: str) -> Dict[str, Any]:
    """从 tula_config.yaml 解析硬件参数，返回标准化 dict。"""
    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # 直接读取扁平化的 YAML 键值，如果找不到则使用默认值
    return {
        "port": raw.get("port", "COM5"),
        "baudrate": raw.get("baudrate", 115200),
        "active_axes": raw.get("active_axes", [1]),
    }


def load_robot_from_config(config_path: Optional[str] = None) -> TulaLeRobot:
    """工厂方法: 从 YAML 配置文件构建 TulaLeRobot 实例。

    如果未提供 config_path，默认查找本文件同目录下的 tula_config.yaml。
    """
    if config_path is None:
        config_path = os.path.join(_current_dir, "tula_config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"找不到配置文件: {config_path}。请先创建 tula_config.yaml。"
        )

    return TulaLeRobot(config_path=config_path)


# ==============================================================================
# 自检入口 — 模拟 LeRobot 工具链加载
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  TulaLeRobot 适配器自检 (无硬件连接也可运行)")
    print("=" * 60)

    # 1. 加载配置
    cfg_path = os.path.join(_current_dir, "tula_config.yaml")
    if os.path.exists(cfg_path):
        cfg = _load_config(cfg_path)
        print(f"\n[CONFIG] {cfg_path}")
        print(f"  port        = {cfg['port']}")
        print(f"  baudrate    = {cfg['baudrate']}")
        print(f"  active_axes = {cfg['active_axes']}")
    else:
        print(f"\n[WARN] 未找到 {cfg_path}，使用默认参数。")
        cfg = {"port": "COM5", "baudrate": 115200, "active_axes": [1]}

    # 2. 构建适配器 (不连接硬件)
    robot = TulaLeRobot(
        port=cfg["port"],
        baudrate=cfg["baudrate"],
        active_axes=cfg["active_axes"],
    )

    print(f"\n[ROBOT] {robot}")
    print(f"  num_dofs          = {robot.num_dofs}")
    print(f"  dof_names         = {robot.dof_names}")
    print(f"  robot_type        = {robot.robot_type}")
    print(f"  leader_arms       = {robot.leader_arms}")
    print(f"  follower_arms     = {list(robot.follower_arms.keys())}")
    print(f"  cameras           = {robot.cameras}")

    low, high = robot.get_action_space_bounds()
    print(f"\n[SPACE] Action low  = {low}")
    print(f"         Action high = {high}")

    print(f"\n[FEATURES]")
    for k, v in robot.features.items():
        print(f"  {k}: {v}")

    print("\n[OK] 适配器基本检查通过。物理连接测试请运行 test_lerobot_integration.py")
    