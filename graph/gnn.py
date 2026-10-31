"""Small CPU-capable GraphSAGE model and label-free NetworkX conversion."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import networkx as nx
import torch
from torch import Tensor, nn
from torch.nn import functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv


REGISTRATION_CLASSES = ("MSE", "Class-A", "Class-B", "Class-C")


@dataclass(frozen=True)
class GraphTensorization:
    """Tensor graph plus external ID mappings, never included in model features."""

    data: HeteroData
    node_ids: dict[str, tuple[str, ...]]
    index_by_id: dict[str, dict[str, int]]


def _node_features(
    node_type: str,
    attrs: dict[str, Any],
    vendor_bid_stats: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
) -> list[float]:
    features = attrs.get("features", {})
    if node_type == "vendor":
        turnover = float(features["turnover_cr"])
        experience = float(features["years_experience"])
        registration = features["registration_class"]
        if registration not in REGISTRATION_CLASSES:
            raise ValueError(f"unsupported vendor registration class {registration!r}")
        return [
            math.log1p(max(0.0, turnover)),
            max(0.0, experience) / 30.0,
            *[float(registration == category) for category in REGISTRATION_CLASSES],
            *vendor_bid_stats,
        ]
    if node_type == "tender":
        # Tender IDs, titles, and open dates are intentionally excluded: the
        # synthetic scenario placement/order can correlate with evaluation labels.
        return [
            math.log1p(max(0.0, float(features["estimated_value_cr"]))),
            max(0.0, float(features["bid_days"])) / 90.0,
        ]
    # Person/address/contact/buyer nodes have no safe, non-identity attributes.
    # A constant feature allows relation messages to be learned without encoding IDs.
    return [1.0]


def networkx_to_heterodata(graph: nx.MultiDiGraph) -> GraphTensorization:
    """Convert the existing structural graph without consulting labels or scores."""
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("GraphSAGE conversion requires a NetworkX MultiDiGraph")

    ids_by_type: dict[str, tuple[str, ...]] = {}
    index_by_id: dict[str, dict[str, int]] = {}
    for node_type in sorted({attrs.get("type") for _, attrs in graph.nodes(data=True)}):
        if not node_type:
            raise ValueError("every graph node must have a type")
        ids = tuple(sorted(node for node, attrs in graph.nodes(data=True) if attrs.get("type") == node_type))
        ids_by_type[node_type] = ids
        index_by_id[node_type] = {node_id: index for index, node_id in enumerate(ids)}

    data = HeteroData()
    vendor_bids: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for vendor_id, _, edge_attrs in graph.edges(data=True):
        if edge_attrs.get("type") == "submitted_bid":
            vendor_bids[vendor_id].append(edge_attrs["features"])

    for node_type, node_ids in ids_by_type.items():
        rows = []
        for node_id in node_ids:
            bids = vendor_bids.get(node_id, ()) if node_type == "vendor" else ()
            bid_count = len(bids)
            bid_stats = (
                math.log1p(bid_count),
                sum(float(bid["won"]) for bid in bids) / bid_count if bid_count else 0.0,
                sum(float(bid["bid_ratio"]) for bid in bids) / bid_count if bid_count else 0.0,
                sum(float(bid["rank"]) for bid in bids) / bid_count / 10.0 if bid_count else 0.0,
            )
            rows.append(_node_features(node_type, graph.nodes[node_id], bid_stats))
        data[node_type].x = torch.tensor(rows, dtype=torch.float32)

    relation_edges: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
    for source, target, _, attrs in sorted(
        graph.edges(keys=True, data=True),
        key=lambda edge: (edge[0], edge[1], str(edge[2]), edge[3].get("type", "")),
    ):
        relation = attrs.get("type")
        source_type = graph.nodes[source].get("type")
        target_type = graph.nodes[target].get("type")
        if not relation or not source_type or not target_type:
            raise ValueError(f"edge {source!r}->{target!r} has a missing type")
        edge_type = (source_type, str(relation), target_type)
        relation_edges.setdefault(edge_type, []).append((
            index_by_id[source_type][source], index_by_id[target_type][target],
        ))

    for (source_type, relation, target_type), edges in sorted(relation_edges.items()):
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        data[(source_type, relation, target_type)].edge_index = edge_index
        reverse_type = (target_type, f"rev_{relation}", source_type)
        reverse_edges = [(target, source) for source, target in edges]
        data[reverse_type].edge_index = torch.tensor(reverse_edges, dtype=torch.long).t().contiguous()

    return GraphTensorization(data=data, node_ids=ids_by_type, index_by_id=index_by_id)


class _SAGEBlock(nn.Module):
    def __init__(
        self,
        node_types: tuple[str, ...],
        edge_types: tuple[tuple[str, str, str], ...],
        input_dims: dict[str, int],
        hidden_channels: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.conv = HeteroConv({
            edge_type: SAGEConv(
                (input_dims[edge_type[0]], input_dims[edge_type[2]]),
                hidden_channels,
                root_weight=False,
            )
            for edge_type in edge_types
        }, aggr="mean")
        self.self_projection = nn.ModuleDict({
            node_type: nn.Linear(input_dims[node_type], hidden_channels)
            for node_type in node_types
        })
        self.dropout = dropout

    def forward(
        self,
        x_dict: dict[str, Tensor],
        edge_index_dict: dict[tuple[str, str, str], Tensor],
    ) -> dict[str, Tensor]:
        messages = self.conv(x_dict, edge_index_dict)
        result = {}
        for node_type, values in x_dict.items():
            aggregate = self.self_projection[node_type](values)
            if node_type in messages:
                aggregate = aggregate + messages[node_type]
            result[node_type] = F.dropout(F.relu(aggregate), p=self.dropout, training=self.training)
        return result


class HeterogeneousGraphSAGE(nn.Module):
    """Two relation-aware GraphSAGE layers and a binary vendor head."""

    def __init__(
        self,
        metadata: tuple[list[str], list[tuple[str, str, str]]],
        input_dims: dict[str, int],
        hidden_channels: int = 16,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        node_types, edge_types = metadata
        node_types = tuple(node_types)
        edge_types = tuple(edge_types)
        self.layer1 = _SAGEBlock(node_types, edge_types, input_dims, hidden_channels, dropout)
        hidden_dims = {node_type: hidden_channels for node_type in node_types}
        self.layer2 = _SAGEBlock(node_types, edge_types, hidden_dims, hidden_channels, dropout)
        self.vendor_head = nn.Linear(hidden_channels, 1)

    def forward(self, data: HeteroData) -> tuple[Tensor, Tensor]:
        x = self.layer1(data.x_dict, data.edge_index_dict)
        x = self.layer2(x, data.edge_index_dict)
        embeddings = x["vendor"]
        return self.vendor_head(embeddings).squeeze(-1), embeddings


def seed_torch(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
