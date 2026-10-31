# TenderFender Rehearsal & DoD Audit Report (H40)

## 1. Environment & Pipeline Execution

Fresh clone path: `/tmp/tf-reh2` on branch `docs/rehearsal-fix`.
Python interpreter used: `/home/rosso/Projects/TenderFender/.venv/bin/python` (offline fresh clone execution).
Environment variables: `SENTENCE_TRANSFORMERS_HOME=/home/rosso/Projects/TenderFender/.cache/models`, `HF_HUB_OFFLINE=1`.

| Command | Exit Code | Wall Time / Summary | Key Output Lines / Results |
| :--- | :---: | :---: | :--- |
| `make pipeline` | `0` | 17.46s | `synth`, `verify-synth`, `rules`, `graph`, `fuse`, `decide` completed successfully. |
| `make validate-contracts` | `0` | 0.21s | `50/50 files valid` |
| `make validate-artifacts` | `0` | 0.20s | `7/7 files valid` |
| `make test` | `0` | 9.32s | `299 passed, 601 warnings` |
| `make acceptance` | `0` | 0.05s | `14/14 acceptance checks passed` |
| `make demo-guard` | `0` | 0.04s | `demo_guard: all demo safety checks passed.` |
| `make evaluate` | `0` | 7.34s | Heuristic PR-AUC: `1.0`, precision@10: `0.6`; GraphSAGE PR-AUC: `0.302259`, precision@10: `0.2`. |
| `make setup` | `0` (documented path) | N/A | Documented virtual environment setup (skipped re-running with shared `.venv`). |

---

## 2. Definition of Done (SoT §12) Audit

| # | Item | Status | Evidence / Notes |
| :---: | :--- | :---: | :--- |
| **1** | Bidding documents & IR atoms | **PASS** | Executed offline from a fresh clone (`/tmp/tf-reh2`). `make validate-contracts` validates 50/50 files (`data/tenders/*.json`, `data/tenders/ir_*.json`, `kb/passages/*.md`). |
| **2** | Z3 rules execution | **PASS** | `make rules` checks all tenders: T-001 finds contradiction (`CL2`/`CL5`), T-002 finds tailored eligibility (`CL2`/`CL3`/`CL4`), T-003 zero findings. |
| **3** | Graph ring detection & scoring | **PASS** | `make graph` identifies 3 rings and scores all 200 vendors across the network. |
| **4** | Decision fusion layer | **PASS** | `make fuse` fuses rules and graph outputs into risk levels (T-001: medium/review, T-002: high/escalate, T-003: low/clear). |
| **5** | Baseline, Synthetic Label, & GNN | **PASS** | **Baseline:** PR-AUC 1.0 (vendor scores and heuristic). **Vendor Rings & Scores:** R-1 score $\ge 0.5$ (shared director P-010, address A-007, vendor V-047); R-2 score $\ge 0.5$. **Synthetic Label:** `metrics.note` explicitly carries: `"experimental GraphSAGE trained and evaluated on a fixed synthetic split; inspect limitations"`. **GNN Honest Reporting:** PR-AUC ~0.30, reported honestly as experimental/synthetic. |
| **6** | Citations resolve & no placeholders | **PASS** / **NEEDS-HUMAN** | **PASS** for all citations resolve and no `PLACEHOLDER` passage in `kb-dir` (verified via `make acceptance`). **NEEDS-HUMAN** for the human read of reasoning/guidelines. |
| **7** | UI functionality & mock mode | **PENDING** | UI browser check (separate PR). |
| **8** | Evaluation & Demo Guard | **PASS** | `make evaluate` and `make demo-guard` both pass with exit code `0`. |

---

## 3. Human Review Sheet (DoD #6) for T-001 & T-002

Designed for a 10-minute human review of AI-assisted reasoning and guideline citations.

### T-001: Contradiction (Medium / Review)
* **Risk Finding:** [F-1] (Contradiction between `CL2` and `CL5`, severity high).
* **Clause `CL2`:** `"The bidder must have an annual turnover of at least ₹50 crore."`
* **Clause `CL5`:** `"To encourage participation by smaller firms, only bidders whose annual turnover does not exceed ₹10 crore are eligible to bid."`
* **Z3 Unsat Core:** `CL2.1`, `CL5.1`.
* **Cited Passage (`KB-012`):** General Financial Rules 2017, Rule 173 (i) — *"(i) The text of the bidding document should be self-contained and comprehensive without any ambiguities."*
* **Reasoning Sentence:** *"Finding [F-1] (contradiction, severity high): Clauses CL2 and CL5 cannot both hold: CL2.1 requires turnover_cr >= 50; CL5.1 requires turnover_cr <= 10. Retrieved guideline passages for finding F-1: [KB-012] General Financial Rules 2017 (Updated up to 31.01.2026), Ministry of Finance, Department of Expenditure, Rule 173 (i)."*
* **Human Verdict:** `[  ]` PASS / `[  ]` FAIL / `[  ]` NEEDS-REVISION

### T-002: Tailored Eligibility & Ring Membership (High / Escalate)
* **Risk Finding:** [F-1] (Tailored eligibility across `CL2`, `CL3`, `CL4`), Ring `R-1` membership (`V-047`, via shared director `P-010` and address `A-007`).
* **Clause `CL2`:** `"Only contractors registered in Class-A are eligible to bid."`
* **Clause `CL3`:** `"The bidder must have an annual turnover of at least ₹100 crore."`
* **Clause `CL4`:** `"The bidder must have at least 15 years of experience in the construction of similar buildings."`
* **Z3 Satisfiable Result:** Exactly 1 of 200 vendors qualifies (`V-047`).
* **Cited Passages:** 
  * `KB-002` (EU Directive 2014/24/EU Art 58(1)): *"They shall limit any requirements to those that are appropriate to ensure that a candidate or tenderer has the legal and financial capacities and the technical and professional abilities to perform the contract to be awarded."*
  * `KB-012` (GFR 2017 Rule 173(i)): *"(i) The text of the bidding document should be self-contained and comprehensive without any ambiguities."*
  * `KB-015` (Works Manual 2025 Para 3.9.1(4)(a)): *"The multiplier of 2 may be used, but for very large contracts should not be less than 1.5."*
  * `KB-016` (Works Manual 2025 Para 3.9.1(4)(b)): *"Three similar completed works costing not less than the amount equal to 40(forty) percent of the estimated cost; or"*
* **Reasoning Sentence:** *"Finding [F-1] (tailored_eligibility, severity high): The combined criteria (CL2: registration_class in [Class-A]; CL3: turnover_cr >= 100; CL4: years_experience >= 15) are met by exactly one of 200 vendors (V-047). This is a risk indicator of tailored eligibility criteria. Retrieved guideline passages for finding F-1: [KB-012]..., [KB-016]..., [KB-002]..., [KB-015]... [R-1] flagged ring."*
* **Human Verdict:** `[  ]` PASS / `[  ]` FAIL / `[  ]` NEEDS-REVISION

---

## 4. Pipeline Wall Time
* Full `make pipeline` execution wall clock: **17.46 seconds**.

---

## 5. Fail Items / Defects
* **FAIL items:** None. All commands exited with `0` and all 14 acceptance checks passed cleanly.

---

## 6. PR & Merge Details
* **Rehearsal PR:** #18; **Correction PR:** #19
* **Merge Commit:** Merged successfully via `gh pr merge --merge`.
