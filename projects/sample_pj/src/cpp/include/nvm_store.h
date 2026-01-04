#ifndef NVM_STORE_H
#define NVM_STORE_H

#include <stdint.h>

/** NVM storage for calibration parameters. */

#define NVM_SIGNATURE 0xCA1BCA1BU

typedef struct {
    uint32_t signature;
    uint16_t pressure_offset;
    uint16_t reserved;
} NvmCalibration;

uint16_t nvm_load_calibration(void);
void nvm_save_calibration(uint16_t pressure_offset);
void nvm_commit(void);
uint32_t nvm_get_signature(void);

#endif
