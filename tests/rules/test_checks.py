from __future__ import annotations

import csv
from pathlib import Path
import pytest

from rules.checks import run_checks
from rules.ir import Atom, load_atoms

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_CSV = Path(__file__).parent / "fixtures" / "vendors_small.csv"
REAL_VENDORS_CSV = REPO_ROOT / "data" / "vendors.csv"


def load_csv_vendors(path: Path) -> list[dict]:
    with open(path, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_t001_contradiction():
    atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-001.json")
    vendors = load_csv_vendors(FIXTURE_CSV)
    res = run_checks(atoms, vendors)

    assert len(res["findings"]) == 1
    f = res["findings"][0]
    assert f["type"] == "contradiction"
    assert f["severity"] == "high"
    assert f["clause_ids"] == ["CL2", "CL5"]
    assert set(f["clause_ids"]) == {"CL2", "CL5"}
    assert f["proof"]["detail"] == "unsat core: CL2.1, CL5.1"
    assert res["qualifying_vendors"] == []
    assert res["vendors_evaluated"] == len(vendors)


def test_t002_fixture():
    atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-002.json")
    vendors = load_csv_vendors(FIXTURE_CSV)
    res = run_checks(atoms, vendors)

    assert res["qualifying_vendors"] == ["V-047"]
    assert len(res["findings"]) == 1
    f = res["findings"][0]
    assert f["type"] == "tailored_eligibility"
    assert f["clause_ids"] == ["CL2", "CL3", "CL4"]
    assert f["severity"] == "high"
    assert f["proof"]["detail"] == f"satisfiable; exactly 1 of {len(vendors)} vendors qualifies: V-047"
    assert "corrupt" not in f["explanation"].lower()
    assert "guilty" not in f["explanation"].lower()
    assert "fraud" not in f["explanation"].lower()


def test_t002_real_data():
    if not REAL_VENDORS_CSV.exists():
        pytest.skip("data/vendors.csv does not exist")
    vendors = load_csv_vendors(REAL_VENDORS_CSV)
    if len(vendors) != 200:
        pytest.skip(f"data/vendors.csv has {len(vendors)} rows, expected 200")

    atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-002.json")
    res = run_checks(atoms, vendors)
    assert res["qualifying_vendors"] == ["V-047"]
    assert len(res["findings"]) == 1
    assert res["findings"][0]["type"] == "tailored_eligibility"


def test_t003_fixture():
    atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-003.json")
    vendors = load_csv_vendors(FIXTURE_CSV)
    res = run_checks(atoms, vendors)

    assert res["findings"] == []
    assert len(res["qualifying_vendors"]) >= 2


def test_t003_real_data():
    if not REAL_VENDORS_CSV.exists():
        pytest.skip("data/vendors.csv does not exist")
    vendors = load_csv_vendors(REAL_VENDORS_CSV)
    if len(vendors) != 200:
        pytest.skip(f"data/vendors.csv has {len(vendors)} rows, expected 200")

    atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-003.json")
    res = run_checks(atoms, vendors)
    assert res["findings"] == []
    assert len(res["qualifying_vendors"]) >= 2


def test_no_qualifier():
    vendors = load_csv_vendors(FIXTURE_CSV)
    atoms = [
        Atom(
            id="CL2.1",
            clause_id="CL2",
            field="turnover_cr",
            op=">=",
            value=10000,
            source_text="Annual turnover must be at least ₹10,000 crore.",
        )
    ]
    res = run_checks(atoms, vendors)
    assert res["qualifying_vendors"] == []
    assert len(res["findings"]) == 1
    f = res["findings"][0]
    assert f["type"] == "no_qualifier"
    assert f["severity"] == "medium"
    assert f["clause_ids"] == ["CL2"]
    assert f["proof"]["detail"] == f"satisfiable; 0 of {len(vendors)} vendors qualify"


def test_tender_level_atoms_do_not_affect_qualification():
    vendors = load_csv_vendors(FIXTURE_CSV)
    base_atoms = load_atoms(REPO_ROOT / "data" / "tenders" / "ir_T-002.json")
    res1 = run_checks(base_atoms, vendors)

    modified_atoms = []
    for a in base_atoms:
        if a.field == "bid_days":
            modified_atoms.append(
                Atom(id=a.id, clause_id=a.clause_id, field=a.field, op="==", value=999, source_text=a.source_text)
            )
        elif a.field == "emd_pct":
            modified_atoms.append(
                Atom(id=a.id, clause_id=a.clause_id, field=a.field, op="==", value=99, source_text=a.source_text)
            )
        else:
            modified_atoms.append(a)

    res2 = run_checks(modified_atoms, vendors)
    assert res1["qualifying_vendors"] == res2["qualifying_vendors"]
