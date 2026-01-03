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
