"""CLI: python -m fusion.run --rules-dir ... --graph ... --data-dir ... --out-dir ...

Reads files only (decoupling rule, SoT 4)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from fusion.fuse import fuse


class InputError(Exception):
    pass


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise InputError(f"missing input file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON in {path}: {exc}") from exc


def _csv_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise InputError(f"missing input file: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _title(tender_id: str, data_dir: Path) -> str:
    tender_file = data_dir / "tenders" / f"{tender_id}.json"
    if tender_file.is_file():
        return _load_json(tender_file)["title"]
    for row in _csv_rows(data_dir / "tenders.csv"):
        if row["tender_id"] == tender_id:
            return row["title"]
    raise InputError(f"no title for {tender_id}: not in {tender_file} nor {data_dir / 'tenders.csv'}")


def run(rules_dir: Path, graph_path: Path, data_dir: Path, out_dir: Path) -> list[Path]:
    if not rules_dir.is_dir():
        raise InputError(f"missing rules directory: {rules_dir}")
    rules_files = sorted(rules_dir.glob("T-*.json"))
    if not rules_files:
        raise InputError(f"no T-*.json files in {rules_dir}")
    graph = _load_json(graph_path)
    bids = _csv_rows(data_dir / "bids.csv")

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for rf in rules_files:
        rules = _load_json(rf)
        tender_id = rules["tender_id"]
        if rf.stem != tender_id:
            raise InputError(f"{rf} contains tender_id {tender_id}")
        bidders = {b["vendor_id"] for b in bids if b["tender_id"] == tender_id}
        record = fuse(rules, graph, bidders, _title(tender_id, data_dir))
        out = out_dir / f"{tender_id}.json"
        out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out)
        print(f"fusion {tender_id}: risk={record['risk_level']} decision={record['decision']} -> {out}")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fusion.run")
    ap.add_argument("--rules-dir", type=Path, required=True)
    ap.add_argument("--graph", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        run(args.rules_dir, args.graph, args.data_dir, args.out_dir)
    except InputError as exc:
        print(f"fusion error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
