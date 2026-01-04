#ifndef BRAKE_CONTROLLER_H
#define BRAKE_CONTROLLER_H

#include <stdint.h>
#include <stdbool.h>

/**
 * Brake controller interface.
 * Handles brake timing, safety interlocks, and calibration.
 */

#define BRAKE_MAX_PRESSURE 120U
#define BRAKE_DIAG_INTERVAL_MS 50U

typedef enum {
    BRAKE_MODE_STANDBY = 0,
    BRAKE_MODE_ACTIVE = 1,
    BRAKE_MODE_ERROR = 2,
} BrakeMode;

typedef struct {
    BrakeMode mode;
    uint16_t pressure_kpa;
    uint16_t temperature_c;
    bool safety_interlock;
} BrakeStatus;

/** Initialize brake subsystem and load NVM calibration. */
void brake_init(void);

/** Apply brake pressure with timing protection and safety checks. */
void brake_apply(uint16_t target_pressure_kpa);

/** Release brake pressure safely. */
void brake_release(void);

/** Update brake timing offsets based on calibration. */
void brake_update_timing(uint16_t offset_ms);

/** Run brake diagnostics and error handling. */
void brake_run_diagnostics(void);

/** Persist calibration values to NVM storage. */
void brake_store_calibration(uint16_t pressure_offset);

/** Get current brake status. */
BrakeStatus brake_get_status(void);

#endif
