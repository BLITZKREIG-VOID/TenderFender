from __future__ import annotations

import datetime
import http.client
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

from rules.ir import Atom, REG_CLASSES, VENDOR_FIELDS, TENDER_FIELDS

# The OpenRouter request pattern below is copied from decision/write.py on purpose: SoT section 4
# forbids one module importing another module's code, so rules/ keeps its own minimal copy.
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
SEED = 42
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 120


class CompileError(Exception):
    """Raised when compilation of a clause or tender fails."""

    pass


class RateLimitDailyExhausted(CompileError):
    """Raised when OpenRouter free tier daily quota is exhausted (HTTP 429)."""

    def __init__(self, message: str, reset_time: str | None = None):
        super().__init__(message)
        self.reset_time = reset_time


class HTTP503Error(CompileError):
    """Raised on transient HTTP 503 Service Unavailable."""

    pass


class InvalidModelOutput(Exception):
    """The model replied, but with truncated or empty content; counts as an invalid attempt."""


def resolve_model() -> str:
    return os.environ.get("RULES_MODEL") or DEFAULT_MODEL


def _http_error_message(code: int, body: str) -> str:
    snippet = body[:500]
    if code == 429:
        return f"OpenRouter HTTP 429: rate-limited (free models have tight limits); wait and rerun. {snippet}"
    if code == 404 and "data policy" in body.lower():
        return (f"OpenRouter HTTP 404 (data policy): enable the free-model data policy in the OpenRouter "
                f"privacy settings. {snippet}")
    return f"OpenRouter HTTP {code}: {snippet}"


def _parse_reset_time(raw_reset: Any) -> str | None:
    if raw_reset is None:
        return None
    raw_str = str(raw_reset).strip()
    if not raw_str:
        return None
    try:
        val = float(raw_str)
        if val > 1e11:
            val /= 1000.0
        if val > 1e8:
            dt = datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    return raw_str


def _parse_daily_rate_limit(headers: Any, body: Any) -> tuple[bool, str | None]:
    """Check if HTTP 429 is due to OpenRouter free-tier daily quota exhaustion."""
    is_daily = False
    reset_val = None

    if headers:
        try:
            rem = None
            if hasattr(headers, "get"):
                rem = headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining")
                reset_val = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
            if rem is not None and str(rem).strip() == "0":
                is_daily = True
        except Exception:
            pass

    parsed_json = None
    if isinstance(body, dict):
        parsed_json = body
    elif isinstance(body, str):
        try:
            parsed_json = json.loads(body)
        except Exception:
            pass

    if isinstance(parsed_json, dict):
        err = parsed_json.get("error") if isinstance(parsed_json.get("error"), dict) else parsed_json
        meta = err.get("metadata") if isinstance(err.get("metadata"), dict) else {}

        limit_source = meta.get("limit_source") or err.get("limit_source") or parsed_json.get("limit_source")
        if limit_source == "openrouter_free_tier_daily":
            is_daily = True

        meta_headers = meta.get("headers") if isinstance(meta.get("headers"), dict) else {}
        meta_rem = meta_headers.get("X-RateLimit-Remaining") or meta_headers.get("x-ratelimit-remaining")
        if meta_rem is not None and str(meta_rem).strip() == "0":
            is_daily = True

        meta_reset = (
            meta_headers.get("X-RateLimit-Reset")
            or meta_headers.get("x-ratelimit-reset")
            or meta.get("X-RateLimit-Reset")
        )
        if meta_reset is not None and reset_val is None:
            reset_val = meta_reset

    if isinstance(body, str):
        if "openrouter_free_tier_daily" in body:
            is_daily = True
        if re.search(r'["\']?X-RateLimit-Remaining["\']?\s*[:=]\s*["\']?0["\']?', body, re.IGNORECASE):
            is_daily = True
        if reset_val is None:
            m = re.search(r'["\']?X-RateLimit-Reset["\']?\s*[:=]\s*["\']?([0-9]+)["\']?', body, re.IGNORECASE)
            if m:
                reset_val = m.group(1)

    reset_str = _parse_reset_time(reset_val)
    return is_daily, reset_str


