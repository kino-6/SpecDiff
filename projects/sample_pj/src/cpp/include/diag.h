#ifndef DIAG_H
#define DIAG_H

#include <stdint.h>

/** Diagnostics and error_handling for safety monitoring. */

typedef enum {
    DIAG_CODE_NONE = 0,
    DIAG_CODE_SAFETY_INTERLOCK = 10,
    DIAG_CODE_PRESSURE_LIMIT = 11,
    DIAG_CODE_OVER_TEMP = 12,
    DIAG_CODE_CAN_BUS = 13,
} DiagCode;

void diag_record_error(DiagCode code);
void diag_clear_error(DiagCode code);
void diag_report_status(uint16_t brake_mode);
DiagCode diag_get_last_error(void);
void diag_reset_all(void);

#endif
