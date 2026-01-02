"""Code extraction helpers for CrossSpec."""

from crossspec.code_extract.c_cpp_extractor import extract_c_cpp_units
from crossspec.code_extract.python_extractor import extract_python_units
from crossspec.code_extract.scanner import (
    DEFAULT_EXCLUDES,
    DEFAULT_INCLUDE_C,
    DEFAULT_INCLUDE_CPP,
    DEFAULT_INCLUDE_PYTHON,
    ScannedFile,
    default_includes,
    detect_language,
    read_text_with_fallback,
    scan_files,
)

__all__ = [
    "DEFAULT_EXCLUDES",
    "DEFAULT_INCLUDE_C",
    "DEFAULT_INCLUDE_CPP",
    "DEFAULT_INCLUDE_PYTHON",
    "ScannedFile",
    "default_includes",
    "detect_language",
    "read_text_with_fallback",
    "scan_files",
    "extract_c_cpp_units",
    "extract_python_units",
]
