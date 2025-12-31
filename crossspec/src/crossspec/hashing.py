"""Hashing utilities."""

import hashlib

from crossspec.normalize import normalize_light


DEFAULT_HASH_ALGO = "sha256"
DEFAULT_HASH_BASIS = "normalize_light"


def hash_text(text: str) -> dict:
    """Compute deterministic hash for text."""
    normalized = normalize_light(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {
        "algo": DEFAULT_HASH_ALGO,
        "basis": DEFAULT_HASH_BASIS,
        "value": digest,
    }
