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

