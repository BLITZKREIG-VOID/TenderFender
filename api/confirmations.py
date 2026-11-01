"""
Persistent auditor decisions on formalized atoms.

File shape (JSON)::

    {tender_id: {atom_id: {"status": "confirmed" | "rejected", "note": str, "at": ISO8601}}}

Location: env ``CONFIRMATIONS_PATH`` (read on every call), default
``<repo>/data/real/confirmations.json``. Writes are atomic (temp file in the same
directory + ``os.replace``). Concurrency: a process-wide ``threading.Lock`` only; the
API is a single process (uvicorn dev server or one Lambda execution environment).
Two API processes sharing one file can lose each other's updates.

Lambda: the package directory is read-only, so ``CONFIRMATIONS_PATH`` points at ``/tmp``.
On first use the file there is seeded from the packaged default file. ``/tmp`` is
per-execution-environment and ephemeral; the committed file is the source of truth.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = ("confirmed", "rejected")
_LOCK = threading.Lock()


class ConfirmationsError(Exception):
    """Raised when the confirmations file cannot be read or written."""

    def __init__(self, message: str, code: str, status: int):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def default_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "real" / "confirmations.json"


def confirmations_path() -> Path:
    env = os.environ.get("CONFIRMATIONS_PATH")
    return Path(env) if env else default_path()


def _readonly(path: Path, exc: OSError) -> ConfirmationsError:
    return ConfirmationsError(
        f"Confirmations file {path} is not writable ({exc.strerror or exc}); decision not saved",
        "confirmations_readonly",
        503,
    )


def _read_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfirmationsError(
            f"Cannot read confirmations file {path}: {exc.strerror or exc}", "confirmations_unreadable", 500
        ) from exc
    except ValueError as exc:
        raise ConfirmationsError(
            f"Confirmations file {path} is not valid JSON: {exc}", "confirmations_corrupt", 500
        ) from exc
    if not isinstance(data, dict):
        raise ConfirmationsError(
            f"Confirmations file {path} must contain a JSON object", "confirmations_corrupt", 500
        )
    return data


def _load_locked() -> dict[str, Any]:
    """Read the store; seed it from the packaged default on first use. Caller holds the lock."""
    path = confirmations_path()
    if path.is_file():
        return _read_file(path)
    seed = default_path()
    if seed != path and seed.is_file():
        data = _read_file(seed)  # validate before copying
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(seed, path)
        except OSError:
            pass  # reads still work from the seed contents; a later write reports 503 if the path is unwritable
        return data
    return {}


def _write_locked(data: dict[str, Any]) -> None:
    path = confirmations_path()
    tmp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, path)
    except OSError as exc:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise _readonly(path, exc) from exc


def load_tender(tender_id: str) -> dict[str, dict[str, Any]]:
    with _LOCK:
        return dict(_load_locked().get(tender_id, {}))


def set_status(tender_id: str, atom_id: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    entry = {
        "status": status,
        "note": note,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with _LOCK:
        data = _load_locked()
        tender = data.setdefault(tender_id, {})
        tender[atom_id] = entry
        _write_locked(data)
    return entry


def atom_status(tender_id: str, atom_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Per-atom state for the tender's current atoms; atoms with no record are ``undecided``."""
    stored = load_tender(tender_id)
    return {
        aid: stored[aid] if aid in stored else {"status": "undecided", "note": "", "at": None}
        for aid in atom_ids
    }


def formalization_status(statuses: dict[str, dict[str, Any]]) -> str:
    """``confirmed`` only when there is at least one atom and every atom is confirmed."""
    if statuses and all(s["status"] == "confirmed" for s in statuses.values()):
        return "confirmed"
    return "unconfirmed"
