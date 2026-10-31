# SOURCE OF TRUTH: Tender Integrity MVP (48h hackathon) — v2

This file wins over chat messages, prompts and individual plans. If anything conflicts with it, flag the conflict; do not pick silently.
Only the Lead (P3) edits this file, via PR. Everyone else proposes changes in `docs/CONTRACT_CHANGES.md`.

**Team:** Arnav (P1), Anirudh (P2), Hardhik (P3, Lead), Harsh (P4). Personal plans: `PLAN_Arnav_P1_rule_checker.md`, `PLAN_Anirudh_P2_network_checker.md`, `PLAN_Hardhik_P3_rag_decision_lead.md`, `PLAN_Harsh_P4_website_server.md`.

**v2 changes:** added the RAG decision layer; reassigned roles (P2 now generates data, P3 owns the decision layer, P1 owns tender texts, guideline passages, demo script and slides).

## 1. Goal and demo story

One tender goes in; one risk card and one recommendation come out:
1. **Rules:** Z3 proves the *formalized* tender clauses contradict, or that exactly one vendor can qualify.
2. **Network:** the vendor graph flags a ring (shared directors/addresses, bid rotation, cover bids), and the vendor Z3 said "uniquely qualifies" sits inside that ring.
3. **Decision:** a RAG layer retrieves relevant procurement guideline passages and writes a cited recommendation: **clear**, **review** or **escalate**, for a human to approve.

**Wording rule:** outputs are "risk indicators", never "corrupt", "guilty" or "proves illegality". Say "proves the formalized rules conflict". Recommendations are for human review, not automatic decisions.

## 2. Scope

| In (MVP) | Out (future work) |
|---|---|
| 3 demo tenders with clause text, 300 synthetic tenders with bids | Live portal scraping, OCR |
| LLM clause-to-IR (cached for demo) | General legal NLP, Dafny |
| 3 Z3 checks | Threshold-splitting, timeline traps |
| Synthetic graph with planted rings | Real labels |
| Baseline screens + one GraphSAGE | Other GNN architectures, GNNExplainer |
| RAG over 10–20 guideline passages, cited recommendation | Vector database, large legal corpus, legal advice |
| One-page web app | Auth, report export |

## 3. Team and ownership

| ID | Major role | Minor roles | Owns (only edit these) |
|---|---|---|---|
| P1 (Arnav) | Rule checker | Demo tender texts, guideline passages, demo script and slides | `rules/`, `data/tenders/`, `kb/passages/`, `docs/DEMO_SCRIPT.md`, `slides/`, `tests/rules/` |
| P2 (Anirudh) | Network checker | Synthetic data generator, evaluation script, graph display data | `synth/`, `graph/`, `scripts/evaluate.py`, `tests/graph/`, `tests/synth/` |
| P3 (Hardhik) | Lead: RAG decision layer (incl. fusion) | Repo setup, contracts, Makefile, pipeline, status board, submission | `contracts/`, `fusion/`, `decision/`, `scripts/` (except `evaluate.py`), `Makefile`, `docs/` (except `DEMO_SCRIPT.md`), this file, `tests/fusion/`, `tests/decision/` |
| P4 (Harsh) | Website and server | Mocks, API tests, fallback screenshots | `api/`, `ui/`, `mocks/`, `tests/api/` |

Shared (read-only for non-owners): `contracts/`, `data/`, `kb/`.

## 4. Architecture

```
data/tenders/*.json ─► rules/ (LLM→IR→Z3) ─► artifacts/rules/T-xxx.json ──────────┐
synth/ → data/*.csv ─► graph/ (screens + GraphSAGE) ─► artifacts/graph/graph_output.json ─┤
                                                                                     ├─► fusion/ ─► decision/ (RAG over kb/passages) ─► artifacts/fused/T-xxx.json ─► api/ ─► ui/
```

**Decoupling rule:** each step writes files into `artifacts/`; the API only reads files. No module imports another module's code.
`MOCK=1` makes the API read `mocks/` instead of `artifacts/`.

## 5. Stack and conventions

- Python 3.14, `z3-solver`, `pydantic`, `torch` + `torch_geometric` (CPU), `networkx`, `scikit-learn`, `pandas`, `numpy`, `sentence-transformers`, `jsonschema`, `pytest`, FastAPI + `uvicorn`.
- LLM: Anthropic API via env `ANTHROPIC_API_KEY`. The demo must run offline from cached IR and cached decisions.
- Embeddings: a small local sentence-transformers model (suggested all-MiniLM-L6-v2; confirm it downloads by H6 and cache it).
- UI: Vite + React + TypeScript + Cytoscape.js (P4 may change this before H4; log it in section 13).
- Pin versions in `requirements.txt` only after confirming they install.
- Seed everywhere: `SEED=42`.
- IDs: vendors `V-001`..`V-200`, tenders `T-001`..`T-300`, people `P-001`.., addresses `A-001`.., contacts `CT-001`.., buyers `B-001`.., clauses `CL1`..`CLn` (per tender), atoms `CL2.1`, findings `F-1`.., rings `R-1`.., passages `KB-001`...

