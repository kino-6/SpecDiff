"""Fallback retriever with deterministic scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from crossspec.domain.models import ClaimRef, Query
from crossspec.domain.ports import ClaimStorePort, RetrieverPort
from crossspec.infra.scoring import score_claim


@dataclass
class FallbackRetriever(RetrieverPort):
    store: ClaimStorePort

    def retrieve(self, query: Query, *, top_k: int) -> List[ClaimRef]:
        refs: List[ClaimRef] = []
        for claim in self.store.iter_all(type_filter=query.type):
            score, feature_score, keyword_score = score_claim(query, claim)
            if not query.feature and not query.q:
                score = 0
            refs.append(
                ClaimRef(
                    claim_id=claim.claim_id,
                    score=float(score),
                    reason=(
                        f"feature_overlap={feature_score}; "
                        f"keyword_overlap={keyword_score}"
                    ),
                )
            )
        refs.sort(key=lambda ref: (-ref.score, ref.claim_id))
        if not query.feature and not query.q:
            return refs[:top_k]
        return [ref for ref in refs if ref.score > 0][:top_k]
