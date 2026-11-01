"""decision_review.py: claim splitting, evidence lookup, verdict carry-over.

Fixture text is a format example only, not a real tender or legal text.
"""
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "decision_review", Path(__file__).resolve().parents[2] / "scripts" / "decision_review.py")
dr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dr)

REASONING = ("Only one vendor qualifies [F-1]. The passage says X [KB-901]. "
             "Members share a director [R-1]. This sentence has no citation.")


def _setup(tmp_path):
    fused, kb, rules = tmp_path / "fused", tmp_path / "kb", tmp_path / "rules"
    for d in (fused, kb, rules):
        d.mkdir()
    (fused / "T-900.json").write_text(json.dumps({
        "tender_id": "T-900", "decision_source": "cache", "risk_level": "high",
        "decision": "escalate", "reasoning": REASONING}))
    (fused / "T-901.json").write_text(json.dumps({
        "tender_id": "T-901", "decision_source": "template", "risk_level": "low",
        "decision": "clear", "reasoning": "Template reasoning."}))
    (kb / "KB-901.md").write_text(
        "---\npassage_id: KB-901\nsource_title: FORMAT EXAMPLE, not a real tender\n"
        "source_url: https://example.invalid/x\nsection: Sec 1\n---\nFORMAT EXAMPLE | verbatim body.\n")
    (rules / "T-900.json").write_text(json.dumps({"findings": [{
        "finding_id": "F-1", "type": "t", "severity": "high", "clause_ids": ["CL1"],
        "source_texts": ["FORMAT EXAMPLE, not a real tender"], "proof": {"method": "m", "detail": "d"},
        "explanation": "expl"}]}))
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"rings": [{"ring_id": "R-1", "vendor_ids": ["V-1", "V-2"],
                                            "link_types": ["shared_director"], "score": 0.5}]}))
    return ["--fused-dir", str(fused), "--kb-dir", str(kb), "--rules-dir", str(rules),
            "--graph", str(graph), "--out", str(tmp_path / "review.md")]


def test_claims_and_evidence(tmp_path):
    args = _setup(tmp_path)
    assert dr.main(args) == 0
    text = (tmp_path / "review.md").read_text()
    assert "- claims: 4" in text
    assert "FORMAT EXAMPLE \\| verbatim body." in text  # full passage, pipe escaped
    assert "source_url: https://example.invalid/x" in text
    assert "explanation: expl" in text and "members: V-1, V-2" in text
    assert dr.NO_CITATION in text
    assert "template, fixed wording" in text


def test_verdicts_carried_over(tmp_path):
    args = _setup(tmp_path)
    out = tmp_path / "review.md"
    dr.main(args)
    first = out.read_text()
    assert dr.main(args) == 0 and out.read_text() == first  # deterministic

    lines = first.splitlines()
    idx = next(i for i, ln in enumerate(lines) if ln.startswith("| 2 | The passage says X"))
    assert lines[idx].endswith("|  |  |")
    lines[idx] = lines[idx][: -len("|  |  |")] + "| yes | checked vs passage |"
    out.write_text("\n".join(lines) + "\n")
    filled = out.read_text()

    assert dr.main(args) == 0
    again = out.read_text()
    assert again == filled
    assert again.count("| yes | checked vs passage |") == 1
