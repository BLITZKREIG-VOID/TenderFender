#!/usr/bin/env python3
"""Phase 4 prep tool: inspect retrieval scores and ranking against KB passages.

Reuses decision.retrieve (load_passages, build_queries, make_retriever, retrieve)
and evaluates top-k candidates for each finding and ring query in intermediate
fusion records (or synthesized from rules + graph).

Exit codes:
  0: Success (tables printed).
  1: Missing or empty KB directory (states 'no passages found in <path>'),
     or missing fusion inputs.
  2: Command-line argument error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct script invocation
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from decision.retrieve import (
    DEFAULT_MIN_SCORE,
    DEFAULT_TOP_K,
    Passage,
    build_queries,
    load_passages,
    make_retriever,
    retrieve,
)


def load_inputs_from_fusion(fusion_dir: Path) -> list[tuple[str, dict]]:
    """Loads (tender_id, inputs) from fusion intermediate JSON files."""
    if not fusion_dir.exists():
        raise FileNotFoundError(f"fusion directory does not exist: {fusion_dir}")

    if fusion_dir.is_file():
        files = [fusion_dir]
    elif fusion_dir.is_dir():
        files = sorted(fusion_dir.glob("T-*.json"))
        if not files:
            files = sorted(fusion_dir.glob("*.json"))
    else:
        raise FileNotFoundError(f"fusion path is not a file or directory: {fusion_dir}")

    if not files:
        raise FileNotFoundError(f"no JSON files found in {fusion_dir}")

    records: list[tuple[str, dict]] = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        tid = data.get("tender_id", f.stem)
        inputs = data.get("_inputs", data)
        records.append((tid, inputs))
    return records


def load_inputs_from_rules_and_graph(rules_dir: Path, graph_file: Path | None) -> list[tuple[str, dict]]:
    """Loads (tender_id, inputs) from rules files and optional graph file."""
    if not rules_dir.is_dir():
        raise FileNotFoundError(f"rules directory does not exist: {rules_dir}")

    rules_files = sorted(rules_dir.glob("T-*.json"))
    if not rules_files:
        rules_files = sorted(rules_dir.glob("*.json"))
    if not rules_files:
        raise FileNotFoundError(f"no JSON files found in {rules_dir}")

    rings: list[dict] = []
    if graph_file and graph_file.is_file():
        gdata = json.loads(graph_file.read_text(encoding="utf-8"))
        try:
            from fusion.fuse import flagged_rings
            rings = flagged_rings(gdata)
        except Exception:
            rings = [r for r in gdata.get("rings", []) if r.get("score", 0.0) >= 0.5]

    records: list[tuple[str, dict]] = []
    for rf in rules_files:
        rdata = json.loads(rf.read_text(encoding="utf-8"))
        tid = rdata.get("tender_id", rf.stem)
        inputs = {"findings": rdata.get("findings", []), "rings": rings}
        records.append((tid, inputs))
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="inspect_retrieval.py",
        description="Inspect top-k retrieved KB passages for finding and ring queries."
    )
    parser.add_argument(
        "--fusion-dir",
        type=Path,
        default=Path("artifacts/fusion"),
        help="intermediate fusion directory or file (default: artifacts/fusion)",
    )
    parser.add_argument(
        "--rules-dir",
        type=Path,
        default=None,
        help="optional rules directory to construct _inputs from rules + graph",
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=None,
        help="optional graph_output.json to construct _inputs with --rules-dir",
    )
    parser.add_argument(
        "--kb-dir",
        type=Path,
        default=Path("kb/passages"),
        help="path to knowledge base passages directory (default: kb/passages)",
    )
    parser.add_argument(
        "--retriever",
        choices=("embedding", "keyword"),
        default="embedding",
        help="retriever implementation to inspect (default: embedding)",
    )
    parser.add_argument(
        "--top",
        "--top-k",
        type=int,
        default=6,
        dest="top",
        help="maximum number of passages to show per query (default: 6)",
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="allow PLACEHOLDER passages (default: False)",
    )
    parser.add_argument(
        "--format",
        choices=("table", "markdown"),
        default="table",
        help="output format: 'table' or 'markdown' (default: table)",
    )
    return parser.parse_args(argv)


def inspect_retrieval(args: argparse.Namespace) -> int:
    passages = load_passages(args.kb_dir)
    if not passages:
        print(f"no passages found in {args.kb_dir}", file=sys.stderr)
        return 1
    if not any(not p.placeholder for p in passages) and not args.allow_placeholder:
        print(
            f"warning: all {len(passages)} passages in {args.kb_dir} are placeholders; "
            "pass --allow-placeholder to include them",
            file=sys.stderr,
        )

    try:
        if args.rules_dir is not None:
            records = load_inputs_from_rules_and_graph(args.rules_dir, args.graph)
        else:
            records = load_inputs_from_fusion(args.fusion_dir)
    except FileNotFoundError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    retriever = make_retriever(args.retriever)
    min_cutoff = DEFAULT_MIN_SCORE[args.retriever]

    # Collect rows across all tenders and queries
    rows: list[dict] = []
    for tid, inputs in records:
        queries = build_queries(inputs)
        if not queries:
            continue

        retrieved = retrieve(
            queries,
            passages,
            retriever,
            top_k=args.top,
            min_score=float("-inf"),
            allow_placeholder=args.allow_placeholder,
        )

        for qk in queries:
            hits = retrieved.get(qk, [])
            for rank, (passage, score) in enumerate(hits, start=1):
                above = "yes" if score >= min_cutoff else "no"
                placeholder = "yes" if passage.placeholder else "no"
                rows.append({
                    "tender": tid,
                    "query": qk,
                    "rank": rank,
                    "passage_id": passage.passage_id,
                    "score": score,
                    "above_min": above,
                    "placeholder": placeholder,
                    "source_title": passage.source_title,
                })

    if args.format == "markdown":
        headers = ["Tender", "Query", "Rank", "Passage ID", "Score", "Above Min", "Placeholder", "Relevant?", "Source Title"]
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for r in rows:
            clean_title = r["source_title"].replace("|", "-")
            print(f"| {r['tender']} | {r['query']} | {r['rank']} | {r['passage_id']} | {r['score']:.4f} | {r['above_min']} | {r['placeholder']} | | {clean_title} |")
    else:
        col_names = ["Tender", "Query", "Rank", "Passage ID", "Score", "Above Min", "Placeholder", "Source Title"]
        data_rows = [
            [
                r["tender"],
                r["query"],
                str(r["rank"]),
                r["passage_id"],
                f"{r['score']:.4f}",
                r["above_min"],
                r["placeholder"],
                r["source_title"],
            ]
            for r in rows
        ]
        if not data_rows:
            print("No queries or passages to display.")
            return 0

        widths = [max(len(str(val)) for val in col) for col in zip(*([col_names] + data_rows))]
        header_line = "  ".join(col.ljust(w) for col, w in zip(col_names, widths))
        sep_line = "  ".join("-" * w for w in widths)
        print(header_line)
        print(sep_line)
        for d in data_rows:
            print("  ".join(str(val).ljust(w) for val, w in zip(d, widths)))

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return inspect_retrieval(args)


if __name__ == "__main__":
    sys.exit(main())
