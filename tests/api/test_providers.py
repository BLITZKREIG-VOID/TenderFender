"""api/providers.py: detection, validation, model listing, chat adapters, retries and key scrubbing.

Every provider is mocked at the HTTP layer (providers.send); real network access fails the test."""

from __future__ import annotations

import json
import logging
import urllib.request

import pytest

from api import providers
from api.providers import ProviderError
from tests.api.byok_fakes import (FakeHTTP, anthropic_reply, chat_url, fake_key, google_reply, models_url,
                                  openai_reply, resp)

OR_KEY_URL = providers.OPENROUTER_KEY_URL
ALL_PROVIDERS = ("openrouter", "anthropic", "google", "groq", "xai", "openai", "deepseek", "mistral")


@pytest.fixture(autouse=True)
def http(monkeypatch):
    fake = FakeHTTP()
    monkeypatch.setattr(providers, "send", fake)
    monkeypatch.setattr(providers, "sleep", lambda s: None)

    def no_network(*a, **k):
        raise AssertionError("real network access in a test")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(providers._OPENER, "open", no_network)
    return fake


def deadline():
    return providers.Deadline(60)


# ── detection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,expected", [
    ("openrouter", ["openrouter"]), ("anthropic", ["anthropic"]), ("google", ["google"]), ("groq", ["groq"]),
    ("xai", ["xai"]), ("openai", ["openai"]), ("mistral", ["mistral"]),
])
def test_candidates_by_prefix(name, expected):
    assert providers.candidates(fake_key(name)) == expected


def test_candidates_ambiguous_sk_key_requires_hint():
    with pytest.raises(providers.ProviderError) as exc:
        providers.candidates(fake_key("sk"))
    assert exc.value.status == 400
    assert exc.value.code == "provider_hint_required"
    assert exc.value.candidates == ["openai", "deepseek"]


def test_hint_overrides_prefix_and_must_be_known():
    assert providers.candidates(fake_key("sk"), "deepseek") == ["deepseek"]
    assert providers.candidates(fake_key("sk"), "openai") == ["openai"]
    assert providers.resolve(fake_key("sk"), "openai") == "openai"
    with pytest.raises(ProviderError) as exc:
        providers.candidates(fake_key("sk"), "https://evil.example")
    assert exc.value.status == 400 and exc.value.code == "unknown_provider"

def test_source_has_no_literal_key_prefixes():
    src = open(providers.__file__, encoding="utf-8").read()
    assert ("sk" + "-or-") not in src and ("sk" + "-ant") not in src


@pytest.mark.parametrize("bad", ["short", "has space " + "x" * 20, "line\nbreak" + "x" * 20, "x" * 513, "ключ" * 8])
def test_key_format_rejected_without_echo(bad):
    with pytest.raises(ProviderError) as exc:
        providers.check_key_format(bad)
    assert exc.value.code == "invalid_key_format" and bad not in json.dumps(exc.value.detail())


def test_check_openrouter_key_valid():
    key = fake_key("openrouter")
    providers.check_openrouter_key(key)


@pytest.mark.parametrize("bad", [
    fake_key("anthropic"),
    fake_key("google"),
    fake_key("sk"),
    "short",
    "garbage_key_string",
])
def test_check_openrouter_key_non_openrouter_rejected(bad):
    with pytest.raises(ProviderError) as exc:
        providers.check_openrouter_key(bad)
    assert exc.value.status == 400
    assert exc.value.code == "openrouter_key_required"
    assert exc.value.message == "Only OpenRouter keys are supported."
    assert bad not in json.dumps(exc.value.detail())

def test_all_urls_are_fixed_https():
    for p in providers.PROVIDERS.values():
        assert p.base_url.startswith("https://") and "{" not in p.base_url


@pytest.mark.parametrize("model", ["../../v1/files", "a b", "x" * 300, "", "m?x=1", "m#frag"])
def test_check_model_rejects_unsafe_ids(model):
    with pytest.raises(ProviderError) as exc:
        providers.check_model("openai", model)
    assert exc.value.code == "invalid_model"


def test_check_model_google_rejects_slash():
    providers.check_model("openrouter", "meta-llama/llama-3:free")
    with pytest.raises(ProviderError):
        providers.check_model("google", "gemini/../../x")


# ── detect: one test per provider ────────────────────────────────────────────

