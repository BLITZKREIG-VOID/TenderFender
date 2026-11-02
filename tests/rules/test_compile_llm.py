from __future__ import annotations

import io
import json
import urllib.error

import pytest

from rules import compile_llm
from rules.compile_llm import (
    CompileError,
    HTTP503Error,
    RateLimitDailyExhausted,
    _call_api,
    compile_clause,
    compile_tender_batched,
)

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
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(CompileError, match="OPENROUTER_API_KEY is not set"):
        _call_api("system prompt", [{"role": "user", "content": "hi"}])


def test_missing_aws_credentials_raises_compile_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    with pytest.raises(CompileError, match="AWS credentials not found"):
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


BATCH_TENDER = {
    "tender_id": "RT-001",
    "clauses": [
        {"clause_id": "CL1", "text": "Annual turnover of bidder shall be at least 50 crore."},
        {"clause_id": "CL2", "text": "Bidder must have 5 years experience in similar works."},
    ],
}

BATCH_VALID_REPLY = {
    "CL1": [
        {
            "id": "CL1.1",
            "clause_id": "CL1",
            "field": "turnover_cr",
            "op": ">=",
            "value": 50,
            "source_text": "turnover of bidder shall be at least 50 crore",
        }
    ],
    "CL2": [
        {
            "id": "CL2.1",
            "clause_id": "CL2",
            "field": "years_experience",
            "op": ">=",
            "value": 5,
            "source_text": "5 years experience",
        }
    ],
}


def test_batched_request_shape(http):
    replies, seen = http
    replies.append(chat(json.dumps(BATCH_VALID_REPLY)))
    atoms = compile_tender_batched(BATCH_TENDER)
    assert len(atoms) == 2
    assert [a.id for a in atoms] == ["CL1.1", "CL2.1"]
    assert len(seen) == 1

    req = seen[0]
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer test-key"
    body = json.loads(req.data)
    assert body["model"] == compile_llm.DEFAULT_MODEL
    user_msg = body["messages"][1]["content"]
    assert "Clause ID: CL1" in user_msg
    assert "Annual turnover of bidder shall be at least 50 crore." in user_msg
    assert "Clause ID: CL2" in user_msg
    assert "Bidder must have 5 years experience in similar works." in user_msg


def test_batched_key_clause_mismatch_rejected(http):
    replies, seen = http
    bad_reply = {
        "CL1": [
            {
                "id": "CL1.1",
                "clause_id": "CL2",  # mismatch: key is CL1 but atom is CL2
                "field": "turnover_cr",
                "op": ">=",
                "value": 50,
                "source_text": "turnover of bidder shall be at least 50 crore",
            }
        ],
        "CL2": [],
    }
    replies.extend([chat(json.dumps(bad_reply))] * 3)
    with pytest.raises(CompileError, match="after 3 attempts"):
        compile_tender_batched(BATCH_TENDER)
    assert len(seen) == 3


def test_batched_source_text_not_substring_rejected(http):
    replies, seen = http
    bad_reply = {
        "CL1": [
            {
                "id": "CL1.1",
                "clause_id": "CL1",
                "field": "turnover_cr",
                "op": ">=",
                "value": 50,
                "source_text": "completely fabricated text not in clause",
            }
        ],
        "CL2": [],
    }
    replies.extend([chat(json.dumps(bad_reply)), chat(json.dumps(BATCH_VALID_REPLY))])
    atoms = compile_tender_batched(BATCH_TENDER)
    assert len(atoms) == 2
    assert len(seen) == 2
    second_body = json.loads(seen[1].data)["messages"]
    assert "Validation error:" in second_body[-1]["content"]


