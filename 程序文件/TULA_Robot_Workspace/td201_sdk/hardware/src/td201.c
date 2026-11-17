#include "td201.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#else
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>
#include <time.h>
#endif

#define TD201_CMD_BUF   128
#define TD201_RESP_BUF  256
#define TD201_INFO_LINES 16
#define TD201_POLL_MS     100

/*
 * ============================================================
 * 工业级实时控制常量
 *
 * TD201_TXN_TIMEOUT_MS:
 *   一次「发送→接收」原子事务的硬超时上限(毫秒)。
 *   50Hz控制周期=20ms，5ms超时确保在单周期内有足够余量，
 *   即使脏数据帧被连续丢弃2~3次也不会耗尽时间片。
 * TD201_LINE_TIMEOUT_MS:
 *   通用单行读取的超时上限，用于 info/reset 等非实时路径。
 * ============================================================
 */
#define TD201_TXN_TIMEOUT_MS    12
#define TD201_LINE_TIMEOUT_MS  50

#if defined(_WIN32) || defined(_WIN64)
#define TD201_SLEEP_MS(ms) Sleep(ms)
#else
#define TD201_SLEEP_MS(ms) usleep((unsigned int)(ms) * 1000U)
#endif

static void td201_sleep_ms(int ms)
{
    if (ms > 0) {
        TD201_SLEEP_MS(ms);
    }
}

/*
 * ------------------------------------------------------------
 * 获取当前单调时钟，单位毫秒 (跨平台)
 * 用于实现微秒级非阻塞超时轮询，替代粗放式 Sleep 挂起。
 * Windows: GetTickCount64() 返回系统启动后的毫秒数。
 * Linux:   clock_gettime(CLOCK_MONOTONIC) 不受系统时间跳变影响。
 * ------------------------------------------------------------
 */
static unsigned long get_time_ms(void)
{
#if defined(_WIN32) || defined(_WIN64)
    return (unsigned long)GetTickCount64();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (unsigned long)((unsigned long long)ts.tv_sec * 1000ULL +
                           (unsigned long long)ts.tv_nsec / 1000000ULL);
#endif
}

struct td201_dev {
#if defined(_WIN32) || defined(_WIN64)
    HANDLE port_handle;     // Windows 系统的串口句柄
#else
    int port_handle;        // Linux/macOS 系统的文件描述符
#endif
    int baudrate;           // 记录当前配置的波特率
    bool is_open;           // 记录物理串口是否处于成功打开的状态
};

static td201_err_t check_axis(const td201_axis_t *axis)
{
    //指针有效性与逻辑地址检查
    if (!axis || axis->axis_id < 1 || axis->axis_id > 99) {
        return TD201_ERR_INVALID_ARG;
    }
    //物理设备绑定与状态检查
    if (!axis->dev || !axis->dev->is_open) {
        return TD201_ERR_NOT_OPEN;
    }
    return TD201_OK;
}

static td201_err_t check_dev(const td201_dev_t *dev)
{
    //检查设备指针有效性（是否误传了空指针）与打开状态
    if (!dev || !dev->is_open) {
        return TD201_ERR_NOT_OPEN;
    }
    return TD201_OK;
}

//说人话函数
const char *td201_strerror(td201_err_t err)
{
    switch (err) {
    case TD201_OK: return "OK";
    case TD201_ERR_INVALID_ARG: return "Invalid argument";
    case TD201_ERR_NOT_OPEN: return "Device not open";
    case TD201_ERR_IO: return "I/O error";
    case TD201_ERR_TIMEOUT: return "Timeout";
    case TD201_ERR_PROTOCOL: return "Protocol mismatch";
    case TD201_ERR_RANGE: return "Parameter out of range";
    case TD201_ERR_NOMEM: return "Out of memory";
    case TD201_ERR_HARDWARE_FATAL: return "Hardware fatal fault";
    default: return "Unknown error";
    }
}

/* ------------------------------------------------------------------ */
/* Serial layer                                                        */
/* ------------------------------------------------------------------ */

