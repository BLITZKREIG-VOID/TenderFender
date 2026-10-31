from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Callable

from rules.ir import Atom, REG_CLASSES, VENDOR_FIELDS, TENDER_FIELDS

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class CompileError(Exception):
    """Raised when compilation of a clause or tender fails."""

    pass


def _call_api(system: str, messages: list[dict[str, Any]]) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise CompileError("Missing ANTHROPIC_API_KEY environment variable")

    model = os.environ.get("RULES_MODEL", "claude-sonnet-4-5")
    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0,
        "system": system,
        "messages": messages,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "x-api-key": key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        resp_data = json.loads(response.read().decode("utf-8"))
        return resp_data["content"][0]["text"]


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
        raw_reply = call(SYSTEM_PROMPT, messages)
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
