#!/usr/bin/env bash
set -euo pipefail

uv venv
source .venv/bin/activate
uv pip install -e ./crossspec[demo]
cp crossspec/crossspec.yml.example crossspec.yml

crossspec demo --config samples/crossspec.yml
