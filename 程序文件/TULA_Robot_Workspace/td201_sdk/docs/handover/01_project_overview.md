# 01 项目概览

[返回 README](../../README.md) · [下一章](02_hardware_and_protocol.md)

> 历史交接背景：下文提及的 Tula/LeRobot 适配源码不随独立 SDK 分发。它们不是本目录的运行依赖或可执行入口。独立 SDK 以 [README](../../README.md) 和[测试与安全](06_testing_and_safety.md)为准。

## 目的和边界

本工程解决“PC 应用如何使用 TD-201 控制器”。PC 发送位置目标、配置和查询；板卡接收编码器反馈并驱动执行机构。本仓库不是 TD-201 固件，也不在 Python 中实现板内 PID/PWM。

当前路线：C SDK → ctypes → TulaRobot → 自定义 TulaLeRobot。外层目录另有纯 Python/pyserial 实现，与本工程不互相 import。不能把外层安全移动、直线轴菜单或28项FakeSerial测试算作本工程的能力或验收。

## 已完成的工作

| 层次 | 代码已经存在 | 尚不能宣称 |
|---|---|---|
| C SDK | 设备句柄、轴绑定、ASCII事务、状态/位置读取、闭环/开环命令、回零和配置 | 全部API实机通过 |
| 物理量层 | 固定200 counts/degree及通用pulses_per_unit换算 | 任意平台均适用同一比例 |
| Python SDK | 9个常用C函数的ctypes声明、总线/单轴对象 | Python已封装全部C功能 |
| TulaRobot | 多轴read/write，可选set_angles群发后轮询 | 硬件级同步、线程安全、稳定50Hz |
| TulaLeRobot | ndarray动作、观测字典、YAML组装、空间描述 | 正式LeRobot录制/回放/遥操作已接通 |
| 工程 | 路径整理、统一DLL命名、独立副本构建和加载 | 已在另一台电脑或真实电机验收 |

主要证据：[td201.h](../../hardware/include/td201.h)、`td201_motor.py`、`tula_robot.py`、`tula_lerobot_env.py`。

## 证据怎么读

- **源码事实**：以实际函数体和分支为准，不能仅依赖注释。
- **历史验收事实**：以编译退出码、PE信息、导出名单和哈希为准；只覆盖构建和加载。
- **合理推断**：解释硬件工作机理时标出适用前提，不代替现场接线、型号和固件确认。
- **待确认**：没有铭牌、版本、实机日志或一致规格支持的信息。

厂商辅助资料包含内部整理的中文PDF和旧截图，不应默认同一修订版。规格冲突见[硬件与协议](02_hardware_and_protocol.md)。

## 当前验收基线

前序验收在另一个独立副本进行；本工程不依赖该副本。证据记录显示：DLL和C测试EXE构建退出码0；Python3.8.5 x64从4个cwd加载副本新DLL；新旧51个导出名称一致；原项目40文件哈希不变。

本轮只读取记录并写文档，没有重跑构建、加载或硬件测试。完整环境和哈希见[环境与构建](05_environment_and_build.md)。

## 新员工第一天目标

1. 区分控制器、执行机构和机械转台。
2. 能从action追踪到ma帧，从cp追踪回角度。
3. 知道import、connect、home、write分别何时发生。
4. 能区分编译、加载和硬件验收。
5. 实机前读完[安全指南](06_testing_and_safety.md)和[当前限制](07_current_status_and_limitations.md)。
