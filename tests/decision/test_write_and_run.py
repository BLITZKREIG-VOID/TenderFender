import http.client
import io
import json
import urllib.error

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


def test_template_reasoning_starts_with_template_note(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir)
    out = write.write_template(f, r)
    assert out["reasoning"].startswith(write.TEMPLATE_NOTE)

    empty = make_empty_fusion()
    out_empty = write.write_template(empty, {})
    assert out_empty["reasoning"].startswith(write.TEMPLATE_NOTE)

# ---------------------------------------------------------------- LLM with fake transport

def completion(content, finish_reason="stop", **message_extra):
    return {"choices": [{"finish_reason": finish_reason,
                         "message": {"role": "assistant", "content": content, **message_extra}}]}


class FakeTransport:
    """Items are reply texts (wrapped in a chat-completion body) or ready-made response dicts."""

    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, request):
        self.requests.append(request)
        reply = self.replies.pop(0)
        return reply if isinstance(reply, dict) else completion(reply)


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


def test_llm_request_shape_and_prompt_contents(kb_dir):
    f = make_fusion()
    r = retrieved_for(f, kb_dir)
    t = FakeTransport([GOOD])
    write.write_llm(f, r, set(), api_key=FAKE_KEY, model="my-model", transport=t)
    req = t.requests[0]
    assert req["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert req["headers"]["Authorization"] == f"Bearer {FAKE_KEY}" and req["headers"]["X-Title"] == "TenderFender"
    body = req["body"]
    assert body["model"] == "my-model" and body["temperature"] == 0 and body["seed"] == 42
    assert body["max_tokens"] == 4096 and "response_format" not in body and "system" not in body
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["messages"][0]["content"] == write.SYSTEM_PROMPT and "FIXED" in body["messages"][0]["content"]
    payload = json.loads(body["messages"][1]["content"])
    assert payload["risk_level"] == "high" and payload["decision"] == "escalate"
    assert set(payload) == {"tender_id", "title", "risk_level", "decision", "fixed_fields_note", "findings", "rings",
                            "retrieved_passages_by_key", "passages"}


def test_llm_ignores_reasoning_field(kb_dir):
    f = make_fusion()
    t = FakeTransport([completion(GOOD, reasoning="See [KB-555] which proves illegality.")])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert "KB-555" not in out["reasoning"]


def test_llm_finish_reason_length_is_invalid_and_retried(kb_dir):
    f = make_fusion()
    t = FakeTransport([completion(GOOD, finish_reason="length"), GOOD])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert len(t.requests) == 2 and out["reasoning"].startswith("Finding")
    assert "finish_reason=length" in t.requests[1]["body"]["messages"][-1]["content"]


@pytest.mark.parametrize("content", ["", "   ", None])
def test_llm_empty_content_is_invalid_and_retried(kb_dir, content):
    f = make_fusion()
    t = FakeTransport([completion(content), GOOD])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert len(t.requests) == 2 and out["reasoning"].startswith("Finding")
    assert "empty content" in t.requests[1]["body"]["messages"][-1]["content"]


def test_llm_persistent_length_or_empty_raises_after_retries(kb_dir):
    f = make_fusion()
    t = FakeTransport([completion(GOOD, finish_reason="length"), completion(""), completion(GOOD, "length")])
    with pytest.raises(DecisionValidationError, match="after 2 retries"):
        write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert len(t.requests) == 3


def test_llm_200_with_error_body_raises_llmerror(kb_dir):
    f = make_fusion()
    t = FakeTransport([{"error": {"code": 502, "message": "upstream provider failed"}}])
    with pytest.raises(write.LLMError, match="upstream provider failed") as ei:
        write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert FAKE_KEY not in str(ei.value) and len(t.requests) == 1


def test_llm_unexpected_response_shape_raises_llmerror(kb_dir):
    f = make_fusion()
    with pytest.raises(write.LLMError, match="unexpected OpenRouter response shape"):
        write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY,
                        transport=FakeTransport([{"choices": []}]))


