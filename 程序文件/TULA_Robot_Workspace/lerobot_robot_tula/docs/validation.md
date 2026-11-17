# 第二阶段验收（2026-11-04）

- 目标：LeRobot `ba83e4cf43737e2665be0aafcb5f513b83c7d0f3`（0.6.2），
  Windows x64 Python 3.12.13，draccus 0.11.6。
- 从该提交的单独源码快照构建 LeRobot，在临时环境中安装并运行验证；
  环境复用本机已有第三方依赖，不代表全新机器的完整依赖安装验收。
  本地原 LeRobot checkout、原 Python 环境和 SDK 未改动。
- 构建并安装 `lerobot_robot_tula-0.1.0-py3-none-win_amd64.whl`。
  wheel 内 DLL 与 SDK 原件的 SHA-256 一致；未重新编译。
- 从项目外运行 `python -B -m unittest discover -s <插件目录>/tests -v`，13 项通过。
  新进程在禁止 ctypes.CDLL 的情况下，用真实 LeRobot 自动发现、draccus 解析
  `--robot.type=tula_robot` 及限位，再由 make_robot_from_config 创建 Robot。
- 其余测试用假驱动验证双轴映射、counts/度数、连接/断开、逐轴发送间隔、
  不等待到位、未回零与报警拒绝、范围与非有限值拒绝、部分失败清理。
- 未加载或调用真实 TD-201 DLL、未打开串口、未执行真实回零或运动。
  尚未验证真机行为、实际周期延迟、完整 teleoperate/record 与 Linux。
