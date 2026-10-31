# Status board (SoT 16)

Each owner updates their own row at every checkpoint. Evidence = command + real result.

| Person | Last checkpoint | Evidence (command + result) | Blockers |
|---|---|---|---|
| P1 (Arnav) | | | |
| P2 (Anirudh) | | | |
| P3 (Hardhik, Lead) | P3 deliverables on branch `p3/decision` (pre-H12) | `make setup` exit 0 (Python 3.14.8, CPU torch 2.15.0+cpu from download.pytorch.org/whl/cpu, embedding model cached in `.cache/models`); `make validate-contracts` exit 0 (25/25 files valid incl. `mocks/`); `make test` exit 0 (166 passed; 58 new in `tests/fusion` + `tests/decision`); `make pipeline-mock DECISION_MODE=template RETRIEVER=embedding` exit 0 online and with `HF_HUB_OFFLINE=1`: T-001 medium/review, T-002 high/escalate (linked_vendors[0]=V-047 in R-1), T-003 low/clear; `make pipeline` exit 2 at `verify-synth` (no CLI in `synth/verify.py`) | No `ANTHROPIC_API_KEY`: decisions use `DECISION_MODE=template` (announced fallback, SoT 13 D11). No real KB passages yet (`kb/` empty): reasoning states "No guideline passage ... retrieved" for every finding/ring. LLM writer path only tested against a fake transport |
| P4 (Harsh) | | | |

## Checkpoints

- [x] H2 contracts frozen (schemas, examples, README, `make validate-contracts`) — P3 content ready on `p3/decision`, awaiting merge
- [ ] H12 real `rules/T-001.json` and baseline `graph_output.json` exist; API serves them
- [ ] H24 `make pipeline` end to end incl. decisions; T-002 escalate, V-047 in R-1
- [ ] H36 feature freeze
- [ ] H40 full demo rehearsal from a clean clone
- [ ] H48 submit

## Announced fallbacks (SoT 15; never silent)

- `DECISION_MODE ?= template` in the Makefile until an `ANTHROPIC_API_KEY` exists and `artifacts/decisions/` has been generated with `DECISION_MODE=llm`. `auto` fails loudly (it never falls back). Template mode does not write `artifacts/decisions/`.
- Retrieval uses the embedding model by default (`RETRIEVER=embedding`); `RETRIEVER=keyword` is an explicit opt-in, never chosen automatically.
- `make pipeline-mock` uses fixture bids in `contracts/examples/data/` (not `data/bids.csv`) because current real T-003 bidders are all ring members (see request 1).

## Requests to owners

1. **P2 (Anirudh) — data:** regenerate data so the T-003 bidders are not members of planted rings R-1/R-2/R-3. Currently all 10 T-003 bidders (V-102, V-019, V-188, V-079, V-103, V-145, V-100, V-007, V-101, V-179) are ring members (R-2 / R-3), so with real data T-003 fuses to medium/review instead of low/clear under the new fusion rule (CC-01). Also T-001 and T-002 have R-2 bidders (fine for T-001: medium; for T-002 the unique qualifier rule still gives high).
2. **P2 (Anirudh) — `synth.verify` CLI:** `synth/verify.py` has no `if __name__ == "__main__"` entry point, so `python -m synth.verify` would be a silent no-op. `make verify-synth` refuses to run until the CLI exists (exits 2 with a message). Needs: exit non-zero on any failed check, print per-check result.
3. **P1 (Arnav) / P4 (Harsh) — mock vs tender clause numbering:** `mocks/rules/T-002.json` uses clauses CL1–CL3 (atoms CL1.1, CL2.1, CL3.1) but `data/tenders/T-002.json` has the criteria in CL2 (Class-A), CL3 (turnover), CL4 (experience); CL1 is the scope clause. Real rules output must use CL2/CL3/CL4 (see `contracts/examples/rules_T-002.json`). Mock should be aligned so the UI highlights the right clauses.
4. **P4 (Harsh) — API `passages`:** `/api/tenders/{id}/analysis` currently returns only passage ids; per SoT 9 it should read `kb/passages/KB-xxx.md` front matter (title, section, url, text) for every `KB-` citation.
5. **P1 (Arnav) — `rules/`:** `make rules` runs `python -m rules.run` (no arguments) and must write `artifacts/rules/T-00x.json` valid against `contracts/schemas/rules_output.json`; `make graph` runs `python -m graph.run` and must write `artifacts/graph/graph_output.json` (P2). Both modules do not exist on `main` yet.
6. **All — passages:** real passages go in `kb/passages/KB-xxx.md` with exactly the front matter in SoT 7 (`topics: [a, b]` on one line, `retrieved: YYYY-MM-DD`). `make validate-contracts` checks them. No `PLACEHOLDER` in `kb/`.

## Mocks validation

`make validate-contracts` result: all of `mocks/rules`, `mocks/graph`, `mocks/fused` validate (exit 0). No mock failures.
