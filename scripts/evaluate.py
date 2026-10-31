"""Run label-separated GraphSAGE and heuristic evaluation on P2 data."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from graph.build import build_graph
from graph.evaluation import evaluate_graphsage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="Directory containing graph CSVs and labels.json")
    seeds = parser.add_mutually_exclusive_group()
    seeds.add_argument("--seed", type=int, help="Run one split (default: 42)")
    seeds.add_argument("--seeds", type=int, nargs="+", help="Run and summarize multiple fixed splits")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--hidden-channels", type=int, default=16)
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    graph = build_graph(data_dir)
    selected_seeds = args.seeds if args.seeds is not None else [args.seed if args.seed is not None else 42]
    runs = []
    for seed in selected_seeds:
        result = evaluate_graphsage(
            graph,
            data_dir / "labels.json",
            seed=seed,
            epochs=args.epochs,
            hidden_channels=args.hidden_channels,
        )
        runs.append({
            "seed": seed,
            "test_positive_vendors": result.metrics["gnn"]["test_positive_vendors"],
            "heuristic": result.metrics["baseline"],
            "graphsage": {
                "pr_auc": result.metrics["gnn"]["pr_auc"],
                "precision_at_10": result.metrics["gnn"]["precision_at_10"],
            },
        })

    summary = None
    if len(runs) > 1:
        summary = {}
        for model in ("heuristic", "graphsage"):
            summary[model] = {}
            for metric in ("pr_auc", "precision_at_10"):
                values = [run[model][metric] for run in runs]
                summary[model][metric] = {
                    "mean": round(statistics.fmean(values), 6),
                    "std_population": round(statistics.pstdev(values), 6),
                }
    print(json.dumps({"runs": runs, "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
