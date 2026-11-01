from __future__ import annotations

import json
import shutil
from pathlib import Path
from jsonschema import Draft202012Validator

from rules.compile_llm import RateLimitDailyExhausted
from rules.ir import Atom
from rules.run import REPO_ROOT, load_schemas, main


def test_run_all_with_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "1")
    ret = main(["--all", "--out-dir", str(tmp_path)])
    assert ret == 0

    schema_dir = REPO_ROOT / "contracts" / "schemas"
    schemas, registry = load_schemas(schema_dir)
    validator = Draft202012Validator(schemas["rules_output"], registry=registry)

    out_files = sorted(tmp_path.glob("T-*.json"))
    assert len(out_files) == 3

    for f in out_files:
        doc = json.loads(f.read_text(encoding="utf-8"))
        validator.validate(doc)
        assert doc["formalization_status"] == "unconfirmed"


def test_write_cache_with_cache_mode_fails(monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "1")
    ret = main(["--all", "--write-cache"])
    assert ret != 0


def test_tampered_cache_fails_and_no_output(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "1")

    # Set up temporary data dir with vendors.csv and tenders
    tmp_data = tmp_path / "data"
    tmp_tenders = tmp_data / "tenders"
    tmp_tenders.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "data" / "vendors.csv", tmp_data / "vendors.csv")

    shutil.copy(REPO_ROOT / "data" / "tenders" / "T-001.json", tmp_tenders / "T-001.json")
    ir_content = json.loads((REPO_ROOT / "data" / "tenders" / "ir_T-001.json").read_text(encoding="utf-8"))
    # Tamper source_text of first atom
    ir_content[0]["source_text"] = "TAMPERED TEXT DOES NOT MATCH"
    (tmp_tenders / "ir_T-001.json").write_text(json.dumps(ir_content), encoding="utf-8")

    out_dir = tmp_path / "output"
    ret = main(["--tender", "T-001", "--data-dir", str(tmp_data), "--out-dir", str(out_dir)])

    assert ret != 0
    assert not (out_dir / "T-001.json").exists()


def test_refuse_to_write_empty_cache_on_empty_compile(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "0")

    tmp_data = tmp_path / "data"
    tmp_tenders = tmp_data / "tenders"
    tmp_tenders.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "data" / "vendors.csv", tmp_data / "vendors.csv")
    # Create dummy tender
    dummy = {"tender_id": "T-001", "title": "Test", "clauses": [{"clause_id": "CL1", "text": "Unrelated"}]}
    (tmp_tenders / "T-001.json").write_text(json.dumps(dummy), encoding="utf-8")

    # Mock compile_tender to return []
    monkeypatch.setattr("rules.run.compile_tender", lambda tender: [])

    out_dir = tmp_path / "output"
    cache_file = tmp_tenders / "ir_T-001.json"
    ret = main(["--tender", "T-001", "--data-dir", str(tmp_data), "--out-dir", str(out_dir), "--write-cache"])

    assert ret != 0
    assert not cache_file.exists()


def test_daily_limit_429_stops_run_immediately(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RULES_USE_CACHE", "0")

    tmp_data = tmp_path / "data"
    tmp_tenders = tmp_data / "tenders"
    tmp_tenders.mkdir(parents=True)

    # Create two RT tenders
    for tid in ["RT-001", "RT-002"]:
        doc = {
            "tender_id": tid,
            "title": f"Tender {tid}",
            "source_portal": "ISRO",
            "source_url": "https://www.isro.gov.in/tender",
            "source_ref": f"REF-{tid}",
            "retrieved": "2026-11-01",
            "clauses": [{"clause_id": "CL1", "source_clause_no": "1", "text": "Turnover >= 50 Cr"}],
        }
        (tmp_tenders / f"{tid}.json").write_text(json.dumps(doc), encoding="utf-8")

    call_count = 0

    def mock_compile_batched(tender):
        nonlocal call_count
        call_count += 1
        raise RateLimitDailyExhausted(
            "OpenRouter HTTP 429: free-tier daily rate limit reached (limit_source=openrouter_free_tier_daily, "
            "X-RateLimit-Remaining=0). Run stopped. Quota resets at: 2026-11-02 00:00:00 UTC.",
            reset_time="2026-11-02 00:00:00 UTC",
        )

    monkeypatch.setattr("rules.run.compile_tender_batched", mock_compile_batched)

    out_dir = tmp_path / "output"
    ret = main(["--data-dir", str(tmp_data), "--out-dir", str(out_dir)])

    assert ret == 1
    # Must stop immediately on the first tender and NOT call RT-002
    assert call_count == 1
    captured = capsys.readouterr()
    assert "FATAL:" in captured.err
    assert "2026-11-02 00:00:00 UTC" in captured.err


def test_batch_mode_flag_and_default_for_rt(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_USE_CACHE", "0")

    tmp_data = tmp_path / "data"
    tmp_tenders = tmp_data / "tenders"
    tmp_tenders.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "data" / "vendors.csv", tmp_data / "vendors.csv")

    dummy_t = {
        "tender_id": "T-001",
        "title": "Synthetic",
        "clauses": [{"clause_id": "CL1", "text": "Clause 1 text"}],
    }
    (tmp_tenders / "T-001.json").write_text(json.dumps(dummy_t), encoding="utf-8")

    dummy_rt = {
        "tender_id": "RT-001",
        "title": "Real",
        "source_portal": "ISRO",
        "source_url": "https://www.isro.gov.in/tender",
        "source_ref": "REF-1",
        "retrieved": "2026-11-01",
        "clauses": [{"clause_id": "CL1", "source_clause_no": "1", "text": "Clause 1 text"}],
    }
    (tmp_tenders / "RT-001.json").write_text(json.dumps(dummy_rt), encoding="utf-8")

    atom_item = Atom(
        id="CL1.1",
        clause_id="CL1",
        field="turnover_cr",
        op=">=",
        value=50,
        source_text="Clause 1 text",
    )

    batched_called = []
    per_clause_called = []

    monkeypatch.setattr(
        "rules.run.compile_tender_batched",
        lambda tender: batched_called.append(tender["tender_id"]) or [atom_item],
    )
    monkeypatch.setattr(
        "rules.run.compile_tender",
        lambda tender: per_clause_called.append(tender["tender_id"]) or [atom_item],
    )

    out_dir = tmp_path / "output"

    # RT-001 should default to batched mode without --batch
    ret = main(["--tender", "RT-001", "--data-dir", str(tmp_data), "--out-dir", str(out_dir)])
    assert ret == 0
    assert batched_called == ["RT-001"]
    assert per_clause_called == []

    batched_called.clear()
    per_clause_called.clear()

    # T-001 should default to per-clause mode without --batch
    ret = main(["--tender", "T-001", "--data-dir", str(tmp_data), "--out-dir", str(out_dir)])
    assert ret == 0
    assert batched_called == []
    assert per_clause_called == ["T-001"]

    batched_called.clear()
    per_clause_called.clear()

    # T-001 with --batch should use batched mode
    ret = main(["--tender", "T-001", "--data-dir", str(tmp_data), "--out-dir", str(out_dir), "--batch"])
    assert ret == 0
    assert batched_called == ["T-001"]
    assert per_clause_called == []
