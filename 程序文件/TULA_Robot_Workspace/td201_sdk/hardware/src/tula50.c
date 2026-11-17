#include "tula50.h"
#include <math.h>
#include <stddef.h>

#define TULA50_PULSES_PER_DEGREE  200.0   /* 0.005 deg/pulse → 1/0.005 = 200 pulses/deg */
#define TULA50_MAX_PULSES         2147000000L

td201_err_t tula50_set_angle_wait(td201_axis_t *axis, double target_deg, long timeout_ms)
{
    /* Range guard: avoid overflow when converting double → long */
    double pulses = target_deg * TULA50_PULSES_PER_DEGREE;
    if (pulses > (double)TULA50_MAX_PULSES || pulses < (double)(-TULA50_MAX_PULSES)) {
        return TD201_ERR_RANGE;
    }

    long target_counts = (long)(pulses > 0.0 ? floor(pulses + 0.5) : ceil(pulses - 0.5));
    return td201_move_absolute_wait(axis, target_counts, timeout_ms);
}

td201_err_t tula50_set_angle(td201_axis_t *axis, double target_deg)
{
    /* Range guard: avoid overflow when converting double → long */
    double pulses = target_deg * TULA50_PULSES_PER_DEGREE;
    if (pulses > (double)TULA50_MAX_PULSES || pulses < (double)(-TULA50_MAX_PULSES)) {
        return TD201_ERR_RANGE;
    }

    long target_counts = (long)(pulses > 0.0 ? floor(pulses + 0.5) : ceil(pulses - 0.5));
    return td201_move_absolute(axis, target_counts, NULL);
}

td201_err_t tula50_get_angle(td201_axis_t *axis, double *current_deg)
{
    if (!current_deg) {
        return TD201_ERR_INVALID_ARG;
    }

    long pulses = 0;
    td201_err_t err = td201_get_position(axis, &pulses);
    if (err != TD201_OK) {
        return err;
    }

    *current_deg = (double)pulses / TULA50_PULSES_PER_DEGREE;
    return TD201_OK;
}

td201_err_t tula50_move_physical_wait(td201_axis_t *axis, double target_val,
                                       double pulses_per_unit, long timeout_ms)
{
    if (!axis || pulses_per_unit <= 0.0 || timeout_ms <= 0) {
        return TD201_ERR_INVALID_ARG;
    }

    double pulses = target_val * pulses_per_unit;
    if (pulses > (double)TULA50_MAX_PULSES || pulses < (double)(-TULA50_MAX_PULSES)) {
        return TD201_ERR_RANGE;
    }

    long target_counts = (long)(pulses > 0.0 ? floor(pulses + 0.5) : ceil(pulses - 0.5));
    return td201_move_absolute_wait(axis, target_counts, timeout_ms);
}

td201_err_t tula50_get_physical(td201_axis_t *axis, double pulses_per_unit,
                                 double *current_val)
{
    if (!axis || !current_val || pulses_per_unit <= 0.0) {
        return TD201_ERR_INVALID_ARG;
    }

    long pulses = 0;
    td201_err_t err = td201_get_position(axis, &pulses);
    if (err != TD201_OK) {
        return err;
    }

    *current_val = (double)pulses / pulses_per_unit;
    return TD201_OK;
}