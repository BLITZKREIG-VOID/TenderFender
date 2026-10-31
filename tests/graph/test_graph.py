from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx
import pytest
from torch_geometric.data import HeteroData

from graph.build import GraphDataError, build_graph
from graph.evaluation import binary_metrics, evaluate_graphsage, stratified_split
from graph.gnn import HeterogeneousGraphSAGE, networkx_to_heterodata
from graph.run import build_graph_output, run as run_graph_pipeline
from graph.screens import _category, explain_vendors, find_rings, score_vendors


VENDOR_FIELDS = [
    "vendor_id", "name", "turnover_cr", "years_experience",
    "registration_class", "address_id", "contact_id",
]
DIRECTOR_FIELDS = ["person_id", "name"]
VENDOR_DIRECTOR_FIELDS = ["vendor_id", "person_id"]
TENDER_FIELDS = ["tender_id", "buyer_id", "title", "estimated_value_cr", "bid_days", "open_date"]
BID_FIELDS = ["tender_id", "vendor_id", "bid_amount_cr", "bid_ratio", "rank", "won", "submitted_at"]


def _vendor(vendor_id: str, *, address: str, contact: str) -> dict[str, str]:
    return {
        "vendor_id": vendor_id,
        "name": f"Vendor {vendor_id}",
        "turnover_cr": "20.5",
        "years_experience": "8",
        "registration_class": "Class-A",
        "address_id": address,
        "contact_id": contact,
    }


def _tender(tender_id: str, buyer_id: str = "B-001") -> dict[str, str]:
    number = int(tender_id.split("-")[1])
    return {
        "tender_id": tender_id,
        "buyer_id": buyer_id,
        "title": f"Tender {tender_id}",
        "estimated_value_cr": "100.0",
        "bid_days": "30",
        "open_date": f"2025-01-{(number - 1) % 28 + 1:02d}",
    }


def _bid(tender_id: str, vendor_id: str, amount: float, rank: int, won: bool) -> dict[str, str]:
    return {
        "tender_id": tender_id,
        "vendor_id": vendor_id,
        "bid_amount_cr": f"{amount:.2f}",
        "bid_ratio": f"{amount / 100:.4f}",
        "rank": str(rank),
        "won": "1" if won else "0",
        "submitted_at": "2025-01-01T09:00:00",
    }


