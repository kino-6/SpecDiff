from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(item) for item in items) + "\n", encoding="utf-8")


def test_make_report_generates_summary(tmp_path: Path) -> None:
    claims_path = tmp_path / "claims.jsonl"
    code_claims_path = tmp_path / "code_claims.jsonl"
    report_path = tmp_path / "report.md"

    spec_claims = [
        {
            "claim_id": "CLM-GEN-000001",
            "authority": "normative",
            "text_raw": "The braking system shall respond within 200ms.",
            "source": {"type": "pdf", "path": "docs/specs/reqs.pdf"},
            "provenance": {"page": 1},
            "facets": {"feature": ["brake"]},
        },
        {
            "claim_id": "CLM-GEN-000002",
            "authority": "approved_interpretation",
            "text_raw": "Timing constraints are validated in QA.",
            "source": {"type": "xlsx", "path": "docs/qa/qa.xlsx"},
            "provenance": {"sheet": "Q&A"},
            "facets": {"feature": ["timing"]},
        },
    ]
    code_claims = [
        {
            "claim_id": "CLM-PY-000001",
            "authority": "informative",
            "text_raw": "def init(): pass",
            "source": {"type": "code", "path": "src/py/app.py"},
            "provenance": {"language": "python", "symbol": "init"},
        },
        {
            "claim_id": "CLM-CPP-000001",
            "authority": "informative",
            "text_raw": "void init();",
            "source": {"type": "code", "path": "src/cpp/app.cpp"},
            "provenance": {"language": "cpp", "symbol": "init"},
        },
    ]

    _write_jsonl(claims_path, spec_claims)
    _write_jsonl(code_claims_path, code_claims)

    script_path = Path(__file__).resolve().parents[2] / "projects" / "sample_pj" / "scripts" / "make_report.py"
    subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--claims",
            str(claims_path),
            "--code-claims",
            str(code_claims_path),
            "--out",
            str(report_path),
        ],
        check=True,
    )

    report = report_path.read_text(encoding="utf-8")
    assert "# CrossSpec Sample Project Report" in report
    assert "Total spec claims: 2" in report
    assert "- pdf: 1" in report
    assert "- xlsx: 1" in report
    assert "- normative: 1" in report
    assert "- approved_interpretation: 1" in report
    assert "- brake: 1" in report
    assert "- timing: 1" in report
    assert "Total code claims: 2" in report
    assert "- python: 1" in report
    assert "- cpp: 1" in report
