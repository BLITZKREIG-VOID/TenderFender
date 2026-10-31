from __future__ import annotations

from typing import Any
import z3

from rules.ir import Atom, REG_CLASSES

RegClass, reg_consts = z3.EnumSort("RegClass", list(REG_CLASSES))
REG_MAP: dict[str, Any] = {name: reg_consts[i] for i, name in enumerate(REG_CLASSES)}


def make_vars() -> dict[str, z3.ExprRef]:
    return {
        "turnover_cr": z3.Real("turnover_cr"),
        "years_experience": z3.Real("years_experience"),
        "bid_days": z3.Real("bid_days"),
        "emd_pct": z3.Real("emd_pct"),
        "registration_class": z3.Const("registration_class", RegClass),
    }


def atom_expr(atom: Atom, vars: dict[str, z3.ExprRef]) -> z3.BoolRef:
    var = vars[atom.field]
    if atom.field == "registration_class":
        if atom.op == "==":
            return var == REG_MAP[atom.value]
        elif atom.op == "in":
            return z3.Or([var == REG_MAP[v] for v in atom.value])
        else:
            raise ValueError(f"Unsupported op {atom.op} for registration_class")
    else:
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
