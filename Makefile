.PHONY: smoke

smoke:
	PYTHONPATH=crossspec/src python -m crossspec.cli extract --config crossspec/samples/crossspec.yml
	PYTHONPATH=crossspec/src python -c "import json; from pathlib import Path; from crossspec.claims import Claim; path=Path('crossspec/samples/output/claims.jsonl'); lines=path.read_text(encoding='utf-8').splitlines(); [ (print(line), Claim(**json.loads(line))) for line in lines[:3] ]"
