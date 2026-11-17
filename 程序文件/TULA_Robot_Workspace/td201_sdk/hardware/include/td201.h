#ifndef TD201_H
#define TD201_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================== */
/* 核心系统句柄 (Core System Handles)                                         */
/* ========================================================================== */

/**
 * @brief 控制器设备句柄 (Opaque Device Handle)
 * * 功能：这是一个“不透明指针”设计。它只在头文件中声明，
 * 真实的结构体隐藏在 td201.c 中。
 * 作用是彻底隔离底层系统资源，防止上层用户随意篡改串口状态。
 */
typedef struct td201_dev td201_dev_t;

/**
 * @brief 运动轴结构体 (Axis Handle)
 * * 功能：代表系统中的一个具体的物理电机轴。将逻辑轴号与底层的物理串口设备绑定在一起。
 * 支持 RS-485 菊花链模式（一个串口挂载多个控制器）。
 */
typedef struct td201_axis {
    uint8_t axis_id;                    // 轴节点地址 (例如 1 对应文档中的 01 轴)
    td201_dev_t *dev;                   // 指向该轴所属的底层物理串口设备句柄
} td201_axis_t;                             

/* ========================================================================== */
/* 状态与错误码 (Status & Error Codes)                                        */
/* ========================================================================== */

/**
 * @brief 驱动库全局错误码枚举 (Error Codes)
 * * 功能：统一规范所有 API 函数的返回值。方便上层程序通过 switch-case 进行故障排查。
 */
typedef enum {
    TD201_OK = 0,               //0,执行成功，无错误
    TD201_ERR_INVALID_ARG,      //1,参数无效 (例如传入了空指针或轴号越界)
    TD201_ERR_NOT_OPEN,         //2,设备未打开或句柄失效
    TD201_ERR_IO,               //3,底层 I/O 错误 (串口读写失败)
    TD201_ERR_TIMEOUT,          //4,通信超时 (控制器无应答)
    TD201_ERR_PROTOCOL,         //5,协议解析错误 (收到乱码或前缀不匹配)
    TD201_ERR_RANGE,            //6,数值超出控制器的允许范围 (如频率、电压设置过高)
    TD201_ERR_NOMEM,            //7,内存分配失败 (malloc失败)
    TD201_ERR_HARDWARE_FATAL,   //8,致命硬件保护 (编码器/过温/Z相等，不含 POSITION_ERR)
} td201_err_t;

/** 状态寄存器位掩码 (与 TULA status 回传一致) */
#define TD201_STATUS_MOTOR_RUNNING  0x8000u
#define TD201_STATUS_HOME_MISSING   0x1000u
#define TD201_FATAL_MASK            (0x0010u | 0x0004u | 0x0001u)

/**
 * @brief 电机报警状态结构体 (Alarm State)
 * * 功能：解析并存储控制器返回的报警信息。对应 "al" 或 "status" 指令的回传。
 */
typedef struct {
    int alarm_code;             // 报警代码 (例如 0 表示无报警，其他值表示特定的报警类型)
    unsigned int alarm_hex;     // 报警状态的十六进制位掩码 (每一位代表一个具体的报警条件，如过热、过流等)
} td201_alarm_t;

/* ========================================================================== */
/* 硬件配置参数 (Hardware Configuration Info)                                 */
/* ========================================================================== */

/**
 * @brief 控制器综合信息结构体 (Controller Information)
 * * 功能：汇总控制器 Flash 中存储的全部出厂和运行参数。
 * 对应 "info" 指令连续回传的十几行参数内容。
 */
typedef struct {
    long freq_khz;              // 压电陶瓷驱动频率 (kHz)
    int volt;                   // 驱动电压 (Vdc)
    int enc_type;               // 编码器类型 (例如 1: 增量式, 2: 绝对式)
    long resolution_nm;         // 编码器分辨率 (纳米/脉冲)
    int swap;                   // 编码器通道 A/B 交换标志 (0 或 1)
    int motor_invert;           // 电机运动方向反转标志 (0 或 1)
    long velocity;              // 默认运动速度百分比或预设值
    long home_offset;           // 寻原点后的偏移量 (脉冲数)
    long limit_reverse;         // 软件反向限位 (负方向脉冲极值)
    long limit_forward;         // 软件正向限位 (正方向脉冲极值)
    long stroke;                // 机械总行程
    long in_position;           // 到位区间容差 (目标位置 ± in_position 内即认为到达)
} td201_info_t;