def _write_csv(root: Path, filename: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (root / filename).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _dataset(
    root: Path,
    *,
    vendors: list[dict[str, str]] | None = None,
    directors: list[dict[str, str]] | None = None,
    links: list[dict[str, str]] | None = None,
    tenders: list[dict[str, str]] | None = None,
    bids: list[dict[str, str]] | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    vendors = vendors if vendors is not None else [
        _vendor("V-001", address="A-001", contact="CT-001"),
        _vendor("V-002", address="A-001", contact="CT-002"),
        _vendor("V-003", address="A-003", contact="CT-003"),
    ]
    directors = directors if directors is not None else [
        {"person_id": "P-001", "name": "Director One"},
        {"person_id": "P-002", "name": "Director Two"},
    ]
    links = links if links is not None else [
        {"vendor_id": "V-001", "person_id": "P-001"},
        {"vendor_id": "V-002", "person_id": "P-001"},
        {"vendor_id": "V-003", "person_id": "P-002"},
    ]
    tenders = tenders if tenders is not None else [_tender("T-001")]
    bids = bids if bids is not None else [
        _bid("T-001", "V-001", 80.0, 1, True),
        _bid("T-001", "V-002", 82.0, 2, False),
        _bid("T-001", "V-003", 90.0, 3, False),
    ]
    _write_csv(root, "vendors.csv", VENDOR_FIELDS, vendors)
    _write_csv(root, "directors.csv", DIRECTOR_FIELDS, directors)
    _write_csv(root, "vendor_directors.csv", VENDOR_DIRECTOR_FIELDS, links)
    _write_csv(root, "tenders.csv", TENDER_FIELDS, tenders)
    _write_csv(root, "bids.csv", BID_FIELDS, bids)
    return root


def _rotation_dataset(
    root: Path,
    *,
    same_buyer: bool = True,
    cover: bool = False,
    rotate_winners: bool = True,
) -> Path:
    vendors = [
        _vendor("V-001", address="A-001", contact="CT-001"),
        _vendor("V-002", address="A-002", contact="CT-002"),
        _vendor("V-003", address="A-003", contact="CT-003"),
    ]
    tenders = []
    bids = []
    for index in range(1, 7):
        tender_id = f"T-{index:03d}"
        buyer_id = "B-001" if same_buyer else f"B-{index:03d}"
        tenders.append(_tender(tender_id, buyer_id))
        winner = (index - 1) % 3 if rotate_winners else 0
        winning_amount = 80.0
        for vendor_index, vendor in enumerate(vendors):
            amount = winning_amount if vendor_index == winner else (
                winning_amount * 1.02 if cover else 85.0 + vendor_index
            )
            bids.append(_bid(tender_id, vendor["vendor_id"], amount, vendor_index + 1, vendor_index == winner))
    return _dataset(root, vendors=vendors, tenders=tenders, bids=bids)


def _training_dataset(root: Path) -> tuple[Path, Path]:
    vendors = [
        _vendor(f"V-{index:03d}", address=f"A-{index:03d}", contact=f"CT-{index:03d}")
        for index in range(1, 13)
    ]
    bids = [
        _bid("T-001", vendor["vendor_id"], 80.0 + index, index, index == 1)
        for index, vendor in enumerate(vendors, start=1)
    ]
    root = _dataset(root, vendors=vendors, bids=bids)
    ring_labels = {
        "rings": [
            {"ring_id": "R-1", "vendor_ids": ["V-001"]},
            {"ring_id": "R-2", "vendor_ids": ["V-002"]},
            {"ring_id": "R-3", "vendor_ids": ["V-003"]},
        ],
        "vendor_labels": {f"V-{index:03d}": int(index <= 3) for index in range(1, 13)},
        "planted_type": {f"V-{index:03d}": "evaluation-only" for index in range(1, 13)},
    }
    labels_path = root / "labels.json"
    labels_path.write_text(json.dumps(ring_labels), encoding="utf-8")
    return root, labels_path


def test_builds_typed_heterogeneous_graph_with_expected_relationships(tmp_path: Path) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))

    assert isinstance(graph, nx.MultiDiGraph)
    types = [attrs["type"] for _, attrs in graph.nodes(data=True)]
    assert {kind: types.count(kind) for kind in set(types)} == {
        "vendor": 3, "person": 2, "address": 2, "contact": 3, "tender": 1, "buyer": 1,
    }
    edge_types = [attrs["type"] for _, _, attrs in graph.edges(data=True)]
    assert {kind: edge_types.count(kind) for kind in set(edge_types)} == {
        "directed_by": 3, "located_at": 3, "has_contact": 3,
        "submitted_bid": 3, "issued_by": 1,
    }
    assert graph.has_edge("V-001", "P-001", key="directed_by")
    assert graph.has_edge("V-001", "A-001", key="located_at")
    assert graph.has_edge("V-001", "T-001", key="bid:T-001:V-001")
    assert graph.has_edge("T-001", "B-001", key="issued_by")
    assert not graph.has_edge("V-001", "B-001")


def test_bid_edges_preserve_each_bid_and_attributes(tmp_path: Path) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))
    data = graph.get_edge_data("V-002", "T-001")["bid:T-001:V-002"]

    assert data["type"] == "submitted_bid"
    assert data["features"] == {
        "bid_amount_cr": 82.0,
        "bid_ratio": 0.82,
        "rank": 2,
        "won": False,
        "submitted_at": "2025-01-01T09:00:00",
    }
    assert graph.number_of_edges("V-001", "T-001") == 1
    assert graph.number_of_edges("V-002", "T-001") == 1


