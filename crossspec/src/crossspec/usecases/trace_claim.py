"""Trace claim use-case."""

from __future__ import annotations

from crossspec.domain.models import TraceResult
from crossspec.domain.ports import TraceEnginePort


def trace_claim(
    trace_engine: TraceEnginePort,
    spec_claim_id: str,
    *,
    top_k: int = 10,
) -> TraceResult:
    return trace_engine.trace(spec_claim_id, top_k=top_k)