def _post(request: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(request["url"], data=json.dumps(request["body"]).encode("utf-8"),
                                 headers=request["headers"], method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310 (fixed https URL)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        if exc.code == 429:
            is_daily, reset_str = _parse_daily_rate_limit(exc.headers, body)
            if is_daily:
                msg = (
                    f"OpenRouter HTTP 429: free-tier daily rate limit reached "
                    f"(limit_source=openrouter_free_tier_daily, X-RateLimit-Remaining=0). "
                    f"Run stopped. Quota resets at: {reset_str or 'unknown'}."
                )
                raise RateLimitDailyExhausted(msg, reset_time=reset_str) from exc
        if exc.code == 503:
            raise HTTP503Error(f"OpenRouter HTTP 503 (service unavailable): {body[:500]}") from exc
        raise CompileError(_http_error_message(exc.code, body)) from exc
    except urllib.error.URLError as exc:
        raise CompileError(f"OpenRouter unreachable: {exc.reason}") from exc
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        raise CompileError(f"OpenRouter request failed: {type(exc).__name__}: {exc}") from exc


def _call_api(system: str, messages: list[dict[str, Any]]) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise CompileError("OPENROUTER_API_KEY is not set")

    response = _post({
        "url": API_URL,
        "headers": {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "TenderFender",
        },
        "body": {
            "model": resolve_model(),
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0,
            "seed": SEED,
            "max_tokens": MAX_TOKENS,
        },
    })
    if isinstance(response, dict) and response.get("error"):
        err = response["error"]
        is_daily, reset_str = _parse_daily_rate_limit({}, err)
        if is_daily:
            msg = (
                f"OpenRouter HTTP 429: free-tier daily rate limit reached "
                f"(limit_source=openrouter_free_tier_daily, X-RateLimit-Remaining=0). "
                f"Run stopped. Quota resets at: {reset_str or 'unknown'}."
            )
            raise RateLimitDailyExhausted(msg, reset_time=reset_str)
        err_str = str(err)
        if "503" in err_str:
            raise HTTP503Error(f"OpenRouter returned 503: {err_str[:500]}")
        raise CompileError(f"OpenRouter returned an error: {err_str[:500]}")
    try:
        choice = response["choices"][0]
        text = choice["message"]["content"]
        finish = choice.get("finish_reason")
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise CompileError(f"unexpected OpenRouter response shape: {str(response)[:300]}") from exc
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise CompileError(f"unexpected OpenRouter response shape: {str(response)[:300]}")
    if finish == "length":
        raise InvalidModelOutput(
            f"model output was truncated (finish_reason=length, max_tokens={MAX_TOKENS})")
    if not text.strip():
        raise InvalidModelOutput("model returned empty content")
    return text


SYSTEM_PROMPT = f"""You are a formalization engine converting tender clauses into IR atoms.
Vocabulary:
- Fields:
  - Vendor-level: {list(VENDOR_FIELDS)}
  - Tender-level: {list(TENDER_FIELDS)}
- Operators: [">=", "<=", "==", "in"]
- Value types:
  - numeric: turnover_cr, turnover_lakh, turnover_pct, years_experience, bid_days, emd_pct, emd_amount_lakh, estimated_cost_lakh, turnover_period_years, max_loss_years, solvency_lakh, solvency_pct: number (integer or float)
  - registration_class: string in {list(REG_CLASSES)} (for op "==") or list of strings in {list(REG_CLASSES)} (for op "in")
  - similar_works: object with optional "years" (number) and required "alternatives" list of objects, each having optional "count" (int), "pct" (number), "amount_lakh" (number)
- Atom structure:
  {{"id": "<clause_id>.1", "clause_id": "<clause_id>", "field": "...", "op": "...", "value": ..., "source_text": "..."}}

Rules:
1. Output ONLY a valid JSON array of atom objects. No markdown formatting, no explanations.
2. Atom ids must be sequentially numbered: <clause_id>.1, <clause_id>.2, ...
3. The "source_text" property must match the clause text EXACTLY.
4. Extract ALL applicable conditions: if a clause specifies both a percentage and an amount in Lakhs, or turnover period, emit separate atoms for each condition.
5. If the clause does not specify any conditions on the supported fields, output an empty array [].
"""

MAX_RETRIES = 2


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


BATCH_SYSTEM_PROMPT = f"""You are a formalization engine converting tender clauses into IR atoms.
Vocabulary:
- Fields:
  - Vendor-level: {list(VENDOR_FIELDS)}
  - Tender-level: {list(TENDER_FIELDS)}
- Operators: [">=", "<=", "==", "in"]
- Value types:
  - numeric: turnover_cr, turnover_lakh, turnover_pct, years_experience, bid_days, emd_pct, emd_amount_lakh, estimated_cost_lakh, turnover_period_years, max_loss_years, solvency_lakh, solvency_pct: number (integer or float)
  - registration_class: string in {list(REG_CLASSES)} (for op "==") or list of strings in {list(REG_CLASSES)} (for op "in")
  - similar_works: object with optional "years" (number) and required "alternatives" list of objects, each having optional "count" (int), "pct" (number), "amount_lakh" (number)
- Atom structure:
  {{"id": "<clause_id>.1", "clause_id": "<clause_id>", "field": "...", "op": "...", "value": ..., "source_text": "..."}}

Rules:
1. Output ONLY a valid JSON object mapping each clause_id to an array of its atom objects: {{"CL1": [atoms...], "CL2": [], ...}}. No markdown formatting, no explanations.
2. For each clause, atom ids must be sequentially numbered: <clause_id>.1, <clause_id>.2, ...
3. Each atom's "clause_id" property must match the key for that clause.
4. The "source_text" property must be a verbatim excerpt or full text from that clause.
5. Extract ALL applicable conditions: if a clause specifies both a percentage and an amount in Lakhs, or turnover period, emit separate atoms for each condition.
6. If a clause does not specify any conditions on the supported fields, output an empty array [] for that clause_id.
7. Include every clause_id from the prompt as a key in the output JSON object.
"""


def compile_clause(
    clause_id: str,
    text: str,
    *,
    call: Callable[[str, list[dict[str, Any]]], str] = _call_api,
) -> list[Atom]:
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Clause ID: {clause_id}\nClause Text: {text}"}
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_reply = call(SYSTEM_PROMPT, messages)
        except InvalidModelOutput as e:
            last_error = e
            if attempt < MAX_RETRIES:
                messages[-1] = {
                    "role": "user",
                    "content": f"{messages[-1]['content']}\n\nPrevious reply rejected: {e}. "
                               "Return ONLY a valid JSON array.",
                }
            continue
        raw = raw_reply.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError(f"Expected a JSON array of atoms, got {type(parsed).__name__}")
            atoms: list[Atom] = []
            for i, item in enumerate(parsed):
                if not isinstance(item, dict):
                    raise ValueError(f"Atom at index {i} is not a JSON object")
                atom = Atom.model_validate(item)
                if atom.clause_id != clause_id:
                    raise ValueError(
                        f"Atom clause_id '{atom.clause_id}' does not match expected clause_id '{clause_id}'"
                    )
                if atom.source_text != text:
                    raise ValueError("Atom source_text does not equal clause text exactly")
                atoms.append(atom)

            return atoms

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                messages.append({"role": "assistant", "content": raw_reply})
                messages.append({
                    "role": "user",
                    "content": f"Validation error: {e}. Please fix the issue and return ONLY a valid JSON array.",
                })

    raise CompileError(
        f"Failed to compile clause {clause_id} after {MAX_RETRIES + 1} attempts: {last_error}"
    )


def compile_tender(
    tender: dict[str, Any],
    *,
    call: Callable[[str, list[dict[str, Any]]], str] = _call_api,
) -> list[Atom]:
    all_atoms: list[Atom] = []
    for clause in tender.get("clauses", []):
        atoms = compile_clause(clause["clause_id"], clause["text"], call=call)
        all_atoms.extend(atoms)
    return all_atoms


def compile_tender_batched(
    tender: dict[str, Any],
    *,
    call: Callable[[str, list[dict[str, Any]]], str] = _call_api,
) -> list[Atom]:
    clauses = tender.get("clauses", [])
    if not clauses:
        return []

    clause_map = {c["clause_id"]: c["text"] for c in clauses}
    tender_id = tender.get("tender_id", "unknown")

    lines = [
        f"Tender ID: {tender_id}",
        "Extract IR atoms for each of the following clauses. Return a valid JSON object mapping each clause_id to an array of its atom objects: {\"CL1\": [atoms...], \"CL2\": [], ...}.",
        "",
    ]
    for c in clauses:
        lines.append(f"Clause ID: {c['clause_id']}\nClause Text: {c['text']}\n")
    user_content = "\n".join(lines).strip()

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_content}
    ]

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw_reply = call(BATCH_SYSTEM_PROMPT, messages)
        except RateLimitDailyExhausted:
            raise
        except (InvalidModelOutput, HTTP503Error) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                if isinstance(e, HTTP503Error):
                    pass
                else:
                    messages[-1] = {
                        "role": "user",
                        "content": f"{messages[-1]['content']}\n\nPrevious reply rejected: {e}. "
                                   "Return ONLY a valid JSON object keyed by clause_id.",
                    }
            continue
        except CompileError as e:
            err_str = str(e)
            if "openrouter_free_tier_daily" in err_str or "X-RateLimit-Remaining: 0" in err_str or "X-RateLimit-Remaining=0" in err_str:
                raise RateLimitDailyExhausted(str(e)) from e
            if "503" in err_str:
                last_error = e
                if attempt < MAX_RETRIES:
                    continue
            raise

        raw = raw_reply.strip()
        if raw.startswith("```"):
            code_lines = raw.splitlines()
            if code_lines[0].startswith("```"):
                code_lines = code_lines[1:]
            if code_lines and code_lines[-1].startswith("```"):
                code_lines = code_lines[:-1]
            raw = "\n".join(code_lines).strip()

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected a JSON object keyed by clause_id, got {type(parsed).__name__}")

            for key in parsed:
                if key not in clause_map:
                    raise ValueError(f"Unknown clause_id key in output: '{key}'")

            all_atoms: list[Atom] = []
            for clause in clauses:
                cid = clause["clause_id"]
                ctext = clause["text"]
                ctext_norm = _normalize_whitespace(ctext)

                raw_atoms = parsed.get(cid, [])
                if not isinstance(raw_atoms, list):
                    raise ValueError(f"Expected list of atoms for clause '{cid}', got {type(raw_atoms).__name__}")

                for i, item in enumerate(raw_atoms):
                    if not isinstance(item, dict):
                        raise ValueError(f"Atom at index {i} in clause '{cid}' is not an object")
                    atom = Atom.model_validate(item)
                    if atom.clause_id != cid:
                        raise ValueError(
                            f"Atom clause_id '{atom.clause_id}' does not match key '{cid}'"
                        )
                    if not atom.source_text or not atom.source_text.strip():
                        raise ValueError(f"Atom {atom.id} has empty source_text")
                    src_norm = _normalize_whitespace(atom.source_text)
                    if src_norm not in ctext_norm:
                        raise ValueError(
                            f"Atom {atom.id} source_text is not a substring of clause {cid} text after whitespace normalisation"
                        )
                    all_atoms.append(atom)

            return all_atoms

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                messages.append({"role": "assistant", "content": raw_reply})
                messages.append({
                    "role": "user",
                    "content": f"Validation error: {e}. Please fix the issue and return ONLY a valid JSON object mapping clause_id to atoms.",
                })

    raise CompileError(
        f"Failed to compile tender {tender_id} after {MAX_RETRIES + 1} attempts: {last_error}"
    )
