# Status board (SoT 16)

Each owner updates their own row at every checkpoint. Evidence = command + real result.

| Person | Last checkpoint | Evidence (command + result) | Blockers |
|---|---|---|---|
| P1 (Arnav) | | | |
| P2 (Anirudh) | | | |
| P3 (Hardhik, Lead) | P3 Phase 1 complete; branch `p3/decision` awaiting Hardhik's review, push and PR | Fresh clean-clone proof in `/tmp/tf-clean`: `make setup` exit 0 (Python 3.14.8, CPU torch 2.15.0+cpu, MiniLM model cached in `.cache/models`); `HF_HUB_OFFLINE=1 make pipeline-mock DECISION_MODE=template RETRIEVER=embedding` exit 0 (T-001 medium/review, T-002 high/escalate with linked_vendors[0]=V-047 in R-1, T-003 low/clear); `make validate-contracts` exit 0 (25/25 valid; 4 expected artifacts not produced yet); `make test` exit 0 (167 passed); `make acceptance-mock` exit 2 (T-001 PASS, T-002 clause IDs FAIL on mock CL1-CL3 vs CL2-CL4, T-003 PASS, citations PASS, demo hygiene MISSING kb/passages); `make validate-artifacts` exit 2 / python exit 1 (3/3 valid; 4 expected artifacts missing); demo-guard smoke runs all pass (exit 0 on mock output, exit 1 on temp PLACEHOLDER passage, exit 1 on missing template note). Clean clone removed. | No `ANTHROPIC_API_KEY`: decisions use `DECISION_MODE=template` (announced fallback, SoT 13 D11). No real KB passages yet (`kb/passages` not created): reasoning carries template note and states "No guideline passage ... retrieved" for every finding/ring. LLM writer path tested against fake transport. |
| P4 (Harsh) | | | |

### Before you pull (all teammates)
The `venv/` untrack removes tracked `venv/` from teammate checkouts on pull. Run `make setup` afterwards to set up local `.venv` (Python 3.14 + CPU torch + cached embedding model).

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

## Requests to owners (Lead Plan Part 1B)

1. **P2 (Anirudh) — data & graph:** Regenerate data so R-2/R-3 are off T-001..T-003, R-2 sits on one buyer, no T-003 bidder is in any ring, and V-047 bids on T-002. Add a `synth.verify` CLI that exits non-zero on failure. Add `graph.run` with paths starting from V-047.
2. **P1 (Arnav) — rules & passages:** `rules.run --all`; 10–20 real guideline passages in `kb/passages/KB-xxx.md` (no `PLACEHOLDER` in `source_title`).
3. **P4 (Harsh) — mock sync & API passages:** API passage metadata from `kb/passages`; sync `mocks/rules/T-002` to CL2–CL4 (`contracts/examples` already uses CL2–CL4).
## Mocks validation

`make validate-contracts` result: all of `mocks/rules`, `mocks/graph`, `mocks/fused` validate (exit 0). No mock failures.
