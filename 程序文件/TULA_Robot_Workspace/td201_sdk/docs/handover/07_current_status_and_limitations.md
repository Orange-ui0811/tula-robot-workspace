# 07 当前状态、限制与待确认事项

[返回 README](../../README.md) · [上一章](06_testing_and_safety.md) · [下一章](08_training_guide.md)

> 历史交接背景：下文提及的 Tula/LeRobot 适配源码不随独立 SDK 分发。它们不是本目录的运行依赖或可执行入口。独立 SDK 以 [README](../../README.md) 和[测试与安全](06_testing_and_safety.md)为准。

## 完成度矩阵

“已实现”指代码存在，不表示所有分支经实机验证；“验收通过”只用于已有明确测试记录。

| 项目 | 状态 | 依据与边界 |
|---|---|---|
| C串口/ASCII/API | 已实现 | td201.c/h有连接、轴、事务、查询、运动、回零、开环和配置；Windows交付物可构建 |
| TULA换算 | 已实现 | tula50.c固定200与通用pulses_per_unit；比例适用性需逐轴确认 |
| ctypes | 已实现且独立副本加载通过 | 9个函数声明，不等于全部C API已Python化 |
| 多轴read/write | 已实现 | TulaRobot按active_axes管理；write非阻塞，无机械限位检查 |
| 多轴set_angles | 已实现，实机未验收 | 群发后按cp误差轮询；默认10秒/15counts/目标50Hz；非硬件同步 |
| TulaLeRobot | 原型 | ndarray send_action、capture_observation、spaces/features、robot_type |
| calibration | 未完成正式集成 | 硬件home不等于LeRobot标定文件/持久化；本包装没有calibrate/is_calibrated |
| leader/follower | 部分结构占位 | leader_arms={}，follower_arms固定tula_arm；无示教数据链路 |
| camera | 未实现 | cameras={}，无图像观测 |
| 动作限位 | 未实现整机执行保护 | get_action_space_bounds返回±90°，但send_action/write不使用该边界裁剪 |
| RobotConfig注册 | 未完成 | 目标适配无当前RobotConfig子类和register_subclass |
| 官方Robot完整接口 | 不满足 | 见下方与本地基类对照 |
| 官方工厂/插件 | 未接通 | 无tula专用工厂分支，亦无匹配注册配置/插件入口 |
| lerobot-record/replay/teleoperate | 未验收且缺接口接入 | CLI存在于LeRobot不等于Tula可用 |
| Linux运行 | 未验证 | C含POSIX分支，未附.so；两加载器的非Windows库名也不一致 |

## YAML实际消费范围

`tula_config.yaml`和`包装加载器`的_load_config表明：

| 字段 | 定义 | 当前使用 |
|---|---|---|
| bus.port | COM5 | 用于打开总线 |
| bus.baudrate | 115200 | 用于总线配置 |
| axes[].axis_id | 默认1 | 构成active_axes，列表顺序决定action顺序 |
| axes[].name | joint_0 | 未消费；dof_names实际生成joint_1等，不能用此字段改名 |
| robot.leader_arms | {} | 未消费，代码固定空字典 |
| robot.follower_arms及axes索引 | tula_arm/索引0 | 未消费，代码自行构造tula_arm |
| safety.joint_limits_deg | ±90° | 未加载到动作检查；空间函数硬编码同值只是描述 |
| safety.max_torque_percent | 60 | 未消费，没有对应Python力矩控制 |
| safety.enable_limit_check | true | 未消费，不提供保护开关效果 |

load_robot_from_config()返回对象，不会自动connect；实际连接默认回零。测试脚本可用--port/--baudrate/--axes覆盖配置，但这不让未接入字段自动生效。

## 与当前本地LeRobot的差距

历史辅助检查对象是单独的 LeRobot 仓库，不是本 SDK 的运行依赖。

