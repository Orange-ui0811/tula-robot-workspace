# 04 文件职责索引

[返回 README](../../README.md) · [上一章](03_software_architecture.md) · [下一章](05_environment_and_build.md)

以下路径均相对本项目根目录。可先读 FFI 示例及公开头文件，再按需要追踪 C 实现。

## 核心、配置和二进制

| 相对路径 | 主要职责 | 关键类/函数 | 依赖关系 | 是否直接涉及硬件 |
|---|---|---|---|---|
| [hardware/include/td201.h](../../hardware/include/td201.h) | SDK公开类型、错误码、状态掩码、通信/运动/配置API | td201_dev_t、td201_axis_t、td201_err_t、td201_alarm_t、td201_info_t | 被C源及测试include | 声明本身不操作 |
| [hardware/src/td201.c](../../hardware/src/td201.c) | 设备资源、Win32/POSIX串口、帧、回复过滤、运动和配置实现 | td201_open/close、serial_write、format_cmd、send_and_recv、td201_transaction、td201_get_position/alarm/info、home_wait、safe_home_wait、set_* | td201.h、系统API；被tula50及测试调用 | 调用相关API会读写设备 |
| [hardware/include/tula50.h](../../hardware/include/tula50.h) | 角度与通用物理量接口 | tula50_set_angle[_wait]、get_angle、move_physical_wait/get_physical | include td201.h；对应tula50.c | 声明不操作 |
| [hardware/src/tula50.c](../../hardware/src/tula50.c) | 角度/计数换算及计数范围检查 | 固定200、通用pulses_per_unit | tula50.h、math.h、td201_* | 调用会下发或读取 |
| [hardware/libs/td201.dll](../../hardware/libs/td201.dll) | Windows x64运行时C SDK | 51个导出名；随附 FFI 示例声明其中4个 | 对应两份C源；ctypes加载 | 加载不连接，调用控制API才操作 |
| [hardware/libs/libtd201.a](../../hardware/libs/libtd201.a) | GCC链接导入库 | 指向td201.dll的导入符号 | 与DLL同任务输出；Python不加载；当前C测试不使用 | 只链接 |

## 测试文件：不是随意可运行的单元测试

| 相对路径 | 主要职责与关键入口 | 导入/调用关系 | 是否直接涉及硬件 |
|---|---|---|---|
| [tests/test_hardware_c.c](../../tests/test_hardware_c.c) | main交互终端，绑定1/2/3，配置/状态、开环、回零、双轴、波特率及Z轴测试 | td201.h、tula50.h；直接调用C SDK | 运行即尝试串口；菜单可运动/改参数 |
| [tests/test_td201_ffi.py](../../tests/test_td201_ffi.py) | 最小Python/C示例，TD201Axis、load_td201_library、main | ctypes/sys/pathlib；从源码位置加载DLL，main打开COM5绑定轴1并读角度 | main开串口；无主动运动调用，但不是离线测试 |

FFI 示例只用标准库；导入不连接设备，执行 main 会开串口。详见[测试分类](06_testing_and_safety.md)。

## 构建、文档和历史文件

| 路径 | 作用/依赖 | 是否硬件入口 |
|---|---|---|
| [.vscode/tasks.json](../../.vscode/tasks.json) | 两个gcc任务：正式DLL+导入库、固定C测试源+SDK源的EXE；workspaceFolder定位 | 只构建 |
| [.vscode/c_cpp_properties.json](../../.vscode/c_cpp_properties.json) | gcc通过PATH、windows-gcc-x64智能感知 | 否 |
| [.vscode/launch.json](../../.vscode/launch.json) | Python当前文件运行；GDB先构建后运行固定的C测试EXE | 调试会执行程序，不是只编译 |
| [.vscode/settings.json](../../.vscode/settings.json) | C_Cpp_Runner工具/告警设置，useMsvc=false；独立扩展选项不等于tasks参数 | 否 |
| [Makefile](../../Makefile) | 独立 SDK 的 GNU Make 入口，dll/c-test 与 VS Code 构建任务对应 | 只构建 |
| [README.md](../../README.md) | 入口、快速开始及交接索引 | 文档 |
| [docs/handover](.) | 01概览、02硬件、03架构、04索引、05环境、06安全、07限制、08培训 | 文档 |
| [docs/TULA_command_list.xlsx](../TULA_command_list.xlsx) | 协议原始命令/参数/示例；只读资料 | 否 |
| [docs/TD-201命令参考手册.pdf](../TD-201命令参考手册.pdf) | 帧、通信、状态 | 否 |
| [docs/TD-201技术规格.pdf](../TD-201技术规格.pdf) | 板卡结构、接口、编码器、供电 | 否 |
| [docs/驱动器技术资料.pdf](../驱动器技术资料.pdf) | 具体转台和控制单元截图 | 否 |
| [docs/转台图纸资料.pdf](../转台图纸资料.pdf) | 转台规格及图纸，与另一资料有冲突 | 否 |
| [docs/_pdf_extract.txt](../_pdf_extract.txt) | 历史PC Manager手册文字提取，含乱码 | 否 |

独立 SDK 不包含 LeRobot 适配或包安装定义；C 测试 EXE 由构建任务生成，不随目录交付。
