"""Search claims use-case."""

from __future__ import annotations

from typing import List, Optional

from crossspec.claims import Claim
from crossspec.domain.models import Query
from crossspec.domain.ports import ClaimStorePort, RetrieverPort


def search_claims(
    store: ClaimStorePort,
    query: Query,
    *,
    top_k: int = 20,
    retriever: Optional[RetrieverPort] = None,
) -> List[Claim]:
    if retriever:
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
    return list(store.search(query, top_k=top_k))
