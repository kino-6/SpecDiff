from __future__ import annotations

from pathlib import Path
import textwrap

from crossspec.cli import extract_command


def _write_eml(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "From: sender@example.com",
                "To: receiver@example.com",
                "Subject: Test message",
                "Message-ID: <test@example.com>",
                "",
                "Hello from CrossSpec.",
            ]
        ),
        encoding="utf-8",
    )


def _write_config(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def _count_claims(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_repo_root_relative_to_config_dir(tmp_path: Path) -> None:
    config_dir = tmp_path / "cfg"
    repo_root = tmp_path / "repo" / "projects" / "sample_pj"
    eml_path = repo_root / "docs" / "spec" / "a.eml"
    eml_path.parent.mkdir(parents=True)
    _write_eml(eml_path)

    config_dir.mkdir()
    config_path = config_dir / "crossspec.yml"
    _write_config(
        config_path,
        f"""
        version: 1
        project:
          name: "Test"
          repo_root: "../repo/projects/sample_pj"
        outputs:
          claims_dir: "outputs"
          jsonl_filename: "claims.jsonl"
        knowledge_sources:
          - name: "Mail"
            type: eml
            authority: informative
            paths:
              - "docs/spec/**/*.eml"
        """,
    )

    extract_command(str(config_path))
    output_path = repo_root / "outputs" / "claims.jsonl"
    assert output_path.exists()
    assert _count_claims(output_path) == 1


def test_knowledge_sources_absolute_paths(tmp_path: Path) -> None:
    config_dir = tmp_path / "cfg"
    repo_root = tmp_path / "repo"
    eml_path = repo_root / "docs" / "spec" / "a.eml"
    eml_path.parent.mkdir(parents=True)
    _write_eml(eml_path)

    config_dir.mkdir()
    config_path = config_dir / "crossspec.yml"
    absolute_pattern = str(eml_path.parent / "*.eml")
    _write_config(
        config_path,
        f"""
        version: 1
        project:
          name: "Test"
          repo_root: "../repo"
        outputs:
          claims_dir: "outputs"
          jsonl_filename: "claims.jsonl"
        knowledge_sources:
          - name: "Mail"
            type: eml
            authority: informative
            paths:
              - "{absolute_pattern}"
        """,
    )

    extract_command(str(config_path))
    output_path = repo_root / "outputs" / "claims.jsonl"
    assert output_path.exists()
    assert _count_claims(output_path) == 1


def test_outputs_path_resolution_with_cwd_independence(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    repo_root = tmp_path / "repo"
    eml_path = repo_root / "docs" / "spec" / "a.eml"
    eml_path.parent.mkdir(parents=True)
    _write_eml(eml_path)

    config_dir.mkdir()
    config_path = config_dir / "crossspec.yml"
    _write_config(
        config_path,
        """
        version: 1
        project:
          name: "Test"
          repo_root: "../repo"
        outputs:
          claims_dir: "outputs"
          jsonl_filename: "claims.jsonl"
        knowledge_sources:
          - name: "Mail"
            type: eml
            authority: informative
            paths:
              - "docs/spec/**/*.eml"
        """,
    )

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    extract_command(str(config_path))
    output_path = repo_root / "outputs" / "claims.jsonl"
    assert output_path.exists()
    assert _count_claims(output_path) == 1


def test_tagging_taxonomy_path_resolution(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    repo_root = tmp_path / "repo"
    taxonomy_path = repo_root / "taxonomy" / "features.yaml"
    taxonomy_path.parent.mkdir(parents=True)
    taxonomy_path.write_text(
        textwrap.dedent(
            """
            version: 1
            facet_keys: ["feature", "artifact", "component"]
            feature: ["brake"]
            artifact: ["note"]
            component: ["system"]
            """
        ),
        encoding="utf-8",
    )

    config_dir.mkdir()
    config_path = config_dir / "crossspec.yml"
    _write_config(
        config_path,
        """
        version: 1
        project:
          name: "Test"
          repo_root: "../repo"
        outputs:
          claims_dir: "outputs"
          jsonl_filename: "claims.jsonl"
        knowledge_sources: []
        tagging:
          enabled: true
          provider: "llm"
          taxonomy_path: "taxonomy/features.yaml"
          llm:
            model: "fake"
            base_url: "http://localhost"
            api_key: "fake"
            temperature: 0.0
          output:
            facets_key: "facets"
        """,
    )

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    extract_command(str(config_path))
    output_path = repo_root / "outputs" / "claims.jsonl"
    assert output_path.exists()
    assert _count_claims(output_path) == 0
