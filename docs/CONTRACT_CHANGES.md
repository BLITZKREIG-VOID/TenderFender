# Contract changes

Everyone proposes changes here; only the Lead (P3) edits `SOURCE_OF_TRUTH.md`, `contracts/schemas/` and `contracts/examples/` (one commit, then announce).

## Template

```
### CC-nn: <title>
- Date / proposer:
- Status: proposed | approved | applied
- Contract(s) affected: (SoT section, schema file)
- Change:
- Why:
- Impacted owners / required follow-up:
- Applied in: (commit)
```

## Entries

### CC-01: Fusion rule change (D10)
- Date / proposer: 2026-10-31, Lead (Hardhik); Boss-approved.
- Status: applied (SoT 8.4, decisions log D10; implemented in `fusion/fuse.py`; tests in `tests/fusion/`).
- Contract(s) affected: SoT 8.4 "Fusion rule". Output shape of `artifacts/fused/T-xxx.json` is unchanged; only `risk_level` / `linked_vendors[].reason` derivation changes.
- Change:
  - `high`: a `tailored_eligibility` finding exists, `qualifying_vendors` has exactly 1 vendor, and that vendor is in a flagged ring (ring `score >= 0.5`).
  - `medium`: otherwise, if any rule finding has severity `high`, OR any **bidder** of the tender (from `data/bids.csv`) is in a flagged ring. Qualifiers that did not bid no longer count.
  - `low`: otherwise.
  - `linked_vendors[].reason` enum is now `unique_qualifier_in_flagged_ring | bidder_in_flagged_ring` (was `qualifier/bidder` wording in the SoT prose). `fused.json` enforces it.
- Why: a qualifier-in-ring trigger made the clean control T-003 `medium` whenever any of its many qualifiers happened to be a ring member, although they never bid.
- Impacted owners: P2 must regenerate data so the T-003 bidders are not members of planted rings R-1/R-2/R-3 (currently all 10 T-003 bidders are ring members, so with real data T-003 fuses to medium/review). P4: `mocks/fused` unaffected in shape. Tests use fixtures, not `data/`.

### CC-02: Intermediate `artifacts/fusion/` folder
- Date / proposer: 2026-10-31, Lead (Hardhik).
- Status: applied (SoT section 6 layout, decisions log D13).
- Contract(s) affected: none public. New intermediate `artifacts/fusion/T-xxx.json` = all deterministic §8.4 fields (tender_id, title, risk_level, rule_finding_ids, graph_flag_ring_ids, linked_vendors, summary, decision) plus `_inputs: {findings, rings}`. Written by `fusion/`, read only by `decision/`. Not validated by a schema, must not be consumed by `api/` or `ui/`.
- Why: `decision/` must not import `fusion/` or read rules/graph itself (decoupling rule, SoT 4).
- Impacted owners: none.

### CC-03: Decision-layer fields and schema strictness
- Date / proposer: 2026-10-31, Lead (Hardhik).
- Status: applied (`contracts/schemas/`).
- Change: `fused.json` requires all §8.4 fields, `citations.kind ∈ guideline|finding|ring`, `decision_source ∈ llm|template|cache`, exact `disclaimer`. `scripts/validate_contracts.py` additionally enforces `low→clear`, `medium→review`, `high→escalate`, citation kind/prefix match, and that cited findings/rings are listed in `rule_finding_ids` / `graph_flag_ring_ids`. `rules_output.formalization_status ∈ unconfirmed|confirmed`; `graph_output.graph.nodes[].type ∈ vendor|person|address|contact|buyer|tender`; `metrics.gnn_status ∈ trained|skipped`.
- Why: contract freeze (H2) needs schemas strict enough to catch drift.
- Impacted owners: P1/P2/P4 run `make validate-contracts` on their outputs and mocks; report enum gaps here instead of editing schemas.

### CC-04: Optional graph fields `gnn_vendor_scores`, `vendor_explanations`
- Date / proposer: 2026-10-31, P2 (Anirudh) output in PR #7; accepted by Lead (Hardhik).
- Status: applied (`contracts/schemas/graph_output.json`).
- Change: `graph_output.json` may carry `gnn_vendor_scores` (`{V-xxx: 0..1}`, empty when the GNN is skipped) and `vendor_explanations` (array of `{vendor_id, risk_score, ...}` evidence records). Both optional and additive; `vendor_scores`, `rings`, `paths`, `graph`, `metrics` unchanged.
- Why: PR #7 emitted them and `make validate-contracts` rejected the real artifact (root `additionalProperties: false`).
- Impacted owners: none; fusion/decision and the API ignore them.