def test_missing_required_references_fail_with_context(tmp_path: Path) -> None:
    links = [
        {"vendor_id": "V-001", "person_id": "P-999"},
    ]
    with pytest.raises(GraphDataError, match="vendor_directors.csv:2 references unknown person"):
        build_graph(_dataset(tmp_path / "data", links=links))


@pytest.mark.parametrize("duplicate_file", ["vendor_directors", "bids"])
def test_duplicate_relationships_fail_instead_of_being_overwritten(tmp_path: Path, duplicate_file: str) -> None:
    kwargs = {}
    if duplicate_file == "vendor_directors":
        kwargs["links"] = [
            {"vendor_id": "V-001", "person_id": "P-001"},
            {"vendor_id": "V-001", "person_id": "P-001"},
        ]
    else:
        kwargs["bids"] = [
            _bid("T-001", "V-001", 80.0, 1, True),
            _bid("T-001", "V-001", 80.0, 2, False),
            _bid("T-001", "V-002", 82.0, 3, False),
            _bid("T-001", "V-003", 90.0, 4, False),
        ]
    message = "Duplicate vendor/director" if duplicate_file == "vendor_directors" else "Duplicate bid"
    with pytest.raises(GraphDataError, match=message):
        build_graph(_dataset(tmp_path / "data", **kwargs))


def test_empty_or_malformed_csv_has_useful_error(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    (root / "vendors.csv").write_text("", encoding="utf-8")
    with pytest.raises(GraphDataError, match="vendors.csv has no CSV header"):
        build_graph(root)


def test_bad_numeric_value_has_useful_error(tmp_path: Path) -> None:
    vendors = [
        _vendor("V-001", address="A-001", contact="CT-001"),
        _vendor("V-002", address="A-001", contact="CT-001"),
        _vendor("V-003", address="A-003", contact="CT-003"),
    ]
    vendors[0]["turnover_cr"] = "not-a-number"
    with pytest.raises(GraphDataError, match="invalid numeric value turnover_cr"):
        build_graph(_dataset(tmp_path / "data", vendors=vendors))


def test_builder_never_opens_labels_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _dataset(tmp_path / "data")
    (root / "labels.json").write_text("not valid JSON and should not be read", encoding="utf-8")
    original_open = Path.open

    def guarded_open(path: Path, *args, **kwargs):
        if path.name == "labels.json":
            raise AssertionError("graph builder attempted to load evaluation labels")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    graph = build_graph(root)
    assert graph.number_of_nodes() > 0


def test_r1_shared_director_and_address_is_detected(tmp_path: Path) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))
    rings = find_rings(graph)

    assert len(rings) == 1
    assert rings[0].vendor_ids == ("V-001", "V-002")
    assert rings[0].link_types == ("shared_address", "shared_director")
    assert rings[0].score >= 0.5


@pytest.mark.parametrize("signal", ["shared_director", "shared_address"])
def test_individual_ownership_signals_are_explained_without_group_threshold(
    tmp_path: Path, signal: str,
) -> None:
    vendors = [
        _vendor("V-001", address="A-001", contact="CT-001"),
        _vendor("V-002", address="A-001" if signal == "shared_address" else "A-002", contact="CT-002"),
        _vendor("V-003", address="A-003", contact="CT-003"),
    ]
    links = [
        {"vendor_id": "V-001", "person_id": "P-001"},
        {"vendor_id": "V-002", "person_id": "P-002" if signal == "shared_address" else "P-001"},
        {"vendor_id": "V-003", "person_id": "P-002"},
    ]
    graph = build_graph(_dataset(tmp_path / "data", vendors=vendors, links=links))
    scores, explanations = explain_vendors(graph)
    v1 = next(row for row in explanations if row["vendor_id"] == "V-001")

    assert scores["V-001"] == 0.2
    assert v1["evidence_types"] == [signal]
    assert v1["related_vendor_ids"] == ["V-002"]
    assert v1["relationship_types"] == (["directed_by"] if signal == "shared_director" else ["located_at"])
    assert v1["evidence"][0]["resource_ids"]


