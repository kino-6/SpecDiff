#ifndef CAN_IF_H
#define CAN_IF_H

#include <stdint.h>
#include <stdbool.h>
#include "brake_controller.h"

/** CAN interface for brake comms and diagnostics frames. */

#define CAN_ID_BRAKE_STATUS 0x120U
#define CAN_ID_DIAG_STATUS  0x121U

typedef enum {
    CAN_OK = 0,
    CAN_ERROR_TIMEOUT = 1,
    CAN_ERROR_BUS = 2,
} CanResult;

void can_init(void);
CanResult can_send_frame(uint32_t can_id, const uint8_t *payload, uint8_t len);
CanResult can_send_brake_status(const BrakeStatus *status);
bool can_poll(uint32_t *can_id, uint8_t *payload, uint8_t *len);

#endif