td201_err_t td201_open(const char *port_name, int baudrate, td201_dev_t **out_dev)
{
    //参数检查：端口名不能为空，输出指针不能为空，波特率必须为正数
    if (!port_name || !out_dev || baudrate <= 0) {
        return TD201_ERR_INVALID_ARG;
    }
    //为指针变量dev结构体分配内存并初始化基本字段
    td201_dev_t *dev = (td201_dev_t *)calloc(1, sizeof(td201_dev_t));
    if (!dev) {
        return TD201_ERR_NOMEM;
    }

    dev->baudrate = baudrate;
    dev->is_open = false;   //先标记为未打开，后续成功打开后再改为true

#if defined(_WIN32) || defined(_WIN64)
    char full_port_name[64];
    snprintf(full_port_name, sizeof(full_port_name), "\\\\.\\%s", port_name);//兼容串口号为10及以上的COM口

    //调用 Win32 API CreateFileA 来打开物理串口设备，获取句柄并存储在 dev 结构体中
    dev->port_handle = CreateFileA(
        full_port_name, GENERIC_READ | GENERIC_WRITE, 0, NULL,
        OPEN_EXISTING, 0, NULL);                
    if (dev->port_handle == INVALID_HANDLE_VALUE) {
        free(dev);
        return TD201_ERR_IO;
    }
    //调用DCB结构体配置串口参数：波特率、数据位、停止位、校验位等
    DCB dcb = {0};
    dcb.DCBlength = sizeof(dcb);
    if (!GetCommState(dev->port_handle, &dcb)) {
        CloseHandle(dev->port_handle);
        free(dev);
        return TD201_ERR_IO;
    }
    dcb.BaudRate = (DWORD)baudrate; // 设置波特率
    dcb.ByteSize = 8;               // 8数据位
    dcb.StopBits = ONESTOPBIT;      // 1停止位
    dcb.Parity = NOPARITY;          // 无校验
    if (!SetCommState(dev->port_handle, &dcb)) {
        CloseHandle(dev->port_handle);
        free(dev);
        return TD201_ERR_IO;
    }

    //调用 SetCommTimeouts 来设置串口的读写超时参数，确保在通信异常时不会无限阻塞
    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutConstant = 100;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    timeouts.WriteTotalTimeoutConstant = 100;
    timeouts.WriteTotalTimeoutMultiplier = 10;
    SetCommTimeouts(dev->port_handle, &timeouts);
#else
    dev->port_handle = open(port_name, O_RDWR | O_NOCTTY | O_SYNC);
    if (dev->port_handle < 0) {
        free(dev);
        return TD201_ERR_IO;
    }

    struct termios tty;
    if (tcgetattr(dev->port_handle, &tty) != 0) {
        close(dev->port_handle);
        free(dev);
        return TD201_ERR_IO;
    }

    speed_t speed = B115200;
    switch (baudrate) {
    case 9600: speed = B9600; break;
    case 19200: speed = B19200; break;
    case 38400: speed = B38400; break;
    case 57600: speed = B57600; break;
    case 115200: speed = B115200; break;
    default:
        close(dev->port_handle);
        free(dev);
        return TD201_ERR_INVALID_ARG;
    }
    cfsetospeed(&tty, speed);
    cfsetispeed(&tty, speed);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
    tty.c_iflag &= ~IGNBRK;
    tty.c_lflag = 0;
    tty.c_oflag = 0;
    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 10;
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);
    tty.c_cflag |= (CLOCAL | CREAD);
    tty.c_cflag &= ~(PARENB | PARODD);
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CRTSCTS;

    if (tcsetattr(dev->port_handle, TCSANOW, &tty) != 0) {
        close(dev->port_handle);
        free(dev);
        return TD201_ERR_IO;
    }
#endif

    dev->is_open = true;
    *out_dev = dev;
    return TD201_OK;
}

void td201_close(td201_dev_t *dev)
{
    if (!dev) {
        return;
    }
    if (dev->is_open) {
#if defined(_WIN32) || defined(_WIN64)
        CloseHandle(dev->port_handle);      //关闭串口句柄，解除串口占用
#else
        close(dev->port_handle);
#endif
        dev->is_open = false;
    }
    free(dev);
}

td201_err_t td201_axis_bind(td201_dev_t *dev, uint8_t axis_id, td201_axis_t *axis)
{
    td201_err_t err = check_dev(dev);
    if (err != TD201_OK) {
        return err;
    }
    if (!axis || axis_id < 1 || axis_id > 99) {
        return TD201_ERR_INVALID_ARG;
    }
    axis->axis_id = axis_id;
    axis->dev = dev;
    return TD201_OK;
}

void td201_axis_unbind(td201_axis_t *axis)
{
    if (axis) {
        axis->dev = NULL;
        axis->axis_id = 0;
    }
}

td201_err_t td201_flush_rx(td201_dev_t *dev)
{
    td201_err_t err = check_dev(dev);
    if (err != TD201_OK) {
        return err;
    }
#if defined(_WIN32) || defined(_WIN64)
    if (!PurgeComm(dev->port_handle, PURGE_RXCLEAR)) {
        return TD201_ERR_IO;
    } //PurgeComm的PURGE_RXCLEAR标志用于清空输入缓冲区中的数据，防止后续读取到过期或无效的数据
#else
    if (tcflush(dev->port_handle, TCIFLUSH) != 0) {
        return TD201_ERR_IO;
    }
#endif
    return TD201_OK;
}

static int serial_write(td201_dev_t *dev, const char *data, int len)
{
#if defined(_WIN32) || defined(_WIN64)
    DWORD written = 0;
    if (!WriteFile(dev->port_handle, data, (DWORD)len, &written, NULL)) {
        return -1;
    }//WriteFile函数用于向串口发送数据，成功时返回写入的字节数，失败时返回-1。注意这里将DWORD类型的written转换为int类型返回给调用者。
    return (int)written;
#else
    ssize_t n = write(dev->port_handle, data, (size_t)len);
    return (n < 0) ? -1 : (int)n;
#endif
}

td201_err_t td201_serial_read_line(td201_dev_t *dev, char *buffer, int max_len, int *out_len)
{
    td201_err_t err = check_dev(dev);
    if (err != TD201_OK) {
        return err;
    }
    if (!buffer || max_len <= 1) {
        return TD201_ERR_INVALID_ARG;
    }

    int total = 0;
    char c = 0;

    while (total < max_len - 1) {
#if defined(_WIN32) || defined(_WIN64)
        DWORD nread = 0;
        if (!ReadFile(dev->port_handle, &c, 1, &nread, NULL) || nread == 0) {
            break;
        }
#else
        if (read(dev->port_handle, &c, 1) <= 0) {
            break;
        }
#endif
        buffer[total++] = c;
        if (c == '\r' || c == '\n') {
            break;
        }
    }
    buffer[total] = '\0';
    if (out_len) {
        *out_len = total;
    }
    return (total > 0) ? TD201_OK : TD201_ERR_TIMEOUT;//如果成功读取到数据则返回TD201_OK，如果没有读取到任何数据则返回TD201_ERR_TIMEOUT，表示通信超时或控制器无应答。
}

