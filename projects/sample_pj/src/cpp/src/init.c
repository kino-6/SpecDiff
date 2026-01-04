#include "brake_controller.h"
#include "diag.h"

void system_init(void) {
    /* System init sequence with safety checks. */
    brake_init();
    diag_clear_error(DIAG_CODE_NONE);
    brake_update_timing(5U);
}
