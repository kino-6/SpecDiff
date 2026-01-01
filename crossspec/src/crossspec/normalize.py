"""Normalization utilities."""

import re


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_light(text: str) -> str:
    """Collapse whitespace runs and strip leading/trailing whitespace."""
    return _WHITESPACE_RE.sub(" ", text).strip()
