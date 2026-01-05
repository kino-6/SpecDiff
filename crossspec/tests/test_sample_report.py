from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_make_report_generates_summary(tmp_path: Path) -> None:
    claims_path = tmp_path / "claims.jsonl"
    code_claims_path = tmp_path / "code_claims.jsonl"
    report_path = tmp_path / "report.md"
    details_path = tmp_path / "report_details.md"

    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    claims_path.write_text((fixtures_dir / "sample_pj_claims.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    code_claims_path.write_text((fixtures_dir / "sample_pj_code_claims.jsonl").read_text(encoding="utf-8"), encoding="utf-8")

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
            "--details",
            str(details_path),
        ],
        check=True,
    )

    report = report_path.read_text(encoding="utf-8")
    details = details_path.read_text(encoding="utf-8")
    assert "# CrossSpec Sample Project Report" in report
    assert "Total spec claims: 4" in report
    assert "- pdf: 1" in report
    assert "- xlsx: 1" in report
    assert "- pptx: 1" in report
    assert "- eml: 1" in report
    assert "- normative: 1" in report
    assert "- approved_interpretation: 1" in report
    assert "- informative: 1" in report
    assert "- unverified: 1" in report
    assert "By facets.feature (multi-label counts):" in report
    assert "- brake: 1" in report
    assert "- timing: 1" in report
    assert "- watchdog: 1" in report
    assert "Total code claims: 4" in report
    assert "- python: 2" in report
    assert "- c: 1" in report
    assert "- cpp: 1" in report
    assert "Spec vs Code Trace Matrix" in report
    assert "[timing](report_details.md#feature-timing)" in report
    assert "Evidence (readable excerpts)" in report
    assert "Gaps" in report
    assert "### Spec-only features" in report
    assert "- watchdog: 1" in report
    assert "### Code-only features" in report
    assert "- failsafe_counter: 1" in report
    assert "Golden Queries (expected to return results)" in report
    assert "--query \"retry\"" in report
    assert "--query \"init\"" in report
    assert "report_details.md#feature-timing" in report
    assert "source.path**: src/" in report
    assert "scripts/" not in report
    assert "## feature: timing" in details
    assert "feature-timing" in details
