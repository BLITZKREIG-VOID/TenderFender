"""
Reader for guideline passages (``kb/passages/KB-xxx.md``).

Format: see ``kb/passages/README.md`` (a ``---`` front matter block with
``passage_id``, ``source_title``, ``source_url``, ``section``, ``retrieved``,
``topics: [a, b]`` followed by the excerpt body).  This is a deliberately small,
independent parser: the API does not import ``decision/``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_ID_RE = re.compile(r"^KB-\d{3}$")


def kb_dir() -> Path:
    """Passage directory: ``$KB_DIR`` if set, else ``<project root>/kb/passages``."""
    env = os.environ.get("KB_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "kb" / "passages"


def _parse_topics(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


def parse_passage(text: str) -> dict[str, Any] | None:
    """Parse passage markdown; returns ``None`` if the front matter is malformed."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    if not meta.get("passage_id"):
        return None
    return {
        "passage_id": meta["passage_id"],
        "source_title": meta.get("source_title", ""),
        "source_url": meta.get("source_url", ""),
        "section": meta.get("section", ""),
        "retrieved": meta.get("retrieved", ""),
        "topics": _parse_topics(meta.get("topics", "")),
        "text": "\n".join(lines[end + 1:]).strip(),
    }


def load_passage(passage_id: str) -> dict[str, Any]:
    """Return the passage entry, or ``{"passage_id": ..., "missing": True}`` if unavailable."""
    missing: dict[str, Any] = {"passage_id": passage_id, "missing": True}
    if not _ID_RE.match(passage_id):
        return missing
    path = kb_dir() / f"{passage_id}.md"
    try:
        parsed = parse_passage(path.read_text(encoding="utf-8"))
    except OSError:
        return missing
    if parsed is None or parsed["passage_id"] != passage_id:
        return missing
    return parsed
