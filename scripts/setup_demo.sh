#!/usr/bin/env bash
set -euo pipefail

uv venv
source .venv/bin/activate
uv pip install -e ./crossspec[demo]
cp crossspec/crossspec.yml.example crossspec.yml

echo "Setup complete."
echo "Run: crossspec extract --config crossspec.yml"
