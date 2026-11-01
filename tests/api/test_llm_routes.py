"""Tests for api/llm_routes.py: detect, regenerate, compile, my-tenders CRUD, grounded chat.

Mocked HTTP for every provider; fake keys built at runtime; keys never appear in responses or logs.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import auth, llm_routes, providers, users
from api.auth import require_user
from api.main import app
from api.users import ItemTooLarge, MAX_USER_TENDERS, UsersStore, users_store
from tests.api.test_auth_users import FakeTable, make_verifier
from tests.api.byok_fakes import (
    FakeHTTP,
    anthropic_reply,
    chat_url,
    fake_key,
    google_reply,
    models_url,
    openai_reply,
    resp,
)

ALL_PROVIDERS = ("openrouter", "anthropic", "google", "groq", "xai", "openai", "deepseek", "mistral")
TEST_USER = {"user_id": "test-user-001", "email": "auditor@example.gov.in"}


@pytest.fixture
def table():
    return FakeTable()


@pytest.fixture
def store(table):
    return UsersStore(table)


@pytest.fixture(autouse=True)
def disable_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK", "0")

@pytest.fixture
def http(monkeypatch):
    fake = FakeHTTP()
    monkeypatch.setattr(providers, "send", fake)
    monkeypatch.setattr(providers, "sleep", lambda s: None)

    def no_network(*a, **k):
        raise AssertionError("real network access in a test")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(providers._OPENER, "open", no_network)
    return fake


@pytest.fixture
def consumed():
    return []


@pytest.fixture
def client(table, store, consumed, monkeypatch):
    verifier = make_verifier()
    app.dependency_overrides[require_user] = lambda: TEST_USER
    app.dependency_overrides[users_store] = lambda: store
    app.dependency_overrides[auth.get_verifier] = lambda: verifier

    real_consume = users.consume

    def tracking_consume(user_id: str, kind: str, st: Any = None, now: Any = None):
        consumed.append((user_id, kind))
        return real_consume(user_id, kind, st or store, now=now)

    monkeypatch.setattr(llm_routes, "consume", tracking_consume)
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()

# ── Detect endpoint ──────────────────────────────────────────────────────────


def test_detect_requires_auth(table, store):
    app.dependency_overrides[users_store] = lambda: store
    app.dependency_overrides[auth.get_verifier] = lambda: make_verifier()
    with TestClient(app) as tc:
        res = tc.post("/api/llm/detect", headers={"X-LLM-Key": fake_key("openrouter")})
        assert res.status_code == 401
    app.dependency_overrides.clear()

def test_detect_missing_key_header(client):
    res = client.post("/api/llm/detect")
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "llm_key_required"


def test_detect_invalid_key_format_does_not_echo_key(client):
    bad_key = "short"
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": bad_key})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "invalid_key_format"
    assert bad_key not in res.text


@pytest.mark.parametrize("name", ALL_PROVIDERS)
def test_detect_every_provider_scrubs_key(client, http, caplog, name):
    caplog.set_level(logging.DEBUG)
    key = fake_key("sk" if name == "deepseek" else name)
    model = "m-1"
    if name == "openrouter":
        http.add("GET", providers.OPENROUTER_KEY_URL, resp(200, {"data": {"is_free_tier": True}}))
        http.add("GET", models_url(name), resp(200, {"data": [{"id": model, "name": "M1", "pricing": {"prompt": "0"}}]}))
    elif name == "anthropic":
        http.add("GET", models_url(name), resp(200, {"data": [{"id": model, "display_name": "M1"}]}))
    elif name == "google":
        http.add("GET", models_url(name), resp(200, {"models": [{"name": f"models/{model}", "displayName": "M1", "supportedGenerationMethods": ["generateContent"]}]}))
    else:
        http.add("GET", models_url(name), resp(200, {"data": [{"id": model, "name": "M1"}]}))

    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key, "X-LLM-Provider": name})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["provider"] == name
    assert key not in res.text
    assert key not in caplog.text


# ── Regenerate endpoint ──────────────────────────────────────────────────────


def test_regenerate_unknown_tender(client, http):
    key = fake_key("openrouter")
    res = client.post("/api/tenders/T-999/regenerate", json={"model": "m-1"}, headers={"X-LLM-Key": key})
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "not_found"


def test_regenerate_nothing_to_explain_t003(client, http):
    key = fake_key("openrouter")
    res = client.post("/api/tenders/T-003/regenerate", json={"model": "m-1"}, headers={"X-LLM-Key": key})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "nothing_to_explain"


def test_regenerate_t001_success(client, http, store, consumed, caplog):
    caplog.set_level(logging.DEBUG)
    key = fake_key("openrouter")
    model = "test/model"
    payload = json.dumps({
        "reasoning": "Finding [F-1] supported by [KB-012].",
        "recommended_actions": ["Review procurement procedure."],
    })
    http.add("POST", chat_url("openrouter"), openai_reply(payload))

    res = client.post("/api/tenders/T-001/regenerate", json={"model": model}, headers={"X-LLM-Key": key})
    assert res.status_code == 200
    data = res.json()
    assert data["tender_id"] == "T-001"
    assert data["validated"] is True
    assert data["decision_source"] == "user_llm"
    assert data["provider"] == "openrouter"
    assert data["model"] == model
    assert "[F-1]" in data["reasoning"]
    assert any(c["ref"] == "F-1" for c in data["citations"])
    assert key not in res.text
    assert key not in caplog.text
    assert ("test-user-001", "regen") in consumed

    # Check store has REGEN#T-001
    item = store.get_item("test-user-001", "REGEN#T-001")
    assert item is not None
    assert item["reasoning"] == data["reasoning"]


def test_regenerate_validation_failure_scrubs_errors(client, http, caplog):
    caplog.set_level(logging.DEBUG)
    key = fake_key("openrouter")
    model = "test/model"
    # LLM outputs unknown ref and forbidden wording
    bad_payload = json.dumps({
        "reasoning": f"This tender is corrupt! See [KB-999] for key {key}.",
        "recommended_actions": ["Audit."],
    })
    http.add("POST", chat_url("openrouter"), openai_reply(bad_payload))

    res = client.post("/api/tenders/T-001/regenerate", json={"model": model}, headers={"X-LLM-Key": key})
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "llm_output_invalid"
    assert key not in res.text
    assert key not in caplog.text


# ── Compile endpoint ─────────────────────────────────────────────────────────


SAMPLE_ELIGIBILITY_TEXT = """
1. Technical Capability
The bidder must have completed at least 3 similar works in the last 5 years.
Each work must be of value at least 50 Lakh.

