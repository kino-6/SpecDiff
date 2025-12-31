"""PDF extractor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from crossspec.claims import Authority
from crossspec.extract.base import ExtractedClaim, Extractor


class PdfExtractor(Extractor):
    def __init__(self, path: Path, authority: Authority) -> None:
        self.path = path
        self.authority = authority

    def extract(self) -> Iterable[ExtractedClaim]:
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF extraction") from exc

        doc = fitz.open(self.path)
        for page_index, page in enumerate(doc, start=1):
            blocks = page.get_text("blocks")
            for block in blocks:
                x0, y0, x1, y1, text, *_ = block
                paragraphs = self._split_paragraphs(text)
                for paragraph in paragraphs:
                    if len(paragraph.strip()) < 40:
                        continue
                    provenance = {"page": page_index, "bbox": [x0, y0, x1, y1]}
                    yield ExtractedClaim(
                        text_raw=paragraph.strip(),
                        source_type="pdf",
                        source_path=str(self.path),
                        authority=self.authority,
                        provenance=provenance,
                    )

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        parts = re.split(r"\n\s*\n", text)
        return [part for part in parts if part.strip()]
