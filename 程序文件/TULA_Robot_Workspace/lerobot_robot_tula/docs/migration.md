# 迁移来源与边界

- 原 Tula 的 ctypes 设备/轴绑定、位置读取、角度发送迁入 td201_driver.py。
  保留原函数签名；报警、停止接口按 SDK 头文件和 DLL 导出核对后增补。
- 原 TulaRobot 的 counts/200、轴顺序、逐轴 1 ms 延时及可选到位轮询迁入 controller.py。
  周期动作不经过到位轮询；move_and_wait 显式使用旧签名默认的 30 秒、15 counts、目标 50 Hz。
  等待超时返回 False，不代表运动已停止。
- TulaLeRobot 的 ndarray 包装替换为正式 Robot，不迁移 sys.path 注入、旧基类和压测入口。
- 本地旧 LeRobot 0.5.2 的核心抽象方法和工厂可用于兼容对照；目标 0.6.2
  改用 lerobot.lerobot_types，并增加可选 position-hold 与标定辅助方法。
  本插件不用旧类型路径，不声明 position-hold，不继承舵机总线。
- 旧 YAML 的 active_axes: [1, 2] 转为 axes: {joint_1: 1, joint_2: 2}。
  port 与 baudrate 可保留；旧 action_limits 从未生效，不能原样当作安全数据。
  正式配置的 action_limits_deg 接受每关节 [最小度, 最大度]，必须由现场确认。
- 测试用限位、端口、模拟状态都不是实机配置。SDK DLL 与旧适配副本哈希相同；
  本轮只静态核对 PE/导出，不加载或调用真实 DLL。
