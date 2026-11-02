"""
Tests for the Tender Integrity API.

Run with:  MOCK=1 pytest tests/api -q
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure mock mode is set before importing the app
os.environ["MOCK"] = "1"

from api.auth import optional_user  # noqa: E402
from api.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _signed_in():
    """Confirm/reject require sign-in; these tests act as a signed-in auditor."""
    app.dependency_overrides[optional_user] = lambda: {"user_id": "test-auditor"}
    yield
    app.dependency_overrides.pop(optional_user, None)


def test_confirm_and_reject_require_sign_in():
    app.dependency_overrides.pop(optional_user, None)
    for verb in ("confirm", "reject"):
        resp = client.post(f"/api/tenders/T-001/atoms/CL2.1/{verb}")
        assert resp.status_code == 401 and resp.json()["detail"]["code"] == "unauthenticated"


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
    # formalization_status is "confirmed" only once every atom (T-001 has CL2.1 and CL5.1) is confirmed
    resp = client.post("/api/tenders/T-001/atoms/CL2.1/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["formalization_status"] == "unconfirmed"
    assert data["atom_id"] == "CL2.1"
    assert set(data) == {"tender_id", "atom_id", "formalization_status"}

    resp = client.post("/api/tenders/T-001/atoms/CL5.1/confirm")
    assert resp.json()["formalization_status"] == "confirmed"

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

# ── Static UI Serving & SPA Routing ──────────────────────────────────────────

def test_static_ui_serving_with_temp_dist(tmp_path):
    dist_dir = tmp_path / "ui_dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>SPA Index</html>")
    (dist_dir / "favicon.svg").write_text("<svg>favicon</svg>")
    
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "app-12345.js").write_text("console.log('app');")

    os.environ["UI_DIST"] = str(dist_dir)
    try:
        from importlib import reload
        import api.main
        reload(api.main)
        from api.main import app as dynamic_app
        dyn_client = TestClient(dynamic_app)

        r1 = dyn_client.get("/")
        assert r1.status_code == 200
        assert "SPA Index" in r1.text
        assert "no-cache" in r1.headers.get("cache-control", "")

        r2 = dyn_client.get("/assets/app-12345.js")
        assert r2.status_code == 200
        assert "immutable" in r2.headers.get("cache-control", "")

        r3 = dyn_client.get("/tenders/T-002")
        assert r3.status_code == 200
        assert "SPA Index" in r3.text

        r4 = dyn_client.get("/api/nope")
        assert r4.status_code == 404
    finally:
        os.environ.pop("UI_DIST", None)
        reload(api.main)


# ── Persistent confirmations ─────────────────────────────────────────────────


def _fresh_client():
    from api.main import app as fresh_app
    return TestClient(fresh_app)


def test_atom_status_in_analysis_defaults_undecided():
    data = client.get("/api/tenders/T-001/analysis").json()
    assert set(data["atom_status"]) == {"CL2.1", "CL5.1"}
    assert all(v["status"] == "undecided" for v in data["atom_status"].values())
    assert data["rules"]["formalization_status"] == "unconfirmed"


def test_confirm_and_reject_persist_across_fresh_instances(tmp_path):
    path = tmp_path / "confirmations.json"
    assert client.post("/api/tenders/T-001/atoms/CL2.1/confirm").status_code == 200
    resp = client.post("/api/tenders/T-001/atoms/CL5.1/reject", json={"note": "wrong op"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected" and body["note"] == "wrong op"
    assert body["formalization_status"] == "unconfirmed"

    stored = __import__("json").loads(path.read_text())
    assert stored["T-001"]["CL2.1"]["status"] == "confirmed"
    assert stored["T-001"]["CL5.1"] == {"status": "rejected", "note": "wrong op", "at": stored["T-001"]["CL5.1"]["at"]}
    assert "T" in stored["T-001"]["CL5.1"]["at"]

    data = _fresh_client().get("/api/tenders/T-001/analysis").json()
    assert data["atom_status"]["CL2.1"]["status"] == "confirmed"
    assert data["atom_status"]["CL5.1"]["status"] == "rejected"
    assert data["atom_status"]["CL5.1"]["note"] == "wrong op"
    assert data["rules"]["formalization_status"] == "unconfirmed"
    # other tenders are unaffected
    other = client.get("/api/tenders/T-002/analysis").json()
    assert all(v["status"] == "undecided" for v in other["atom_status"].values())


def test_reject_without_body_and_reconfirm_overrides():
    resp = client.post("/api/tenders/T-001/atoms/CL2.1/reject")
    assert resp.status_code == 200 and resp.json()["note"] == ""
    client.post("/api/tenders/T-001/atoms/CL2.1/confirm")
    data = client.get("/api/tenders/T-001/analysis").json()
    assert data["atom_status"]["CL2.1"]["status"] == "confirmed"


def test_reject_not_found():
    assert client.post("/api/tenders/T-999/atoms/CL2.1/reject").status_code == 404
    assert client.post("/api/tenders/T-001/atoms/FAKE.1/reject").status_code == 404


def test_confirm_readonly_path_returns_503(tmp_path, monkeypatch):
    ro = tmp_path / "ro"
    ro.mkdir()
    ro.chmod(0o500)
    monkeypatch.setenv("CONFIRMATIONS_PATH", str(ro / "confirmations.json"))
    try:
        if os.access(ro, os.W_OK):
            pytest.skip("running as a user that ignores directory permissions")
        for action in ("confirm", "reject"):
            resp = client.post(f"/api/tenders/T-001/atoms/CL2.1/{action}")
            assert resp.status_code == 503
            detail = resp.json()["detail"]
            assert detail["code"] == "confirmations_readonly"
            assert detail["error"]
    finally:
        ro.chmod(0o700)


def test_seed_copied_on_first_use(tmp_path, monkeypatch):
    import json
    from api import confirmations
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"T-001": {"CL2.1": {"status": "confirmed", "note": "", "at": "2026-01-01T00:00:00+00:00"}}}))
    target = tmp_path / "tmp" / "confirmations.json"
    monkeypatch.setattr(confirmations, "default_path", lambda: seed)
    monkeypatch.setenv("CONFIRMATIONS_PATH", str(target))
    data = client.get("/api/tenders/T-001/analysis").json()
    assert data["atom_status"]["CL2.1"]["status"] == "confirmed"
    assert target.is_file()
    client.post("/api/tenders/T-001/atoms/CL5.1/confirm")
    assert json.loads(seed.read_text())["T-001"].keys() == {"CL2.1"}  # seed itself is never modified
    assert client.get("/api/tenders/T-001/analysis").json()["rules"]["formalization_status"] == "confirmed"