/*
 * ------------------------------------------------------------
 * 带硬截止时间的单行读取 (Hard-deadline read-line)
 *
 * 与 td201_serial_read_line 的区别在于：
 *   - 增加 deadline_ms 截止时间参数。
 *   - 每读取一个字节前先检查 get_time_ms() 是否已超过截止时刻。
 *   - 若超时且尚未读到任何数据，返回 TD201_ERR_TIMEOUT。
 *   - 若超时但已读到部分字节(未遇到\r)，仍返回已读内容。
 *
 * 这是实现「微秒级非阻塞超时」的核心原语，
 * 50Hz 控制周期下绝不让线程在串口上无限挂起。
 * ------------------------------------------------------------
 */
static td201_err_t serial_read_line_deadline(td201_dev_t *dev, char *buffer, int max_len,
                                             int *out_len, unsigned long deadline_ms)
{
    td201_err_t err = check_dev(dev);
    if (err != TD201_OK) {
        return err;
    }
    if (!buffer || max_len <= 1) {
        return TD201_ERR_INVALID_ARG;
    }

    int total = 0;
    char c = 0;

    while (total < max_len - 1) {
        /* ---------- 微秒级非阻塞超时检查 ----------
         * 在每次尝试读取单个字节之前，先检查单调时钟是否已超过
         * 本次事务的硬截止时间。这确保即使操作系统串口驱动
         * ReadFile/read 内部有毫秒级超时，我们也能提前退出，
         * 绝不让 50Hz 控制周期被串口阻塞。
         */
        if (get_time_ms() >= deadline_ms) {
            break;
        }

#if defined(_WIN32) || defined(_WIN64)
        DWORD nread = 0;
        if (!ReadFile(dev->port_handle, &c, 1, &nread, NULL) || nread == 0) {
            /* 无数据可读时主动让出 CPU 时间片(1ms)，
             * 避免纯忙等(Busy-wait)吃满单核。
             * 对于 115200bps 的 TD-201 协议，1ms 轮询足够精细。 */
            Sleep(0);
            continue;
        }
#else
        ssize_t r = read(dev->port_handle, &c, 1);
        if (r <= 0) {
            /* Linux: 无数据时短暂让出调度 */
            struct timespec req = {0, 100000}; /* 0.1ms */
            nanosleep(&req, NULL);
            continue;
        }
#endif
        buffer[total++] = c;
        if (c == '\r' || c == '\n') {
            break;
        }
    }

    buffer[total] = '\0';
    if (out_len) {
        *out_len = total;
    }
    return (total > 0) ? TD201_OK : TD201_ERR_TIMEOUT;
}

/* ------------------------------------------------------------------ */
/* Protocol helpers                                                    */
/* ------------------------------------------------------------------ */

static int format_cmd(const td201_axis_t *axis, const char *cmd, const char *param,
                      char *buf, size_t buf_sz)
{
    if (param && param[0] != '\0') {
        /* 如果param参数非空且不为空字符串，进行格式化拼装：
        >：起始符；
        %02u：把后面的 axis_id 作为无符号整数打印，如果数字是一位数（如1），前面自动补0（变成01）；%s：插入指令 
        %s：插入指令;
         :插入一个极其关键的空格，它是指令格式的一部分，必须存在;
        %s：插入参数
        \r：插入回车符。控制器只有收到这个符号，才知道指令说完了
        */
        return snprintf(buf, buf_sz, ">%02u%s %s\r", (unsigned)axis->axis_id, cmd, param);
    }
    //如果param参数为空或是空字符串，则不插入空格和参数，直接拼装指令和回车符,一般用于查询状态
    return snprintf(buf, buf_sz, ">%02u%s\r", (unsigned)axis->axis_id, cmd);
}

//检查回复字符串的前缀是否与预期的格式匹配，例如 "<01ma" 表示 01 轴对 ma 指令的回复
static bool response_matches(const td201_axis_t *axis, const char *cmd, const char *line)
{
    char prefix[16];
    snprintf(prefix, sizeof(prefix), "<%02u%s", (unsigned)axis->axis_id, cmd);
    return strncmp(line, prefix, strlen(prefix)) == 0;
}

/*
 * ============================================================
 * 核心事务函数 (Atomic Transaction Engine)
 *
 * 这是整个 TD-201 通信栈的「心脏」。
 * 实现了工业级实时控制所需的三大机制：
 *
 * [机制1] 事务原子化与发前清空 (Atomic Transaction & Pre-Flush)
 *         在拼接并写入 TX 之前，先调用 td201_flush_rx() 通过
 *         PurgeComm(PURGE_RXCLEAR) 物理清空串口接收 FIFO，
 *         确保上一次超时/异常事务遗留的脏数据绝不污染本次读取。
 *
 * [机制2] 滑动窗口脏数据过滤 (Robust Sliding-Window Parsing)
 *         收到数据后绝不盲目信任前几个字节。
 *         如果读到的帧前缀与目标轴号不匹配（收到了轴1的旧回复等），
 *         将该帧静默丢弃，清空 Buffer，在剩余超时内继续尝试读取
 *         下一帧，直到找到合法的匹配回复或时间耗尽。
 *
 * [机制3] 微秒级非阻塞超时 (Microsecond Non-blocking Polling)
 *         使用 get_time_ms() 获取单调时钟，为本次事务设置
 *         TD201_TXN_TIMEOUT_MS (5ms) 硬截止时间。
 *         每轮读取使用 serial_read_line_deadline() 以非阻塞方式
 *         轮询，绝不让 50Hz (20ms) 控制线程被串口长期挂起。
 * ============================================================
 */
