# Samples (Demo)

This folder contains a reproducible demo that generates small artifacts and runs CrossSpec.

## Generate samples

```bash
python samples/generate_samples.py
```

## Demo extraction

```bash
crossspec demo --config samples/crossspec.yml
```

The demo prints:
- counts per `source.type`
- counts per `authority`
- counts per `facets.feature` (if tagging enabled; otherwise prints "no facets")
- 3 sample claims with provenance and a text preview

### Ollama tagging

`samples/crossspec.yml` enables tagging with a local Ollama server by default. If Ollama is not running or the response is invalid, CrossSpec falls back to empty facets. To disable tagging entirely, set `tagging.enabled: false`.
