# LeRobot 本地开发说明

LeRobot 是 Hugging Face 的机器人框架，提供机器人设备接口、配置、遥操作、数据采集和策略工具。通用说明见[官方 README](README.md)；本文只说明本工作区的版本和 Tula 插件接入。

## 版本与环境

| 对象 | 当前基线 |
|---|---|
| 本地 LeRobot | 0.6.2，`ba83e4cf43737e2665be0aafcb5f513b83c7d0f3` |
| 本地 Tula 插件 | 0.1.0，依赖 `lerobot>=0.6.2,<0.7`；本轮仅验证指定提交 |
| 统一环境 | Windows x64、CPython 3.12.13 x64、工作区根目录 `.venv`；实测 draccus 0.11.6 |
| 验收 | 两个项目均为本地 editable 安装；官方发现、解析、工厂创建及 13 项无硬件测试通过 |

框架的 [Robot 工厂](src/lerobot/robots/utils.py)负责创建对象；[插件发现模块](src/lerobot/utils/import_utils.py)按已安装发行包名发现独立插件。仓库内的旧 Tula 原型不是当前入口。

## 使用或重建统一环境

以下 PowerShell 命令在[工作区根目录](../README.md)执行。已有正常的 `.venv` 可直接复用。重建前用 `git -C .\lerobot rev-parse HEAD` 核对上表提交，准备 uv 和已有的 CPython 3.12.13 x64；重建环境不需要升级 LeRobot。

```powershell
# 仅在 .venv 不存在时创建。若 uv 找不到该版本，用已有解释器的完整路径替换版本号。
uv venv --python 3.12.13 --no-python-downloads .venv
uv pip install --python .\.venv\Scripts\python.exe -e .\lerobot
uv pip install --python .\.venv\Scripts\python.exe --no-deps -e .\lerobot_robot_tula
uv pip check --python .\.venv\Scripts\python.exe
```

首次安装会获取基础依赖，不需要为插件安装训练、数据集等可选功能。安装插件时用 `--no-deps` 保留已安装的本地 LeRobot；依赖检查失败时先核对提交和安装来源，不要另装 PyPI LeRobot 覆盖它。

在**工作区根目录**复跑无硬件测试（预期 `Ran 13 tests`、`OK`）：

```powershell
.\.venv\Scripts\python.exe -I -B -m unittest discover -s .\lerobot_robot_tula\tests -v
```

## 无硬件发现与创建

LeRobot 按已安装发行包名的 `lerobot_robot_` 前缀发现插件，导入 `lerobot_robot_tula` 后注册 `tula_robot`，然后 draccus 解析 `--robot.type=tula_robot`，官方工厂创建对象。仅把源码目录放进 PYTHONPATH 不等于安装插件；无需改本目录的 Robot 工厂。

在上面的环境中，可从工作区根运行以下 PowerShell 片段。它只验证发现、解析和创建，临时标定目录会自动清理。**不要加 `robot.connect()`**，`MOCK` 也不是实际串口。

```powershell
@'
from dataclasses import dataclass
from tempfile import TemporaryDirectory
import draccus
from lerobot.robots import RobotConfig, make_robot_from_config
from lerobot.utils.import_utils import register_third_party_plugins

@dataclass
class Args:
    robot: RobotConfig

with TemporaryDirectory() as tmp:
    register_third_party_plugins()
    cfg = draccus.parse(Args, args=[
        "--robot.type=tula_robot", "--robot.port=MOCK",
        "--robot.calibration_dir", tmp,
    ])
    robot = make_robot_from_config(cfg.robot)
    print(robot.name, robot.observation_features)
    assert not robot.is_connected
'@ | .\.venv\Scripts\python.exe -I -B -
```

正式创建通过不等于真机通过，也不等于 `lerobot-teleoperate` 或 `lerobot-record` 已验收。这些流程还需要动作键和单位兼容的 Teleoperator；实机测试见[现场计划](../HARDWARE_TEST_PLAN.md)。
