"""
Tests for the Tender Integrity API.

Run with:  MOCK=1 pytest tests/api -q
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure mock mode is set before importing the app
os.environ["MOCK"] = "1"

from api.main import app  # noqa: E402

client = TestClient(app)


# ── Health ───────────────────────────────────────────────────────────────────


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["mode"] == "mock"


# ── Tender list ──────────────────────────────────────────────────────────────


def test_tenders_returns_list():
    resp = client.get("/api/tenders")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    ids = {t["tender_id"] for t in data}
    assert ids == {"T-001", "T-002", "T-003"}


def test_tenders_have_required_fields():
    resp = client.get("/api/tenders")
    for tender in resp.json():
        assert "tender_id" in tender
        assert "title" in tender
        assert "risk_level" in tender
        assert "decision" in tender


def test_tender_risk_levels():
    resp = client.get("/api/tenders")
    by_id = {t["tender_id"]: t for t in resp.json()}
    assert by_id["T-001"]["risk_level"] == "medium"
    assert by_id["T-001"]["decision"] == "review"
    assert by_id["T-002"]["risk_level"] == "high"
    assert by_id["T-002"]["decision"] == "escalate"
    assert by_id["T-003"]["risk_level"] == "low"
    assert by_id["T-003"]["decision"] == "clear"


# ── Tender analysis ─────────────────────────────────────────────────────────


def test_analysis_t001():
    resp = client.get("/api/tenders/T-001/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fused"]["tender_id"] == "T-001"
    assert data["fused"]["risk_level"] == "medium"
    assert data["rules"]["tender_id"] == "T-001"
    assert len(data["rules"]["findings"]) == 1
    assert data["rules"]["findings"][0]["type"] == "contradiction"
    assert set(data["rules"]["findings"][0]["clause_ids"]) == {"CL2", "CL5"}
    assert len(data["clauses"]) >= 2


def test_analysis_t002_high_risk():
    resp = client.get("/api/tenders/T-002/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fused"]["risk_level"] == "high"
    assert data["fused"]["decision"] == "escalate"
    assert data["fused"]["linked_vendors"][0]["vendor_id"] == "V-047"
    assert data["fused"]["linked_vendors"][0]["ring_id"] == "R-1"
    assert data["rules"]["qualifying_vendors"] == ["V-047"]


def test_analysis_t003_clean():
    resp = client.get("/api/tenders/T-003/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fused"]["risk_level"] == "low"
    assert data["fused"]["decision"] == "clear"
    assert data["rules"]["findings"] == []
    assert len(data["rules"]["qualifying_vendors"]) > 1


def test_analysis_not_found():
    resp = client.get("/api/tenders/T-999/analysis")
    assert resp.status_code == 404


# ── Graph endpoint ───────────────────────────────────────────────────────────


def test_graph_t002():
    resp = client.get("/api/tenders/T-002/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "graph" in data
    assert "nodes" in data["graph"]
    assert "edges" in data["graph"]
    assert len(data["highlighted_paths"]) >= 1
    assert data["highlighted_paths"][0]["from"] == "V-047"
    assert len(data["rings"]) == 1
    assert data["rings"][0]["ring_id"] == "R-1"


def test_graph_t003_no_highlights():
    resp = client.get("/api/tenders/T-003/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["highlighted_paths"] == []
    assert data["rings"] == []


def test_graph_not_found():
    resp = client.get("/api/tenders/T-999/graph")
    assert resp.status_code == 404


# ── Confirm atom ─────────────────────────────────────────────────────────────


def test_confirm_atom():
    resp = client.post("/api/tenders/T-001/atoms/CL2.1/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["formalization_status"] == "confirmed"
    assert data["atom_id"] == "CL2.1"

    # Verify the analysis now reflects confirmed status
    analysis = client.get("/api/tenders/T-001/analysis").json()
    assert analysis["rules"]["formalization_status"] == "confirmed"


def test_confirm_atom_not_found_tender():
    resp = client.post("/api/tenders/T-999/atoms/CL2.1/confirm")
    assert resp.status_code == 404


def test_confirm_atom_not_found_atom():
    resp = client.post("/api/tenders/T-001/atoms/FAKE.1/confirm")
    assert resp.status_code == 404



# ── Passages & clauses ───────────────────────────────────────────────────────

PASSAGE_KEYS = {"passage_id", "source_title", "source_url", "section", "retrieved", "topics", "text"}


def test_analysis_passages_have_kb_fields():
    data = client.get("/api/tenders/T-002/analysis").json()
    cited = [c["ref"] for c in data["fused"]["citations"] if c["kind"] == "guideline"]
    assert cited
    assert [p["passage_id"] for p in data["passages"]] == cited
    for p in data["passages"]:
        assert set(p) == PASSAGE_KEYS
        assert "missing" not in p
        assert p["source_title"] and p["source_url"].startswith("http")
        assert p["section"] and p["retrieved"] and p["text"]
        assert isinstance(p["topics"], list) and p["topics"]


def test_analysis_passage_matches_file():
    p = client.get("/api/tenders/T-001/analysis").json()["passages"][0]
    assert p["passage_id"] == "KB-012"
    assert p["section"] == "Rule 173 (i)"
    assert "eligibility" in p["topics"]
    assert p["text"].startswith("Excerpt")


def test_analysis_missing_passage_does_not_crash(tmp_path, monkeypatch):
    (tmp_path / "KB-009.md").write_text(
        "---\npassage_id: KB-009\nsource_title: T\nsource_url: http://x\n"
        "section: S\nretrieved: 2026-01-01\ntopics: [a, b]\n---\nbody text\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KB_DIR", str(tmp_path))
    # T-002 cites KB-014 / KB-013, which are absent from tmp_path
    resp = client.get("/api/tenders/T-002/analysis")
    assert resp.status_code == 200
    passages = resp.json()["passages"]
    assert passages and all(p == {"passage_id": p["passage_id"], "missing": True} for p in passages)
    # T-003 cites KB-009, which exists here
    p = client.get("/api/tenders/T-003/analysis").json()["passages"][0]
    assert p["topics"] == ["a", "b"] and p["text"] == "body text" and "missing" not in p


def test_analysis_malformed_passage_is_missing(tmp_path, monkeypatch):
    (tmp_path / "KB-009.md").write_text("no front matter here", encoding="utf-8")
    monkeypatch.setenv("KB_DIR", str(tmp_path))
    p = client.get("/api/tenders/T-003/analysis").json()["passages"][0]
    assert p == {"passage_id": "KB-009", "missing": True}


def test_clauses_come_from_tender_data():
    data = client.get("/api/tenders/T-002/analysis").json()
    by_id = {c["clause_id"]: c["text"] for c in data["clauses"]}
    assert len(by_id) == 7
    assert by_id["CL3"] == "The bidder must have an annual turnover of at least ₹100 crore."
    assert by_id["CL5"].startswith("Bids must be submitted")
