# CrossSpec

CrossSpec is a CLI-first, API-friendly toolkit for extracting immutable claims from common business artifacts. Each claim preserves the original `text_raw`, includes provenance metadata, and is hashed deterministically for auditability. Optional LLM-based tagging can add facets constrained by a user-defined taxonomy.

## Features

- Extract claims from PDF, XLSX, PPTX, and EML sources.
- Immutable `text_raw` with provenance and SHA-256 hashing.
- Optional facet tagging constrained by taxonomy YAML.
- Modular extractor design to add new formats easily.

## Quickstart

```bash
uv venv
source .venv/bin/activate
uv pip install -e ./crossspec

cp crossspec/crossspec.yml.example crossspec.yml
crossspec extract --config crossspec.yml
```

## Demo (effect verification)

```bash
crossspec demo --config samples/crossspec.yml
```

This generates small sample artifacts, runs extraction, and prints a human-friendly summary.

## Example configuration

See [`crossspec.yml.example`](crossspec.yml.example) for a complete template.

## Claim schema (summary)

Each JSONL line represents a claim with required fields such as:

- `schema_version`, `claim_id`, `authority`, `status`
- `text_raw` (original text) and `hash`
- `source` and `provenance`
- `created_at` and `extracted_by`

Optional fields: `text_norm`, `facets`, `relations`.

## Supported formats

- **PDF**: Extracted per text block/paragraph with page and bounding box provenance.
- **XLSX**: Row-based extraction using configured columns.
- **PPTX**: One claim per slide, with optional notes.
- **EML**: Parsed email headers and plain text body.

## Development

```bash
pytest
```
