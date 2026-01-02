"""C/C++ code extractor using heuristic scanning."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from crossspec.claims import Authority
from crossspec.extract.base import ExtractedClaim

from crossspec.code_extract.scanner import iter_lines_slice

logger = logging.getLogger(__name__)

CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch"}


class ScanState:
    def __init__(self) -> None:
        self.in_block_comment = False
        self.in_line_comment = False
        self.in_string = False
        self.in_char = False
        self.escape_next = False

    def reset_line(self) -> None:
        self.in_line_comment = False



def extract_c_cpp_units(
    *,
    path: Path,
    source_path: str,
    text: str,
    unit: str,
    authority: Authority,
    sha1: str,
    language: str,
    is_header: bool,
) -> List[ExtractedClaim]:
    lines = text.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    if unit == "file":
        return [
            _build_claim(
                source_path=source_path,
                authority=authority,
                lines=lines,
                line_start=1,
                line_end=total_lines,
                unit="file",
                symbol=Path(source_path).name,
                sha1=sha1,
                language=language,
            )
        ]

    if unit == "class":
        claims = [
            _build_claim(
                source_path=source_path,
                authority=authority,
                lines=lines,
                line_start=start,
                line_end=end,
                unit="class",
                symbol=name,
                sha1=sha1,
                language=language,
            )
            for name, start, end in _find_class_blocks(lines)
        ]
        return claims

    if unit == "function":
        function_blocks = list(_find_function_blocks(lines))
        if not function_blocks and is_header:
            return [
                _build_claim(
                    source_path=source_path,
                    authority=authority,
                    lines=lines,
                    line_start=1,
                    line_end=total_lines,
                    unit="file",
                    symbol=Path(source_path).name,
                    sha1=sha1,
                    language=language,
                )
            ]
        return [
            _build_claim(
                source_path=source_path,
                authority=authority,
                lines=lines,
                line_start=start,
                line_end=end,
                unit="function",
                symbol=name,
                sha1=sha1,
                language=language,
            )
            for name, start, end in function_blocks
        ]

    return []


def _build_claim(
    *,
    source_path: str,
    authority: Authority,
    lines: List[str],
    line_start: int,
    line_end: int,
    unit: str,
    symbol: str,
    sha1: str,
    language: str,
) -> ExtractedClaim:
    return ExtractedClaim(
        text_raw=iter_lines_slice(lines, line_start, line_end),
        source_type="code",
        source_path=source_path,
        authority=authority,
        provenance={
            "path": source_path,
            "language": language,
            "unit": unit,
            "symbol": symbol,
            "line_start": line_start,
            "line_end": line_end,
            "sha1_of_file": sha1,
        },
    )


def _find_class_blocks(lines: List[str]) -> Iterable[Tuple[str, int, int]]:
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        match = re.search(r"\b(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)", line)
        if not match:
            continue
        name = match.group(2)
        brace_location = _find_opening_brace(lines, idx, line.find(match.group(0)))
        if not brace_location:
            continue
        start_line, start_col = brace_location
        end_line = _find_block_end(lines, start_line, start_col)
        if end_line is None:
            logger.debug("Failed to match class block in %s", name)
            continue
        yield name, idx + 1, end_line + 1


def _find_function_blocks(lines: List[str]) -> Iterable[Tuple[str, int, int]]:
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.lstrip().startswith("#define"):
            idx += 1
            continue
        if "(" not in line:
            idx += 1
            continue
        signature, end_idx, brace_location = _collect_signature(lines, idx)
        if not signature:
            idx = max(idx + 1, end_idx)
            continue
        name = _extract_function_name(signature)
        if not name:
            idx = max(idx + 1, end_idx)
            continue
        if name in CONTROL_KEYWORDS:
            idx = max(idx + 1, end_idx)
            continue
        if not brace_location:
            idx = max(idx + 1, end_idx)
            continue
        brace_line, brace_col = brace_location
        end_line = _find_block_end(lines, brace_line, brace_col)
        if end_line is None:
            idx = max(idx + 1, end_idx)
            continue
        yield name, idx + 1, end_line + 1
        idx = max(end_line + 1, end_idx + 1)


def _collect_signature(
    lines: List[str], start_idx: int, max_lines: int = 25
) -> Tuple[str, int, Optional[Tuple[int, int]]]:
    state = ScanState()
    parts: List[str] = []
    end_idx = start_idx
    brace_location: Optional[Tuple[int, int]] = None

    for idx in range(start_idx, min(len(lines), start_idx + max_lines)):
        line = lines[idx]
        end_idx = idx
        state.reset_line()
        parts.append(line)
        for col, char in enumerate(line):
            if state.in_line_comment:
                break
            if state.escape_next:
                state.escape_next = False
                continue
            if char == "\\" and (state.in_string or state.in_char):
                state.escape_next = True
                continue
            if state.in_block_comment:
                if char == "*" and _peek(line, col) == "/":
                    state.in_block_comment = False
                continue
            if char == "/" and _peek(line, col) == "*" and not state.in_string and not state.in_char:
                state.in_block_comment = True
                continue
            if char == "/" and _peek(line, col) == "/" and not state.in_string and not state.in_char:
                state.in_line_comment = True
                continue
            if char == '"' and not state.in_char:
                state.in_string = not state.in_string
            elif char == "'" and not state.in_string:
                state.in_char = not state.in_char
            if state.in_string or state.in_char:
                continue
            if char == ";":
                return "", end_idx, None
            if char == "{":
                brace_location = (idx, col)
                signature = "\n".join(parts)
                return signature, end_idx, brace_location
    return "", end_idx, None


def _extract_function_name(signature: str) -> Optional[str]:
    stripped = " ".join(signature.split())
    matches = re.findall(r"([A-Za-z_][A-Za-z0-9_:~]*)\s*\(", stripped)
    if not matches:
        return None
    name = matches[-1]
    return name


def _find_opening_brace(
    lines: List[str], start_line: int, start_col: int
) -> Optional[Tuple[int, int]]:
    state = ScanState()
    for idx in range(start_line, len(lines)):
        line = lines[idx]
        state.reset_line()
        for col, char in enumerate(line):
            if idx == start_line and col < start_col:
                continue
            if state.in_line_comment:
                break
            if state.escape_next:
                state.escape_next = False
                continue
            if char == "\\" and (state.in_string or state.in_char):
                state.escape_next = True
                continue
            if state.in_block_comment:
                if char == "*" and _peek(line, col) == "/":
                    state.in_block_comment = False
                continue
            if char == "/" and _peek(line, col) == "*" and not state.in_string and not state.in_char:
                state.in_block_comment = True
                continue
            if char == "/" and _peek(line, col) == "/" and not state.in_string and not state.in_char:
                state.in_line_comment = True
                continue
            if char == '"' and not state.in_char:
                state.in_string = not state.in_string
            elif char == "'" and not state.in_string:
                state.in_char = not state.in_char
            if state.in_string or state.in_char:
                continue
            if char == "{":
                return idx, col
            if char == ";":
                return None
    return None


def _find_block_end(lines: List[str], start_line: int, start_col: int) -> Optional[int]:
    state = ScanState()
    brace_count = 0
    for idx in range(start_line, len(lines)):
        line = lines[idx]
        state.reset_line()
        for col, char in enumerate(line):
            if idx == start_line and col < start_col:
                continue
            if state.in_line_comment:
                break
            if state.escape_next:
                state.escape_next = False
                continue
            if char == "\\" and (state.in_string or state.in_char):
                state.escape_next = True
                continue
            if state.in_block_comment:
                if char == "*" and _peek(line, col) == "/":
                    state.in_block_comment = False
                continue
            if char == "/" and _peek(line, col) == "*" and not state.in_string and not state.in_char:
                state.in_block_comment = True
                continue
            if char == "/" and _peek(line, col) == "/" and not state.in_string and not state.in_char:
                state.in_line_comment = True
                continue
            if char == '"' and not state.in_char:
                state.in_string = not state.in_string
            elif char == "'" and not state.in_string:
                state.in_char = not state.in_char
            if state.in_string or state.in_char:
                continue
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return idx
    return None


def _peek(line: str, col: int) -> str:
    if col + 1 < len(line):
        return line[col + 1]
    return ""
