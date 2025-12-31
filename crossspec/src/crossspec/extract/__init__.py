"""Extractors."""

from crossspec.extract.base import ExtractedClaim, Extractor
from crossspec.extract.eml_extractor import EmlExtractor
from crossspec.extract.pdf_extractor import PdfExtractor
from crossspec.extract.pptx_extractor import PptxExtractor
from crossspec.extract.xlsx_extractor import XlsxExtractor

__all__ = [
    "ExtractedClaim",
    "Extractor",
    "EmlExtractor",
    "PdfExtractor",
    "PptxExtractor",
    "XlsxExtractor",
]
