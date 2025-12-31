"""CLI for CrossSpec."""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Iterable, List, Optional

import typer

from crossspec.claims import Authority, Claim, ClaimIdGenerator, category_from_facets, build_claim
from crossspec.config import CrossspecConfig, KnowledgeSource, MailConfig, PptxConfig, load_config
from crossspec.extract import EmlExtractor, PdfExtractor, PptxExtractor, XlsxExtractor
from crossspec.io.jsonl import write_jsonl
from crossspec.tagging import load_taxonomy
from crossspec.tagging.llm_tagger import LlmTagger

app = typer.Typer(help="CrossSpec CLI")


@app.command()
def extract(config: str = typer.Option(..., "--config", help="Path to config YAML")) -> None:
    """Extract claims from configured knowledge sources."""
    cfg = load_config(config)
    claims = list(_extract_claims(cfg))
    output_path = Path(cfg.outputs.claims_dir) / cfg.outputs.jsonl_filename
    write_jsonl(output_path, claims)
    typer.echo(f"Wrote {len(claims)} claims to {output_path}")


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
    tagger: Optional[LlmTagger] = None
    facets_key = "facets"
    if cfg.tagging and cfg.tagging.enabled:
        taxonomy = load_taxonomy(cfg.tagging.taxonomy_path)
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
        return PdfExtractor(path=path, authority=authority)
    if source.type == "xlsx":
        if not source.xlsx:
            raise ValueError(f"Missing xlsx config for source {source.name}")
        return XlsxExtractor(path=path, authority=authority, config=source.xlsx)
    if source.type == "pptx":
        config = source.pptx or PptxConfig()
        return PptxExtractor(path=path, authority=authority, config=config)
    if source.type == "eml":
        config = source.mail or MailConfig()
        return EmlExtractor(path=path, authority=authority, config=config)
    raise ValueError(f"Unsupported source type: {source.type}")
