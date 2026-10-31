import json

import pytest

from decision import run as drun
from decision import write
from decision.retrieve import KeywordRetriever, build_queries, load_passages, retrieve
from decision.validate import DecisionValidationError, validate_decision
from tests.decision.conftest import make_empty_fusion, make_fusion

FAKE_KEY = "test-key-not-real"


def retrieved_for(fusion, kb_dir, allow_placeholder=True, min_score=0.0):
    return retrieve(build_queries(fusion["_inputs"]), load_passages(kb_dir), KeywordRetriever(),
                    min_score=min_score, allow_placeholder=allow_placeholder)


# ---------------------------------------------------------------- template

def test_template_cites_findings_rings_and_retrieved_passages(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir)
    out = write.write_template(f, r)
    assert "[F-1]" in out["reasoning"] and "[R-1]" in out["reasoning"] and "[KB-901]" in out["reasoning"]
    cites = validate_decision(out, write.allowed_refs(f["_inputs"], r), set())
    assert {"ref": "KB-901", "kind": "guideline"} in cites
    assert any("escalate" in a.lower() for a in out["recommended_actions"])


def test_template_states_missing_support_explicitly(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir, allow_placeholder=False)  # placeholders excluded -> nothing retrieved
    out = write.write_template(f, r)
    assert "No guideline passage in the knowledge base was retrieved in support of finding F-1." in out["reasoning"]
    assert "No guideline passage in the knowledge base was retrieved in support of ring R-1." in out["reasoning"]
    assert "KB-" not in out["reasoning"]


def test_template_with_no_findings_or_rings_invents_nothing():
    f = make_empty_fusion()
    out = write.write_template(f, {})
    assert "No rule findings and no flagged rings" in out["reasoning"]
    assert validate_decision(out, set(), set()) == []
    assert out["recommended_actions"] == ["No action required beyond standard procurement review."]


# ---------------------------------------------------------------- LLM with fake transport

class FakeTransport:
    def __init__(self, texts):
        self.texts, self.requests = list(texts), []

    def __call__(self, request):
        self.requests.append(request)
        return {"content": [{"type": "text", "text": self.texts.pop(0)}]}


def j(reasoning, actions=("Review.",)):
    return json.dumps({"reasoning": reasoning, "recommended_actions": list(actions)})


GOOD = j("Finding [F-1] and ring [R-1] supported by [KB-901].")
BAD = j("See [KB-555] which proves illegality.")


def test_llm_retry_invalid_invalid_valid_succeeds(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir)
    t = FakeTransport([BAD, BAD, GOOD])
    out = write.write_llm(f, r, set(), api_key=FAKE_KEY, model="m", transport=t)
    assert len(t.requests) == 3
    assert out["citations"] == [{"ref": "KB-901", "kind": "guideline"}, {"ref": "F-1", "kind": "finding"},
                                {"ref": "R-1", "kind": "ring"}]
    # error feedback is sent on retries
    assert "rejected" in t.requests[1]["body"]["messages"][-1]["content"]
    assert "KB-555" in t.requests[1]["body"]["messages"][-1]["content"]


def test_llm_three_invalid_raises(kb_dir):
    f = make_fusion()
    t = FakeTransport([BAD, BAD, BAD])
    with pytest.raises(DecisionValidationError, match="after 2 retries"):
        write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert len(t.requests) == 3


def test_llm_non_json_counts_as_invalid(kb_dir):
    f = make_fusion()
    t = FakeTransport(["not json", GOOD])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert out["reasoning"].startswith("Finding")


def test_llm_prompt_contains_only_allowed_material_and_fixed_fields(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir)
    t = FakeTransport([GOOD])
    write.write_llm(f, r, set(), api_key=FAKE_KEY, model="my-model", transport=t)
    req = t.requests[0]
    assert req["url"] == "https://api.anthropic.com/v1/messages"
    assert req["headers"]["x-api-key"] == FAKE_KEY and req["body"]["model"] == "my-model"
    payload = json.loads(req["body"]["messages"][0]["content"])
    assert payload["risk_level"] == "high" and payload["decision"] == "escalate"
    assert set(payload) == {"tender_id", "title", "risk_level", "decision", "fixed_fields_note", "findings", "rings",
                            "retrieved_passages_by_key", "passages"}
    assert "FIXED" in req["body"]["system"]


