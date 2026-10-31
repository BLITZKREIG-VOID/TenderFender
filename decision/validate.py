"""Citation and wording validation for decision text (SoT 8.4 RAG rules)."""

from __future__ import annotations

import re

# Every reference-like token, case-insensitive, including malformed ones (KB-12, KB-0042, kb-004,
# R-01, F-1a). Each must then be an exact member of the allowed set; nothing is silently ignored.
REF_RE = re.compile(r"(?<![A-Za-z0-9])(?:KB|F|R)-\d+[A-Za-z0-9]*", re.I)

# Wording rule (SoT 1): risk indicators only, never conclusions of guilt/illegality.
# `corrupt` is matched as a whole word so that official titles containing
# "Corruption" (e.g. an Act's name) are not rejected.
FORBIDDEN_PATTERNS = [
    re.compile(r"\bcorrupt\b", re.I),
    re.compile(r"\bguilty\b", re.I),
    re.compile(r"\bproves?\s+(?:the\s+)?illegal\w*", re.I),
    re.compile(r"\b(?:is|are|was|were|committed|constitutes?)\s+(?:a\s+|an\s+)?fraud(?:ulent)?\b", re.I),
]


class DecisionValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def extract_refs(text: str) -> list[str]:
    return REF_RE.findall(text)


def ref_kind(ref: str) -> str:
    if ref.startswith("KB-"):
        return "guideline"
    if ref.startswith("F-"):
        return "finding"
    if ref.startswith("R-"):
        return "ring"
    raise ValueError(f"unknown ref prefix: {ref}")


def _ref_sort_key(ref: str) -> tuple[int, int]:
    order = {"guideline": 0, "finding": 1, "ring": 2}
    return (order[ref_kind(ref)], int(ref.split("-", 1)[1]))


def validate_decision(text_fields: dict, allowed_refs: set[str], placeholder_ids: set[str]) -> list[dict]:
    """Validate `{"reasoning": str, "recommended_actions": [str]}`.

    Returns the citations list derived from refs found in the text (never trusted
    from the LLM). Raises DecisionValidationError listing every problem found."""
    errors: list[str] = []
    reasoning = text_fields.get("reasoning")
    actions = text_fields.get("recommended_actions")
    if not isinstance(reasoning, str) or not reasoning.strip():
        errors.append("reasoning must be a non-empty string")
        reasoning = ""
    if (not isinstance(actions, list) or not actions
            or not all(isinstance(a, str) and a.strip() for a in actions)):
        errors.append("recommended_actions must be a non-empty list of non-empty strings")
        actions = []

    texts = [reasoning, *actions]
    refs: set[str] = set()
    for t in texts:
        refs.update(extract_refs(t))

    valid: list[str] = []
    for ref in sorted(refs):
        if ref in placeholder_ids:
            errors.append(f"placeholder passage cited: {ref}")
        elif ref not in allowed_refs:
            errors.append("malformed or unknown reference (must exactly match a retrieved passage, "
                          f"finding or ring of this tender): {ref}")
        else:
            valid.append(ref)

    for t in texts:
        for pat in FORBIDDEN_PATTERNS:
            m = pat.search(t)
            if m:
                errors.append(f"forbidden wording: {m.group(0)!r}")

    if errors:
        raise DecisionValidationError(errors)
    return [{"ref": r, "kind": ref_kind(r)} for r in sorted(valid, key=_ref_sort_key)]
