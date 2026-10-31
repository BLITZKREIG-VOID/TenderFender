"""Deterministic, label-free evidence screens and vendor risk explanations.

The baseline uses transparent heuristic points (not probabilities): shared
director 20, shared address 20, buyer rotation 30, repeated cover bidding 30.
Per-vendor evidence is deduplicated by signal and tender/resource; the final
score is the sum capped at 100 and normalized to [0, 1]. Group context is
reported separately and never adds points a second time.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import networkx as nx


MAX_SCORE = 100.0
SIGNAL_POINTS = {
    "shared_director": 20.0,
    "shared_address": 20.0,
    "bid_rotation": 30.0,
    "cover_bids": 30.0,
}
ROTATION_TENDER_CAP = 12
COVER_TENDER_CAP = 10
COVER_MIN_RATIO = 1.01
COVER_MAX_RATIO = 1.03
# A 1-3 % near-winner bid happens by chance on roughly one in five tenders, so
# a buyer's cover ring needs a support count chance does not reach (cap is 10).
COVER_MIN_TENDERS = 8


@dataclass(frozen=True, order=True)
class Evidence:
    """One deduplicated, auditable observation supporting a screen."""

    signal: str
    vendor_ids: tuple[str, ...]
    tender_ids: tuple[str, ...] = ()
    relationship_types: tuple[str, ...] = ()
    resource_ids: tuple[str, ...] = ()
    buyer_id: str | None = None
    bid_ratios: tuple[tuple[str, str, float], ...] = ()
    related_vendor_ids: tuple[str, ...] = ()
    winner_by_tender: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RingCandidate:
    vendor_ids: tuple[str, ...]
    link_types: tuple[str, ...]
    score: float
    screen: str
    anchor_id: str | None = None
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)


def _pairs(values: list[str]):
    return combinations(sorted(set(values)), 2)


def _ownership_observations(graph: nx.MultiDiGraph) -> list[Evidence]:
    resources: dict[tuple[str, str], list[str]] = defaultdict(list)
    for vendor_id, attrs in graph.nodes(data=True):
        if attrs.get("type") != "vendor":
            continue
        for _, target, edge_attrs in graph.out_edges(vendor_id, data=True):
            edge_type = edge_attrs.get("type")
            if edge_type in {"directed_by", "located_at"}:
                resources[(edge_type, target)].append(vendor_id)

    observations = []
    names = {"directed_by": "shared_director", "located_at": "shared_address"}
    for (edge_type, resource_id), vendor_ids in sorted(resources.items()):
        for left, right in _pairs(vendor_ids):
            observations.append(Evidence(
                signal=names[edge_type],
                vendor_ids=(left, right),
                relationship_types=(edge_type,),
                resource_ids=(resource_id,),
            ))
    return observations


def _ownership_rings(graph: nx.MultiDiGraph) -> list[RingCandidate]:
    pair_evidence: dict[tuple[str, str], set[str]] = defaultdict(set)
    pair_resources: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for item in _ownership_observations(graph):
        left, right = item.vendor_ids
        edge_type = item.relationship_types[0]
        pair_evidence[(left, right)].add(edge_type)
        pair_resources[(left, right, edge_type)].update(item.resource_ids)

    # Preserve the established screen rule: one shared attribute alone is
    # weak. A candidate ownership pair must share two distinct link types.
    pair_graph = nx.Graph()
    for (left, right), evidence in pair_evidence.items():
        if len(evidence) >= 2:
            pair_graph.add_edge(left, right, evidence=evidence)

    rings: list[RingCandidate] = []
    for component in nx.connected_components(pair_graph):
        members = tuple(sorted(component))
        evidence_types: set[str] = set()
        pair_scores: list[float] = []
        observations: list[Evidence] = []
        for left, right in combinations(members, 2):
            evidence = pair_evidence.get((left, right), set())
            if evidence:
                evidence_types.update(evidence)
                pair_scores.append(min(1.0, 0.35 * len(evidence)))
                for edge_type in sorted(evidence):
                    name = "shared_director" if edge_type == "directed_by" else "shared_address"
                    observations.append(Evidence(
                        signal=name,
                        vendor_ids=(left, right),
                        relationship_types=(edge_type,),
                        resource_ids=tuple(sorted(pair_resources[(left, right, edge_type)])),
                    ))
        if len(members) >= 2 and pair_scores:
            rings.append(RingCandidate(
                members,
                tuple(sorted({
                    "directed_by": "shared_director",
                    "located_at": "shared_address",
                }[kind] for kind in evidence_types)),
                max(pair_scores),
                "ownership",
                evidence=tuple(sorted(observations)),
            ))
    return rings


def _bid_observations(graph: nx.MultiDiGraph) -> tuple[dict[str, str], dict[str, list[tuple[str, dict[str, Any]]]]]:
    tender_buyers = {
        tender_id: buyer_id
        for tender_id, buyer_id, edge in graph.edges(data=True)
        if edge.get("type") == "issued_by"
    }
    bids_by_tender: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for vendor_id, tender_id, edge in graph.edges(data=True):
        if edge.get("type") == "submitted_bid":
            bids_by_tender[tender_id].append((vendor_id, edge["features"]))
    return tender_buyers, bids_by_tender


def _rotation_rings(graph: nx.MultiDiGraph) -> list[RingCandidate]:
    tender_buyers, bids_by_tender = _bid_observations(graph)
    tender_bidders: dict[str, set[str]] = defaultdict(set)
    tender_winners: dict[str, str] = {}
    for tender_id, bids in bids_by_tender.items():
        for vendor_id, attrs in bids:
            tender_bidders[tender_id].add(vendor_id)
            if attrs["won"]:
                tender_winners[tender_id] = vendor_id

    pair_tenders: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for tender_id, bidders in tender_bidders.items():
        buyer_id = tender_buyers.get(tender_id)
        if not buyer_id:
            continue
        for left, right in _pairs(list(bidders)):
            pair_tenders[(buyer_id, left, right)].append(tender_id)

    rings: list[RingCandidate] = []
    for buyer_id in sorted({key[0] for key in pair_tenders}):
        pair_graph = nx.Graph()
        for (pair_buyer, left, right), shared_tenders in pair_tenders.items():
            if pair_buyer == buyer_id and len(shared_tenders) >= 6:
                pair_graph.add_edge(left, right, tenders=tuple(sorted(shared_tenders)))

        for component in nx.connected_components(pair_graph):
            members = tuple(sorted(component))
            if len(members) < 3:
                continue
            shared_tenders: set[str] = set()
            for left, right in pair_graph.subgraph(members).edges:
                shared_tenders.update(pair_graph[left][right]["tenders"])
            tenders = tuple(sorted(shared_tenders))
            winners = {tender_winners[tender] for tender in tenders if tender in tender_winners}
            if len(winners.intersection(members)) != len(members):
                continue
            repetition = min(1.0, len(tenders) / ROTATION_TENDER_CAP)
            winner_coverage = len(winners.intersection(members)) / len(members)
            score = round(0.6 * repetition + 0.4 * winner_coverage, 4)
            if score >= 0.5:
                rings.append(RingCandidate(
                    members, ("bid_rotation",), score, "rotation", buyer_id,
                    (Evidence(
                        "bid_rotation", members, tenders,
                        ("issued_by", "submitted_bid"), (buyer_id,), buyer_id,
                        winner_by_tender=tuple(sorted(
                            (tender, tender_winners[tender])
                            for tender in tenders if tender in tender_winners
                        )),
                    ),),
                ))
    return rings


def _cover_rings(graph: nx.MultiDiGraph) -> list[RingCandidate]:
    tender_buyers, bids_by_tender = _bid_observations(graph)
    cover_events: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for tender_id, bids in bids_by_tender.items():
        winners = [(vendor, attrs) for vendor, attrs in bids if attrs["won"]]
        if len(winners) != 1:
            continue
        winner_id, winner_attrs = winners[0]
        winner_amount = winner_attrs["bid_amount_cr"]
        if winner_amount <= 0:
            continue
        buyer_id = tender_buyers.get(tender_id)
        if not buyer_id:
            continue
        for vendor_id, attrs in bids:
            if vendor_id == winner_id:
                continue
            relative = attrs["bid_amount_cr"] / winner_amount
            if COVER_MIN_RATIO <= relative <= COVER_MAX_RATIO:
                cover_events[buyer_id].append((vendor_id, tender_id, relative))

    rings: list[RingCandidate] = []
    for buyer_id, events in sorted(cover_events.items()):
        members = tuple(sorted({vendor for vendor, _, _ in events}))
        distinct_tenders = {tender for _, tender, _ in events}
        if len(members) < 2 or len(distinct_tenders) < COVER_MIN_TENDERS:
            continue
        score = round(min(1.0, len(distinct_tenders) / COVER_TENDER_CAP), 4)
        grouped_events: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        for vendor_id, tender_id, ratio in events:
            winner_id = next(
                vendor for vendor, attrs in bids_by_tender[tender_id] if attrs["won"]
            )
            grouped_events[vendor_id].append((tender_id, ratio, winner_id))
        observations = tuple(sorted(
            Evidence(
                "cover_bids",
                (vendor_id,),
                tuple(sorted(tender_id for tender_id, _, _ in vendor_events)),
                ("issued_by", "submitted_bid"),
                (buyer_id,),
                buyer_id,
                tuple(sorted((tender_id, vendor_id, ratio) for tender_id, ratio, _ in vendor_events)),
                tuple(sorted({winner for _, _, winner in vendor_events})),
                tuple(sorted((tender_id, winner) for tender_id, _, winner in vendor_events)),
            )
            for vendor_id, vendor_events in grouped_events.items()
        ))
        if score >= 0.5:
            rings.append(RingCandidate(
                members, ("cover_bids",), score, "cover", buyer_id, observations,
            ))
    return rings


def find_rings(graph: nx.MultiDiGraph) -> list[RingCandidate]:
    """Return deterministic candidates derived only from observed graph data."""
    candidates = [*_ownership_rings(graph), *_rotation_rings(graph), *_cover_rings(graph)]
    screen_order = {"ownership": 0, "rotation": 1, "cover": 2}
    return sorted(candidates, key=lambda item: (
        screen_order[item.screen], item.vendor_ids, item.anchor_id or "",
    ))


def _category(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.40:
        return "elevated"
    if score >= 0.20:
        return "guarded"
    return "low"


def explain_vendors(
    graph: nx.MultiDiGraph,
    rings: list[RingCandidate] | None = None,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Score vendors and return evidence explanations without evaluation labels."""
    rings = rings if rings is not None else find_rings(graph)
    by_vendor: dict[str, list[Evidence]] = defaultdict(list)
    for item in _ownership_observations(graph):
        for vendor_id in item.vendor_ids:
            by_vendor[vendor_id].append(item)
    for ring in rings:
        for item in ring.evidence:
            for vendor_id in item.vendor_ids:
                by_vendor[vendor_id].append(item)

    scores: dict[str, float] = {}
    explanations: list[dict[str, Any]] = []
    vendors = sorted(node for node, attrs in graph.nodes(data=True) if attrs.get("type") == "vendor")
    for vendor_id in vendors:
        evidence_by_signal: dict[str, list[Evidence]] = defaultdict(list)
        for item in by_vendor.get(vendor_id, ()):
            evidence_by_signal[item.signal].append(item)

        points = 0.0
        if evidence_by_signal.get("shared_director"):
            points += SIGNAL_POINTS["shared_director"]
        if evidence_by_signal.get("shared_address"):
            points += SIGNAL_POINTS["shared_address"]
        rotation_tenders = {
            tender for item in evidence_by_signal.get("bid_rotation", ()) for tender in item.tender_ids
        }
        if rotation_tenders:
            points += SIGNAL_POINTS["bid_rotation"] * min(1.0, len(rotation_tenders) / ROTATION_TENDER_CAP)
        cover_tenders = {
            tender for item in evidence_by_signal.get("cover_bids", ()) for tender in item.tender_ids
        }
        if cover_tenders:
            points += SIGNAL_POINTS["cover_bids"] * min(1.0, len(cover_tenders) / COVER_TENDER_CAP)
        normalized = round(min(MAX_SCORE, points) / MAX_SCORE, 4)
        scores[vendor_id] = normalized
        if not any(evidence_by_signal.values()):
            continue

        relevant = [item for values in evidence_by_signal.values() for item in values]
        related_vendors = sorted({
            other
            for item in relevant
            for other in (*item.vendor_ids, *item.related_vendor_ids)
            if other != vendor_id
        })
        tender_ids = sorted({tender for item in relevant for tender in item.tender_ids})
        relationship_types = sorted({rel for item in relevant for rel in item.relationship_types})
        evidence_types = sorted(signal for signal, items in evidence_by_signal.items() if items)
        group_context = []
        for ring in rings:
            if vendor_id in ring.vendor_ids:
                group_context.append({
                    "screen": ring.screen,
                    "vendor_ids": list(ring.vendor_ids),
                    "anchor_id": ring.anchor_id,
                    "score": ring.score,
                })
        detail = []
        for item in sorted(set(relevant)):
            detail.append({
                "type": item.signal,
                "vendor_ids": list(item.vendor_ids),
                "related_vendor_ids": sorted({
                    other for other in (*item.vendor_ids, *item.related_vendor_ids)
                    if other != vendor_id
                }),
                "tender_ids": list(item.tender_ids),
                "relationship_types": list(item.relationship_types),
                "resource_ids": list(item.resource_ids),
                "buyer_id": item.buyer_id,
                "bid_ratios": [
                    {"tender_id": tender, "vendor_id": vendor, "ratio": round(ratio, 6)}
                    for tender, vendor, ratio in item.bid_ratios
                ],
                "winning_bids": [
                    {"tender_id": tender, "winner_vendor_id": winner}
                    for tender, winner in item.winner_by_tender
                ],
            })
        descriptions = {
            "shared_director": "Shares one or more directors with another vendor.",
            "shared_address": "Shares a registered address with another vendor.",
            "bid_rotation": "Repeatedly bids alongside a same-buyer group whose members rotate wins.",
            "cover_bids": "Submitted repeated bids 1–3% above another vendor's winning bid.",
        }
        explanation = " ".join(descriptions[signal] for signal in evidence_types)
        explanations.append({
            "vendor_id": vendor_id,
            "risk_score": normalized,
            "risk_category": _category(normalized),
            "evidence_types": evidence_types,
            "related_vendor_ids": related_vendors,
            "tender_ids": tender_ids,
            "relationship_types": relationship_types,
            "evidence": detail,
            "groups": group_context,
            "explanation": explanation,
        })
    return dict(sorted(scores.items())), explanations


def score_vendors(graph: nx.MultiDiGraph, rings: list[RingCandidate] | None = None) -> dict[str, float]:
    """Return each vendor's deterministic normalized heuristic score [0, 1]."""
    return explain_vendors(graph, rings)[0]
