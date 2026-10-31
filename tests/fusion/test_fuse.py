"""Behavior of the fusion rule (SoT 8.4, Boss decision D10). Fixtures only; no dependency on data/."""

import csv
import json

import pytest

from fusion.fuse import fuse
from fusion.run import InputError, main, run


def finding(fid="F-1", ftype="contradiction", severity="high"):
    return {"finding_id": fid, "type": ftype, "severity": severity, "clause_ids": ["CL2", "CL5"],
            "source_texts": ["a", "b"], "proof": {"method": "z3_unsat_core", "detail": "x"},
            "explanation": "Clauses cannot both hold."}


def rules(tid, findings=(), qualifiers=()):
    return {"tender_id": tid, "formalization_status": "unconfirmed", "atoms": [],
            "findings": list(findings), "qualifying_vendors": list(qualifiers), "vendors_evaluated": 200}


def ring(rid, vendors, score=0.9, links=("shared_director",)):
    return {"ring_id": rid, "vendor_ids": list(vendors), "link_types": list(links), "score": score}


def graph(rings, paths=()):
    return {"vendor_scores": {}, "rings": list(rings), "paths": list(paths), "graph": {"nodes": [], "edges": []},
            "metrics": {}}


R1 = ring("R-1", ["V-045", "V-046", "V-047"], 0.91, ("shared_director", "shared_address"))
PATH = {"from": "V-047", "to": "V-045", "nodes": ["V-047", "P-010", "V-045"], "edge_types": ["directed_by"] * 2}


def test_contradiction_without_ring_bidders_is_medium_review():
    out = fuse(rules("T-001", [finding()]), graph([R1]), {"V-001", "V-002"}, "t")
    assert (out["risk_level"], out["decision"]) == ("medium", "review")
    assert out["linked_vendors"] == [] and out["graph_flag_ring_ids"] == []
    assert out["rule_finding_ids"] == ["F-1"]


def test_tailored_with_unique_qualifier_in_flagged_ring_is_high_escalate():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-047"])
    out = fuse(r, graph([R1], [PATH]), {"V-001"}, "t")
    assert (out["risk_level"], out["decision"]) == ("high", "escalate")
    lv = out["linked_vendors"][0]
    assert lv == {"vendor_id": "V-047", "reason": "unique_qualifier_in_flagged_ring", "ring_id": "R-1",
                  "path": ["V-047", "P-010", "V-045"]}
    assert out["graph_flag_ring_ids"] == ["R-1"]
    assert out["_inputs"]["rings"] == [R1] and out["_inputs"]["findings"] == r["findings"]


def test_unique_qualifier_listed_first_then_bidders_sorted_with_fallback_path():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-047"])
    r2 = ring("R-2", ["V-100", "V-101"], 0.74, ("bid_rotation",))
    out = fuse(r, graph([r2, R1], [PATH]), {"V-101", "V-100", "V-047"}, "t")
    assert [(v["vendor_id"], v["reason"]) for v in out["linked_vendors"]] == [
        ("V-047", "unique_qualifier_in_flagged_ring"),
        ("V-100", "bidder_in_flagged_ring"), ("V-101", "bidder_in_flagged_ring")]
    assert out["linked_vendors"][1]["path"] == ["V-100"]  # no graph path from V-100
    assert out["graph_flag_ring_ids"] == ["R-1", "R-2"]


def test_clean_tender_with_qualifiers_in_rings_but_bidders_outside_is_low_clear():
    """Dropped trigger: qualifiers that did not bid no longer count."""
    r = rules("T-003", [], ["V-045", "V-046", "V-047", "V-001"])
    out = fuse(r, graph([R1]), {"V-001", "V-002"}, "t")
    assert (out["risk_level"], out["decision"]) == ("low", "clear")
    assert out["linked_vendors"] == [] and out["graph_flag_ring_ids"] == []


def test_bidder_in_flagged_ring_without_findings_is_medium():
    out = fuse(rules("T-009"), graph([R1]), {"V-046", "V-001"}, "t")
    assert (out["risk_level"], out["decision"]) == ("medium", "review")
    assert [v["vendor_id"] for v in out["linked_vendors"]] == ["V-046"]
    assert out["linked_vendors"][0]["reason"] == "bidder_in_flagged_ring"