def test_batched_daily_limit_429_stops_run(http):
    replies, seen = http
    body_dict = {
        "error": {
            "message": "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day",
            "code": 429,
            "metadata": {
                "headers": {
                    "X-RateLimit-Limit": "50",
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": "1793577600000",
                },
                "limit_source": "openrouter_free_tier_daily",
            },
        }
    }
    err = urllib.error.HTTPError(
        compile_llm.API_URL,
        429,
        "Too Many Requests",
        {"X-RateLimit-Remaining": "0"},
        io.BytesIO(json.dumps(body_dict).encode("utf-8")),
    )
    replies.append(err)
    with pytest.raises(RateLimitDailyExhausted) as exc_info:
        compile_tender_batched(BATCH_TENDER)
    assert len(seen) == 1
    assert "openrouter_free_tier_daily" in str(exc_info.value)
    assert "2026-11-02 00:00:00 UTC" in str(exc_info.value)
    assert exc_info.value.reset_time == "2026-11-02 00:00:00 UTC"


def test_batched_retry_budget_transient_503(http):
    replies, seen = http
    err503_1 = urllib.error.HTTPError(
        compile_llm.API_URL, 503, "Service Unavailable", {}, io.BytesIO(b"overloaded 1")
    )
    err503_2 = urllib.error.HTTPError(
        compile_llm.API_URL, 503, "Service Unavailable", {}, io.BytesIO(b"overloaded 2")
    )
    replies.extend([err503_1, err503_2, chat(json.dumps(BATCH_VALID_REPLY))])
    atoms = compile_tender_batched(BATCH_TENDER)
    assert len(atoms) == 2
    assert len(seen) == 3


def test_batched_retry_budget_exhaustion(http):
    replies, seen = http
    err503 = urllib.error.HTTPError(
        compile_llm.API_URL, 503, "Service Unavailable", {}, io.BytesIO(b"overloaded")
    )
    replies.extend([err503] * 3)
    with pytest.raises(CompileError, match="after 3 attempts"):
        compile_tender_batched(BATCH_TENDER)
    assert len(seen) == 3


def test_batched_retry_budget_mixed(http):
    replies, seen = http
    err503 = urllib.error.HTTPError(
        compile_llm.API_URL, 503, "Service Unavailable", {}, io.BytesIO(b"overloaded")
    )
    replies.extend([err503, chat("invalid json"), chat(json.dumps(BATCH_VALID_REPLY))])
    atoms = compile_tender_batched(BATCH_TENDER)
    assert len(atoms) == 2


class FakeBedrockCompileClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_bedrock_compile_success(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    valid_reply = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {"reasoningContent": {"reasoningText": {"text": "thinking..."}}},
                    {"text": json.dumps([ATOM])},
                ],
            }
        },
        "stopReason": "end_turn",
    }
    fake = FakeBedrockCompileClient([valid_reply])
    res = compile_llm._call_bedrock("sys", [{"role": "user", "content": "hi"}], client=fake)
    assert json.loads(res) == [ATOM]
    assert fake.calls[0]["modelId"] == compile_llm.BEDROCK_DEFAULT_MODEL
    assert fake.calls[0]["inferenceConfig"] == {"maxTokens": compile_llm.MAX_TOKENS}


def test_bedrock_compile_max_tokens_truncated(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    reply = {
        "output": {"message": {"role": "assistant", "content": [{"text": "truncated"}]}},
        "stopReason": "max_tokens",
    }
    fake = FakeBedrockCompileClient([reply])
    with pytest.raises(compile_llm.InvalidModelOutput, match="stopReason=max_tokens"):
        compile_llm._call_bedrock("sys", [{"role": "user", "content": "hi"}], client=fake)


def test_bedrock_compile_access_denied_no_retry(monkeypatch):
    import botocore.exceptions
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    err = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Account under verification"}},
        "converse",
    )
    fake = FakeBedrockCompileClient([err])
    with pytest.raises(CompileError, match="AccessDeniedException"):
        compile_llm._call_bedrock("sys", [{"role": "user", "content": "hi"}], client=fake)
    assert len(fake.calls) == 1


def test_bedrock_compile_throttling_raises_http503(monkeypatch):
    import botocore.exceptions
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    throttle = botocore.exceptions.ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "converse",
    )
    fake = FakeBedrockCompileClient([throttle])
    with pytest.raises(HTTP503Error, match="ThrottlingException"):
        compile_llm._call_bedrock("sys", [{"role": "user", "content": "hi"}], client=fake)
    assert len(fake.calls) == 1
