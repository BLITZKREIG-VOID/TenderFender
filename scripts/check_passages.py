#!/usr/bin/env python3
"""Check that every kb/passages/KB-xxx.md excerpt appears in a local source text.

Sources are plain-text files supplied by the user in kb/sources/ (see
kb/sources/README.md). No PDF parsing is done here.

Per passage: PASS (all fragments found, in order), FAIL (a fragment is missing
or out of order) or UNCHECKED (no local source). Exit 1 on any FAIL; with
--strict also on any UNCHECKED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_QUOTES = dict.fromkeys(map(ord, "\"'`\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u00ab\u00bb\u2039\u203a"), None)
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_PREFIX = re.compile(r"^\s*Excerpt\s*\(.*?\)\s*:\s*", re.S)
_GAP = re.compile(r"\u2026|\.{3}")
_PASSAGE_ID = re.compile(r"^KB-\d+$")


def normalise(text: str) -> str:
    """Case-fold, unify dashes, drop quote characters, collapse whitespace."""
    text = text.translate(_DASHES).translate(_QUOTES).casefold()
    return " ".join(text.split())


def passage_body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n.*?\n---\s*\n", raw, re.S)
    body = raw[m.end():] if m else raw
    return _PREFIX.sub("", body, count=1)


def fragments(body: str) -> list[str]:
    return [f for f in (normalise(p) for p in _GAP.split(body)) if f]


def find_source(pid: str, sources_dir: Path, index: dict[str, str]) -> Path | None:
    if pid in index:
        p = sources_dir / index[pid]
        return p if p.is_file() else None
    if sources_dir.is_dir():
        for p in sorted(sources_dir.iterdir()):
            if p.is_file() and p.name.startswith(pid) and p.suffix.lower() != ".md":
                return p
    return None


def first_missing(frags: list[str], source: str) -> str | None:
    pos = 0
    for f in frags:
        i = source.find(f, pos)
        if i < 0:
            return f
        pos = i + len(f)
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kb-dir", type=Path, default=ROOT / "kb" / "passages")
    ap.add_argument("--sources-dir", type=Path, default=ROOT / "kb" / "sources")
    ap.add_argument("--strict", action="store_true", help="also exit 1 on UNCHECKED passages")
    args = ap.parse_args(argv)

    index: dict[str, str] = {}
    index_path = args.sources_dir / "index.json"
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))

    counts = {"PASS": 0, "FAIL": 0, "UNCHECKED": 0}
    for path in sorted(args.kb_dir.glob("KB-*.md")):
        pid = path.stem
        if not _PASSAGE_ID.match(pid):
            continue
        src = find_source(pid, args.sources_dir, index)
        if src is None:
            status, detail = "UNCHECKED", "no local source"
        else:
            frags = fragments(passage_body(path))
            if not frags:
                status, detail = "FAIL", f"no excerpt text found ({src.name})"
            else:
                missing = first_missing(frags, normalise(src.read_text(encoding="utf-8", errors="replace")))
                if missing is None:
                    status, detail = "PASS", f"{len(frags)} fragment(s) found in {src.name}"
                else:
                    shown = missing if len(missing) <= 80 else missing[:77] + "..."
                    status, detail = "FAIL", f"{src.name}: first missing fragment: {shown!r}"
        counts[status] += 1
        print(f"{pid}  {status:<9}  {detail}")

    print(f"SUMMARY: {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['UNCHECKED']} UNCHECKED "
          f"(UNCHECKED = not verified against a source)")
    if counts["FAIL"] or (args.strict and counts["UNCHECKED"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
