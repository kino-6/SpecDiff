"""Get claim use-case."""

from __future__ import annotations

from typing import Optional

from crossspec.claims import Claim
from crossspec.domain.ports import ClaimStorePort


def get_claim(store: ClaimStorePort, claim_id: str) -> Optional[Claim]:
    return store.get(claim_id)
