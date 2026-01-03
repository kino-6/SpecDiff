$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$repoRoot = (Resolve-Path (Join-Path $projectRoot "..\..")).Path
Set-Location $repoRoot
$configPath = Join-Path $projectRoot "crossspec.pj.yml"
$outputDir = Join-Path $projectRoot "outputs"

if (-not (Get-Command crossspec -ErrorAction SilentlyContinue)) {
  Write-Error "crossspec is not installed. Please install it and retry."
  exit 1
}

try {
  Invoke-RestMethod -Uri "http://localhost:11434/v1/models" -TimeoutSec 2 | Out-Null
} catch {
  Write-Warning "Ollama does not appear to be running at http://localhost:11434."
  Write-Warning "Start Ollama or set tagging.enabled: false in $configPath."
}

New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

Write-Host "[1/3] Extracting spec claims..."
& crossspec extract --config $configPath

Write-Host "[2/3] Extracting code claims..."
& crossspec code-extract --repo (Join-Path $projectRoot "src") --unit function --out (Join-Path $outputDir "code_claims.jsonl")

Write-Host "[3/3] Generating report..."
& python (Join-Path $projectRoot "scripts" "make_report.py")

Write-Host "Done. Report available at $(Join-Path $outputDir "report.md")"
