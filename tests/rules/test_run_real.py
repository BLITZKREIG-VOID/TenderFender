"""rules.run on real (RT-) tenders: not_checked, skipped vendor check, no vendor data. Fixtures are format examples."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from rules.run import REPO_ROOT, load_schemas, main

SKIPPED = {"status": "skipped", "reason": "no vendor data for real tenders; synthetic vendors are never used"}
C1 = "1. FORMAT EXAMPLE, not a real tender: the bidder must have an annual turnover of at least 50 crore."
C2 = "2. FORMAT EXAMPLE, not a real tender: a clause nothing can express."
C3 = "3. FORMAT EXAMPLE, not a real tender: the bidder must have an annual turnover of at most 10 crore."


def atom(clause: str, n: int, op: str, value: int, text: str) -> dict:
    return {"id": f"{clause}.{n}", "clause_id": clause, "field": "turnover_cr", "op": op, "value": value,
            "source_text": text}


def make_real_dir(tmp_path: Path, atoms: list[dict]) -> Path:
    data = tmp_path / "real"
    tenders = data / "tenders"
    tenders.mkdir(parents=True)
    doc = {
        "tender_id": "RT-001",
        "title": "FORMAT EXAMPLE, not a real tender",
        "source_portal": "CPPP",
        "source_url": "https://example.invalid/format-example",
        "source_ref": "FORMAT-EXAMPLE",
        "retrieved": "2026-01-01",
        "clauses": [
            {"clause_id": "CL1", "source_clause_no": "1", "text": C1},
            {"clause_id": "CL2", "source_clause_no": "2", "text": C2},
            {"clause_id": "CL3", "source_clause_no": "3", "text": C3},
        ],
    }
    (tenders / "RT-001.json").write_text(json.dumps(doc), encoding="utf-8")
    (tenders / "ir_RT-001.json").write_text(json.dumps(atoms), encoding="utf-8")
    return data


@pytest.fixture(autouse=True)
def _cache(monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "1")


def run_real(data: Path, out: Path) -> dict:
    assert main(["--all", "--data-dir", str(data), "--out-dir", str(out)]) == 0
    doc = json.loads((out / "RT-001.json").read_text(encoding="utf-8"))
    schemas, registry = load_schemas(REPO_ROOT / "contracts" / "schemas")
    Draft202012Validator(schemas["rules_output"], registry=registry).validate(doc)
    return doc


def test_not_checked_and_vendor_skip(tmp_path):
    data = make_real_dir(tmp_path, [atom("CL1", 1, ">=", 50, C1)])
    doc = run_real(data, tmp_path / "out")
    assert doc["tender_id"] == "RT-001"
    assert doc["not_checked"] == [
        {"clause_id": "CL2", "text": C2, "reason": "no expressible atom"},
        {"clause_id": "CL3", "text": C3, "reason": "no expressible atom"},
    ]
    assert doc["vendor_check"] == SKIPPED
    assert doc["findings"] == []
    assert doc["qualifying_vendors"] == [] and doc["vendors_evaluated"] == 0


def test_all_clauses_unexpressible_listed(tmp_path):
    data = make_real_dir(tmp_path, [])
    doc = run_real(data, tmp_path / "out")
    assert [n["clause_id"] for n in doc["not_checked"]] == ["CL1", "CL2", "CL3"]
    assert doc["atoms"] == [] and doc["findings"] == []


def test_contradiction_still_runs_and_no_vendor_findings(tmp_path):
    data = make_real_dir(tmp_path, [atom("CL1", 1, ">=", 50, C1), atom("CL3", 1, "<=", 10, C3)])
    doc = run_real(data, tmp_path / "out")
    assert [f["type"] for f in doc["findings"]] == ["contradiction"]
    assert doc["findings"][0]["clause_ids"] == ["CL1", "CL3"]
    assert [n["clause_id"] for n in doc["not_checked"]] == ["CL2"]
    assert doc["vendor_check"] == SKIPPED and doc["qualifying_vendors"] == []


def test_satisfiable_has_no_tailored_or_no_qualifier_even_if_vendors_csv_present(tmp_path):
    data = make_real_dir(tmp_path, [atom("CL1", 1, ">=", 50, C1)])
    shutil.copy(REPO_ROOT / "data" / "vendors.csv", data / "vendors.csv")  # must be ignored for RT-
    doc = run_real(data, tmp_path / "out")
    assert doc["findings"] == [] and doc["vendors_evaluated"] == 0


def test_single_real_tender_by_id(tmp_path):
    data = make_real_dir(tmp_path, [])
    assert main(["--tender", "RT-001", "--data-dir", str(data), "--out-dir", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o" / "RT-001.json").is_file()


def test_missing_cache_fails(tmp_path):
    data = make_real_dir(tmp_path, [])
    (data / "tenders" / "ir_RT-001.json").unlink()
    assert main(["--all", "--data-dir", str(data), "--out-dir", str(tmp_path / "o")]) != 0
    assert not (tmp_path / "o" / "RT-001.json").exists()


def test_invalid_real_tender_fails(tmp_path):
    data = make_real_dir(tmp_path, [])
    p = data / "tenders" / "RT-001.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    del doc["source_url"]
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert main(["--all", "--data-dir", str(data), "--out-dir", str(tmp_path / "o")]) != 0


def test_demo_tender_output_has_no_new_keys(tmp_path):
    assert main(["--all", "--out-dir", str(tmp_path)]) == 0
    for f in tmp_path.glob("T-*.json"):
        doc = json.loads(f.read_text(encoding="utf-8"))
        assert "not_checked" not in doc and "vendor_check" not in doc