/* ========================================================================== */
/* 生命周期与基础管理 (Lifecycle & Management)                                */
/* ========================================================================== */

/**
 * @brief 打开并初始化底层串口设备
 * @param port_name 串口名称 (如 Windows 的 "COM3" 或 Linux 的 "/dev/ttyUSB0")
 * @param baudrate 波特率 (通常为 115200)
 * @param out_dev 用于接收分配好的设备句柄指针
 * @return TD201_OK 成功，否则返回对应的错误码
 */
td201_err_t td201_open(const char *port_name, int baudrate, td201_dev_t **out_dev);

/**
 * @brief 关闭设备并释放底层资源 (程序退出前必须调用)
 * @param dev 需要关闭的设备句柄
 */
void td201_close(td201_dev_t *dev);

/**
 * @brief 将错误码枚举转换为可读的字符串描述 ,用于日志打印
 * @param err 错误码
 * @return 对应的全英文错误信息字符串
 */
const char *td201_strerror(td201_err_t err);

/* ========================================================================== */
/* 轴对象绑定 (Axis Binding)                                                  */
/* ========================================================================== */

/**
 * @brief 将逻辑轴对象绑定到物理串口设备上
 * @note 在调用 td201_close 之前，建议先调用 unbind 解除绑定
 * @param dev 已打开的底层串口设备
 * @param axis_id 目标轴的硬件地址 (1~99，文档通常标识为 01~99)
 * @param axis 用户分配的轴句柄，用于保存绑定状态
 * @return TD201_OK 成功
 */
td201_err_t td201_axis_bind(td201_dev_t *dev, uint8_t axis_id, td201_axis_t *axis);

/**
 * @brief 解除轴的绑定关系，清空内部指针防止野指针操作
 * @param axis 需要解绑的轴句柄
 */
void td201_axis_unbind(td201_axis_t *axis);

/* ========================================================================== */
/* 底层通信与事务 (Low-level I/O & Transaction)                               */
/* ========================================================================== */

/**
 * @brief 清空串口接收缓冲区内的遗留脏数据 (发指令前调用可防止串位)
 * @param dev 设备句柄
 */
td201_err_t td201_flush_rx(td201_dev_t *dev);

/**
 * @brief 从串口读取一行数据，直到遇到 '\r' 或 '\n' 或超时
 * @param dev 设备句柄
 * @param buffer 用于存储读入数据的缓冲数组
 * @param max_len 缓冲区的最大长度
 * @param out_len 实际读取的字节数 (可选，传 NULL 忽略)
 */
td201_err_t td201_serial_read_line(td201_dev_t *dev, char *buffer, int max_len, int *out_len);

/**
 * @brief 核心事务函数：发送指令并(可选)等待严格匹配的回复
 * @note 发送格式为 `>NNcmd [param]\r`。如果 resp 非空，会校验回复的前缀是否为 `<NNcmd`。
 * @param axis 绑定的轴句柄
 * @param cmd 指令字符串 (如 "ma", "status")
 * @param param 参数字符串 (如 "1000", 可传 NULL)
 * @param resp 用于接收回复数据的缓冲区 (如果不需要接收，传 NULL)
 * @param resp_max 接收缓冲区的最大长度
 * @return TD201_OK 成功，或者协议校验失败/超时错误
 */
td201_err_t td201_transaction(td201_axis_t *axis, const char *cmd, const char *param,
                              char *resp, int resp_max);

/* ========================================================================== */
/* 闭环运动控制 (Motion PTP)                                                  */
/* ========================================================================== */

/**
 * @brief [指令: ma] 移动到绝对目标位置
 * @param axis 轴句柄
 * @param target_pos 绝对目标位置 (脉冲数)
 * @param echo_pos 接收控制器确认回传的位置数值 (可选，传 NULL 忽略)
 */
td201_err_t td201_move_absolute(td201_axis_t *axis, long target_pos, long *echo_pos);

/**
 * @brief [指令: mr] 相对当前位置移动指定距离
 * @param axis 轴句柄
 * @param distance 相对移动的距离 (脉冲数，可正可负)
 * @param echo_pos 接收控制器确认回传的目标位置数值 (可选，传 NULL 忽略)
 */
