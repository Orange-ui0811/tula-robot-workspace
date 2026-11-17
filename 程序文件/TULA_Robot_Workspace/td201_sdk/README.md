# TD-201 C SDK（Windows x64）

本目录是独立的 TD-201 C SDK。它包含串口协议和控制 API、TULA 物理量换算、原有 Windows x64 二进制及 C/Python 诊断示例。无需原始交接包、LeRobot、Tula 适配层或 pyserial。

| 目录 | 内容 |
|---|---|
| [hardware/include](hardware/include) | SDK 公开头文件 |
| [hardware/src](hardware/src) | 两份 C 实现 |
| [hardware/libs](hardware/libs) | td201.dll（运行时）及 libtd201.a（GCC 导入库） |
| [tests](tests) | C 硬件诊断源码和 Python ctypes FFI 示例 |
| [.vscode](.vscode) | 构建与调试任务 |
| [docs](docs) | 协议、规格及交接资料 |

## 环境

- 使用 Windows x64；Python FFI 需要 64 位 Python，与 DLL 位数一致。FFI 只用标准库，无需安装额外 Python 包。
- 在 TULA 工作区内可复用根目录 `.venv` 的 CPython 3.12.13 x64；SDK 独立使用时不依赖 LeRobot、Tula 插件或该虚拟环境。
- 仅在需要重新构建时准备 x64 GCC/MinGW-w64，将 bin 加入 PATH。用 `gcc -dumpmachine` 确认是 Windows x64 目标，例如 `x86_64-w64-mingw32`。
- VS Code 可选：将本目录作为工作区，C 构建/调试使用 C/C++ 扩展，GDB 通过 PATH 查找。
- SDK 源码有 POSIX 分支，但此目录不交付 Linux 动态库，本次不做 Linux 移植。

## 使用随附 DLL

头文件见 [td201.h](hardware/include/td201.h) 和 [tula50.h](hardware/include/tula50.h)。[test_td201_ffi.py](tests/test_td201_ffi.py) 是 ctypes 声明和读角度示例，不是安装包或完整机器人 SDK。其 `load_td201_library()` 按 `Path(__file__).resolve().parents[1]` 查找本目录的 `hardware/libs/td201.dll`，与启动工作目录无关；调用方仍须先正确找到 Python 模块。

**不要直接执行 FFI 脚本来验证加载。** 它的 `main()` 会打开串口。若只检查 DLL，应只调用加载函数，不调用电机 API。完整测试边界见[测试与安全](docs/handover/06_testing_and_safety.md)。

## 测试文件与串口配置

| 文件 | 用途与边界 |
|---|---|
| [test_hardware_c.c](tests/test_hardware_c.c) | 交互式诊断源码，可只编译。生成的 EXE 会打开串口，菜单包含回零、运动和波特率修改 |
| [test_td201_ffi.py](tests/test_td201_ffi.py) | 通过 ctypes 调用 DLL 的最小示例；加载函数只绑定签名，脚本 `main()` 会打开串口、绑定轴并读角度 |

C API 用设备与轴句柄管理串口，Python ctypes 映射结构体和函数签名，调用的仍是 DLL 内同一套 C API。只检查随附 DLL 时，可在 **SDK 根目录**运行：

```powershell
python -B -c "import runpy; runpy.run_path('tests/test_td201_ffi.py')['load_td201_library'](); print('TD-201 DLL load OK')"
```

该命令不执行 `main()`，不调用任何电机函数。传入脚本完整路径时，也可以从别的工作目录启动；库路径始终由脚本位置推导。

实机诊断前，从设备管理器确认实际 `COMx`，再核对驱动器的波特率和轴地址。Windows SDK 接收 `COMx` 并自行加设备前缀，配置 8 数据位、1 停止位、无校验。C 测试启动时可输入串口，默认 COM5、初始波特率 115200，绑定软件轴 1/2/3；绑定不证明实物上有三个轴。FFI 示例中的 `PORT_NAME`、`BAUDRATE`、`AXIS_ID` 默认是 COM5、115200、1，没有 CLI 覆盖参数。

**先读[测试与安全](docs/handover/06_testing_and_safety.md)及工作区的[实机测试计划](../HARDWARE_TEST_PLAN.md)，再由获授权人员连接设备。** 确认平台行程、轴地址、回零路径和急停，关闭占用 COM 的工具；不要用默认值试探硬件。关闭串口或退出程序不等于停机。C 菜单第 1 项只查询双轴信息和位置，第 0 项退出；第 2～5 项可能引发运动，第 6 项修改设备运行时波特率。

## 后续构建入口

在根目录打开 VS Code，运行 `Build td201 DLL` 或 `Build C Test Executable`。DLL 任务输出 `hardware/libs/td201.dll` 和 `hardware/libs/libtd201.a`；C 测试任务把 SDK 源码直接编进 `tests/test_hardware_c.exe`，不使用导入库。

不用 VS Code 时，在本目录执行下面对应命令。它们会写入构建输出；如需保留随附二进制，请在另一个副本中构建。

```powershell
gcc -fdiagnostics-color=always -g -shared -Ihardware/include hardware/src/td201.c hardware/src/tula50.c -o hardware/libs/td201.dll "-Wl,--out-implib,hardware/libs/libtd201.a"
gcc -fdiagnostics-color=always -g -Ihardware/include tests/test_hardware_c.c hardware/src/td201.c hardware/src/tula50.c -o tests/test_hardware_c.exe
```

如已有 GNU Make，也可执行 `make dll` 或 `make c-test`，不需要为此安装 Make。**构建与运行是两件事**：F5/GDB 会运行硬件测试程序，不能用作只编译检查。

## 阅读入口

- [01 项目概览](docs/handover/01_project_overview.md) · [02 硬件与协议](docs/handover/02_hardware_and_protocol.md)
- [04 文件索引](docs/handover/04_file_reference.md) · [05 环境与构建](docs/handover/05_environment_and_build.md) · [06 测试与安全](docs/handover/06_testing_and_safety.md)
- [03 架构](docs/handover/03_software_architecture.md)、[07 状态与限制](docs/handover/07_current_status_and_limitations.md)、[08 培训](docs/handover/08_training_guide.md)保留交接时期的上层背景。上层适配代码及其联调测试不随本 SDK 分发。
