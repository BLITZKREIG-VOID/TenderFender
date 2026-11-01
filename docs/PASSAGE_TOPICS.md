# Citation topics for real eligibility findings (Phase 6, step 1)

Real tenders will produce findings that need a verifiable citation from `kb/passages/`. This list is derived from the rule fields and finding types in the code, and shows what the knowledge base already covers and where to look for what is missing. It adds no new legal text.

Derived from:
- Atom fields in `rules/ir.py`: `turnover_cr`, `years_experience`, `registration_class` (vendor fields; classes `MSE`, `Class-A`, `Class-B`, `Class-C`), `bid_days`, `emd_pct` (tender fields).
- Finding types in `rules/checks.py`: `contradiction`, `tailored_eligibility`, `no_qualifier`.

**EU law** below means Directive 2014/24/EU (KB-001 to KB-007): comparative only, not Indian law. KB-008 is the Competition Act, 2002 (India). KB-009 to KB-013 are General Financial Rules 2017 (GFR). KB-014 to KB-018 are the Manual for Procurement of Works (Second Edition, 2025) ("Works Manual").

Passage titles for the table: GFR = "General Financial Rules 2017 (Updated up to 31.01.2026), Ministry of Finance, Department of Expenditure"; Works Manual = "Manual for Procurement of Works (Second Edition, 2025), Ministry of Finance, Department of Expenditure"; Directive = "Directive 2014/24/EU of the European Parliament and of the Council of 26 February 2014 on public procurement and repealing Directive 2004/18/EC".

## 1. Topics that exist today

| Topic (finding / field) | Existing passages (KB id; source_title; section) | EU law? | Gap |
|---|---|---|---|
| Contradiction (`contradiction`: criteria that cannot all be met) | KB-012; GFR; Rule 173 (i) (bidding document "self-contained and comprehensive without any ambiguities") | no | Only an indirect basis (clarity of the document); nothing that speaks of internally inconsistent criteria specifically |
| Turnover threshold (`turnover_cr`) | KB-003; Directive; Article 58(3) (yearly turnover not above two times the estimated contract value) | **yes** | |
| | KB-015; Works Manual; Para 3.9.1 (4) (a) (minimum annual value of general construction work, multiplier of 2 or not less than 1.5) | no | |
| | KB-012; GFR; Rule 173 (i) (eligibility criteria such as experience and financial position are to be stated) | no | General only |
| Experience (`years_experience`) | KB-016; Works Manual; Para 3.9.1 (4) (b) (similar works completed in the last seven years; three works of at least 40 percent of estimated cost) | no | |
| | KB-012; GFR; Rule 173 (i) (minimum level of experience as an eligibility criterion) | no | General only |
| Registration class (`registration_class`) | none that addresses registration class directly | | **Gap**. KB-002 (Directive; Article 58(1); requirements related and proportionate to the subject matter; **EU law**) and KB-011 (GFR; Rule 170 (i); bid security except for Micro and Small Enterprises) are only adjacent (the second concerns the MSE class, not registration requirements) |
| Bid period (`bid_days`) | KB-010; GFR; Rule 161 (vi) (ordinarily three weeks minimum for bid submission) | no | |
| | KB-006; Directive; Article 27(1) (35 days minimum in open procedures) | **yes** | |
| EMD / bid security (`emd_pct`) | KB-011; GFR; Rule 170 (i) (two to five percent of estimated value; MSEs excepted) | no | |
| Tailored eligibility (`tailored_eligibility`: exactly one vendor qualifies) | KB-014; Works Manual; Para 3.9.1 (4) (qualification criteria not to leave out capable contractors; effect on competition) | no | |
| | KB-009; GFR; Rule 144 (fair, transparent procedure; promotion of competition) | no | |
| | KB-001; Directive; Article 18(1) (equal treatment; competition not artificially narrowed); KB-002; Directive; Article 58(1) | **yes** | |
| No qualifier (`no_qualifier`: criteria satisfiable but no evaluated vendor qualifies) | KB-014 and KB-002 are the nearest (criteria should be proportionate and not unduly restrictive) | KB-002 **yes** | No passage addresses this finding directly; use these only as context |

Topics in `kb/passages` not tied to an eligibility finding yet (collusion, conflict of interest, award): KB-004, KB-005, KB-007 (Directive, **EU law**); KB-008, KB-013, KB-017, KB-018 (India). They are relevant if later phases add graph findings to real tenders.

## 2. Likely widened topics (not in the rule IR yet)

`rules/ir.py` has only the five fields above. Real tenders will probably express these as well; each needs citations before a finding on it can be shown.

| Topic | Existing coverage | Gap |
|---|---|---|
| Similar-work value and count (e.g. "N works each of at least X percent of estimated cost") | KB-016 (Works Manual; Para 3.9.1 (4) (b)) | Covered for works. GFR and goods/services equivalents are not in the KB |
| Average turnover and its period (e.g. "average annual turnover over the last N years") | KB-015 (Works Manual; Para 3.9.1 (4) (a); annual value and multiplier) and KB-003 (Directive; Article 58(3); **EU law**; yearly turnover) | Nothing in the KB addresses the number of years over which turnover is averaged |

## 3. Where to look for the missing passages

These are suggested places to look. The user verifies and copies the text, then saves it as a new `kb/passages/KB-xxx.md` (format in `kb/passages/README.md`) and, if desired, saves the source text for `make check-passages` (see `kb/sources/README.md`). Nothing here is a citation.

| Topic | GFR 2017 | Works Manual 2025 | CVC guidance |
|---|---|---|---|
| Contradiction / ambiguity in eligibility criteria | Rule 173 (already cited by KB-012); other text in the same rule may add to it (section to be located by user) | Para 3.9.1 (4) (already cited by KB-014); other qualification-criteria text near it (section to be located by user) | (document and section to be located by user) |
| Registration class | (section to be located by user; look for contractor or supplier registration and enlistment) | (section to be located by user; look for registration or enlistment of contractors) | (document and section to be located by user) |
| Turnover averaging period | (section to be located by user) | Para 3.9.1 (4) (a) is already cited by KB-015; look near it for the period (section to be located by user) | (document and section to be located by user) |
| Similar-work value and count | (section to be located by user) | Para 3.9.1 (4) (b) is already cited by KB-016; look near it for variants (section to be located by user) | (document and section to be located by user) |
| Bid period, EMD | Rules 161 and 170 are already cited (KB-010, KB-011); works-specific periods and security are in the Works Manual (section to be located by user) | (section to be located by user) | (document and section to be located by user) |
| Tailored or restrictive criteria | Rule 144 (already cited by KB-009) | Para 3.9.1 (4) (already cited by KB-014) | (document and section to be located by user) |
