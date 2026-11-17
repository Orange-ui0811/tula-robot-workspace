#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32) || defined(_WIN64)
#include <windows.h>
#define SLEEP_MS(x) Sleep(x)
#else
#include <unistd.h>
#define SLEEP_MS(x) usleep((x) * 1000)
#endif

#include "td201.h"
#include "tula50.h"

typedef enum {
    STAGE_MENU = 0,
    STAGE_INFO = 1,
    STAGE_HOME = 2,
    STAGE_MOTION = 3,
    STAGE_SAFE_HOME = 4,
    STAGE_ZAXIS = 5,
    STAGE_BAUD_TEST = 6,
    STAGE_EXIT = 99
} test_stage_t;

static void print_err(const char *what, td201_err_t err) {
    printf("  [错误] %s 失败: %s (%d)\n", what, td201_strerror(err), (int)err);
}

static void get_user_input(char *buf, int max_len) {
    if (fgets(buf, max_len, stdin) != NULL) {
        buf[strcspn(buf, "\r\n")] = '\0';
    } else {
        buf[0] = '\0';
    }
}

static long prompt_long(const char *prompt_text, long default_val) {
    char input[64];
    printf("%s (直接回车默认 %ld): ", prompt_text, default_val);
    get_user_input(input, sizeof(input));
    if (strlen(input) > 0) {
        return atol(input);
    }
    return default_val;
}

/**
 * @brief 波特率即时切换闭环测试 (Loopback Revert Pattern)
 *
 * 严格无副作用：仅在 RAM 中修改波特率，绝不写入 Flash。
 * 状态机流程：
 *   115200 open → bind → set_baudrate(460800) → close → reopen(460800) →
 *   5× get_position → set_baudrate(115200) → close → reopen(115200) → verify → done
 *
 * @param port_name  串口名称 (如 "COM5")
 * @param axis_id    目标轴硬件地址 (1~3)
 * @return 0 全部通过，非 0 表示失败步骤编号 (1-based)
 */
