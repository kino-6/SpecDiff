#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        items.append(json.loads(stripped))
    return items


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _compact_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _excerpt(text: str, limit: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def _count_by(items: Iterable[Dict[str, Any]], key_path: List[str], default: str) -> Counter:
    counts: Counter = Counter()
    for item in items:
        current: Any = item
        for key in key_path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = default
                break
        if current is None:
            current = default
        counts[str(current)] += 1
    return counts


def _select_spec_samples(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: Dict[str, Dict[str, Any]] = {}
    for claim in claims:
        source_type = str(claim.get("source", {}).get("type", "unknown"))
        if source_type not in selected:
            selected[source_type] = claim
    return list(selected.values())


def _select_code_samples(claims: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    seen_languages = set()
    seen_symbols = set()
    for claim in claims:
        provenance = claim.get("provenance", {})
        language = str(provenance.get("language", "unknown"))
        symbol = str(provenance.get("symbol", ""))
        if language not in seen_languages or (symbol and symbol not in seen_symbols):
            selected.append(claim)
            seen_languages.add(language)
            if symbol:
                seen_symbols.add(symbol)
        if len(selected) >= limit:
            return selected
    for claim in claims:
        if claim in selected:
            continue
        selected.append(claim)
        if len(selected) >= limit:
            break
    return selected


def _format_samples(samples: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for claim in samples:
        claim_id = claim.get("claim_id", "(unknown)")
        source_path = claim.get("source", {}).get("path", "(unknown)")
        provenance = claim.get("provenance", {})
        text_raw = claim.get("text_raw", "")
        lines.append("- **claim_id**: {0}\n  - **source.path**: {1}\n  - **provenance**: `{2}`\n  - **excerpt**: {3}".format(
            claim_id,
            source_path,
            _compact_json(provenance),
            _excerpt(text_raw),
        ))
    return "\n".join(lines)


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "- (none)"
    return "\n".join(f"- {key}: {value}" for key, value in counter.most_common())


def build_report(claims_path: Path, code_claims_path: Path, output_path: Path) -> None:
    spec_claims = _read_jsonl(claims_path)
    code_claims = _read_jsonl(code_claims_path)

    source_counts = _count_by(spec_claims, ["source", "type"], "unknown")
    authority_counts = _count_by(spec_claims, ["authority"], "unknown")

    feature_counts: Counter = Counter()
    for claim in spec_claims:
        facets = claim.get("facets", {}) or {}
        features = _as_list(facets.get("feature"))
        for feature in features:
            feature_counts[feature] += 1

    code_language_counts = _count_by(code_claims, ["provenance", "language"], "unknown")

    timestamp = datetime.now(timezone.utc).isoformat()

    spec_samples = _select_spec_samples(spec_claims)
    code_samples = _select_code_samples(code_claims, limit=3)

    lines = [
        "# CrossSpec Sample Project Report",
        "",
        f"Generated: {timestamp}",
        "",
        "## Summary counts",
        "",
        f"- Total spec claims: {len(spec_claims)}",
        "- By source.type:",
        _format_counter(source_counts),
        "- By authority:",
        _format_counter(authority_counts),
        "- By facets.feature:",
        _format_counter(feature_counts),
        "",
        f"- Total code claims: {len(code_claims)}",
        "- By language:",
        _format_counter(code_language_counts),
        "",
        "## Representative samples",
        "",
        "### Spec claim samples",
    ]

    if spec_samples:
        lines.append(_format_samples(spec_samples))
    else:
        lines.append("No spec claims yet.")

    lines.extend([
        "",
        "### Code claim samples",
    ])

    if code_samples:
        lines.append(_format_samples(code_samples))
    else:
        lines.append("No code claims yet.")

    lines.extend([
        "",
        "## Example searches",
        "",
        "```bash",
        "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --feature brake",
        "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query timing",
        "crossspec search --claims projects/sample_pj/outputs/code_claims.jsonl --query init",
        "```",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "outputs"

    parser = argparse.ArgumentParser(description="Generate a CrossSpec report for sample_pj.")
    parser.add_argument("--claims", type=Path, default=output_dir / "claims.jsonl")
    parser.add_argument("--code-claims", type=Path, default=output_dir / "code_claims.jsonl")
    parser.add_argument("--out", type=Path, default=output_dir / "report.md")
    args = parser.parse_args()

    build_report(args.claims, args.code_claims, args.out)


if __name__ == "__main__":
    main()
