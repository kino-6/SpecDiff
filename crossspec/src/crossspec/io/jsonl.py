"""JSONL writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from crossspec.claims import Claim


def write_jsonl(path: Path, claims: Iterable[Claim]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for claim in claims:
            handle.write(json.dumps(claim.model_dump(), ensure_ascii=False))
            handle.write("\n")
