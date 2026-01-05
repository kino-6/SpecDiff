"""REST API adapter."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Query as FastQuery

from crossspec.claims import Claim
from crossspec.domain.models import Query
from crossspec.server.wire import ServiceBundle


def create_app(services: ServiceBundle) -> FastAPI:
    app = FastAPI(title="CrossSpec Server (REST)")

    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/claims")
    def list_claims(
        type: Optional[str] = None,
        feature: Optional[str] = None,
        q: Optional[str] = None,
        top: int = FastQuery(20, ge=1, le=100),
    ) -> Dict[str, Any]:
        query = Query(type=type, feature=feature, q=q)
        claims = services.search_claims(query, top_k=top)
        return {
            "claims": [_claim_summary(claim) for claim in claims],
        }

    @app.get("/claims/{claim_id}")
    def get_claim(claim_id: str) -> Dict[str, Any]:
        claim = services.get_claim(claim_id)
        if not claim:
            return {"error": "not_found"}
        return claim.model_dump()

    @app.get("/trace/{spec_claim_id}")
    def trace_claim(spec_claim_id: str, top: int = FastQuery(10, ge=1, le=50)) -> Dict[str, Any]:
        trace = services.trace_claim(spec_claim_id, top_k=top)
        return {
            "spec": _dump_claim(trace.spec),
            "impl": [_dump_claim(item) for item in trace.impl],
            "test": [_dump_claim(item) for item in trace.test],
            "coverage": trace.coverage.model_dump(),
        }

    @app.get("/coverage")
    def coverage(feature: Optional[str] = None) -> Dict[str, Any]:
        rows = services.compute_coverage(feature=feature)
        return {"coverage": [row.model_dump() for row in rows]}

    return app


def _claim_summary(claim: Claim) -> Dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "authority": getattr(claim.authority, "value", claim.authority),
        "source": _source_payload(claim),
        "excerpt": _excerpt(claim.text_raw),
        "facets": claim.facets,
    }


def _source_payload(claim: Claim) -> Dict[str, Any]:
    source = claim.source
    return {
        "type": source.type,
        "path": source.path,
        "doc_rev": source.doc_rev,
    }


def _dump_claim(claim: Claim) -> Dict[str, Any]:
    return claim.model_dump()


def _excerpt(text: str, limit: int = 160) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1] + "…"
