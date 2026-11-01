"""API behaviour for real (RT-) tenders and the `source` tag. Fixtures are format examples in tmp_path."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.loaders as loaders
from api.main import app

REPO = Path(__file__).resolve().parent.parent.parent
EXAMPLES = REPO / "contracts" / "examples"
CLAUSE = "1. FORMAT EXAMPLE, not a real tender: the bidder must have an annual turnover of at least 50 crore."
NETWORK_NA = {"status": "not_applicable", "reason": "needs bid data (post-award)"}


def _write(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch):
    """A throwaway project root holding one synthetic (T-001) and one real (RT-001) tender."""
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setattr(loaders, "_project_root", lambda: tmp_path)
    art = tmp_path / "artifacts"
    # synthetic T-001 from the contract examples
    _write(art / "fused" / "T-001.json", json.loads((EXAMPLES / "fused_T-001.json").read_text()))
    _write(art / "rules" / "T-001.json", json.loads((EXAMPLES / "rules_T-001.json").read_text()))
    _write(art / "graph" / "graph_output.json", json.loads((EXAMPLES / "graph_output.json").read_text()))
    # real RT-001
    fused = json.loads((EXAMPLES / "fused_RT-001.json").read_text())
    _write(art / "fused" / "RT-001.json", fused)
    atom = {"id": "CL1.1", "clause_id": "CL1", "field": "turnover_cr", "op": ">=", "value": 50, "source_text": CLAUSE}
    _write(art / "rules_real" / "RT-001.json", {
        "tender_id": "RT-001", "formalization_status": "unconfirmed", "atoms": [atom], "findings": [],
        "qualifying_vendors": [], "vendors_evaluated": 0,
        "not_checked": [{"clause_id": "CL2", "text": "2. FORMAT EXAMPLE, not a real tender: unexpressible.",
                         "reason": "no expressible atom"}],
        "vendor_check": {"status": "skipped", "reason": "no vendor data for real tenders; synthetic vendors are never used"},
    })
    _write(tmp_path / "data" / "real" / "tenders" / "RT-001.json", {
        "tender_id": "RT-001", "title": "FORMAT EXAMPLE, not a real tender", "source_portal": "CPPP",
        "source_url": "https://example.invalid/format-example", "source_ref": "FORMAT-EXAMPLE",
        "retrieved": "2026-01-01",
        "clauses": [
            {"clause_id": "CL1", "source_clause_no": "1", "text": CLAUSE},
            {"clause_id": "CL2", "source_clause_no": "2(a)", "text": "2. FORMAT EXAMPLE, not a real tender: unexpressible.",
             "needs_review": True},
        ],
    })
    return tmp_path


@pytest.fixture
def client(root):
    return TestClient(app)


def test_list_includes_t_and_rt_with_source_tags(client):
    items = {t["tender_id"]: t for t in client.get("/api/tenders").json()}
    assert set(items) == {"T-001", "RT-001"}
    assert items["RT-001"]["source"] == "real"
    assert items["T-001"]["source"] == "synthetic_demo"
    assert items["RT-001"]["decision"] == "clear" and items["RT-001"]["risk_level"] == "low"


def test_list_fused_ids_sorted_and_ignores_other_files(root):
    _write(root / "artifacts" / "fused" / "X-001.json", {})
    assert loaders.list_fused_ids() == ["RT-001", "T-001"]


def test_rt_analysis_reads_rules_real_and_real_clauses_with_source(client):
    data = client.get("/api/tenders/RT-001/analysis").json()
    assert data["source"] == "real"
    assert data["fused"]["tender_id"] == "RT-001" and data["fused"]["network_check"] == NETWORK_NA
    assert data["rules"]["tender_id"] == "RT-001" and data["rules"]["vendor_check"]["status"] == "skipped"
    assert [a["id"] for a in data["rules"]["atoms"]] == ["CL1.1"]
    assert data["rules"]["not_checked"][0]["clause_id"] == "CL2"
    assert (data["source_portal"], data["source_url"], data["retrieved"], data["source_ref"]) == (
        "CPPP", "https://example.invalid/format-example", "2026-01-01", "FORMAT-EXAMPLE")
    by_id = {c["clause_id"]: c for c in data["clauses"]}
    assert by_id["CL1"]["source_clause_no"] == "1" and by_id["CL1"]["text"] == CLAUSE
    assert by_id["CL2"]["source_clause_no"] == "2(a)" and by_id["CL2"]["needs_review"] is True
    assert data["atom_status"] == {"CL1.1": {"status": "undecided", "note": "", "at": None}}


def test_rt_rules_are_not_read_from_synthetic_rules_dir(root, client):
    _write(root / "artifacts" / "rules" / "RT-001.json", {"tender_id": "RT-001", "atoms": [], "findings": [{"x": 1}]})
    assert client.get("/api/tenders/RT-001/analysis").json()["rules"]["atoms"][0]["id"] == "CL1.1"


def test_synthetic_analysis_unchanged_apart_from_source(client):
    data = client.get("/api/tenders/T-001/analysis").json()
    assert data["source"] == "synthetic_demo"
    for key in ("source_url", "source_portal", "retrieved", "source_ref"):
        assert key not in data
    assert all("source_clause_no" not in c for c in data["clauses"])


def test_rt_analysis_without_tender_file_still_serves(root, client):
    (root / "data" / "real" / "tenders" / "RT-001.json").unlink()
    data = client.get("/api/tenders/RT-001/analysis").json()
    assert data["source"] == "real" and "source_url" not in data
    assert [c["clause_id"] for c in data["clauses"]] == ["CL1"]  # falls back to atom source text


def test_rt_graph_is_200_empty_with_network_not_applicable(client):
    resp = client.get("/api/tenders/RT-001/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["graph"] == {"nodes": [], "edges": []}
    assert body["rings"] == [] and body["highlighted_paths"] == [] and body["vendor_scores"] == {}
    assert body["network_check"] == NETWORK_NA


def test_rt_graph_needs_no_graph_artifact(root, client):
    (root / "artifacts" / "graph" / "graph_output.json").unlink()
    assert client.get("/api/tenders/RT-001/graph").status_code == 200
    assert client.get("/api/tenders/T-001/graph").status_code == 404  # synthetic behaviour unchanged


def test_unknown_rt_is_404(client):
    assert client.get("/api/tenders/RT-999/analysis").status_code == 404
    assert client.get("/api/tenders/RT-999/graph").status_code == 404


def test_confirmations_work_for_rt_atoms(client, tmp_path):
    resp = client.post("/api/tenders/RT-001/atoms/CL1.1/confirm")
    assert resp.status_code == 200 and resp.json()["formalization_status"] == "confirmed"
    data = client.get("/api/tenders/RT-001/analysis").json()
    assert data["rules"]["formalization_status"] == "confirmed"
    assert data["atom_status"]["CL1.1"]["status"] == "confirmed"
    resp = client.post("/api/tenders/RT-001/atoms/CL1.1/reject", json={"note": "wrong op"})
    assert resp.status_code == 200 and resp.json()["status"] == "rejected"
    assert client.get("/api/tenders/RT-001/analysis").json()["rules"]["formalization_status"] == "unconfirmed"
    assert client.post("/api/tenders/RT-001/atoms/NOPE.1/confirm").status_code == 404
    stored = json.loads(Path(os.environ["CONFIRMATIONS_PATH"]).read_text())
    assert "RT-001" in stored and "T-001" not in stored


def test_source_field_on_fused_wins_over_id_prefix(root):
    assert loaders.tender_source({"source": "synthetic_demo"}, "RT-001") == "synthetic_demo"
    assert loaders.tender_source({}, "RT-001") == "real"
    assert loaders.tender_source(None, "T-001") == "synthetic_demo"


def test_path_traversal_ids_are_rejected(root):
    assert loaders.load_rules("RT-001/../../x") is None
    assert loaders.load_fused("../x") is None
    assert loaders.load_tender_clauses("RT-..") == []
    assert loaders.load_real_tender("RT-001/..") is None


def test_mock_mode_still_serves_demo_tenders_tagged(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    items = TestClient(app).get("/api/tenders").json()
    assert {t["tender_id"] for t in items} == {"T-001", "T-002", "T-003"}
    assert {t["source"] for t in items} == {"synthetic_demo"}
    assert TestClient(app).get("/api/tenders/T-002/analysis").json()["source"] == "synthetic_demo"
