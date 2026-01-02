"""CLI for CrossSpec."""

from __future__ import annotations

import glob
from pathlib import Path
import sys
from typing import Iterable, List, Optional

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    typer = None

from crossspec.claims import Authority, Claim, ClaimIdGenerator, SourceInfo, category_from_facets, build_claim
from crossspec.config import CrossspecConfig, KnowledgeSource, MailConfig, PptxConfig, load_config
from crossspec.io.jsonl import write_jsonl
from crossspec.tagging import load_taxonomy

if typer:
    app = typer.Typer(help="CrossSpec CLI")
else:
    app = None


def extract_command(config: str) -> None:
    """Extract claims from configured knowledge sources."""
    cfg = load_config(config)
    claims = list(_extract_claims(cfg))
    output_path = Path(cfg.outputs.claims_dir) / cfg.outputs.jsonl_filename
    write_jsonl(output_path, claims)
    message = f"Wrote {len(claims)} claims to {output_path}"
    if typer:
        typer.echo(message)
    else:
        print(message)


if typer:

    @app.command()
    def extract(config: str = typer.Option(..., "--config", help="Path to config YAML")) -> None:
        extract_command(config)

    @app.command()
    def demo(config: str = typer.Option(..., "--config", help="Path to config YAML")) -> None:
        demo_command(config)

    @app.command()
    def search(
        config: str = typer.Option(..., "--config", help="Path to config YAML"),
        query: Optional[str] = typer.Option(None, "--query", help="Search query"),
        feature: Optional[str] = typer.Option(None, "--feature", help="Facet feature filter"),
        authority: Optional[str] = typer.Option(None, "--authority", help="Authority filter"),
        type: Optional[str] = typer.Option(None, "--type", help="Source type filter"),
        top: int = typer.Option(10, "--top", help="Max results"),
        claims: Optional[str] = typer.Option(None, "--claims", help="Claims JSONL path"),
        show_provenance: bool = typer.Option(False, "--show-provenance", help="Show provenance"),
        show_source: bool = typer.Option(False, "--show-source", help="Show source details"),
    ) -> None:
        search_command(
            config=config,
            query=query,
            feature=feature,
            authority=authority,
            source_type=type,
            top=top,
            claims_path=claims,
            show_provenance=show_provenance,
            show_source=show_source,
        )

    @app.command()
    def index() -> None:
        """Placeholder for future indexing."""
        typer.echo("Indexing is not implemented yet.")


    @app.command()
    def analyze() -> None:
        """Placeholder for future analysis."""
        typer.echo("Analysis is not implemented yet.")


def _extract_claims(cfg: CrossspecConfig) -> Iterable[Claim]:
    repo_root = Path(cfg.project.repo_root)
    tagger: Optional[object] = None
    facets_key = "facets"
    if cfg.tagging and cfg.tagging.enabled:
        taxonomy = load_taxonomy(cfg.tagging.taxonomy_path)
        from crossspec.tagging.llm_tagger import LlmTagger

        tagger = LlmTagger(taxonomy=taxonomy, llm=cfg.tagging.llm)
        facets_key = cfg.tagging.output.facets_key

    id_generator = ClaimIdGenerator()

    for source in cfg.knowledge_sources:
        for path in _expand_paths(repo_root, source.paths):
            extractor = _build_extractor(source, path)
            for extracted in extractor.extract():
                facets = None
                if tagger:
                    facets = tagger.tag(extracted.text_raw)
                category = category_from_facets(facets)
                claim_id = id_generator.next_id(category)
                facets_payload = None
                if facets is not None:
                    facets_payload = facets if facets_key == "facets" else {facets_key: facets}
                claim = build_claim(
                    claim_id=claim_id,
                    authority=extracted.authority,
                    text_raw=extracted.text_raw,
                    source_type=extracted.source_type,
                    source_path=extracted.source_path,
                    provenance=extracted.provenance,
                    facets=facets_payload,
                )
                yield claim


def _expand_paths(repo_root: Path, patterns: List[str]) -> List[Path]:
    paths: List[Path] = []
    for pattern in patterns:
        if Path(pattern).is_absolute():
            matches = glob.glob(pattern, recursive=True)
        else:
            matches = glob.glob(str(repo_root / pattern), recursive=True)
        for match in matches:
            paths.append(Path(match))
    return sorted(set(paths))


