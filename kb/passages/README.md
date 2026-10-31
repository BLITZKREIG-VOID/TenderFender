# Guideline passages (`kb/passages/`, owner P1)

Short excerpts from real public procurement documents, retrieved by `decision/` (RAG) and cited in recommendations as `KB-xxx`.

## Format (SOURCE_OF_TRUTH.md section 7; schema `contracts/schemas/kb_passage.json`)

```
---
passage_id: KB-001
source_title: <official document title>
source_url: <link>
section: <section as printed in the document>
retrieved: <YYYY-MM-DD>
topics: [eligibility, turnover]
---
<short excerpt or faithful summary of text actually read>
```

Rules:
- Real public documents only; each passage was read in the source document linked in `source_url`.
- Excerpts are verbatim and short; `…` marks omitted text. Section numbers are copied as printed in the document.
- `passage_id` must equal the file name. No placeholder passages in this folder (test placeholders live in `tests/decision/fixtures/kb/`, see SoT D14).
- Excerpts are guidance for human review, not legal advice. EU Directive passages are comparative (EU law), not Indian law.

## Sources (all retrieved 2026-10-31)

| Source | URL |
|---|---|
| Directive 2014/24/EU of the European Parliament and of the Council of 26 February 2014 on public procurement and repealing Directive 2004/18/EC | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014L0024 |
| The Competition Act, 2002 (12 of 2003) | https://www.cci.gov.in/images/legalframeworkact/en/the-competition-act-20021652103427.pdf |
| General Financial Rules 2017 (Updated up to 31.01.2026), Ministry of Finance, Department of Expenditure | https://doe.gov.in/files/circulars_document/GFRupdatedupto31012026.pdf |
| Manual for Procurement of Works (Second Edition, 2025), Ministry of Finance, Department of Expenditure | https://doe.gov.in/files/manuals_documents/Works_Manual_SE_2025.pdf |

## Passages

| ID | Source | Section | Topics |
|---|---|---|---|
| KB-001 | Directive 2014/24/EU (EU public procurement directive) | Article 18(1) | tailored_eligibility, competition, equal_treatment |
| KB-002 | Directive 2014/24/EU (EU public procurement directive) | Article 58(1) | eligibility, selection_criteria, proportionality |
| KB-003 | Directive 2014/24/EU (EU public procurement directive) | Article 58(3) | eligibility, turnover, proportionality |
| KB-004 | Directive 2014/24/EU (EU public procurement directive) | Article 24 | conflict_of_interest |
| KB-005 | Directive 2014/24/EU (EU public procurement directive) | Article 57(4)(d) | collusion, exclusion, bid_rigging |
| KB-006 | Directive 2014/24/EU (EU public procurement directive) | Article 27(1) | bid_period, time_limits |
| KB-007 | Directive 2014/24/EU (EU public procurement directive) | Article 67(1) | bid_evaluation, award |
| KB-008 | The Competition Act, 2002 | Section 3(3)(d) and Explanation | collusion, bid_rigging, competition_law |
| KB-009 | General Financial Rules 2017 | Rule 144 | competition, fairness, bid_evaluation |
| KB-010 | General Financial Rules 2017 | Rule 161 (vi) | bid_period, time_limits |
| KB-011 | General Financial Rules 2017 | Rule 170 (i) | emd, bid_security |
| KB-012 | General Financial Rules 2017 | Rule 173 (i) | eligibility, contradiction, clarity, experience, turnover |
| KB-013 | General Financial Rules 2017 | Rule 175 (1) | collusion, bid_rigging, conflict_of_interest, code_of_integrity |
| KB-014 | Manual for Procurement of Works | Para 3.9.1 (4) | eligibility, tailored_eligibility, qualification_criteria, competition |
| KB-015 | Manual for Procurement of Works | Para 3.9.1 (4) (a) | eligibility, turnover, qualification_criteria |
| KB-016 | Manual for Procurement of Works | Para 3.9.1 (4) (b) | eligibility, experience, qualification_criteria |
| KB-017 | Manual for Procurement of Works | Para 6.2.4 (1) | conflict_of_interest, bid_evaluation |
| KB-018 | Manual for Procurement of Works | Section 6.6, risk table, row g) Anti-competitive practices, items i) and k) | collusion, cover_bidding, bid_rotation, bid_rigging |

## Verification

Every quoted segment was checked programmatically to appear verbatim (whitespace-normalised) in the text extracted from the source document on 2026-10-31. KB-010 and KB-012 join one sentence across a PDF footnote/page break; each part was checked separately.
