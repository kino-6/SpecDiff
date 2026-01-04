#include "can_if.h"
#include "diag.h"

void can_init(void) {
    /* Initialize CAN controller, timing, and comms buffers. */
}

CanResult can_send_frame(uint32_t can_id, const uint8_t *payload, uint8_t len) {
    (void)payload;
    (void)len;
    if (can_id == 0U) {
        diag_record_error(DIAG_CODE_CAN_BUS);
        return CAN_ERROR_BUS;
    }
    return CAN_OK;
}

CanResult can_send_brake_status(const BrakeStatus *status) {
    uint8_t payload[4] = {0};
    payload[0] = (uint8_t)status->mode;
    payload[1] = (uint8_t)(status->pressure_kpa & 0xFFU);
    payload[2] = (uint8_t)(status->pressure_kpa >> 8);
    payload[3] = status->safety_interlock ? 1U : 0U;
    return can_send_frame(CAN_ID_BRAKE_STATUS, payload, 4U);
}

bool can_poll(uint32_t *can_id, uint8_t *payload, uint8_t *len) {
    (void)payload;
    (void)len;
    *can_id = 0U;
    return false;
}
