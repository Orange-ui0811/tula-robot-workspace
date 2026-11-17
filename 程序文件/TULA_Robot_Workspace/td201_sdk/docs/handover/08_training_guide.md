# 08 新员工培训提纲（40分钟）

[返回 README](../../README.md) · [上一章](07_current_status_and_limitations.md)

采用读代码、看协议和查看已有验收记录的形式，不连接电机、不运行硬件程序。展示“命令长什么样”不等于发送该命令。

> 历史交接背景：下文提及的 Tula/LeRobot 适配源码不随独立 SDK 分发。它们不是本目录的运行依赖或可执行入口。独立 SDK 以 [README](../../README.md) 和[测试与安全](06_testing_and_safety.md)为准。

## 时间安排

| 时间 | 主题与目标 | 展示文件 | 核心概念 | 应理解的结论 |
|---|---|---|---|---|
| 0～5分钟 | 硬件组成和控制器工作原理 | [02硬件章](02_hardware_and_protocol.md)、TD-201技术规格第2页 | 板卡、TULA、转台、ABZ/QEI、PID/PWM | PC给目标，板内闭环驱动；两只TULA不等于两个转台轴 |
| 5～9分钟 | ASCII协议 | 命令参考手册；命令表G3/H3、G14/H14 | 轴号、ma/cp、回车、回显/到位 | ASCII是帧编码，目标回显不证明到位 |
| 9～14分钟 | C SDK | [td201.h](../../hardware/include/td201.h)、[td201.c](../../hardware/src/td201.c)、[tula50.c](../../hardware/src/tula50.c) | 设备/轴句柄、事务、错误码、200换算 | 串口/协议在C，角度换算是单独层；注释需核对实现 |
| 14～18分钟 | ctypes | `td201_motor.py` | argtypes/restype、指针、long/double、库路径 | import加载DLL；connect才开端口；API只封装子集 |
| 18～23分钟 | 多轴控制 | `tula_robot.py` | active_axes、write、set_angles、生命周期 | 数组顺序对应轴号；默认write不等到位；connect默认home |
| 23～27分钟 | LeRobot包装 | `tula_lerobot_env.py`、[07状态章](07_current_status_and_limitations.md) | send_action、capture_observation、当前官方Robot差异 | 原型包装不是正式注册；YAML不是所有字段都生效 |
| 27～32分钟 | 环境、构建和迁移 | [05环境章](05_environment_and_build.md)、[tasks.json](../../.vscode/tasks.json) | PATH、x64、DLL/导入库、C测试直接链接 | 3.8.5只证明SDK加载；LeRobot另需>=3.12；构建不运行 |
| 32～37分钟 | 测试和安全 | [06安全章](06_testing_and_safety.md)、联调参数解析 | dry/live、skip-swing、回零、退出不等于停机 | 编译/加载/离线/硬件验收边界不同 |
| 37～40分钟 | 完成度与下一步 | [07状态章](07_current_status_and_limitations.md) | 缺口、证据、待确认清单 | 先确认硬件/版本/安全，再制定适配和实机验收任务 |

缩为30分钟时减少C内部事务细节和FAQ；扩为45分钟时用5分钟让新员工口头追踪action与cp链路，不加入实机演示。

## 推荐代码阅读顺序

1. tula_config.yaml：哪些轴、哪个端口；随后看_load_config确认只消费了哪些字段。
2. tula_lerobot_env.py：上层如何组装对象、动作和观测的真实结构。
3. tula_robot.py：connect/home、active_axes顺序、read/write与set_angles区别。
4. td201_motor.py：设备/轴对象、C函数映射及错误转换。
5. tula50.c：角度到counts、计数范围与机械限位的区别。
6. td201.h/td201.c：设备、事务、format_cmd、ma/cp、状态和超时的真实行为。
7. tasks.json及测试文件：如何构建，以及哪些入口会接触硬件。

## 常见问题

### 为什么不能让LeRobot直接调用DLL？

技术上可以自行写ctypes调用，但LeRobot需要对象生命周期、配置、动作/观测、标定和安全接口。DLL只提供设备/轴级C API；直接调用意味着仍要实现这些桥接工作。不是LeRobot在技术上禁止DLL。

### 为什么需要TulaRobot？

它聚合一个总线和多个TD201Motor，定义数组元素与轴号的顺序，集中处理连接和读取，并提供可选多轴到位轮询。上层无需重复处理每轴对象，但这层目前没有完整机械限位或停机保障。

### ASCII意味着控制频率一定很低吗？

不一定。实际周期取决于波特率、帧长、逐轴请求数、驱动缓存、回复、超时和系统调度。当前有50Hz目标压测脚本，没有本套文档可引用的硬件性能验收；不能由脚本目标或C注释承诺实时频率。

### 为什么需要回零？

增量编码器需要机械参考；上电HOME_MISSING表示原点未知。hm建立参考，会产生真实运动。回零不等于写一个0，也不等于已完成LeRobot标定。

### 为什么DLL加载成功不代表控制正常？

加载只证明系统能解析库、位数和依赖基本匹配。它没有证明端口、地址、固件协议、编码器比例、回零方向、机械行程或运动到位。此前加载验收未调用任何电机函数。

### 当前已经正式接入LeRobot了吗？

没有。TulaLeRobot是自定义原型，缺当前RobotConfig/注册及完整Robot接口。官方工厂和record/replay/teleoperate未验收。本地LeRobot目录里的另一个Tula副本也不会自动接收本工程更新。

### disconnect或Ctrl+C能安全停止吗？

不能保证。disconnect不发送stop，控制器可能继续已收到的动作；异常时应使用现场已确认的急停/安全断电流程。

### YAML里enable_limit_check=true为什么还要确认限位？

因为_load_config没有消费safety字段；±90°空间描述也未被write使用。不能把配置存在当作保护生效。

## 培训结束检查

请新员工说明：action[0]对应哪个轴；角度在哪里变成计数；ma成功为什么不代表到位；connect为什么有运动风险；哪个产物给Python加载；SDK与LeRobot为什么要分环境；下一步需要哪些实机参数。回答应能定位回代码和本套文档，而非记住推测值。
