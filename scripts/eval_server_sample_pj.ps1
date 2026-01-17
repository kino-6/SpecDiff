#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Error "Missing required command: $Name"
    exit 1
  }
}

Require-Command crossspec
Require-Command curl

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
  $pythonCmd = "python3"
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
  $pythonCmd = "uv run python"
} else {
  Write-Error "Missing required command: python (or python3) or uv"
  exit 1
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "Running sample project pipeline..."
bash scripts/run_sample_pj.sh

$specClaims = "projects/sample_pj/outputs/claims.jsonl"
$codeClaims = "projects/sample_pj/outputs/code_claims.jsonl"
if (-not (Test-Path $specClaims)) { Write-Error "Missing output: $specClaims"; exit 1 }
if (-not (Test-Path $codeClaims)) { Write-Error "Missing output: $codeClaims"; exit 1 }

function Test-PortAvailable {
  param([int]$Port)
  $listener = $null
  try {
    $listener = New-Object System.Net.Sockets.TcpListener([Net.IPAddress]::Parse("127.0.0.1"), $Port)
    $listener.Start()
    return $true
  } catch {
    return $false
  } finally {
    if ($listener) { $listener.Stop() }
  }
}

function Select-Port {
  param([int[]]$Ports)
  foreach ($port in $Ports) {
    if (Test-PortAvailable $port) { return $port }
  }
  return $null
}

$openWebUiPort = Select-Port -Ports @(8080, 8081, 8090)
if (-not $openWebUiPort) { Write-Error "No open port for OpenWebUI server."; exit 1 }

$openWebUiLog = New-TemporaryFile
$openWebUiProcess = Start-Process crossspec -ArgumentList "serve --config projects/sample_pj/crossspec.pj.yml --api openwebui --host 127.0.0.1 --port $openWebUiPort" -RedirectStandardOutput $openWebUiLog -RedirectStandardError $openWebUiLog -PassThru

try {
  $healthUrl = "http://127.0.0.1:$openWebUiPort/healthz"
  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    try {
      Invoke-RestMethod -Uri $healthUrl -Method Get | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Milliseconds 200
    }
  }
  if (-not $ready) {
    Write-Error "Server failed to start. Log: $openWebUiLog"
    Get-Content $openWebUiLog -Tail 50 | Write-Error
    exit 1
  }

  $traceResponse = Invoke-RestMethod -Uri "http://127.0.0.1:$openWebUiPort/tools/trace" -Method Post -ContentType "application/json" -Body '{"spec_claim_id":"CLM-BRAKE-000001","top":3}'
  $planResponse = Invoke-RestMethod -Uri "http://127.0.0.1:$openWebUiPort/tools/plan" -Method Post -ContentType "application/json" -Body '{"requirement_text":"The brake controller shall initialize comms within 100ms and report diagnostics on timing drift."}'
  if (-not $traceResponse.data.coverage.status) { Write-Error "Missing coverage status"; exit 1 }
  if (-not $traceResponse.data.impl -or $traceResponse.data.impl.Count -lt 1) { Write-Error "Expected impl matches"; exit 1 }
  if (-not $planResponse.data.req_breakdown -or $planResponse.data.req_breakdown.Count -lt 1) { Write-Error "Empty req_breakdown"; exit 1 }

  $restPort = Select-Port -Ports @(8081, 8090, 8091)
  if (-not $restPort -or $restPort -eq $openWebUiPort) { Write-Error "No open port for REST server."; exit 1 }

  $restLog = New-TemporaryFile
  $restProcess = Start-Process crossspec -ArgumentList "serve --config projects/sample_pj/crossspec.pj.yml --api rest --host 127.0.0.1 --port $restPort" -RedirectStandardOutput $restLog -RedirectStandardError $restLog -PassThru
  try {
    $restHealth = "http://127.0.0.1:$restPort/healthz"
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
      try {
        Invoke-RestMethod -Uri $restHealth -Method Get | Out-Null
        $ready = $true
        break
      } catch {
        Start-Sleep -Milliseconds 200
      }
    }
    if (-not $ready) {
      Write-Error "REST server failed to start. Log: $restLog"
      Get-Content $restLog -Tail 50 | Write-Error
      exit 1
    }

    $restTrace = Invoke-RestMethod -Uri "http://127.0.0.1:$restPort/trace/CLM-BRAKE-000001?top=3" -Method Get
    if (-not $restTrace.coverage.status) { Write-Error "Missing coverage status"; exit 1 }
    if (-not $restTrace.impl -or $restTrace.impl.Count -lt 1) { Write-Error "Expected impl matches"; exit 1 }

    $specCount = (Get-Content $specClaims).Length
    $codeCount = (Get-Content $codeClaims).Length

    Write-Host ""
    Write-Host "=== Summary ==="
    Write-Host "Spec claims lines: $specCount"
    Write-Host "Code claims lines: $codeCount"
    Write-Host "Trace coverage status: $($traceResponse.data.coverage.status)"
    Write-Host "OpenWebUI port: $openWebUiPort"
    Write-Host "REST port: $restPort"
    Write-Host ""
    Write-Host "Evaluation completed successfully."
  } finally {
    if ($restProcess) { $restProcess.Stop() | Out-Null }
  }
} finally {
  if ($openWebUiProcess) { $openWebUiProcess.Stop() | Out-Null }
}
