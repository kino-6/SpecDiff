#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

uv venv
source .venv/bin/activate
uv pip install -e ./crossspec[demo]
cp crossspec/crossspec.yml.example crossspec.yml

crossspec demo --config samples/crossspec.yml

mkdir -p outputs
rm -f outputs/code_claims.jsonl
crossspec extract --config samples/crossspec.yml --save
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --unit function --language python --top 5
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --save

# Option examples (runnable)
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --dry-run
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --include "**/*.py" --exclude "**/.git/**"
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --unit class
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --unit file
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --max-bytes 500000
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --encoding utf-8
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --language c
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --language cpp
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --language python
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --authority informative --status active
crossspec code-extract --repo "$repo_root" --config samples/crossspec.yml --out outputs/code_claims.jsonl
crossspec code-extract --repo "$repo_root" --out outputs/code_claims.jsonl --top 3
