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


# Connector preference when several equally short display paths link two vendors:
# a shared director is the stronger ownership link (SoT section 8.3 example),
# then a shared address, then same-buyer bidding.
_CONNECTOR_PRIORITY = {"directed_by": 0, "located_at": 1, "bid_to": 2}


def _shortest_paths(
    adjacency: dict[str, list[tuple[str, str]]], source: str, target: str,
) -> list[tuple[list[str], list[str]]]:
    """Return every shortest (nodes, edge_types) path from source to target."""
    distance = {source: 0}
    queue = [source]
    for current in queue:
        if current == target:
            break
        for neighbor, _ in adjacency[current]:
            if neighbor not in distance:
                distance[neighbor] = distance[current] + 1
                queue.append(neighbor)
    if target not in distance:
        return []

    found: list[tuple[list[str], list[str]]] = []

    def walk(current: str, nodes: list[str], types: list[str]) -> None:
        if current == target:
            found.append((nodes, types))
            return
        for neighbor, edge_type in sorted(set(adjacency[current])):
            if distance.get(neighbor) == distance[current] + 1 and distance[neighbor] <= distance[target]:
                walk(neighbor, [*nodes, neighbor], [*types, edge_type])

    walk(source, [source], [])
    return found


def build_paths(
    rings: list[RingCandidate],
    nodes: dict[str, dict[str, Any]],
    edges: dict[tuple[str, str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit every shortest display path between flagged vendors in each ring.

    For one vendor pair, a shared-director path sorts before a shared-address path.
    """
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for source, target, edge_type in edges:
        adjacency[source].append((target, edge_type))
        adjacency[target].append((source, edge_type))

    output: list[dict[str, Any]] = []
    for ring in rings:
        for source, target in combinations(ring.vendor_ids, 2):
            for path_nodes, path_types in _shortest_paths(adjacency, source, target):
                output.append({"from": source, "to": target, "nodes": path_nodes, "edge_types": path_types})
                output.append({"from": target, "to": source, "nodes": list(reversed(path_nodes)), "edge_types": list(reversed(path_types))})
    return sorted(output, key=lambda path: (
        path["from"], path["to"],
        [_CONNECTOR_PRIORITY.get(edge_type, 9) for edge_type in path["edge_types"]],
        path["nodes"],
    ))


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
