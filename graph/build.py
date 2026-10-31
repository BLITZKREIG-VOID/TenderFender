"""Build the internal heterogeneous procurement graph from P2 CSV data.

The builder intentionally does not read ``labels.json``. Node IDs are keys for
joining records, while the ``features`` dictionaries contain only observed
attributes suitable for later model preparation.
"""

from __future__ import annotations

import csv
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import networkx as nx


class GraphDataError(ValueError):
    """Raised when an input dataset cannot safely be represented as a graph."""


def _read_csv(data_dir: Path, filename: str, required: set[str]) -> list[dict[str, str]]:
    path = data_dir / filename
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise GraphDataError(f"{path} has no CSV header")
            missing = required - set(reader.fieldnames)
            if missing:
                raise GraphDataError(
                    f"{path} is missing required columns: {', '.join(sorted(missing))}"
                )
            return [dict(row) for row in reader]
    except OSError as exc:
        raise GraphDataError(f"Could not read {path}: {exc}") from exc


def _required(row: dict[str, str], key: str, context: str) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise GraphDataError(f"{context} has an empty required field {key!r}")
    return value


def _number(row: dict[str, str], key: str, context: str, *, integer: bool = False) -> int | float:
    raw = _required(row, key, context)
    try:
        value: int | float = int(raw) if integer else float(raw)
    except ValueError as exc:
        raise GraphDataError(f"{context} has invalid numeric value {key}={raw!r}") from exc
    if isinstance(value, float) and not math.isfinite(value):
        raise GraphDataError(f"{context} has non-finite numeric value {key}={raw!r}")
    return value


def _unique_index(rows: list[dict[str, str]], key: str, filename: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows, start=2):
        value = _required(row, key, f"{filename}:{index}")
        if value in result:
            raise GraphDataError(f"Duplicate {key} {value!r} in {filename}")
        result[value] = row
    return result


