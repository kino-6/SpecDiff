"""Minimal YAML loader with PyYAML fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_yaml(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    content = file_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return _parse_minimal_yaml(content)
    return yaml.safe_load(content)


def _parse_minimal_yaml(content: str) -> Dict[str, Any]:
    lines = _strip_comments(content)
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(0, root)]
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        stripped = line.strip()
        if stripped.startswith("- "):
            if not isinstance(container, list):
                raise ValueError("Invalid YAML: list item under non-list container")
            item = stripped[2:].strip()
            if not item:
                new_map: Dict[str, Any] = {}
                container.append(new_map)
                stack.append((indent + 2, new_map))
            elif ":" in item:
                key, value = _split_key_value(item)
                new_map = {key: _parse_value(value)} if value != "" else {key: _new_container(lines, idx, indent)}
                container.append(new_map)
                if value == "":
                    stack.append((indent + 2, new_map[key]))
            else:
                container.append(_parse_value(item))
        else:
            key, value = _split_key_value(stripped)
            if value == "":
                new_container = _new_container(lines, idx, indent)
                if isinstance(container, dict):
                    container[key] = new_container
                else:
                    raise ValueError("Invalid YAML: mapping under list without key")
                stack.append((indent + 2, new_container))
            else:
                if isinstance(container, dict):
                    container[key] = _parse_value(value)
                else:
                    raise ValueError("Invalid YAML: mapping under list without key")
        idx += 1
    return root


def _strip_comments(content: str) -> List[str]:
    lines = []
    for line in content.splitlines():
        if "#" in line:
            index = line.find("#")
            line = line[:index]
        lines.append(line.rstrip("\n"))
    return lines


def _split_key_value(line: str) -> Tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Invalid YAML line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(item.strip()) for item in inner.split(",")]
    if value in {"null", "None", "~"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith(("\"", "'")) and value.endswith(("\"", "'")) and len(value) >= 2:
        return value[1:-1]
    if _is_int(value):
        return int(value)
    if _is_float(value):
        return float(value)
    return value


def _new_container(lines: List[str], idx: int, indent: int) -> Any:
    next_line = _peek_next_nonempty(lines, idx)
    if next_line is None:
        return {}
    next_indent = len(next_line) - len(next_line.lstrip(" "))
    if next_indent <= indent:
        return {}
    stripped = next_line.strip()
    if stripped.startswith("- "):
        return []
    return {}


def _peek_next_nonempty(lines: List[str], idx: int) -> str | None:
    for next_line in lines[idx + 1 :]:
        if next_line.strip():
            return next_line
    return None


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return "." in value