def test_rotation_evidence_includes_buyer_vendors_and_all_tenders(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(tmp_path / "data"))
    scores, explanations = explain_vendors(graph)
    v1 = next(row for row in explanations if row["vendor_id"] == "V-001")
    rotation = next(item for item in v1["evidence"] if item["type"] == "bid_rotation")

    assert scores["V-001"] == 0.35  # shared director (20) + six-tender rotation (15)
    assert rotation["tender_ids"] == [f"T-{i:03d}" for i in range(1, 7)]
    assert rotation["relationship_types"] == ["issued_by", "submitted_bid"]
    assert rotation["buyer_id"] == "B-001"
    assert rotation["winning_bids"] == [
        {"tender_id": f"T-{i:03d}", "winner_vendor_id": f"V-{(i - 1) % 3 + 1:03d}"}
        for i in range(1, 7)
    ]
    assert v1["related_vendor_ids"] == ["V-002", "V-003"]


def test_cover_evidence_retains_tender_ratio_and_winner(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(tmp_path / "data", cover=True, rotate_winners=False))
    _, explanations = explain_vendors(graph)
    v2 = next(row for row in explanations if row["vendor_id"] == "V-002")
    cover = next(item for item in v2["evidence"] if item["type"] == "cover_bids")

    assert cover["tender_ids"] == [f"T-{i:03d}" for i in range(1, 7)]
    assert cover["buyer_id"] == "B-001"
    assert cover["relationship_types"] == ["issued_by", "submitted_bid"]
    assert cover["bid_ratios"] == [
        {"tender_id": f"T-{i:03d}", "vendor_id": "V-002", "ratio": 1.02}
        for i in range(1, 7)
    ]
    assert cover["winning_bids"] == [
        {"tender_id": f"T-{i:03d}", "winner_vendor_id": "V-001"}
        for i in range(1, 7)
    ]
    assert "V-001" in v2["related_vendor_ids"]


def test_scores_deduplicate_duplicate_graph_evidence(tmp_path: Path) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))
    graph.add_edge("V-001", "P-001", key="duplicate-for-unit-test", type="directed_by")
    scores, explanations = explain_vendors(graph)
    v1 = next(row for row in explanations if row["vendor_id"] == "V-001")

    assert scores["V-001"] == 0.4
    assert len([item for item in v1["evidence"] if item["type"] == "shared_director"]) == 1


def test_score_boundaries_and_no_evidence_vendors(tmp_path: Path) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))
    scores, explanations = explain_vendors(graph)

    assert scores["V-001"] == 0.4
    assert scores["V-003"] == 0.0
    assert {row["vendor_id"] for row in explanations} == {"V-001", "V-002"}
    assert next(row for row in explanations if row["vendor_id"] == "V-001")["risk_category"] == "elevated"
    assert score_vendors(graph) == scores


def test_risk_category_score_boundaries() -> None:
    assert _category(0.0) == "low"
    assert _category(0.1999) == "low"
    assert _category(0.20) == "guarded"
    assert _category(0.3999) == "guarded"
    assert _category(0.40) == "elevated"
    assert _category(0.6999) == "elevated"
    assert _category(0.70) == "high"
    assert _category(1.0) == "high"


def test_explanations_and_scores_are_deterministic(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(tmp_path / "data", cover=True))
    first = explain_vendors(graph)
    second = explain_vendors(graph)
    assert first == second