static int test_baudrate_modification(const char *port_name, uint8_t axis_id) {
    printf("\n");
    printf("################################################################\n");
    printf("###  [BAUD TEST] 波特率即时切换闭环测试开始\n");
    printf("###  串口: %s | 轴: %d | 模式: RAM-Only (不写入 Flash)\n", port_name, axis_id);
    printf("################################################################\n\n");

    int ret = 0;
    const int BAUD_ORIGINAL  = 115200;
    const int BAUD_HIGH      = 460800;

    /* =========================================================================
     * Stage 1: 初始连接 (115200)
     * ========================================================================= */
    printf("[BAUD TEST] Stage 1/6: 以 %d bps 打开串口并绑定轴 %d...\n",
           BAUD_ORIGINAL, axis_id);

    td201_dev_t *dev = NULL;
    td201_err_t err = td201_open(port_name, BAUD_ORIGINAL, &dev);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 1 打开串口", err);
        return 1;
    }
    printf("[BAUD TEST]   √ 串口 %s @ %d bps 打开成功。\n", port_name, BAUD_ORIGINAL);

    td201_axis_t axis;
    err = td201_axis_bind(dev, axis_id, &axis);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 1 绑定轴", err);
        td201_close(dev);
        return 1;
    }
    printf("[BAUD TEST]   √ 轴 %d 绑定成功。\n", axis_id);

    /* =========================================================================
     * Stage 2: 下发新波特率 (460800, RAM only)
     * ========================================================================= */
    printf("[BAUD TEST] Stage 2/6: 下发波特率切换指令 -> %d bps (RAM 即时生效)...\n",
           BAUD_HIGH);

    err = td201_set_baudrate(&axis, BAUD_HIGH);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 2 设置波特率", err);
        td201_axis_unbind(&axis);
        td201_close(dev);
        return 2;
    }
    printf("[BAUD TEST]   √ td201_set_baudrate(%d) 指令已成功送达。\n", BAUD_HIGH);
    printf("[BAUD TEST]   ! 注意: 未调用 td201_save_to_flash，故障重启后将自动恢复 %d bps。\n",
           BAUD_ORIGINAL);

    /* =========================================================================
     * Stage 3: 断开并以新波特率重连
     * ========================================================================= */
    printf("[BAUD TEST] Stage 3/6: 断开旧连接，以 %d bps 重连...\n", BAUD_HIGH);

    td201_axis_unbind(&axis);
    td201_close(dev);
    dev = NULL;
    printf("[BAUD TEST]   √ 旧连接已彻底释放。\n");

    printf("[BAUD TEST]   等待 150 ms 确保硬件总线电平稳定...\n");
    SLEEP_MS(150);

    err = td201_open(port_name, BAUD_HIGH, &dev);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 3 以高波特率重连", err);
        return 3;
    }
    printf("[BAUD TEST]   √ 串口 %s @ %d bps 重连成功。\n", port_name, BAUD_HIGH);

    err = td201_axis_bind(dev, axis_id, &axis);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 3 重连后绑定轴", err);
        td201_close(dev);
        return 3;
    }
    printf("[BAUD TEST]   √ 轴 %d 在高波特率下重新绑定成功。\n", axis_id);

    /* =========================================================================
     * Stage 4: 高频验证 (5 次连续位置读取)
     * ========================================================================= */
    printf("[BAUD TEST] Stage 4/6: 高频验证 — 连续 5 次 td201_get_position @ %d bps...\n",
           BAUD_HIGH);

    int fail_count = 0;
    for (int i = 1; i <= 5; i++) {
        long pos = 0;
        err = td201_get_position(&axis, &pos);
        if (err == TD201_OK) {
            printf("[BAUD TEST]   [%d/5] √ position = %ld counts\n", i, pos);
        } else {
            printf("[BAUD TEST]   [%d/5] ✗ 失败: %s (%d)\n",
                   i, td201_strerror(err), (int)err);
            fail_count++;
        }
        if (i < 5) {
            SLEEP_MS(20);
        }
    }

    if (fail_count > 0) {
        printf("[BAUD TEST]   ! 高频验证: %d/5 次失败，高波特率通讯不稳定。\n", fail_count);
        /* 仍然尝试还原，不要让设备留在高波特率状态 */
        ret = 4;
    } else {
        printf("[BAUD TEST]   √ 高频验证全部通过 (%d bps 通讯正常)。\n", BAUD_HIGH);
    }

    /* =========================================================================
     * Stage 5: 安全还原 (切回 115200)
     * ========================================================================= */
    printf("[BAUD TEST] Stage 5/6: 安全还原 — 将波特率切回 %d bps...\n", BAUD_ORIGINAL);

    err = td201_set_baudrate(&axis, BAUD_ORIGINAL);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 5 还原波特率指令发送", err);
        printf("[BAUD TEST]   !!! 严重警告: 设备可能停留在 %d bps !!!\n", BAUD_HIGH);
        td201_axis_unbind(&axis);
        td201_close(dev);
        return 5;
    }
    printf("[BAUD TEST]   √ td201_set_baudrate(%d) 还原指令已送达。\n", BAUD_ORIGINAL);

    td201_axis_unbind(&axis);
    td201_close(dev);
    dev = NULL;
    printf("[BAUD TEST]   √ 高波特率连接已关闭。\n");

    printf("[BAUD TEST]   等待 150 ms 确保总线稳定...\n");
    SLEEP_MS(150);

    /* =========================================================================
     * Stage 6: 终极确认 (以 115200 重连并读取状态)
     * ========================================================================= */
    printf("[BAUD TEST] Stage 6/6: 终极确认 — 以 %d bps 重连并验证...\n", BAUD_ORIGINAL);

    err = td201_open(port_name, BAUD_ORIGINAL, &dev);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 6 以原始波特率重连", err);
        printf("[BAUD TEST]   !!! 致命: 无法以 %d bps 重连，设备可能失联 !!!\n",
               BAUD_ORIGINAL);
        return 6;
    }
    printf("[BAUD TEST]   √ 串口 %s @ %d bps 还原重连成功。\n", port_name, BAUD_ORIGINAL);

    err = td201_axis_bind(dev, axis_id, &axis);
    if (err != TD201_OK) {
        print_err("[BAUD TEST] Stage 6 还原后绑定轴", err);
        td201_close(dev);
        return 6;
    }
    printf("[BAUD TEST]   √ 轴 %d 在原始波特率下绑定成功。\n", axis_id);

    /* 读取一次位置做最终确认 */
    {
        long pos = 0;
        err = td201_get_position(&axis, &pos);
        if (err == TD201_OK) {
            printf("[BAUD TEST]   √ 终极确认: position = %ld counts，通讯完全正常。\n", pos);
        } else {
            printf("[BAUD TEST]   ! 终极确认: 位置读取失败 (%s)，但串口已重连。\n",
                   td201_strerror(err));
        }
    }

    /* 清理 */
    td201_axis_unbind(&axis);
    td201_close(dev);
    dev = NULL;

    if (ret == 0) {
        printf("\n[BAUD TEST] ============ 测试全部通过 ============\n");
        printf("[BAUD TEST] 波特率切换: %d -> %d -> %d bps 闭环验证成功。\n",
               BAUD_ORIGINAL, BAUD_HIGH, BAUD_ORIGINAL);
        printf("[BAUD TEST] 未使用 Flash 写入，硬件状态与测试前完全一致。\n");
    } else {
        printf("\n[BAUD TEST] ============ 测试失败 (阶段 %d) ============\n", ret);
    }
    printf("################################################################\n\n");

    return ret;
}

