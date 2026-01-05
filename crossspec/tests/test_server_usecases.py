from __future__ import annotations

from pathlib import Path

from crossspec.domain.models import Query
from crossspec.infra.fallback_retriever import FallbackRetriever
from crossspec.infra.jsonl_store import JsonlClaimStore
from crossspec.infra.trace_engine import DefaultTraceEngine
from crossspec.usecases.compute_coverage import compute_coverage
from crossspec.usecases.get_claim import get_claim
from crossspec.usecases.search_claims import search_claims
from crossspec.usecases.trace_claim import trace_claim

FIXTURES = Path(__file__).parent / "fixtures"


def _build_store() -> JsonlClaimStore:
    return JsonlClaimStore(
        [
            FIXTURES / "server_spec_claims.jsonl",
            FIXTURES / "server_code_claims.jsonl",
            FIXTURES / "server_test_claims.jsonl",
        ]
    )


def test_get_claim() -> None:
    store = _build_store()
    claim = get_claim(store, "CLM-BRAKE-000001")
    assert claim is not None
    assert claim.claim_id == "CLM-BRAKE-000001"


def test_search_claims_deterministic() -> None:
    store = _build_store()
    query = Query(feature="brake", q="overheat fault")
    results = search_claims(store, query, top_k=3)
    assert [claim.claim_id for claim in results] == [
        "CLM-CODE-000001",
        "CLM-TEST-000001",
        "CLM-BRAKE-000001",
    ]


def test_trace_claim_status() -> None:
    store = _build_store()
    retriever = FallbackRetriever(store)
    trace_engine = DefaultTraceEngine(store=store, retriever=retriever)
    trace = trace_claim(trace_engine, "CLM-BRAKE-000001", top_k=5)
    assert [claim.claim_id for claim in trace.impl] == ["CLM-CODE-000001"]
    assert [claim.claim_id for claim in trace.test] == ["CLM-TEST-000001"]
    assert trace.coverage.status.value == "both"


def test_compute_coverage_rows() -> None:
    store = _build_store()
    rows = compute_coverage(store, features=["brake", "comms"])
    assert [row.feature for row in rows] == ["brake", "comms"]
    assert rows[0].impl_count == 1
    assert rows[0].test_count == 1
    assert rows[0].status.value == "both"
    assert rows[1].impl_count == 0
    assert rows[1].test_count == 0
    assert rows[1].status.value == "none"
