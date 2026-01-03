$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

& (Join-Path $repoRoot "projects" "sample_pj" "scripts" "run_eval.ps1")
