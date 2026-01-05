"""OpenWebUI tool API adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from crossspec.claims import Claim
from crossspec.domain.models import TraceResult
from crossspec.server.wire import ServiceBundle


class TraceRequest(BaseModel):
    spec_claim_id: str
    top: int = 5


class PlanRequest(BaseModel):
    requirement_text: str
    hints: Optional[dict] = None


def create_app(services: ServiceBundle) -> FastAPI:
    app = FastAPI(title="CrossSpec Server (OpenWebUI)")

    @app.post("/tools/trace")
    def trace_tool(payload: TraceRequest) -> Dict[str, Any]:
        trace = services.trace_claim(payload.spec_claim_id, top_k=payload.top)
        markdown = format_trace_markdown(trace)
        return {
            "markdown": markdown,
            "data": _dump_trace(trace),
        }

    @app.post("/tools/plan")
    def plan_tool(payload: PlanRequest) -> Dict[str, Any]:
        plan = services.plan_requirement(payload.requirement_text, hints=payload.hints)
        return {
            "markdown": plan.markdown,
            "data": plan.model_dump(),
        }

    return app


def format_trace_markdown(trace: TraceResult) -> str:
    lines: List[str] = [
        "## CrossSpec Trace",
        "",
        f"**Spec** (`{trace.spec.claim_id}`)",
        _indent(_excerpt(trace.spec.text_raw)),
        "",
        "**Impl matches**",
    ]
    if trace.impl:
        lines.extend([_format_match(claim) for claim in trace.impl])
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("**Test matches**")
    if trace.test:
        lines.extend([_format_match(claim) for claim in trace.test])
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append(
        f"Coverage: {trace.coverage.status} "
        f"(impl={trace.coverage.impl_count}, test={trace.coverage.test_count})"
    )
    return "\n".join(lines)


def _dump_trace(trace: TraceResult) -> Dict[str, Any]:
    return {
        "spec": trace.spec.model_dump(),
        "impl": [claim.model_dump() for claim in trace.impl],
        "test": [claim.model_dump() for claim in trace.test],
        "coverage": trace.coverage.model_dump(),
    }


def _format_match(claim: Claim) -> str:
    location = _format_location(claim)
    excerpt = _excerpt(claim.text_raw)
    return f"- {location}\n  {_indent(excerpt)}"


def _format_location(claim: Claim) -> str:
    source_path = claim.source.path
    provenance = claim.provenance or {}
    symbol = provenance.get("symbol")
    line_start = provenance.get("line_start")
    line_end = provenance.get("line_end")
    line_range = None
    if line_start is not None and line_end is not None:
        line_range = f"{line_start}-{line_end}"
    elif line_start is not None:
        line_range = str(line_start)
    parts = [source_path]
    if line_range:
        parts.append(f":{line_range}")
    if symbol:
        parts.append(f" `{symbol}`")
    return "".join(parts)


def _excerpt(text: str, limit: int = 180) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1] + "…"


def _indent(text: str, prefix: str = "> ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())