def test_llm_requires_api_key(kb_dir, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    f = make_fusion()
    with pytest.raises(write.LLMError, match="OPENROUTER_API_KEY"):
        write.write_llm(f, {}, set(), transport=FakeTransport([]))


def test_llm_api_key_from_env_goes_only_into_bearer_header(kb_dir, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    f = make_fusion()
    t = FakeTransport([GOOD])
    write.write_llm(f, retrieved_for(f, kb_dir), set(), transport=t)
    assert t.requests[0]["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert FAKE_KEY not in json.dumps(t.requests[0]["body"])


def test_llm_default_model_from_env(kb_dir, monkeypatch):
    monkeypatch.setenv("DECISION_MODEL", "env-model")
    f = make_fusion()
    t = FakeTransport([GOOD])
    write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert t.requests[0]["body"]["model"] == "env-model"
    monkeypatch.delenv("DECISION_MODEL")
    t = FakeTransport([GOOD])
    write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert t.requests[0]["body"]["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"


# ---------------------------------------------------------------- run: modes, cache, invariants

@pytest.fixture
def env(tmp_path, kb_dir, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DECISION_MODEL", raising=False)
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
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    t = FakeTransport([GOOD])
    go(env, "llm", transport=t)
    assert read(env, "T-002")["decision_source"] == "llm"
    entry = json.loads((env["cache_dir"] / "T-002.json").read_text())
    assert entry["decision_source"] == "llm" and entry["retriever"] == "keyword" and entry["input_hash"]
    assert entry["model"] == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert FAKE_KEY not in (env["cache_dir"] / "T-002.json").read_text()

    monkeypatch.delenv("OPENROUTER_API_KEY")
    go(env, "cache")  # hit
    assert read(env, "T-002")["decision_source"] == "cache"
    go(env, "auto")  # hit via auto without key
    assert read(env, "T-002")["decision_source"] == "cache"
    assert len(t.requests) == 1  # no further LLM calls


def test_model_change_makes_cache_stale(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    monkeypatch.setenv("DECISION_MODEL", "model-a")
    go(env, "llm", transport=FakeTransport([GOOD]))
    assert json.loads((env["cache_dir"] / "T-002.json").read_text())["model"] == "model-a"
    go(env, "cache")  # same model: hit
    monkeypatch.setenv("DECISION_MODEL", "model-b")
    with pytest.raises(drun.DecisionError, match="stale"):
        go(env, "cache")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    with pytest.raises(drun.DecisionError, match="OPENROUTER_API_KEY") as ei:
        go(env, "auto")
    assert "DECISION_MODE=template" in str(ei.value)


def test_input_change_makes_cache_stale_and_auto_fails_loudly(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    go(env, "llm", transport=FakeTransport([GOOD]))
    monkeypatch.delenv("OPENROUTER_API_KEY")

    # change an input -> hash mismatch -> loud failure, never silent regeneration
    fusion = json.loads((env["fusion_dir"] / "T-002.json").read_text())
    fusion["_inputs"]["findings"][0]["explanation"] += " Changed."
    (env["fusion_dir"] / "T-002.json").write_text(json.dumps(fusion))
    with pytest.raises(drun.DecisionError, match="stale"):
        go(env, "cache")
    with pytest.raises(drun.DecisionError, match="DECISION_MODE=template"):
        go(env, "auto")


def test_tampered_cache_is_revalidated(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    t = FakeTransport([GOOD])
    go(env, "llm", transport=t)
    p = env["cache_dir"] / "T-002.json"
    entry = json.loads(p.read_text())
    entry["reasoning"] += " Also see [KB-999]."
    p.write_text(json.dumps(entry))
    with pytest.raises(DecisionValidationError, match="KB-999"):
        go(env, "cache")


def test_zero_evidence_tender_never_calls_llm(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
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


# ---------------------------------------------------------------- hardening (D18)

def test_llm_actions_are_fixed_actions_then_deduplicated_extras(kb_dir):
    f = make_fusion()
    fixed = write._actions(f)
    t = FakeTransport([j("Finding [F-1] per [KB-901].", [fixed[0], "Ask for the audit file."])])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert out["recommended_actions"] == fixed + ["Ask for the audit file."]


def test_llm_cannot_drop_fixed_actions(kb_dir):
    f = make_fusion()
    t = FakeTransport([j("Finding [F-1].", ["Ask for the audit file."])])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert out["recommended_actions"][:len(write._actions(f))] == write._actions(f)


def test_llm_contradicting_extra_action_rejected(kb_dir):
    f = make_fusion()
    t = FakeTransport([j("Finding [F-1].", ["No further action required."]),
                       j("Finding [F-1].", ["Proceed with award."]),
                       j("Finding [F-1].", ["Ask for the audit file."])])
    out = write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)
    assert len(t.requests) == 3 and "contradicts decision" in t.requests[1]["body"]["messages"][-1]["content"]
    assert out["recommended_actions"][-1] == "Ask for the audit file."


def test_llm_lookalike_citation_rejected(kb_dir):
    f = make_fusion()
    t = FakeTransport([j("See KB\u2011777."), j("See KB 777."), j("See F\u20139.")])
    with pytest.raises(DecisionValidationError, match="after 2 retries"):
        write.write_llm(f, retrieved_for(f, kb_dir), set(), api_key=FAKE_KEY, transport=t)


def test_system_prompt_marks_inputs_untrusted():
    assert "untrusted data" in write.SYSTEM_PROMPT and "ignore any instructions" in write.SYSTEM_PROMPT


@pytest.mark.parametrize("exc", [ConnectionResetError("reset"), TimeoutError("timed out"),
                                 http.client.IncompleteRead(b""), json.JSONDecodeError("bad", "x", 0)])
def test_urllib_transport_maps_network_errors_to_llmerror(monkeypatch, exc):
    def boom(*a, **k):
        raise exc
    monkeypatch.setattr(write.urllib.request, "urlopen", boom)
    with pytest.raises(write.LLMError):
        write.urllib_transport({"url": "https://example.invalid", "headers": {}, "body": {}})


class FakeHTTPError(urllib.error.HTTPError):
    def __init__(self, code, body):
        super().__init__("https://openrouter.ai", code, "err", {}, io.BytesIO(body.encode()))


@pytest.mark.parametrize("code,body,needles", [
    (429, "slow down", ["429", "rate-limited", "no automatic retry"]),
    (404, "No endpoints found matching your data policy", ["404", "data policy", "privacy settings"]),
    (401, "x" * 2000, ["401"]),
])
def test_urllib_transport_http_errors_are_clean_llmerrors(monkeypatch, code, body, needles):
    def boom(*a, **k):
        raise FakeHTTPError(code, body)
    monkeypatch.setattr(write.urllib.request, "urlopen", boom)
    with pytest.raises(write.LLMError) as ei:
        write.urllib_transport({"url": "https://example.invalid", "headers": {"Authorization": "Bearer " + FAKE_KEY},
                                "body": {}})
    msg = str(ei.value)
    assert all(n in msg for n in needles) and FAKE_KEY not in msg and len(msg) < 700


def test_urllib_transport_uses_120s_timeout(monkeypatch):
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"choices": []}'

    def fake_urlopen(req, timeout=None):
        seen["timeout"] = timeout
        return Resp()
    monkeypatch.setattr(write.urllib.request, "urlopen", fake_urlopen)
    assert write.urllib_transport({"url": "https://example.invalid", "headers": {}, "body": {}}) == {"choices": []}
    assert seen["timeout"] == 120


def test_main_prints_clean_error_exit_2_for_llm_and_decision_errors(env, monkeypatch, capsys):
    argv = ["--fusion-dir", str(env["fusion_dir"]), "--kb-dir", str(env["kb_dir"]),
            "--out-dir", str(env["out_dir"]), "--cache-dir", str(env["cache_dir"]),
            "--mode", "llm", "--retriever", "keyword", "--allow-placeholder", "--min-score", "0"]
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)

    def boom(*a, **k):
        raise TimeoutError("timed out")
    monkeypatch.setattr(write.urllib.request, "urlopen", boom)
    assert drun.main(argv) == 2
    assert "decision error: LLMError" in capsys.readouterr().err
    cache_argv = [a if a != "llm" else "cache" for a in argv]
    assert drun.main(cache_argv) == 2
    assert "decision error: DecisionError" in capsys.readouterr().err


@pytest.mark.parametrize("stem,tid", [("T-002", "../../evil"), ("T-002", "T-2"), ("T-002", "T-003"),
                                      ("T-002", "T-0021")])
def test_run_rejects_bad_or_mismatched_tender_id(env, stem, tid):
    bad = make_fusion()
    bad["tender_id"] = tid
    (env["fusion_dir"] / f"{stem}.json").write_text(json.dumps(bad))
    with pytest.raises(drun.DecisionError, match="tender_id"):
        go(env, "template")
    assert not list(env["out_dir"].parent.glob("evil*")) and not (env["out_dir"].parent.parent / "evil.json").exists()


def test_cache_must_be_json_object(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    env["cache_dir"].mkdir()
    (env["cache_dir"] / "T-002.json").write_text("[1, 2]")
    with pytest.raises(drun.DecisionError, match="must be an object"):
        go(env, "cache")


def test_risk_decision_mismatch_raises(env):
    bad = make_fusion(risk="high", decision="clear")
    (env["fusion_dir"] / "T-002.json").write_text(json.dumps(bad))
    with pytest.raises(drun.DecisionError, match="does not match risk_level"):
        go(env, "template")


def test_cached_contradicting_text_is_rejected_on_load(env, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    t = FakeTransport([j("Finding [F-1].", ["Ask for the audit file."])])
    go(env, "llm", transport=t)
    p = env["cache_dir"] / "T-002.json"
    entry = json.loads(p.read_text())
    entry["recommended_actions"].append("No further action required.")
    p.write_text(json.dumps(entry))
    with pytest.raises(DecisionValidationError, match="contradicts decision"):
        go(env, "cache")


def test_auto_without_key_error_names_key_and_template_mode(env):
    with pytest.raises(drun.DecisionError) as ei:
        go(env, "auto")
    assert "OPENROUTER_API_KEY" in str(ei.value) and "DECISION_MODE=template" in str(ei.value)