static td201_err_t send_and_recv(td201_axis_t *axis, const char *cmd, const char *param,
                                 char *resp, int resp_max, bool verify)
{
    /* ---- 构建发送报文 ---- */
    char tx[TD201_CMD_BUF];
    int tx_len = format_cmd(axis, cmd, param, tx, sizeof(tx));
    if (tx_len <= 0 || tx_len >= (int)sizeof(tx)) {
        return TD201_ERR_INVALID_ARG;
    }

    /*
     * ---- [机制1] 原子事务：发前物理清空接收缓冲区 ----
     * 在任何 TX 写入之前，必须通过 PurgeComm(PURGE_RXCLEAR) /
     * tcflush(TCIFLUSH) 将串口硬件 FIFO 中残留的脏数据全部丢弃。
     * 这保证了本次事务的 RX 通道是「清洁」的起点，
     * 上次超时、异常或轴间串扰遗留的字节不会污染后续解析。
     */
    td201_err_t err = td201_flush_rx(axis->dev);
    if (err != TD201_OK) {
        return err;
    }

    /* ---- 发送指令 ---- */
    if (serial_write(axis->dev, tx, tx_len) != tx_len) {
        return TD201_ERR_IO;
    }

    /* 若无 resp 缓冲区，说明调用方不需要接收回复（如开环指令） */
    if (!resp || resp_max <= 0) {
        return TD201_OK;
    }

    /*
     * ---- [机制3] 微秒级非阻塞超时：设定硬截止时间 ----
     * 本次原子事务的总超时上限为 TD201_TXN_TIMEOUT_MS (5ms)。
     * deadline_ms 是一个单调递增的「死线时刻」，所有读取操作
     * 必须在此时刻之前完成，否则视为 FRAME_LOST / TIMEOUT。
     */
    unsigned long deadline_ms = get_time_ms() + TD201_TXN_TIMEOUT_MS;

    /*
     * ---- [机制2] 滑动窗口脏数据过滤循环 ----
     * 在一个硬截止时间内，持续尝试读取完整行。
     * 如果读到的帧前缀与当前轴号不匹配：
     *   - 不视为致命错误（不立即返回 TD201_ERR_PROTOCOL）
     *   - 将该脏帧静默丢弃
     *   - 清空本地 Buffer
     *   - 在剩余超时窗口内尝试读取下一帧
     * 只有当时间耗尽仍无合法帧时，才返回超时错误。
     */
    int dirty_frames_discarded = 0;  /* 诊断计数：丢弃的脏帧数 */
    while (get_time_ms() < deadline_ms) {
        int n = 0;
        err = serial_read_line_deadline(axis->dev, resp, resp_max, &n,
                                        deadline_ms);
        if (err != TD201_OK) {
            /*
             * 未读到任何数据（超时或 IO 错误），
             * 继续在循环中重试，直到硬截止时间耗尽。
             */
            continue;
        }

        /*
         * 读到一行数据，检查前缀是否合法。
         * 合法的帧必须以 '<' + 两位轴号 + 命令字符串 开头。
         * 例如轴2的 ma 指令期望 "<02ma"。
         */

        /* 特殊处理：al 指令可能回复 "<NNstatus" 而非 "<NNal" */
        bool matched = false;
        if (verify) {
            if (strcmp(cmd, "al") == 0) {
                char alt[16];
                snprintf(alt, sizeof(alt), "<%02ustatus",
                         (unsigned)axis->axis_id);
                if (strncmp(resp, alt, strlen(alt)) == 0) {
                    matched = true;
                }
                /* 也允许标准前缀 "<NNal" */
                if (!matched && response_matches(axis, cmd, resp)) {
                    matched = true;
                }
            } else {
                matched = response_matches(axis, cmd, resp);
            }
        } else {
            /* verify == false 时不做前缀校验，读到即返回 */
            matched = true;
        }

        if (matched) {
            /* ---- 合法帧匹配成功，事务正常返回 ---- */
            if (dirty_frames_discarded > 0) {
                /*
                 * 诊断日志：若丢弃过脏帧，静默记录但不中断流程。
                 * 这对高频运行时排查串扰问题非常有用。
                 */
                printf("[TD201 WARN] Discarded %d dirty frame(s) before "
                       "matching <%02u%s\n",
                       dirty_frames_discarded,
                       (unsigned)axis->axis_id, cmd);
                fflush(stdout);
            }
            return TD201_OK;
        }

        /*
         * ---- 帧前缀不匹配：静默丢弃脏数据 ----
         * 这是解决「轴间串扰」问题的核心逻辑：
         * 当读到轴1的旧回复或乱码时，不立即报错退圈，
         * 而是将其丢弃并继续在剩余时间内寻找合法帧。
         */
        dirty_frames_discarded++;

        /* 诊断输出：帮助现场定位串扰来源 */
        {
            char resp_clean[TD201_RESP_BUF];
            strncpy(resp_clean, resp, sizeof(resp_clean) - 1);
            resp_clean[sizeof(resp_clean) - 1] = '\0';
            for (char *p = resp_clean; *p; p++) {
                if (*p == '\r' || *p == '\n') *p = ' ';
            }
            printf("[TD201 DISCARD] dirty frame #%d for axis %02u/%s: "
                   "[%s]\n",
                   dirty_frames_discarded,
                   (unsigned)axis->axis_id, cmd, resp_clean);
            fflush(stdout);
        }

        /* 清空 Buffer 为下一轮读取做准备 */
        memset(resp, 0, (size_t)resp_max);

        /* 继续循环，在剩余超时窗口内尝试读下一帧 */
    }

    /*
     * ---- 硬超时退出 ----
     * 在 TD201_TXN_TIMEOUT_MS 内既未读到合法帧，也未读到任何数据。
     * 返回 TD201_ERR_TIMEOUT，让上层决定重试或进入保护。
     */
    if (dirty_frames_discarded > 0) {
        printf("[TD201 TIMEOUT] No valid frame for <%02u%s after "
               "discarding %d dirty frame(s) in %dms\n",
               (unsigned)axis->axis_id, cmd,
               dirty_frames_discarded, TD201_TXN_TIMEOUT_MS);
        fflush(stdout);
    }
    return TD201_ERR_TIMEOUT;
}

