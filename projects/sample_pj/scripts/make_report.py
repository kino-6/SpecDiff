#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MAX_EVIDENCE_CHARS = 700
MAX_DETAIL_CHARS = 5000
TOP_FEATURES = 6


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


def _format_excerpt(text: str, limit: int = MAX_EVIDENCE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n(truncated)"


def _format_full_text(text: str, limit: int = MAX_DETAIL_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n(truncated)"


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


def _select_code_samples(claims: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    python_samples: List[Dict[str, Any]] = []
    c_family_samples: List[Dict[str, Any]] = []
    other_samples: List[Dict[str, Any]] = []

    for claim in claims:
        language = str(claim.get("provenance", {}).get("language", "unknown")).lower()
        if language == "python":
            python_samples.append(claim)
        elif language in {"c", "cpp", "c++", "cxx"}:
            c_family_samples.append(claim)
        else:
            other_samples.append(claim)

    selected = python_samples[:2] + c_family_samples[:2]

    for claim in other_samples:
        if len(selected) >= limit:
            break
        selected.append(claim)

    for claim in claims:
        if len(selected) >= limit:
            break
        if claim not in selected:
            selected.append(claim)

    return selected


def _format_samples(samples: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for claim in samples:
        claim_id = claim.get("claim_id", "(unknown)")
        source_path = claim.get("source", {}).get("path", "(unknown)")
        provenance = claim.get("provenance", {})
        text_raw = claim.get("text_raw", "")
        lines.append(
            "- **claim_id**: {0}\n  - **source.path**: {1}\n  - **provenance**: `{2}`\n  - **excerpt**: {3}".format(
                claim_id,
                source_path,
                _compact_json(provenance),
                _format_excerpt(text_raw, limit=160).replace("\n", " "),
            )
        )
    return "\n".join(lines)


def _format_counter(counter: Counter) -> str:
    if not counter:
        return "- (none)"
    return "\n".join(f"- {key}: {value}" for key, value in counter.most_common())


def _features_from_claim(claim: Dict[str, Any]) -> List[str]:
    facets = claim.get("facets", {}) or {}
    if not isinstance(facets, dict):
        return []
    if "feature" in facets and isinstance(facets.get("feature"), list):
        return [str(item) for item in facets.get("feature") or []]
    for value in facets.values():
        if isinstance(value, dict) and isinstance(value.get("feature"), list):
            return [str(item) for item in value.get("feature") or []]
    return []


def _feature_count(claims: List[Dict[str, Any]], feature: str) -> int:
    feature_lower = feature.lower()
    total = 0
    for claim in claims:
        for item in _features_from_claim(claim):
            if str(item).lower() == feature_lower:
                total += 1
    return total


def _query_count(claims: List[Dict[str, Any]], query: str) -> int:
    query_lower = query.lower()
    return sum(1 for claim in claims if query_lower in str(claim.get("text_raw", "")).lower())


def _trace_matrix(spec_counts: Counter, code_counts: Counter, features: List[str]) -> List[Dict[str, Any]]:
    rows = []
    for feature in features:
        spec_count = spec_counts.get(feature, 0)
        code_count = code_counts.get(feature, 0)
        if spec_count and code_count:
            status = "both"
        elif spec_count:
            status = "spec-only"
        elif code_count:
            status = "code-only"
        else:
            status = "none"
        rows.append(
            {
                "feature": feature,
                "spec_count": spec_count,
                "code_count": code_count,
                "status": status,
                "total": spec_count + code_count,
            }
        )
    order = {"both": 0, "spec-only": 1, "code-only": 2, "none": 3}
    return sorted(rows, key=lambda row: (order[row["status"]], -row["total"], row["feature"]))


def _sanitize_anchor(value: str) -> str:
    slug = []
    last_hyphen = False
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
            last_hyphen = False
        else:
            if not last_hyphen:
                slug.append("-")
                last_hyphen = True
    cleaned = "".join(slug).strip("-")
    return cleaned or "feature"


def _format_backlink(claim: Dict[str, Any]) -> str:
    source = claim.get("source", {}) or {}
    source_type = str(source.get("type", ""))
    path = str(source.get("path", "(unknown)"))
    provenance = claim.get("provenance", {}) or {}
    hints = []
    if source_type == "pdf":
        page = provenance.get("page")
        if page is not None:
            hints.append(f"page {page}")
    elif source_type == "xlsx":
        sheet = provenance.get("sheet")
        row = provenance.get("row")
        if sheet:
            hints.append(f"sheet {sheet}")
        if row is not None:
            hints.append(f"row {row}")
    elif source_type == "pptx":
        slide = provenance.get("slide")
        if slide is not None:
            hints.append(f"slide {slide}")
    elif source_type == "eml":
        subject = provenance.get("subject")
        message_id = provenance.get("message_id")
        if subject:
            hints.append(f"subject {subject}")
        if message_id:
            hints.append(f"message-id {message_id}")
    elif source_type == "code":
        symbol = provenance.get("symbol")
        line_start = provenance.get("line_start")
        line_end = provenance.get("line_end")
        if symbol:
            hints.append(f"symbol {symbol}")
        if line_start is not None and line_end is not None:
            hints.append(f"lines {line_start}-{line_end}")
    if hints:
        return f"{path} ({', '.join(hints)})"
    return path


def _sorted_claims_for_feature(claims: List[Dict[str, Any]], feature: str) -> List[Dict[str, Any]]:
    filtered = [claim for claim in claims if feature in _features_from_claim(claim)]
    return sorted(filtered, key=lambda claim: str(claim.get("claim_id", "")))


def _features_from_claims(claims: List[Dict[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for claim in claims:
        for feature in _features_from_claim(claim):
            counts[feature] += 1
    return counts


def _parse_yaml_value(lines: List[str], key: str) -> Optional[str]:
    key_prefix = f"{key}:"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(key_prefix):
            value = stripped[len(key_prefix):].strip()
            if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
                return value[1:-1]
            return value
    return None


def _resolve_repo_root_from_config(config_path: Path) -> Path:
    lines = config_path.read_text(encoding="utf-8").splitlines()
    repo_root_value = _parse_yaml_value(lines, "repo_root") or "."
    repo_root = Path(repo_root_value).expanduser()
    if repo_root.is_absolute():
        return repo_root.resolve()
    return (config_path.parent / repo_root).resolve()


def _resolve_taxonomy_from_config(config_path: Path) -> Optional[Path]:
    if not config_path.exists():
        return None
    lines = config_path.read_text(encoding="utf-8").splitlines()
    taxonomy_value = _parse_yaml_value(lines, "taxonomy_path")
    if not taxonomy_value:
        return None
    taxonomy_path = Path(taxonomy_value).expanduser()
    if taxonomy_path.is_absolute():
        return taxonomy_path.resolve()
    repo_root = _resolve_repo_root_from_config(config_path)
    return (repo_root / taxonomy_path).resolve()


def _load_taxonomy_features(path: Optional[Path]) -> List[str]:
    if not path or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    features: List[str] = []
    in_feature_block = False
    for line in lines:
        raw = line.rstrip()
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("feature:"):
            in_feature_block = True
            remainder = stripped[len("feature:"):].strip()
            if remainder.startswith("[") and remainder.endswith("]"):
                inner = remainder[1:-1].strip()
                if inner:
                    items = [item.strip().strip("\"'") for item in inner.split(",")]
                    features.extend([item for item in items if item])
                in_feature_block = False
            elif remainder:
                features.append(remainder.strip("\"'"))
                in_feature_block = False
            continue
        if in_feature_block:
            if stripped.startswith("-"):
                value = stripped[1:].strip()
                if value:
                    features.append(value.strip("\"'"))
                continue
            if not raw.startswith(" "):
                in_feature_block = False
    return features


def build_report(
    claims_path: Path,
    code_claims_path: Path,
    output_path: Path,
    details_path: Path,
    taxonomy_path: Optional[Path],
) -> None:
    spec_claims = _read_jsonl(claims_path)
    code_claims = _read_jsonl(code_claims_path)

    source_counts = _count_by(spec_claims, ["source", "type"], "unknown")
    authority_counts = _count_by(spec_claims, ["authority"], "unknown")
    feature_counts = _features_from_claims(spec_claims)
    code_feature_counts = _features_from_claims(code_claims)

    code_language_counts = _count_by(code_claims, ["provenance", "language"], "unknown")

    timestamp = datetime.now(timezone.utc).isoformat()

    spec_samples = _select_spec_samples(spec_claims)
    code_samples = _select_code_samples(code_claims, limit=4)

    golden_queries = [
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --feature brake",
            "count": _feature_count(spec_claims, "brake"),
        },
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --feature can",
            "count": _feature_count(spec_claims, "can"),
        },
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query timing",
            "count": _query_count(spec_claims, "timing"),
        },
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query calibration",
            "count": _query_count(spec_claims, "calibration"),
        },
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query \"retry\"",
            "count": _query_count(spec_claims, "retry"),
        },
        {
            "command": "crossspec search --claims projects/sample_pj/outputs/code_claims.jsonl --query \"init\"",
            "count": _query_count(code_claims, "init"),
        },
    ]

    taxonomy_features = _load_taxonomy_features(taxonomy_path)
    feature_set = set(feature_counts.keys()) | set(code_feature_counts.keys()) | set(taxonomy_features)
    ordered_features = list(taxonomy_features) + sorted(feature_set - set(taxonomy_features))

    matrix_rows = _trace_matrix(feature_counts, code_feature_counts, ordered_features)

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
        "- By facets.feature (multi-label counts):",
        _format_counter(feature_counts),
        "",
        f"- Total code claims: {len(code_claims)}",
        "- By language:",
        _format_counter(code_language_counts),
        "",
        "## Spec vs Code Trace Matrix",
        "",
        "| feature | spec_count | code_count | status |",
        "| --- | --- | --- | --- |",
    ]

    for row in matrix_rows:
        lines.append(f"| {row['feature']} | {row['spec_count']} | {row['code_count']} | {row['status']} |")

    lines.extend([
        "",
        "## Evidence (readable excerpts)",
        "",
    ])

    top_features = [
        row["feature"]
        for row in sorted(matrix_rows, key=lambda row: (-row["total"], row["feature"]))
        if row["total"] > 0
    ][:TOP_FEATURES]

    if not top_features:
        lines.append("No feature evidence available yet.")
    else:
        for feature in top_features:
            anchor = _sanitize_anchor(feature)
            lines.append(f"### Feature: {feature}")
            lines.append(f"See full details: report_details.md#feature-{anchor}")
            lines.append("")
            spec_matches = _sorted_claims_for_feature(spec_claims, feature)
            code_matches = _sorted_claims_for_feature(code_claims, feature)
            lines.append("#### Spec claims")
            if spec_matches:
                for claim in spec_matches[:3]:
                    lines.append(f"- **{claim.get('claim_id')}** — {_format_backlink(claim)}")
                    lines.append("```text")
                    lines.append(_format_excerpt(str(claim.get("text_raw", ""))))
                    lines.append("```")
            else:
                lines.append("- (none)")
            lines.append("")
            lines.append("#### Code claims")
            if code_matches:
                for claim in code_matches[:3]:
                    lines.append(f"- **{claim.get('claim_id')}** — {_format_backlink(claim)}")
                    lines.append("```text")
                    lines.append(_format_excerpt(str(claim.get("text_raw", ""))))
                    lines.append("```")
            else:
                lines.append("- (none)")
            lines.append("")

    spec_only = [row for row in matrix_rows if row["status"] == "spec-only"]
    code_only = [row for row in matrix_rows if row["status"] == "code-only"]

    lines.extend([
        "## Gaps",
        "",
        "### Spec-only features",
    ])
    if spec_only:
        for row in spec_only:
            lines.append(f"- {row['feature']}: {row['spec_count']}")
    else:
        lines.append("- (none)")

    lines.extend([
        "",
        "### Code-only features",
    ])
    if code_only:
        for row in code_only:
            lines.append(f"- {row['feature']}: {row['code_count']}")
    else:
        lines.append("- (none)")

    lines.extend([
        "",
        "## Representative samples",
        "",
        "### Spec claim samples",
    ])

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
        "## Golden Queries (expected to return results)",
        "",
    ])

    for entry in golden_queries:
        status = "OK" if entry["count"] >= 1 else "MISSING"
        lines.append(f"- `{entry['command']}` — {status} ({entry['count']} results)")

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

    _write_details_report(
        details_path=details_path,
        timestamp=timestamp,
        features=ordered_features,
        spec_claims=spec_claims,
        code_claims=code_claims,
    )