def test_detect_openrouter_key_info_models_and_limitations(http):
    key = fake_key("openrouter")
    http.add("GET", OR_KEY_URL, resp(200, {"data": {
        "label": key[:12] + "...abc", "is_free_tier": True, "limit": None, "usage": 0.5, "limit_remaining": None,
        "rate_limit": {"requests": 20, "interval": "10s"}}}))
    http.add("GET", models_url("openrouter"), resp(200, {"data": [
        {"id": "paid/model", "name": "Paid", "context_length": 200000, "pricing": {"prompt": "0.000003"}},
        {"id": "small/free", "name": "Small free", "context_length": 8000, "pricing": {"prompt": "0"}},
        {"id": providers.OPENROUTER_DEFAULT_MODEL, "name": "Nemotron", "context_length": 131072,
         "pricing": {"prompt": "0"}},
    ]}, headers={"X-RateLimit-Limit": "20"}))
    out = providers.detect(key)
    assert out["provider"] == "openrouter" and out["valid"] is True
    assert out["key_info"] == {"is_free_tier": True, "limit": None, "usage": 0.5, "limit_remaining": None,
                               "rate_limit": {"requests": 20, "interval": "10s"}}
    assert [m["id"] for m in out["models"]] == ["small/free", providers.OPENROUTER_DEFAULT_MODEL, "paid/model"]
    assert [m["free"] for m in out["models"]] == [True, True, False]
    assert out["recommended_model"] == providers.OPENROUTER_DEFAULT_MODEL
    assert "OpenRouter /api/v1/key reports is_free_tier = true." in out["limitations"]
    assert 'OpenRouter /api/v1/key reports rate_limit = {"interval": "10s", "requests": 20}.' in out["limitations"]
    assert "OpenRouter response header x-ratelimit-limit: 20" in out["limitations"]
    assert all(c["headers"]["Authorization"] == f"Bearer {key}" for c in http.calls)
    assert key not in json.dumps(out)


def test_detect_openrouter_free_tier_recommends_largest_free_model(http):
    http.add("GET", OR_KEY_URL, resp(200, {"data": {"is_free_tier": True}}))
    http.add("GET", models_url("openrouter"), resp(200, {"data": [
        {"id": "big/paid", "context_length": 1000000, "pricing": {"prompt": "0.1"}},
        {"id": "a/free:free", "context_length": 32000, "pricing": {"prompt": "0.1"}},
        {"id": "b/free", "context_length": 64000, "pricing": {"prompt": 0}},
    ]}))
    out = providers.detect(fake_key("openrouter"))
    assert out["recommended_model"] == "b/free"
    assert out["limitations"] == ["OpenRouter /api/v1/key reports is_free_tier = true."]


def test_detect_anthropic_follows_pages_and_sends_version_header(http):
    key = fake_key("anthropic")
    url = models_url("anthropic")
    http.add("GET", url,
             resp(200, {"data": [{"id": "claude-new", "display_name": "Claude New"}], "has_more": True,
                        "last_id": "claude-new"}, headers={"anthropic-ratelimit-requests-limit": "50"}),
             resp(200, {"data": [{"id": "claude-old", "display_name": "Claude Old"}], "has_more": False}))
    out = providers.detect(key)
    assert out["provider"] == "anthropic" and out["key_info"] is None
    assert [m["id"] for m in out["models"]] == ["claude-new", "claude-old"]
    assert out["recommended_model"] == "claude-new"
    assert out["limitations"] == ["Anthropic response header anthropic-ratelimit-requests-limit: 50"]
    assert "after_id=claude-new" in http.calls[1]["url"]
    for c in http.calls:
        assert c["headers"]["x-api-key"] == key and c["headers"]["anthropic-version"] == "2023-06-01"
        assert "Authorization" not in c["headers"]


