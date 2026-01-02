"""Claim model and helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from crossspec.pydantic_compat import BaseModel, Field

from crossspec.hashing import hash_text
from crossspec.normalize import normalize_light


class Authority(str, Enum):
    normative = "normative"
    approved_interpretation = "approved_interpretation"
    informative = "informative"
    unverified = "unverified"


class Status(str, Enum):
    active = "active"
    retired = "retired"


class HashInfo(BaseModel):
    algo: str
    basis: str
    value: str


class SourceInfo(BaseModel):
    type: str
    path: str
    doc_rev: Optional[str] = None


class Relations(BaseModel):
    supersedes: Optional[List[str]] = None
    replaced_by: Optional[List[str]] = None
    merged_into: Optional[List[str]] = None
    split_into: Optional[List[str]] = None


class Claim(BaseModel):
    schema_version: int = 1
    claim_id: str
    authority: Authority
    status: Status = Status.active
    text_raw: str
    hash: HashInfo
    source: SourceInfo
    provenance: Dict[str, Any]
    created_at: str
    extracted_by: str = "crossspec-extractor@0.1.0"
    text_norm: Optional[str] = None
    facets: Optional[Dict[str, Any]] = None
    relations: Optional[Relations] = None


class ClaimIdGenerator:
    """Generate sequential claim IDs per category per run."""

    def __init__(self) -> None:
        self._counters = defaultdict(int)

    def next_id(self, category: str) -> str:
        self._counters[category] += 1
        return f"CLM-{category}-{self._counters[category]:06d}"


def category_from_facets(
    facets: Optional[Dict[str, Any]],
    category_hint: Optional[str] = None,
) -> str:
    if category_hint:
        return category_hint
    if facets and facets.get("feature"):
        feature = str(facets["feature"][0])
        sanitized = []
        for char in feature.strip().upper():
            if char.isalnum():
                sanitized.append(char)
            else:
                sanitized.append("_")
        category = "".join(sanitized)
        return category[:6] if category else "GEN"
    return "GEN"


def build_claim(
    *,
    claim_id: str,
    authority: Authority,
    text_raw: str,
    source_type: str,
    source_path: str,
    provenance: Dict[str, Any],
    facets: Optional[Dict[str, Any]] = None,
    status: Status = Status.active,
    doc_rev: Optional[str] = None,
) -> Claim:
    created_at = datetime.now(timezone.utc).isoformat()
    hash_info = hash_text(text_raw)
    text_norm = normalize_light(text_raw)
    return Claim(
        claim_id=claim_id,
        authority=authority,
        status=status,
        text_raw=text_raw,
        hash=HashInfo(**hash_info),
        source=SourceInfo(type=source_type, path=source_path, doc_rev=doc_rev),
        provenance=provenance,
        created_at=created_at,
        text_norm=text_norm,
        facets=facets,
    )
