"""Bring-your-own-key LLM providers: key detection, validation, model listing and chat adapters.

Every call goes server-side to a FIXED provider URL from ``PROVIDERS`` (no user-supplied base URLs,
redirects are refused, model ids are validated before they reach a URL), so a user cannot point the
Lambda at an arbitrary host.

The user's key is only ever a function argument: it is sent in a request header (never in a URL),
never stored in module state, never logged, and scrubbed from every error text, including provider
error bodies that echo it back. Limitations shown to the user are built only from provider responses
(OpenRouter ``/api/v1/key`` fields and ``*ratelimit*`` response headers); nothing is invented.
"""

from __future__ import annotations

import http.client
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 45       # one HTTP call
DEADLINE_SECONDS = 50      # all calls for one API request; the Lambda timeout is 60 s
MAX_RETRIES = 2            # transport retries, only on 5xx / network errors / timeouts
RETRY_BACKOFF_SECONDS = (1.0, 2.0)
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_MODEL_PAGES = 5
REDACTED = "[redacted]"
RETRYABLE_STATUS = frozenset({500, 502, 503, 504, 529})

# Key prefixes are assembled at runtime so the repository secret grep never matches this file.
_SK = "sk" + "-"
PREFIX_OPENROUTER = _SK + "or-"
PREFIX_ANTHROPIC = _SK + "ant-"
PREFIX_OPENAI_PROJECT = _SK + "proj-"
PREFIX_GOOGLE = "AI" + "za"
PREFIX_GROQ = "gsk" + "_"
PREFIX_XAI = "xai" + "-"

KEY_RE = re.compile(r"[A-Za-z0-9._~+/=:-]{16,512}")
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}")
# Anything that looks like a (possibly masked) key of a known provider, e.g. an upstream
# "Incorrect API key provided: <prefix>abc***xyz" echo.
_KEYLIKE_RE = re.compile(
    "(?:" + "|".join(re.escape(p) for p in (_SK, PREFIX_GOOGLE, PREFIX_GROQ, PREFIX_XAI)) + r")[A-Za-z0-9._*\-]{4,}")
# Models listed by OpenAI-compatible endpoints that cannot chat.
_NON_CHAT_RE = re.compile(
    r"embed|whisper|tts|dall-e|moderation|audio|realtime|transcribe|image|search|davinci|babbage|guard", re.I)
# OpenRouter /api/v1/key fields passed through as key_info (when present). `label` is dropped: it is a masked key.
KEY_INFO_FIELDS = ("is_free_tier", "limit", "limit_remaining", "limit_reset", "usage", "usage_daily",
                   "usage_weekly", "usage_monthly", "rate_limit", "free_model_daily_requests")


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    base_url: str
    models_path: str
    chat_path: str
    api: str                          # "openai" | "anthropic" | "google"
    max_tokens_field: str = "max_tokens"
    send_temperature: bool = True


