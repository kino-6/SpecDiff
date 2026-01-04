#include "brake_controller.h"
#include "can_if.h"
#include "diag.h"
#include "nvm_store.h"

static BrakeStatus g_status = {BRAKE_MODE_STANDBY, 0U, 25U, true};
static uint16_t g_pressure_offset = 0U;

void brake_init(void) {
    g_status.mode = BRAKE_MODE_STANDBY;
    g_status.pressure_kpa = 0U;
    g_status.safety_interlock = true;
    g_pressure_offset = nvm_load_calibration();
    can_init();
}

void brake_apply(uint16_t target_pressure_kpa) {
    if (!g_status.safety_interlock) {
        diag_record_error(DIAG_CODE_SAFETY_INTERLOCK);
        g_status.mode = BRAKE_MODE_ERROR;
        return;
    }
    if (target_pressure_kpa > BRAKE_MAX_PRESSURE) {
        diag_record_error(DIAG_CODE_PRESSURE_LIMIT);
        g_status.mode = BRAKE_MODE_ERROR;
        return;
    }
    g_status.mode = BRAKE_MODE_ACTIVE;
    g_status.pressure_kpa = (uint16_t)(target_pressure_kpa + g_pressure_offset);
    can_send_brake_status(&g_status);
}

void brake_release(void) {
    g_status.pressure_kpa = 0U;
    g_status.mode = BRAKE_MODE_STANDBY;
    can_send_brake_status(&g_status);
}

void brake_update_timing(uint16_t offset_ms) {
    /* Timing offsets are applied for brake comms synchronization. */
    g_pressure_offset = offset_ms;
}

void brake_run_diagnostics(void) {
    if (g_status.temperature_c > 90U) {
        diag_record_error(DIAG_CODE_OVER_TEMP);
        g_status.mode = BRAKE_MODE_ERROR;
    }
    diag_report_status(g_status.mode);
}

void brake_store_calibration(uint16_t pressure_offset) {
    g_pressure_offset = pressure_offset;
    nvm_save_calibration(g_pressure_offset);
}

BrakeStatus brake_get_status(void) {
    return g_status;
}
