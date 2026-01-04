"""CLI for CrossSpec."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Iterable, List, Optional

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal envs
    typer = None

from crossspec.claims import Authority, Claim, ClaimIdGenerator, SourceInfo, Status, category_from_facets, build_claim
from crossspec.config import CrossspecConfig, KnowledgeSource, MailConfig, PptxConfig, load_config
from crossspec.code_extract import (
    DEFAULT_EXCLUDES,
    default_includes,
    extract_c_cpp_units,
    extract_python_units,
    read_text_with_fallback,
    scan_files_with_summary,
)
from crossspec.io.jsonl import write_jsonl
from crossspec.paths import expand_paths, resolve_path, resolve_repo_root
from crossspec.tagging import load_taxonomy

if typer:
    app = typer.Typer(help="CrossSpec CLI")
else:
    app = None


def extract_command(config: str, save: bool = False) -> None:
    """Extract claims from configured knowledge sources."""
    cfg = load_config(config)
    config_path = Path(config)
    repo_root = resolve_repo_root(config_path, cfg.project.repo_root)
    output_path = _resolve_output_path(repo_root, cfg)
    message = f"Resolved repo_root={repo_root} output_path={output_path}"
    if typer:
        typer.echo(message)
    else:
        print(message)
    if save and output_path.exists():
        count = _count_jsonl_lines(output_path)
        message = f"Using existing claims at {output_path} ({count} claims)"
        if typer:
            typer.echo(message)
        else:
            print(message)
        return
    claims = list(_extract_claims(cfg, repo_root=repo_root, config_path=config_path))
    write_jsonl(output_path, claims)
    message = f"Wrote {len(claims)} claims to {output_path}"
    if typer:
        typer.echo(message)
    else:
        print(message)


if typer:

    @app.command()
    def extract(
        config: str = typer.Option(..., "--config", help="Path to config YAML"),
        save: bool = typer.Option(False, "--save", help="Reuse existing output if present"),
    ) -> None:
        extract_command(config, save=save)

    @app.command()
    def demo(config: str = typer.Option(..., "--config", help="Path to config YAML")) -> None:
        demo_command(config)

    @app.command()
    def search(
        config: Optional[str] = typer.Option(None, "--config", help="Path to config YAML"),
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

    @app.command(name="code-extract")
    def code_extract(
        repo: str = typer.Option(".", "--repo", help="Repository root to scan"),
        config: Optional[str] = typer.Option(None, "--config", help="Optional config YAML"),
        out: str = typer.Option(..., "--out", help="Output JSONL path"),
        include: Optional[List[str]] = typer.Option(None, "--include", help="Include glob (repeatable)"),
        exclude: Optional[List[str]] = typer.Option(None, "--exclude", help="Exclude glob (repeatable)"),
        unit: str = typer.Option("function", "--unit", help="Extraction unit (function|class|file)"),
        max_bytes: int = typer.Option(1_000_000, "--max-bytes", help="Skip files larger than this"),
        encoding: str = typer.Option("utf-8", "--encoding", help="Primary encoding"),
        language: str = typer.Option("all", "--language", help="Language filter (c|cpp|python|all)"),
        authority: str = typer.Option("informative", "--authority", help="Authority value"),
        status: str = typer.Option("active", "--status", help="Status value"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Print matched files"),
        save: bool = typer.Option(False, "--save", help="Reuse existing output if present"),
        top: Optional[int] = typer.Option(None, "--top", help="Limit number of units extracted"),
    ) -> None:
        code_extract_command(
            repo=repo,
            config=config,
            out=out,
            include=include,
            exclude=exclude,
            unit=unit,
            max_bytes=max_bytes,
            encoding=encoding,
            language=language,
            authority=authority,
            status=status,
            dry_run=dry_run,
            save=save,
            top=top,
        )

    @app.command()
    def index() -> None:
        """Placeholder for future indexing."""
        typer.echo("Indexing is not implemented yet.")


    @app.command()
    def analyze() -> None:
        """Placeholder for future analysis."""
        typer.echo("Analysis is not implemented yet.")


def _extract_claims(
    cfg: CrossspecConfig,
    *,
    repo_root: Path,
    config_path: Path,
) -> Iterable[Claim]:
    tagger: Optional[object] = None
    facets_key = "facets"
    if cfg.tagging and cfg.tagging.enabled:
        taxonomy_path = _resolve_taxonomy_path(
            repo_root=repo_root,
            config_path=config_path,
            taxonomy_path=cfg.tagging.taxonomy_path,
        )
        taxonomy = load_taxonomy(str(taxonomy_path))
        from crossspec.tagging.llm_tagger import LlmTagger

        tagger = LlmTagger(taxonomy=taxonomy, llm=cfg.tagging.llm)
        facets_key = cfg.tagging.output.facets_key

    id_generator = ClaimIdGenerator()

    for source in cfg.knowledge_sources:
        expanded = _expand_paths(repo_root, source.paths)
        message = f"Knowledge source '{source.name}': matched {len(expanded)} files"
        if typer:
            typer.echo(message)
        else:
            print(message)
        for path in expanded:
            extractor = _build_extractor(source, path)
            for extracted in extractor.extract():
                facets = None
                if tagger:
                    facets = tagger.tag(extracted.text_raw)
                category = category_from_facets(facets, category_hint=None)
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
    return expand_paths(repo_root, patterns)


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


def _resolve_output_path(repo_root: Path, cfg: CrossspecConfig) -> Path:
    claims_dir = resolve_path(repo_root, cfg.outputs.claims_dir)
    return claims_dir / cfg.outputs.jsonl_filename


def _resolve_taxonomy_path(repo_root: Path, config_path: Path, taxonomy_path: str) -> Path:
    resolved = resolve_path(repo_root, taxonomy_path)
    if not resolved.exists():
        message = (
            "Taxonomy file not found. "
            f"config_path={config_path.resolve()} "
            f"repo_root={repo_root} "
            f"taxonomy_path={taxonomy_path} "
            f"resolved_path={resolved}"
        )
        raise FileNotFoundError(message)
    return resolved


def demo_command(config: str) -> None:
    cfg = load_config(config)
    config_path = Path(config)
    repo_root = resolve_repo_root(config_path, cfg.project.repo_root)
    output_path = _resolve_output_path(repo_root, cfg)
    _run_demo(cfg, output_path=output_path, repo_root=repo_root, config_path=config_path)


def code_extract_command(
    *,
    repo: str,
    config: Optional[str],
    out: str,
    include: Optional[List[str]],
    exclude: Optional[List[str]],
    unit: str,
    max_bytes: int,
    encoding: str,
    language: str,
    authority: str,
    status: str,
    dry_run: bool,
    save: bool,
    top: Optional[int],
) -> None:
    repo_root = Path(repo).resolve()
    if config and repo == ".":
        cfg = load_config(config)
        config_path = Path(config)
        repo_root = resolve_repo_root(config_path, cfg.project.repo_root)
    includes = include or default_includes(language)
    excludes = exclude or list(DEFAULT_EXCLUDES)
    output_path = Path(out)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    if save and output_path.exists() and not dry_run:
        count = _count_jsonl_lines(output_path)
        message = f"Using existing claims at {output_path} ({count} claims)"
        if typer:
            typer.echo(message)
        else:
            print(message)
        return

    try:
        output_rel = output_path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        output_rel = None
    if output_rel:
        excludes = list(excludes) + [output_rel]

    scanned, scan_summary = scan_files_with_summary(
        repo_root=repo_root,
        includes=includes,
        excludes=excludes,
        max_bytes=max_bytes,
        language_filter=language,
    )
    if dry_run:
        for entry in scanned:
            print(entry.path)
        return

    id_generator = ClaimIdGenerator()
    claims: List[Claim] = []
    authority_value = Authority(authority)
    status_value = Status(status)
    extracted_count = 0
    decode_error_count = 0
    for entry in scanned:
        try:
            text, sha1 = read_text_with_fallback(entry.path, encoding)
        except UnicodeDecodeError as exc:
            decode_error_count += 1
            print(f"Skipping {entry.path}: {exc}")
            continue
        except OSError as exc:
            print(f"Skipping {entry.path}: {exc}")
            continue
        if entry.language == "python":
            extracted_units = extract_python_units(
                path=entry.path,
                source_path=entry.relative_path,
                text=text,
                unit=unit,
                authority=authority_value,
                sha1=sha1,
            )
        else:
            extracted_units = extract_c_cpp_units(
                path=entry.path,
                source_path=entry.relative_path,
                text=text,
                unit=unit,
                authority=authority_value,
                sha1=sha1,
                language=entry.language,
                is_header=entry.is_header,
            )
        for extracted in extracted_units:
            category_hint = _category_from_language(entry.language)
            category = category_from_facets(None, category_hint=category_hint)
            claim_id = id_generator.next_id(category)
            claim = build_claim(
                claim_id=claim_id,
                authority=authority_value,
                text_raw=extracted.text_raw,
                source_type=extracted.source_type,
                source_path=extracted.source_path,
                provenance=extracted.provenance,
                status=status_value,
            )
            claims.append(claim)
            extracted_count += 1
            if top is not None and extracted_count >= top:
                break
        if top is not None and extracted_count >= top:
            break

    write_jsonl(output_path, claims)
    message = f"Wrote {len(claims)} code claims to {output_path}"
    if typer:
        typer.echo(message)
    else:
        print(message)
    include_globs = ", ".join(includes) if includes else "(none)"
    exclude_globs = ", ".join(excludes) if excludes else "(none)"
    summary_message = (
        "Summary: "
        f"repo_root={repo_root}, "
        f"include={include_globs}, "
        f"exclude={exclude_globs}, "
        f"total_files_matched={scan_summary.total_files_matched}, "
        "total_files_skipped("
        f"excluded={scan_summary.skipped_excluded}, "
        f"too_large={scan_summary.skipped_too_large}, "
        f"decode_error={decode_error_count}"
        "), "
        f"total_units_extracted={extracted_count}"
    )
    if typer:
        typer.echo(summary_message)
    else:
        print(summary_message)
    if extracted_count == 0:
        top_paths = ", ".join(entry.relative_path for entry in scanned[:5])
        debug_message = f"Top scanned paths: {top_paths}" if top_paths else "Top scanned paths: (none)"
        if typer:
            typer.echo(debug_message)
        else:
            print(debug_message)


def _category_from_language(language: str) -> str:
    if language == "python":
        return "PY"
    if language == "c":
        return "C"
    return "CPP"


def _count_jsonl_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return 0


def _run_demo(cfg: CrossspecConfig, *, output_path: Path, repo_root: Path, config_path: Path) -> None:
    from collections import Counter
    import subprocess

    samples_script = Path("samples/generate_samples.py")
    if samples_script.exists():
        subprocess.run([sys.executable, str(samples_script)], check=True)
    else:
        print("samples/generate_samples.py not found; skipping sample generation.")

    pdf_expected = Path("samples/input/sample.pdf")
    if not pdf_expected.exists():
        raise RuntimeError(
            "Demo requires PDF sample generation. Install extras with "
            "`pip install -e \"./crossspec[demo]\"` (or `uv pip install -e ./crossspec[demo]`)."
        )
    claims = list(_extract_claims(cfg, repo_root=repo_root, config_path=config_path))
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
    config: Optional[str],
    query: Optional[str],
    feature: Optional[str],
    authority: Optional[str],
    source_type: Optional[str],
    top: int,
    claims_path: Optional[str],
    show_provenance: bool,
    show_source: bool,
) -> None:
    if claims_path:
        input_path = Path(claims_path)
    else:
        if not config:
            raise ValueError("--config is required when --claims is not provided")
        cfg = load_config(config)
        config_path = Path(config)
        repo_root = resolve_repo_root(config_path, cfg.project.repo_root)
        input_path = _resolve_output_path(repo_root, cfg)
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
    extract_parser.add_argument("--save", action="store_true", help="Reuse existing output if present")
    demo_parser = subparsers.add_parser("demo", help="Run demo generation and summary")
    demo_parser.add_argument("--config", required=True, help="Path to config YAML")
    search_parser = subparsers.add_parser("search", help="Search claims")
    search_parser.add_argument("--config", required=False, help="Path to config YAML")
    search_parser.add_argument("--query", required=False, help="Search query")
    search_parser.add_argument("--feature", required=False, help="Facet feature filter")
    search_parser.add_argument("--authority", required=False, help="Authority filter")
    search_parser.add_argument("--type", required=False, help="Source type filter")
    search_parser.add_argument("--top", type=int, default=10, help="Max results")
    search_parser.add_argument("--claims", required=False, help="Claims JSONL path")
    search_parser.add_argument("--show-provenance", action="store_true", help="Show provenance")
    search_parser.add_argument("--show-source", action="store_true", help="Show source details")
    code_extract_parser = subparsers.add_parser("code-extract", help="Extract code claims")
    code_extract_parser.add_argument("--repo", default=".", help="Repository root to scan")
    code_extract_parser.add_argument("--config", required=False, help="Optional config YAML")
    code_extract_parser.add_argument("--out", required=True, help="Output JSONL path")
    code_extract_parser.add_argument("--include", action="append", help="Include glob (repeatable)")
    code_extract_parser.add_argument("--exclude", action="append", help="Exclude glob (repeatable)")
    code_extract_parser.add_argument("--unit", default="function", help="Extraction unit (function|class|file)")
    code_extract_parser.add_argument("--max-bytes", type=int, default=1_000_000, help="Skip files larger than this")
    code_extract_parser.add_argument("--encoding", default="utf-8", help="Primary encoding")
    code_extract_parser.add_argument("--language", default="all", help="Language filter (c|cpp|python|all)")
    code_extract_parser.add_argument("--authority", default="informative", help="Authority value")
    code_extract_parser.add_argument("--status", default="active", help="Status value")
    code_extract_parser.add_argument("--dry-run", action="store_true", help="Print matched files")
    code_extract_parser.add_argument("--save", action="store_true", help="Reuse existing output if present")
    code_extract_parser.add_argument("--top", type=int, default=None, help="Limit number of units extracted")
    subparsers.add_parser("index", help="Indexing (not implemented)")
    subparsers.add_parser("analyze", help="Analysis (not implemented)")
    args = parser.parse_args()
    if args.command == "extract":
        extract_command(args.config, save=args.save)
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
    elif args.command == "code-extract":
        code_extract_command(
            repo=args.repo,
            config=args.config,
            out=args.out,
            include=args.include,
            exclude=args.exclude,
            unit=args.unit,
            max_bytes=args.max_bytes,
            encoding=args.encoding,
            language=args.language,
            authority=args.authority,
            status=args.status,
            dry_run=args.dry_run,
            save=args.save,
            top=args.top,
        )
    elif args.command == "index":
        print("Indexing is not implemented yet.")
    elif args.command == "analyze":
        print("Analysis is not implemented yet.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
