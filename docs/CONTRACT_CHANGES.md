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
