"""Domain models for CrossSpec server."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from crossspec.claims import Claim
from crossspec.pydantic_compat import BaseModel


class Query(BaseModel):
    type: Optional[str] = None
    feature: Optional[str] = None
    q: Optional[str] = None


class ClaimRef(BaseModel):
    claim_id: str
    score: float
    reason: Optional[str] = None


class CoverageStatus(str, Enum):
    both = "both"
    impl_only = "impl_only"
    test_only = "test_only"
    none = "none"


class CoverageSummary(BaseModel):
    impl_count: int
    test_count: int
    status: CoverageStatus


class TraceResult(BaseModel):
    spec: Claim
    impl: List[Claim]
    test: List[Claim]
    coverage: CoverageSummary


class PlanResult(BaseModel):
    markdown: str
    req_breakdown: List[str]
    impl_plan: List[str]
    test_plan: List[str]
    assumptions: List[str]


class CoverageRow(BaseModel):
    feature: str
    spec_count: int
    impl_count: int
    test_count: int
    status: CoverageStatus
