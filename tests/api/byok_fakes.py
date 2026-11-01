"""Shared fakes for the BYOK tests: runtime-built fake keys and a recording fake HTTP layer (no real network)."""

from __future__ import annotations

import json
from typing import Any, Callable

from api import providers
from api.providers import HttpResponse


def fake_key(provider: str) -> str:
    """Clearly fake keys built at runtime from the detection prefixes (the repo secret grep never matches)."""
    filler = "FAKE0TEST0KEY0" + "x" * 24
    prefix = {
        "openrouter": providers.PREFIX_OPENROUTER + "v1-",
        "anthropic": providers.PREFIX_ANTHROPIC + "api03-",
        "google": providers.PREFIX_GOOGLE,
        "groq": providers.PREFIX_GROQ,
        "xai": providers.PREFIX_XAI,
        "openai": providers.PREFIX_OPENAI_PROJECT,
        "deepseek": "sk" + "-",
        "sk": "sk" + "-",
        "mistral": "",
    }[provider]
    return prefix + filler


def resp(status: int = 200, body: Any = None, headers: dict[str, str] | None = None) -> HttpResponse:
    raw = body if isinstance(body, bytes) else json.dumps(body if body is not None else {}).encode("utf-8")
    return HttpResponse(status, {k.lower(): v for k, v in (headers or {}).items()}, raw)


Handler = Callable[[str, str, dict[str, str], Any], HttpResponse]


class FakeHTTP:
    """Routes (method, url-without-query) to queued responses or a handler; records every call."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], list[HttpResponse | Handler | BaseException]] = {}
        self.calls: list[dict[str, Any]] = []

    def add(self, method: str, url: str, *responses: HttpResponse | Handler | BaseException) -> None:
        self.routes.setdefault((method, url), []).extend(responses)

    def __call__(self, method: str, url: str, headers: dict[str, str], body: bytes | None,
                 timeout: float) -> HttpResponse:
        payload = json.loads(body) if body else None
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": payload,
                           "timeout": timeout})
        base = url.split("?", 1)[0]
        queue = self.routes.get((method, base))
        if not queue:
            raise AssertionError(f"unexpected HTTP call {method} {base}")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            return item(method, url, headers, payload)
        return item

    def bodies(self, url: str) -> list[Any]:
        return [c["body"] for c in self.calls if c["url"].split("?", 1)[0] == url]


def openai_reply(text: str, finish: str = "stop") -> HttpResponse:
    return resp(200, {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]})


def anthropic_reply(text: str, stop: str = "end_turn") -> HttpResponse:
    return resp(200, {"content": [{"type": "text", "text": text}], "stop_reason": stop})


def google_reply(text: str, finish: str = "STOP") -> HttpResponse:
    return resp(200, {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": finish}]})


def chat_url(provider: str, model: str = "") -> str:
    p = providers.PROVIDERS[provider]
    return p.base_url + p.chat_path.format(model=model)


def models_url(provider: str) -> str:
    p = providers.PROVIDERS[provider]
    return p.base_url + p.models_path


def reply_for(provider: str, text: str, model: str = "") -> tuple[str, HttpResponse]:
    """(chat URL, a successful reply carrying `text`) in the provider's own wire format."""
    api = providers.PROVIDERS[provider].api
    if api == "anthropic":
        return chat_url(provider), anthropic_reply(text)
    if api == "google":
        return chat_url(provider, model), google_reply(text)
    return chat_url(provider), openai_reply(text)
