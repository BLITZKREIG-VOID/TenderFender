"""
Loader utilities for the Tender Integrity API.

Reads JSON artifacts from either `mocks/` (when MOCK=1) or `artifacts/` based
on the MOCK environment variable.  All paths are resolved relative to the
project root (one level above the `api/` package).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    """Return the project root directory (parent of the `api/` package)."""
    return Path(__file__).resolve().parent.parent


def is_mock_mode() -> bool:
    """Return True when the API should serve mock data."""
    return os.environ.get("MOCK", "0") == "1"


def _base_dir() -> Path:
    """Return the base directory for data files (mocks/ or artifacts/)."""
    root = _project_root()
    return root / "mocks" if is_mock_mode() else root / "artifacts"


# ── generic loader ────────────────────────────────────────────────────────────


def load_json(relative_path: str) -> dict[str, Any] | list[Any] | None:
    """
    Load and parse a JSON file relative to the current base directory.

    Returns ``None`` if the file does not exist.
    """
    path = _base_dir() / relative_path
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── domain-specific loaders ──────────────────────────────────────────────────


def is_real_id(tender_id: str) -> bool:
    """Real (user-provided) tenders are ``RT-NNN``; synthetic demo tenders are ``T-NNN``."""
    return tender_id.startswith("RT-")


def tender_source(fused: dict[str, Any] | None, tender_id: str) -> str:
    """``real`` | ``synthetic_demo``: the fused tag if present, else derived from the id."""
    if fused and fused.get("source") in ("real", "synthetic_demo"):
        return fused["source"]
    return "real" if is_real_id(tender_id) else "synthetic_demo"


def _safe_id(tender_id: str) -> bool:
    return not ("/" in tender_id or "\\" in tender_id or ".." in tender_id)


def load_rules(tender_id: str) -> dict[str, Any] | None:
    """Load the rule-checker output for a given tender (real tenders: ``artifacts/rules_real/``)."""
    if not _safe_id(tender_id):
        return None
    if is_real_id(tender_id) and not is_mock_mode():
        return load_json(f"rules_real/{tender_id}.json")
    return load_json(f"rules/{tender_id}.json")


def load_graph() -> dict[str, Any] | None:
    """Load the graph analysis output."""
    return load_json("graph/graph_output.json")


def load_fused(tender_id: str) -> dict[str, Any] | None:
    """Load the fused decision output for a given tender."""
    if not _safe_id(tender_id):
        return None
    return load_json(f"fused/{tender_id}.json")


def list_fused_ids() -> list[str]:
    """Return a sorted list of tender IDs (``T-*`` and ``RT-*``) available in the fused directory."""
    fused_dir = _base_dir() / "fused"
    if not fused_dir.is_dir():
        return []
    return sorted(p.stem for p in [*fused_dir.glob("T-*.json"), *fused_dir.glob("RT-*.json")])



def load_real_tender(tender_id: str) -> dict[str, Any] | None:
    """``data/real/tenders/RT-xxx.json`` (None if absent, malformed or not an RT id)."""
    if not (is_real_id(tender_id) and _safe_id(tender_id)):
        return None
    path = _project_root() / "data" / "real" / "tenders" / f"{tender_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load_tender_clauses(tender_id: str) -> list[dict[str, Any]]:
    """Real clause list: ``data/tenders/<id>.json`` (T-) or ``data/real/tenders/<id>.json`` (RT-, with ``source_clause_no``)."""
    if not _safe_id(tender_id):
        return []
    if is_real_id(tender_id):
        data = load_real_tender(tender_id)
        if data is None:
            return []
        return [
            {
                "clause_id": c["clause_id"],
                "text": c.get("text", ""),
                "source_clause_no": c.get("source_clause_no", ""),
                **({"needs_review": c["needs_review"]} if "needs_review" in c else {}),
            }
            for c in data.get("clauses", [])
            if isinstance(c, dict) and "clause_id" in c
        ]
    if not tender_id.startswith("T-"):
        return []
    path = _project_root() / "data" / "tenders" / f"{tender_id}.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [
        {"clause_id": c["clause_id"], "text": c.get("text", "")}
        for c in data.get("clauses", [])
        if isinstance(c, dict) and "clause_id" in c
    ]
