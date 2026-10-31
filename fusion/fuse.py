"""Deterministic fusion of rule findings and graph rings (SoT 8.4). Pure logic, no I/O."""

from __future__ import annotations

RING_FLAG_THRESHOLD = 0.5
DECISION_BY_RISK = {"low": "clear", "medium": "review", "high": "escalate"}
UNIQUE_REASON = "unique_qualifier_in_flagged_ring"
BIDDER_REASON = "bidder_in_flagged_ring"


def _ring_sort_key(ring: dict) -> tuple[int, str]:
    rid = ring["ring_id"]
    suffix = rid.split("-", 1)[1]
    return (int(suffix) if suffix.isdigit() else 10**9, rid)


def flagged_rings(graph: dict) -> list[dict]:
    """Rings with score >= RING_FLAG_THRESHOLD, ordered by numeric ring id."""
    rings = [r for r in graph["rings"] if r["score"] >= RING_FLAG_THRESHOLD]
    return sorted(rings, key=_ring_sort_key)


def unique_qualifier(rules: dict) -> str | None:
    """The single qualifying vendor if a tailored_eligibility finding exists with exactly one qualifier."""
    tailored = any(f["type"] == "tailored_eligibility" for f in rules["findings"])
    qualifiers = rules["qualifying_vendors"]
    if tailored and len(qualifiers) == 1:
        return qualifiers[0]
    return None


def risk_level(rules: dict, rings: list[dict], bidders: set[str]) -> str:
    """high: tailored_eligibility with exactly 1 qualifier in a flagged ring.
    medium: any high-severity finding, or any bidder in a flagged ring. else low."""
    flagged_members = {v for r in rings for v in r["vendor_ids"]}
    uq = unique_qualifier(rules)
    if uq is not None and uq in flagged_members:
        return "high"
    if any(f["severity"] == "high" for f in rules["findings"]):
        return "medium"
    if bidders & flagged_members:
        return "medium"
    return "low"


def _link(vendor: str, reason: str, rings: list[dict], graph: dict) -> dict:
    containing = [r for r in rings if vendor in r["vendor_ids"]]
    # highest-score ring first; ties broken by ring id
    best = sorted(containing, key=lambda r: (-r["score"], _ring_sort_key(r)))[0]
    path = next((p["nodes"] for p in graph["paths"] if p["from"] == vendor), [vendor])
    return {"vendor_id": vendor, "reason": reason, "ring_id": best["ring_id"], "path": list(path)}


def _summary(tender_id: str, findings: list[dict], uq_in_ring: str | None,
             ring_bidders: list[str], risk: str) -> str:
    if findings:
        parts = [f"{len(findings)} rule finding(s) ("
                 + ", ".join(f"{f['finding_id']}: {f['type']}" for f in findings) + ")"]
    else:
        parts = ["no rule findings"]
    if uq_in_ring:
        parts.append(f"the unique qualifier {uq_in_ring} is in a flagged ring")
    if ring_bidders:
        parts.append(f"{len(ring_bidders)} bidder(s) in flagged rings (" + ", ".join(ring_bidders) + ")")
    else:
        parts.append("no bidder belongs to a flagged ring")
    return f"Risk indicators for {tender_id}: " + "; ".join(parts) + f". Risk level: {risk}."


def fuse(rules: dict, graph: dict, bidders: set[str], title: str) -> dict:
    """Build the intermediate fused record (deterministic §8.4 fields + `_inputs`)."""
    tender_id = rules["tender_id"]
    rings = flagged_rings(graph)
    uq = unique_qualifier(rules)
    flagged_members = {v for r in rings for v in r["vendor_ids"]}
    uq_in_ring = uq if uq in flagged_members else None
    ring_bidders = sorted(b for b in bidders if b in flagged_members)

    risk = risk_level(rules, rings, bidders)

    linked: list[dict] = []
    if uq_in_ring:
        linked.append(_link(uq_in_ring, UNIQUE_REASON, rings, graph))
    for b in ring_bidders:
        if b != uq_in_ring:
            linked.append(_link(b, BIDDER_REASON, rings, graph))

    relevant = {v for v in ([uq_in_ring] if uq_in_ring else []) + ring_bidders}
    referenced = [r for r in rings if relevant & set(r["vendor_ids"])]

    return {
        "tender_id": tender_id,
        "title": title,
        "risk_level": risk,
        "rule_finding_ids": [f["finding_id"] for f in rules["findings"]],
        "graph_flag_ring_ids": [r["ring_id"] for r in referenced],
        "linked_vendors": linked,
        "summary": _summary(tender_id, rules["findings"], uq_in_ring, ring_bidders, risk),
        "decision": DECISION_BY_RISK[risk],
        "_inputs": {"findings": rules["findings"], "rings": referenced},
    }
