from __future__ import annotations

import http.client
import json
import os
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


def _post(request: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(request["url"], data=json.dumps(request["body"]).encode("utf-8"),
                                 headers=request["headers"], method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310 (fixed https URL)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CompileError(_http_error_message(exc.code, exc.read().decode("utf-8", "replace"))) from exc
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
        raise CompileError(f"OpenRouter returned an error: {str(response['error'])[:500]}")
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
  - turnover_cr, years_experience, bid_days, emd_pct: number (integer or float)
  - registration_class: string in {list(REG_CLASSES)} (for op "==") or list of strings in {list(REG_CLASSES)} (for op "in")
- Atom structure:
  {{"id": "<clause_id>.1", "clause_id": "<clause_id>", "field": "...", "op": "...", "value": ..., "source_text": "..."}}

Rules:
1. Output ONLY a valid JSON array of atom objects. No markdown formatting, no explanations.
2. Atom ids must be sequentially numbered: <clause_id>.1, <clause_id>.2, ...
3. The "source_text" property must match the clause text EXACTLY.
4. If the clause does not specify any conditions on the supported fields, output an empty array [].
"""

MAX_RETRIES = 2


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
        try:
            parsed = json.loads(raw_reply)
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
