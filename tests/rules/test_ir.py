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
