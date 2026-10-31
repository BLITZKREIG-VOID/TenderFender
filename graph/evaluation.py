"""Label-separated GraphSAGE training and held-out baseline evaluation."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn

from graph.gnn import HeterogeneousGraphSAGE, networkx_to_heterodata, seed_torch
from graph.screens import score_vendors


@dataclass(frozen=True)
class EvaluationResult:
    metrics: dict[str, Any]
    vendor_scores: dict[str, float]


def load_evaluation_labels(
    labels_path: str | Path,
    vendor_ids: tuple[str, ...],
) -> tuple[Tensor, dict[str, set[str]]]:
    """Read ring membership as targets only; this is not part of graph features."""
    path = Path(labels_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FileNotFoundError(f"Could not read evaluation labels {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evaluation labels {path} are not valid JSON: {exc}") from exc

    rings = payload.get("rings")
    if not isinstance(rings, list):
        raise ValueError("Evaluation labels must contain a rings array")
    vendor_set = set(vendor_ids)
    memberships: dict[str, set[str]] = {}
    for ring_id in ("R-1", "R-2", "R-3"):
        row = next((item for item in rings if item.get("ring_id") == ring_id), None)
        if not isinstance(row, dict) or not isinstance(row.get("vendor_ids"), list):
            raise ValueError(f"Evaluation labels are missing vendor membership for {ring_id}")
        members = set(row["vendor_ids"])
        unknown = members - vendor_set
        if unknown:
            raise ValueError(f"{ring_id} labels reference unknown vendors: {sorted(unknown)}")
        memberships[ring_id] = members

    positive = set.union(*memberships.values())
    targets = torch.tensor([float(vendor_id in positive) for vendor_id in vendor_ids], dtype=torch.float32)
    if not positive or positive == vendor_set:
        raise ValueError("Union of R-1/R-2/R-3 labels must contain positive and negative vendors")
    return targets, memberships


def stratified_split(targets: Tensor, seed: int = 42) -> dict[str, list[int]]:
    """Deterministically stratify binary labels into 60/20/20 index splits."""
    rng = random.Random(seed)
    split = {name: [] for name in ("train", "validation", "test")}
    fractions = (0.6, 0.2, 0.2)
    for label in (0, 1):
        indices = torch.where(targets == float(label))[0].tolist()
        rng.shuffle(indices)
        count = len(indices)
        if count < 3:
            raise ValueError(f"Need at least 3 vendors for label {label}, found {count}")
        sizes = [int(count * fraction) for fraction in fractions]
        remainder = count - sum(sizes)
        order = sorted(range(3), key=lambda i: (-(count * fractions[i] - sizes[i]), i))
        for index in order[:remainder]:
            sizes[index] += 1
        if sizes[2] == 0:
            donor = max((0, 1), key=lambda i: sizes[i])
            sizes[donor] -= 1
            sizes[2] += 1
        cursor = 0
        for name, size in zip(split, sizes):
            split[name].extend(indices[cursor:cursor + size])
            cursor += size
    for indices in split.values():
        indices.sort()
    return split


def binary_metrics(targets: list[int], scores: list[float], *, k: int = 10) -> dict[str, float]:
    """Return average-precision PR-AUC and precision@k using deterministic ties."""
    if len(targets) != len(scores) or not targets:
        raise ValueError("metrics require equally sized, non-empty targets and scores")
    positives = sum(targets)
    if positives == 0 or positives == len(targets):
        raise ValueError("PR-AUC requires positive and negative examples")
    ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    hit_count = 0
    precision_sum = 0.0
    for rank, index in enumerate(ranked, start=1):
        if targets[index]:
            hit_count += 1
            precision_sum += hit_count / rank
    top_k = ranked[:min(k, len(ranked))]
    return {
        "pr_auc": round(precision_sum / positives, 6),
        "precision_at_10": round(sum(targets[index] for index in top_k) / len(top_k), 6),
    }


def _subset_metrics(
    targets: Tensor,
    scores: Tensor,
    indices: list[int],
) -> dict[str, float] | None:
    subset_targets = [int(targets[index].item()) for index in indices]
    if not subset_targets or not any(subset_targets) or all(subset_targets):
        return None
    subset_scores = [float(scores[index].item()) for index in indices]
    return binary_metrics(subset_targets, subset_scores)


def evaluate_graphsage(
    graph: Any,
    labels_path: str | Path,
    *,
    seed: int = 42,
    epochs: int = 80,
    hidden_channels: int = 16,
) -> EvaluationResult:
    """Train on train-mask labels and report validation/test metrics.

    The full graph topology is used transductively, but only training-mask
    vendor labels enter the loss. Validation/test targets are used for metrics
    only; there is no early stopping or model selection on the test split.
    """
    if epochs < 1:
        raise ValueError("epochs must be positive")
    converted = networkx_to_heterodata(graph)
    vendor_ids = converted.node_ids.get("vendor", ())
    if not vendor_ids:
        raise ValueError("the graph has no vendor nodes")
    targets, ring_memberships = load_evaluation_labels(labels_path, vendor_ids)
    splits = stratified_split(targets, seed)

    train_mask = torch.zeros(len(vendor_ids), dtype=torch.bool)
    validation_mask = torch.zeros_like(train_mask)
    test_mask = torch.zeros_like(train_mask)
    train_mask[splits["train"]] = True
    validation_mask[splits["validation"]] = True
    test_mask[splits["test"]] = True
    if torch.any(train_mask & validation_mask) or torch.any(train_mask & test_mask) or torch.any(validation_mask & test_mask):
        raise AssertionError("train, validation, and test masks must be disjoint")

    previous_threads = torch.get_num_threads()
    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    try:
        seed_torch(seed)
        input_dims = {node_type: store.x.size(1) for node_type, store in converted.data.node_items()}
        model = HeterogeneousGraphSAGE(
            converted.data.metadata(), input_dims, hidden_channels=hidden_channels,
        ).to(torch.device("cpu"))
        positive_count = float(targets[train_mask].sum().item())
        negative_count = float(train_mask.sum().item()) - positive_count
        if positive_count == 0 or negative_count == 0:
            raise ValueError("training split must contain positive and negative vendor labels")
        loss_fn = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(negative_count / positive_count))
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=0.001)
        model.train()
        for _ in range(epochs):
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(converted.data)
            loss = loss_fn(logits[train_mask], targets[train_mask])
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            logits, _ = model(converted.data)
            probabilities = torch.sigmoid(logits).cpu()
    finally:
        torch.set_num_threads(previous_threads)
        torch.use_deterministic_algorithms(previous_deterministic)

    validation_metrics = _subset_metrics(targets, probabilities, splits["validation"])
    test_metrics = _subset_metrics(targets, probabilities, splits["test"])
    if test_metrics is None:
        raise ValueError("test split does not contain both positive and negative vendors")

    heuristic = score_vendors(graph)
    test_ids = [vendor_ids[index] for index in splits["test"]]
    baseline_metrics = binary_metrics(
        [int(targets[index].item()) for index in splits["test"]],
        [float(heuristic[vendor_ids[index]]) for index in splits["test"]],
    )

    per_ring: dict[str, Any] = {}
    for ring_id, members in ring_memberships.items():
        ring_targets = [int(vendor_id in members) for vendor_id in test_ids]
        positive_test = sum(ring_targets)
        negative_test = len(ring_targets) - positive_test
        if positive_test < 2 or negative_test < 2:
            per_ring[ring_id] = {
                "status": "pending",
                "reason": "test split needs at least two positive and two negative vendors for this ring",
                "test_positive_count": positive_test,
                "test_negative_count": negative_test,
            }
            continue
        test_scores = [float(probabilities[index].item()) for index in splits["test"]]
        baseline_scores = [heuristic[vendor_ids[index]] for index in splits["test"]]
        per_ring[ring_id] = {
            "status": "evaluated",
            "gnn": binary_metrics(ring_targets, test_scores),
            "baseline": binary_metrics(ring_targets, baseline_scores),
            "test_positive_count": positive_test,
            "test_negative_count": negative_test,
        }

    vendor_scores = {
        vendor_id: round(float(probabilities[index].item()), 6)
        for index, vendor_id in enumerate(vendor_ids)
    }
    metrics = {
        "baseline": baseline_metrics,
        "gnn": {
            **test_metrics,
            "validation": validation_metrics,
            "per_ring": per_ring,
            "split": {
                name: len(indices) for name, indices in splits.items()
            },
            "test_positive_vendors": int(targets[splits["test"]].sum().item()),
            "seed": seed,
            "epochs": epochs,
            "architecture": f"2-layer relation-aware heterogeneous GraphSAGE; hidden={hidden_channels}",
            "experimental": True,
            "evaluation_note": "single synthetic split; metrics are not generalization estimates",
        },
        "gnn_status": "trained",
        "note": "experimental GraphSAGE trained and evaluated on a fixed synthetic split; inspect limitations",
    }
    return EvaluationResult(metrics=metrics, vendor_scores=dict(sorted(vendor_scores.items())))
