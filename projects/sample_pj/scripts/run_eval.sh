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

pdf_count=$(find "${PROJECT_ROOT}/docs" -name "*.pdf" | wc -l | tr -d ' ')
xlsx_count=$(find "${PROJECT_ROOT}/docs" -name "*.xlsx" | wc -l | tr -d ' ')
pptx_count=$(find "${PROJECT_ROOT}/docs" -name "*.pptx" | wc -l | tr -d ' ')
eml_count=$(find "${PROJECT_ROOT}/docs" -name "*.eml" | wc -l | tr -d ' ')
if [[ "${pdf_count}" -eq 0 || "${xlsx_count}" -eq 0 || "${pptx_count}" -eq 0 || "${eml_count}" -eq 0 ]]; then
  echo "Expected generated docs under ${PROJECT_ROOT}/docs but found:"
  echo "  pdf=${pdf_count} xlsx=${xlsx_count} pptx=${pptx_count} eml=${eml_count}"
  exit 1
fi

echo "[1/3] Extracting spec claims..."
extract_log="$(mktemp)"
crossspec extract --config "${CONFIG_PATH}" | tee "${extract_log}"

spec_claims_path="${OUTPUT_DIR}/claims.jsonl"
spec_claims_count=0
if [[ -f "${spec_claims_path}" ]]; then
  spec_claims_count=$(grep -cve '^\\s*$' "${spec_claims_path}" || true)
fi
if [[ "${spec_claims_count}" -eq 0 ]]; then
  echo "No spec claims extracted. Debug output:"
  cat "${extract_log}"
fi

echo "[2/3] Extracting code claims..."
crossspec code-extract \
  --config "${CONFIG_PATH}" \
  --repo "${PROJECT_ROOT}/src" \
  --unit function \
  --out "${OUTPUT_DIR}/code_claims.jsonl"

echo "[3/3] Generating report..."
python "${PROJECT_ROOT}/scripts/make_report.py"

echo "Done. Report available at ${OUTPUT_DIR}/report.md"
