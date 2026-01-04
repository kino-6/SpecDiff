"""Brake tooling helpers for simulation and calibration checks."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BrakeModel:
    """Simple brake model tracking timing and safety state."""

    pressure_kpa: int = 0
    timing_offset_ms: int = 0
    safety_interlock: bool = True

    def apply(self, target_kpa: int) -> int:
        """Apply brake pressure with safety checks and diagnostics."""
        if not self.safety_interlock:
            raise RuntimeError("safety interlock open")
        self.pressure_kpa = target_kpa + self.timing_offset_ms
        return self.pressure_kpa

    def release(self) -> None:
        """Release brake pressure."""
        self.pressure_kpa = 0


def compute_pressure(command_kpa: int, calibration_offset: int) -> int:
    """Compute calibrated brake pressure for comms frames."""
    return command_kpa + calibration_offset


def compute_deceleration(pressure_kpa: int) -> float:
    """Estimate deceleration for diagnostics and safety review."""
    return max(0.0, pressure_kpa / 100.0)


def update_timing(model: BrakeModel, offset_ms: int) -> None:
    """Update timing offset for brake actuation."""
    model.timing_offset_ms = offset_ms


def check_safety_interlock(model: BrakeModel) -> bool:
    """Return True if safety checks pass."""
    return model.safety_interlock


def validate_pressure_range(pressure_kpa: int) -> bool:
    """Validate brake pressure against calibration limits."""
    return 0 <= pressure_kpa <= 120


def record_calibration(offset_ms: int) -> dict:
    """Build a calibration record for NVM storage."""
    return {"calibration": offset_ms, "nvm": True}


def diagnostics_summary(errors: list[str]) -> str:
    """Summarize diagnostics and error_handling results."""
    if not errors:
        return "diagnostics: OK"
    return "diagnostics: " + ", ".join(errors)
