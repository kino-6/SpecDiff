#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "${PROJECT_ROOT}/../.." && pwd)"
CONFIG_PATH="${PROJECT_ROOT}/crossspec.pj.yml"
OUTPUT_DIR="${PROJECT_ROOT}/outputs"

cd "${REPO_ROOT}"

if ! command -v crossspec >/dev/null 2>&1; then
  echo "crossspec is not installed. Please install it and retry."
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if ! curl -s --max-time 2 "http://localhost:11434/v1/models" >/dev/null; then
    echo "Ollama does not appear to be running at http://localhost:11434."
    echo "Start Ollama or set tagging.enabled: false in ${CONFIG_PATH}."
  fi
else
  echo "curl not found; skipping Ollama availability check."
fi

mkdir -p "${OUTPUT_DIR}"

echo "[0/3] Generating sample documents..."
python "${PROJECT_ROOT}/scripts/generate_docs.py"

echo "[1/3] Extracting spec claims..."
crossspec extract --config "${CONFIG_PATH}"

echo "[2/3] Extracting code claims..."
crossspec code-extract \
  --repo "${PROJECT_ROOT}/src" \
  --unit function \
  --out "${OUTPUT_DIR}/code_claims.jsonl"

echo "[3/3] Generating report..."
python "${PROJECT_ROOT}/scripts/make_report.py"

echo "Done. Report available at ${OUTPUT_DIR}/report.md"
