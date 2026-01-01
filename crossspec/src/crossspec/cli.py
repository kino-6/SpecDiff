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

from crossspec.claims import Authority, Claim, ClaimIdGenerator, category_from_facets, build_claim
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

    print("Sample claims:")
    if not claims:
        print("  (no claims found)")
        return
    for claim in claims[:3]:
        text_preview = claim.text_raw.replace("\n", " ")[:120]
        print(f"  {claim.claim_id} | {claim.source.path} | {claim.provenance}")
        print(f"    {text_preview}")


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
    subparsers.add_parser("index", help="Indexing (not implemented)")
    subparsers.add_parser("analyze", help="Analysis (not implemented)")
    args = parser.parse_args()
    if args.command == "extract":
        extract_command(args.config)
    elif args.command == "demo":
        demo_command(args.config)
    elif args.command == "index":
        print("Indexing is not implemented yet.")
    elif args.command == "analyze":
        print("Analysis is not implemented yet.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
