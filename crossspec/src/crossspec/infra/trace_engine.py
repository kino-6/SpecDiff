"""Default trace engine implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from crossspec.claims import Claim
from crossspec.domain.models import CoverageStatus, CoverageSummary, Query, TraceResult
from crossspec.domain.ports import ClaimStorePort, RetrieverPort, TraceEnginePort


@dataclass
class DefaultTraceEngine(TraceEnginePort):
    store: ClaimStorePort
    retriever: RetrieverPort

    def trace(self, spec_claim_id: str, *, top_k: int) -> TraceResult:
        spec = self.store.get(spec_claim_id)
        if not spec:
            raise KeyError(f"Spec claim not found: {spec_claim_id}")

        query = _query_from_spec(spec)
        impl_claims = _resolve_claims(self.store, self.retriever, query, "code", top_k)
        test_claims = _resolve_claims(self.store, self.retriever, query, "test", top_k)
        coverage = _coverage_summary(len(impl_claims), len(test_claims))
        return TraceResult(spec=spec, impl=impl_claims, test=test_claims, coverage=coverage)


def _query_from_spec(spec: Claim) -> Query:
    facets = getattr(spec, "facets", None) or {}
    feature = None
    features = facets.get("feature") or []
    if features:
        feature = str(features[0])
    text = spec.text_norm or spec.text_raw
    return Query(feature=feature, q=text)


def _resolve_claims(
    store: ClaimStorePort,
    retriever: RetrieverPort,
    base_query: Query,
    type_value: str,
    top_k: int,
) -> List[Claim]:
    query = Query(type=type_value, feature=base_query.feature, q=base_query.q)
    refs = retriever.retrieve(query, top_k=top_k)
    claims: List[Claim] = []
    seen = set()
    for ref in refs:
        if ref.claim_id in seen:
            continue
        seen.add(ref.claim_id)
        claim = store.get(ref.claim_id)
        if claim:
            claims.append(claim)
    return claims


def _coverage_summary(impl_count: int, test_count: int) -> CoverageSummary:
    if impl_count > 0 and test_count > 0:
        status = CoverageStatus.both
    elif impl_count > 0 and test_count == 0:
        status = CoverageStatus.impl_only
    elif impl_count == 0 and test_count > 0:
        status = CoverageStatus.test_only
    else:
        status = CoverageStatus.none
    return CoverageSummary(impl_count=impl_count, test_count=test_count, status=status)
