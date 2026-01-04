#include "diag.h"
#include "can_if.h"

static DiagCode g_last_error = DIAG_CODE_NONE;

void diag_record_error(DiagCode code) {
    g_last_error = code;
}

void diag_clear_error(DiagCode code) {
    if (g_last_error == code) {
        g_last_error = DIAG_CODE_NONE;
    }
}

void diag_report_status(uint16_t brake_mode) {
    uint8_t payload[2] = {0};
    payload[0] = (uint8_t)g_last_error;
    payload[1] = (uint8_t)brake_mode;
    (void)can_send_frame(CAN_ID_DIAG_STATUS, payload, 2U);
}

DiagCode diag_get_last_error(void) {
    return g_last_error;
}

void diag_reset_all(void) {
    g_last_error = DIAG_CODE_NONE;
}
