# TULA Python Test Windows 交接版

本文件夹是给 Windows 电脑使用的 TULA 执行器测试版本。

为避免 macOS 与 Windows 之间传输时出现中文文件名乱码，交接压缩包统一使用英文文件名。文件内容和运行菜单仍为中文：

```text
README_CN.md
install_deps.bat
start_menu.bat
```

注意：请先把 zip 解压成普通文件夹后再运行，不要直接在压缩包预览窗口里双击运行。

当前通信方式是 USB 转串口，Windows 下串口号通常是：

```text
COM4
COM5
COM6
```

实际串口号请在：

```text
设备管理器 -> 端口（COM 和 LPT）
```

中查看。

## 1. 文件说明

### 推荐入口文件

```text
start_menu.bat
```

Windows 双击启动入口。会自动进入中文测试菜单，不需要手动输入很长的 Python 命令。

```text
install_deps.bat
```

首次使用时双击运行，用于安装 Python 串口库 `pyserial`。

```text
tula_windows_menu.py
```

中文交互菜单主程序。支持手动输入串口号、旋转轴状态读取、回零、绝对运动、相对运动、双轴运动、分段大角度运动、停止、直线轴状态读取、直线轴回零和直线轴安全移动。

### 核心 SDK 文件

```text
tula_controller.py
```

TULA 执行器底层控制库，是当前最核心的 SDK 文件。负责打开串口、发送命令、读取返回帧、解析状态码、读取位置、回零、停止、绝对运动、相对运动、开环运动、双轴联动和安全移动。

```text
tula_commands.py
```

TULA 命令和状态定义文件。用于集中管理命令名称、状态码含义和后续扩展。以后如果增加新的驱动器型号或新命令，优先在这里补充。

```text
requirements.txt
```

Python 依赖列表。目前主要依赖 `pyserial`。

### 常用测试脚本

```text
tula_ping_test.py
```

只读通信测试脚本。用于确认串口能打开、驱动器有返回、轴号正确、状态和当前位置能读取。该脚本不会主动让轴运动。

```text
tula_recover_test.py
```

恢复和回零脚本。用于停止轴、查看状态、清理 `HOME_MISSING` 或 `POSITION_ERR` 后重新回零。断电重启、手动转动轴或出现位置错误后，优先使用这个脚本恢复。

```text
tula_safe_move_test.py
```

单轴小角度安全运动脚本。带有最大移动范围限制，适合第一次验证某个轴能否按目标角度运动并返回零点。

```text
tula_repeatability_test.py
```

重复性测试脚本。用于多次执行双轴目标位置、回零、反向运动等动作，并输出误差和通过情况，可生成 CSV 测试报告。

```text
tula_home_monitor_test.py
```

回零过程监控脚本。用于观察回零过程中状态码和位置变化，排查某个轴回零时间过长、一直 `MOTOR_RUNNING` 或找不到零点的问题。

```text
tula_linear_test.py
```

直线轴测试脚本。用于未来接入直线平台，支持按 counts 测试，也支持在已知 `counts_per_mm` 后按 mm 测试。

### 进阶测试脚本

```text
tula_basic_test.py
```

旋转轴基础闭环测试脚本。包含版本读取、配置读取、状态读取、回零、小角度相对运动和绝对运动。

```text
tula_dual_axis_test.py
```

双轴联动测试脚本。用于测试两轴同时相对运动、绝对运动、反向运动和开环运动。

```text
tula_openloop_test.py
```

开环控制测试脚本。用于测试 `on/off/cy/fo/re/bi` 等开环相关命令。

### LeRobot 接口原型文件

```text
tula_motor_bus.py
```

参考 LeRobot motor bus 思路写的 TULA 电机总线封装。把轴号映射为关节名，例如 `joint_1`、`joint_2`，提供类似读取位置、写入目标位置、读取状态等接口。

```text
tula_robot.py
```

参考 LeRobot robot 抽象写的 TULA 机器人接口原型。把执行器位置封装成 observation 和 action，例如 `joint_1.pos`、`joint_2.pos`。

```text
tula_motor_bus_example.py
```

