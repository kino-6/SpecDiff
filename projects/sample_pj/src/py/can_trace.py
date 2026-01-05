"""CAN trace helpers for comms diagnostics."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CanFrame:
    can_id: int
    data: bytes


def parse_line(line: str) -> CanFrame:
    """Parse a CAN trace line into a frame."""
    parts = line.strip().split()
    can_id = int(parts[0], 16)
    data = bytes(int(b, 16) for b in parts[1:])
    return CanFrame(can_id=can_id, data=data)


def parse_trace_lines(lines: list[str]) -> list[CanFrame]:
    """Parse multiple trace lines for comms analysis."""
    return [parse_line(line) for line in lines if line.strip()]


def filter_diagnostics(frames: list[CanFrame], diag_id: int) -> list[CanFrame]:
    """Filter diagnostics frames by CAN ID."""
    return [frame for frame in frames if frame.can_id == diag_id]


def summarize_comms(frames: list[CanFrame]) -> dict:
    """Summarize comms activity for timing and error handling."""
    return {
        "count": len(frames),
        "first_id": frames[0].can_id if frames else None,
        "diagnostics": any(frame.can_id == 0x121 for frame in frames),
    }


def build_brake_status_frame(pressure_kpa: int, safety: bool) -> CanFrame:
    """Create a brake status frame payload."""
    payload = bytes([pressure_kpa & 0xFF, (pressure_kpa >> 8) & 0xFF, int(safety)])
    return CanFrame(can_id=0x120, data=payload)


def increment_failsafe_counter(failsafe_counter: int) -> int:
    """Increment the failsafe_counter used by comms fallback logic."""
    return failsafe_counter + 1