static double prompt_double(const char *prompt_text, double default_val) {
    char input[64];
    printf("%s (直接回车默认 %.1f): ", prompt_text, default_val);
    get_user_input(input, sizeof(input));
    if (strlen(input) > 0) {
        return atof(input);
    }
    return default_val;
}

int main(void) {
    printf("=================================================\n");
    printf("     TD-201 三轴交互式控制终端 (主菜单模式)\n");
    printf("=================================================\n\n");

    // --- 初始化：配置串口与三轴绑定 ---
    char port_name[32] = "COM5";
    printf("请输入串口号 (默认 COM5): ");
    char input_port[32];
    get_user_input(input_port, sizeof(input_port));
    if (strlen(input_port) > 0) strcpy(port_name, input_port);

    int baudrate = 115200;
    td201_dev_t *controller = NULL;
    td201_err_t err = td201_open(port_name, baudrate, &controller);
    if (err != TD201_OK) {
        print_err("打开串口", err);
        return 1;
    }
    printf("√ 串口 %s 成功打开。\n", port_name);

    // 绑定物理控制器上的三个电机通道
    td201_axis_t axis1, axis2, axis3;
    td201_err_t err_bind;

    err_bind = td201_axis_bind(controller, 1, &axis1);
    if (err_bind != TD201_OK) {
        print_err("绑定轴 1", err_bind);
        td201_close(controller);
        return 1;
    }

    err_bind = td201_axis_bind(controller, 2, &axis2);
    if (err_bind != TD201_OK) {
        print_err("绑定轴 2", err_bind);
        td201_close(controller);
        return 1;
    }

    err_bind = td201_axis_bind(controller, 3, &axis3);
    if (err_bind != TD201_OK) {
        print_err("绑定轴 3 (Z轴)", err_bind);
        td201_close(controller);
        return 1;
    }

    printf("√ 已成功绑定 轴 1, 轴 2 和 轴 3 (Z轴)。\n");

    td201_axis_t *active_axis = &axis1;
    test_stage_t current_stage = STAGE_MENU;

    // --- 状态机主循环 ---
    while (current_stage != STAGE_EXIT) {
        
        // ------------------ 主菜单逻辑 ------------------
        if (current_stage == STAGE_MENU) {
            printf("\n=================== 主菜单 ===================\n");
            printf("  1. 读取双轴信息与物理位置\n");
            printf("  2. 原厂指令回零 (标准 HOME)\n");
            printf("  3. 闭环绝对运动测试\n");
            printf("  4. 柔性触边寻零安全测试 (Safe Soft-Homing)\n");
            printf("  5. Z轴直线闭环运动测试 (动态分辨率)\n");
            printf("  6. 波特率即时切换闭环测试 (RAM-Only)\n");
            printf("  0. 退出程序\n");
            printf("==============================================\n");
            
            long choice = prompt_long("请输入功能编号", 0);
            if (choice == 1) current_stage = STAGE_INFO;
            else if (choice == 2) current_stage = STAGE_HOME;
            else if (choice == 3) current_stage = STAGE_MOTION;
            else if (choice == 4) current_stage = STAGE_SAFE_HOME;
            else if (choice == 5) current_stage = STAGE_ZAXIS;
            else if (choice == 6) current_stage = STAGE_BAUD_TEST;
            else if (choice == 0) {
                current_stage = STAGE_EXIT;
                continue;
            }
            else {
                printf("  ! 无效的选择，请重新输入。\n");
                continue;
            }
        }

        printf("\n-------------------------------------------------\n");

        // ------------------ 功能执行逻辑 ------------------
        switch (current_stage) {
            case STAGE_INFO:
                printf(">>> 功能 1: 双轴设备信息与物理位置读取 <<<\n\n");

                td201_info_t info1, info2;
                long pos1 = 0, pos2 = 0;
                td201_err_t e_info, e_pos;

                // --- 轴 1 参数与位置读取 ---
                printf("[轴 1]: \n");
                e_info = td201_get_info(&axis1, &info1);
                if (e_info == TD201_OK) {
                    printf("  -> 参数配置: 驱动电压 = %dV, 编码器分辨率 = %ld nm/pulse\n", info1.volt, info1.resolution_nm);
                    printf("  -> 软件限位: 反向限位(逆) = %ld counts, 正向限位(顺) = %ld counts\n", info1.limit_reverse, info1.limit_forward);
                } else {
                    printf("  -> 参数配置: 读取失败 (%s)\n", td201_strerror(e_info));
                }

                SLEEP_MS(50);
                td201_flush_rx(controller);

                e_pos = td201_get_position(&axis1, &pos1);
                if (e_pos == TD201_OK) {
                    printf("  -> 物理坐标: 当前编码器位置 = %ld counts\n", pos1);
                } else {
                    printf("  -> 物理坐标: 位置读取失败 (%s)\n", td201_strerror(e_pos));
                }

                // --- 轴 2 参数与位置读取 ---
                printf("\n[轴 2]: \n");
                e_info = td201_get_info(&axis2, &info2);
                if (e_info == TD201_OK) {
                    printf("  -> 参数配置: 驱动电压 = %dV, 编码器分辨率 = %ld nm/pulse\n", info2.volt, info2.resolution_nm);
                    printf("  -> 软件限位: 反向限位(逆) = %ld counts, 正向限位(顺) = %ld counts\n", info2.limit_reverse, info2.limit_forward);
                } else {
                    printf("  -> 参数配置: 读取失败 (%s) (若未接双轴可忽略)\n", td201_strerror(e_info));
                }

                SLEEP_MS(50);
                td201_flush_rx(controller);

                e_pos = td201_get_position(&axis2, &pos2);
                if (e_pos == TD201_OK) {
                    printf("  -> 物理坐标: 当前编码器位置 = %ld counts\n", pos2);
                } else {
                    printf("  -> 物理坐标: 位置读取失败 (%s) (若未接双轴可忽略)\n", td201_strerror(e_pos));
                }
                break;

            case STAGE_HOME: {
                printf(">>> 功能 2: 报警检查与双轴回零(Homing) <<<\n\n");

                td201_alarm_t alarm1, alarm2;
                int need_home = 0;

                // 检查轴 1
                if (td201_get_alarm(&axis1, &alarm1) == TD201_OK) {
                    printf("  [轴 1] 报警寄存器: 0x%X\n", alarm1.alarm_hex);
                    td201_print_alarm_details(alarm1.alarm_hex);
                    if (alarm1.alarm_hex & TD201_STATUS_HOME_MISSING) need_home = 1;
                }
                // 检查轴 2
                if (td201_get_alarm(&axis2, &alarm2) == TD201_OK) {
                    printf("  [轴 2] 报警寄存器: 0x%X\n", alarm2.alarm_hex);
                    td201_print_alarm_details(alarm2.alarm_hex);
                    if (alarm2.alarm_hex & TD201_STATUS_HOME_MISSING) need_home = 1;
                }

                if (need_home) {
                    printf("\n  ! 提示: 检测到至少一个轴存在 HOME MISSING (0x1000) 状态。\n");
                } else {
                    printf("\n  √ 提示: 双轴均无 HOME MISSING 报警(仍可手动执行回零)。\n");
                }

                /* ---- 回零轴选择 ---- */
                int home_sel = 0;
                {
                    printf("  选择回零电机:\n");
                    printf("    0 = 跳过回零\n");
                    printf("    1 = 仅轴 1 回零\n");
                    printf("    2 = 仅轴 2 回零\n");
                    printf("    3 = 轴 1 与轴 2 均回零\n");
                    long _sel = prompt_long("  请输入选项", 0);
                    if (_sel < 0 || _sel > 3) {
                        printf("  ! 无效选项 %ld，视为跳过。\n", _sel);
                        _sel = 0;
                    }
                    home_sel = (int)_sel;
                }
                int do_home1 = (home_sel == 1 || home_sel == 3);
                int do_home2 = (home_sel == 2 || home_sel == 3);

                /* ================================================================
                 *  双轴并行回零 (非阻塞 Fire-and-Forget + 统一外部状态机轮询)
                 * ================================================================ */
                if (do_home1 && do_home2) {
                    const long parallel_timeout_ms = 10000;

                    printf("\n>>> 正在并行执行 [轴 1] 和 [轴 2] 的回零操作...\n");
                    printf("  (非阻塞下发, 统一轮询超时 %ld 秒)\n", parallel_timeout_ms / 1000);

                    /* --- Fire-and-Forget: 连续下发非阻塞回零指令 --- */
                    err = td201_home(&axis1);
                    if (err != TD201_OK) {
                        print_err("轴 1 下发回零指令", err);
                    }
                    err = td201_home(&axis2);
                    if (err != TD201_OK) {
                        print_err("轴 2 下发回零指令", err);
                    }

                    /* --- 统一轮询等待循环 --- */
                    long elapsed = 0;
                    int home1_ok = 0, home2_ok = 0;
                    int fatal1 = 0, fatal2 = 0;

                    while (elapsed < parallel_timeout_ms) {
                        SLEEP_MS(100);
                        elapsed += 100;

                        /* 轮询轴 1 */
                        if (!home1_ok && !fatal1) {
                            td201_alarm_t a1;
                            if (td201_get_alarm(&axis1, &a1) == TD201_OK) {
                                if (a1.alarm_hex & TD201_FATAL_MASK) {
                                    printf("  ! 警告: 轴 1 检测到严重错误 (0x%X)\n", a1.alarm_hex);
                                    td201_print_alarm_details(a1.alarm_hex);
                                    fatal1 = 1;
                                } else if (!(a1.alarm_hex & TD201_STATUS_HOME_MISSING)) {
                                    home1_ok = 1;
                                    printf("  [轴 1] HOME_MISSING 已清除, 回零完成。\n");
                                }
                            }
                        }

                        /* 轮询轴 2 */
                        if (!home2_ok && !fatal2) {
                            td201_alarm_t a2;
                            if (td201_get_alarm(&axis2, &a2) == TD201_OK) {
                                if (a2.alarm_hex & TD201_FATAL_MASK) {
                                    printf("  ! 警告: 轴 2 检测到严重错误 (0x%X)\n", a2.alarm_hex);
                                    td201_print_alarm_details(a2.alarm_hex);
                                    fatal2 = 1;
                                } else if (!(a2.alarm_hex & TD201_STATUS_HOME_MISSING)) {
                                    home2_ok = 1;
                                    printf("  [轴 2] HOME_MISSING 已清除, 回零完成。\n");
                                }
                            }
                        }

                        /* 任一轴发生严重错误时立即退出 */
                        if (fatal1 || fatal2) {
                            printf("  ! 因严重错误中止并行回零轮询。\n");
                            break;
                        }

                        /* 双轴均回零完成 */
                        if (home1_ok && home2_ok) {
                            printf("  √ 双轴并行回零完成 (耗时 %ld ms)。\n", elapsed);
                            break;
                        }
                    }

                    /* 超时处理 */
                    if (elapsed >= parallel_timeout_ms && !(home1_ok && home2_ok)) {
                        printf("  ! 警告: 双轴并行回零超时 (%ld ms)\n", parallel_timeout_ms);
                        if (!home1_ok) printf("    轴 1: 回零未完成\n");
                        if (!home2_ok) printf("    轴 2: 回零未完成\n");
                    }

                    /* 循环结束后打印两轴物理归零坐标 */
                    printf("\n  --- 归零坐标 ---\n");
                    {
                        long p1, p2;
                        if (td201_get_position(&axis1, &p1) == TD201_OK) {
                            printf("  [轴 1] 物理归零坐标: %ld counts\n", p1);
                        } else {
                            printf("  [轴 1] 物理归零坐标: 读取失败\n");
                        }
                        if (td201_get_position(&axis2, &p2) == TD201_OK) {
                            printf("  [轴 2] 物理归零坐标: %ld counts\n", p2);
                        } else {
                            printf("  [轴 2] 物理归零坐标: 读取失败\n");
                        }
                    }

                } else if (do_home1) {
                    /* 单轴回零 (轴 1 单独, 保留阻塞等待以简化) */
                    const long home_timeout_ms = 30000;
                    printf("\n  --- 执行原厂指令回零 (最长 %ld 秒) ---\n", home_timeout_ms / 1000);
                    printf("  [轴 1] 正在回零...\n");
                    err = td201_home_wait(&axis1, home_timeout_ms);
                    if (err == TD201_OK) {
                        long pos;
                        if (td201_get_position(&axis1, &pos) == TD201_OK) {
                            printf("  [轴 1] √ 回零成功，当前位置: %ld counts\n", pos);
                        } else {
                            printf("  [轴 1] √ 回零成功 (位置读取失败)\n");
                        }
                    } else {
                        printf("  [轴 1] ✗ 回零失败: %s\n", td201_strerror(err));
                        td201_alarm_t a;
                        if (td201_get_alarm(&axis1, &a) == TD201_OK) {
                            td201_print_alarm_details(a.alarm_hex);
                        }
                    }

                } else if (do_home2) {
                    /* 单轴回零 (轴 2 单独) */
                    const long home_timeout_ms = 30000;
                    printf("\n  --- 执行原厂指令回零 (最长 %ld 秒) ---\n", home_timeout_ms / 1000);
                    printf("  [轴 2] 正在回零...\n");
                    err = td201_home_wait(&axis2, home_timeout_ms);
                    if (err == TD201_OK) {
                        long pos;
                        if (td201_get_position(&axis2, &pos) == TD201_OK) {
                            printf("  [轴 2] √ 回零成功，当前位置: %ld counts\n", pos);
                        } else {
                            printf("  [轴 2] √ 回零成功 (位置读取失败)\n");
                        }
                    } else {
                        printf("  [轴 2] ✗ 回零失败: %s\n", td201_strerror(err));
                        td201_alarm_t a;
                        if (td201_get_alarm(&axis2, &a) == TD201_OK) {
                            td201_print_alarm_details(a.alarm_hex);
                        }
                    }
                } else {
                    printf("  已跳过回零。\n");
                }
                break;
            }

            case STAGE_MOTION: {
                printf(">>> 功能 3: 闭环运动测试 (单轴/双轴并行) <<<\n\n");

                /* ---- 轴选择 ---- */
                long axis_sel = prompt_long(
                    "  请选择要调试的轴 (1=轴1单动, 2=轴2单动, 3=双轴联动) (默认 1)",
                    1);
                if (axis_sel < 1 || axis_sel > 3) {
                    printf("  ! 无效选择 %ld，默认使用轴 1 单动。\n", axis_sel);
                    axis_sel = 1;
                }

                double target_deg1 = 0.0, target_deg2 = 0.0;
                int move1 = 0, move2 = 0;

                if (axis_sel == 1) {
                    target_deg1 = prompt_double("  请输入轴 1 的绝对目标角度 (度)", 0.0);
                    move1 = 1;
                    active_axis = &axis1;  /* 保持与其他 stage 兼容 */
                } else if (axis_sel == 2) {
                    target_deg2 = prompt_double("  请输入轴 2 的绝对目标角度 (度)", 0.0);
                    move2 = 1;
                    active_axis = &axis2;
                } else {
                    /* 双轴联动 */
                    target_deg1 = prompt_double("  请输入轴 1 的目标角度 (度)", 0.0);
                    target_deg2 = prompt_double("  请输入轴 2 的目标角度 (度)", 0.0);
                    move1 = 1;
                    move2 = 1;
                    /* active_axis 保持不变, 不影响其他 stage */
                }

                /* ================================================================
                 *  非阻塞 Fire-and-Forget 下发
                 * ================================================================ */
                if (move1) {
                    printf("  [轴 1] 正在以非阻塞方式下发角度指令 (目标: %.1f 度)...\n", target_deg1);
                    err = tula50_set_angle(&axis1, target_deg1);
                    if (err != TD201_OK) {
                        print_err("轴 1 下发角度指令", err);
                    }
                }
                if (move2) {
                    printf("  [轴 2] 正在以非阻塞方式下发角度指令 (目标: %.1f 度)...\n", target_deg2);
                    err = tula50_set_angle(&axis2, target_deg2);
                    if (err != TD201_OK) {
                        print_err("轴 2 下发角度指令", err);
                    }
                }

                /* ================================================================
                 *  统一多轴运动轮询循环 (外部状态机)
                 * ================================================================ */
                const long motion_timeout_ms = 30000;
                long elapsed = 0;
                int done1 = (move1 == 0);  /* 不参与运动则视为已完成 */
                int done2 = (move2 == 0);
                int fatal1 = 0, fatal2 = 0;

                printf("\n  --- 开始多轴运动轮询 (SLEEP_MS=50, 超时 %ld 秒) ---\n",
                       motion_timeout_ms / 1000);

                while (elapsed < motion_timeout_ms) {
                    SLEEP_MS(50);
                    elapsed += 50;

                    /* 轮询轴 1 */
                    if (!done1 && !fatal1) {
                        td201_alarm_t a1;
                        if (td201_get_alarm(&axis1, &a1) == TD201_OK) {
                            if (a1.alarm_hex & TD201_FATAL_MASK) {
                                printf("  ! 警告: 轴 1 运动中出现严重错误 (0x%X)\n", a1.alarm_hex);
                                td201_print_alarm_details(a1.alarm_hex);
                                fatal1 = 1;
                            } else if (!(a1.alarm_hex & TD201_STATUS_MOTOR_RUNNING)) {
                                /* MOTOR_RUNNING (0x8000) 清除 → 电机停止 */
                                done1 = 1;
                                printf("  [轴 1] 运动完成 (MOTOR_RUNNING 已清除, 耗时 %ld ms)\n", elapsed);
                            }
                        }
                    }

                    /* 轮询轴 2 */
                    if (!done2 && !fatal2) {
                        td201_alarm_t a2;
                        if (td201_get_alarm(&axis2, &a2) == TD201_OK) {
                            if (a2.alarm_hex & TD201_FATAL_MASK) {
                                printf("  ! 警告: 轴 2 运动中出现严重错误 (0x%X)\n", a2.alarm_hex);
                                td201_print_alarm_details(a2.alarm_hex);
                                fatal2 = 1;
                            } else if (!(a2.alarm_hex & TD201_STATUS_MOTOR_RUNNING)) {
                                done2 = 1;
                                printf("  [轴 2] 运动完成 (MOTOR_RUNNING 已清除, 耗时 %ld ms)\n", elapsed);
                            }
                        }
                    }

                    /* 任一轴出现严重错误时退出轮询 */
                    if (fatal1 || fatal2) {
                        printf("  ! 因严重错误中止运动轮询。\n");
                        break;
                    }

                    /* 全部参与运动的轴均完成 */
                    if (done1 && done2) {
                        printf("  √ 所有运动轴已完成 (总耗时 %ld ms)。\n", elapsed);
                        break;
                    }
                }

                /* 超时处理 */
                if (elapsed >= motion_timeout_ms && !(done1 && done2)) {
                    printf("  ! 警告: 运动超时 (%ld ms)\n", motion_timeout_ms);
                    if (!done1 && move1) printf("    轴 1: 未完成\n");
                    if (!done2 && move2) printf("    轴 2: 未完成\n");
                }

                /* ================================================================
                 *  运动结束后打印各轴实际角度与目标的偏差
                 * ================================================================ */
                printf("\n  --- 运动结果汇总 ---\n");
                if (move1) {
                    double cur1 = 0.0;
                    if (tula50_get_angle(&axis1, &cur1) == TD201_OK) {
                        printf("  [轴 1] 目标: %7.2f 度, 实际到达: %7.2f 度, 偏差: %+.2f 度\n",
                               target_deg1, cur1, cur1 - target_deg1);
                    } else {
                        printf("  [轴 1] 角度读取失败\n");
                    }
                }
                if (move2) {
                    double cur2 = 0.0;
                    if (tula50_get_angle(&axis2, &cur2) == TD201_OK) {
                        printf("  [轴 2] 目标: %7.2f 度, 实际到达: %7.2f 度, 偏差: %+.2f 度\n",
                               target_deg2, cur2, cur2 - target_deg2);
                    } else {
                        printf("  [轴 2] 角度读取失败\n");
                    }
                }
                break;
            }

            case STAGE_SAFE_HOME: {
                printf(">>> 功能 4: 柔性触边寻零安全测试 (Safe Soft-Homing) <<<\n\n");

                long cal_axis_sel = prompt_long("  请选择要验证的轴 (输入 1 或 2)", active_axis->axis_id);
                active_axis = (cal_axis_sel == 2) ? &axis2 : &axis1;
                printf("  √ 已切换: 安全寻零将针对 [轴 %d] 执行。\n", active_axis->axis_id);

                long timeout = prompt_long("  请输入最大等待超时时间 (ms)", 30000);

                long dir_input = prompt_long("  请输入寻死点方向 (0=反转re, 1=正转fo)", 1);
                int search_dir = (dir_input == 0) ? 0 : 1;

                long duty_input = prompt_long("  请输入寻死点占空比 (建议重载轴输入 35~40)", 35);
                int search_duty = (int)duty_input;

                const char *dir_str = (search_dir == 1) ? "正转(fo/顺时针)" : "反转(re/逆时针)";

                printf("\n  [轴 %d] 正在执行柔性触边寻零 (最长等待 %ld ms)...\n", active_axis->axis_id, timeout);
                printf("  (参数: 方向=%s, 占空比=%d%%, 抗抖动连续3次位置变化≤1判定堵转)\n", dir_str, search_duty);
                
                err = td201_safe_home_wait(active_axis, timeout, search_dir, search_duty);

                if (err == TD201_OK) {
                    long pos;
                    if (td201_get_position(active_axis, &pos) == TD201_OK) {
                        printf("\n  √ 安全寻零成功！当前绝对物理位置: %ld counts\n", pos);
                    } else {
                        printf("\n  √ 安全寻零成功 (位置读取失败)\n");
                    }
                } else {
                    printf("\n  ✗ 安全寻零失败: %s\n", td201_strerror(err));
                    td201_alarm_t a;
                    if (td201_get_alarm(active_axis, &a) == TD201_OK) {
                        td201_print_alarm_details(a.alarm_hex);
                    }
                }
                break;
            }

            case STAGE_BAUD_TEST: {
                printf(">>> 功能 6: 波特率即时切换闭环测试 <<<\n\n");

                /* 选择用于测试的轴 */
                long baud_axis_sel = prompt_long(
                    "  请选择用于波特率测试的轴 (1=轴1, 2=轴2, 3=轴3) (默认 1)",
                    1);
                if (baud_axis_sel < 1 || baud_axis_sel > 3) {
                    printf("  ! 无效选择 %ld，默认使用轴 1。\n", baud_axis_sel);
                    baud_axis_sel = 1;
                }

                /* 波特率测试期间需要独占串口，所以先临时解绑并关闭当前连接 */
                printf("  [提示] 波特率测试需要独占串口资源，正在临时释放当前连接...\n");

                td201_axis_unbind(&axis1);
                td201_axis_unbind(&axis2);
                td201_axis_unbind(&axis3);
                td201_close(controller);
                controller = NULL;

                printf("  [提示] 当前连接已释放。开始执行波特率闭环测试...\n");

                int baud_result = test_baudrate_modification(port_name, (uint8_t)baud_axis_sel);

                if (baud_result != 0) {
                    printf("  ! 波特率测试在阶段 %d 失败，详见上方日志。\n", baud_result);
                } else {
                    printf("  √ 波特率测试全部通过。\n");
                }

                /* 测试完成，重新建立原始连接以恢复主菜单可用状态 */
                printf("  [提示] 正在重新建立原始连接 (%s @ %d)...\n", port_name, baudrate);
                err = td201_open(port_name, baudrate, &controller);
                if (err != TD201_OK) {
                    print_err("重新打开串口", err);
                    printf("  !!! 致命: 无法恢复串口连接，程序将退出。\n");
                    return 1;
                }
                err = td201_axis_bind(controller, 1, &axis1);
                if (err != TD201_OK) { print_err("重新绑定轴 1", err); td201_close(controller); return 1; }
                err = td201_axis_bind(controller, 2, &axis2);
                if (err != TD201_OK) { print_err("重新绑定轴 2", err); td201_close(controller); return 1; }
                err = td201_axis_bind(controller, 3, &axis3);
                if (err != TD201_OK) { print_err("重新绑定轴 3", err); td201_close(controller); return 1; }
                printf("  √ 串口连接与三轴绑定已恢复，主菜单可用。\n");
                break;
            }

            case STAGE_ZAXIS: {
                printf(">>> 功能 5: Z轴直线闭环运动测试 (轴 3) <<<\n\n");

                double target_mm = prompt_double("请输入Z轴目标位置 (mm)", 10.0);
                double resolution = prompt_double("请输入Z轴编码器分辨率 (脉冲数/mm)", 1000.0);
                long timeout_ms = prompt_long("请输入超时时间 (ms)", 5000);

                printf("\n  [轴 3 (Z轴)] 正在移动至 %.2f mm (分辨率: %.1f pulses/mm, 最长等待 %ld ms)...\n",
                       target_mm, resolution, timeout_ms);

                err = tula50_move_physical_wait(&axis3, target_mm, resolution, timeout_ms);

                if (err == TD201_OK) {
                    double current_mm = 0.0;
                    if (tula50_get_physical(&axis3, resolution, &current_mm) == TD201_OK) {
                        printf("  √ Z轴运动完成，实际到达: %.2f mm (目标: %.2f mm, 偏差: %.3f mm)\n",
                               current_mm, target_mm, current_mm - target_mm);
                    } else {
                        printf("  √ Z轴运动完成 (位置读取失败)\n");
                    }
                } else {
                    printf("  ✗ Z轴运动失败: %s\n", td201_strerror(err));
                    td201_alarm_t a;
                    if (td201_get_alarm(&axis3, &a) == TD201_OK) {
                        td201_print_alarm_details(a.alarm_hex);
                    }
                }
                break;
            }

            default:
                break;
        }

        // --- 执行完毕后统一阻塞，等待返回主菜单 ---
        printf("\n(本阶段测试执行完毕，按回车键返回主菜单...)");
        char dummy[32];
        get_user_input(dummy, sizeof(dummy));
        
        current_stage = STAGE_MENU;
    }

    // --- 退出与清理 ---
    printf("\n正在关闭端口，清理资源...\n");
    td201_axis_unbind(&axis1);
    td201_axis_unbind(&axis2);
    td201_axis_unbind(&axis3);
    td201_close(controller);
    printf("测试已安全结束。再见！\n");
    return 0;
}