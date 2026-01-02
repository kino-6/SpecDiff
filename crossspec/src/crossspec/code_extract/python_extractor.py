"""Python code extractor."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Iterable, List, Optional

from crossspec.claims import Authority
from crossspec.extract.base import ExtractedClaim

from crossspec.code_extract.scanner import iter_lines_slice

logger = logging.getLogger(__name__)


def extract_python_units(
    *,
    path: Path,
    source_path: str,
    text: str,
    unit: str,
    authority: Authority,
    sha1: str,
) -> List[ExtractedClaim]:
    lines = text.splitlines()
    total_lines = len(lines)
    if unit == "file":
        return [
            ExtractedClaim(
                text_raw=iter_lines_slice(lines, 1, total_lines),
                source_type="code",
                source_path=source_path,
                authority=authority,
                provenance=_build_provenance(
                    path=source_path,
                    language="python",
                    unit="file",
                    symbol=Path(source_path).name,
                    line_start=1,
                    line_end=total_lines,
                    sha1=sha1,
                ),
            )
        ]

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        logger.warning("Failed to parse %s: %s", path, exc)
        return []

    extracted: List[ExtractedClaim] = []
    if unit == "class":
        for node in _iter_class_nodes(tree):
            line_start, line_end = _node_line_span(node, lines)
            extracted.append(
                ExtractedClaim(
                    text_raw=iter_lines_slice(lines, line_start, line_end),
                    source_type="code",
                    source_path=source_path,
                    authority=authority,
                    provenance=_build_provenance(
                        path=source_path,
                        language="python",
                        unit="class",
                        symbol=node.name,
                        line_start=line_start,
                        line_end=line_end,
                        sha1=sha1,
                    ),
                )
            )
        return extracted

    if unit == "function":
        for node in _iter_function_nodes(tree):
            line_start, line_end = _node_line_span(node, lines)
            symbol = node.name
            if isinstance(getattr(node, "parent", None), ast.ClassDef):
                symbol = f"{node.parent.name}.{node.name}"
            extracted.append(
                ExtractedClaim(
                    text_raw=iter_lines_slice(lines, line_start, line_end),
                    source_type="code",
                    source_path=source_path,
                    authority=authority,
                    provenance=_build_provenance(
                        path=source_path,
                        language="python",
                        unit="function",
                        symbol=symbol,
                        line_start=line_start,
                        line_end=line_end,
                        sha1=sha1,
                    ),
                )
            )
    return extracted


def _iter_class_nodes(tree: ast.AST) -> Iterable[ast.ClassDef]:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef):
            yield node


def _iter_function_nodes(tree: ast.AST) -> Iterable[ast.AST]:
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if isinstance(getattr(node, "parent", None), (ast.Module, ast.ClassDef)):
                yield node


def _node_line_span(node: ast.AST, lines: List[str]) -> tuple[int, int]:
    line_start = getattr(node, "lineno", 1) or 1
    end_lineno = getattr(node, "end_lineno", None)
    if end_lineno is None:
        end_lineno = _fallback_end_lineno(line_start, lines)
    line_end = max(line_start, min(end_lineno, len(lines)))
    return line_start, line_end


def _fallback_end_lineno(line_start: int, lines: List[str]) -> int:
    if line_start > len(lines):
        return len(lines)
    indent = _indent_of(lines[line_start - 1])
    for idx in range(line_start, len(lines)):
        if not lines[idx].strip():
            continue
        if _indent_of(lines[idx]) <= indent:
            return idx
    return len(lines)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _build_provenance(
    *,
    path: str,
    language: str,
    unit: str,
    symbol: str,
    line_start: int,
    line_end: int,
    sha1: str,
) -> dict:
    return {
        "path": path,
        "language": language,
        "unit": unit,
        "symbol": symbol,
        "line_start": line_start,
        "line_end": line_end,
        "sha1_of_file": sha1,
    }
