from __future__ import annotations

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from rules.ir import Atom, load_atoms

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="unknown_field",  # type: ignore
            op=">=",
            value=50,
            source_text="Some text",
        )


def test_unknown_op_rejected():
    with pytest.raises(ValidationError):
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="turnover_cr",
            op="!=",  # type: ignore
            value=50,
            source_text="Some text",
        )


def test_extra_key_rejected():
    with pytest.raises(ValidationError):
        Atom.model_validate({
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "turnover_cr",
            "op": ">=",
            "value": 50,
            "source_text": "Some text",
            "extra_field": "disallowed",
        })


def test_registration_class_unknown_class_rejected():
    with pytest.raises(ValidationError):
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="registration_class",
            op="==",
            value="Class-Z",
            source_text="Some text",
        )
    with pytest.raises(ValidationError):
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="registration_class",
            op="in",
            value=["Class-A", "Class-Z"],
            source_text="Some text",
        )


def test_numeric_field_with_in_rejected():
    with pytest.raises(ValidationError):
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="turnover_cr",
            op="in",
            value=[50, 100],  # type: ignore
            source_text="Some text",
        )


def test_id_not_matching_clause_id_rejected():
    with pytest.raises(ValidationError):
        Atom(
            id="CL3.1",
            clause_id="CL2",
            field="turnover_cr",
            op=">=",
            value=50,
            source_text="Some text",
        )


def test_cached_ir_source_text_equals_clause_text():
    for tid in ["T-001", "T-002", "T-003"]:
        tender_path = REPO_ROOT / "data" / "tenders" / f"{tid}.json"
        ir_path = REPO_ROOT / "data" / "tenders" / f"ir_{tid}.json"
        assert ir_path.exists(), f"{ir_path} does not exist"

        tender_data = json.loads(tender_path.read_text(encoding="utf-8"))
        clause_map = {c["clause_id"]: c["text"] for c in tender_data["clauses"]}

        atoms = load_atoms(ir_path)
        assert len(atoms) > 0
        for a in atoms:
            assert a.clause_id in clause_map, f"Clause {a.clause_id} not found in {tid}"
            assert a.source_text == clause_map[a.clause_id], f"Mismatch in {tid} atom {a.id}"

def test_widened_numeric_fields_valid():
    fields_and_vals = [
        ("turnover_lakh", 51.96),
        ("turnover_pct", 30.0),
        ("turnover_period_years", 3),
        ("max_loss_years", 2),
        ("solvency_lakh", 41.57),
        ("solvency_pct", 40.0),
        ("estimated_cost_lakh", 103.92),
        ("emd_amount_lakh", 2.0784),
    ]
    for field, val in fields_and_vals:
        atom = Atom(
            id="CL1.1",
            clause_id="CL1",
            field=field,  # type: ignore
            op=">=" if "pct" in field or "lakh" in field else "==",
            value=val,
            source_text="Sample text",
        )
        assert atom.field == field
        assert atom.value == val


def test_similar_works_valid():
    atom = Atom(
        id="CL6.1",
        clause_id="CL6",
        field="similar_works",
        op=">=",
        value={
            "years": 7,
            "alternatives": [
                {"count": 3, "pct": 40.0, "amount_lakh": 41.57},
                {"count": 2, "pct": 60.0, "amount_lakh": 62.35},
                {"count": 1, "pct": 80.0, "amount_lakh": 83.14},
            ],
        },
        source_text="Sample work experience text",
    )
    assert atom.field == "similar_works"
    assert len(atom.value["alternatives"]) == 3


def test_similar_works_invalid():
    with pytest.raises(ValidationError):
        # missing alternatives
        Atom(
            id="CL6.1",
            clause_id="CL6",
            field="similar_works",
            op=">=",
            value={"years": 7},
            source_text="Sample text",
        )
    with pytest.raises(ValidationError):
        # empty alternatives
        Atom(
            id="CL6.1",
            clause_id="CL6",
            field="similar_works",
            op=">=",
            value={"alternatives": []},
            source_text="Sample text",
        )
    with pytest.raises(ValidationError):
        # invalid op
        Atom(
            id="CL6.1",
            clause_id="CL6",
            field="similar_works",
            op="<=",  # type: ignore
            value={"alternatives": [{"count": 1, "pct": 50.0}]},
            source_text="Sample text",
        )
    with pytest.raises(ValidationError):
        # alternative without pct or amount_lakh
        Atom(
            id="CL6.1",
            clause_id="CL6",
            field="similar_works",
            op=">=",
            value={"alternatives": [{"count": 1}]},
            source_text="Sample text",
        )
