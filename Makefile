# TenderFender pipeline (SoT section 10). Override any variable on the command line, e.g.
#   make pipeline-mock DECISION_MODE=template RETRIEVER=keyword
PY            ?= .venv/bin/python
# Announced fallback (SoT 13 D11/15): no ANTHROPIC_API_KEY yet, so the default is the deterministic template writer.
# Modes: template | llm | cache | auto. `auto` fails loudly if there is neither a matching cache entry nor an API key.
DECISION_MODE ?= template
RETRIEVER     ?= embedding
RULES_DIR     ?= artifacts/rules
GRAPH_JSON    ?= artifacts/graph/graph_output.json
DATA_DIR      ?= data
KB_DIR        ?= kb/passages

# Embedding model cache lives inside the repo (gitignored) so offline runs work after `make setup`.
export SENTENCE_TRANSFORMERS_HOME ?= $(CURDIR)/.cache/models
EMBEDDING_MODEL ?= all-MiniLM-L6-v2
export EMBEDDING_MODEL

FUSION_DIR := artifacts/fusion
FUSED_DIR  := artifacts/fused
CACHE_DIR  := artifacts/decisions

.PHONY: setup synth verify-synth rules graph fuse decide pipeline pipeline-mock \
        validate-contracts evaluate api ui demo test

setup:
	@test -x $(PY) || { command -v uv >/dev/null 2>&1 && uv venv --python 3.14 .venv || python3.14 -m venv .venv; }
	@# torch from the CPU-only index first (SoT 5); requirements.txt's unpinned `torch` is then already satisfied, everything else comes from PyPI.
	@if command -v uv >/dev/null 2>&1; then \
	   uv pip install --python $(PY) torch --index-url https://download.pytorch.org/whl/cpu && \
	   uv pip install --python $(PY) -r requirements.txt; \
	 else \
	   $(PY) -m pip install torch --index-url https://download.pytorch.org/whl/cpu && \
	   $(PY) -m pip install -r requirements.txt; fi
	$(PY) -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('$(EMBEDDING_MODEL)', cache_folder='$(SENTENCE_TRANSFORMERS_HOME)'); print('embedding model cached in $(SENTENCE_TRANSFORMERS_HOME)')"

synth:
	$(PY) -m synth.generator --seed 42

verify-synth:
	@grep -q "__main__" synth/verify.py || { echo "verify-synth: synth/verify.py has no CLI entry point (P2 must add 'if __name__ == \"__main__\"'; see docs/STATUS.md). Refusing to run a no-op check." >&2; exit 2; }
	$(PY) -m synth.verify

rules:
	$(PY) -m rules.run

graph:
	$(PY) -m graph.run

fuse:
	$(PY) -m fusion.run --rules-dir $(RULES_DIR) --graph $(GRAPH_JSON) --data-dir $(DATA_DIR) --out-dir $(FUSION_DIR)

decide:
	$(PY) -m decision.run --fusion-dir $(FUSION_DIR) --kb-dir $(KB_DIR) --out-dir $(FUSED_DIR) \
	  --cache-dir $(CACHE_DIR) --mode $(DECISION_MODE) --retriever $(RETRIEVER)

# Sequential recipe lines so any failing step stops the pipeline (also under `make -j`).
pipeline:
	$(MAKE) synth
	$(MAKE) verify-synth
	$(MAKE) rules
	$(MAKE) graph
	$(MAKE) fuse
	$(MAKE) decide

# P3 path on mock inputs: mocks/rules + mocks/graph + fixture bids (contracts/examples/data) -> artifacts/fusion, artifacts/fused.
pipeline-mock:
	$(MAKE) fuse RULES_DIR=mocks/rules GRAPH_JSON=mocks/graph/graph_output.json DATA_DIR=contracts/examples/data
	$(MAKE) decide

validate-contracts:
	$(PY) scripts/validate_contracts.py

evaluate:
	$(PY) scripts/evaluate.py

api:
	$(PY) -m uvicorn api.main:app --reload

ui:
	npm --prefix ui run dev

demo:
	bash scripts/demo.sh

test:
	$(PY) -m pytest tests/
