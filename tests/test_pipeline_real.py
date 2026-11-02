"""`make pipeline-real` end to end in tmp dirs. All tender text is "FORMAT EXAMPLE, not a real tender"."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.loaders as loaders
from api.main import app
import api.auth as auth

REPO = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")

C1 = "1. FORMAT EXAMPLE, not a real tender: the bidder must have an annual turnover of at least 50 crore."
C2 = "2. FORMAT EXAMPLE, not a real tender: a clause nothing can express."
C3 = "3. FORMAT EXAMPLE, not a real tender: the bidder must have an annual turnover of at most 10 crore."


def _atom(clause: str, op: str, value: int, text: str) -> dict:
    return {"id": f"{clause}.1", "clause_id": clause, "field": "turnover_cr", "op": op, "value": value,
            "source_text": text}


class Root:
    """A throwaway project root: tmp/data/real, tmp/artifacts/{rules_real,fusion_real,fused,decisions}."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.tenders = tmp / "data" / "real" / "tenders"
        self.fused = tmp / "artifacts" / "fused"
        self.env = {k: v for k, v in os.environ.items() if k not in ("OPENROUTER_API_KEY", "DECISION_MODE")}
        self.env["CONFIRMATIONS_PATH"] = str(tmp / "confirmations.json")

    def add_tender(self, atoms: list[dict] | None, tid: str = "RT-001") -> None:
        self.tenders.mkdir(parents=True, exist_ok=True)
        (self.tenders / f"{tid}.json").write_text(json.dumps({
            "tender_id": tid, "title": "FORMAT EXAMPLE, not a real tender", "source_portal": "CPPP",
            "source_url": "https://example.invalid/format-example", "source_ref": "FORMAT-EXAMPLE",
            "retrieved": "2026-01-01",
            "clauses": [{"clause_id": "CL1", "source_clause_no": "1", "text": C1},
                        {"clause_id": "CL2", "source_clause_no": "2", "text": C2},
                        {"clause_id": "CL3", "source_clause_no": "3", "text": C3}],
        }), encoding="utf-8")
        if atoms is not None:
            (self.tenders / f"ir_{tid}.json").write_text(json.dumps(atoms), encoding="utf-8")

    def make(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        cmd = ["make", "-C", str(REPO), "pipeline-real", f"PY={sys.executable}", "RETRIEVER=keyword",
               f"REAL_DATA_DIR={self.tmp / 'data' / 'real'}", f"RULES_REAL_DIR={self.tmp / 'artifacts' / 'rules_real'}",
               f"FUSION_REAL_DIR={self.tmp / 'artifacts' / 'fusion_real'}", f"FUSED_DIR={self.fused}",
               f"CACHE_DIR={self.tmp / 'artifacts' / 'decisions'}", *args]
        return subprocess.run(cmd, capture_output=True, text=True, env={**self.env, **env}, cwd=REPO)


@pytest.fixture
def root(tmp_path):
    return Root(tmp_path)


CONTRADICTION = [_atom("CL1", ">=", 50, C1), _atom("CL3", "<=", 10, C3)]


def test_zero_real_tenders_fails_with_message_and_writes_nothing(root):
    r = root.make()
    assert r.returncode != 0  # make reports a failed recipe as 2; the recipe itself `exit 1`s
    assert "no real tenders in" in r.stderr and "data/real/tenders" in r.stderr
    assert not (root.tmp / "artifacts").exists()


def test_empty_tenders_dir_fails_too(root):
    root.tenders.mkdir(parents=True)
    (root.tenders / "ir_RT-001.json").write_text("[]")  # an IR alone is not a tender
    r = root.make()
    assert r.returncode != 0 and "no real tenders in" in r.stderr


def test_unconfirmed_ir_fails_pointing_to_review_doc(root):
    root.add_tender(CONTRADICTION)
    r = root.make(DECISION_MODE="template")
    assert r.returncode != 0
    assert "docs/REVIEW_ATOMS.md" in r.stderr and "ALLOW_UNCONFIRMED=1" in r.stderr
    assert not (root.fused / "RT-001.json").exists()


def test_allow_unconfirmed_marks_outputs_unconfirmed(root):
    root.add_tender(CONTRADICTION)
    r = root.make("DECISION_MODE=template", ALLOW_UNCONFIRMED="1")
    assert r.returncode == 0, r.stderr
    rules = json.loads((root.tmp / "artifacts" / "rules_real" / "RT-001.json").read_text())
    assert rules["formalization_status"] == "unconfirmed"
    assert "UNCONFIRMED" in r.stderr


def test_missing_ir_fails(root):
    root.add_tender(None)
    r = root.make("DECISION_MODE=template", ALLOW_UNCONFIRMED="1")
    assert r.returncode != 0 and "Cached IR file not found" in r.stderr


def test_auto_without_key_fails_loudly_for_uncached_finding(root):
    root.add_tender(CONTRADICTION)
    r = root.make(ALLOW_UNCONFIRMED="1")  # DECISION_MODE defaults to auto
    assert r.returncode != 0
    assert "DECISION_MODE=auto" in r.stderr and "DECISION_MODE=template" in r.stderr
    assert not (root.fused / "RT-001.json").exists()


def test_end_to_end_review_export_pipeline_and_api(root, monkeypatch):
    root.add_tender(CONTRADICTION)
    # 1. first run on the unconfirmed IR so the reviewer can see the atoms in the API/UI
    assert root.make("DECISION_MODE=template", ALLOW_UNCONFIRMED="1").returncode == 0

    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("CONFIRMATIONS_PATH", root.env["CONFIRMATIONS_PATH"])
    monkeypatch.setattr(loaders, "_project_root", lambda: root.tmp)
    client = TestClient(app)
    for atom_id in ("CL1.1", "CL3.1"):
        assert client.post(f"/api/tenders/RT-001/atoms/{atom_id}/confirm").status_code == 200

    # 2. export the confirmed IR
    exp = subprocess.run([sys.executable, str(REPO / "scripts" / "export_confirmed_ir.py"), "RT-001",
                          "--ir", str(root.tenders / "ir_RT-001.json"),
                          "--confirmations", root.env["CONFIRMATIONS_PATH"]],
                         capture_output=True, text=True, cwd=REPO, env=root.env)
    assert exp.returncode == 0, exp.stderr
    assert (root.tenders / "ir_RT-001.confirmed.json").is_file()

    # 3. the pipeline now needs no ALLOW_UNCONFIRMED
    r = root.make("DECISION_MODE=template")
    assert r.returncode == 0, r.stderr
    rules = json.loads((root.tmp / "artifacts" / "rules_real" / "RT-001.json").read_text())
    assert rules["formalization_status"] == "confirmed" and rules["findings"][0]["type"] == "contradiction"
    fusion = json.loads((root.tmp / "artifacts" / "fusion_real" / "RT-001.json").read_text())
    assert fusion["network_check"]["status"] == "not_applicable" and fusion["source"] == "real"
    fused = json.loads((root.fused / "RT-001.json").read_text())
    assert (fused["risk_level"], fused["decision"], fused["decision_source"]) == ("medium", "review", "template")
    assert fused["reasoning"].startswith("Template reasoning")
    assert fused["graph_flag_ring_ids"] == [] and fused["linked_vendors"] == []
    assert sorted(p.name for p in root.fused.iterdir()) == ["RT-001.json"]  # no T- artifacts appear

    # 4. the API serves it (anonymous gets empty list and 401 on RT; signed-in gets RT)
    assert client.get("/api/tenders").json() == []
    assert client.get("/api/tenders/RT-001/analysis").status_code == 401
    assert client.get("/api/tenders/RT-001/graph").status_code == 401

    app.dependency_overrides[auth.optional_user] = lambda: {"user_id": "test-auditor"}
    try:
        assert [(t["tender_id"], t["source"]) for t in client.get("/api/tenders").json()] == [("RT-001", "real")]
        analysis = client.get("/api/tenders/RT-001/analysis").json()
        assert analysis["source_url"] == "https://example.invalid/format-example"
        assert analysis["rules"]["formalization_status"] == "confirmed"
        assert [n["clause_id"] for n in analysis["rules"]["not_checked"]] == ["CL2"]
        assert client.get("/api/tenders/RT-001/graph").json()["network_check"]["status"] == "not_applicable"
    finally:
        app.dependency_overrides.pop(auth.optional_user, None)


def test_fused_output_validates_against_contract(root):
    root.add_tender(CONTRADICTION)
    assert root.make("DECISION_MODE=template", ALLOW_UNCONFIRMED="1").returncode == 0
    r = subprocess.run([sys.executable, "scripts/validate_contracts.py", "--file", str(root.fused / "RT-001.json")],
                       capture_output=True, text=True, cwd=REPO, env={**root.env, "PYTHONPATH": str(REPO)})
    assert r.returncode == 0, r.stdout + r.stderr
