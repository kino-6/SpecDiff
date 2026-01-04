"""NVM codec utilities for calibration payloads."""
from __future__ import annotations

import struct

NVM_SIGNATURE = 0xCA1BCA1B


def encode_calibration(offset_ms: int) -> bytes:
    """Encode calibration timing data for NVM storage."""
    return struct.pack("<IH", NVM_SIGNATURE, offset_ms)


def decode_calibration(blob: bytes) -> int:
    """Decode calibration timing data from NVM storage."""
    signature, offset = struct.unpack("<IH", blob[:6])
    if signature != NVM_SIGNATURE:
        raise ValueError("nvm signature mismatch")
    return offset


def default_nvm_blob() -> bytes:
    """Return default NVM blob for init sequences."""
    return encode_calibration(0)


def verify_nvm_signature(blob: bytes) -> bool:
    """Check NVM signature for safety diagnostics."""
    try:
        decode_calibration(blob)
    except ValueError:
        return False
    return True
