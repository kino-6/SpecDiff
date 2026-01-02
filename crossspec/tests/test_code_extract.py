from pathlib import Path

from crossspec.claims import Authority, ClaimIdGenerator, build_claim
from crossspec.code_extract.c_cpp_extractor import extract_c_cpp_units
from crossspec.code_extract.python_extractor import extract_python_units
from crossspec.code_extract.scanner import read_text_with_fallback


def _build_claims(extracted):
    generator = ClaimIdGenerator()
    claims = []
    for item in extracted:
        claim_id = generator.next_id("GEN")
        claims.append(
            build_claim(
                claim_id=claim_id,
                authority=item.authority,
                text_raw=item.text_raw,
                source_type=item.source_type,
                source_path=item.source_path,
                provenance=item.provenance,
            )
        )
    return claims


def test_python_function_extraction(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        """

def top():
    return 1


class Sample:
    def method(self):
        return 2
""".lstrip(),
        encoding="utf-8",
    )
    text, sha1 = read_text_with_fallback(sample, "utf-8")
    extracted = extract_python_units(
        path=sample,
        source_path="sample.py",
        text=text,
        unit="function",
        authority=Authority.informative,
        sha1=sha1,
    )
    assert len(extracted) == 2
    by_symbol = {item.provenance["symbol"]: item for item in extracted}
    assert set(by_symbol.keys()) == {"top", "Sample.method"}
    for item in extracted:
        assert item.provenance["language"] == "python"
        assert item.provenance["unit"] == "function"
        assert item.provenance["line_start"] >= 1
        assert item.provenance["line_end"] >= item.provenance["line_start"]
        assert item.text_raw
    assert by_symbol["top"].provenance["line_start"] == 1
    assert by_symbol["Sample.method"].provenance["line_start"] == 6

    claims = _build_claims(extracted)
    repeat_claims = _build_claims(extracted)
    assert claims[0].hash.value
    assert claims[0].hash.value == repeat_claims[0].hash.value


def test_c_function_extraction(tmp_path: Path) -> None:
    sample = tmp_path / "sample.c"
    sample.write_text(
        """
int add(int a, int b) {
    return a + b;
}
""".lstrip(),
        encoding="utf-8",
    )
    text, sha1 = read_text_with_fallback(sample, "utf-8")
    extracted = extract_c_cpp_units(
        path=sample,
        source_path="sample.c",
        text=text,
        unit="function",
        authority=Authority.informative,
        sha1=sha1,
        language="c",
        is_header=False,
    )
    assert len(extracted) == 1
    item = extracted[0]
    assert item.provenance["symbol"] == "add"
    assert item.provenance["language"] == "c"
    assert item.provenance["line_start"] == 1
    assert item.provenance["line_end"] == 3
    assert "return a + b" in item.text_raw


def test_cpp_class_extraction(tmp_path: Path) -> None:
    sample = tmp_path / "sample.hpp"
    sample.write_text(
        """
class Widget {
public:
    void run();
};
""".lstrip(),
        encoding="utf-8",
    )
    text, sha1 = read_text_with_fallback(sample, "utf-8")
    extracted = extract_c_cpp_units(
        path=sample,
        source_path="sample.hpp",
        text=text,
        unit="class",
        authority=Authority.informative,
        sha1=sha1,
        language="cpp",
        is_header=True,
    )
    assert len(extracted) == 1
    item = extracted[0]
    assert item.provenance["symbol"] == "Widget"
    assert item.provenance["unit"] == "class"
    assert item.provenance["line_start"] == 1
    assert item.provenance["line_end"] == 4
    assert "class Widget" in item.text_raw


def test_header_defaults_to_file(tmp_path: Path) -> None:
    sample = tmp_path / "constants.h"
    sample.write_text("#define MAX_VALUE 10\n", encoding="utf-8")
    text, sha1 = read_text_with_fallback(sample, "utf-8")
    extracted = extract_c_cpp_units(
        path=sample,
        source_path="constants.h",
        text=text,
        unit="function",
        authority=Authority.informative,
        sha1=sha1,
        language="c",
        is_header=True,
    )
    assert len(extracted) == 1
    item = extracted[0]
    assert item.provenance["unit"] == "file"
    assert item.provenance["line_start"] == 1
    assert item.provenance["line_end"] == 1
    assert "MAX_VALUE" in item.text_raw