td201_err_t td201_move_relative(td201_axis_t *axis, long distance, long *echo_pos);

/**
 * @brief [指令: hm] 触发硬件自动寻原点动作
 */
td201_err_t td201_home(td201_axis_t *axis);

/**
 * @brief [指令: auto] 触发系统自动整定 (Auto-tuning)
 */
td201_err_t td201_auto_tune(td201_axis_t *axis);

/**
 * @brief [指令: st] 紧急停止当前轴的所有运动
 */
td201_err_t td201_stop(td201_axis_t *axis);

/**
 * @brief [高级 API] 绝对运动并阻塞等待电机停止 (轮询 0x8000)
 * @param timeout_ms 最大等待毫秒数，必须 > 0
 * @note 运动中对 0x0008 (POSITION_ERR) 不判为致命；触发 TD201_FATAL_MASK 时 stop 并返回 TD201_ERR_HARDWARE_FATAL
 */
td201_err_t td201_move_absolute_wait(td201_axis_t *axis, long target, long timeout_ms);

/**
 * @brief [高级 API] 回零并阻塞等待完成 (0x1000 清除且 0x8000 为 0)
 * @param timeout_ms 最大等待毫秒数，必须 > 0
 */
td201_err_t td201_home_wait(td201_axis_t *axis, long timeout_ms);

/**
 * @brief [安全回零] 柔性触边寻零 (Soft-Homing)
 *
 * 针对存在机械限位且驱动器默认顺时针寻零的转台，执行 5 阶段安全回零：
 *   1. 降占空比至 search_duty (降低推力，抗负载可调)
 *   2. 开环运行至指定方向的机械死点 (search_dir 控制方向)
 *   3. 高频堵转检测 (50ms 轮询 cp, 连续 3 次位置变化 ≤1 脉冲即判定到位，抗抖动)
 *   4. 急停并恢复默认占空比 48
 *   5. 调用 td201_home_wait 执行标准顺时针寻零
 *
 * @param axis        已绑定的轴句柄
 * @param timeout_ms  阶段 2~3 堵转检测的最大等待毫秒数 (阶段 5 使用相同超时)
 * @param search_dir  寻死点方向 (0=反转re/逆时针, 1=正转fo/顺时针)
 * @param search_duty 寻死点时的安全占空比 (建议范围 1~45，函数内部自动限幅)
 * @return TD201_OK 回零成功，否则返回对应错误码
 */
td201_err_t td201_safe_home_wait(td201_axis_t *axis, long timeout_ms, int search_dir, int search_duty);

/* ========================================================================== */
/* 开环控制 (Open-loop) 针对无编码器或特殊调试场景                            */
/* ========================================================================== */

/** @brief [指令: on] 设置开环运行的通电持续时间 (微秒) */
td201_err_t td201_set_on_time(td201_axis_t *axis, long on_time);

/** @brief [指令: off] 设置开环运行的断电休眠间隔 (毫秒) */
td201_err_t td201_set_off_interval(td201_axis_t *axis, long interval_ms);

/** @brief [指令: cy] 设置开环运行的循环次数 */
td201_err_t td201_set_cycles(td201_axis_t *axis, long cycles);

/** @brief [指令: re] 执行开环反向运行 */
td201_err_t td201_run_reverse(td201_axis_t *axis);

/** @brief [指令: fo] 执行开环正向运行 */
td201_err_t td201_run_forward(td201_axis_t *axis);

/** @brief [指令: bi] 执行开环双向(往复)运行 */
td201_err_t td201_run_bidirectional(td201_axis_t *axis);

/* ========================================================================== */
/* 状态查询 (Status)                                                          */
/* ========================================================================== */

/**
 * @brief [指令: cp] 获取当前编码器反馈的实际位置
 * @param position 用于输出当前位置的脉冲数
 */
td201_err_t td201_get_position(td201_axis_t *axis, long *position);

/**
 * @brief [指令: al] 获取电机报警码与状态寄存器
 * @note 这是非阻塞状态监控的首选函数，适合放入定时器轮询。
 * @param alarm 输出解析好的报警结构体 (含状态码及十六进制位掩码)
 */
