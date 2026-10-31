# Contracts

JSON Schemas (draft 2020-12) in `schemas/`, one valid example per schema in `examples/`. Source: `SOURCE_OF_TRUTH.md` §7–§8. Contract changes go through `docs/CONTRACT_CHANGES.md`; only the Lead edits this folder.

| Schema | SoT | File it validates | Producer | Consumer |
|---|---|---|---|---|
| `ir_atom.json` | 8.1 | atoms inside rules output; `data/tenders/ir_T-00x.json` (array of atoms) | P1 `rules/` | P1 `rules/` (Z3), UI |
| `rules_output.json` | 8.2 | `artifacts/rules/T-xxx.json` | P1 `rules/` | `fusion/`, `api/` |
| `graph_output.json` | 8.3 | `artifacts/graph/graph_output.json` | P2 `graph/` | `fusion/`, `api/` |
| `fused.json` | 8.4 | `artifacts/fused/T-xxx.json` | P3 `decision/` | `api/`, `ui/` |
| `tender.json` | 7 | `data/tenders/T-00x.json` | P1 | `rules/`, `api/` |
| `kb_passage.json` | 7 | front matter of `kb/passages/KB-xxx.md` | P1 | `decision/`, `api/` |
| `labels.json` | 7 | `data/labels.json` (evaluation only) | P2 `synth/` | `scripts/evaluate.py` |

Examples: `ir_atom.json`, `rules_T-00{1,2,3}.json`, `graph_output.json`, `fused_T-00{1,2,3}.json`, `tender.json`, `kb_passage.json`, `labels.json`. The examples follow the planted scenarios (T-001 contradiction CL2+CL5, T-002 tailored eligibility V-047 in ring R-1, T-003 clean control) and the fusion rule in §8.4.

Not in the JSON Schema (enforced by `scripts/validate_contracts.py`): decision consistency (`low→clear`, `medium→review`, `high→escalate`); every ref found inline in `reasoning`/`recommended_actions` appears in `citations`; `F-`/`R-` citations must be listed in `rule_finding_ids` / `graph_flag_ring_ids`, and `citations.kind` must match the ref prefix.

Intermediate (not a public contract): `artifacts/fusion/T-xxx.json` written by `fusion/`, read only by `decision/`. Same fields as fused, minus reasoning fields, plus `_inputs`. See `docs/CONTRACT_CHANGES.md`.

Validate: `make validate-contracts` (all contracts, examples, mocks, data) or `make validate-artifacts` (checks that required pipeline artifacts exist and validate).