### CC-05: Real-tender format, `rules_output.not_checked` / `vendor_check`
- Date / proposer: 2026-11-01, Lead (Hardhik) with Phase 4 prep.
- Status: applied (`contracts/schemas/real_tender.json` new, `contracts/schemas/rules_output.json`).
- Change: new `real_tender.json` for `data/real/tenders/RT-xxx.json` (`tender_id ^RT-\d{3}$`, `title`, `source_portal`, `source_url`, `source_ref`, `retrieved`, `clauses[{clause_id, source_clause_no, text, needs_review?}]`). `rules_output.json`: `tender_id` now `^R?T-\d{3}$`; optional `not_checked: [{clause_id, text, reason}]` (clauses with zero atoms, verbatim text) and optional `vendor_check: {status: run|skipped, reason}`. Real tenders always carry both (`vendor_check.status = skipped`, `qualifying_vendors = []`, `vendors_evaluated = 0`, no `tailored_eligibility`/`no_qualifier` findings); T-001..T-003 outputs are unchanged and omit both keys. `ir_atom.json` is NOT changed. `scripts/validate_contracts.py` validates `data/real/tenders/RT-*.json`, `ir_RT-*.json`, `artifacts/rules_real/*.json` when present, and checks `not_checked`/`vendor_check` consistency.
- Why: real tender text must be kept with its source and clause numbers, clauses the rule format cannot express must stay visible instead of being dropped, and synthetic vendors must never be evaluated against real tenders.
- Impacted owners: P4 UI shows the `not_checked` badge; fusion/decision/graph do not consume `rules_real`.

### CC-06: Optional `fused.source` / `fused.network_check`; RT tender ids in `fused.json`
- Date / proposer: 2026-11-01, Phase 7 (real-tender pipeline prep).
- Status: applied (`contracts/schemas/fused.json`, `contracts/examples/fused_RT-001.json`, `scripts/validate_contracts.py`).
- Change: `fused.json` `tender_id` is now `^R?T-\d{3}$`; new optional `source` (`real | synthetic_demo`) and optional `network_check` (`{status: "not_applicable", reason}`). Real-tender fusion (`python -m fusion.run --real`) always emits both with `graph_flag_ring_ids: []`, `linked_vendors: []`; synthetic T- fusion emits neither, so `artifacts/fusion` and `artifacts/fused` for T-001..T-003 are byte-identical (consumers treat a missing `source` as `synthetic_demo`). `validate_contracts.py` additionally rejects a `network_check` next to non-empty rings/linked vendors and checks the RT file-name match; the `fused_RT-001.json` example is format-example text. No `mocks/fused/RT-*.json` is added (the mock API keeps its three demo tenders; `mocks/rules/RT-001.json` already exists).
- Why: real tenders have no bid data before award, so the network check cannot run; it must be stated explicitly instead of looking like a clean graph result.
- Impacted owners: API/UI read the new fields (`source`, `network_check`); `decision/` accepts `RT-NNN` ids.


### CC-07: Phase 4 ISRO real tenders integration
- Date / proposer: 2026-11-01, Phase 4 Worker
- Status: applied
- Contract(s) affected: real_tender.json, rules_output.json
- Change: Imported 14 ISRO tenders into data/real/tenders/RT-nnn.json, committed data/real/tools/, added attribution and neutral framing in API/UI.
- Why: Full Phase 4 implementation.

### CC-08: Widened IR schema (`ir_atom.json`) and `amount_mismatch` finding type (`rules_output.json`)
- Date / proposer: 2026-11-01, Phase 4 Worker
- Status: applied (`contracts/schemas/ir_atom.json`, `contracts/schemas/rules_output.json`)
- Change: `ir_atom.json` field enum widened to include `turnover_lakh`, `turnover_pct`, `turnover_period_years`, `max_loss_years`, `solvency_lakh`, `solvency_pct`, `estimated_cost_lakh`, `emd_amount_lakh`, and `similar_works`. `value` accepts structured object for `similar_works` (alternatives with count, pct, amount_lakh and years). `rules_output.json` finding type enum widened to include `amount_mismatch`.
- Why: Real ISRO public tenders require expressibility for turnover in Lakhs/percent, solvency in Lakhs/percent, loss years, turnover period, EMD amounts, and similar works alternatives. Mismatch between stated percentage and printed ₹ amount constitutes a medium-severity risk indicator.
- Impacted owners: P1 rules engine and checks; downstream consumers ignore new fields for synthetic demo tenders (byte-identical).

### CC-09: Site AI on Amazon Bedrock and `GET /api/llm/site`
- Date / proposer: 2026-11-02, Backend Worker (Lead / Boss approved).
- Status: applied (SoT §13 D41; `api/llm_routes.py`, `api/providers.py`, `api/users.py`, `decision/write.py`, `rules/compile_llm.py`).
- Contract(s) affected: API endpoints. New endpoint `GET /api/llm/site`; keyless requests to `/api/tenders/{id}/regenerate`, `/api/compile`, `/api/tenders/{id}/chat` now route to site AI on Bedrock.
- Change:
  - New `GET /api/llm/site` (signed-in) returns `{"available": bool, "provider": "bedrock", "model": str, "month_spend_usd": float, "cap_usd": float}`.
  - When no `X-LLM-Key` header is sent and `SITE_AI_ENABLED=true` (default), requests run on Bedrock `openai.gpt-oss-120b-1:0` via the Lambda execution role.
  - Spend guard reads month's spend from users table item `pk="GLOBAL", sk="SPEND#YYYY-MM"`; if `>= SITE_AI_MONTHLY_CAP_USD` (default $10), returns 503 `{"code": "site_ai_budget_exhausted"}`. Post-call estimated cost from Converse usage is added via atomic `ADD` in integer micro-dollars.
  - With `X-LLM-Key`, BYOK requests continue unchanged and do not count against or get blocked by the site AI cap.
- Why: Enable site AI using AWS credits without requiring users to bring an API key, bounded by a strict $10/month hard cap.
- Impacted owners: UI (P4) consumes `GET /api/llm/site` and displays site AI shared budget status when no key is saved.
