# SpecDiff
仕様と実装を横断したトレーサビリティ検証

## Project-level evaluation demo

See [projects/sample_pj/README.md](projects/sample_pj/README.md) for a dedicated workspace
that evaluates CrossSpec on a mini-project without mixing artifacts into the core repo.

## Server evaluation (sample project)

Use the runnable evaluation script to generate sample claims, start the CrossSpec server,
exercise the OpenWebUI and REST APIs, and print a short summary:

```bash
bash scripts/eval_server_sample_pj.sh
```

Optional PowerShell variant (best-effort on Windows):

```powershell
.\scripts\eval_server_sample_pj.ps1
```
