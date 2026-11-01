#!/usr/init/env python3
# -*- coding: utf-8 -*-
"""Convert a raw real-tender text file into data/real/tenders/RT-xxx.json (contracts/schemas/real_tender.json).

Raw format: see data/real/raw/README.md (five `key: value` header lines, a `---` line, then the eligibility
section pasted verbatim). Deterministic, no LLM: clauses are split on the document's own numbering and the
text is kept verbatim apart from whitespace normalisation.

Usage: python scripts/import_tender.py data/real/raw/RT-001.txt [--out-dir data/real/tenders] [--force]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
HEADER_KEYS = ("title", "source_portal", "source_url", "source_ref", "retrieved")
TENDER_ID_RE = re.compile(r"^RT-\d{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CLAUSE_START_RE = re.compile(r"^\s*(\d+(?:\.\d+)*(?:\([a-z0-9]+\))*|\([a-z]\)|[a-z]\))[.)]?\s")
TABLE_LIKE_RE = re.compile(r"\t|\||\S {3,}\S.* {3,}\S")
MAX_CLAUSE_CHARS = 1200
ROMAN_NUMERALS = frozenset(("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"))


class ImportError_(Exception):
    pass


def parse_raw(raw: str) -> tuple[dict[str, str], list[str]]:
    """Return (header, body_lines). Raises ImportError_ on any format problem."""
    lines = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    try:
        sep = next(i for i, line in enumerate(lines) if line.strip() == "---")
    except StopIteration:
        raise ImportError_("no '---' separator line between header and body") from None
    header: dict[str, str] = {}
    for line in lines[:sep]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ImportError_(f"bad header line (expected 'key: value'): {line!r}")
        key, value = (s.strip() for s in line.split(":", 1))
        if key not in HEADER_KEYS:
            raise ImportError_(f"unknown header key {key!r}; allowed: {', '.join(HEADER_KEYS)}")
        if key in header:
            raise ImportError_(f"duplicate header key {key!r}")
        header[key] = value
    missing = [k for k in HEADER_KEYS if not header.get(k)]
    if missing:
        raise ImportError_(f"missing or empty header keys: {', '.join(missing)}")
    if not DATE_RE.match(header["retrieved"]):
        raise ImportError_(f"retrieved must be YYYY-MM-DD, got {header['retrieved']!r}")
    url = urlparse(header["source_url"])
    if url.scheme not in ("http", "https") or not url.netloc:
        raise ImportError_(f"source_url must be an http(s) URL, got {header['source_url']!r}")
    body = lines[sep + 1:]
    if not any(line.strip() for line in body):
        raise ImportError_("empty body after the '---' line")
    return header, body


def split_clauses(body: list[str]) -> list[dict]:
    """Split body lines on the document's own numbering. Text is verbatim except whitespace normalisation."""
    groups: list[dict] = []  # {"no": str, "lines": [raw lines]}
    for line in body:
        matched_no = None
        s = line.strip()

        # Check details table rows
        if " | " in s:
            m_table = re.match(r"^([a-z0-9]+(?:\.\d+)*|\([ivxlc0-9]+\)|[a-z])\b", s, re.I)
            if m_table:
                matched_no = m_table.group(1)

        # Check standalone criteria letters/sections like "a", "b", "I", "II"
        if matched_no is None:
            m_crit = re.match(r"^([a-jA-J]|[I|V|X]+)[.\)]?\s*$", s)
            if m_crit:
                val = m_crit.group(1)
                if val.lower() not in ROMAN_NUMERALS:
                    matched_no = val

        # Check standard clause numbering
        if matched_no is None:
            m = CLAUSE_START_RE.match(line)
            if m:
                val = m.group(1)
                if val.lower() not in ROMAN_NUMERALS:
                    matched_no = val

        if matched_no is not None:
            groups.append({"no": matched_no, "lines": [line]})
        elif line.strip():
            if not groups:
                groups.append({"no": "", "lines": []})  # text before any number
            groups[-1]["lines"].append(line)

    counts: dict[str, int] = {}
    for g in groups:
        if g["no"]:
            counts[g["no"]] = counts.get(g["no"], 0) + 1

    clauses = []
    for i, g in enumerate(groups, start=1):
        text = " ".join(" ".join(g["lines"]).split())
        review = (
            not g["no"]
            or counts.get(g["no"], 0) > 1
            or len(text) > MAX_CLAUSE_CHARS
            or any(TABLE_LIKE_RE.search(line) for line in g["lines"])
        )
        clause = {"clause_id": f"CL{i}", "source_clause_no": g["no"], "text": text}
        if review:
            clause["needs_review"] = True
        clauses.append(clause)
    return clauses


def build_tender(raw_path: Path) -> dict:
    tender_id = raw_path.stem
    if not TENDER_ID_RE.match(tender_id):
        raise ImportError_(f"file name must be RT-NNN.txt (tender_id ^RT-\\d{{3}}$), got {raw_path.name!r}")
    header, body = parse_raw(raw_path.read_text(encoding="utf-8"))
    tender = {"tender_id": tender_id, **{k: header[k] for k in HEADER_KEYS}, "clauses": split_clauses(body)}
    schema = json.loads((REPO_ROOT / "contracts" / "schemas" / "real_tender.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message[:200]}"
              for e in Draft202012Validator(schema).iter_errors(tender)]
    if errors:
        raise ImportError_("output does not match real_tender.json:\n  " + "\n  ".join(errors))
    return tender


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import a raw real-tender text file into RT-xxx.json")
    ap.add_argument("raw", type=Path, help="raw text file, e.g. data/real/raw/RT-001.txt")
    ap.add_argument("--out-dir", type=Path, default=Path("data/real/tenders"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing RT-xxx.json")
    args = ap.parse_args(argv)

    try:
        tender = build_tender(args.raw)
    except (ImportError_, OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"Error: {args.raw}: {exc}\n")
        return 1

    out = args.out_dir / f"{tender['tender_id']}.json"
    if out.exists() and not args.force:
        sys.stderr.write(f"Error: {out} exists; pass --force to overwrite\n")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tender, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    flagged = [c["clause_id"] for c in tender["clauses"] if c.get("needs_review")]
    print(f"{tender['tender_id']}: {len(tender['clauses'])} clauses, needs_review={len(flagged)} {flagged} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
