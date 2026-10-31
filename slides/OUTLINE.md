# Slides outline — TenderFender

Owner: P1 (Arnav). Six slides. Numbers marked **[from artifacts]** must be copied from the files on the day, not typed from memory.

## 1. Problem
- Tender clauses can be written so only one firm qualifies, or so they contradict each other.
- Manual review is slow and catches this late.
- Goal: flag **risk indicators** early, with evidence, for a human to decide.

## 2. Live demo
- Tender list → T-002 (escalate) → T-001 (review) → T-003 (clear). Follow `docs/DEMO_SCRIPT.md`.

## 3. How it works
- Clauses → LLM → structured rules (IR, cached; `unconfirmed` until a human ticks them).
- Z3 checks: contradiction (unsat core), exactly-one qualifier, no qualifier.
- Vendor graph: shared directors/addresses, bid rotation, cover bids → flagged rings (baseline screens + GraphSAGE).
- Deterministic fusion → risk level → recommendation (clear / review / escalate); LLM only explains (SoT D8).
- RAG over 18 short excerpts from real public documents (EU Directive 2014/24/EU, Competition Act 2002, GFR 2017, Manual for Procurement of Works 2025); every citation must resolve.

## 4. Results (label: **synthetic data**)
- T-001: Z3 unsat core = CL2, CL5 **[from artifacts/rules/T-001.json]**.
- T-002: qualifying vendors = V-047 only, of 200 **[from artifacts/rules/T-002.json]**; V-047 in ring R-1 **[from artifacts/fused/T-002.json]**.
- T-003: zero findings **[from artifacts/rules/T-003.json]**.
- Graph metrics: baseline vs GNN PR-AUC and precision@10 on ring-group holdout **[from artifacts/graph/graph_output.json, "synthetic data"]**.

## 5. Limits
- Synthetic vendors, bids and rings; no real labels.
- Formalization can be wrong: atoms stay `unconfirmed` until a human confirms them.
- Only five fields and three checks; no threshold-splitting or timeline traps.
- Guideline passages are short excerpts for context, not legal advice; EU passages are comparative, not Indian law.
- Outputs are risk indicators and recommendations for human review, not findings of wrongdoing.

## 6. Next steps
- Real tender documents (with OCR) and more rule types.
- Human-reviewed labels to evaluate the graph models properly.
- Larger guideline corpus with reviewer feedback on citations.