td201_err_t td201_transaction(td201_axis_t *axis, const char *cmd, const char *param,
                              char *resp, int resp_max)
{
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    if (!cmd || cmd[0] == '\0') {
        return TD201_ERR_INVALID_ARG;
    }
    return send_and_recv(axis, cmd, param, resp, resp_max, resp != NULL);
}

//已读回执确认器
static td201_err_t tx_simple(td201_axis_t *axis, const char *cmd, const char *param)
{
    char resp[TD201_RESP_BUF];
    return td201_transaction(axis, cmd, param, resp, (int)sizeof(resp));
}

//数值型指令发送器，适用于大多数需要发送数值参数的指令，如位置、速度、增益等。它会将数值转换为字符串参数，并可选地解析回执中的数值回显。
static td201_err_t tx_long(td201_axis_t *axis, const char *cmd, long value, long *echo)
{
    char param[32];
    snprintf(param, sizeof(param), "%ld", value);
    char resp[TD201_RESP_BUF];
    td201_err_t err = td201_transaction(axis, cmd, param, resp, (int)sizeof(resp));
    if (err != TD201_OK) {
        return err;
    }
    if (echo) {
        const char *sp = strchr(resp, ' ');
        if (!sp || sscanf(sp + 1, "%ld", echo) != 1) {
            return TD201_ERR_PROTOCOL;
        }
    }
    return TD201_OK;
}

//整数型指令发送器，适用于需要发送整数参数的指令，如增益设置等。它会将整数转换为字符串参数，并可选地解析回执中的数值回显。
static td201_err_t tx_int(td201_axis_t *axis, const char *cmd, int value)
{
    char param[24];
    snprintf(param, sizeof(param), "%d", value);
    return tx_simple(axis, cmd, param);
}

//增益参数检查器，确保传入的增益值在控制器允许的范围内（0~32767）。如果超出范围，返回 TD201_ERR_RANGE 错误码。
static td201_err_t check_gain(int v)
{
    return (v >= 0 && v <= 32767) ? TD201_OK : TD201_ERR_RANGE;
}

/* ------------------------------------------------------------------ */
/* Motion                                                              */
/* ------------------------------------------------------------------ */

td201_err_t td201_move_absolute(td201_axis_t *axis, long target_pos, long *echo_pos)
{
    if (target_pos < -2147000000L || target_pos > 2147000000L) {
        return TD201_ERR_RANGE;
    }
    
    // 【终极修改】：放弃 tx_long 的死等回执。直接使用 td201_transaction 且 resp 传 NULL！
    // 这样 C 语言把指令推入串口后会瞬间 return (耗时 < 1ms)
    char param[32];
    snprintf(param, sizeof(param), "%ld", target_pos);
    return td201_transaction(axis, "ma", param, NULL, 0);
}

td201_err_t td201_move_relative(td201_axis_t *axis, long distance, long *echo_pos)
{
    if (distance < -2147000000L || distance > 2147000000L) {
        return TD201_ERR_RANGE;
    }
    return tx_long(axis, "mr", distance, echo_pos);
}

td201_err_t td201_home(td201_axis_t *axis)
{
    return tx_simple(axis, "hm", NULL);
}

td201_err_t td201_auto_tune(td201_axis_t *axis)
{
    return tx_simple(axis, "auto", NULL);
}

td201_err_t td201_stop(td201_axis_t *axis)
{
    return tx_simple(axis, "st", NULL);
}

void td201_print_alarm_details(unsigned int alarm_hex)
{
    if (alarm_hex == 0) {
        return;
    }

    printf("\n    ==== [底层诊断] 状态寄存器解析 (0x%X) ====\n", alarm_hex);

    if (alarm_hex & TD201_STATUS_MOTOR_RUNNING) {
        printf("      - [状态] MOTOR_RUNNING (驱动器正在运行)\n");
    }
    if (alarm_hex & 0x0400u) {
        printf("      - [模式] PULSE DIR_OPEN (处于 脉冲-方向开放模式)\n");
    }
    if (alarm_hex & 0x0200u) {
        printf("      - [模式] PULSE DIR (处于 脉冲-方向模式)\n");
    }
    if (alarm_hex & 0x2000u) {
        printf("      - [报警] AUTO_TUNING (自动调谐错误)\n");
    }
    if (alarm_hex & TD201_STATUS_HOME_MISSING) {
        printf("      - [拦截] HOME MISSING (初始位置未知，请先回零)\n");
    }
    if (alarm_hex & 0x0100u) {
        printf("      - [拦截] ILLEGAL CMD (指令格式有误，控制器无法识别)\n");
    }
    if (alarm_hex & 0x0080u) {
        printf("      - [拦截] PARAMETER ERR (参数超出范围，通常是撞了软限位)\n");
    }
    if (alarm_hex & 0x0010u) {
        printf("      - [硬件] ENCODER_ERR (编码器错误：信号线接反、断开或故障)\n");
    }
    if (alarm_hex & 0x0008u) {
        printf("      - [保护] POSITION_ERR (位置跟随误差，高速运动时可能短暂出现)\n");
    }
    if (alarm_hex & 0x0004u) {
        printf("      - [硬件] ENCODER_Z_ERR (Z相原点信号读取错误)\n");
    }
    if (alarm_hex & 0x0001u) {
        printf("      - [保护] OVER_TEMP (驱动板温度过高，进入热保护)\n");
    }

    printf("    ==================================================\n");
}

