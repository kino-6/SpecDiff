"""Extractor base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Iterable

from crossspec.claims import Authority


@dataclass(frozen=True)
class ExtractedClaim:
    text_raw: str
    source_type: str
    source_path: str
    authority: Authority
    provenance: Dict[str, Any]


class Extractor(ABC):
    @abstractmethod
    def extract(self) -> Iterable[ExtractedClaim]:
        raise NotImplementedError