def _build_extractor(source: KnowledgeSource, path: Path):
    authority = Authority(source.authority)
    if source.type == "pdf":
        from crossspec.extract.pdf_extractor import PdfExtractor

        return PdfExtractor(path=path, authority=authority)
    if source.type == "xlsx":
        if not source.xlsx:
            raise ValueError(f"Missing xlsx config for source {source.name}")
        from crossspec.extract.xlsx_extractor import XlsxExtractor

        return XlsxExtractor(path=path, authority=authority, config=source.xlsx)
    if source.type == "pptx":
        config = source.pptx or PptxConfig()
        from crossspec.extract.pptx_extractor import PptxExtractor

        return PptxExtractor(path=path, authority=authority, config=config)
    if source.type == "eml":
        config = source.mail or MailConfig()
        from crossspec.extract.eml_extractor import EmlExtractor

        return EmlExtractor(path=path, authority=authority, config=config)
    raise ValueError(f"Unsupported source type: {source.type}")


def demo_command(config: str) -> None:
    cfg = load_config(config)
    _run_demo(cfg)


def _run_demo(cfg: CrossspecConfig) -> None:
    from collections import Counter
    import subprocess

    samples_script = Path("samples/generate_samples.py")
    if samples_script.exists():
        subprocess.run([sys.executable, str(samples_script)], check=True)
    else:
        print("samples/generate_samples.py not found; skipping sample generation.")

    output_path = Path(cfg.outputs.claims_dir) / cfg.outputs.jsonl_filename
    pdf_expected = Path("samples/input/sample.pdf")
    if not pdf_expected.exists():
        raise RuntimeError(
            "Demo requires PDF sample generation. Install extras with "
            "`pip install -e \"./crossspec[demo]\"` (or `uv pip install -e ./crossspec[demo]`)."
        )
    claims = list(_extract_claims(cfg))
    write_jsonl(output_path, claims)
    print(f"Wrote {len(claims)} claims to {output_path}")

    by_source = Counter(claim.source.type for claim in claims)
    by_authority = Counter(getattr(claim.authority, "value", str(claim.authority)) for claim in claims)
    feature_counts = Counter()
    has_facets = False
    for claim in claims:
        if claim.facets and isinstance(claim.facets, dict):
            features = []
            if "feature" in claim.facets:
                features = claim.facets.get("feature") or []
            else:
                for value in claim.facets.values():
                    if isinstance(value, dict) and "feature" in value:
                        features = value.get("feature") or []
                        break
            if features:
                has_facets = True
                feature_counts.update(features)

    print("Counts by source.type:")
    for key, value in by_source.items():
        print(f"  {key}: {value}")
    print("Counts by authority:")
    for key, value in by_authority.items():
        print(f"  {key}: {value}")
    if has_facets:
        print("Counts by facets.feature:")
        for key, value in feature_counts.items():
            print(f"  {key}: {value}")
    else:
        print("Counts by facets.feature: no facets")
    print("Note: Counts by facets.feature is multi-label; totals can exceed total claims.")

    print("Sample claims:")
    if not claims:
        print("  (no claims found)")
        return
    samples_by_type = _select_representative_samples(claims)
    for source_type in sorted(samples_by_type):
        claim = samples_by_type[source_type]
        text_preview = claim.text_raw.replace("\n", " ")[:160]
        print(f"TYPE: {source_type} | {claim.claim_id} | {claim.source.path} | {claim.provenance}")
        print(f"  {text_preview}")


def _authority_rank(value: str) -> int:
    order = {
        "normative": 4,
        "approved_interpretation": 3,
        "informative": 2,
        "unverified": 1,
    }
    return order.get(value, 0)


def _features_from_facets(facets: Optional[dict]) -> List[str]:
    if not facets or not isinstance(facets, dict):
        return []
    if "feature" in facets and isinstance(facets.get("feature"), list):
        return facets.get("feature") or []
    for value in facets.values():
        if isinstance(value, dict) and isinstance(value.get("feature"), list):
            return value.get("feature") or []
    return []


def _select_representative_samples(claims: List[Claim]) -> dict:
    grouped = {}
    for claim in claims:
        source_type = claim.source.type
        grouped.setdefault(source_type, []).append(claim)
    samples = {}
    for source_type, items in grouped.items():
        def sort_key(item: Claim) -> tuple:
            authority_value = getattr(item.authority, "value", str(item.authority))
            rank = _authority_rank(authority_value)
            has_feature = bool(_features_from_facets(item.facets))
            return (-rank, -int(has_feature), item.claim_id)

        samples[source_type] = sorted(items, key=sort_key)[0]
    return samples


