# 05 环境、构建与部署

[返回 README](../../README.md) · [上一章](04_file_reference.md) · [下一章](06_testing_and_safety.md)

## 最小环境

- 使用随附库：Windows x64、64 位 Python。FFI 示例只用 ctypes、pathlib 和 sys，不需 NumPy、PyYAML 或 LeRobot。
- 重建时才需要 Windows x64 GCC/MinGW-w64。将工具链加入 PATH，检查 `where.exe gcc` 和 `gcc -dumpmachine`。VS Code 工作区打开 SDK 根目录，GDB 调试还需 PATH 中有 gdb。
- 实机才需要 USB 串口驱动和已核对的 COM、波特率、轴地址。示例默认值不代表现场配置；不要为了验证工程路径而开串口。

## 路径与产物

- 两个 VS Code 任务使用 `${workspaceFolder}` 锚定输入和输出。测试任务固定编译 tests/test_hardware_c.c，不取当前编辑文件。GDB 启动配置指向同一 EXE。
- [README 中的构建命令](../../README.md)适用于 SDK 根目录。已有 GNU Make 时，[Makefile](../../Makefile)提供等价的 dll 与 c-test 目标，亦可用 make -C 指定根目录。
- td201.dll 是运行时库，libtd201.a 是链接导入库。C 测试编译直接包含 SDK 源码；不会为运行而依赖 DLL。不要运行其 EXE 验证编译。
- FFI 按自身文件位置加载 DLL，不依赖 cwd、源目录、兄弟项目或将库目录加到 PATH。加载与执行硬件测试应分开。
- DLL 已存在时不必先编译；重建会覆盖 DLL 和导入库，建议用独立副本。检查 Python 位数、DLL 是否存在、架构及导出名，不要通过改库名绕过错误。

## 已有验收边界

交接基线此前在同一台 Windows 11 x64 机器的独立副本上，用 GCC 16.1.0 构建 DLL、导入库与 C 测试 EXE，并用 Python 3.8.5 x64 验证 DLL 加载和不同 cwd 的路径。该记录不是本目录重新构建的结果，不证明实机或 Linux 可用。本次独立整理保留原二进制，不交付旧 EXE、目标文件或上层适配。
