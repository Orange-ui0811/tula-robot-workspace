# TULA Robot 工作区

本工作区用于维护 Tula 机器人与 TD-201 控制器的集成：LeRobot 提供统一机器人接口，Tula 插件实现设备适配，TD-201 SDK 维护底层串口协议和 C API。

| 目录 | 职责 | 从这里开始 |
|---|---|---|
| `lerobot/` | Hugging Face 官方源码 checkout，供框架开发和参考 | [本地环境与插件接入](lerobot/README.local.md)；[官方 README](lerobot/README.md) |
| `lerobot_robot_tula/` | 独立安装的 Tula 插件，负责配置、机器人接口、多轴控制和 ctypes | [插件安装、文件索引与测试](lerobot_robot_tula/README.md) |
| `td201_sdk/` | C 源码、公开头文件、原生库及诊断示例 | [SDK 环境、构建与串口安全](td201_sdk/README.md) |

## 调用关系

```text
LeRobot 配置 / 工厂
  → TulaRobot → TulaController → TD201Driver（ctypes）
  → 插件包内的 td201.dll → ASCII 串口 → TD-201 控制器
```

DLL 来自 TD-201 SDK，但随插件安装产物分发；运行时不从兄弟 SDK 目录读取，也不要求三个项目处在同一父目录。SDK 可独立使用。LeRobot checkout 中的旧 Tula 原型不是正式插件入口。

## 当前软件基线

| 项目 | 基线 |
|---|---|
| LeRobot | 0.6.2，`ba83e4cf43737e2665be0aafcb5f513b83c7d0f3` |
| Tula 插件 | 0.1.0 |
| Python 环境 | Windows x64，CPython 3.12.13，工作区根目录 `.venv` |
| 安装 | 先装本地 LeRobot，再装本地 Tula 插件；均为 editable，使用同一个解释器 |
| 软件验收 | 官方插件发现、配置解析、工厂创建通过；13 项无硬件测试全部通过 |

在**工作区根目录**运行以下命令，复跑插件发现和 Mock 测试（不加载 TD-201 DLL，不打开串口）：

```powershell
.\.venv\Scripts\python.exe -I -B -m unittest discover -s .\lerobot_robot_tula\tests -v
```

## 新员工开发顺序

1. 先读[本地环境说明](lerobot/README.local.md)，复用工作区 `.venv`；缺少环境时按该页重建，不另装一份 PyPI LeRobot。
2. 按[插件测试说明](lerobot_robot_tula/README.md)运行无硬件测试，确认安装包可发现、工厂可创建，再读关节键与双轴映射。开发适配功能优先改插件。
3. 需要查 C API、DLL 或串口问题时再读[SDK 文档](td201_sdk/README.md)。正常插件开发不需要重编 DLL；C API 或原生库变更应单独验收。
4. 真机由获授权的现场人员按[实机测试计划](HARDWARE_TEST_PLAN.md)分阶段验收。13 项无硬件测试不代表实机、完整录制或遥操作流程已经验收。
