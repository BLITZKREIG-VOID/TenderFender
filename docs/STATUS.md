# Status board (SoT 16)

Each owner updates their own row at every checkpoint. Evidence = command + real result.

| Person | Last checkpoint | Evidence (command + result) | Blockers |
|---|---|---|---|
| P1 (Arnav) | PR #8 merged: `rules.run` and 18 real guideline passages in `kb/passages/` | Real rules on main: T-001 contradiction CL2/CL5; T-002 only V-047 (CL2–CL4); T-003 no findings | none |
| P2 (Anirudh) | PR #7 merged: `graph.run` (paths from V-047) | Real graph on main: R-1 {V-045, V-046, V-047} 0.7; R-2 {V-100..V-103} 1.0; R-3 (cover, 28 vendors) 1.0; R-4 (cover, 8 vendors incl. V-124) 0.6 is not a planted ring | R-4 puts T-003 bidder V-124 in a flagged ring (T-003 medium/review); `synth.verify` has no CLI; fix in progress on a separate branch |
| P3 (Hardhik, Lead) | P3 Phase 1 complete; RAG writer switched to OpenRouter (SoT 13 D19) on branch `p3/openrouter` (local commits; Boss pushes/merges). Decision cache `artifacts/decisions/` not generated yet | Fresh clean-clone proof (Phase 1, before the OpenRouter cutover) in `/tmp/tf-clean`: `make setup` exit 0 (Python 3.14.8, CPU torch 2.15.0+cpu, MiniLM model cached in `.cache/models`); `HF_HUB_OFFLINE=1 make pipeline-mock DECISION_MODE=template RETRIEVER=embedding` exit 0 (T-001 medium/review, T-002 high/escalate with linked_vendors[0]=V-047 in R-1, T-003 low/clear); `make validate-contracts` exit 0 (25/25 valid; 4 expected artifacts not produced yet); `make acceptance-mock` exit 2 (T-001 PASS, T-002 clause IDs FAIL on mock CL1-CL3 vs CL2-CL4, T-003 PASS, citations PASS, demo hygiene MISSING kb/passages). After the OpenRouter cutover: `make test` exit 0 (238 passed), `make validate-contracts` exit 0 (25/25 valid), `HF_HUB_OFFLINE=1 make pipeline-mock DECISION_MODE=template RETRIEVER=embedding` exit 0, `make acceptance-mock` exit 2 (only the known CL1-CL3 FAIL and kb/passages MISSING). | LLM writer: OpenRouter, `OPENROUTER_API_KEY` (shell only, never committed), default model `nvidia/nemotron-3-ultra-550b-a55b:free` (`DECISION_MODEL` overrides). Tested against a fake transport only; no real call made yet. To generate the cache: `export OPENROUTER_API_KEY=...` in your shell, then `make decide DECISION_MODE=llm` once, and commit `artifacts/decisions/`. The free model is rate-limited (429: wait and rerun) and the provider may log prompts (synthetic data only). Until then decisions use `DECISION_MODE=template` (announced fallback, SoT 13 D11). No real KB passages yet (`kb/passages` not created): reasoning carries template note and states "No guideline passage ... retrieved" for every finding/ring. |
| P3 integration round | `fix/p3-integration` (worktree /tmp/tf-p3), awaiting merge | `make test` exit 0 with torch_geometric 2.8.1; `HF_HUB_OFFLINE=1 make decide DECISION_MODE=template` on real rules+graph: guideline citations T-001 7→2, T-002 8→4, T-003 4→1; `make acceptance`: T-002 path check PASS (connector A-007), T-003 bidder/risk checks FAIL (V-124 in R-4) | T-003 acceptance until P2's graph fix merges; relevance marks in `docs/RETRIEVAL_TUNING.md` are agent pre-judgments, human confirmation pending |
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

- `DECISION_MODE ?= template` in the Makefile until `artifacts/decisions/` has been generated with `OPENROUTER_API_KEY` set in the shell and `make decide DECISION_MODE=llm`. `auto` fails loudly (it never falls back). Template mode does not write `artifacts/decisions/`. Changing `DECISION_MODEL` makes the cache stale.
- Retrieval uses the embedding model by default (`RETRIEVER=embedding`); `RETRIEVER=keyword` is an explicit opt-in, never chosen automatically.
- `make pipeline-mock` uses fixture bids in `contracts/examples/data/` (not `data/bids.csv`) because current real T-003 bidders are all ring members (see request 1).

## Requests to owners (Lead Plan Part 1B)

1. **P2 (Anirudh) — data & graph:** PARTLY RESOLVED (PR #7 merged: `graph.run`, paths from V-047). Open, fix in progress on a separate branch: ring R-4 (cover, 8 vendors, 0.6) is not planted and puts T-003 bidder V-124 in a flagged ring, so T-003 is medium/review instead of low/clear; `synth.verify` still has no `__main__` CLI, so `make verify-synth` / `make pipeline` stop there.
2. **P1 (Arnav) — rules & passages:** RESOLVED (PR #8 merged: `rules.run`, 18 real guideline passages, no PLACEHOLDER).
3. **P4 (Harsh) — mock sync & API passages:** IN PROGRESS (integration round, owned by P4AppFixes). Not verified here.
4. **P3 (Hardhik) — integration round:** DONE on `fix/p3-integration`, awaiting merge: `torch_geometric==2.8.1` pinned; `scripts/acceptance.py` T-002 path check follows SoT 12 #3; retrieval cutoffs tuned on the real KB (embedding 0.50, keyword 0.055, top-k 4; `docs/RETRIEVAL_TUNING.md`).

## Mocks validation

`make validate-contracts` result: all of `mocks/rules`, `mocks/graph`, `mocks/fused` validate (exit 0). No mock failures.