td201_err_t td201_move_absolute_wait(td201_axis_t *axis, long target, long timeout_ms)
{
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    if (timeout_ms <= 0) {
        return TD201_ERR_INVALID_ARG;
    }

    err = td201_move_absolute(axis, target, NULL);
    if (err != TD201_OK) {
        return err;
    }

    int elapsed = 0;
    while (elapsed < timeout_ms) {
        td201_sleep_ms(TD201_POLL_MS);
        elapsed += TD201_POLL_MS;

        td201_alarm_t alarm;
        err = td201_get_alarm(axis, &alarm);
        if (err != TD201_OK) {
            continue;
        }

        if (!(alarm.alarm_hex & TD201_STATUS_MOTOR_RUNNING)) {
            return TD201_OK;
        }

        if (alarm.alarm_hex & TD201_FATAL_MASK) {
            td201_stop(axis);
            return TD201_ERR_HARDWARE_FATAL;
        }
    }

    td201_stop(axis);
    return TD201_ERR_TIMEOUT;
}

td201_err_t td201_home_wait(td201_axis_t *axis, long timeout_ms)
{
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    if (timeout_ms <= 0) {
        return TD201_ERR_INVALID_ARG;
    }

    err = td201_home(axis);
    if (err != TD201_OK) {
        return err;
    }

    int elapsed = 0;
    while (elapsed < timeout_ms) {
        td201_sleep_ms(TD201_POLL_MS);
        elapsed += TD201_POLL_MS;

        td201_alarm_t alarm;
        err = td201_get_alarm(axis, &alarm);
        if (err != TD201_OK) {
            continue;
        }

        if (!(alarm.alarm_hex & TD201_STATUS_HOME_MISSING) &&
            !(alarm.alarm_hex & TD201_STATUS_MOTOR_RUNNING)) {
            return TD201_OK;
        }

        if (alarm.alarm_hex & TD201_FATAL_MASK) {
            td201_stop(axis);
            return TD201_ERR_HARDWARE_FATAL;
        }
    }

    return TD201_ERR_TIMEOUT;
}

/* ================================================================== */
/* 安全回零 (Safe Soft-Homing)                                         */
/* ================================================================== */

td201_err_t td201_safe_home_wait(td201_axis_t *axis, long timeout_ms,
                                  int search_dir, int search_duty)
{
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    if (timeout_ms <= 0) {
        return TD201_ERR_INVALID_ARG;
    }

    /* ---- 占空比限幅保护 ---- */
    if (search_duty < 1) {
        search_duty = 20;  /* 输入非法极小值时回退到安全默认值 */
    } else if (search_duty > 45) {
        search_duty = 45;
    }

    /* ---- Phase 1: 降功率柔性模式 ---- */
    err = td201_set_duty(axis, search_duty);
    if (err != TD201_OK) {
        return err;
    }
    td201_sleep_ms(50);

    /* ---- Phase 2: 开环寻死点 (方向由 search_dir 决定) ---- */
    if (search_dir == 1) {
        err = td201_run_forward(axis);
    } else {
        err = td201_run_reverse(axis);
    }
    if (err != TD201_OK) {
        /* 恢复默认占空比后返回 */
        td201_set_duty(axis, 48);
        return err;
    }

    /* ---- Phase 3: 高频堵转检测 (抗抖动) ---- */
    long last_position = 0;
    int stall_count = 0;
    int elapsed_ms = 0;
    int got_first = 0;  /* 是否已拿到第一个有效位置样本 */

    while (elapsed_ms < timeout_ms) {
        td201_sleep_ms(50);
        elapsed_ms += 50;

        /* 检查致命报警 */
        td201_alarm_t alarm;
        if (td201_get_alarm(axis, &alarm) == TD201_OK) {
            if (alarm.alarm_hex & TD201_FATAL_MASK) {
                td201_stop(axis);
                td201_sleep_ms(50);
                td201_set_duty(axis, 48);
                return TD201_ERR_HARDWARE_FATAL;
            }
        }

        /* 读取当前编码器位置 */
        long current_position = 0;
        err = td201_get_position(axis, &current_position);
        if (err != TD201_OK) {
            /* cp 偶尔丢包时不中断，维持上次状态 */
            continue;
        }

        if (!got_first) {
            last_position = current_position;
            got_first = 1;
            continue;
        }

        /* 抗抖动：重载压电电机撞击死点时允许 ±1 脉冲的抖动 */
        if (labs(current_position - last_position) <= 1) {
            stall_count++;
            if (stall_count >= 3) {
                /* 连续 3 次 (>=150ms) 位置基本不变，判定已触机械死点 */
                break;
            }
        } else {
            stall_count = 0;
            last_position = current_position;
        }
    }

    /* ---- Phase 4: 急停与恢复动力 ---- */
    td201_stop(axis);
    td201_sleep_ms(50);
    td201_set_duty(axis, 48);

    /* 若堵转检测超时，不做后续顺时针寻零，直接返回超时 */
    if (elapsed_ms >= timeout_ms) {
        return TD201_ERR_TIMEOUT;
    }

    /* ---- Phase 5: 安全顺时针寻零 ---- */
    return td201_home_wait(axis, timeout_ms);
}