def test_networkx_conversion_preserves_heterogeneous_relations_without_ids_in_features(
    tmp_path: Path,
) -> None:
    graph = build_graph(_dataset(tmp_path / "data"))
    converted = networkx_to_heterodata(graph)

    assert isinstance(converted.data, HeteroData)
    assert set(converted.data.node_types) == {"vendor", "person", "address", "contact", "tender", "buyer"}
    relations = {edge_type[1] for edge_type in converted.data.edge_types}
    assert {"directed_by", "located_at", "has_contact", "submitted_bid", "issued_by"} <= relations
    assert {f"rev_{name}" for name in ("directed_by", "located_at", "has_contact", "submitted_bid", "issued_by")} <= relations
    assert converted.data["vendor"].x.shape == (3, 10)
    assert converted.data["tender"].x.shape == (1, 2)
    assert all(store.x.dtype.is_floating_point for _, store in converted.data.node_items())
    assert not hasattr(converted.data["vendor"], "y")
    assert set(converted.data["vendor"].keys()) == {"x"}
    assert converted.node_ids["vendor"] == ("V-001", "V-002", "V-003")


def test_heterogeneous_graphsage_forward_pass_runs_on_cpu(tmp_path: Path) -> None:
    import torch

    graph = build_graph(_dataset(tmp_path / "data"))
    converted = networkx_to_heterodata(graph)
    input_dims = {node_type: store.x.size(1) for node_type, store in converted.data.node_items()}
    model = HeterogeneousGraphSAGE(converted.data.metadata(), input_dims, hidden_channels=8)
    logits, embeddings = model(converted.data)

    assert logits.device.type == "cpu"
    assert embeddings.device.type == "cpu"
    assert logits.shape == (3,)
    assert embeddings.shape == (3, 8)


def test_evaluation_labels_are_separate_from_graph_features_and_use_union_target(tmp_path: Path) -> None:
    import torch

    root, labels_path = _training_dataset(tmp_path / "data")
    converted = networkx_to_heterodata(build_graph(root))
    assert "y" not in converted.data["vendor"]
    assert not any("label" in key for key in converted.data["vendor"].keys())
    from graph.evaluation import load_evaluation_labels

    targets, _ = load_evaluation_labels(labels_path, converted.node_ids["vendor"])
    assert torch.equal(targets, torch.tensor([1.0, 1.0, 1.0, *([0.0] * 9)]))


