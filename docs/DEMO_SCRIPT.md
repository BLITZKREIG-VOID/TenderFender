# Demo script (3 minutes) — TenderFender

Owner: P1 (Arnav). Follows SOURCE_OF_TRUTH.md section 1. Run from the cached pipeline (`make pipeline`, offline) or the UI on `MOCK=1` as fallback.

**Wording rule (SoT 1):** say "risk indicator", "the formalized rules conflict", "recommendation for human review". Never describe a vendor or official as having done wrong.

**Before going on stage:** `make demo-guard` passes; the UI is open on the tender list; `artifacts/fused/T-00x.json` exist; note which `KB-xxx` passages each fused file actually cites (the script below must quote only those).

| Time | Screen | Say |
|---|---|---|
| 0:00–0:20 | Title slide | "Public tenders can be written so that only one firm can win, or so that the rules contradict each other. Reviewers find this by hand, late. TenderFender flags these risk indicators automatically and explains them with cited procurement guidelines, for a human to decide." |
| 0:20–0:35 | Tender list | "Three demo tenders. Each has a risk level and a recommendation: clear, review or escalate. These are recommendations for human review, not decisions." |
| 0:35–1:15 | T-002 detail: clauses CL2–CL4 highlighted | "T-002 asks for Class-A registration, at least ₹100 crore turnover and 15 years of experience. An LLM turned each clause into a formal rule, and Z3 checked all 200 vendors: exactly one, V-047, meets all three. That is a risk indicator of tailored eligibility." Point at the `unconfirmed` status and the confirm ticks: "A human confirms each formalized clause." |
| 1:15–1:40 | T-002 graph panel, highlighted path | "The network checker shows V-047 shares a director and an address with V-045 and V-046: a flagged ring, R-1. The only qualifier sits inside a flagged ring, so the risk level is high and the recommendation is escalate." |
| 1:40–2:00 | T-002 decision panel | Read the recommendation and one cited passage aloud (use a `KB-xxx` the fused file actually cites). "Every citation resolves to a real guideline passage, a rule finding or a ring. The disclaimer says this is a risk indicator, not a finding of wrongdoing." |
| 2:00–2:20 | T-001 detail | "T-001: clause CL2 requires turnover of at least ₹50 crore; CL5 allows only bidders with turnover of at most ₹10 crore. Z3 proves the formalized rules conflict: no bidder can satisfy both. Recommendation: review." |
| 2:20–2:30 | T-003 detail | "T-003 is the clean control: consistent criteria, many qualifying vendors, no findings, recommendation clear." |
| 2:30–3:00 | Limits slide | "Limits: synthetic vendor data; formalization is unconfirmed until a human ticks it; only three checks on five fields; the passages are guidance, not legal advice. Next: real tender text, more rule types, and human-reviewed labels." |

## Fallbacks (announce, never silent)
- Live pipeline fails → `MOCK=1` UI, say "this is the mock data path".
- UI fails → fallback screenshots/recording (P4).
- Decisions are `decision_source: template` while no API key exists (SoT D11): say "template reasoning" if asked; do not present it as AI-written.