## 6. Repo layout

```
tender-mvp/
├── SOURCE_OF_TRUTH.md
├── Makefile
├── requirements.txt
├── contracts/ (schemas/*.json, examples/*.json, README.md)
├── mocks/                 # copies of contracts/examples for T-001..T-003
├── data/ (vendors.csv, directors.csv, vendor_directors.csv, tenders.csv, bids.csv, labels.json, tenders/T-00x.json, tenders/ir_T-00x.json)
├── kb/passages/           # KB-xxx.md guideline passages (P1)
├── synth/ (generate.py, verify.py)                     # P2
├── rules/ (ir.py, compile_llm.py, to_z3.py, checks.py, run.py)   # P1
├── graph/ (build.py, screens.py, gnn.py, explain.py, run.py)     # P2
├── fusion/ (fuse.py, run.py)                            # P3
├── decision/ (retrieve.py, write.py, validate.py, run.py)        # P3
├── api/ (main.py, loaders.py)                           # P4
├── ui/                                                  # P4
├── artifacts/ (rules/, graph/, fusion/, fused/, decisions/)  # generated; gitignored except cached IR and cached decisions; fusion/ = intermediate fusion→decision hand-off (D13)
├── scripts/ (validate_contracts.py, evaluate.py, demo.sh)
├── slides/                                              # P1
├── docs/ (CONTRACT_CHANGES.md, DEMO_SCRIPT.md, STATUS.md)
└── tests/
```

## 7. Data files

Produced by P2 (except `data/tenders/`, written by P1). Consumed by all.

- `vendors.csv`: vendor_id, name, turnover_cr, years_experience, registration_class (one of `MSE`, `Class-A`, `Class-B`, `Class-C`), address_id, contact_id
- `directors.csv`: person_id, name
- `vendor_directors.csv`: vendor_id, person_id
- `tenders.csv`: tender_id, buyer_id, title, estimated_value_cr, bid_days, open_date
- `bids.csv`: tender_id, vendor_id, bid_amount_cr, bid_ratio (bid/estimate), rank, won (0/1), submitted_at
- `labels.json`: `{"rings":[{"ring_id","vendor_ids","type"}], "vendor_labels":{"V-xxx":0|1}, "planted_type":{"V-xxx":"shell_ring|rotation|cover|none"}}`. **Labels are for evaluation only; models must not read labels or `planted_type` as features.**
- `tenders/T-00x.json` (P1): `{"tender_id","title","clauses":[{"clause_id":"CL1","text":"..."}]}` for the 3 demo tenders only.

### Planted scenarios (fixed; generator, rules and tests must match)

| Tender | Planted issue | Expected risk / decision |
|---|---|---|
| T-001 | Contradiction: CL2 requires turnover ≥ ₹50 cr; CL5 allows only bidders with turnover ≤ ₹10 cr. Unsat core = {CL2, CL5}. | medium / review |
| T-002 | Tailored eligibility: exactly one of 200 vendors, **V-047**, qualifies. V-047 is in ring R-1. | high / escalate |
| T-003 | Clean control: consistent criteria, several qualifiers, no findings. | low / clear |

Graph plants: **R-1** = V-045, V-046, V-047 sharing director P-010 and address A-007 (shell ring). **R-2** = V-100..V-103 rotate wins across 12 tenders with the same buyer (rotation). **R-3** = cover bidders whose bids sit 1 to 3% above the winner on a subset of tenders. Everything else is random noise.

**Handoff:** P1 sends P2 the exact T-002 criteria by H3, so P2 can generate vendor attributes where only V-047 qualifies.

### Guideline passages (`kb/passages/KB-xxx.md`, P1)

```
---
passage_id: KB-001
source_title: <official document title>
source_url: <link>
section: <section as printed in the document>
retrieved: <date>
topics: [eligibility, turnover]
---
<short excerpt or faithful summary of text actually read>
```
Real public documents only. Short excerpts. Never invent section numbers. Placeholder passages must contain `PLACEHOLDER` in `source_title` and must never appear in the demo.

## 8. Contracts (JSON; schemas in `contracts/schemas/`, examples in `contracts/examples/`)

