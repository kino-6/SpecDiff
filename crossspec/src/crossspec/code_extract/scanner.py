"""File scanning utilities for code extraction."""

from __future__ import annotations

import fnmatch
import glob
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


DEFAULT_EXCLUDES = [
    "**/.git/**",
    "**/.venv/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/build/**",
    "**/dist/**",
    "**/node_modules/**",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/.tox/**",
    "**/outputs/**",
    "**/samples/output/**",
    "**/samples/input/**",
]

DEFAULT_INCLUDE_C = ["**/*.c", "**/*.h"]
DEFAULT_INCLUDE_CPP = ["**/*.cc", "**/*.cpp", "**/*.cxx", "**/*.hpp", "**/*.hh"]
DEFAULT_INCLUDE_PYTHON = ["**/*.py"]

LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "c": {".c", ".h"},
    "cpp": {".cc", ".cpp", ".cxx", ".hpp", ".hh"},
}


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    relative_path: str
    language: str
    is_header: bool


@dataclass(frozen=True)
class ScanSummary:
    total_files_matched: int
    skipped_excluded: int
    skipped_too_large: int


def default_includes(language: str) -> List[str]:
    if language == "python":
        return list(DEFAULT_INCLUDE_PYTHON)
    if language == "c":
        return list(DEFAULT_INCLUDE_C)
    if language == "cpp":
        return list(DEFAULT_INCLUDE_CPP)
    if language == "all":
        return list(DEFAULT_INCLUDE_C + DEFAULT_INCLUDE_CPP + DEFAULT_INCLUDE_PYTHON)
    raise ValueError(f"Unsupported language filter: {language}")


def detect_language(path: Path) -> Optional[str]:
    suffix = path.suffix.lower()
    for language, extensions in LANGUAGE_EXTENSIONS.items():
        if suffix in extensions:
            return language
    return None


def scan_files(
    *,
    repo_root: Path,
    includes: Sequence[str],
    excludes: Sequence[str],
    max_bytes: int,
    language_filter: str,
) -> List[ScannedFile]:
    scanned, _summary = scan_files_with_summary(
        repo_root=repo_root,
        includes=includes,
        excludes=excludes,
        max_bytes=max_bytes,
        language_filter=language_filter,
    )
    return scanned


def scan_files_with_summary(
    *,
    repo_root: Path,
    includes: Sequence[str],
    excludes: Sequence[str],
    max_bytes: int,
    language_filter: str,
) -> Tuple[List[ScannedFile], ScanSummary]:
    repo_root = repo_root.resolve()
    matches: set[Path] = set()
    for pattern in includes:
        if Path(pattern).is_absolute():
            glob_pattern = pattern
        else:
            glob_pattern = str(repo_root / pattern)
        for match in glob.glob(glob_pattern, recursive=True):
            matches.add(Path(match))

    scanned: List[ScannedFile] = []
    matched_files = 0
    skipped_excluded = 0
    skipped_too_large = 0
    for path in sorted(matches, key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        resolved_path = path.resolve()
        try:
            rel_path = resolved_path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        matched_files += 1
        if _is_excluded(rel_path, excludes):
            skipped_excluded += 1
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_bytes:
            skipped_too_large += 1
            continue
        language = detect_language(path)
        if not language:
            continue
        if language_filter != "all" and language != language_filter:
            continue
        is_header = path.suffix.lower() in {".h", ".hpp", ".hh"}
        scanned.append(
            ScannedFile(
                path=resolved_path,
                relative_path=rel_path,
                language=language,
                is_header=is_header,
            )
        )
    summary = ScanSummary(
        total_files_matched=matched_files,
        skipped_excluded=skipped_excluded,
        skipped_too_large=skipped_too_large,
    )
    return scanned, summary


def _is_excluded(rel_path: str, excludes: Sequence[str]) -> bool:
    anchored_path = f"/{rel_path}"
    return any(
        fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(anchored_path, pattern)
        for pattern in excludes
    )


def read_text_with_fallback(path: Path, encoding: str) -> Tuple[str, str]:
    data = path.read_bytes()
    sha1 = hashlib.sha1(data).hexdigest()
    for candidate in (encoding, "utf-8-sig", "latin-1"):
        try:
            return data.decode(candidate), sha1
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), sha1


def iter_lines_slice(lines: List[str], line_start: int, line_end: int) -> str:
    start_index = max(line_start - 1, 0)
    end_index = min(line_end, len(lines))
    return "\n".join(lines[start_index:end_index])
