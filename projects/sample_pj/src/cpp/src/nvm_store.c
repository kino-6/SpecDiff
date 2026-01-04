#include "nvm_store.h"

static NvmCalibration g_shadow = {NVM_SIGNATURE, 0U, 0U};

uint16_t nvm_load_calibration(void) {
    if (g_shadow.signature != NVM_SIGNATURE) {
        g_shadow.signature = NVM_SIGNATURE;
        g_shadow.pressure_offset = 0U;
    }
    return g_shadow.pressure_offset;
}

void nvm_save_calibration(uint16_t pressure_offset) {
    g_shadow.signature = NVM_SIGNATURE;
    g_shadow.pressure_offset = pressure_offset;
    nvm_commit();
}

void nvm_commit(void) {
    /* Persist to non-volatile memory; placeholder for flash write. */
}

uint32_t nvm_get_signature(void) {
    return g_shadow.signature;
}