2. Financial Turnover
The average annual financial turnover during the last 3 years must be at least 100 Lakh.
"""


def test_compile_text_too_long(client):
    key = fake_key("openrouter")
    res = client.post("/api/compile", json={
        "title": "Big Tender",
        "text": "x" * 20001,
        "model": "m-1",
    }, headers={"X-LLM-Key": key})
    assert res.status_code == 422


def test_compile_no_clauses(client):
    key = fake_key("openrouter")
    res = client.post("/api/compile", json={
        "title": "Empty",
        "text": "\n\n   \n",
        "model": "m-1",
    }, headers={"X-LLM-Key": key})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "no_clauses"


def test_compile_limit_reached(client, store):
    key = fake_key("openrouter")
    for i in range(MAX_USER_TENDERS):
        t_id = f"U-{i:08x}"
        store.put_tender("test-user-001", t_id, {"title": f"Tender {i}"}, {"tender_id": t_id, "title": f"Tender {i}"})
    res = client.post("/api/compile", json={
        "title": "Tender 21",
        "text": SAMPLE_ELIGIBILITY_TEXT,
        "model": "m-1",
    }, headers={"X-LLM-Key": key})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "tender_limit"

def test_compile_success(client, http, store, consumed, caplog):
    caplog.set_level(logging.DEBUG)
    key = fake_key("groq")
    model = "llama-3"

    # Response for batched compile
    atoms_reply = json.dumps({
        "CL1": [{
            "id": "CL1.1",
            "clause_id": "CL1",
            "field": "years_experience",
            "op": ">=",
            "value": 5,
            "source_text": "The bidder must have completed at least 3 similar works in the last 5 years.",
        }],
        "CL2": [{
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "turnover_lakh",
            "op": ">=",
            "value": 100.0,
            "source_text": "The average annual financial turnover during the last 3 years must be at least 100 Lakh.",
        }],
    })
    http.add("POST", chat_url("groq"), openai_reply(atoms_reply))

    res = client.post("/api/compile", json={
        "title": "Sample Works Tender",
        "text": SAMPLE_ELIGIBILITY_TEXT,
        "model": model,
    }, headers={"X-LLM-Key": key, "X-LLM-Provider": "groq"})

    assert res.status_code == 200
    data = res.json()
    assert data["tender_id"].startswith("U-")
    assert data["title"] == "Sample Works Tender"
    assert data["vendor_check"] == {"status": "skipped", "reason": "no vendor data for user-compiled tenders; synthetic vendors are never used"}
    assert len(data["clauses"]) >= 2
    assert ("test-user-001", "compile") in consumed
    assert key not in res.text
    assert key not in caplog.text

    # Verify item stored in user store
    stored = store.get_item("test-user-001", f"TENDER#{data['tender_id']}")
    assert stored is not None
    assert stored["title"] == "Sample Works Tender"


# ── My-tenders CRUD ──────────────────────────────────────────────────────────


def test_my_tenders_crud(client, store):
    # Empty initially
    res = client.get("/api/me/tenders")
    assert res.status_code == 200
    assert res.json() == []

    # Insert two tenders
    t1 = {"tender_id": "U-11111111", "title": "Tender One", "created_at": "2026-11-01T10:00:00Z", "findings": [{"finding_id": "F-1"}]}
    t2 = {"tender_id": "U-22222222", "title": "Tender Two", "created_at": "2026-11-02T10:00:00Z", "findings": []}
    s1 = {"tender_id": "U-11111111", "uid": "U-11111111", "title": "Tender One", "created_at": "2026-11-01T10:00:00Z", "findings_count": 1, "clause_count": 2}
    s2 = {"tender_id": "U-22222222", "uid": "U-22222222", "title": "Tender Two", "created_at": "2026-11-02T10:00:00Z", "findings_count": 0, "clause_count": 1}
    store.put_tender("test-user-001", "U-11111111", t1, s1)
    store.put_tender("test-user-001", "U-22222222", t2, s2)
    # List is sorted by created_at desc
    res = client.get("/api/me/tenders")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert items[0]["tender_id"] == "U-22222222"
    assert items[1]["tender_id"] == "U-11111111"

    # Get single tender
    res = client.get("/api/me/tenders/U-11111111")
    assert res.status_code == 200
    assert res.json()["title"] == "Tender One"

    # Get non-existent
    res = client.get("/api/me/tenders/U-99999999")
    assert res.status_code == 404

    # Bad format ID
    res = client.get("/api/me/tenders/not-a-uuid")
    assert res.status_code == 404

    # Delete
    res = client.delete("/api/me/tenders/U-11111111")
    assert res.status_code == 204
    assert store.get_item("test-user-001", "TENDER#U-11111111") is None

    # Delete again -> 404
    res = client.delete("/api/me/tenders/U-11111111")
    assert res.status_code == 404


# ── Grounded chat endpoint ───────────────────────────────────────────────────


def test_chat_invalid_turn_structure(client):
    key = fake_key("openrouter")
    # Must start and end with user and alternate
    res = client.post("/api/tenders/T-001/chat", json={
        "model": "m-1",
        "messages": [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi"},
        ],
    }, headers={"X-LLM-Key": key})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "invalid_messages"


def test_chat_public_tender_grounded_answer(client, http, caplog):
    caplog.set_level(logging.DEBUG)
    key = fake_key("openrouter")
    http.add("POST", chat_url("openrouter"), openai_reply("Finding [F-1] indicates contradictory criteria."))

    res = client.post("/api/tenders/T-001/chat", json={
        "model": "m-1",
        "messages": [{"role": "user", "content": "What findings exist?"}],
    }, headers={"X-LLM-Key": key})

    assert res.status_code == 200
    data = res.json()
    assert "Finding [F-1]" in data["answer"]
    assert data["citations"] == [{"kind": "finding", "ref": "F-1"}]
    assert key not in res.text
    assert key not in caplog.text


def test_chat_user_tender_grounded_answer(client, http, store):
    key = fake_key("anthropic")
    u_id = "U-12345678"
    store.put_item("test-user-001", f"TENDER#{u_id}", {
        "tender_id": u_id,
        "title": "Compiled Tender",
        "findings": [{"finding_id": "F-1", "kind": "amount_mismatch", "detail": "mismatch"}],
        "clauses": [{"clause_id": "CL1", "text": "Clause 1"}],
    })
    http.add("POST", chat_url("anthropic"), anthropic_reply("The tender has finding [F-1]."))

    res = client.post(f"/api/tenders/{u_id}/chat", json={
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": "Summary?"}],
    }, headers={"X-LLM-Key": key})

    assert res.status_code == 200
    data = res.json()
    assert "[F-1]" in data["answer"]
    assert data["citations"] == [{"kind": "finding", "ref": "F-1"}]


def test_chat_retries_on_unknown_ref_then_succeeds(client, http):
    key = fake_key("openrouter")
    # First attempt: cites unknown ref [KB-999]
    # Second attempt: corrected citation [F-1]
    http.add("POST", chat_url("openrouter"),
             openai_reply("See [KB-999]."),
             openai_reply("Corrected: see finding [F-1]."))

    res = client.post("/api/tenders/T-001/chat", json={
        "model": "m-1",
        "messages": [{"role": "user", "content": "Explain findings"}],
    }, headers={"X-LLM-Key": key})

    assert res.status_code == 200
    assert "[F-1]" in res.json()["answer"]
    assert len(http.calls) == 2


def test_chat_fails_after_retries_with_forbidden_wording(client, http, caplog):
    caplog.set_level(logging.DEBUG)
    key = fake_key("openrouter")
    # Model uses forbidden word "corrupt" on both attempts
    http.add("POST", chat_url("openrouter"),
             openai_reply(f"This tender is corrupt: {key}."),
             openai_reply(f"Still corrupt: {key}."))

    res = client.post("/api/tenders/T-001/chat", json={
        "model": "m-1",
        "messages": [{"role": "user", "content": "Explain findings"}],
    }, headers={"X-LLM-Key": key})

    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "llm_output_invalid"
    assert key not in res.text
    assert key not in caplog.text


def test_p1_1_detect_consumes_quota_and_enforces_limits(client, http, monkeypatch):
    key = fake_key("groq")
    http.add("GET", models_url("groq"), resp(200, {"data": [{"id": "llama-3"}]}))
    # Successful detect consumes "detect"
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key})
    assert res.status_code == 200

    # User daily limit reached
    monkeypatch.setenv("DAILY_LIMIT_DETECT", "1")
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key})
    assert res.status_code == 429
    assert res.json()["detail"]["code"] == "daily_limit"

    # Global daily limit reached
    monkeypatch.setenv("DAILY_LIMIT_DETECT", "10")
    monkeypatch.setenv("GLOBAL_DAILY_LIMIT_DETECT", "1")
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key})
    assert res.status_code == 429
    assert res.json()["detail"]["code"] == "global_daily_limit"


def test_routes_kill_switch_when_disabled(client, monkeypatch):
    monkeypatch.setenv("LLM_FEATURES_ENABLED", "false")
    key = fake_key("openrouter")

    # All 4 LLM routes return 503 llm_disabled
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key})
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "llm_disabled"

    res = client.post("/api/tenders/T-001/regenerate", json={"model": "m-1"}, headers={"X-LLM-Key": key})
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "llm_disabled"

    res = client.post("/api/compile", json={"title": "T", "text": "1. Test", "model": "m-1"}, headers={"X-LLM-Key": key})
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "llm_disabled"

    res = client.post("/api/tenders/T-001/chat", json={"model": "m-1", "messages": [{"role": "user", "content": "hi"}]}, headers={"X-LLM-Key": key})
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "llm_disabled"

    # Public demo endpoints stay completely operational
    res = client.get("/api/tenders")
    assert res.status_code == 200


def test_p3_4_detect_ambiguous_sk_key_requires_provider_hint(client, http):
    key = fake_key("sk")
    # Without X-LLM-Provider: rejected with 400 and candidates
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key})
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "provider_hint_required"
    assert detail["candidates"] == ["openai", "deepseek"]

    # With X-LLM-Provider: accepted and routed
    http.add("GET", models_url("deepseek"), resp(200, {"data": [{"id": "deepseek-chat"}]}))
    res = client.post("/api/llm/detect", headers={"X-LLM-Key": key, "X-LLM-Provider": "deepseek"})
    assert res.status_code == 200
    assert res.json()["provider"] == "deepseek"


def test_deadline_seconds_is_50_seconds():
    assert providers.DEADLINE_SECONDS == 50
    assert providers.TIMEOUT_SECONDS <= 45


def test_p2_2_my_tenders_returns_summaries(client, store):
    t1 = {"tender_id": "U-11111111", "title": "Tender One", "created_at": "2026-11-01T10:00:00Z", "clauses": ["c1", "c2"]}
    s1 = {"tender_id": "U-11111111", "uid": "U-11111111", "title": "Tender One", "created_at": "2026-11-01T10:00:00Z", "clause_count": 2, "findings_count": 0}
    store.put_tender("test-user-001", "U-11111111", t1, s1)

    res = client.get("/api/me/tenders")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    item = items[0]
    assert item["uid"] == "U-11111111"
    assert item["tender_id"] == "U-11111111"
    assert item["clause_count"] == 2
    assert item["findings_count"] == 0
    assert "clauses" not in item  # full data not leaked in summary listing


def test_p3_5_compile_atomic_tender_cap(client, store):
    # Pre-fill store to max 20 tenders
    for i in range(MAX_USER_TENDERS):
        tid = f"U-{i:08x}"
        store.put_tender("test-user-001", tid, {"tender_id": tid}, {"tender_id": tid, "title": f"T{i}"})
    assert store.get_tender_count("test-user-001") == 20

    # Next compile fails with 409 tender_limit
    key = fake_key("groq")
    res = client.post("/api/compile", json={
        "title": "Tender 21",
        "text": SAMPLE_ELIGIBILITY_TEXT,
        "model": "llama-3",
    }, headers={"X-LLM-Key": key, "X-LLM-Provider": "groq"})
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "tender_limit"
    assert store.get_tender_count("test-user-001") == 20