def test_llm_requires_api_key(kb_dir, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    f = make_fusion()
    with pytest.raises(write.LLMError, match="ANTHROPIC_API_KEY"):
        write.write_llm(f, {}, set(), transport=FakeTransport([]))


def test_llm_default_model_from_env(kb_dir, monkeypatch):
    monkeypatch.setenv("DECISION_MODEL", "env-model")
    f = make_fusion()
    t = FakeTransport([GOOD])
    write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert t.requests[0]["body"]["model"] == "env-model"
    monkeypatch.delenv("DECISION_MODEL")
    t = FakeTransport([GOOD])
    write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert t.requests[0]["body"]["model"] == "claude-sonnet-4-5"


# ---------------------------------------------------------------- run: modes, cache, invariants

@pytest.fixture
def env(tmp_path, kb_dir, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fdir = tmp_path / "fusion"
    fdir.mkdir()
    (fdir / "T-002.json").write_text(json.dumps(make_fusion()))
    (fdir / "T-003.json").write_text(json.dumps(make_empty_fusion()))
    return {"fusion_dir": fdir, "kb_dir": kb_dir, "out_dir": tmp_path / "fused", "cache_dir": tmp_path / "cache"}


def go(env, mode, **kw):
    return drun.run(env["fusion_dir"], env["kb_dir"], env["out_dir"], env["cache_dir"], mode=mode,
                    retriever_name="keyword", allow_placeholder=True, min_score=0.0, **kw)


def read(env, tid):
    return json.loads((env["out_dir"] / f"{tid}.json").read_text())


def test_template_mode_builds_valid_final_record_and_keeps_risk(env):
    go(env, "template")
    rec = read(env, "T-002")
    assert "_inputs" not in rec and rec["decision_source"] == "template"
    assert (rec["risk_level"], rec["decision"]) == ("high", "escalate")
    assert rec["disclaimer"] == drun.DISCLAIMER
    assert {"ref": "F-1", "kind": "finding"} in rec["citations"]
    t3 = read(env, "T-003")
    assert (t3["risk_level"], t3["decision"], t3["citations"]) == ("low", "clear", [])
    assert not (env["cache_dir"] / "T-002.json").exists()  # template does not write the cache


def test_placeholder_never_cited_without_flag(env):
    drun.run(env["fusion_dir"], env["kb_dir"], env["out_dir"], env["cache_dir"], mode="template",
             retriever_name="keyword", min_score=0.0)
    assert not [c for c in read(env, "T-002")["citations"] if c["kind"] == "guideline"]


def test_auto_without_cache_or_key_fails_loudly(env):
    with pytest.raises(drun.DecisionError, match="DECISION_MODE=template"):
        go(env, "auto")


def test_cache_mode_without_entry_fails(env):
    with pytest.raises(drun.DecisionError, match="no cached decision"):
        go(env, "cache")


def test_llm_writes_cache_then_cache_hit_and_hash_mismatch(env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    t = FakeTransport([GOOD])
    go(env, "llm", transport=t)
    assert read(env, "T-002")["decision_source"] == "llm"
    entry = json.loads((env["cache_dir"] / "T-002.json").read_text())
    assert entry["decision_source"] == "llm" and entry["retriever"] == "keyword" and entry["input_hash"]

    monkeypatch.delenv("ANTHROPIC_API_KEY")
    go(env, "cache")  # hit
    assert read(env, "T-002")["decision_source"] == "cache"
    go(env, "auto")  # hit via auto without key
    assert read(env, "T-002")["decision_source"] == "cache"
    assert len(t.requests) == 1  # no further LLM calls

    # change an input -> hash mismatch -> loud failure, never silent regeneration
    fusion = json.loads((env["fusion_dir"] / "T-002.json").read_text())
    fusion["_inputs"]["findings"][0]["explanation"] += " Changed."
    (env["fusion_dir"] / "T-002.json").write_text(json.dumps(fusion))
    with pytest.raises(drun.DecisionError, match="stale"):
        go(env, "cache")
    with pytest.raises(drun.DecisionError, match="DECISION_MODE=template"):
        go(env, "auto")


def test_tampered_cache_is_revalidated(env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    t = FakeTransport([GOOD])
    go(env, "llm", transport=t)
    p = env["cache_dir"] / "T-002.json"
    entry = json.loads(p.read_text())
    entry["reasoning"] += " Also see [KB-999]."
    p.write_text(json.dumps(entry))
    with pytest.raises(DecisionValidationError, match="KB-999"):
        go(env, "cache")


def test_zero_evidence_tender_never_calls_llm(env, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_KEY)
    (env["fusion_dir"] / "T-002.json").unlink()
    t = FakeTransport([])  # any call would IndexError
    go(env, "llm", transport=t)
    assert read(env, "T-003")["decision_source"] == "template" and t.requests == []


def test_empty_kb_allowed_and_stated(env, tmp_path):
    env["kb_dir"] = tmp_path / "no_kb"
    go(env, "template")
    assert "No guideline passage in the knowledge base was retrieved in support of finding F-1." in read(env, "T-002")["reasoning"]


def test_missing_fusion_dir_errors(env, tmp_path):
    env["fusion_dir"] = tmp_path / "nope"
    with pytest.raises(drun.DecisionError, match="missing fusion directory"):
        go(env, "template")


def test_no_real_http_used(monkeypatch):
    """Guard: tests must always inject a transport; the default must never be hit here."""
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("real HTTP attempted"))
    f = make_fusion()
    with pytest.raises(DecisionValidationError):
        write.write_llm(f, {}, set(), api_key=FAKE_KEY, transport=FakeTransport([BAD, BAD, BAD]))