def test_split_and_metrics_are_reproducible_and_correct() -> None:
    import torch

    targets = torch.tensor([1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    first = stratified_split(targets, seed=42)
    second = stratified_split(targets, seed=42)
    assert first == second
    assert set(first["train"]).isdisjoint(first["validation"])
    assert set(first["train"]).isdisjoint(first["test"])
    assert set(first["validation"]).isdisjoint(first["test"])
    assert set().union(*map(set, first.values())) == set(range(len(targets)))
    assert binary_metrics([1, 0, 1, 0], [0.9, 0.8, 0.7, 0.1]) == {
        "pr_auc": 0.833333,
        "precision_at_10": 0.5,
    }


def test_graphsage_training_is_reproducible_and_reports_heldout_metrics(tmp_path: Path) -> None:
    root, labels_path = _training_dataset(tmp_path / "data")
    graph = build_graph(root)
    first = evaluate_graphsage(graph, labels_path, seed=7, epochs=3, hidden_channels=8)
    second = evaluate_graphsage(graph, labels_path, seed=7, epochs=3, hidden_channels=8)

    assert first == second
    assert first.metrics["gnn_status"] == "trained"
    assert first.metrics["gnn"]["pr_auc"] >= 0.0
    assert first.metrics["gnn"]["precision_at_10"] >= 0.0
    assert first.metrics["baseline"].keys() == {"pr_auc", "precision_at_10"}
    assert first.metrics["gnn"]["per_ring"]["R-1"]["status"] == "pending"
    assert set(first.vendor_scores) == set(f"V-{index:03d}" for index in range(1, 13))


def test_pipeline_retains_pending_metrics_when_evaluation_labels_are_unavailable(
    tmp_path: Path,
) -> None:
    data_dir = _dataset(tmp_path / "data")  # intentionally no labels.json
    output = run_graph_pipeline(data_dir, tmp_path / "graph_output.json")

    assert output["metrics"]["gnn_status"] == "skipped"
    assert "pending" in output["metrics"]["note"]
    assert output["metrics"]["gnn"] == {"pr_auc": 0.0, "precision_at_10": 0.0}
    assert output["gnn_vendor_scores"] == {}


def test_r2_same_buyer_winner_rotation_is_detected(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(tmp_path / "data", same_buyer=True))
    rings = find_rings(graph)

    assert any(
        ring.screen == "rotation"
        and ring.vendor_ids == ("V-001", "V-002", "V-003")
        and ring.anchor_id == "B-001"
        for ring in rings
    )


def test_r2_requires_each_member_to_win_at_least_once(tmp_path: Path) -> None:
    root = _rotation_dataset(tmp_path / "data", same_buyer=True, rotate_winners=False)
    graph = build_graph(root)
    assert not any(ring.screen == "rotation" for ring in find_rings(graph))


def test_rotation_across_different_buyers_does_not_claim_same_buyer_ring(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(tmp_path / "data", same_buyer=False))
    assert not any(ring.screen == "rotation" for ring in find_rings(graph))


def test_r3_repeated_cover_bids_are_detected(tmp_path: Path) -> None:
    graph = build_graph(_rotation_dataset(
        tmp_path / "data", same_buyer=True, cover=True, rotate_winners=False,
    ))
    rings = find_rings(graph)

    assert any(
        ring.screen == "cover"
        and ring.vendor_ids == ("V-002", "V-003")
        and ring.anchor_id == "B-001"
        for ring in rings
    )


def test_screen_membership_comes_from_observed_structure_not_labels(tmp_path: Path) -> None:
    root = _dataset(tmp_path / "data")
    (root / "labels.json").write_text(json.dumps({
        "rings": [{"ring_id": "FAKE", "vendor_ids": ["V-003"], "type": "cover"}],
        "vendor_labels": {"V-003": 1},
        "planted_type": {"V-003": "cover"},
    }), encoding="utf-8")
    output = build_graph_output(build_graph(root))

    assert output["rings"][0]["vendor_ids"] == ["V-001", "V-002"]
    assert all("FAKE" not in json.dumps(value) for value in output.values())


def test_artifact_is_deterministic_and_matches_api_display_shape(tmp_path: Path) -> None:
    from graph.run import write_graph_output

    graph = build_graph(_dataset(tmp_path / "data"))
    first = build_graph_output(graph)
    second = build_graph_output(graph)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert set(first) == {
        "vendor_scores", "gnn_vendor_scores", "vendor_explanations",
        "rings", "paths", "graph", "metrics",
    }
    assert first["gnn_vendor_scores"] == {}
    assert all(0.0 <= score <= 1.0 for score in first["vendor_scores"].values())
    assert first["vendor_scores"]["V-003"] == 0.0
    assert first["vendor_explanations"]
    assert all(set(row) == {
        "vendor_id", "risk_score", "risk_category", "evidence_types",
        "related_vendor_ids", "tender_ids", "relationship_types", "evidence",
        "groups", "explanation",
    } for row in first["vendor_explanations"])
    assert all(row["explanation"] for row in first["vendor_explanations"])
    assert set(first["graph"]) == {"nodes", "edges"}
    assert all(set(node) == {"id", "type", "label", "flagged"} for node in first["graph"]["nodes"])
    assert all(set(edge) == {"source", "target", "type"} for edge in first["graph"]["edges"])
    assert {node["type"] for node in first["graph"]["nodes"]} <= {"vendor", "person", "address", "buyer"}
    assert {edge["type"] for edge in first["graph"]["edges"]} <= {"directed_by", "located_at", "bid_to"}
    assert first["metrics"]["gnn_status"] == "skipped"
    assert "experimental" in first["metrics"]["note"]
    assert "pending" in first["metrics"]["note"]
    assert first["metrics"]["baseline"] == {"pr_auc": 0.0, "precision_at_10": 0.0}

    output_path = tmp_path / "artifacts" / "graph_output.json"
    write_graph_output(first, output_path)
    first_bytes = output_path.read_bytes()
    assert json.loads(first_bytes) == first
    write_graph_output(second, output_path)
    assert output_path.read_bytes() == first_bytes
