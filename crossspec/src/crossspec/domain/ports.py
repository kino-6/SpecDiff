"""Ports (interfaces) for CrossSpec server."""

from __future__ import annotations

from typing import Iterable, Optional, Protocol

from crossspec.claims import Claim
from crossspec.domain.models import ClaimRef, PlanResult, Query, TraceResult


class ClaimStorePort(Protocol):
    def search(self, query: Query, top_k: int = 20) -> list[Claim]:
        ...

    def get(self, claim_id: str) -> Optional[Claim]:
        ...

    def iter_all(self, type_filter: Optional[str] = None) -> Iterable[Claim]:
        ...


class RetrieverPort(Protocol):
    def retrieve(self, query: Query, *, top_k: int) -> list[ClaimRef]:
        ...


class TraceEnginePort(Protocol):
    def trace(self, spec_claim_id: str, *, top_k: int) -> TraceResult:
        ...


class PlannerPort(Protocol):
    def plan(self, requirement_text: str, hints: Optional[dict] = None) -> PlanResult:
        ...
