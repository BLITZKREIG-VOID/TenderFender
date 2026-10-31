"""Create the compact display graph and auditable paths for the API/UI."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any

import networkx as nx

from graph.screens import RingCandidate


DISPLAY_NODE_TYPES = {"vendor", "person", "address", "buyer"}


def _display_projection(
    graph: nx.MultiDiGraph,
    rings: list[RingCandidate],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    for ring in rings:
        members = set(ring.vendor_ids)
        for vendor_id in ring.vendor_ids:
            attrs = graph.nodes[vendor_id]
            nodes[vendor_id] = {
                "id": vendor_id,
                "type": "vendor",
                "label": attrs["label"],
                "flagged": True,
            }

        # Include only shared director/address connectors that explain the
        # ownership screen. Contacts remain internal per the agreed UI shape.
        if ring.screen == "ownership":
            for vendor_id in ring.vendor_ids:
                for _, target, edge in graph.out_edges(vendor_id, data=True):
                    edge_type = edge.get("type")
                    if edge_type not in {"directed_by", "located_at"}:
                        continue
                    connected_members = {
                        source for source, _, incoming in graph.in_edges(target, data=True)
                        if incoming.get("type") == edge_type and source in members
                    }
                    if len(connected_members) < 2:
                        continue
                    attrs = graph.nodes[target]
                    nodes[target] = {
                        "id": target,
                        "type": attrs["type"],
                        "label": attrs["label"],
                        "flagged": False,
                    }
                    edges[(vendor_id, target, edge_type)] = {
                        "source": vendor_id, "target": target, "type": edge_type,
                    }

        # Buyer nodes are display connectors for rotation/cover evidence. The
        # internal bidder->tender->buyer path is collapsed only here.
        if ring.screen in {"rotation", "cover"} and ring.anchor_id:
            buyer_id = ring.anchor_id
            buyer_attrs = graph.nodes[buyer_id]
            nodes[buyer_id] = {
                "id": buyer_id,
                "type": "buyer",
                "label": buyer_attrs["label"],
                "flagged": False,
            }
            tenders_for_buyer = {
                tender_id for tender_id, target, edge in graph.edges(data=True)
                if edge.get("type") == "issued_by" and target == buyer_id
            }
            for vendor_id in ring.vendor_ids:
                if any(
                    target in tenders_for_buyer and edge.get("type") == "submitted_bid"
                    for _, target, edge in graph.out_edges(vendor_id, data=True)
                ):
                    edges[(vendor_id, buyer_id, "bid_to")] = {
                        "source": vendor_id, "target": buyer_id, "type": "bid_to",
                    }

    return nodes, edges


def build_paths(
    rings: list[RingCandidate],
    nodes: dict[str, dict[str, Any]],
    edges: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit shortest display paths between flagged vendors in each ring."""
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source, target, edge_type in edges:
        adjacency[source].append((target, edge_type))
        adjacency[target].append((source, edge_type))

    output: list[dict[str, Any]] = []
    for ring in rings:
        for source, target in combinations(ring.vendor_ids, 2):
            queue: list[tuple[str, list[str], list[str]]] = [(source, [source], [])]
            visited = {source}
            found: tuple[list[str], list[str]] | None = None
            while queue:
                current, path_nodes, path_types = queue.pop(0)
                if current == target:
                    found = (path_nodes, path_types)
                    break
                for neighbor, edge_type in sorted(adjacency[current]):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    queue.append((neighbor, [*path_nodes, neighbor], [*path_types, edge_type]))
            if found:
                path_nodes, path_types = found
                output.append({"from": source, "to": target, "nodes": path_nodes, "edge_types": path_types})
                output.append({"from": target, "to": source, "nodes": list(reversed(path_nodes)), "edge_types": list(reversed(path_types))})
    return sorted(output, key=lambda path: (path["from"], path["to"]))


def build_display_graph(
    graph: nx.MultiDiGraph,
    rings: list[RingCandidate],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    nodes, edges = _display_projection(graph, rings)
    display = {
        "nodes": [nodes[node_id] for node_id in sorted(nodes) if nodes[node_id]["type"] in DISPLAY_NODE_TYPES],
        "edges": [edges[key] for key in sorted(edges)],
    }
    return display, build_paths(rings, nodes, edges)
