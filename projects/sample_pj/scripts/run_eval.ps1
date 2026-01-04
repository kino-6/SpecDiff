$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $projectRoot "..\..")
$configPath = Join-Path $projectRoot "crossspec.pj.yml"
$outputDir = Join-Path $projectRoot "outputs"

Set-Location $repoRoot

if (-not (Get-Command crossspec -ErrorAction SilentlyContinue)) {
  Write-Host "crossspec is not installed. Please install it and retry."
  exit 1
}

if (Get-Command curl -ErrorAction SilentlyContinue) {
  try {
    $null = curl -s --max-time 2 "http://localhost:11434/v1/models"
  } catch {
    Write-Host "Ollama does not appear to be running at http://localhost:11434."
    Write-Host "Start Ollama or set tagging.enabled: false in $configPath."
  }
} else {
  Write-Host "curl not found; skipping Ollama availability check."
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Write-Host "[0/3] Generating sample documents..."
& python (Join-Path $projectRoot "scripts" "generate_docs.py")

Write-Host "[1/3] Extracting spec claims..."
& crossspec extract --config $configPath

Write-Host "[2/3] Extracting code claims..."
& crossspec code-extract --repo (Join-Path $projectRoot "src") --unit function --out (Join-Path $outputDir "code_claims.jsonl")

Write-Host "[3/3] Generating report..."
& python (Join-Path $projectRoot "scripts" "make_report.py")

Write-Host "Done. Report available at $(Join-Path $outputDir "report.md")"