@pytest.mark.parametrize("score,expected", [(0.49, "low"), (0.5, "medium")])
def test_ring_score_boundary(score, expected):
    out = fuse(rules("T-009"), graph([ring("R-1", ["V-001", "V-002"], score)]), {"V-001"}, "t")
    assert out["risk_level"] == expected


def test_tailored_but_qualifier_not_in_flagged_ring_is_medium():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-200"])
    out = fuse(r, graph([R1]), {"V-001"}, "t")
    assert (out["risk_level"], out["decision"]) == ("medium", "review")
    assert out["linked_vendors"] == []


def test_tailored_with_two_qualifiers_is_not_high():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-045", "V-047"])
    assert fuse(r, graph([R1]), set(), "t")["risk_level"] == "medium"


def test_unflagged_ring_qualifier_does_not_make_high():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-047"])
    out = fuse(r, graph([ring("R-1", ["V-047", "V-046"], 0.4)]), set(), "t")
    assert out["risk_level"] == "medium"


def test_low_severity_finding_alone_is_low():
    out = fuse(rules("T-009", [finding("F-1", "no_qualifier", "low")]), graph([]), set(), "t")
    assert out["risk_level"] == "low"


def test_summary_uses_indicator_wording():
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-047"])
    s = fuse(r, graph([R1]), set(), "t")["summary"].lower()
    assert "risk indicators" in s
    for bad in ("corrupt", "guilty", "proves illegality"):
        assert bad not in s


# ------------------------------------------------------------------ CLI

def _setup(tmp_path, rules_obj):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "T-002.json").write_text(json.dumps(rules_obj))
    (tmp_path / "graph.json").write_text(json.dumps(graph([R1], [PATH])))
    data = tmp_path / "data"
    data.mkdir()
    with (data / "bids.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tender_id", "vendor_id", "bid_amount_cr", "bid_ratio", "rank", "won", "submitted_at"])
        w.writerow(["T-002", "V-001", 1, 1, 1, 1, "x"])
    with (data / "tenders.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tender_id", "buyer_id", "title", "estimated_value_cr", "bid_days", "open_date"])
        w.writerow(["T-002", "B-001", "CSV title", 1, 7, "x"])
    return data


def test_run_writes_fused_with_title_from_csv_fallback(tmp_path):
    r = rules("T-002", [finding("F-1", "tailored_eligibility")], ["V-047"])
    data = _setup(tmp_path, r)
    run(tmp_path / "rules", tmp_path / "graph.json", data, tmp_path / "out")
    rec = json.loads((tmp_path / "out" / "T-002.json").read_text())
    assert rec["title"] == "CSV title" and rec["risk_level"] == "high"


def test_title_prefers_tender_json(tmp_path):
    data = _setup(tmp_path, rules("T-002"))
    (data / "tenders").mkdir()
    (data / "tenders" / "T-002.json").write_text(json.dumps({"tender_id": "T-002", "title": "JSON title", "clauses": []}))
    run(tmp_path / "rules", tmp_path / "graph.json", data, tmp_path / "out")
    assert json.loads((tmp_path / "out" / "T-002.json").read_text())["title"] == "JSON title"


def test_missing_graph_is_clear_error_and_nonzero_exit(tmp_path, capsys):
    data = _setup(tmp_path, rules("T-002"))
    code = main(["--rules-dir", str(tmp_path / "rules"), "--graph", str(tmp_path / "nope.json"),
                 "--data-dir", str(data), "--out-dir", str(tmp_path / "out")])
    assert code != 0 and "missing input file" in capsys.readouterr().err


def test_missing_bids_raises(tmp_path):
    data = _setup(tmp_path, rules("T-002"))
    (data / "bids.csv").unlink()
    with pytest.raises(InputError, match="bids.csv"):
        run(tmp_path / "rules", tmp_path / "graph.json", data, tmp_path / "out")
