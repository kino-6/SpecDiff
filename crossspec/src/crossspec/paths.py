"""Path resolution helpers for config-driven paths."""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Iterable, List


def is_absolute_like(path: str) -> bool:
    return Path(path).is_absolute() or path.startswith("~")


def resolve_repo_root(config_file_path: Path, repo_root: str) -> Path:
    config_dir = config_file_path.resolve().parent
    if is_absolute_like(repo_root):
        return Path(repo_root).expanduser().resolve()
    return (config_dir / repo_root).resolve()


def resolve_path(repo_root_abs: Path, path: str) -> Path:
    if is_absolute_like(path):
        return Path(path).expanduser().resolve()
    return (repo_root_abs / path).resolve()


def resolve_glob(repo_root_abs: Path, pattern: str) -> List[Path]:
    if is_absolute_like(pattern):
        glob_pattern = str(Path(pattern).expanduser())
    else:
        glob_pattern = str(repo_root_abs / pattern)
    matches = glob.glob(glob_pattern, recursive=True)
    return sorted({Path(match).resolve() for match in matches})


def expand_paths(repo_root_abs: Path, patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for pattern in patterns:
        paths.extend(resolve_glob(repo_root_abs, pattern))
    return sorted({path for path in paths})
