import json
from pathlib import Path

from crossspec.claims import Authority, Claim, build_claim
from crossspec.cli import _search_claims


def _write_jsonl(path: Path, claims: list[Claim]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for claim in claims:
            handle.write(json.dumps(claim.model_dump(), ensure_ascii=False))
            handle.write("\n")


def test_search_filters_by_type_authority_feature(tmp_path: Path) -> None:
    claims = [
        build_claim(
            claim_id="CLM-GEN-000001",
            authority=Authority.normative,
            text_raw="Brake timing is critical.",
            source_type="pdf",
            source_path="docs/a.pdf",
            provenance={"page": 1},
            facets={"feature": ["brake"]},
        ),
        build_claim(
            claim_id="CLM-GEN-000002",
            authority=Authority.informative,
            text_raw="CAN bus overview.",
            source_type="pptx",
            source_path="slides/a.pptx",
            provenance={"slide": 1},
            facets={"feature": ["comms"]},
        ),
    ]
    jsonl_path = tmp_path / "claims.jsonl"
    _write_jsonl(jsonl_path, claims)

    results = _search_claims(
        input_path=jsonl_path,
        query=None,
        feature="brake",
        authority="normative",
        source_type="pdf",
    )
    assert len(results) == 1
    assert results[0].claim_id == "CLM-GEN-000001"


def test_search_query_ranking(tmp_path: Path) -> None:
    claims = [
        build_claim(
            claim_id="CLM-GEN-000010",
            authority=Authority.informative,
            text_raw="Timing requirements apply.",
            source_type="pdf",
            source_path="docs/a.pdf",
            provenance={"page": 1},
        ),
        build_claim(
            claim_id="CLM-GEN-000009",
            authority=Authority.normative,
            text_raw="Timing.",
            source_type="pdf",
            source_path="docs/b.pdf",
            provenance={"page": 2},
        ),
    ]
    jsonl_path = tmp_path / "claims.jsonl"
    _write_jsonl(jsonl_path, claims)

    results = _search_claims(
        input_path=jsonl_path,
        query="timing",
        feature=None,
        authority=None,
        source_type=None,
    )
    assert results[0].claim_id == "CLM-GEN-000009"
