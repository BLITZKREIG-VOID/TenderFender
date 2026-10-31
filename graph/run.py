"""Build and serialize ``artifacts/graph/graph_output.json``."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import networkx as nx

from graph.build import build_graph
from graph.explain import build_display_graph
from graph.screens import RingCandidate, explain_vendors, find_rings


def build_graph_output(
    graph: nx.MultiDiGraph,
    evaluation: Any | None = None,
) -> dict[str, Any]:
    """Return the P2 graph artifact without consulting evaluation labels."""
    rings = find_rings(graph)
    vendor_scores, vendor_explanations = explain_vendors(graph, rings)
    display_graph, paths = build_display_graph(graph, rings)
    ring_rows = [
        {
            "ring_id": f"R-{index}",
            "vendor_ids": list(ring.vendor_ids),
            "link_types": list(ring.link_types),
            "score": round(float(ring.score), 4),
        }
        for index, ring in enumerate(rings, start=1)
    ]

    # Keep the mock-compatible pending shape unless an evaluation completed.
    metrics = {
        "baseline": {"pr_auc": 0.0, "precision_at_10": 0.0},
        "gnn": {"pr_auc": 0.0, "precision_at_10": 0.0},
        "gnn_status": "skipped",
        "note": "experimental GraphSAGE; metrics pending scripts/evaluate.py",
    }
    gnn_vendor_scores: dict[str, float] = {}
    if evaluation is not None:
        metrics = evaluation.metrics
        gnn_vendor_scores = evaluation.vendor_scores
    return {
        "vendor_scores": vendor_scores,
        "gnn_vendor_scores": gnn_vendor_scores,
        "vendor_explanations": vendor_explanations,
        "rings": ring_rows,
        "paths": paths,
        "graph": display_graph,
        "metrics": metrics,
    }


def write_graph_output(
    output: dict[str, Any],
    output_path: str | Path = "artifacts/graph/graph_output.json",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)
    return path


def run(
    data_dir: str | Path = "data",
    output_path: str | Path = "artifacts/graph/graph_output.json",
    *,
    evaluate_gnn: bool = True,
    seed: int = 42,
    epochs: int = 80,
) -> dict[str, Any]:
    graph = build_graph(data_dir)
    evaluation = None
    if evaluate_gnn:
        try:
            from graph.evaluation import evaluate_graphsage

            evaluation = evaluate_graphsage(
                graph, Path(data_dir) / "labels.json", seed=seed, epochs=epochs,
            )
        except (ImportError, FileNotFoundError, ValueError) as exc:
            # Missing ML dependencies or unusable evaluation labels must leave
            # explicit pending metrics; training/data bugs still surface.
            print(f"[graph] GraphSAGE evaluation skipped: {exc}")
    output = build_graph_output(graph, evaluation)
    write_graph_output(output, output_path)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the TenderFender graph artifact")
    parser.add_argument("--data-dir", default="data", help="Directory containing the five structural CSVs")
    parser.add_argument("--output", default="artifacts/graph/graph_output.json", help="Output JSON path")
    parser.add_argument("--skip-gnn", action="store_true", help="Build heuristic output without model evaluation")
    parser.add_argument("--seed", type=int, default=42, help="GraphSAGE train/evaluation seed")
    parser.add_argument("--epochs", type=int, default=80, help="GraphSAGE training epochs")
    args = parser.parse_args(argv)
    output = run(args.data_dir, args.output, evaluate_gnn=not args.skip_gnn, seed=args.seed, epochs=args.epochs)
    print(
        f"[graph] nodes={len(output['graph']['nodes'])} "
        f"edges={len(output['graph']['edges'])} rings={len(output['rings'])} "
        f"vendors_scored={len(output['vendor_scores'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
