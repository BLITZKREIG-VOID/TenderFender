from __future__ import annotations

import io
import json
import urllib.error

import pytest

from rules import compile_llm
from rules.compile_llm import CompileError, _call_api, compile_clause

ATOM = {
    "id": "CL2.1",
    "clause_id": "CL2",
    "field": "turnover_cr",
    "op": ">=",
    "value": 50,
    "source_text": "Clause text",
}


class FakeResponse:
    def __init__(self, body: dict):
        self._raw = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def chat(content, finish="stop") -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


@pytest.fixture
def http(monkeypatch):
    """Replace urlopen; returns (queue of replies, list of captured requests). No real network."""
    replies: list = []
    seen: list = []

    def fake_urlopen(req, timeout=None):
        seen.append(req)
        item = replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)

    monkeypatch.setattr(compile_llm.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("RULES_MODEL", raising=False)
    return replies, seen


def test_always_invalid_replies():
    call_count = 0

    def mock_call(system: str, messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        return "Invalid JSON"

    with pytest.raises(CompileError):
        compile_clause("CL2", "Clause text", call=mock_call)

    assert call_count == 3


def test_invalid_then_valid():
    call_count = 0
    valid_payload = json.dumps([
        {
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "turnover_cr",
            "op": ">=",
            "value": 50,
            "source_text": "Clause text",
        }
    ])

    def mock_call(system: str, messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json"
        return valid_payload

    atoms = compile_clause("CL2", "Clause text", call=mock_call)
    assert call_count == 2
    assert len(atoms) == 1
    assert atoms[0].id == "CL2.1"
    assert atoms[0].value == 50


def test_wrong_source_text_counts_as_invalid():
    call_count = 0
    bad_payload = json.dumps([
        {
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "turnover_cr",
            "op": ">=",
            "value": 50,
            "source_text": "Wrong source text",
        }
    ])
    good_payload = json.dumps([
        {
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "turnover_cr",
            "op": ">=",
            "value": 50,
            "source_text": "Expected text",
        }
    ])

    def mock_call(system: str, messages: list[dict]) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return bad_payload
        return good_payload

    atoms = compile_clause("CL2", "Expected text", call=mock_call)
    assert call_count == 2
    assert len(atoms) == 1
    assert atoms[0].source_text == "Expected text"


def test_missing_openrouter_api_key_raises_compile_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(CompileError, match="OPENROUTER_API_KEY is not set"):
        _call_api("system prompt", [{"role": "user", "content": "hi"}])


def test_request_shape_and_default_model(http):
    replies, seen = http
    replies.append(chat(json.dumps([ATOM])))
    atoms = compile_clause("CL2", "Clause text")
    assert [a.id for a in atoms] == ["CL2.1"]
    req = seen[0]
    assert req.full_url == "https://openrouter.ai/api/v1/chat/completions"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer test-key"
    body = json.loads(req.data)
    assert body["model"] == compile_llm.DEFAULT_MODEL == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1] == {"role": "user", "content": "Clause ID: CL2\nClause Text: Clause text"}
    assert body["temperature"] == 0


def test_model_override(http, monkeypatch):
    replies, seen = http
    monkeypatch.setenv("RULES_MODEL", "some/other-model")
    replies.append(chat(json.dumps([ATOM])))
    compile_clause("CL2", "Clause text")
    assert json.loads(seen[0].data)["model"] == "some/other-model"


def test_retry_then_success_over_http(http):
    replies, seen = http
    replies.extend([chat("not json"), chat(json.dumps([ATOM]))])
    atoms = compile_clause("CL2", "Clause text")
    assert len(atoms) == 1
    assert len(seen) == 2
    second = json.loads(seen[1].data)["messages"]
    assert second[-2] == {"role": "assistant", "content": "not json"}
    assert second[-1]["content"].startswith("Validation error:")


def test_retries_exhausted_over_http(http):
    replies, seen = http
    replies.extend([chat("bad")] * 3)
    with pytest.raises(CompileError, match="after 3 attempts"):
        compile_clause("CL2", "Clause text")
    assert len(seen) == 3


@pytest.mark.parametrize("reply", [chat("[]", finish="length"), chat(""), chat(None)])
def test_length_or_empty_is_invalid_then_retried(http, reply):
    replies, seen = http
    replies.extend([reply, chat(json.dumps([ATOM]))])
    atoms = compile_clause("CL2", "Clause text")
    assert len(atoms) == 1
    assert len(seen) == 2
    assert "Previous reply rejected" in json.loads(seen[1].data)["messages"][-1]["content"]


def test_http_error_is_not_retried(http):
    replies, seen = http
    replies.append(urllib.error.HTTPError(
        compile_llm.API_URL, 429, "Too Many Requests", {}, io.BytesIO(b"slow down")))
    with pytest.raises(CompileError, match="HTTP 429"):
        compile_clause("CL2", "Clause text")
    assert len(seen) == 1