### 8.1 IR atom
```json
{"id":"CL2.1","clause_id":"CL2","field":"turnover_cr","op":">=","value":50,"source_text":"..."}
```
- `field` ∈ `turnover_cr | years_experience | registration_class | bid_days | emd_pct`
- `op` ∈ `>= | <= | == | in`; `value` is number, string or list of strings (for `in`).
- Vendor-level fields (for qualification): `turnover_cr`, `years_experience`, `registration_class`. Tender-level: `bid_days`, `emd_pct`.

### 8.2 `artifacts/rules/T-xxx.json` (P1)
```json
{
  "tender_id":"T-001",
  "formalization_status":"unconfirmed",
  "atoms":[{"id":"CL2.1","clause_id":"CL2","field":"turnover_cr","op":">=","value":50,"source_text":"..."}],
  "findings":[{
    "finding_id":"F-1","type":"contradiction","severity":"high",
    "clause_ids":["CL2","CL5"],"source_texts":["...","..."],
    "proof":{"method":"z3_unsat_core","detail":"unsat core: CL2.1, CL5.1"},
    "explanation":"Clauses CL2 and CL5 cannot both hold."
  }],
  "qualifying_vendors":[],
  "vendors_evaluated":200
}
```
- `type` ∈ `contradiction | tailored_eligibility | no_qualifier`; `severity` ∈ `high | medium | low`.
- `tailored_eligibility`: exactly 1 vendor qualifies (severity high). `no_qualifier`: satisfiable but 0 vendors qualify.
- `qualifying_vendors` is empty when the rule set is unsatisfiable.

### 8.3 `artifacts/graph/graph_output.json` (P2)
```json
{
  "vendor_scores":{"V-047":0.93},
  "rings":[{"ring_id":"R-1","vendor_ids":["V-045","V-046","V-047"],"link_types":["shared_director","shared_address"],"score":0.91}],
  "paths":[{"from":"V-047","to":"V-045","nodes":["V-047","P-010","V-045"],"edge_types":["directed_by","directed_by"]}],
  "graph":{"nodes":[{"id":"V-047","type":"vendor","label":"...","flagged":true}],"edges":[{"source":"V-047","target":"P-010","type":"directed_by"}]},
  "metrics":{"baseline":{"pr_auc":0.0,"precision_at_10":0.0},"gnn":{"pr_auc":0.0,"precision_at_10":0.0},"gnn_status":"trained|skipped","note":"synthetic data"}
}
```
`graph` is a display subgraph (flagged rings, their connectors, one-hop neighbors), not the full graph.

### 8.4 `artifacts/fused/T-xxx.json` (P3)
```json
{
  "tender_id":"T-002","title":"...","risk_level":"high",
  "rule_finding_ids":["F-1"],"graph_flag_ring_ids":["R-1"],
  "linked_vendors":[{"vendor_id":"V-047","reason":"unique_qualifier_in_flagged_ring","ring_id":"R-1","path":["V-047","P-010","V-045"]}],
  "summary":"...",
  "decision":"escalate",
  "reasoning":"...",
  "citations":[{"ref":"KB-004","kind":"guideline"},{"ref":"F-1","kind":"finding"},{"ref":"R-1","kind":"ring"}],
  "recommended_actions":["..."],
  "decision_source":"llm|template|cache",
  "disclaimer":"Risk indicators only; not a finding of wrongdoing. Recommendation requires human review."
}
```

**Fusion rule (deterministic; changed by D10):**
- `high`: a `tailored_eligibility` finding exists, `qualifying_vendors` has exactly 1 vendor, and that vendor is in a flagged ring (ring `score >= 0.5`).
- `medium`: otherwise, if any rule finding has severity `high`, or any **bidder** of the tender (from `data/bids.csv`) is in a flagged ring. Qualifiers that did not bid no longer count.
- `low`: otherwise.
- `graph_flag_ring_ids` = flagged rings containing the unique qualifier or any bidder. `linked_vendors`: the unique qualifier first (`unique_qualifier_in_flagged_ring`), then bidders sorted by id (`bidder_in_flagged_ring`); `ring_id` = the highest-scoring flagged ring containing the vendor; `path` = nodes of the first graph path whose `from` is the vendor, else `[vendor_id]`.

**Decision rule (deterministic):** `low → clear`, `medium → review`, `high → escalate`. The LLM never changes `risk_level` or `decision`.