def _write_details_report(
    *,
    details_path: Path,
    timestamp: str,
    features: List[str],
    spec_claims: List[Dict[str, Any]],
    code_claims: List[Dict[str, Any]],
) -> None:
    details_lines = [
        "# CrossSpec Sample Project Report Details",
        "",
        f"Generated: {timestamp}",
        "",
    ]

    for feature in features:
        anchor = _sanitize_anchor(feature)
        details_lines.append(f"<a id=\"feature-{anchor}\"></a>")
        details_lines.append(f"## feature: {feature}")
        details_lines.append("")
        spec_matches = _sorted_claims_for_feature(spec_claims, feature)
        code_matches = _sorted_claims_for_feature(code_claims, feature)

        details_lines.append("### Spec claims")
        if spec_matches:
            for claim in spec_matches:
                provenance = claim.get("provenance", {}) or {}
                details_lines.append(f"- **{claim.get('claim_id')}**")
                details_lines.append(f"  - source: {_format_backlink(claim)}")
                details_lines.append(f"  - provenance: `{_compact_json(provenance)}`")
                details_lines.append("  - text_raw:")
                details_lines.append("```text")
                details_lines.append(_format_full_text(str(claim.get("text_raw", ""))))
                details_lines.append("```")
        else:
            details_lines.append("- (none)")

        details_lines.append("")
        details_lines.append("### Code claims")
        if code_matches:
            for claim in code_matches:
                provenance = claim.get("provenance", {}) or {}
                details_lines.append(f"- **{claim.get('claim_id')}**")
                details_lines.append(f"  - source: {_format_backlink(claim)}")
                details_lines.append(f"  - provenance: `{_compact_json(provenance)}`")
                details_lines.append("  - text_raw:")
                details_lines.append("```text")
                details_lines.append(_format_full_text(str(claim.get("text_raw", ""))))
                details_lines.append("```")
        else:
            details_lines.append("- (none)")

        details_lines.append("")
        details_lines.append("---")
        details_lines.append("")

    details_path.parent.mkdir(parents=True, exist_ok=True)
    details_path.write_text("\n".join(details_lines) + "\n", encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = project_root / "outputs"
    config_path = project_root / "crossspec.pj.yml"

    parser = argparse.ArgumentParser(description="Generate a CrossSpec report for sample_pj.")
    parser.add_argument("--claims", type=Path, default=output_dir / "claims.jsonl")
    parser.add_argument("--code-claims", type=Path, default=output_dir / "code_claims.jsonl")
    parser.add_argument("--out", type=Path, default=output_dir / "report.md")
    parser.add_argument("--details", type=Path, default=output_dir / "report_details.md")
    parser.add_argument("--taxonomy", type=Path, default=None)
    args = parser.parse_args()

    taxonomy_path = args.taxonomy
    if taxonomy_path is None:
        taxonomy_path = _resolve_taxonomy_from_config(config_path)

    build_report(args.claims, args.code_claims, args.out, args.details, taxonomy_path)


if __name__ == "__main__":
    main()
