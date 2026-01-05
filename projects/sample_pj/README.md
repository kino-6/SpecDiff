# Project-level demo workspace

This folder is a dedicated, isolated workspace for evaluating CrossSpec on a realistic
mini-project without mixing artifacts into the core repo.

## How to run

```bash
./projects/sample_pj/scripts/run_eval.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File projects/sample_pj/scripts/run_eval.ps1
```

The eval scripts generate small sample PDFs/XLSX/PPTX files under `projects/sample_pj/docs/`
before extraction. This avoids committing binary files to the repo.

## Serve (OpenWebUI tool API)

```bash
bash scripts/run_sample_pj.sh
```

```bash
crossspec serve --config projects/sample_pj/crossspec.pj.yml --api openwebui --port 8080
```

Example tool call:

```bash
curl -X POST http://localhost:8080/tools/trace -H 'Content-Type: application/json' \\
  -d '{"spec_claim_id":"CLM-BRAKE-000001","top":3}'
```

## Golden queries (expected to return results)

```bash
crossspec search --claims projects/sample_pj/outputs/claims.jsonl --feature brake
crossspec search --claims projects/sample_pj/outputs/claims.jsonl --feature can
crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query timing
crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query calibration
crossspec search --claims projects/sample_pj/outputs/claims.jsonl --query "retry"
crossspec search --claims projects/sample_pj/outputs/code_claims.jsonl --query "init"
```

## Tagging (Ollama)

Tagging is enabled by default and expects a local Ollama server:

- Base URL: `http://localhost:11434/v1`
- Model: `gpt-oss:20b`

If Ollama is not running, either start it or set `tagging.enabled: false` in
`projects/sample_pj/crossspec.pj.yml`.

## Outputs

Generated artifacts are written to:

- `projects/sample_pj/outputs/claims.jsonl`
- `projects/sample_pj/outputs/code_claims.jsonl`
- `projects/sample_pj/outputs/report.md`
