# Tula Robot — LeRobot 插件

独立安装的 Windows x86-64 Tula/TD-201 机器人插件。它把官方 LeRobot 的配置、生命周期和观测/动作接口映射到 TD-201 多轴控制，不修改 LeRobot 或 C SDK。

```text
LeRobot 工厂 → TulaRobot → TulaController → TD201Driver
                                            ↓ ctypes
                                    包内 td201.dll → TD-201
```

## 文件职责

| 文件 | 作用 |
|---|---|
| [`__init__.py`](src/lerobot_robot_tula/__init__.py) | 导出 TulaRobotConfig 和 TulaRobot；导入时注册配置，不加载 DLL |
| [`config.py`](src/lerobot_robot_tula/config.py) | 注册 `tula_robot`，校验端口、轴地址及经确认的每轴度数限位 |
| [`robot.py`](src/lerobot_robot_tula/robot.py) | 实现 LeRobot Robot：features、连接、标定接口、观测和动作；显式提供回零与软件停止 |
| [`controller.py`](src/lerobot_robot_tula/controller.py) | 绑定轴、读取 counts 转度、检查状态、按配置顺序下发、清理连接；独立的到位等待不进入周期控制 |
| [`td201_driver.py`](src/lerobot_robot_tula/td201_driver.py) | ctypes 签名、设备和轴句柄、状态、位置、目标、回零及停止；仅真实驱动连接时加载库 |
| [`tests/test_discovery.py`](tests/test_discovery.py) | 新进程中用正式插件发现、draccus 和工厂创建 Robot；禁止加载 DLL |
| [`tests/test_robot.py`](tests/test_robot.py) | 注入假 Driver，验证双轴顺序、范围和状态拒绝、连接及故障清理 |

## 环境、安装与测试

插件 0.1.0 的已验收组合是 Windows x64、CPython 3.12.13 x64、LeRobot 0.6.2（`ba83e4cf43737e2665be0aafcb5f513b83c7d0f3`）。[依赖](pyproject.toml)为 `lerobot>=0.6.2,<0.7`，但不代表整个版本范围均已测试。两个项目均以本地 editable 方式安装在工作区根目录 `.venv`；从零准备按[统一安装说明](../lerobot/README.local.md)先装本地框架，再装插件。

从**工作区根目录**复跑无硬件测试：

```powershell
.\.venv\Scripts\python.exe -I -B -m unittest discover -s .\lerobot_robot_tula\tests -v
```

先安装再测试：LeRobot 的 `register_third_party_plugins()` 按发行包名称发现并导入插件，注册 `tula_robot`；draccus 解析 `--robot.type=tula_robot` 后，由 `make_robot_from_config()` 创建 `TulaRobot`。正式入口不使用 LeRobot 仓库里的旧 Tula 原型。

当前统一环境 **13 项无硬件测试全部通过**，包括从工作区外启动的发现、解析和工厂验证。Mock 不加载真实 TD-201 DLL、不接触串口，也不能证明实机时序和停机效果。[历史 wheel 验收](docs/validation.md)是另一轮验证，不是当前安装方式。

## 配置、动作与安全

- 类型为 `tula_robot`，须显式指定 `port`。默认轴映射为 `joint_1 → 1`、`joint_2 → 2`，波特率 115200；它们来自旧例，不是现场验收值。旧 YAML 的字段迁移见[迁移说明](docs/migration.md)。
- features 声明 `joint_1.pos` 等扁平度数标量。动作必须覆盖恰好全部配置关节，并提供现场确认的 `action_limits_deg`。缺限位、缺键、多键、非有限值或越界，整帧在发送前拒绝，不静默裁剪。
- `connect()` 打开设备、等待原有 1.5 秒、绑定轴并查状态，**不自动回零**。`calibrate()` 不做主机侧标定，不替代物理回零。只有显式 `home(timeout_ms=...)` 才会请求真实回零，须按硬件规程执行。
- `send_action()` 先检查各轴状态，拒绝未回零或致命报警，再按轴顺序发目标，保留逐轴 1 ms 发送间隔；成功返回下发目标字典，不等待机械到位。状态查询和串口写仍是同步 I/O，真实频率未测。
- 通信中途失败时，前一轴可能已经收到目标；清理串口资源不等于停止电机。显式软件 `stop()` 也不能代替硬件急停。

## DLL 与完成度

DLL 位于 [包内 libs/windows-x86_64](src/lerobot_robot_tula/libs/windows-x86_64)，按模块文件位置查找，仅真实驱动连接时通过 ctypes 加载。Windows wheel 包含该库，不依赖当前工作目录、不访问兄弟 SDK 路径，也不在安装时重编译。DLL 来源为 [TD-201 SDK](../td201_sdk/README.md)，验收哈希为 `DCA559AFFBFD38E755C96418027200F12353A2A165A51D1399332212CD21DEDD`。

**已实现并无硬件验证**：正式发现/创建、配置解析、双轴观测和动作、状态拒绝、异常清理。**尚未实现或验收**：Linux 原生库、相机、自有 Teleoperator、主机标定持久化；实际限位、回零、停机、时延及完整 `teleoperate` / `record` 流程仍待验。分发 DLL 前确认公司授权。

实际连接、回零和运动由获授权的现场人员按[实机测试计划](../HARDWARE_TEST_PLAN.md)执行。
