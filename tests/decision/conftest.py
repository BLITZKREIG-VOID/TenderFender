from pathlib import Path

import pytest

FIXTURE_KB = Path(__file__).parent / "fixtures" / "kb"


@pytest.fixture
def kb_dir():
    return FIXTURE_KB


def make_fusion(tid="T-002", with_ring=True, risk="high", decision="escalate"):
    findings = [{
        "finding_id": "F-1", "type": "tailored_eligibility", "severity": "high",
        "clause_ids": ["CL2", "CL3"], "source_texts": ["Only Class-A contractors", "turnover of at least 100 crore"],
        "proof": {"method": "x", "detail": "exactly 1 of 200 vendors qualifies: V-047"},
        "explanation": "Eligibility criteria are met by exactly one vendor, tailored eligibility turnover."}]
    rings = [{"ring_id": "R-1", "vendor_ids": ["V-045", "V-046", "V-047"],
              "link_types": ["shared_director", "shared_address"], "score": 0.91}] if with_ring else []
    return {"tender_id": tid, "title": "T", "risk_level": risk, "rule_finding_ids": ["F-1"],
            "graph_flag_ring_ids": ["R-1"] if with_ring else [],
            "linked_vendors": [{"vendor_id": "V-047", "reason": "unique_qualifier_in_flagged_ring",
                                "ring_id": "R-1", "path": ["V-047", "P-010", "V-045"]}] if with_ring else [],
            "summary": "Risk indicators for T.", "decision": decision,
            "_inputs": {"findings": findings, "rings": rings}}


def make_empty_fusion(tid="T-003"):
    f = make_fusion(tid, with_ring=False, risk="low", decision="clear")
    f["rule_finding_ids"] = []
    f["_inputs"]["findings"] = []
    return f
