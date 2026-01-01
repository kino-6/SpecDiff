from pathlib import Path

import pytest

from crossspec.tagging.taxonomy import load_taxonomy


def test_load_taxonomy_from_file():
    path = Path(__file__).resolve().parents[1] / "taxonomy" / "features.yaml"
    taxonomy = load_taxonomy(str(path))
    assert taxonomy.version == 1
    assert "feature" in taxonomy.facet_keys
    assert "brake" in taxonomy.feature


def test_load_taxonomy_missing_facets(tmp_path):
    payload = """
version: 1
facet_keys: [feature]
feature: [alpha]
artifact: [note]
component: [Core]
"""
    file_path = tmp_path / "bad.yaml"
    file_path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError):
        load_taxonomy(str(file_path))