/* ------------------------------------------------------------------ */
/* Open-loop                                                           */
/* ------------------------------------------------------------------ */

td201_err_t td201_set_on_time(td201_axis_t *axis, long on_time)
{
    if (on_time < 1 || on_time > 6000000L) {
        return TD201_ERR_RANGE;
    }
    return tx_long(axis, "on", on_time, NULL);
}

td201_err_t td201_set_off_interval(td201_axis_t *axis, long interval_ms)
{
    if (interval_ms < 1 || interval_ms > 600000L) {
        return TD201_ERR_RANGE;
    }
    return tx_long(axis, "off", interval_ms, NULL);
}

td201_err_t td201_set_cycles(td201_axis_t *axis, long cycles)
{
    if (cycles < 1) {
        return TD201_ERR_RANGE;
    }
    return tx_long(axis, "cy", cycles, NULL);
}

td201_err_t td201_run_reverse(td201_axis_t *axis)
{
    return tx_simple(axis, "re", NULL);
}

td201_err_t td201_run_forward(td201_axis_t *axis)
{
    return tx_simple(axis, "fo", NULL);
}

td201_err_t td201_run_bidirectional(td201_axis_t *axis)
{
    return tx_simple(axis, "bi", NULL);
}

/* ------------------------------------------------------------------ */
/* Status                                                              */
/* ------------------------------------------------------------------ */

td201_err_t td201_get_position(td201_axis_t *axis, long *position)
{
    if (!position) {
        return TD201_ERR_INVALID_ARG;
    }
    char resp[TD201_RESP_BUF];
    td201_err_t err = td201_transaction(axis, "cp", NULL, resp, (int)sizeof(resp));
    if (err != TD201_OK) {
        return err;
    }
    long pos = 0;
    if (sscanf(resp, "<%*2ucp %ld", &pos) != 1) {
        return TD201_ERR_PROTOCOL;
    }
    *position = pos;
    return TD201_OK;
}

td201_err_t td201_get_alarm(td201_axis_t *axis, td201_alarm_t *alarm)
{
    if (!alarm) {
        return TD201_ERR_INVALID_ARG;
    }
    char resp[TD201_RESP_BUF];
    td201_err_t err = td201_transaction(axis, "al", NULL, resp, (int)sizeof(resp));
    if (err != TD201_OK) {
        return err;
    }
    int code = 0;
    unsigned int hex = 0;
    if (sscanf(resp, "<%*2dstatus %d (%x)", &code, &hex) != 2 &&
        sscanf(resp, "<%*2dstatus %d (%X)", &code, &hex) != 2) {
        return TD201_ERR_PROTOCOL;
    }
    alarm->alarm_code = code;
    alarm->alarm_hex = hex;
    return TD201_OK;
}

td201_err_t td201_get_status(td201_axis_t *axis, char *out_line, int max_len)
{
    if (!out_line || max_len <= 0) {
        return TD201_ERR_INVALID_ARG;
    }
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    err = td201_flush_rx(axis->dev);
    if (err != TD201_OK) {
        return err;
    }
    char tx[TD201_CMD_BUF];
    int tx_len = format_cmd(axis, "al", NULL, tx, sizeof(tx));
    if (serial_write(axis->dev, tx, tx_len) != tx_len) {
        return TD201_ERR_IO;
    }
    int n = 0;
    err = td201_serial_read_line(axis->dev, out_line, max_len, &n);
    return err;
}

//解析 info 指令的多行回复，根据每行的前缀提取对应的参数值并存储到 td201_info_t 结构体中
static void parse_info_line(const char *line, td201_info_t *info)
{
    long lv = 0;
    int iv = 0;
    if (sscanf(line, "<%*2dfreq %ld", &lv) == 1) {
        info->freq_khz = lv;
    } else if (sscanf(line, "<%*2dvolt %d", &iv) == 1) {
        info->volt = iv;
    } else if (sscanf(line, "<%*2denc %d", &iv) == 1) {
        info->enc_type = iv;
    } else if (sscanf(line, "<%*2dres %ld", &lv) == 1) {
        info->resolution_nm = lv;
    } else if (sscanf(line, "<%*2dswap %d", &iv) == 1) {
        info->swap = iv;
    } else if (sscanf(line, "<%*2dmid %d", &iv) == 1) {
        info->motor_invert = iv;
    } else if (sscanf(line, "<%*2dvel %ld", &lv) == 1) {
        info->velocity = lv;
    } else if (sscanf(line, "<%*2doffset %ld", &lv) == 1) {
        info->home_offset = lv;
    } else if (sscanf(line, "<%*2dlm %ld", &lv) == 1) {
        info->limit_reverse = lv;
    } else if (sscanf(line, "<%*2dlp %ld", &lv) == 1) {
        info->limit_forward = lv;
    } else if (sscanf(line, "<%*2dst %ld", &lv) == 1) {
        info->stroke = lv;
    } else if (sscanf(line, "<%*2dinp %ld", &lv) == 1) {
        info->in_position = lv;
    }
}

