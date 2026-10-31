from __future__ import annotations

from typing import Any
import z3

from rules.ir import Atom, VENDOR_FIELDS
from rules.to_z3 import make_vars, atom_expr, track, vendor_equalities


def _format_clauses(cids: list[str]) -> str:
    if len(cids) == 1:
        return f"Clause {cids[0]} cannot hold"
    elif len(cids) == 2:
        return f"Clauses {cids[0]} and {cids[1]} cannot both hold"
    else:
        return f"Clauses {', '.join(cids[:-1])} and {cids[-1]} cannot all hold"


def _format_atom_value(val: Any) -> str:
    if isinstance(val, list):
        return f"[{', '.join(val)}]"
    return str(val)


def run_checks(atoms: list[Atom], vendors: list[dict[str, Any]]) -> dict[str, Any]:
    vendors_evaluated = len(vendors)
    findings: list[dict[str, Any]] = []

    # (a) Contradiction check: track ALL atoms (vendor + tender level)
    solver = z3.Solver()
    solver.set("core.minimize", True)

    all_vars = make_vars()
    track(solver, atoms, all_vars)
    status = solver.check()

    if status == z3.unknown:
        raise RuntimeError("Z3 solver returned unknown during contradiction check")

    if status == z3.unsat:
        core_ids = {str(c) for c in solver.unsat_core()}
        core_atoms = [a for a in atoms if a.id in core_ids]

        clause_ids: list[str] = []
        source_texts: list[str] = []
        seen_clauses: set[str] = set()
        for a in core_atoms:
            if a.clause_id not in seen_clauses:
                seen_clauses.add(a.clause_id)
                clause_ids.append(a.clause_id)
                source_texts.append(a.source_text)

        atom_reqs = []
        for a in core_atoms:
            if a.op == "in":
                atom_reqs.append(f"{a.id} requires {a.field} in {_format_atom_value(a.value)}")
            else:
                atom_reqs.append(f"{a.id} requires {a.field} {a.op} {a.value}")

        clause_header = _format_clauses(clause_ids)
        explanation = f"{clause_header}: {'; '.join(atom_reqs)}."

        findings.append({
            "finding_id": f"F-{len(findings) + 1}",
            "type": "contradiction",
            "severity": "high",
            "clause_ids": clause_ids,
            "source_texts": source_texts,
            "proof": {
                "method": "z3_unsat_core",
                "detail": f"unsat core: {', '.join(a.id for a in core_atoms)}",
            },
            "explanation": explanation,
        })

        return {
            "findings": findings,
            "qualifying_vendors": [],
            "vendors_evaluated": vendors_evaluated,
        }

    # (b) / (c) SAT: evaluate vendor-level atoms
    vendor_atoms = [a for a in atoms if a.field in VENDOR_FIELDS]
    v_solver = z3.Solver()
    v_vars = make_vars()
    for a in vendor_atoms:
        v_solver.add(atom_expr(a, v_vars))

    qualifying_vendors: list[str] = []
    for row in vendors:
        v_solver.push()
        for eq in vendor_equalities(row, v_vars):
            v_solver.add(eq)
        v_status = v_solver.check()
        if v_status == z3.sat:
            qualifying_vendors.append(row["vendor_id"])
        elif v_status == z3.unknown:
            raise RuntimeError(f"Z3 solver returned unknown for vendor {row.get('vendor_id')}")
        v_solver.pop()

    v_clause_ids: list[str] = []
    v_source_texts: list[str] = []
    seen_v_clauses: set[str] = set()
    for a in vendor_atoms:
        if a.clause_id not in seen_v_clauses:
            seen_v_clauses.add(a.clause_id)
            v_clause_ids.append(a.clause_id)
            v_source_texts.append(a.source_text)

    if len(qualifying_vendors) == 1:
        criteria_parts = []
        for a in vendor_atoms:
            if a.op == "in":
                criteria_parts.append(f"{a.clause_id}: {a.field} in {_format_atom_value(a.value)}")
            else:
                criteria_parts.append(f"{a.clause_id}: {a.field} {a.op} {a.value}")
        criteria_str = "; ".join(criteria_parts)
        explanation = (
            f"The combined criteria ({criteria_str}) are met by exactly one of "
            f"{vendors_evaluated} vendors ({qualifying_vendors[0]}). "
            f"This is a risk indicator of tailored eligibility criteria."
        )

        findings.append({
            "finding_id": f"F-{len(findings) + 1}",
            "type": "tailored_eligibility",
            "severity": "high",
            "clause_ids": v_clause_ids,
            "source_texts": v_source_texts,
            "proof": {
                "method": "z3_per_vendor_check",
                "detail": f"satisfiable; exactly 1 of {vendors_evaluated} vendors qualifies: {qualifying_vendors[0]}",
            },
            "explanation": explanation,
        })
    elif len(qualifying_vendors) == 0:
        findings.append({
            "finding_id": f"F-{len(findings) + 1}",
            "type": "no_qualifier",
            "severity": "medium",
            "clause_ids": v_clause_ids,
            "source_texts": v_source_texts,
            "proof": {
                "method": "z3_per_vendor_check",
                "detail": f"satisfiable; 0 of {vendors_evaluated} vendors qualify",
            },
            "explanation": (
                f"The formalized criteria are satisfiable, but none of the "
                f"{vendors_evaluated} evaluated vendors meet them."
            ),
        })

    return {
        "findings": findings,
        "qualifying_vendors": qualifying_vendors,
        "vendors_evaluated": vendors_evaluated,
    }