- src/lerobot/robots/robot.py当前构造需要RobotConfig，并要求observation_features、action_features、get_observation、is_calibrated、calibrate、configure、connect(calibrate=True)、send_action字典输入/返回等。
- 本工程TulaLeRobot尝试的可选基类是旧路径lerobot.common.robot_devices.robots.robot.Robot，不是上述当前路径。导入失败退化object；如果某旧基类存在，构造/抽象接口是否兼容仍需另验。
- 本工程使用capture_observation和ndarray action，缺当前所需方法，不能只改继承名就算适配。
- src/lerobot/robots/config.py使用draccus ChoiceRegistry。utils.make_robot_from_config没有tula分支，并有通用make_device_from_device_class回退；但Tula没有匹配的注册配置，回退也不能凭目录自动发现它。
- 当前CLI声明来自LeRobot pyproject.toml；没有证据支持直接使用--robot.type=tula_robot。
- LeRobot仓库robots/tula_robot内的Python和libs/td201.dll是另一组拷贝，没有当前工程的自动源码/库依赖。迁移整理和构建成果不会自动进入那个目录。

## 代码与注释/旧说明不一致的地方

| 位置 | 旧说法/容易误读 | 实际代码和培训结论 |
|---|---|---|
| td201.c事务注释 | 5ms、微秒级非阻塞、绝不影响50Hz | 宏12ms，ReadFile仍可阻塞；不是已测性能保证 |
| td201_move_absolute参数说明 | echo_pos可接回显 | 当前ma不接回复、不填echo_pos；成功不是到位 |
| td201.h enc_type | 2是绝对编码器 | 命令表是A/B/Z；需按协议理解 |
| td201.h kf | 前馈增益 | 命令表是IIR参数 |
| td201_get_alarm头文件 | “非阻塞监控” | 实际走等待回复的事务，可能超时，不应按零耗时读理解 |
| TD201Motor.write_position | 保留timeout_ms | 当前不等待；传5000不保证5秒到位 |
| TulaRobot.set_angles | 文档参数默认5秒、真正同步、<1ms/轴 | 函数签名默认10秒，串口顺序发送，无相应实测数据 |
| test_stress.py | 注释说禁用回零/False可跳过 | 实际skip_home=False，而connect在False时执行home |
| TulaLeRobot文档字符串 | 完全兼容、即插即用 | 与当前Robot/配置/工厂不匹配；仅原型 |
| features | 可选datasets可用即可 | Array2D传一维shape，可能与datasets版本不兼容；只捕获ImportError，构造异常不会降级，未执行验证 |
| 三轴C测试的说明 | 三个物理通道绑定成功 | 绑定不探测硬件；单板双轴资料与第三轴拓扑需确认 |

这些只是记录，不在本轮修代码。前序构建报告的核心结论与当前代码无冲突；应收窄的是注释/早期描述中的实时性、安全、完整兼容等说法，以及误用外层pyserial功能的可能性。

## 运行时应重点知道的限制

- disconnect只解绑/关闭，不发stop；异常退出和Ctrl+C不是硬件停机保证。
- connect中途失败、整机标志尚未True时，disconnect可能提前返回，部分资源释放需单独确认。
- set_angles按计数容差判到位，超时返回False但不停止、不检查完整状态字；调用方必须处理False。
- C move_absolute_wait先判不运行成功，再判运行中的fatal；停后错误/最终目标未全面验证。home_wait超时不统一发stop。不能套用外层更严格的状态等待行为。
- 多轴共用串口无线程锁；“事务原子化”不是多线程安全。发送前清RX也可能丢掉异步状态通知，不能当连续报警订阅系统。
- Python没有暴露C所有stop/报警/配置接口；不能假定上层有完整急停/恢复能力。

## 已验收与尚未验证

已记录通过：独立副本DLL构建、C测试EXE编译、Python加载；原工程40文件未改变；新旧51个导出名称一致，没有已确认接口不兼容。

未验证：另一台物理电脑、其他工具链/Python版本、全部C函数调用、全部行为等价、真实电机回零/精度/运动/稳定频率、LeRobot正式集成。本轮文档工作不追加任何上述验收。

## 需人工确认清单

1. 实际转台/执行机构、控制板修订、固件版本、供电及线缆规范。
2. COM、115200是否仍适用、轴地址及第三轴控制器拓扑。
3. 每轴200counts/degree或直线比例、编码器模式/倍频、方向和参考原点。
4. 资料中的精度、HDT70行程/尺寸/重量冲突及安装尺寸定义。
5. 可接受机械行程、软件限位和硬件急停/安全断电流程。
6. 正式DLL构建发布规范、原库编译参数、现场部署的是哪个副本。
7. 目标LeRobot版本、依赖锁、官方RobotConfig/Robot/工厂及CLI适配计划。
8. 压测、实机验收日志和真实到位/超时/异常恢复标准。
