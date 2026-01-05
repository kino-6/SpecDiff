"""Plan requirement use-case."""

from __future__ import annotations

from typing import Optional

from crossspec.domain.models import PlanResult
from crossspec.domain.ports import PlannerPort


def plan_requirement(
    planner: PlannerPort,
    requirement_text: str,
    *,
    hints: Optional[dict] = None,
) -> PlanResult:
    return planner.plan(requirement_text, hints=hints)
