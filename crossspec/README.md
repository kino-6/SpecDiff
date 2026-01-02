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
uv pip install -e ./crossspec\[demo\]

crossspec demo --config samples/crossspec.yml
```

This generates small sample artifacts (including PDF), runs extraction, and prints a human-friendly summary.

Note: Counts by `facets.feature` are multi-label; totals can exceed total claims.

### Example output

```
Generated 3 EML files in /path/to/SpecDiff/samples/input/mail
Generated /path/to/SpecDiff/samples/input/sample.xlsx
Generated /path/to/SpecDiff/samples/input/sample.pptx
Generated /path/to/SpecDiff/samples/input/sample.pdf
Wrote 18 claims to samples/output/claims.jsonl
Counts by source.type:
  pdf: 2
  xlsx: 10
  pptx: 3
  eml: 3
Counts by authority:
  normative: 2
  approved_interpretation: 9
  informative: 7
Counts by facets.feature:
  brake: 6
  can: 4
  error_handling: 7
  timing: 5
  diagnostics: 5
  safety: 7
  calibration: 5
  nvm: 4
  init: 2
  comms: 1
Note: Counts by facets.feature is multi-label; totals can exceed total claims.
Sample claims:
TYPE: eml | CLM-BRAKE-000005 | samples/input/mail/mail1.eml | {...}
  From: demo1@example.com To: team@example.com Date: Fri, 01 Mar 2024 10:00:00 +0000 ...
TYPE: pdf | CLM-BRAKE-000001 | samples/input/sample.pdf | {...}
  Brake controller shall support safe deceleration under normal conditions ...
TYPE: pptx | CLM-BRAKE-000004 | samples/input/sample.pptx | {...}
  [Slide 1] Brake Feature Overview ...
TYPE: xlsx | CLM-BRAKE-000002 | samples/input/sample.xlsx | {...}
  Question: How is brake torque limited? Answer: Via controller thresholds. ...
```

## Search

```bash
crossspec search --config samples/crossspec.yml --feature brake --top 5
crossspec search --config samples/crossspec.yml --query "timing" --type pdf
```

## Code Assertions (code-extract)

CrossSpec can extract code assertions (internally stored as Claims) from C/C++ and Python source files.

```bash
crossspec code-extract --repo . --out outputs/code_claims.jsonl
crossspec search --claims outputs/code_claims.jsonl --query "init" --type code
```

Notes:
- The UI uses the term “Assertion”, but the underlying records remain Claim objects.
- C/C++ extraction is heuristic and best-effort (lightweight brace matching, no full AST).

## Optional setup script

```bash
./scripts/setup_demo.sh
```

## One-command demo script

```bash
./scripts/run_demo.sh
```

## Tagging with Ollama (optional)

CrossSpec can use a local Ollama server via the OpenAI-compatible API.

```bash
ollama pull gpt-oss:20b
```

Update your `crossspec.yml`:

```yaml
tagging:
  enabled: true
  provider: "llm"
  taxonomy_path: "taxonomy/features.yaml"
  llm:
    model: "gpt-oss:20b"
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"
    temperature: 0.0
  output:
    facets_key: "facets"
```

Tagging is optional and can be disabled by setting `tagging.enabled` to `false`.

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
