"""Diagnostic rules for brake safety monitoring."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiagnosticRule:
    name: str
    limit: int
    severity: str

    def evaluate(self, value: int) -> bool:
        """Return True if the value exceeds the safety limit."""
        return value > self.limit


def evaluate_rules(rules: list[DiagnosticRule], value: int) -> list[str]:
    """Evaluate diagnostics rules and return triggered names."""
    return [rule.name for rule in rules if rule.evaluate(value)]


def is_fatal_error(severity: str) -> bool:
    """Classify error handling severity."""
    return severity.lower() in {"fatal", "critical"}


def format_error_report(triggered: list[str]) -> str:
    """Format diagnostics report for comms messaging."""
    if not triggered:
        return "diagnostics: none"
    return "diagnostics: " + ", ".join(triggered)


def calibration_rule() -> DiagnosticRule:
    """Rule ensuring calibration values are within safety bounds."""
    return DiagnosticRule(name="calibration_range", limit=50, severity="warn")


def build_default_rules() -> list[DiagnosticRule]:
    """Build default safety diagnostics rules."""
    return [
        DiagnosticRule(name="over_temp", limit=85, severity="critical"),
        DiagnosticRule(name="pressure_limit", limit=120, severity="fatal"),
        calibration_rule(),
    ]