def test_detect_google_key_in_header_never_in_url(http):
    key = fake_key("google")
    http.add("GET", models_url("google"), resp(200, {"models": [
        {"name": "models/gemini-pro", "displayName": "Gemini Pro", "inputTokenLimit": 1048576,
         "supportedGenerationMethods": ["generateContent", "countTokens"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
    ]}))
    out = providers.detect(key)
    assert out["provider"] == "google"
    assert out["models"] == [{"id": "gemini-pro", "name": "Gemini Pro", "context_length": 1048576, "free": False}]
    assert http.calls[0]["headers"]["x-goog-api-key"] == key
    assert key not in http.calls[0]["url"]


@pytest.mark.parametrize("name,rows,expected", [
    ("groq", [{"id": "llama-3.3-70b", "context_window": 131072, "active": True},
              {"id": "whisper-large-v3", "active": True}, {"id": "retired", "active": False}], ["llama-3.3-70b"]),
    ("xai", [{"id": "grok-4"}, {"id": "grok-2-image"}], ["grok-4"]),
    ("openai", [{"id": "gpt-4.1"}, {"id": "text-embedding-3-small"}, {"id": "tts-1"}], ["gpt-4.1"]),
    ("mistral", [{"id": "mistral-large", "max_context_length": 131072, "capabilities": {"completion_chat": True}},
                 {"id": "mistral-embed", "capabilities": {"completion_chat": False}}], ["mistral-large"]),
])
def test_detect_openai_compatible_providers(http, name, rows, expected):
    http.add("GET", models_url(name), resp(200, {"object": "list", "data": rows}))
    out = providers.detect(fake_key(name))
    assert out["provider"] == name and out["valid"] is True
    assert [m["id"] for m in out["models"]] == expected
    assert out["recommended_model"] == expected[0]
    assert http.calls[0]["headers"]["Authorization"].startswith("Bearer ")


def test_detect_ambiguous_key_requires_hint():
    with pytest.raises(providers.ProviderError) as exc:
        providers.detect(fake_key("sk"))
    assert exc.value.status == 400
    assert exc.value.code == "provider_hint_required"
    assert exc.value.candidates == ["openai", "deepseek"]


def test_detect_ambiguous_key_with_hint(http):
    http.add("GET", models_url("deepseek"), resp(200, {"data": [{"id": "deepseek-chat", "object": "model"}]}))
    out = providers.detect(fake_key("sk"), "deepseek")
    assert out["provider"] == "deepseek" and out["valid"] is True
    assert [c["url"] for c in http.calls] == [models_url("deepseek")]

def test_detect_google_invalid_key_400(http):
    http.add("GET", models_url("google"), resp(400, {"error": {
        "code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT",
        "details": [{"reason": "API_KEY_INVALID"}]}}))
    out = providers.detect(fake_key("google"))
    assert out["valid"] is False and out["provider"] == "google"


def test_detect_quota_error_is_raised_not_swallowed(http):
    http.add("GET", OR_KEY_URL, resp(402, {"error": {"code": 402, "message": "Insufficient credits"}}))
    with pytest.raises(ProviderError) as exc:
        providers.detect(fake_key("openrouter"))
    assert exc.value.status == 402 and exc.value.code == "provider_quota"
    assert exc.value.provider_message == "Insufficient credits"


# ── chat adapters ────────────────────────────────────────────────────────────

MSGS = [{"role": "user", "content": "q1"}, {"role": "assistant", "content": "a1"}, {"role": "user", "content": "q2"}]


@pytest.mark.parametrize("name", ["openrouter", "groq", "xai", "deepseek", "mistral"])
def test_complete_openai_compatible(http, name):
    http.add("POST", chat_url(name), openai_reply("hello"))
    out = providers.complete(name, fake_key(name), "m-1", "SYS", MSGS, max_tokens=100, deadline=deadline())
    assert out == providers.Completion("hello", False)
    body = http.calls[0]["body"]
    assert body["messages"] == [{"role": "system", "content": "SYS"}, *MSGS]
    assert body["model"] == "m-1" and body["max_tokens"] == 100 and body["temperature"] == 0


def test_complete_openai_uses_max_completion_tokens(http):
    http.add("POST", chat_url("openai"), openai_reply("x", finish="length"))
    out = providers.complete("openai", fake_key("openai"), "gpt-x", "S", MSGS, max_tokens=50, deadline=deadline())
    assert out.truncated is True
    body = http.calls[0]["body"]
    assert body["max_completion_tokens"] == 50 and "max_tokens" not in body and "temperature" not in body


def test_complete_anthropic_messages_api(http):
    http.add("POST", chat_url("anthropic"), anthropic_reply("hi", stop="max_tokens"))
    out = providers.complete("anthropic", fake_key("anthropic"), "claude-x", "SYS", MSGS, max_tokens=64,
                             deadline=deadline())
    assert out == providers.Completion("hi", True)
    body = http.calls[0]["body"]
    assert body["system"] == "SYS" and body["messages"] == MSGS and body["max_tokens"] == 64


def test_complete_google_generate_content(http):
    key = fake_key("google")
    http.add("POST", chat_url("google", "gemini-pro"), google_reply("ok", finish="MAX_TOKENS"))
    out = providers.complete("google", key, "gemini-pro", "SYS", MSGS, max_tokens=32, deadline=deadline())
    assert out == providers.Completion("ok", True)
    call = http.calls[0]
    assert call["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    assert key not in call["url"] and call["headers"]["x-goog-api-key"] == key
    assert call["body"]["systemInstruction"] == {"parts": [{"text": "SYS"}]}
    assert [c["role"] for c in call["body"]["contents"]] == ["user", "model", "user"]
    assert call["body"]["generationConfig"]["maxOutputTokens"] == 32


def test_complete_google_blocked_prompt_is_empty(http):
    http.add("POST", chat_url("google", "g"), resp(200, {"promptFeedback": {"blockReason": "SAFETY"}}))
    out = providers.complete("google", fake_key("google"), "g", "S", MSGS, max_tokens=8, deadline=deadline())
    assert out == providers.Completion("", False)


def test_complete_unexpected_shape_is_502(http):
    http.add("POST", chat_url("groq"), resp(200, {"nope": 1}))
    with pytest.raises(ProviderError) as exc:
        providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert exc.value.status == 502 and exc.value.code == "provider_error"


def test_openrouter_200_with_error_object_maps_status(http):
    http.add("POST", chat_url("openrouter"), resp(200, {"error": {"code": 429, "message": "Rate limit exceeded: free"}}))
    with pytest.raises(ProviderError) as exc:
        providers.complete("openrouter", fake_key("openrouter"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert exc.value.status == 429 and exc.value.provider_message == "Rate limit exceeded: free"


# ── errors, retries, timeouts ────────────────────────────────────────────────

@pytest.mark.parametrize("status,code,api_status", [
    (401, "invalid_key", 401), (403, "invalid_key", 401), (402, "provider_quota", 402),
    (429, "provider_rate_limited", 429), (404, "provider_bad_request", 400), (400, "provider_bad_request", 400),
])
def test_http_errors_map_to_clear_codes_without_retry(http, status, code, api_status):
    http.add("POST", chat_url("groq"), resp(status, {"error": {"message": f"upstream says {status}"}},
                                             headers={"Retry-After": "7"}))
    with pytest.raises(ProviderError) as exc:
        providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert (exc.value.status, exc.value.code) == (api_status, code)
    assert exc.value.provider_message == f"upstream says {status}" and exc.value.provider == "groq"
    assert len(http.calls) == 1
    if status == 429:
        assert exc.value.detail()["retry_after"] == "7"


def test_5xx_retried_at_most_twice(http):
    http.add("POST", chat_url("groq"), resp(503, {"error": "busy"}))
    with pytest.raises(ProviderError) as exc:
        providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert exc.value.status == 502 and len(http.calls) == 1 + providers.MAX_RETRIES


def test_5xx_then_success(http):
    http.add("POST", chat_url("groq"), resp(500, {}), openai_reply("fine"))
    out = providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert out.text == "fine" and len(http.calls) == 2


def test_timeouts_retried_then_504(http):
    http.add("POST", chat_url("groq"), TimeoutError("timed out"))
    with pytest.raises(ProviderError) as exc:
        providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=deadline())
    assert exc.value.status == 504 and exc.value.code == "provider_timeout"
    assert len(http.calls) == 3
    assert all(c["timeout"] <= providers.TIMEOUT_SECONDS for c in http.calls)


def test_exhausted_deadline_makes_no_call(http):
    with pytest.raises(ProviderError) as exc:
        providers.complete("groq", fake_key("groq"), "m", "S", MSGS, max_tokens=8, deadline=providers.Deadline(0))
    assert exc.value.status == 504 and http.calls == []


def test_redirects_are_refused():
    handler = providers._NoRedirect()
    assert handler.redirect_request(None, None, 302, "Found", {}, "https://elsewhere.example/") is None


# ── key scrubbing ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ALL_PROVIDERS)
def test_key_never_in_errors_or_logs(http, caplog, name):
    caplog.set_level(logging.DEBUG)
    key = fake_key("sk" if name == "deepseek" else name)
    masked = key[:10] + "****" + key[-4:]
    echo = {"error": {"message": f"Incorrect API key provided: {key} (also {masked})"}}
    p = providers.PROVIDERS[name]
    model = "m-1"
    http.add("GET", OR_KEY_URL, resp(401, echo))
    http.add("GET", models_url(name), resp(403, echo))
    http.add("POST", chat_url(name, model), resp(429, echo))
    with pytest.raises(ProviderError) as chat_exc:
        providers.complete(name, key, model, "S", MSGS, max_tokens=8, deadline=deadline())
    detected = providers.detect(key, name)
    texts = [json.dumps(chat_exc.value.detail()), str(chat_exc.value), json.dumps(detected), caplog.text]
    for text in texts:
        assert key not in text and masked not in text
    assert providers.REDACTED in chat_exc.value.provider_message
    assert p.label in chat_exc.value.message


def test_scrub_handles_raw_encoded_and_keylike():
    key = fake_key("mistral")
    assert providers.scrub(f"a {key} b", key) == f"a {providers.REDACTED} b"
    other = fake_key("groq")
    assert other not in providers.scrub(f"x {other[:12]}***", None)
