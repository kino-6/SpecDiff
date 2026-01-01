"""LLM-based tagging."""

from __future__ import annotations

import json
from typing import Any, Dict

import requests

from crossspec.config import TaggingLlm
from crossspec.tagging.taxonomy import Taxonomy


DEFAULT_FALLBACK = {
    "feature": [],
    "artifact": "note",
    "component": [],
    "confidence": 0.0,
}


class LlmTagger:
    def __init__(self, taxonomy: Taxonomy, llm: TaggingLlm) -> None:
        self.taxonomy = taxonomy
        self.llm = llm

    def tag(self, text: str) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.llm.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.llm.api_key}"},
                json={
                    "model": self.llm.model,
                    "temperature": self.llm.temperature,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a classifier. Reply with strict JSON only, no extra text."
                            ),
                        },
                        {
                            "role": "user",
                            "content": self._prompt(text),
                        },
                    ],
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            facets = json.loads(content)
            if self._validate_facets(facets):
                return facets
        except Exception:
            return DEFAULT_FALLBACK.copy()
        return DEFAULT_FALLBACK.copy()

    def _prompt(self, text: str) -> str:
        return (
            "Classify the following claim into facets using ONLY allowed values. "
            "Return JSON with keys: feature (list), artifact (string), component (list), confidence (0-1).\n"
            f"Allowed feature values: {self.taxonomy.feature}\n"
            f"Allowed artifact values: {self.taxonomy.artifact}\n"
            f"Allowed component values: {self.taxonomy.component}\n"
            f"Claim text: {text}"
        )

    def _validate_facets(self, facets: Dict[str, Any]) -> bool:
        if not isinstance(facets, dict):
            return False
        feature = facets.get("feature", [])
        artifact = facets.get("artifact")
        component = facets.get("component", [])
        if not isinstance(feature, list) or not isinstance(component, list):
            return False
        if artifact not in self.taxonomy.artifact:
            return False
        if any(item not in self.taxonomy.feature for item in feature):
            return False
        if any(item not in self.taxonomy.component for item in component):
            return False
        confidence = facets.get("confidence")
        if not isinstance(confidence, (int, float)):
            return False
        if not 0.0 <= float(confidence) <= 1.0:
            return False
        return True
