"""Compute coverage use-case."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Optional, Set

from crossspec.claims import Claim
from crossspec.domain.models import CoverageRow, CoverageStatus
from crossspec.domain.ports import ClaimStorePort


def compute_coverage(
    store: ClaimStorePort,
    *,
    features: Optional[List[str]] = None,
) -> List[CoverageRow]:
    claims = list(store.iter_all())
    feature_set: Set[str] = set(features or [])
    if not feature_set:
        feature_set = _collect_features(claims)
    ordered_features = sorted(feature_set)

    counts = {
        feature: {"spec": 0, "impl": 0, "test": 0}
        for feature in ordered_features
    }

    for claim in claims:
        claim_features = _features_for_claim(claim)
        if not claim_features:
            continue
        category = _claim_category(claim)
        for feature in claim_features:
            if feature not in counts:
                continue
            counts[feature][category] += 1

    rows: List[CoverageRow] = []
    for feature in ordered_features:
        spec_count = counts[feature]["spec"]
        impl_count = counts[feature]["impl"]
        test_count = counts[feature]["test"]
        status = _coverage_status(impl_count, test_count)
        rows.append(
            CoverageRow(
                feature=feature,
                spec_count=spec_count,
                impl_count=impl_count,
                test_count=test_count,
                status=status,
            )
        )
    return rows


def _collect_features(claims: Iterable[Claim]) -> Set[str]:
    observed: Set[str] = set()
    for claim in claims:
        observed.update(_features_for_claim(claim))
    return observed


def _features_for_claim(claim: Claim) -> List[str]:
    facets = getattr(claim, "facets", None) or {}
    features = facets.get("feature") or []
    return [str(feature) for feature in features]


def _claim_category(claim: Claim) -> str:
    source_type = getattr(claim.source, "type", None)
    if source_type == "code":
        return "impl"
    if source_type == "test":
        return "test"
    return "spec"


def _coverage_status(impl_count: int, test_count: int) -> CoverageStatus:
    if impl_count > 0 and test_count > 0:
        return CoverageStatus.both
    if impl_count > 0 and test_count == 0:
        return CoverageStatus.impl_only
    if impl_count == 0 and test_count > 0:
        return CoverageStatus.test_only
    return CoverageStatus.none
