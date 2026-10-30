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


def load_rules(tender_id: str) -> dict[str, Any] | None:
    """Load the rule-checker output for a given tender."""
    return load_json(f"rules/{tender_id}.json")


def load_graph() -> dict[str, Any] | None:
    """Load the graph analysis output."""
    return load_json("graph/graph_output.json")


def load_fused(tender_id: str) -> dict[str, Any] | None:
    """Load the fused decision output for a given tender."""
    return load_json(f"fused/{tender_id}.json")


def list_fused_ids() -> list[str]:
    """Return a sorted list of tender IDs available in the fused directory."""
    fused_dir = _base_dir() / "fused"
    if not fused_dir.is_dir():
        return []
    return sorted(
        p.stem for p in fused_dir.glob("T-*.json")
    )

