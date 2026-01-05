"""Deterministic scoring helpers."""

from __future__ import annotations

import re
from typing import Set, Tuple

from crossspec.claims import Claim
from crossspec.domain.models import Query

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_text(text: str) -> str:
    return text.lower()


def tokenize(text: str) -> Set[str]:
    return set(_TOKEN_RE.findall(normalize_text(text)))


def feature_overlap_score(query: Query, claim: Claim) -> int:
    if not query.feature:
        return 0
    facets = getattr(claim, "facets", None) or {}
    claim_features = {str(feature).lower() for feature in facets.get("feature", [])}
    return int(query.feature.lower() in claim_features)


def keyword_overlap_score(query: Query, claim: Claim) -> int:
    if not query.q:
        return 0
    claim_text = claim.text_norm or claim.text_raw
    query_tokens = tokenize(query.q)
    claim_tokens = tokenize(claim_text)
    return len(query_tokens & claim_tokens)


def score_claim(query: Query, claim: Claim) -> Tuple[int, int, int]:
    feature_score = feature_overlap_score(query, claim)
    keyword_score = keyword_overlap_score(query, claim)
    total = feature_score + keyword_score
    return total, feature_score, keyword_score
