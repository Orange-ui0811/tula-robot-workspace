# 03 软件架构与调用链

[返回 README](../../README.md) · [上一章](02_hardware_and_protocol.md) · [下一章](04_file_reference.md)

> 历史交接背景：下文提及的 Tula/LeRobot 适配源码不随独立 SDK 分发。它们不是本目录的运行依赖或可执行入口。独立 SDK 以 [README](../../README.md) 和[测试与安全](06_testing_and_safety.md)为准。

## 分层

```text
自定义程序 / 尚待适配的正式LeRobot工具链
  ↓ ndarray角度action
TulaLeRobot.send_action()
  ↓
TulaRobot.write()
  ↓ action[i] → active_axes[i]
TD201Motor.write_position()
  ↓ ctypes _LIB.tula50_set_angle(axis*, double)
hardware/libs/td201.dll
  ↓ tula50_set_angle() → td201_move_absolute()
  ↓ td201_transaction() → send_and_recv() → format_cmd()/serial_write()
Win32 COM → >NNma counts\r → TD-201 → 执行机构
```

这是一条源码可追踪的调用链，不是官方LeRobot端到端通过证明。正式工厂到TulaLeRobot的连接仍缺失。

| 层/文件 | 为什么存在、负责什么 | 上下层数据 |
|---|---|---|
| `tula_lerobot_env.py` / TulaLeRobot | 将自定义硬件封装成LeRobot风格动作、观测和空间描述；不是协议层 | 输入ndarray角度；输出观测字典 |
| `tula_robot.py` / TulaRobot | 一个总线管理多个软件轴，维护active_axes顺序，聚合读取/下发 | 角度数组、轴ID到角度的dict |
| `td201_motor.py` / TD201MotorBus | 持有物理串口设备指针、连接状态 | port编码为bytes，baud为int，dev_ptr为void* |
| 同文件 / TD201Motor | 单轴绑定、角度读取、计数读取、回零和位置下发；把错误码转Python异常 | axis结构、double度、long计数 |
| ctypes | 声明C参数和返回类型，传指针/输出参数；不理解机械行程 | uint8、void*、double、long、int |
| [tula50.c](../../hardware/src/tula50.c) | 隔离物理单位与协议计数 | degree与200 counts/degree；通用pulses_per_unit |
| [td201.c](../../hardware/src/td201.c) | 平台串口、帧格式、回复处理、设备状态API及参数指令 | 设备句柄、轴句柄、ASCII帧 |
| TD-201固件/硬件 | 本仓库之外，完成实际驱动和编码器闭环 | 串口命令到电气/机械动作 |

TulaRobot管理多轴；C td201_dev_t持有串口，td201_axis_t把地址绑定到设备。没有全局单一串口的强制设计；Python模块全局_LIB是库句柄，不是已连接的设备。共用串口的并发调用没有线程锁保障，不能把“事务原子化”注释当成线程安全承诺。

## 对象生命周期

1. import td201_motor：按文件位置加载DLL并设置9个C函数的argtypes/restype，不开串口。
2. 创建TulaLeRobot/TulaRobot：组装bus、单轴对象和空间元数据，尚未连接。
3. connect：TulaLeRobot透传；TulaRobot打开串口、等待1.5秒、逐轴setup，默认逐轴home(timeout_ms=6000)。全部成功后才设置整机is_connected=True。
4. read/write/set_angles：要求整机已连接；失败通常以异常或False返回，具体见下文。
5. disconnect：解绑并关串口，不发stop。若连接中途失败且整机标志仍False，disconnect可能提前返回，不能假定总能清理部分连接。

skip_home=True只能由了解现场状态的调用者选择，不能作为掩盖回零失败的办法。

## 一次动作如何执行

假设active_axes=[1,2]，上层action=np.array([10.0,-5.0])：表示地址1的绝对10°和地址2的绝对-5°。不是“增量10和-5”。此例仅解释数据，不是推荐实机目标。

| 步骤 | 文件与方法 | 处理和结果 |
|---|---|---|
| 1 | TulaLeRobot.send_action(action) | 将ndarray透传给_hardware.write，返回None |
| 2 | TulaRobot.write(action) | 检查连接及数组长度；按active_axes顺序逐轴float转换 |
| 3 | TD201Motor.write_position(deg,timeout_ms=5000) | 检查绑定，调用tula50_set_angle；timeout_ms是保留参数，内部不等待到位；非0抛IOError |
| 4 | tula50_set_angle | 角度×200并取整；检查控制器计数范围，不检查机械±90° |
| 5 | td201_move_absolute | 将counts转换为参数字符串，发送ma；echo_pos当前未被填充 |
| 6 | td201_transaction/send_and_recv | 清空RX、拼帧、serial_write；ma的resp=NULL，因此不等目标回显或实际完成 |

当前例中的计数为2000和-1000；发送格式来自[协议章](02_hardware_and_protocol.md)。成功返回只证明相应写入路径未报错，不证明控制器接受、坐标正确或运动到位。

### 多轴到位等待不是默认write

TulaRobot.set_angles({axis_id:degrees}, timeout=10.0, tolerance_counts=15, poll_hz=50.0)是另一个入口：先set_angle_async逐轴下发，再get_position轮询所有参与轴，按计数误差判到位；超时返回False并记录warning，不自动发stop。没有状态字保护或运动同步时钟。

群发仍经过同一串口串行发送，不是硬件严格同时起动。方法注释的“<1ms/轴”“工业级同步”没有本次实测支持；50Hz是轮询目标，读串口耗时也计入实际周期。

## 读取如何返回

```text
TulaLeRobot.capture_observation()
 → TulaRobot.read()
 → TD201Motor.read_position()
 → tula50_get_angle()
 → td201_get_position() → cp事务 → 当前counts
 → counts/200 → Python float degree
 → np.float32数组 → observation.state
```

capture_observation还返回空的observation.state.leader，以及state.copy()作为action。这个action是当前状态副本，不是上一次命令历史或真正leader示教动作。TD201Motor.get_position()返回原始计数，供set_angles轮询。

## 跨语言边界

_TD201AxisStruct对应C td201_axis_t：uint8 axis_id和设备指针。错误类型通常为C int；dev是opaque void*；位置输出是long*；角度输出是double*。ctypes.byref把输出参数地址传入。已有Windows x64验收中long=4字节、指针=8字节、axis结构16字节。

回零使用td201_home_wait；虽然声明了tula50_set_angle_wait，当前write_position实际调用的是非等待版。Python尚未封装C层的完整报警、stop、配置和安全回零功能。

## 两条路线与LeRobot边界

外层TULARobot/TULAMotorsBus/TULAController是另一组大小写和实现不同的类，本章只讨论TulaRobot/TD201Motor/TulaLeRobot。没有pyserial依赖。

本地LeRobot的Robot要求RobotConfig、observation_features/action_features、get_observation、calibrate/configure等；当前包装使用旧可选基类路径并可退化成object。详细缺口见[状态与限制](07_current_status_and_limitations.md)，不能把“风格接近”说成“完全兼容”。
