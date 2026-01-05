"""JSONL-backed claim store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from crossspec.claims import Authority, Claim, Status, build_claim
from crossspec.domain.models import Query
from crossspec.domain.ports import ClaimStorePort
from crossspec.infra.scoring import score_claim


@dataclass
class JsonlClaimStore(ClaimStorePort):
    paths: Sequence[Path]

    def __post_init__(self) -> None:
        self._by_id: Dict[str, Claim] = {}
        for path in self.paths:
            self._load_path(Path(path))
        self._sorted_ids = sorted(self._by_id)

    def search(self, query: Query, top_k: int = 20) -> List[Claim]:
        claims = [self._by_id[claim_id] for claim_id in self._sorted_ids]
        filtered = [claim for claim in claims if _matches_type(query, claim)]
        if not query.feature and not query.q:
            return filtered[:top_k]

        scored: List[tuple[int, str, Claim]] = []
        for claim in filtered:
            score, _, _ = score_claim(query, claim)
            scored.append((score, claim.claim_id, claim))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [claim for score, _, claim in scored if score > 0][:top_k]

    def get(self, claim_id: str) -> Optional[Claim]:
        return self._by_id.get(claim_id)

    def iter_all(self, type_filter: Optional[str] = None) -> Iterable[Claim]:
        for claim_id in self._sorted_ids:
            claim = self._by_id[claim_id]
            if type_filter and not _matches_type_value(type_filter, claim):
                continue
            yield claim

    def _load_path(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Claims JSONL not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                payload = line.strip()
                if not payload:
                    continue
                data = json.loads(payload)
                claim = _coerce_claim(data)
                if claim.claim_id in self._by_id:
                    continue
                self._by_id[claim.claim_id] = claim


def _coerce_claim(data: dict) -> Claim:
    if "hash" in data and "created_at" in data:
        return Claim(**data)
    source = data.get("source") or {}
    claim = build_claim(
        claim_id=data["claim_id"],
        authority=Authority(data["authority"]),
        text_raw=data["text_raw"],
        source_type=source.get("type", "spec"),
        source_path=source.get("path", "unknown"),
        provenance=data.get("provenance", {}),
        facets=data.get("facets"),
        status=Status(data.get("status", Status.active)),
        doc_rev=source.get("doc_rev"),
    )
    if data.get("relations"):
        claim.relations = data["relations"]
    return claim


def _matches_type(query: Query, claim: Claim) -> bool:
    if not query.type:
        return True
    return _matches_type_value(query.type, claim)


def _matches_type_value(type_filter: str, claim: Claim) -> bool:
    source_type = getattr(claim.source, "type", None)
    if type_filter == "code":
        return source_type == "code"
    if type_filter == "test":
        return source_type == "test"
    if type_filter == "spec":
        return source_type not in {"code", "test"}
    return source_type == type_filter
