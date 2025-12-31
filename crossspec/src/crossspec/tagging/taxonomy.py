"""Taxonomy loader and validation."""

from __future__ import annotations

from typing import List

from crossspec.pydantic_compat import BaseModel, field_validator

from crossspec.yaml_utils import load_yaml

class Taxonomy(BaseModel):
    version: int
    facet_keys: List[str]
    feature: List[str]
    artifact: List[str]
    component: List[str]

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("Only taxonomy version 1 is supported")
        return value


def load_taxonomy(path: str) -> Taxonomy:
    payload = load_yaml(path)
    taxonomy = Taxonomy(**payload)
    _validate_facets(taxonomy)
    return taxonomy


def _validate_facets(taxonomy: Taxonomy) -> None:
    required = {"feature", "artifact", "component"}
    missing = required - set(taxonomy.facet_keys)
    if missing:
        raise ValueError(f"Missing required facet keys: {sorted(missing)}")