def search_command(
    *,
    config: str,
    query: Optional[str],
    feature: Optional[str],
    authority: Optional[str],
    source_type: Optional[str],
    top: int,
    claims_path: Optional[str],
    show_provenance: bool,
    show_source: bool,
) -> None:
    cfg = load_config(config)
    if claims_path:
        input_path = Path(claims_path)
    else:
        input_path = Path(cfg.outputs.claims_dir) / cfg.outputs.jsonl_filename
    results = _search_claims(
        input_path=input_path,
        query=query,
        feature=feature,
        authority=authority,
        source_type=source_type,
    )
    if not results:
        print("No results.")
        return
    for claim in results[:top]:
        authority_value = getattr(claim.authority, "value", str(claim.authority))
        print(f"{claim.claim_id} | {authority_value} | {claim.source.type} | {claim.source.path}")
        if show_source:
            print(f"  source: {claim.source.model_dump()}")
        if show_provenance:
            print(f"  provenance: {claim.provenance}")
        excerpt = " ".join(claim.text_raw.split())[:200]
        print(f"  {excerpt}")


def _search_claims(
    *,
    input_path: Path,
    query: Optional[str],
    feature: Optional[str],
    authority: Optional[str],
    source_type: Optional[str],
) -> List[Claim]:
    import json

    claims: List[Claim] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload.get("source"), dict):
                payload["source"] = SourceInfo(**payload["source"])
            claims.append(Claim(**payload))
    filtered = []
    for claim in claims:
        if source_type and claim.source.type != source_type:
            continue
        if authority:
            authority_value = getattr(claim.authority, "value", str(claim.authority))
            if authority_value != authority:
                continue
        if feature:
            features = _features_from_facets(claim.facets)
            if feature not in features:
                continue
        if query:
            haystack = claim.text_raw
            if claim.text_norm:
                haystack = f"{haystack}\n{claim.text_norm}"
            if query.lower() not in haystack.lower():
                continue
        filtered.append(claim)
    return _rank_claims(filtered, query)


def _rank_claims(claims: List[Claim], query: Optional[str]) -> List[Claim]:
    query_lower = query.lower() if query else None

    def match_key(claim: Claim) -> tuple:
        authority_value = getattr(claim.authority, "value", str(claim.authority))
        rank = _authority_rank(authority_value)
        if query_lower:
            raw_lower = claim.text_raw.lower()
            exact = query_lower in raw_lower
            distance = max(len(claim.text_raw) - len(query_lower), 0)
            return (
                -int(exact),
                distance,
                -rank,
                claim.claim_id,
            )
        return (-rank, claim.claim_id)

    return sorted(claims, key=match_key)


def main() -> None:
    if typer and app:
        app()
        return
    import argparse

    parser = argparse.ArgumentParser(description="CrossSpec CLI (minimal)")
    subparsers = parser.add_subparsers(dest="command")
    extract_parser = subparsers.add_parser("extract", help="Extract claims")
    extract_parser.add_argument("--config", required=True, help="Path to config YAML")
    demo_parser = subparsers.add_parser("demo", help="Run demo generation and summary")
    demo_parser.add_argument("--config", required=True, help="Path to config YAML")
    search_parser = subparsers.add_parser("search", help="Search claims")
    search_parser.add_argument("--config", required=True, help="Path to config YAML")
    search_parser.add_argument("--query", required=False, help="Search query")
    search_parser.add_argument("--feature", required=False, help="Facet feature filter")
    search_parser.add_argument("--authority", required=False, help="Authority filter")
    search_parser.add_argument("--type", required=False, help="Source type filter")
    search_parser.add_argument("--top", type=int, default=10, help="Max results")
    search_parser.add_argument("--claims", required=False, help="Claims JSONL path")
    search_parser.add_argument("--show-provenance", action="store_true", help="Show provenance")
    search_parser.add_argument("--show-source", action="store_true", help="Show source details")
    subparsers.add_parser("index", help="Indexing (not implemented)")
    subparsers.add_parser("analyze", help="Analysis (not implemented)")
    args = parser.parse_args()
    if args.command == "extract":
        extract_command(args.config)
    elif args.command == "demo":
        demo_command(args.config)
    elif args.command == "search":
        search_command(
            config=args.config,
            query=args.query,
            feature=args.feature,
            authority=args.authority,
            source_type=args.type,
            top=args.top,
            claims_path=args.claims,
            show_provenance=args.show_provenance,
            show_source=args.show_source,
        )
    elif args.command == "index":
        print("Indexing is not implemented yet.")
    elif args.command == "analyze":
        print("Analysis is not implemented yet.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
