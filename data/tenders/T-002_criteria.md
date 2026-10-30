# T-002 eligibility criteria (handoff P1 → P2)

Source clauses: `data/tenders/T-002.json`. These values match `mocks/rules/T-002.json`.

A vendor **qualifies for T-002** only if it meets **all three** vendor-level criteria (boundaries inclusive):

| Clause | Field (`vendors.csv`) | Rule |
|---|---|---|
| CL2 | `registration_class` | must be `Class-A` (exactly; `MSE`, `Class-B`, `Class-C` do not qualify) |
| CL3 | `turnover_cr` | `>= 100` |
| CL4 | `years_experience` | `>= 15` |

Tender-level clauses (CL5 bid period of 7 days, CL6 EMD 2%) do not affect vendor qualification.

## Required properties of `data/vendors.csv`

1. **V-047** has `registration_class = Class-A`, `turnover_cr >= 100`, `years_experience >= 15`.
2. **Every other vendor (V-001..V-200 except V-047) fails at least one** of the three criteria.
3. Keep a clear margin from the boundaries (e.g. no other Class-A vendor at exactly 100 cr and 15 years), so small float issues cannot change the result.
4. Suggested for realism: some vendors meet 2 of 3 (e.g. Class-A with high turnover but < 15 years), so uniqueness is not caused by a single criterion. V-045 and V-046 (ring R-1 with V-047) must **not** qualify.

## Related requirements for the other demo tenders

- **T-001:** no data requirement (clauses are contradictory; nobody can qualify by construction).
- **T-003** (clean control) needs **several** qualifying vendors (at least 2; ideally 10+): `registration_class` in {Class-A, Class-B, Class-C}, `turnover_cr >= 5`, `years_experience >= 3`.
