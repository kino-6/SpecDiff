"""Composition root for CrossSpec server."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from crossspec.config import CrossspecConfig
from crossspec.domain.models import Query, TraceResult, PlanResult, CoverageRow
from crossspec.domain.ports import ClaimStorePort, PlannerPort, RetrieverPort, TraceEnginePort
from crossspec.infra.fallback_retriever import FallbackRetriever
from crossspec.infra.jsonl_store import JsonlClaimStore
from crossspec.infra.planner_stub import StubPlanner
from crossspec.infra.trace_engine import DefaultTraceEngine
from crossspec.paths import resolve_path, resolve_repo_root
from crossspec.tagging import load_taxonomy
from crossspec.usecases.compute_coverage import compute_coverage
from crossspec.usecases.get_claim import get_claim
from crossspec.usecases.plan_requirement import plan_requirement
from crossspec.usecases.search_claims import search_claims
from crossspec.usecases.trace_claim import trace_claim


@dataclass
class ClaimPaths:
    spec_claims_path: Path
    code_claims_path: Path
    test_claims_path: Optional[Path] = None


@dataclass
class ServiceBundle:
    store: ClaimStorePort
    retriever: RetrieverPort
    trace_engine: TraceEnginePort
    planner: PlannerPort
    coverage_features: Optional[list[str]]

    def search_claims(self, query: Query, *, top_k: int = 20):
        return search_claims(self.store, query, top_k=top_k, retriever=self.retriever)

    def get_claim(self, claim_id: str):
        return get_claim(self.store, claim_id)

    def trace_claim(self, spec_claim_id: str, *, top_k: int = 10) -> TraceResult:
        return trace_claim(self.trace_engine, spec_claim_id, top_k=top_k)

    def compute_coverage(self, feature: Optional[str] = None) -> list[CoverageRow]:
        features = self.coverage_features
        if feature:
            features = [feature]
        return compute_coverage(self.store, features=features)

    def plan_requirement(self, requirement_text: str, hints: Optional[dict] = None) -> PlanResult:
        return plan_requirement(self.planner, requirement_text, hints=hints)


def resolve_claim_paths(config_path: Path, config: CrossspecConfig) -> ClaimPaths:
    repo_root = resolve_repo_root(config_path, config.project.repo_root)
    claims_dir = resolve_path(repo_root, config.outputs.claims_dir)
    spec_claims_path = claims_dir / config.outputs.jsonl_filename
    code_claims_path = claims_dir / "code_claims.jsonl"
    test_claims_path = claims_dir / "test_claims.jsonl"
    if not test_claims_path.exists():
        test_claims_path = None
    return ClaimPaths(
        spec_claims_path=spec_claims_path,
        code_claims_path=code_claims_path,
        test_claims_path=test_claims_path,
    )


def build_services(config_path: Path, config: CrossspecConfig, paths: ClaimPaths) -> ServiceBundle:
    claim_paths = [paths.spec_claims_path, paths.code_claims_path]
    if paths.test_claims_path:
        claim_paths.append(paths.test_claims_path)
    store = JsonlClaimStore(claim_paths)
    retriever = FallbackRetriever(store)
    trace_engine = DefaultTraceEngine(store=store, retriever=retriever)
    planner = StubPlanner()
    coverage_features = _load_taxonomy_features(config_path, config)
    return ServiceBundle(
        store=store,
        retriever=retriever,
        trace_engine=trace_engine,
        planner=planner,
        coverage_features=coverage_features,
    )


def _load_taxonomy_features(
    config_path: Path,
    config: CrossspecConfig,
) -> Optional[list[str]]:
    if not config.tagging or not config.tagging.taxonomy_path:
        return None
    repo_root = resolve_repo_root(config_path, config.project.repo_root)
    taxonomy_path = resolve_path(repo_root, config.tagging.taxonomy_path)
    if not taxonomy_path.exists():
        return None
    taxonomy = load_taxonomy(str(taxonomy_path))
    return list(taxonomy.feature)