**RAG rules:**
- Retrieval: per finding, query = finding type + explanation + clause texts; top 4 passages by cosine similarity (local embeddings, numpy).
- Retrieval also runs one query per linked ring (ring link types + "collusive bidding ring") (D12). Passages below a minimum similarity (configurable) are not support; `PLACEHOLDER` passages are never retrieved outside tests.
- Decision modes (`DECISION_MODE`): `template`, `llm`, `cache` (only if `input_hash` matches), `auto` (cache hit → cache; else `ANTHROPIC_API_KEY` present → llm; else fail loudly). No silent fallback (D11). `citations` are derived from the refs found in the validated text, not taken from the LLM.
- The LLM receives only the findings, ring info and retrieved passages, and writes `reasoning` and `recommended_actions`.
- Every citation must resolve to a retrieved passage, a finding ID or a ring ID. Invalid citations → max 2 retries, then fail loudly.
- If no passage supports a finding, the reasoning says so instead of inventing support.
- Outputs cached in `artifacts/decisions/`; the demo uses the cache.

## 9. API (P4; reads `artifacts/` or `mocks/`)

| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"status":"ok","mode":"mock|live"}` |
| GET | `/api/tenders` | `[{tender_id,title,buyer_id,estimated_value_cr,risk_level,decision}]` |
| GET | `/api/tenders/{id}/analysis` | `{fused, rules, clauses, passages}` (fused 8.4 incl. decision, rules 8.2, clause texts, cited passage texts and source metadata) |
| GET | `/api/tenders/{id}/graph` | `graph` from 8.3 plus the highlighted `path` for the linked vendor |
| POST | `/api/tenders/{id}/atoms/{atom_id}/confirm` | updated `formalization_status` (in-memory is fine) |

Errors: JSON `{"error":"...","code":"..."}` with correct HTTP status. The UI shows loading, empty and error states.

## 10. Makefile targets (P3)

`setup`, `synth`, `verify-synth`, `rules`, `graph`, `fuse`, `decide`, `pipeline` (= synth → verify-synth → rules → graph → fuse → decide), `validate-contracts`, `evaluate`, `api`, `ui`, `demo`, `test`.
`make pipeline` must work from a clean clone, offline, using cached IR and cached decisions. Any failing step stops the pipeline.

## 11. Timeline (H = hours from start)

| Hour | Milestone | Owner(s) |
|---|---|---|
| H0–H2 | Bootstrap: repo, contracts (incl. decision fields), mocks, fixtures. PyG check. **Contracts frozen at H2.** | P3 (all review), P2 PyG check |
| H3 | Demo tender texts done; T-002 criteria sent to P2 | P1 |
| H6 | Full synthetic data in `data/`; embedding model downloads confirmed | P2, P3 |
| H12 | Real `rules/T-001.json` and baseline `graph_output.json` exist; API serves them | P1, P2, P4 |
| H16 | App fully working on mocks | P4 |
| H20 | 10–20 real guideline passages in `kb/passages/` | P1 |
| H24 | `make pipeline` end to end incl. decisions; T-002 escalate, V-047 in R-1 | P3 (+all) |
| H36 | **Feature freeze.** Only fixes. | all |
| H40 | Full demo rehearsal from a clean clone | all |
| H44 | Fallback screenshots/recording; slides final | P4, P1 |
| H48 | Submit | P3 |

## 12. Definition of Done (acceptance tests)

1. `make pipeline` exits 0 from a clean clone, offline.
2. T-001: contradiction finding with clause_ids exactly `["CL2","CL5"]`; risk `medium`, decision `review`.
3. T-002: `tailored_eligibility` with `qualifying_vendors == ["V-047"]`; risk `high`, decision `escalate`, `linked_vendors[0].vendor_id == "V-047"` in R-1.
4. T-003: zero findings; risk `low`, decision `clear`.
5. Graph: baseline detects all vendors in R-1 and R-2; baseline and GNN metrics (PR-AUC, precision@10) on a ring-group holdout, labeled "synthetic data" (or GNN clearly marked skipped).
6. Decisions: 100% of citations resolve; no PLACEHOLDER passage cited; each reasoning claim checked by a human against its cited source.
7. UI: tender list with risk and decision badges; detail page with risk card, highlighted clauses, confirm ticks, graph with highlighted path, decision panel with citations and disclaimer. Works with `MOCK=1` and live.
8. `make validate-contracts` and `make test` pass.

## 13. Decisions log (append-only; Lead edits)

| # | Decision | Alternative | Why |
|---|---|---|---|
| D1 | Z3Py directly from IR | Dafny/Boogie like FormalJudge | Fewer moving parts, direct unsat cores |
| D2 | GraphSAGE on vendor-vendor projection | Heterogeneous HGT | Faster in 48h; HGT is future work |
| D3 | Cached IR and cached decisions for demo | Live LLM at demo | Demo must not depend on network/API |
| D4 | Path display instead of GNNExplainer | GNNExplainer | Clearer on stage, less time |
| D5 | File-based artifacts between modules | Direct imports / DB | Decoupled parallel work |
| D6 | Vite + React + TS + Cytoscape | Next.js / Streamlit | P4 may revise before H4 |
| D7 | Local embeddings + numpy cosine for RAG | Vector database (Chroma/FAISS) | 10–20 passages need no database |
| D8 | Risk level and decision are deterministic; LLM only explains | LLM decides | Keeps decisions auditable and repeatable |
| D9 | v2 role split (P2 data, P3 decision layer, P1 texts/passages/slides) | v1 split | P3 was overloaded; RAG layer added |
| D10 | Fusion rule change (Lead-approved): `high` = tailored_eligibility with exactly 1 qualifier who is in a flagged ring (score ≥ 0.5); `medium` = any high-severity finding or any **bidder** in a flagged ring; qualifiers that did not bid no longer count | v2 rule: qualifier or bidder in a flagged ring → medium | Qualifier-in-ring made clean control T-003 medium whenever random qualifiers sat in rings; bidders are the actual participants. Request to P2: regenerate data so T-003 bidders are not ring members |
| D11 | `DECISION_MODE` is explicit (`template`/`llm`/`cache`/`auto`); Makefile default is `template` for now. **Announced fallback (SoT 15):** no `ANTHROPIC_API_KEY` exists yet, so decisions are `decision_source: template` until a key is available and the cache is generated | Silent fallback to template when no key / cache miss | Never silent; `auto` fails with a message telling the user to set `DECISION_MODE=template`. Template mode does not write `artifacts/decisions/` |
| D12 | RAG also queries per linked ring (link types + "collusive bidding ring") in addition to per finding; min-score threshold per retriever (embedding 0.30, keyword 0.04), configurable | Findings-only queries | Ring risk indicators need guideline support too; below-threshold passages are not support |
| D13 | New intermediate folder `artifacts/fusion/T-xxx.json` (fusion → decision hand-off; carries `_inputs` findings and rings; not a public contract, not consumed by api/) | decision/ reading rules and graph directly | Keeps decoupling rule (D5) and lets fusion be tested alone |
| D14 | Placeholder KB passages live only in `tests/decision/fixtures/kb/` (`PLACEHOLDER` in `source_title`); retrieval excludes them unless `--allow-placeholder` (tests only) | Placeholders in `kb/passages/` | `kb/` is P1-owned and placeholders must never reach the demo |
| D15 | `venv/` (py3.9, committed) untracked; root `.gitignore` added; project venv is `.venv` (Python 3.14); embedding model cached in `.cache/models` | Keep committed venv | 1,599 tracked files, wrong Python version |

## 14. Rules of collaboration

- Branch per person: `p1/rules`, `p2/graph`, `p3/decision`, `p4/app`. Small commits to your own branch. PRs to `main` reviewed by one other person. Never force-push, `reset --hard`, or delete branches without explicit approval from the Lead.
- Check `git status`, `git log` and the remote before any git action.
- Edit only the folders you own. Contract change = entry in `docs/CONTRACT_CHANGES.md` + message to Lead; Lead updates schemas and examples in one commit and announces it.
- **Done means run.** Every PR description includes: what changed, the exact commands run with their real output/exit status, and what was not verified.
- No new dependency outside section 5 without a decisions-log entry.
- Bounded effort: no unlimited retries, no silent fallbacks. If a check fails, stop and report it.

## 15. Risks and fallbacks

| Risk | Fallback (announce and log; never silent) |
|---|---|
| PyG install fails (checked at H2) | Ship networkx baseline only; mark GNN skipped |
| LLM output flaky or no API key | Cached IR and cached decisions; hand-written IR if needed |
| Embedding model won't download | Keyword-overlap retrieval; log in decisions table |
| RAG writer not ready by H30 | Template reasoning listing findings and retrieved passages; `decision_source: template` |
| Baseline beats GNN | Report honestly; do not tune to win |
| UI blocked on engines | UI runs on `MOCK=1` |
| Time overrun | Cut order: confirm ticks → graph polish → GNN → LLM-written reasoning → T-003 control (last resort) |

## 16. Status board (`docs/STATUS.md`; each owner updates their row at every checkpoint)

| Person | Last checkpoint | Evidence (command + result) | Blockers |
|---|---|---|---|
| P1 (Arnav) | | | |
| P2 (Anirudh) | | | |
| P3 (Hardhik) | | | |
| P4 (Harsh) | | | |