td201_err_t td201_get_info(td201_axis_t *axis, td201_info_t *info)
{
    if (!info) {
        return TD201_ERR_INVALID_ARG;
    }
    memset(info, 0, sizeof(*info));

    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    err = td201_flush_rx(axis->dev);
    if (err != TD201_OK) {
        return err;
    }

    char tx[TD201_CMD_BUF];
    int tx_len = format_cmd(axis, "info", NULL, tx, sizeof(tx));
    if (serial_write(axis->dev, tx, tx_len) != tx_len) {
        return TD201_ERR_IO;
    }

    char line[TD201_RESP_BUF];
    int lines_read = 0;
    while (lines_read < TD201_INFO_LINES) {
        int n = 0;
        err = td201_serial_read_line(axis->dev, line, (int)sizeof(line), &n);
        if (err != TD201_OK || n <= 0) {
            break;
        }
        parse_info_line(line, info);
        lines_read++;
    }
    return (lines_read > 0) ? TD201_OK : TD201_ERR_TIMEOUT;
}

td201_err_t td201_get_version(td201_axis_t *axis, long *yymmdd, long *version)
{
    if (!yymmdd || !version) {
        return TD201_ERR_INVALID_ARG;
    }
    char resp[TD201_RESP_BUF];
    td201_err_t err = td201_transaction(axis, "ver", NULL, resp, (int)sizeof(resp));
    if (err != TD201_OK) {
        return err;
    }
    if (sscanf(resp, "<%*2dver %ld %ld", yymmdd, version) != 2) {
        return TD201_ERR_PROTOCOL;
    }
    return TD201_OK;
}

/* ------------------------------------------------------------------ */
/* Configuration                                                     */
/* ------------------------------------------------------------------ */

td201_err_t td201_set_freq(td201_axis_t *axis, int freq_khz)
{
    if (freq_khz < 20 || freq_khz > 100) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "freq", freq_khz);
}

td201_err_t td201_set_duty(td201_axis_t *axis, int duty_percent)
{
    if (duty_percent < 1 || duty_percent > 48) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "duty", duty_percent);
}

td201_err_t td201_set_volt(td201_axis_t *axis, int voltage)
{
    if (voltage < 16 || voltage > 35) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "volt", voltage);
}

td201_err_t td201_set_enc(td201_axis_t *axis, int enc_type)
{
    if (enc_type != 1 && enc_type != 2) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "enc", enc_type);
}

td201_err_t td201_set_res(td201_axis_t *axis, long resolution_nm)
{
    return tx_long(axis, "res", resolution_nm, NULL);
}

td201_err_t td201_set_swap(td201_axis_t *axis, int swap)
{
    if (swap != 0 && swap != 1) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "swap", swap);
}

td201_err_t td201_set_mid(td201_axis_t *axis, int invert)
{
    if (invert != 0 && invert != 1) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "mid", invert);
}

td201_err_t td201_set_vel(td201_axis_t *axis, int velocity)
{
    if (velocity < 1 || velocity > 100) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "vel", velocity);
}

td201_err_t td201_set_offset(td201_axis_t *axis, long offset)
{
    if (offset < -2147000000L || offset > 2147000000L) {
        return TD201_ERR_RANGE;
    }
    return tx_long(axis, "offset", offset, NULL);
}

td201_err_t td201_set_message(td201_axis_t *axis, int on_off)
{
    if (on_off != 0 && on_off != 1) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "message", on_off);
}

td201_err_t td201_set_in_position(td201_axis_t *axis, int inp_value)
{
    if (inp_value < 0 || inp_value > 1000) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "inp", inp_value);
}

td201_err_t td201_set_baudrate(td201_axis_t *axis, int baudrate)
{
    if (baudrate < 2400 || baudrate > 921600) {
        return TD201_ERR_RANGE;
    }
    return tx_int(axis, "baudrate", baudrate);
}

td201_err_t td201_save_to_flash(td201_axis_t *axis)
{
    return tx_simple(axis, "save", NULL);
}

td201_err_t td201_reset(td201_axis_t *axis)
{
    td201_err_t err = check_axis(axis);
    if (err != TD201_OK) {
        return err;
    }
    err = td201_flush_rx(axis->dev);
    if (err != TD201_OK) {
        return err;
    }
    char tx[TD201_CMD_BUF];
    int tx_len = format_cmd(axis, "reset", NULL, tx, sizeof(tx));
    if (serial_write(axis->dev, tx, tx_len) != tx_len) {
        return TD201_ERR_IO;
    }
    char resp[TD201_RESP_BUF];
    int n = 0;
    err = td201_serial_read_line(axis->dev, resp, (int)sizeof(resp), &n);
    if (err != TD201_OK) {
        return err;
    }
    /* Axis 1 may reply with <ready\r instead of <01reset\r */
    if (response_matches(axis, "reset", resp) || strncmp(resp, "<ready", 6) == 0) {
        return TD201_OK;
    }
    return TD201_ERR_PROTOCOL;
}

td201_err_t td201_set_kp(td201_axis_t *axis, int kp_value)
{
    td201_err_t err = check_gain(kp_value);
    if (err != TD201_OK) {
        return err;
    }
    return tx_int(axis, "kp", kp_value);
}

td201_err_t td201_set_ki(td201_axis_t *axis, int ki_value)
{
    td201_err_t err = check_gain(ki_value);
    if (err != TD201_OK) {
        return err;
    }
    return tx_int(axis, "ki", ki_value);
}

td201_err_t td201_set_kd(td201_axis_t *axis, int kd_value)
{
    td201_err_t err = check_gain(kd_value);
    if (err != TD201_OK) {
        return err;
    }
    return tx_int(axis, "kd", kd_value);
}

td201_err_t td201_set_kf(td201_axis_t *axis, int kf_value)
{
    td201_err_t err = check_gain(kf_value);
    if (err != TD201_OK) {
        return err;
    }
    return tx_int(axis, "kf", kf_value);
}