`tula_motor_bus.py` 的使用示例。用于演示如何通过关节名读取位置和发送目标位置。

```text
tula_robot_example.py
```

`tula_robot.py` 的使用示例。用于演示如何按 LeRobot 风格读取 observation、发送 action，并让两轴返回零点。

### 自动化测试文件

```text
tests/
```

本地软件单元测试目录，使用模拟串口验证 SDK 的解析、状态码、位置读写和 LeRobot 原型接口逻辑，不需要真实硬件。

```text
tests/fake_serial.py
```

模拟串口设备，用于在没有驱动器硬件时测试 Python 代码逻辑。

```text
tests/test_tula_controller_fake_serial.py
```

测试 `tula_controller.py` 的命令发送、返回解析、状态解码和运动接口。

```text
tests/test_tula_robot_fake_serial.py
```

测试 `tula_motor_bus.py` 和 `tula_robot.py` 的关节映射、位置读写和 observation/action 接口。

## 2. 首次使用

1. 安装 Python 3.10 或更高版本。
2. 连接 TULA/TD-201 驱动器和 USB 转串口线。
3. 关闭串口助手、PC Manager 等会占用串口的软件。
4. 双击安装依赖：

```text
install_deps.bat
```

5. 双击启动中文菜单：

```text
start_menu.bat
```

## 3. 中文菜单测试流程

启动后先选择：

```text
1. 输入/修改串口号
```

输入实际串口号，例如：

```text
COM4
```

如果设备管理器里显示 `COM15`，菜单里直接输入：

```text
COM15
```

程序会自动按 Windows 高位串口规则转换，不需要手动输入 `\\.\COM15`。

串口号只在本次菜单运行期间保留，不创建配置文件。每次重新启动菜单后，请先选择功能 1 确认串口号。

之后建议按下面顺序测试。

### 第一步：只读状态

选择：

```text
2. 查看旋转两轴状态（只读，不运动）
```

该功能只读取版本、状态和位置，不会让电机运动。

正常状态一般为：

```text
状态=0 []
```

如果看到：

```text
HOME_MISSING
```

说明该轴还没有回零。

### 第二步：回零

确认机械结构安全后，选择：

```text
3. 单个旋转轴回零
```

或：

```text
4. 旋转两轴回零
```

回零时执行器可能会转动寻找零点。确认机构不会撞线、卡住或碰到限位后再执行。

### 第三步：小角度运动

选择：

```text
5. 单个旋转轴绝对移动到指定角度
```

建议第一次测试输入：

```text
目标角度：0.5
最大允许角度变化：1.0
```

当前旋转轴换算关系：

```text
1 度 = 200 counts
0.5 度 = 100 counts
5 度 = 1000 counts
90 度 = 18000 counts
180 度 = 36000 counts
```

### 第四步：两轴联动

选择：

```text
7. 旋转两轴绝对移动到指定角度
```

建议先用小角度，例如两个轴都输入：

```text
0.5
```

### 第五步：大角度测试

不要直接一次性跳到 90 度或 180 度。

选择：

```text
8. 单个旋转轴分段大角度移动
```

建议每段角度输入：

```text
5
```

或：

```text
10
```

这样可以降低 `POSITION_ERR` 风险。

## 4. 直线轴测试

直线轴相关功能在菜单中：

```text
10. 查看直线轴状态
11. 直线轴回零
12. 直线轴安全移动（counts 或 mm）
```

如果还不知道直线轴的 `counts_per_mm`，选择不使用 mm 测试，先用 counts 模式。

建议第一次直线轴 counts 测试：

```text
直线轴号：3
目标位置：100 counts
最大允许移动：200 counts
```

如果已经知道 `counts_per_mm`，可以选择 mm 测试，例如：

```text
counts_per_mm：50000
目标位置：1.0 mm
最大允许移动：2.0 mm
```

菜单 10、11、12 共用的默认参数现在是 `counts_per_mm=50000.0`、软件最大行程 `15.0 mm`。提示示例也是 `50000`。这些默认值只用于初始化输入，仍必须以实际直线平台参数和机械行程为准，不能仅凭默认值直接运动。

