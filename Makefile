.PHONY: smoke demo eval-server

smoke:
	PYTHONPATH=crossspec/src python -m crossspec.cli extract --config crossspec/samples/crossspec.yml
	PYTHONPATH=crossspec/src python -c "import json; from pathlib import Path; from crossspec.claims import Claim; path=Path('crossspec/samples/output/claims.jsonl'); lines=path.read_text(encoding='utf-8').splitlines(); [ (print(line), Claim(**json.loads(line))) for line in lines[:3] ]"

demo:
	PYTHONPATH=crossspec/src python -m crossspec.cli demo --config samples/crossspec.yml

eval-server:
	bash scripts/eval_server_sample_pj.sh
