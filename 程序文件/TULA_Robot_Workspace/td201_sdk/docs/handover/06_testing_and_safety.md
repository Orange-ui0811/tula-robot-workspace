# 06 测试与安全

[返回 README](../../README.md) · [上一章](05_environment_and_build.md) · [下一章](07_current_status_and_limitations.md)

| 入口 | 用途 | 安全边界 |
|---|---|---|
| [test_hardware_c.c](../../tests/test_hardware_c.c) | C SDK 交互诊断源码 | 可只编译；运行生成的 EXE 会打开串口，菜单能回零、运动、改参数 |
| [test_td201_ffi.py](../../tests/test_td201_ffi.py) 的 load_td201_library | ctypes 加载并声明函数签名 | 只调用加载器不打开串口，不调用 TD-201 导出函数 |
| 同文件的 main | 连接、绑定轴并读取角度 | 即使不下发运动也会打开真实串口，不属于离线检查 |
| VS Code GDB 启动配置 | 先构建再运行 C 测试 | 不是编译检查；不要为检查路径而按 F5 |

本目录不含 LeRobot 联调或压力测试，不需 NumPy/PyYAML。编译通过、DLL 可加载与真实硬件行为通过是三回事。

任何获授权的实机测试开始前，确认控制器、端口、轴号、波特率、机械行程与回零方向，关闭占用同一端口的厂商工具，安排可靠急停。接拔转台线缆前切断主电源。异常时按现场安全规程停机，不能把 Ctrl+C 或关串口当作急停。