## 5. 常见状态说明

```text
HOME_MISSING
```

轴未回零。需要确认机械安全后执行回零。

```text
POSITION_ERR
```

位置误差。通常发生在手动转动、运动过大、机械阻力过大或未正确回零后。可以先停止，再重新回零。

```text
MOTOR_RUNNING
```

电机正在运动。等待运动完成，或执行停止。

## 6. 常见软件问题

### 提示 pyserial 未安装

如果菜单提示：

```text
pyserial 未安装
```

先关闭菜单窗口，然后双击：

```text
install_deps.bat
```

如果仍然失败，打开命令行进入本文件夹，手动执行：

```text
python -m pip install -r requirements.txt
```

注意文件名是 `requirements.txt`，不要写成 `requrement.txt`。

### 输入端口号后提示 Permission denied

旧版本会尝试把配置写到当前目录，如果文件夹没有写权限，可能出现：

```text
Permission denied: tula_windows_config.json
```

当前版本已彻底取消串口配置文件，不会写入 `tula_windows_config.json`。如果仍看到该错误，说明启动的是旧文件夹或旧压缩包，请删除旧副本后重新解压最新 zip。

### 运动后出现 32776 / 0x8008

`32776 = 0x8008 = MOTOR_RUNNING + POSITION_ERR`。TD-201 在运动尚未到位时可能暂时报告位置偏差；项目 C SDK 的 `td201.h` 也注明运动中不把 `POSITION_ERR` 判为致命错误。

旧 Python 等待逻辑会在第一次读到该状态时立即发送 `st`，提前结束运动。2026-10-17 修复后的逻辑为：

- 只有同一轴仍处于 `MOTOR_RUNNING` 时，暂时容许 `POSITION_ERR`；单轴和双轴等待均适用。
- 停止后若仍有 `POSITION_ERR`，继续停止并报错。
- 编码器、Z 相、过温、自动调谐、命令及参数错误仍会触发停止。
- 持续运动仍受原有超时约束；运动前检查和最终位置容差没有放宽。

例如目标 30° 对应 6000 counts，容差为 10 时，最终位置 6010 可通过，6011 不通过。日志中的 `ma 6000` 回显只表示返回了目标值，是否到位仍以停止后的 `cp` 位置检查为准。

更新后先退出旧菜单，再用 `MiRobot` 环境重新启动，才能加载修改后的代码。先用功能 2 读取状态；状态正常且已回零后，功能 5 可先测试 0.5°、最大允许角度变化 1°、容差 10、不自动回到 0°。这是绝对目标，请先确认当前位置；若与 0.5° 相差超过 1°，预检会拒绝执行，应根据当前位置选择相邻目标。小角度验证通过后，再按功能 8 分段测试大角度。

本次离线测试覆盖 `0x8008 → 0` 正常完成、`0x8008 → 0x0008` 报错、混合其他错误、双轴分别停止、超时和最终容差，完整测试共 28 项通过。真实硬件运动尚待实机确认，不能据此认定任何 `POSITION_ERR` 都是暂态。

离线测试命令（不连接真实串口）：

```powershell
conda activate MiRobot
Set-Location 'D:\@MiRobot\TULA_Python_Test_Windows'
python -m unittest discover -s tests -v
```

项目 Git 恢复说明见根目录 `GIT_RECOVERY.md`。原版标签为 `before-position-err-fix-20261017`，修复标签为 `position-err-fix-20261017`。

### 端口号输入规则

一次只能输入一个端口号：

```text
COM4
COM15
```

不要输入：

```text
COM4 COM5
```

如果设备管理器显示 `COM15`，菜单里直接输入 `COM15` 即可，程序会自动处理 Windows 高位串口格式。

## 7. 注意事项

- 测试前关闭串口助手和 PC Manager。
- 同一时间只能有一个软件占用串口。
- 第一次测试只做只读状态，不要直接运动。
- 回零前确认线缆、机械结构和限位安全。
- 大角度运动使用分段移动，不建议一次性大跳转。
- 直线轴测试必须先确认轴号、行程方向、行程范围和回零安全。