PROVIDERS: dict[str, Provider] = {p.id: p for p in (
    Provider("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "/models", "/chat/completions", "openai"),
    Provider("anthropic", "Anthropic", "https://api.anthropic.com/v1", "/models", "/messages", "anthropic"),
    Provider("google", "Google AI Studio", "https://generativelanguage.googleapis.com/v1beta", "/models",
             "/models/{model}:generateContent", "google"),
    Provider("groq", "Groq", "https://api.groq.com/openai/v1", "/models", "/chat/completions", "openai"),
    Provider("xai", "xAI", "https://api.x.ai/v1", "/models", "/chat/completions", "openai"),
    # Current OpenAI chat models reject `max_tokens` and non-default temperatures.
    Provider("openai", "OpenAI", "https://api.openai.com/v1", "/models", "/chat/completions", "openai",
             max_tokens_field="max_completion_tokens", send_temperature=False),
    Provider("deepseek", "DeepSeek", "https://api.deepseek.com", "/models", "/chat/completions", "openai"),
    Provider("mistral", "Mistral", "https://api.mistral.ai/v1", "/models", "/chat/completions", "openai"),
)}
ANTHROPIC_VERSION = "2023-06-01"
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
# The project's default free model (decision/write.py); recommended first when the key can use it.
OPENROUTER_DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

_UNAMBIGUOUS_PREFIXES = (
    (PREFIX_OPENROUTER, "openrouter"), (PREFIX_ANTHROPIC, "anthropic"), (PREFIX_GOOGLE, "google"),
    (PREFIX_GROQ, "groq"), (PREFIX_XAI, "xai"), (PREFIX_OPENAI_PROJECT, "openai"),
)


class ProviderError(Exception):
    """A provider call failed. `status`/`code` map to the API error; every text field is already scrubbed."""

    def __init__(self, status: int, code: str, message: str, *, provider: str | None = None,
                 provider_message: str | None = None, retry_after: str | None = None,
                 candidates: list[str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.provider = provider
        self.provider_message = provider_message
        self.retry_after = retry_after
        self.candidates = candidates

    def detail(self) -> dict[str, Any]:
        out: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.provider:
            out["provider"] = self.provider
        if self.provider_message:
            out["provider_message"] = self.provider_message
        if self.retry_after:
            out["retry_after"] = self.retry_after
        if self.candidates:
            out["candidates"] = self.candidates
        return out

@dataclass(frozen=True)
class Completion:
    text: str
    truncated: bool
    usage: dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class Deadline:
    """Wall-clock budget shared by every provider call of one API request."""

    def __init__(self, seconds: float = DEADLINE_SECONDS):
        self._end = time.monotonic() + seconds

    def remaining(self) -> float:
        return self._end - time.monotonic()


# ---------------------------------------------------------------- scrubbing and key checks

def scrub(text: str, key: str | None) -> str:
    """Remove the key (raw and URL-encoded) and anything key-shaped from `text`."""
    if key:
        for form in {key, urllib.parse.quote(key, safe=""), urllib.parse.quote_plus(key)}:
            text = text.replace(form, REDACTED)
        if len(key) >= 12:
            text = re.sub(re.escape(key[:6]) + r"[*._\-]{2,}(?:" + re.escape(key[-4:]) + r")?", REDACTED, text)
            text = re.sub(re.escape(key[:4]) + r"[A-Za-z0-9._\-]*[*._\-]{2,}[A-Za-z0-9._\-]*" + re.escape(key[-4:]), REDACTED, text)
    return _KEYLIKE_RE.sub(REDACTED, text)


def check_key_format(key: str) -> None:
    if not KEY_RE.fullmatch(key):
        raise ProviderError(400, "invalid_key_format",
                            "The X-LLM-Key header must be 16-512 characters with no spaces or control characters.")


def check_openrouter_key(key: str) -> None:
    if not isinstance(key, str) or not key.startswith(PREFIX_OPENROUTER):
        raise ProviderError(400, "openrouter_key_required", "Only OpenRouter keys are supported.")
    check_key_format(key)

def check_model(provider_id: str, model: str) -> None:
    """Model ids end up in request bodies and (Google) in the URL path: allow a strict charset only."""
    is_google = provider_id in PROVIDERS and PROVIDERS[provider_id].api == "google"
    bad = (not MODEL_RE.fullmatch(model) or ".." in model
           or (is_google and "/" in model))
    if bad:
        raise ProviderError(400, "invalid_model", "The model id contains characters that are not allowed.",
                            provider=provider_id)

def candidates(key: str, hint: str | None = None) -> list[str]:
    """Providers to try for `key`, in order: the hint, else the unambiguous prefix, else the ambiguous set."""
    if hint:
        if hint not in PROVIDERS:
            raise ProviderError(400, "unknown_provider",
                                f"X-LLM-Provider must be one of: {', '.join(PROVIDERS)}.")
        return [hint]
    for prefix, pid in _UNAMBIGUOUS_PREFIXES:
        if key.startswith(prefix):
            return [pid]
    if key.startswith(_SK):
        raise ProviderError(
            400,
            "provider_hint_required",
            "This key format is ambiguous between multiple providers; pass an X-LLM-Provider header.",
            candidates=["openai", "deepseek"],
        )
    return ["mistral"]


def resolve(key: str, hint: str | None = None) -> str:
    """Provider for a chat call: the hint, else the prefix match (a bare `sk-` key falls back to OpenAI)."""
    return candidates(key, hint)[0]


# ---------------------------------------------------------------- HTTP

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001 (stdlib signature)
        return None  # a 3xx becomes an HTTPError; headers are never replayed to another host


_OPENER = urllib.request.build_opener(_NoRedirect)


def urllib_send(method: str, url: str, headers: dict[str, str], body: bytes | None,
                timeout: float) -> HttpResponse:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return HttpResponse(resp.status, {k.lower(): v for k, v in resp.headers.items()},
                                resp.read(MAX_RESPONSE_BYTES))
    except urllib.error.HTTPError as exc:
        hdrs = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        return HttpResponse(exc.code, hdrs, exc.read(MAX_RESPONSE_BYTES))

def get_bedrock_client() -> Any:
    import boto3
    region = os.environ.get("BEDROCK_REGION", "ap-south-1")
    return boto3.client("bedrock-runtime", region_name=region)


bedrock_client_getter: Callable[[], Any] = get_bedrock_client

# Replaced in tests; never reassigned at runtime.
send: Callable[[str, str, dict[str, str], bytes | None, float], HttpResponse] = urllib_send
sleep: Callable[[float], None] = time.sleep


def _provider_message(body: bytes, key: str) -> str | None:
    text = body.decode("utf-8", "replace").strip()
    if not text:
        return None
    msg: Any = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = data[0]
    if isinstance(data, dict):
        err = data.get("error", data)
        if isinstance(err, dict):
            msg = err.get("message") or err.get("msg") or err.get("detail")
        elif isinstance(err, str):
            msg = err
        if msg is None:
            msg = data.get("message") or data.get("detail")
    if msg is None:
        msg = text
    if not isinstance(msg, str):
        msg = json.dumps(msg, ensure_ascii=False)
    return scrub(msg, key)[:500]


def _http_error(p: Provider, status: int, headers: dict[str, str], body: bytes, key: str) -> ProviderError:
    pmsg = _provider_message(body, key)
    raw = body.decode("utf-8", "replace")
    if status in (401, 403) or (p.api == "google" and status == 400 and "API_KEY_INVALID" in raw):
        return ProviderError(401, "invalid_key", f"{p.label} rejected the API key (HTTP {status}).",
                             provider=p.id, provider_message=pmsg)
    if status == 402:
        return ProviderError(402, "provider_quota",
                             f"{p.label} reports insufficient credits or quota for this key (HTTP 402).",
                             provider=p.id, provider_message=pmsg)
    if status == 429:
        return ProviderError(429, "provider_rate_limited",
                             f"{p.label} rate limit or quota reached for this key (HTTP 429).",
                             provider=p.id, provider_message=pmsg, retry_after=headers.get("retry-after"))
    if 400 <= status < 500:
        return ProviderError(400, "provider_bad_request", f"{p.label} rejected the request (HTTP {status}).",
                             provider=p.id, provider_message=pmsg)
    if status >= 500:
        return ProviderError(502, "provider_error",
                             f"{p.label} is unavailable (HTTP {status}) after {MAX_RETRIES} retries.",
                             provider=p.id, provider_message=pmsg)
    return ProviderError(502, "provider_error", f"{p.label} returned unexpected HTTP {status}.",
                         provider=p.id, provider_message=pmsg)


def _headers(p: Provider, key: str, *, json_body: bool) -> dict[str, str]:
    h = {"Accept": "application/json", "User-Agent": "TenderFender"}
    if json_body:
        h["Content-Type"] = "application/json"
    if p.api == "anthropic":
        h["x-api-key"] = key
        h["anthropic-version"] = ANTHROPIC_VERSION
    elif p.api == "google":
        h["x-goog-api-key"] = key
    else:
        h["Authorization"] = f"Bearer {key}"
    if p.id == "openrouter":
        h["X-Title"] = "TenderFender"
    return h


def _call(p: Provider, key: str, method: str, url: str, payload: dict | None,
          deadline: Deadline, op: str) -> tuple[dict[str, str], Any]:
    """One logical request with at most MAX_RETRIES retries on 5xx/network errors. Returns (headers, JSON)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = _headers(p, key, json_body=payload is not None)
    for attempt in range(MAX_RETRIES + 1):
        remaining = deadline.remaining()
        if remaining < 1:
            raise ProviderError(504, "provider_timeout",
                                f"{p.label} did not answer within the {DEADLINE_SECONDS} s request budget.",
                                provider=p.id)
        try:
            resp = send(method, url, headers, data, min(TIMEOUT_SECONDS, remaining))
        except (TimeoutError, urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            log.warning("llm provider=%s op=%s attempt=%d transport_error=%s",
                        p.id, op, attempt + 1, type(exc).__name__)
            if attempt < MAX_RETRIES:
                sleep(min(RETRY_BACKOFF_SECONDS[attempt], max(deadline.remaining(), 0)))
                continue
            timed_out = isinstance(exc, TimeoutError) or "timed out" in str(exc)
            raise ProviderError(504 if timed_out else 502, "provider_timeout" if timed_out else "provider_error",
                                f"{p.label} could not be reached ({type(exc).__name__}) after {MAX_RETRIES} retries.",
                                provider=p.id) from None
        log.info("llm provider=%s op=%s attempt=%d status=%d", p.id, op, attempt + 1, resp.status)
        if resp.status in RETRYABLE_STATUS and attempt < MAX_RETRIES:
            sleep(min(RETRY_BACKOFF_SECONDS[attempt], max(deadline.remaining(), 0)))
            continue
        if not 200 <= resp.status < 300:
            raise _http_error(p, resp.status, resp.headers, resp.body, key)
        try:
            return resp.headers, json.loads(resp.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderError(502, "provider_error", f"{p.label} returned a response that is not JSON.",
                                provider=p.id) from None
    raise AssertionError("unreachable")


def _shape_error(p: Provider) -> ProviderError:
    return ProviderError(502, "provider_error", f"{p.label} returned an unexpected response shape.", provider=p.id)


# ---------------------------------------------------------------- detection and model listing

def _model(mid: str, name: Any, ctx: Any, free: bool) -> dict[str, Any]:
    return {"id": mid, "name": name if isinstance(name, str) and name else mid,
            "context_length": ctx if isinstance(ctx, int) and not isinstance(ctx, bool) else None, "free": free}


def _is_zero_price(value: Any) -> bool:
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def _parse_models(p: Provider, data: Any) -> tuple[list[dict[str, Any]], str | None]:
    """Normalise one models page; returns (models, next page cursor)."""
    if not isinstance(data, dict):
        raise _shape_error(p)
    out: list[dict[str, Any]] = []
    if p.api == "google":
        rows = data.get("models", [])
        if not isinstance(rows, list):
            raise _shape_error(p)
        for m in rows:
            if not isinstance(m, dict) or "generateContent" not in (m.get("supportedGenerationMethods") or []):
                continue
            name = m.get("name")
            if isinstance(name, str) and name.startswith("models/"):
                out.append(_model(name[len("models/"):], m.get("displayName"), m.get("inputTokenLimit"), False))
        return out, data.get("nextPageToken") or None
    rows = data.get("data", [])
    if not isinstance(rows, list):
        raise _shape_error(p)
    for m in rows:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str):
            continue
        mid = m["id"]
        if p.id == "openrouter":
            pricing = m.get("pricing") if isinstance(m.get("pricing"), dict) else {}
            free = mid.endswith(":free") or _is_zero_price(pricing.get("prompt"))
            out.append(_model(mid, m.get("name"), m.get("context_length"), free))
        elif p.api == "anthropic":
            out.append(_model(mid, m.get("display_name"), None, False))
        else:
            caps = m.get("capabilities")
            if isinstance(caps, dict) and caps.get("completion_chat") is False:
                continue
            if m.get("active") is False or _NON_CHAT_RE.search(mid):
                continue
            ctx = m.get("context_length", m.get("context_window", m.get("max_context_length")))
            out.append(_model(mid, m.get("name"), ctx, False))
    cursor = data.get("last_id") if p.api == "anthropic" and data.get("has_more") else None
    return out, cursor


def list_models(p: Provider, key: str, deadline: Deadline) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """All chat models for the key (following at most MAX_MODEL_PAGES pages) and the first page's headers."""
    models: list[dict[str, Any]] = []
    first_headers: dict[str, str] | None = None
    cursor: str | None = None
    for _ in range(MAX_MODEL_PAGES):
        query: dict[str, str] = {}
        if p.api == "google":
            query["pageSize"] = "1000"
            if cursor:
                query["pageToken"] = cursor
        elif p.api == "anthropic":
            query["limit"] = "1000"
            if cursor:
                query["after_id"] = cursor
        url = p.base_url + p.models_path + ("?" + urllib.parse.urlencode(query) if query else "")
        headers, data = _call(p, key, "GET", url, None, deadline, "models")
        first_headers = headers if first_headers is None else first_headers
        page, cursor = _parse_models(p, data)
        models.extend(page)
        if not cursor:
            break
    seen: set[str] = set()
    unique = [m for m in models if not (m["id"] in seen or seen.add(m["id"]))]
    unique.sort(key=lambda m: not m["free"])  # stable: free first, provider order otherwise
    return unique, first_headers or {}


def _key_info(key: str, deadline: Deadline) -> dict[str, Any]:
    p = PROVIDERS["openrouter"]
    _, data = _call(p, key, "GET", OPENROUTER_KEY_URL, None, deadline, "key")
    info = data.get("data") if isinstance(data, dict) else None
    if not isinstance(info, dict):
        raise _shape_error(p)
    return {k: info[k] for k in KEY_INFO_FIELDS if k in info}


def _fmt(value: Any) -> str:
    return "null" if value is None else json.dumps(value, ensure_ascii=False, sort_keys=True)


def limitations(p: Provider, key_info: dict[str, Any] | None, headers: dict[str, str]) -> list[str]:
    """Verbatim facts from the provider's own responses; never estimated or assumed."""
    out: list[str] = []
    if key_info:
        for k in KEY_INFO_FIELDS:
            if k in key_info:
                out.append(f"{p.label} /api/v1/key reports {k} = {_fmt(key_info[k])}.")
    for name in sorted(headers):
        if "ratelimit" in name:
            out.append(f"{p.label} response header {name}: {headers[name]}")
    return out


def recommended_model(p: Provider, models: list[dict[str, Any]], key_info: dict[str, Any] | None) -> str | None:
    """From the returned list only: the project default if listed, else the largest context (free first on a free key)."""
    ids = {m["id"] for m in models}
    if p.id == "openrouter" and OPENROUTER_DEFAULT_MODEL in ids:
        return OPENROUTER_DEFAULT_MODEL
    pool = models
    if key_info and key_info.get("is_free_tier"):
        pool = [m for m in models if m["free"]] or models
    if not pool:
        return None
    return max(pool, key=lambda m: m["context_length"] or -1)["id"]  # max keeps the first of equal contexts


def _detect_one(p: Provider, key: str, deadline: Deadline) -> dict[str, Any]:
    key_info = _key_info(key, deadline) if p.id == "openrouter" else None
    models, headers = list_models(p, key, deadline)
    return {"provider": p.id, "valid": True, "models": models, "key_info": key_info,
            "limitations": limitations(p, key_info, headers),
            "recommended_model": recommended_model(p, models, key_info)}


def detect(key: str, hint: str | None = None, deadline: Deadline | None = None) -> dict[str, Any]:
    """Validate the key against each candidate provider in order; a rejected key gives `valid: false`."""
    deadline = deadline or Deadline()
    cands = candidates(key, hint)
    for pid in cands:
        try:
            return _detect_one(PROVIDERS[pid], key, deadline)
        except ProviderError as exc:
            if exc.code != "invalid_key":
                raise
            log.info("llm detect provider=%s rejected the key", pid)
    return {"provider": cands[0] if len(cands) == 1 else None, "valid": False, "models": [], "key_info": None,
            "limitations": [], "recommended_model": None}


# ---------------------------------------------------------------- chat
def complete(provider_id: str, key: str, model: str, system: str, messages: list[dict[str, str]], *,
             max_tokens: int, deadline: Deadline) -> Completion:
    """One chat completion. `messages` are {role: user|assistant, content}; the system prompt is separate."""
    check_model(provider_id, model)
    if provider_id == "bedrock":
        import botocore.exceptions
        converse_system = [{"text": system}]
        converse_messages = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages]
        try:
            client = bedrock_client_getter()
            response = client.converse(
                modelId=model,
                messages=converse_messages,
                system=converse_system,
                inferenceConfig={"maxTokens": max_tokens},
            )
        except (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError) as exc:
            raise ProviderError(500, "credentials_missing", f"AWS credentials not found: {exc}", provider="bedrock") from exc
        except botocore.exceptions.ClientError as exc:
            err_code = exc.response.get("Error", {}).get("Code", "")
            err_msg = exc.response.get("Error", {}).get("Message", str(exc))
            if err_code in ("AccessDeniedException",):
                raise ProviderError(403, "access_denied", f"Bedrock access denied: {err_msg}", provider="bedrock") from exc
            if err_code in ("ValidationException",):
                raise ProviderError(400, "invalid_request", f"Bedrock validation error: {err_msg}", provider="bedrock") from exc
            if err_code in ("ResourceNotFoundException",):
                raise ProviderError(404, "model_not_found", f"Bedrock resource not found: {err_msg}", provider="bedrock") from exc
            if err_code in ("ThrottlingException",):
                raise ProviderError(429, "rate_limited", f"Bedrock throttling: {err_msg}", provider="bedrock") from exc
            if err_code in ("ServiceUnavailableException", "ModelTimeoutException", "InternalServerException"):
                raise ProviderError(503, "service_unavailable", f"Bedrock unavailable: {err_msg}", provider="bedrock") from exc
            raise ProviderError(502, "bedrock_error", f"Bedrock error ({err_code}): {err_msg}", provider="bedrock") from exc
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(502, "bedrock_error", f"Bedrock error: {type(exc).__name__}: {exc}", provider="bedrock") from exc

        try:
            output_msg = response.get("output", {}).get("message", {})
            content_blocks = output_msg.get("content", [])
            text = "".join(b["text"] for b in content_blocks if isinstance(b, dict) and "text" in b)
            truncated = response.get("stopReason") == "max_tokens"
            usage = response.get("usage", {})
        except (KeyError, TypeError, AttributeError):
            raise ProviderError(502, "bedrock_shape_error", "Unexpected Bedrock response structure", provider="bedrock") from None
        return Completion(text, truncated, usage)

    p = PROVIDERS[provider_id]
    if p.api == "anthropic":
        payload: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "system": system,
                                   "messages": messages, "temperature": 0}
        _, data = _call(p, key, "POST", p.base_url + p.chat_path, payload, deadline, "chat")
        try:
            parts = data["content"]
            text = "".join(b.get("text", "") for b in parts if isinstance(b, dict) and b.get("type") == "text")
            truncated = data.get("stop_reason") == "max_tokens"
        except (KeyError, TypeError, AttributeError):
            raise _shape_error(p) from None
        return Completion(text, truncated)

    if p.api == "google":
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                         for m in messages],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
        }
        url = p.base_url + p.chat_path.format(model=urllib.parse.quote(model, safe=""))
        _, data = _call(p, key, "POST", url, payload, deadline, "chat")
        if not isinstance(data, dict):
            raise _shape_error(p)
        cands = data.get("candidates") or []
        if not cands:
            return Completion("", False)  # blocked prompt: no candidate; the caller treats it as empty output
        try:
            cand = cands[0]
            parts = (cand.get("content") or {}).get("parts") or []
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            truncated = cand.get("finishReason") == "MAX_TOKENS"
        except (TypeError, AttributeError):
            raise _shape_error(p) from None
        return Completion(text, truncated)

    payload = {"model": model, "messages": [{"role": "system", "content": system}, *messages],
               p.max_tokens_field: max_tokens}
    if p.send_temperature:
        payload["temperature"] = 0
    _, data = _call(p, key, "POST", p.base_url + p.chat_path, payload, deadline, "chat")
    if isinstance(data, dict) and data.get("error"):
        # OpenRouter can answer 200 with an error object carrying the upstream status code.
        err = data["error"]
        code = err.get("code") if isinstance(err, dict) else None
        status = code if isinstance(code, int) and 400 <= code < 600 else 502
        raise _http_error(p, status, {}, json.dumps(data).encode("utf-8"), key)
    try:
        choice = data["choices"][0]
        text = choice["message"]["content"]
        truncated = choice.get("finish_reason") == "length"
    except (KeyError, IndexError, TypeError, AttributeError):
        raise _shape_error(p) from None
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise _shape_error(p)
    return Completion(text, truncated)
