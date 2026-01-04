"""Keyword-based tagging helper."""

from __future__ import annotations

from typing import Any, Dict, List

from crossspec.tagging.taxonomy import Taxonomy


class KeywordTagger:
    def __init__(self, taxonomy: Taxonomy) -> None:
        self.taxonomy = taxonomy
        self._feature_lookup = [(feature, feature.lower()) for feature in taxonomy.feature]

    def tag(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        matched_features = [
            feature for feature, feature_lower in self._feature_lookup if feature_lower in text_lower
        ]
        return {
            "feature": matched_features,
            "artifact": "note",
            "component": [],
            "confidence": 0.0,
        }

    def features_for(self, text: str) -> List[str]:
        return self.tag(text).get("feature", [])
