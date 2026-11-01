from __future__ import annotations

from typing import Any
import z3

from rules.ir import Atom, REG_CLASSES

RegClass, reg_consts = z3.EnumSort("RegClass", list(REG_CLASSES))
REG_MAP: dict[str, Any] = {name: reg_consts[i] for i, name in enumerate(REG_CLASSES)}


def make_vars() -> dict[str, z3.ExprRef]:
    return {
        "turnover_cr": z3.Real("turnover_cr"),
        "turnover_lakh": z3.Real("turnover_lakh"),
        "turnover_pct": z3.Real("turnover_pct"),
        "turnover_period_years": z3.Real("turnover_period_years"),
        "max_loss_years": z3.Real("max_loss_years"),
        "solvency_lakh": z3.Real("solvency_lakh"),
        "solvency_pct": z3.Real("solvency_pct"),
        "estimated_cost_lakh": z3.Real("estimated_cost_lakh"),
        "emd_amount_lakh": z3.Real("emd_amount_lakh"),
        "years_experience": z3.Real("years_experience"),
        "bid_days": z3.Real("bid_days"),
        "emd_pct": z3.Real("emd_pct"),
        "registration_class": z3.Const("registration_class", RegClass),
        "similar_works_count": z3.Real("similar_works_count"),
        "similar_work_pct": z3.Real("similar_work_pct"),
        "similar_work_amount_lakh": z3.Real("similar_work_amount_lakh"),
        "similar_works_years": z3.Real("similar_works_years"),
    }


def atom_expr(atom: Atom, vars: dict[str, z3.ExprRef]) -> z3.BoolRef:
    if atom.field == "registration_class":
        var = vars[atom.field]
        if atom.op == "==":
            return var == REG_MAP[atom.value]
        elif atom.op == "in":
            return z3.Or([var == REG_MAP[v] for v in atom.value])
        else:
            raise ValueError(f"Unsupported op {atom.op} for registration_class")
    elif atom.field == "similar_works":
        alts = atom.value.get("alternatives", []) if isinstance(atom.value, dict) else []
        years_val = atom.value.get("years") if isinstance(atom.value, dict) else None
        alt_exprs: list[z3.BoolRef] = []
        for alt in alts:
            conds: list[z3.BoolRef] = []
            if "count" in alt and alt["count"] is not None:
                conds.append(vars["similar_works_count"] >= z3.RealVal(str(alt["count"])))
            if "pct" in alt and alt["pct"] is not None:
                conds.append(vars["similar_work_pct"] >= z3.RealVal(str(alt["pct"])))
            if "amount_lakh" in alt and alt["amount_lakh"] is not None:
                conds.append(vars["similar_work_amount_lakh"] >= z3.RealVal(str(alt["amount_lakh"])))
            if years_val is not None:
                conds.append(vars["similar_works_years"] <= z3.RealVal(str(years_val)))
            if conds:
                alt_exprs.append(z3.And(*conds) if len(conds) > 1 else conds[0])
        if not alt_exprs:
            return z3.BoolVal(True)
        return z3.Or(*alt_exprs) if len(alt_exprs) > 1 else alt_exprs[0]
    else:
        var = vars[atom.field]
        val = z3.RealVal(str(atom.value))
        if atom.op == ">=":
            return var >= val
        elif atom.op == "<=":
            return var <= val
        elif atom.op == "==":
            return var == val
        else:
            raise ValueError(f"Unsupported op {atom.op} for numeric field")

def track(solver: z3.Solver, atoms: list[Atom], vars: dict[str, z3.ExprRef]) -> None:
    for a in atoms:
        solver.assert_and_track(atom_expr(a, vars), z3.Bool(a.id))


def vendor_equalities(row: dict[str, Any], vars: dict[str, z3.ExprRef]) -> list[z3.BoolRef]:
    reg_cls = row["registration_class"]
    if reg_cls not in REG_MAP:
        raise ValueError(f"Unknown registration_class {reg_cls!r} in row: {row}")
    return [
        vars["turnover_cr"] == z3.RealVal(str(row["turnover_cr"])),
        vars["years_experience"] == z3.RealVal(str(row["years_experience"])),
        vars["registration_class"] == REG_MAP[reg_cls],
    ]
