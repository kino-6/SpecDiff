#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

require_cmd crossspec
require_cmd curl

PYTHON_CMD=()
if command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v uv >/dev/null 2>&1; then
  PYTHON_CMD=(uv run python)
else
  echo "Missing required command: python (or python3) or uv" >&2
  exit 1
fi

HAVE_JQ=false
if command -v jq >/dev/null 2>&1; then
  HAVE_JQ=true
fi

port_available() {
  local port="$1"
  "${PYTHON_CMD[@]}" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket()
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

choose_port() {
  local port
  for port in "$@"; do
    if port_available "$port"; then
      echo "$port"
      return 0
    fi
  done
  return 1
}

wait_for_healthz() {
  local port="$1"
  local log_file="$2"
  local url="http://127.0.0.1:${port}/healthz"
  local attempt
  for attempt in $(seq 1 30); do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  echo "Server failed to become ready at $url" >&2
  echo "Server log: $log_file" >&2
  tail -n 50 "$log_file" >&2 || true
  return 1
}

start_server() {
  local api="$1"
  local port="$2"
  local log_file
  log_file="$(mktemp)"
  crossspec serve \
    --config projects/sample_pj/crossspec.pj.yml \
    --api "$api" \
    --host 127.0.0.1 \
    --port "$port" \
    >"$log_file" 2>&1 &
  local pid=$!
  echo "$pid:$log_file"
}

cleanup() {
  if [[ -n "${OPENWEBUI_PID:-}" ]]; then
    kill "$OPENWEBUI_PID" 2>/dev/null || true
  fi
  if [[ -n "${REST_PID:-}" ]]; then
    kill "$REST_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "Running sample project pipeline..."
bash scripts/run_sample_pj.sh

spec_claims="projects/sample_pj/outputs/claims.jsonl"
code_claims="projects/sample_pj/outputs/code_claims.jsonl"
if [[ ! -f "$spec_claims" ]]; then
  echo "Missing output: $spec_claims" >&2
  exit 1
fi
if [[ ! -f "$code_claims" ]]; then
  echo "Missing output: $code_claims" >&2
  exit 1
fi

OPENWEBUI_PORT="$(choose_port 8080 8081 8090)"
if [[ -z "$OPENWEBUI_PORT" ]]; then
  echo "Could not find an open port for OpenWebUI server." >&2
  exit 1
fi

echo "Starting OpenWebUI server on port $OPENWEBUI_PORT..."
OPENWEBUI_INFO="$(start_server openwebui "$OPENWEBUI_PORT")"
OPENWEBUI_PID="${OPENWEBUI_INFO%%:*}"
OPENWEBUI_LOG="${OPENWEBUI_INFO#*:}"

wait_for_healthz "$OPENWEBUI_PORT" "$OPENWEBUI_LOG"

echo "Running OpenWebUI API checks..."
TRACE_RESPONSE="$(mktemp)"
PLAN_RESPONSE="$(mktemp)"

curl -sf \
  -X POST "http://127.0.0.1:${OPENWEBUI_PORT}/tools/trace" \
  -H "Content-Type: application/json" \
  -d '{"spec_claim_id":"CLM-BRAKE-000001","top":3}' \
  >"$TRACE_RESPONSE"

curl -sf \
  -X POST "http://127.0.0.1:${OPENWEBUI_PORT}/tools/plan" \
  -H "Content-Type: application/json" \
  -d '{"requirement_text":"The brake controller shall initialize comms within 100ms and report diagnostics on timing drift."}' \
  >"$PLAN_RESPONSE"

if "$HAVE_JQ"; then
  jq -e '.markdown and .data and .data.coverage.status and (.data.impl | length >= 1)' \
    "$TRACE_RESPONSE" >/dev/null
  jq -e '.data.req_breakdown | length >= 1' "$PLAN_RESPONSE" >/dev/null
  PLAN_MARKDOWN="$(jq -r '.markdown' "$PLAN_RESPONSE")"
else
  "${PYTHON_CMD[@]}" - "$TRACE_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

if "markdown" not in payload or "data" not in payload:
    raise SystemExit("Missing markdown/data in trace response")
coverage = payload["data"].get("coverage", {})
if not coverage.get("status"):
    raise SystemExit("Missing coverage status")
impl = payload["data"].get("impl", [])
if len(impl) < 1:
    raise SystemExit("Expected at least one impl match")
PY

  "${PYTHON_CMD[@]}" - "$PLAN_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

if not payload.get("data", {}).get("req_breakdown"):
    raise SystemExit("req_breakdown is empty")
PY

  PLAN_MARKDOWN="$("${PYTHON_CMD[@]}" - "$PLAN_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print(payload.get("markdown", ""))
PY
)"
fi

echo "$PLAN_MARKDOWN" | grep -E -q "CrossSpec Plan|Implementation Plan|Req breakdown" || {
  echo "Plan markdown did not contain expected headings." >&2
  exit 1
}

REST_PORT="$(choose_port 8081 8090 8091)"
if [[ -z "$REST_PORT" ]]; then
  echo "Could not find an open port for REST server." >&2
  exit 1
fi
if [[ "$REST_PORT" == "$OPENWEBUI_PORT" ]]; then
  echo "REST port selection collided with OpenWebUI port." >&2
  exit 1
fi

echo "Starting REST server on port $REST_PORT..."
REST_INFO="$(start_server rest "$REST_PORT")"
REST_PID="${REST_INFO%%:*}"
REST_LOG="${REST_INFO#*:}"

wait_for_healthz "$REST_PORT" "$REST_LOG"

echo "Running REST API check..."
REST_TRACE_RESPONSE="$(mktemp)"
curl -sf "http://127.0.0.1:${REST_PORT}/trace/CLM-BRAKE-000001?top=3" \
  >"$REST_TRACE_RESPONSE"

if "$HAVE_JQ"; then
  jq -e '.coverage.status and (.impl | length >= 1) and .spec' "$REST_TRACE_RESPONSE" >/dev/null
else
  "${PYTHON_CMD[@]}" - "$REST_TRACE_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

if not payload.get("coverage", {}).get("status"):
    raise SystemExit("Missing coverage status")
if len(payload.get("impl", [])) < 1:
    raise SystemExit("Expected at least one impl match")
if not payload.get("spec"):
    raise SystemExit("Missing spec claim")
PY
fi

if "$HAVE_JQ"; then
  COVERAGE_STATUS="$(jq -r '.data.coverage.status' "$TRACE_RESPONSE")"
  TRACE_MARKDOWN="$(jq -r '.markdown' "$TRACE_RESPONSE")"
else
  COVERAGE_STATUS="$("${PYTHON_CMD[@]}" - "$TRACE_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print(payload.get("data", {}).get("coverage", {}).get("status", ""))
PY
)"
  TRACE_MARKDOWN="$("${PYTHON_CMD[@]}" - "$TRACE_RESPONSE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    payload = json.load(handle)

print(payload.get("markdown", ""))
PY
)"
fi

spec_count=$(wc -l < "$spec_claims" | tr -d ' ')
code_count=$(wc -l < "$code_claims" | tr -d ' ')

echo ""
echo "=== Summary ==="
echo "Spec claims lines: $spec_count"
echo "Code claims lines: $code_count"
echo "Trace coverage status: ${COVERAGE_STATUS:-unknown}"
echo "OpenWebUI port: $OPENWEBUI_PORT"
echo "REST port: $REST_PORT"
echo ""
echo "Trace markdown (first 20 lines):"
echo "$TRACE_MARKDOWN" | sed -n '1,20p'

echo ""
echo "Evaluation completed successfully."
