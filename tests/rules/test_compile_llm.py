from __future__ import annotations

import json
import pytest

from rules.compile_llm import CompileError, _call_api, compile_clause


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


def test_missing_anthropic_api_key_raises_compile_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(CompileError, match="Missing ANTHROPIC_API_KEY"):
        _call_api("system prompt", [{"role": "user", "content": "hi"}])