td201_err_t td201_get_alarm(td201_axis_t *axis, td201_alarm_t *alarm);

/**
 * @brief [指令: info] 批量拉取控制器当前的所有核心参数配置
 * @note 该函数会连续读取多行数据，耗时较长，请勿在高频轮询中使用。
 * @param info 输出包含电压、频率、速度等全量配置的结构体
 */
td201_err_t td201_get_info(td201_axis_t *axis, td201_info_t *info);

/**
 * @brief [指令: ver] 获取控制器固件版本及发布日期
 */
td201_err_t td201_get_version(td201_axis_t *axis, long *yymmdd, long *version);

/**
 * @brief 将 status 寄存器位掩码解析为人类可读说明 (输出到 stdout，供调试/ROS2 桥接)
 */
void td201_print_alarm_details(unsigned int alarm_hex);

/* ========================================================================== */
/* 硬件参数配置 (Configuration) 修改后需配合 save 保存                        */
/* ========================================================================== */


/** @brief [指令: freq] 设置压电驱动频率 (kHz, 高危参数) */
td201_err_t td201_set_freq(td201_axis_t *axis, int freq_khz);

/** @brief [指令: duty] 设置 PWM 占空比 (%) */
td201_err_t td201_set_duty(td201_axis_t *axis, int duty_percent);

/** @brief [指令: volt] 设置驱动电压 (V) */
td201_err_t td201_set_volt(td201_axis_t *axis, int voltage);

/** @brief [指令: enc] 设置编码器类型 (1:增量, 2:绝对) */
td201_err_t td201_set_enc(td201_axis_t *axis, int enc_type);

/** @brief [指令: res] 设置编码器物理分辨率 (纳米/脉冲) */
td201_err_t td201_set_res(td201_axis_t *axis, long resolution_nm);

/** @brief [指令: swap] 设置是否交换编码器 A/B 通道 (0或1) */
td201_err_t td201_set_swap(td201_axis_t *axis, int swap);

/** @brief [指令: mid] 设置是否反转电机逻辑运动方向 (0或1) */
td201_err_t td201_set_mid(td201_axis_t *axis, int invert);

/** @brief [指令: vel] 设置系统全局运动速度限制 */
td201_err_t td201_set_vel(td201_axis_t *axis, int velocity);

/** @brief [指令: offset] 设置寻原点成功后的坐标偏移值 */
td201_err_t td201_set_offset(td201_axis_t *axis, long offset);

/** @brief [指令: message] 开关 RS-485 的消息回传模式 (0或1) */
td201_err_t td201_set_message(td201_axis_t *axis, int on_off);

/** @brief [指令: inp] 设置到位容差区间 (目标位 ± inp 内视为停止) */
td201_err_t td201_set_in_position(td201_axis_t *axis, int inp_value);

/** @brief [指令: baudrate] 更改波特率 (注意：修改后需重启连接) */
td201_err_t td201_set_baudrate(td201_axis_t *axis, int baudrate);

/** @brief [指令: save] 将参数保存到 Flash */
td201_err_t td201_save_to_flash(td201_axis_t *axis);

/* ========================================================================== */
/* 闭环滤波/PID参数控制 (Control Filters)                                     */
/* ========================================================================== */

/** @brief [指令: kp] 设置位置环比例增益 */
td201_err_t td201_set_kp(td201_axis_t *axis, int kp_value);

/** @brief [指令: ki] 设置位置环积分增益 */
td201_err_t td201_set_ki(td201_axis_t *axis, int ki_value);

/** @brief [指令: kd] 设置位置环微分增益 */
td201_err_t td201_set_kd(td201_axis_t *axis, int kd_value);

/** @brief [指令: kf] 设置前馈增益系数 */
td201_err_t td201_set_kf(td201_axis_t *axis, int kf_value);

/* ========================================================================== */
/* 弃用接口 (Deprecated)                                                      */
/* ========================================================================== */

/**
 * @deprecated 建议改用 td201_get_alarm 和 td201_stop 获取具体结构化信息。
 * @brief [指令: status] 读取控制器的原始状态返回字符串
 */
td201_err_t td201_get_status(td201_axis_t *axis, char *out_line, int max_len);

#ifdef __cplusplus
}
#endif

#endif /* TD201_H */
