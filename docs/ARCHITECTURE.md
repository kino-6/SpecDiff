# CrossSpec Architecture (Scaffolding)

## Purpose
CrossSpec extracts immutable claim records from common business artifacts (PDF, XLSX, PPTX, EML) into JSONL. Each claim preserves the original text, carries provenance, and is deterministically hashed to support auditability and downstream analysis.

## Non-goals (MVP)
- No vector DB indexing (placeholder only).
- No UI; CLI-first only.
- No stable, cross-run claim ID guarantees (IDs reset each run).
- No advanced content cleaning (e.g., quoted reply stripping in emails).

## Data flow
1. **Inputs**: file globs from `crossspec.yml`.
2. **Extractors**: format-specific extractor modules produce `ExtractedClaim` records.
3. **Claim assembly**: Claim IDs are generated, hashing and normalization are applied.
4. **JSONL output**: one claim per line written to configured output.
5. **Optional tagging**: if enabled, LLM tagging adds a `facets` object constrained by taxonomy.

## Key modules and responsibilities
- `src/crossspec/cli.py`: CLI entrypoint (`extract`, `index`, `analyze`).
- `src/crossspec/config.py`: YAML config parsing into typed models.
- `src/crossspec/claims.py`: claim schema, ID generator, claim construction.
- `src/crossspec/normalize.py`: `normalize_light` implementation.
- `src/crossspec/hashing.py`: deterministic SHA-256 hashing.
- `src/crossspec/io/jsonl.py`: JSONL output writer.
- `src/crossspec/extract/*_extractor.py`: format-specific extraction logic.
- `src/crossspec/tagging/*`: taxonomy loading and optional LLM tagging.

## Claim schema overview
**Required**
- `schema_version`, `claim_id`, `authority`, `status`
- `text_raw`, `hash`, `source`, `provenance`
- `created_at`, `extracted_by`

**Optional**
- `text_norm`, `facets`, `relations`

## Adding a new extractor
1. Create a new extractor class in `src/crossspec/extract/` implementing `Extractor`.
2. Return `ExtractedClaim` records with `text_raw`, `authority`, `source_*`, and `provenance`.
3. Register the new extractor type in `cli._build_extractor`.
4. Update config schema if new extractor settings are required.

## Known limitations / failure modes
- Missing optional dependencies (e.g., PyMuPDF, openpyxl, python-pptx) will raise runtime errors when those formats are used.
- Claim IDs are only stable within a single run.
- PDF extraction quality depends on source structure (text blocks may be noisy).

## Smoke test commands
```bash
make smoke
```

This runs extraction using `samples/crossspec.yml`, prints the first 3 JSONL lines, and validates that each line can be parsed as a `Claim`.
