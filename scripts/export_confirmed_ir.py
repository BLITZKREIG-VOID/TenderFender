"""Export the auditor-confirmed IR for a real tender.

    python scripts/export_confirmed_ir.py RT-001 [--ir PATH] [--confirmations PATH] [--out PATH]

Reads the IR the compiler cached for the tender (default ``data/real/tenders/ir_<id>.json``, written by
``python -m rules.run --write-cache``) and the confirmations file (env ``CONFIRMATIONS_PATH``, default
``data/real/confirmations.json``). Exit 1, listing them, if any atom is undecided or rejected. When every
atom is confirmed, writes

* ``ir_<id>.confirmed.json``       the atoms as a JSON array, same format ``rules.run`` / ``rules.ir.load_atoms`` read;
* ``ir_<id>.confirmed.meta.json``  ``{"confirmed": true, "tender_id", "confirmed_at", "source_ir_sha256", "atoms": {...}}``.

(The metadata is a separate file because the cache loader requires a bare array of atoms.) Idempotent: ``confirmed_at``
is the latest per-atom confirmation time, so re-running on unchanged inputs rewrites byte-identical files.
Rejected atoms must be fixed in the IR file by hand and then re-confirmed in the UI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from api.confirmations import confirmations_path  # noqa: E402
from rules.ir import load_atoms  # noqa: E402


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tender_id", help="e.g. RT-001")
    ap.add_argument("--ir", help="cached IR (default data/real/tenders/ir_<id>.json)")
    ap.add_argument("--confirmations", help="confirmations file (default: $CONFIRMATIONS_PATH or data/real/confirmations.json)")
    ap.add_argument("--out", help="confirmed IR output (default: sibling ir_<id>.confirmed.json)")
    args = ap.parse_args(argv)

    tid = args.tender_id
    ir_path = Path(args.ir) if args.ir else REPO_ROOT / "data" / "real" / "tenders" / f"ir_{tid}.json"
    conf_path = Path(args.confirmations) if args.confirmations else confirmations_path()
    out_path = Path(args.out) if args.out else ir_path.with_name(f"ir_{tid}.confirmed.json")
    meta_path = out_path.with_suffix(".meta.json")

    if not ir_path.is_file():
        print(f"error: IR file not found: {ir_path} (run: python -m rules.run --data-dir data/real --tender {tid} --write-cache)", file=sys.stderr)
        return 2
    try:
        atoms = load_atoms(ir_path)
    except Exception as exc:
        print(f"error: cannot load IR {ir_path}: {exc}", file=sys.stderr)
        return 2
    if not atoms:
        print(f"error: {ir_path} contains no atoms; nothing to confirm", file=sys.stderr)
        return 1

    store: dict = {}
    if conf_path.is_file():
        try:
            store = json.loads(conf_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"error: {conf_path} is not valid JSON: {exc}", file=sys.stderr)
            return 2
    decided = store.get(tid, {}) if isinstance(store, dict) else {}

    problems = []
    for atom in atoms:
        status = decided.get(atom.id, {}).get("status", "undecided")
        if status != "confirmed":
            note = decided.get(atom.id, {}).get("note", "")
            problems.append(f"  {atom.id} [{status}]{' note: ' + note if note else ''}")
    if problems:
        print(f"{tid}: {len(problems)} of {len(atoms)} atoms are not confirmed:", file=sys.stderr)
        print("\n".join(problems), file=sys.stderr)
        print("Fix rejected atoms in the IR file, then re-confirm them in the UI; confirm undecided ones.", file=sys.stderr)
        return 1

    per_atom = {a.id: decided[a.id] for a in atoms}
    meta = {
        "confirmed": True,
        "tender_id": tid,
        "confirmed_at": max(e["at"] for e in per_atom.values()),
        "source_ir_sha256": hashlib.sha256(ir_path.read_bytes()).hexdigest(),
        "atoms": per_atom,
    }
    _atomic_write(out_path, json.dumps([a.model_dump() for a in atoms], indent=2, ensure_ascii=False) + "\n")
    _atomic_write(meta_path, json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{tid}: all {len(atoms)} atoms confirmed -> {out_path}, {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
