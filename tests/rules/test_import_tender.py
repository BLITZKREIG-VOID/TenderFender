from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "import_tender.py"
spec = importlib.util.spec_from_file_location("import_tender", SCRIPT)
import_tender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(import_tender)

HEADER = """title: FORMAT EXAMPLE, not a real tender
source_portal: CPPP
source_url: https://example.invalid/format-example
source_ref: FORMAT-EXAMPLE
retrieved: 2026-01-01
---
"""


def write_raw(tmp_path: Path, body: str, name: str = "RT-001.txt", header: str = HEADER) -> Path:
    p = tmp_path / name
    p.write_text(header + body, encoding="utf-8")
    return p


def run(tmp_path: Path, raw: Path, *extra: str) -> int:
    return import_tender.main([str(raw), "--out-dir", str(tmp_path / "out"), *extra])


def load(tmp_path: Path, tid: str = "RT-001") -> dict:
    return json.loads((tmp_path / "out" / f"{tid}.json").read_text(encoding="utf-8"))


def test_splits_on_own_numbering_and_keeps_text(tmp_path):
    body = (
        "1. FORMAT EXAMPLE first clause\n"
        "   continues on a second line.\n"
        "4.2(b) FORMAT EXAMPLE nested number.\n"
        "(c) FORMAT EXAMPLE bracket letter.\n"
        "d) FORMAT EXAMPLE letter paren.\n"
    )
    assert run(tmp_path, write_raw(tmp_path, body)) == 0
    doc = load(tmp_path)
    assert [c["clause_id"] for c in doc["clauses"]] == ["CL1", "CL2", "CL3", "CL4"]
    assert [c["source_clause_no"] for c in doc["clauses"]] == ["1", "4.2(b)", "(c)", "d)"]
    assert doc["clauses"][0]["text"] == "1. FORMAT EXAMPLE first clause continues on a second line."
    assert all("needs_review" not in c for c in doc["clauses"])
    assert doc["source_ref"] == "FORMAT-EXAMPLE" and doc["retrieved"] == "2026-01-01"


def test_needs_review_triggers(tmp_path):
    body = (
        "preamble without any number\n"
        "1. FORMAT EXAMPLE ok\n"
        "2. FORMAT EXAMPLE duplicate\n"
        "2. FORMAT EXAMPLE duplicate again\n"
        "3. " + "x" * 1200 + "\n"
        "4. FORMAT EXAMPLE | col a | col b |\n"
        "5. FORMAT EXAMPLE tab\tseparated\n"
    )
    assert run(tmp_path, write_raw(tmp_path, body)) == 0
    clauses = load(tmp_path)["clauses"]
    flags = {c["clause_id"]: c.get("needs_review", False) for c in clauses}
    assert clauses[0]["source_clause_no"] == "" and flags["CL1"]
    assert not flags["CL2"]
    assert flags["CL3"] and flags["CL4"]  # duplicate number, both occurrences
    assert flags["CL5"]  # > 1200 chars
    assert flags["CL6"] and flags["CL7"]  # table-like lines


def test_no_numbers_gives_one_flagged_clause(tmp_path):
    assert run(tmp_path, write_raw(tmp_path, "FORMAT EXAMPLE plain text\nmore text\n")) == 0
    clauses = load(tmp_path)["clauses"]
    assert len(clauses) == 1 and clauses[0]["needs_review"] is True
    assert clauses[0]["text"] == "FORMAT EXAMPLE plain text more text"


def test_refuses_overwrite_without_force(tmp_path):
    raw = write_raw(tmp_path, "1. FORMAT EXAMPLE\n")
    assert run(tmp_path, raw) == 0
    before = (tmp_path / "out" / "RT-001.json").read_text(encoding="utf-8")
    raw.write_text(HEADER + "1. FORMAT EXAMPLE changed\n", encoding="utf-8")
    assert run(tmp_path, raw) == 1
    assert (tmp_path / "out" / "RT-001.json").read_text(encoding="utf-8") == before
    assert run(tmp_path, raw, "--force") == 0
    assert "changed" in load(tmp_path)["clauses"][0]["text"]


def test_deterministic(tmp_path):
    raw = write_raw(tmp_path, "1. A\n2. B\n")
    run(tmp_path, raw)
    first = (tmp_path / "out" / "RT-001.json").read_bytes()
    run(tmp_path, raw, "--force")
    assert (tmp_path / "out" / "RT-001.json").read_bytes() == first


@pytest.mark.parametrize(
    "header, name",
    [
        (HEADER.replace("source_ref: FORMAT-EXAMPLE\n", ""), "RT-001.txt"),  # missing key
        (HEADER.replace("2026-01-01", "01/01/2026"), "RT-001.txt"),  # bad date
        (HEADER.replace("https://example.invalid/format-example", "not a url"), "RT-001.txt"),
        (HEADER.replace("title:", "name:"), "RT-001.txt"),  # unknown key
        (HEADER, "T-001.txt"),  # bad tender id
    ],
)
def test_bad_input_rejected(tmp_path, header, name):
    raw = write_raw(tmp_path, "1. FORMAT EXAMPLE\n", name=name, header=header)
    assert run(tmp_path, raw) == 1
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").glob("*.json"))


def test_missing_separator_and_empty_body(tmp_path):
    p = tmp_path / "RT-001.txt"
    p.write_text("title: x\n1. FORMAT EXAMPLE\n", encoding="utf-8")
    assert run(tmp_path, p) == 1
    assert run(tmp_path, write_raw(tmp_path, "   \n\n")) == 1
