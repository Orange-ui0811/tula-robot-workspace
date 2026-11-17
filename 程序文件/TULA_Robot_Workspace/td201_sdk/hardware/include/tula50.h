#ifndef TULA50_H
#define TULA50_H

#include "td201.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief 设置电机绝对角度并等待运动完成
 * @param axis        轴句柄指针
 * @param target_deg  目标角度（单位：度）
 * @param timeout_ms  最大等待时间（单位：毫秒）
 * @return 成功返回 TD201_OK，否则返回错误码
 */
td201_err_t tula50_set_angle_wait(td201_axis_t *axis, double target_deg, long timeout_ms);

/**
 * @brief 非阻塞设置电机绝对角度（Fire-and-Forget）
 *
 * 直接下发底层绝对运动指令后立即返回，不进行任何轮询等待。
 * 调用者需自行管理运动状态与完成检测。适用于 50Hz 高频控制场景。
 *
 * @param axis        轴句柄指针
 * @param target_deg  目标角度（单位：度）
 * @return 成功返回 TD201_OK，否则返回错误码
 */
td201_err_t tula50_set_angle(td201_axis_t *axis, double target_deg);

/**
 * @brief 获取电机当前角度
 * @param axis         轴句柄指针
 * @param current_deg  输出参数：当前角度（单位：度）
 * @return 成功返回 TD201_OK，否则返回错误码
 */
td201_err_t tula50_get_angle(td201_axis_t *axis, double *current_deg);

/**
 * @brief 通用物理单位绝对运动（阻塞等待完成）
 *
 * 将目标物理值乘以 pulses_per_unit 换算为目标脉冲数后，
 * 调用底层 td201_move_absolute_wait 执行运动并等待完成。
 * 适用于毫米、角度等任意物理单位的闭环控制。
 *
 * @param axis            轴句柄指针
 * @param target_val      目标物理值（如 mm 或 deg）
 * @param pulses_per_unit 每物理单位对应的编码器脉冲数
 * @param timeout_ms      最大等待时间（单位：毫秒）
 * @return 成功返回 TD201_OK，否则返回错误码
 */
td201_err_t tula50_move_physical_wait(td201_axis_t *axis, double target_val,
                                       double pulses_per_unit, long timeout_ms);

/**
 * @brief 通用物理单位位置读取
 *
 * 读取当前编码器脉冲数，除以 pulses_per_unit 得到物理双精度浮点值。
 * 适用于毫米、角度等任意物理单位的位置查询。
 *
 * @param axis            轴句柄指针
 * @param pulses_per_unit 每物理单位对应的编码器脉冲数
 * @param current_val     输出参数：当前物理值（如 mm 或 deg）
 * @return 成功返回 TD201_OK，否则返回错误码
 */
td201_err_t tula50_get_physical(td201_axis_t *axis, double pulses_per_unit,
                                 double *current_val);

#ifdef __cplusplus
}
#endif

#endif /* TULA50_H */