def load_graph(data_dir: str | Path = "data") -> nx.MultiDiGraph:
    """Load the five structural CSVs and return an internal MultiDiGraph.

    ``MultiDiGraph`` preserves each typed relationship and its attributes.
    One vendor/tender bid is expected per pair, so a duplicate bid is rejected
    rather than silently overwritten.
    """
    root = Path(data_dir)
    vendors = _read_csv(root, "vendors.csv", {
        "vendor_id", "name", "turnover_cr", "years_experience",
        "registration_class", "address_id", "contact_id",
    })
    directors = _read_csv(root, "directors.csv", {"person_id", "name"})
    vendor_directors = _read_csv(root, "vendor_directors.csv", {"vendor_id", "person_id"})
    tenders = _read_csv(root, "tenders.csv", {
        "tender_id", "buyer_id", "title", "estimated_value_cr", "bid_days", "open_date",
    })
    bids = _read_csv(root, "bids.csv", {
        "tender_id", "vendor_id", "bid_amount_cr", "bid_ratio", "rank", "won", "submitted_at",
    })

    vendor_by_id = _unique_index(vendors, "vendor_id", "vendors.csv")
    director_by_id = _unique_index(directors, "person_id", "directors.csv")
    tender_by_id = _unique_index(tenders, "tender_id", "tenders.csv")
    graph = nx.MultiDiGraph()

    for vendor_id in sorted(vendor_by_id):
        row = vendor_by_id[vendor_id]
        name = _required(row, "name", f"vendor {vendor_id}")
        turnover = _number(row, "turnover_cr", f"vendor {vendor_id}")
        experience = _number(row, "years_experience", f"vendor {vendor_id}", integer=True)
        registration_class = _required(row, "registration_class", f"vendor {vendor_id}")
        if registration_class not in {"MSE", "Class-A", "Class-B", "Class-C"}:
            raise GraphDataError(f"Vendor {vendor_id} has unsupported registration_class {registration_class!r}")
        graph.add_node(
            vendor_id,
            type="vendor",
            label=name,
            features={
                "turnover_cr": turnover,
                "years_experience": experience,
                "registration_class": registration_class,
            },
        )

    for person_id in sorted(director_by_id):
        row = director_by_id[person_id]
        if person_id in graph:
            raise GraphDataError(f"Person ID {person_id!r} collides with another entity ID")
        graph.add_node(person_id, type="person", label=_required(row, "name", f"director {person_id}"), features={})

    for tender_id in sorted(tender_by_id):
        row = tender_by_id[tender_id]
        if tender_id in graph:
            raise GraphDataError(f"Tender ID {tender_id!r} collides with another entity ID")
        buyer_id = _required(row, "buyer_id", f"tender {tender_id}")
        title = _required(row, "title", f"tender {tender_id}")
        estimated = _number(row, "estimated_value_cr", f"tender {tender_id}")
        bid_days = _number(row, "bid_days", f"tender {tender_id}", integer=True)
        open_date = _required(row, "open_date", f"tender {tender_id}")
        try:
            date.fromisoformat(open_date)
        except ValueError as exc:
            raise GraphDataError(f"Tender {tender_id} has invalid open_date {open_date!r}") from exc
        graph.add_node(
            tender_id,
            type="tender",
            label=title,
            features={"estimated_value_cr": estimated, "bid_days": bid_days, "open_date": open_date},
        )
        if buyer_id in graph and graph.nodes[buyer_id].get("type") != "buyer":
            raise GraphDataError(f"Buyer ID {buyer_id!r} collides with another entity ID")
        if buyer_id not in graph:
            graph.add_node(buyer_id, type="buyer", label=f"Buyer {buyer_id}", features={})
        graph.add_edge(tender_id, buyer_id, key="issued_by", type="issued_by")

    seen_director_edges: set[tuple[str, str]] = set()
    for index, row in enumerate(vendor_directors, start=2):
        context = f"vendor_directors.csv:{index}"
        vendor_id = _required(row, "vendor_id", context)
        person_id = _required(row, "person_id", context)
        if vendor_id not in vendor_by_id:
            raise GraphDataError(f"{context} references unknown vendor {vendor_id!r}")
        if person_id not in director_by_id:
            raise GraphDataError(f"{context} references unknown person {person_id!r}")
        pair = (vendor_id, person_id)
        if pair in seen_director_edges:
            raise GraphDataError(f"Duplicate vendor/director relationship {pair!r}")
        seen_director_edges.add(pair)
        graph.add_edge(vendor_id, person_id, key="directed_by", type="directed_by")

    # Address and contact entities have IDs but no metadata tables. Their node
    # labels therefore expose only the opaque source ID.
    seen_addresses: set[str] = set()
    seen_contacts: set[str] = set()
    for vendor_id in sorted(vendor_by_id):
        row = vendor_by_id[vendor_id]
        address_id = (row.get("address_id") or "").strip()
        contact_id = (row.get("contact_id") or "").strip()
        if address_id:
            if address_id not in seen_addresses:
                if address_id in graph and graph.nodes[address_id].get("type") != "address":
                    raise GraphDataError(f"Address ID {address_id!r} collides with another entity ID")
                graph.add_node(address_id, type="address", label=f"Address {address_id}", features={})
                seen_addresses.add(address_id)
            graph.add_edge(vendor_id, address_id, key="located_at", type="located_at")
        if contact_id:
            if contact_id not in seen_contacts:
                if contact_id in graph and graph.nodes[contact_id].get("type") != "contact":
                    raise GraphDataError(f"Contact ID {contact_id!r} collides with another entity ID")
                graph.add_node(contact_id, type="contact", label=f"Contact {contact_id}", features={})
                seen_contacts.add(contact_id)
            graph.add_edge(vendor_id, contact_id, key="has_contact", type="has_contact")

    seen_bids: set[tuple[str, str]] = set()
    winner_count: dict[str, int] = {tender_id: 0 for tender_id in tender_by_id}
    rank_seen: set[tuple[str, int]] = set()
    for index, row in enumerate(bids, start=2):
        context = f"bids.csv:{index}"
        tender_id = _required(row, "tender_id", context)
        vendor_id = _required(row, "vendor_id", context)
        if tender_id not in tender_by_id:
            raise GraphDataError(f"{context} references unknown tender {tender_id!r}")
        if vendor_id not in vendor_by_id:
            raise GraphDataError(f"{context} references unknown vendor {vendor_id!r}")
        pair = (vendor_id, tender_id)
        if pair in seen_bids:
            raise GraphDataError(f"Duplicate bid for vendor {vendor_id} on tender {tender_id}")
        seen_bids.add(pair)
        rank = int(_number(row, "rank", context, integer=True))
        if rank < 1 or (tender_id, rank) in rank_seen:
            raise GraphDataError(f"{context} has invalid or duplicate rank {rank} for {tender_id}")
        rank_seen.add((tender_id, rank))
        won_raw = _required(row, "won", context)
        if won_raw not in {"0", "1"}:
            raise GraphDataError(f"{context} has invalid won value {won_raw!r}")
        if won_raw == "1":
            winner_count[tender_id] += 1
        submitted_at = _required(row, "submitted_at", context)
        try:
            datetime.fromisoformat(submitted_at)
        except ValueError as exc:
            raise GraphDataError(f"{context} has invalid submitted_at {submitted_at!r}") from exc
        graph.add_edge(
            vendor_id,
            tender_id,
            key=f"bid:{tender_id}:{vendor_id}",
            type="submitted_bid",
            features={
                "bid_amount_cr": _number(row, "bid_amount_cr", context),
                "bid_ratio": _number(row, "bid_ratio", context),
                "rank": rank,
                "won": won_raw == "1",
                "submitted_at": submitted_at,
            },
        )

    for tender_id, count in winner_count.items():
        if count != 1:
            raise GraphDataError(f"Tender {tender_id} must have exactly one winning bid; found {count}")

    return graph


def build_graph(data_dir: str | Path = "data") -> nx.MultiDiGraph:
    """Public builder alias used by the graph pipeline."""
    return load_graph(data_dir)
