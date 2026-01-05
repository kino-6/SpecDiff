"""Planner stub implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from crossspec.domain.models import PlanResult
from crossspec.domain.ports import PlannerPort


@dataclass
class StubPlanner(PlannerPort):
    def plan(self, requirement_text: str, hints: Optional[dict] = None) -> PlanResult:
        requirement = requirement_text.strip() if requirement_text else ""
        hint_lines: List[str] = []
        for key, value in (hints or {}).items():
            hint_lines.append(f"- {key}: {value}")

        markdown_lines = [
            "## CrossSpec Plan (stub)",
            "",
            "**Requirement**",
            requirement or "(empty)",
        ]
        if hint_lines:
            markdown_lines.extend(["", "**Hints**", *hint_lines])
        markdown_lines.extend(
            [
                "",
                "**Implementation Plan**",
                "1. TODO: Integrate LLM-backed planner.",
                "2. TODO: Map requirement to code modules.",
                "",
                "**Test Plan**",
                "1. TODO: Add coverage tests.",
            ]
        )
        markdown = "\n".join(markdown_lines)

        req_breakdown = [requirement] if requirement else []
        impl_plan = [
            "TODO: Integrate LLM-backed planner.",
            "TODO: Map requirement to code modules.",
        ]
        test_plan = ["TODO: Add coverage tests."]
        assumptions = ["No LLM provider configured; using stub planner."]
        return PlanResult(
            markdown=markdown,
            req_breakdown=req_breakdown,
            impl_plan=impl_plan,
            test_plan=test_plan,
            assumptions=assumptions,
        )
