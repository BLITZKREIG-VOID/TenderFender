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


TOLERANCE_RELATIVE = 0.005  # 0.5% relative tolerance
TOLERANCE_ABSOLUTE_LAKH = 0.01  # ₹0.01 lakh = ₹1,000 rounding tolerance


def check_amount_mismatches(atoms: list[Atom]) -> list[dict[str, Any]]:
    cost_atom = next((a for a in atoms if a.field == "estimated_cost_lakh"), None)
    if not cost_atom or not isinstance(cost_atom.value, (int, float)) or cost_atom.value <= 0:
        return []

    cost = float(cost_atom.value)
    findings: list[dict[str, Any]] = []

    by_clause: dict[str, list[Atom]] = {}
    for a in atoms:
        by_clause.setdefault(a.clause_id, []).append(a)

    for cid, catoms in by_clause.items():
        # Check solvency: solvency_pct vs solvency_lakh
        solv_pct = next((a for a in catoms if a.field == "solvency_pct"), None)
        solv_lakh = next((a for a in catoms if a.field == "solvency_lakh"), None)
        if solv_pct and solv_lakh and isinstance(solv_pct.value, (int, float)) and isinstance(solv_lakh.value, (int, float)):
            pct = float(solv_pct.value)
            printed = float(solv_lakh.value)
            expected = cost * pct / 100.0
            diff = abs(printed - expected)
            rel_diff = diff / expected if expected > 0 else 0
            if diff > TOLERANCE_ABSOLUTE_LAKH and rel_diff > TOLERANCE_RELATIVE:
                findings.append({
                    "finding_id": f"F-{len(findings) + 1}",
                    "type": "amount_mismatch",
                    "severity": "medium",
                    "clause_ids": [cid],
                    "source_texts": [solv_pct.source_text],
                    "proof": {
                        "method": "amount_mismatch_check",
                        "detail": f"solvency: stated {pct}% of estimated cost {cost} Lakhs = {expected:.2f} Lakhs, but printed amount is {printed:.2f} Lakhs (diff: {diff:.4f} Lakhs)",
                    },
                    "explanation": f"Clause {cid} states solvency of {pct}% of estimated cost ({cost} Lakhs), which computes to {expected:.2f} Lakhs, but printed figure is {printed:.2f} Lakhs.",
                })

        # Check turnover: turnover_pct vs turnover_lakh
        to_pct = next((a for a in catoms if a.field == "turnover_pct"), None)
        to_lakh = next((a for a in catoms if a.field == "turnover_lakh"), None)
        if to_pct and to_lakh and isinstance(to_pct.value, (int, float)) and isinstance(to_lakh.value, (int, float)):
            pct = float(to_pct.value)
            printed = float(to_lakh.value)
            expected = cost * pct / 100.0
            diff = abs(printed - expected)
            rel_diff = diff / expected if expected > 0 else 0
            if diff > TOLERANCE_ABSOLUTE_LAKH and rel_diff > TOLERANCE_RELATIVE:
                findings.append({
                    "finding_id": f"F-{len(findings) + 1}",
                    "type": "amount_mismatch",
                    "severity": "medium",
                    "clause_ids": [cid],
                    "source_texts": [to_pct.source_text],
                    "proof": {
                        "method": "amount_mismatch_check",
                        "detail": f"turnover: stated {pct}% of estimated cost {cost} Lakhs = {expected:.2f} Lakhs, but printed amount is {printed:.2f} Lakhs (diff: {diff:.4f} Lakhs)",
                    },
                    "explanation": f"Clause {cid} states turnover of {pct}% of estimated cost ({cost} Lakhs), which computes to {expected:.2f} Lakhs, but printed figure is {printed:.2f} Lakhs.",
                })

        # Check EMD: emd_pct vs emd_amount_lakh
        emd_p = next((a for a in catoms if a.field == "emd_pct"), None)
        emd_a = next((a for a in catoms if a.field == "emd_amount_lakh"), None)
        if emd_p and emd_a and isinstance(emd_p.value, (int, float)) and isinstance(emd_a.value, (int, float)):
            pct = float(emd_p.value)
            printed = float(emd_a.value)
            expected = cost * pct / 100.0
            diff = abs(printed - expected)
            rel_diff = diff / expected if expected > 0 else 0
            if diff > TOLERANCE_ABSOLUTE_LAKH and rel_diff > TOLERANCE_RELATIVE:
                findings.append({
                    "finding_id": f"F-{len(findings) + 1}",
                    "type": "amount_mismatch",
                    "severity": "medium",
                    "clause_ids": [cid],
                    "source_texts": [emd_p.source_text],
                    "proof": {
                        "method": "amount_mismatch_check",
                        "detail": f"EMD: stated {pct}% of estimated cost {cost} Lakhs = {expected:.2f} Lakhs, but printed amount is {printed:.2f} Lakhs (diff: {diff:.4f} Lakhs)",
                    },
                    "explanation": f"Clause {cid} states EMD of {pct}% of estimated cost ({cost} Lakhs), which computes to {expected:.2f} Lakhs, but printed figure is {printed:.2f} Lakhs.",
                })

        # Check similar_works alternatives
        sw_atom = next((a for a in catoms if a.field == "similar_works"), None)
        if sw_atom and isinstance(sw_atom.value, dict):
            alts = sw_atom.value.get("alternatives", [])
            for i, alt in enumerate(alts):
                if "pct" in alt and "amount_lakh" in alt:
                    pct = float(alt["pct"])
                    printed = float(alt["amount_lakh"])
                    expected = cost * pct / 100.0
                    diff = abs(printed - expected)
                    rel_diff = diff / expected if expected > 0 else 0
                    if diff > TOLERANCE_ABSOLUTE_LAKH and rel_diff > TOLERANCE_RELATIVE:
                        cnt_str = f"{alt.get('count', 1)} works each of " if "count" in alt else ""
                        findings.append({
                            "finding_id": f"F-{len(findings) + 1}",
                            "type": "amount_mismatch",
                            "severity": "medium",
                            "clause_ids": [cid],
                            "source_texts": [sw_atom.source_text],
                            "proof": {
                                "method": "amount_mismatch_check",
                                "detail": f"similar_works alternative {i + 1}: stated {cnt_str}{pct}% of estimated cost {cost} Lakhs = {expected:.2f} Lakhs, but printed amount is {printed:.2f} Lakhs (diff: {diff:.4f} Lakhs)",
                            },
                            "explanation": f"Clause {cid} states similar works alternative ({cnt_str}{pct}% of {cost} Lakhs), which computes to {expected:.2f} Lakhs, but printed figure is {printed:.2f} Lakhs.",
                        })

    return findings

def run_checks(atoms: list[Atom], vendors: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Contradiction check always; the per-vendor checks only when `vendors` is a list (None = no vendor data)."""
    vendors_evaluated = len(vendors) if vendors is not None else 0
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

    findings.extend(check_amount_mismatches(atoms))
    for idx, f in enumerate(findings, start=1):
        f["finding_id"] = f"F-{idx}"

    if vendors is None:
        return {"findings": findings, "qualifying_vendors": [], "vendors_evaluated": 0}

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
