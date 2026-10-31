from __future__ import annotations

import json
import shutil
from pathlib import Path
from jsonschema import Draft202012Validator

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
