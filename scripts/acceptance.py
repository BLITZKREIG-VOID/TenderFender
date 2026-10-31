#!/usr/bin/env python3
"""Acceptance test harness for TenderFender Definition of Done (SoT section 12).

Checks file-verifiable DoD criteria across rules, graph, fusion, data, and knowledge base.
Prints one PASS / FAIL / MISSING line per check, with reason on failure/missing.
Exits 0 only if every check PASSes.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

SOT_DISCLAIMER = "Risk indicators only; not a finding of wrongdoing. Recommendation requires human review."
DECISION_BY_RISK = {"low": "clear", "medium": "review", "high": "escalate"}


def parse_source_title(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip() == "source_title":
                return v.strip().strip('"').strip("'")
    return ""


def load_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, f"file not found: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, f"invalid JSON in {path}: {exc}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TenderFender DoD acceptance tests (SoT section 12)")
    ap.add_argument("--rules-dir", type=Path, default=Path("artifacts/rules"), help="Rules output directory")
    ap.add_argument("--graph", type=Path, default=Path("artifacts/graph/graph_output.json"), help="Graph output JSON")
    ap.add_argument("--fused-dir", type=Path, default=Path("artifacts/fused"), help="Fused output directory")
    ap.add_argument("--data-dir", type=Path, default=Path("data"), help="Data directory containing bids.csv")
    ap.add_argument("--kb-dir", type=Path, default=Path("kb/passages"), help="Knowledge base passages directory")
    args = ap.parse_args(argv)

    results: list[tuple[str, str, str]] = []  # (status, name, reason)

    def record_pass(name: str) -> None:
        results.append(("PASS", name, ""))

    def record_fail(name: str, reason: str) -> None:
        results.append(("FAIL", name, reason))

    def record_missing(name: str, reason: str) -> None:
        results.append(("MISSING", name, reason))

    # ------------------------------------------------------------------ T-001
    r_t1, err_r_t1 = load_json(args.rules_dir / "T-001.json")
    if err_r_t1:
        record_missing("T-001 rules: contradiction finding with clause_ids == ['CL2', 'CL5']", err_r_t1)
    else:
        findings = r_t1.get("findings", [])
        matched = any(
            f.get("type") == "contradiction" and f.get("clause_ids") == ["CL2", "CL5"]
            for f in findings
        )
        if matched:
            record_pass("T-001 rules: contradiction finding with clause_ids == ['CL2', 'CL5']")
        else:
            record_fail(
                "T-001 rules: contradiction finding with clause_ids == ['CL2', 'CL5']",
                f"expected contradiction with clause_ids == ['CL2', 'CL5'], got findings: {findings}",
            )

    f_t1, err_f_t1 = load_json(args.fused_dir / "T-001.json")
    if err_f_t1:
        record_missing("T-001 fused: risk_level == medium and decision == review", err_f_t1)
    else:
        risk = f_t1.get("risk_level")
        dec = f_t1.get("decision")
        if risk == "medium" and dec == "review":
            record_pass("T-001 fused: risk_level == medium and decision == review")
        else:
            record_fail(
                "T-001 fused: risk_level == medium and decision == review",
                f"expected risk_level='medium', decision='review'; got risk_level={risk!r}, decision={dec!r}",
            )

    # ------------------------------------------------------------------ T-002
    r_t2, err_r_t2 = load_json(args.rules_dir / "T-002.json")
    if err_r_t2:
        record_missing("T-002 rules: tailored_eligibility finding with qualifying_vendors == ['V-047']", err_r_t2)
        record_missing("T-002 rules: criteria clause_ids == ['CL2', 'CL3', 'CL4']", err_r_t2)
    else:
        te_findings = [f for f in r_t2.get("findings", []) if f.get("type") == "tailored_eligibility"]
        qv = r_t2.get("qualifying_vendors")
        if te_findings and qv == ["V-047"]:
            record_pass("T-002 rules: tailored_eligibility finding with qualifying_vendors == ['V-047']")
        else:
            record_fail(
                "T-002 rules: tailored_eligibility finding with qualifying_vendors == ['V-047']",
                f"has_tailored_eligibility={bool(te_findings)}, qualifying_vendors={qv}",
            )

        if not te_findings:
            record_fail(
                "T-002 rules: criteria clause_ids == ['CL2', 'CL3', 'CL4']",
                "no tailored_eligibility finding present",
            )
        else:
            cids = te_findings[0].get("clause_ids")
            if cids == ["CL2", "CL3", "CL4"]:
                record_pass("T-002 rules: criteria clause_ids == ['CL2', 'CL3', 'CL4']")
            else:
                record_fail(
                    "T-002 rules: criteria clause_ids == ['CL2', 'CL3', 'CL4']",
                    f"expected ['CL2', 'CL3', 'CL4'], got {cids}",
                )

    graph_doc, err_graph = load_json(args.graph)
    if err_graph:
        record_missing("T-002 graph: ring R-1 contains V-047 with score >= 0.5", err_graph)
    else:
        rings = graph_doc.get("rings", [])
        r1 = next((r for r in rings if r.get("ring_id") == "R-1"), None)
        if not r1:
            record_fail("T-002 graph: ring R-1 contains V-047 with score >= 0.5", "ring R-1 not found in graph")
        else:
            score = r1.get("score", 0.0)
            vids = r1.get("vendor_ids", [])
            if score >= 0.5 and "V-047" in vids:
                record_pass("T-002 graph: ring R-1 contains V-047 with score >= 0.5")
            else:
                record_fail(
                    "T-002 graph: ring R-1 contains V-047 with score >= 0.5",
                    f"R-1 score={score} (needs >= 0.5), vendor_ids={vids} (needs 'V-047')",
                )

    f_t2, err_f_t2 = load_json(args.fused_dir / "T-002.json")
    if err_f_t2:
        record_missing("T-002 fused: risk_level == high and decision == escalate", err_f_t2)
        record_missing("T-002 fused: linked_vendors[0] vendor_id == V-047, ring_id == R-1, path contains P-010", err_f_t2)
    else:
        risk = f_t2.get("risk_level")
        dec = f_t2.get("decision")
        if risk == "high" and dec == "escalate":
            record_pass("T-002 fused: risk_level == high and decision == escalate")
        else:
            record_fail(
                "T-002 fused: risk_level == high and decision == escalate",
                f"expected risk_level='high', decision='escalate'; got risk_level={risk!r}, decision={dec!r}",
            )

        lvs = f_t2.get("linked_vendors", [])
        if not lvs:
            record_fail(
                "T-002 fused: linked_vendors[0] vendor_id == V-047, ring_id == R-1, path contains P-010",
                "linked_vendors list is empty",
            )
        else:
            lv0 = lvs[0]
            vid = lv0.get("vendor_id")
            rid = lv0.get("ring_id")
            path = lv0.get("path", [])
            if vid == "V-047" and rid == "R-1" and "P-010" in path:
                record_pass("T-002 fused: linked_vendors[0] vendor_id == V-047, ring_id == R-1, path contains P-010")
            else:
                record_fail(
                    "T-002 fused: linked_vendors[0] vendor_id == V-047, ring_id == R-1, path contains P-010",
                    f"expected vendor_id='V-047', ring_id='R-1', 'P-010' in path; got vendor_id={vid!r}, ring_id={rid!r}, path={path}",
                )

    # ------------------------------------------------------------------ T-003
    r_t3, err_r_t3 = load_json(args.rules_dir / "T-003.json")
    if err_r_t3:
        record_missing("T-003 rules: zero findings", err_r_t3)
    else:
        findings = r_t3.get("findings", [])
        if len(findings) == 0:
            record_pass("T-003 rules: zero findings")
        else:
            record_fail("T-003 rules: zero findings", f"expected 0 findings, got {len(findings)}: {findings}")

    bids_csv = args.data_dir / "bids.csv"
    if not bids_csv.is_file():
        record_missing("T-003 bids/graph: no T-003 bidder belongs to a ring with score >= 0.5", f"{bids_csv} not found")
    elif err_graph:
        record_missing("T-003 bids/graph: no T-003 bidder belongs to a ring with score >= 0.5", err_graph)
    else:
        t3_bidders: set[str] = set()
        try:
            with open(bids_csv, mode="r", encoding="utf-8") as bf:
                reader = csv.DictReader(bf)
                for row in reader:
                    if row.get("tender_id") == "T-003":
                        t3_bidders.add(row.get("vendor_id", "").strip())
        except Exception as exc:
            record_fail("T-003 bids/graph: no T-003 bidder belongs to a ring with score >= 0.5", f"failed to read {bids_csv}: {exc}")
            t3_bidders = set()

        if t3_bidders:
            flagged_vendors: set[str] = set()
            for r in graph_doc.get("rings", []):
                if r.get("score", 0.0) >= 0.5:
                    flagged_vendors.update(r.get("vendor_ids", []))
            overlap = t3_bidders & flagged_vendors
            if not overlap:
                record_pass("T-003 bids/graph: no T-003 bidder belongs to a ring with score >= 0.5")
            else:
                record_fail(
                    "T-003 bids/graph: no T-003 bidder belongs to a ring with score >= 0.5",
                    f"T-003 bidders in flagged rings: {sorted(overlap)}",
                )

    f_t3, err_f_t3 = load_json(args.fused_dir / "T-003.json")
    if err_f_t3:
        record_missing("T-003 fused: risk_level == low and decision == clear", err_f_t3)
    else:
        risk = f_t3.get("risk_level")
        dec = f_t3.get("decision")
        if risk == "low" and dec == "clear":
            record_pass("T-003 fused: risk_level == low and decision == clear")
        else:
            record_fail(
                "T-003 fused: risk_level == low and decision == clear",
                f"expected risk_level='low', decision='clear'; got risk_level={risk!r}, decision={dec!r}",
            )

    # ---------------------------------------------------------- Decision rule
    if not args.fused_dir.is_dir():
        record_missing("Decision rule: low->clear, medium->review, high->escalate", f"fused directory {args.fused_dir} not found")
    else:
        fused_files = sorted(args.fused_dir.glob("*.json"))
        if not fused_files:
            record_missing("Decision rule: low->clear, medium->review, high->escalate", f"no fused files in {args.fused_dir}")
        else:
            violations: list[str] = []
            for ff in fused_files:
                doc, err = load_json(ff)
                if err:
                    violations.append(err)
                    continue
                risk = doc.get("risk_level")
                dec = doc.get("decision")
                expected = DECISION_BY_RISK.get(risk)
                if expected != dec:
                    violations.append(f"{ff.name}: risk_level={risk!r} but decision={dec!r} (expected {expected!r})")
            if not violations:
                record_pass("Decision rule: low->clear, medium->review, high->escalate for all fused files")
            else:
                record_fail("Decision rule: low->clear, medium->review, high->escalate for all fused files", "; ".join(violations))

    # -------------------------------------------------------------- Citations
    if not args.fused_dir.is_dir() or not list(args.fused_dir.glob("*.json")):
        record_missing("Citations: every fused citation resolves", f"no fused files in {args.fused_dir}")
    else:
        cit_errors: list[str] = []
        cit_missing: list[str] = []
        for ff in sorted(args.fused_dir.glob("*.json")):
            doc, err = load_json(ff)
            if err:
                cit_errors.append(err)
                continue
            tid = doc.get("tender_id", ff.stem)
            rp = args.rules_dir / f"{tid}.json"
            rdoc, rerr = load_json(rp)

            for cit in doc.get("citations", []):
                ref = cit.get("ref", "")
                if ref.startswith("F-"):
                    if rerr:
                        cit_missing.append(f"{ff.name} cites {ref} but {rerr}")
                    else:
                        fids = {item.get("finding_id") for item in rdoc.get("findings", [])}
                        if ref not in fids:
                            cit_errors.append(f"{ff.name}: cited finding {ref} not in {rp.name} findings ({fids})")
                elif ref.startswith("R-"):
                    if err_graph:
                        cit_missing.append(f"{ff.name} cites {ref} but {err_graph}")
                    else:
                        rids = {item.get("ring_id") for item in graph_doc.get("rings", [])}
                        if ref not in rids:
                            cit_errors.append(f"{ff.name}: cited ring {ref} not in graph rings ({rids})")
                elif ref.startswith("KB-"):
                    kbp = args.kb_dir / f"{ref}.md"
                    if not kbp.is_file():
                        cit_errors.append(f"{ff.name}: cited passage {kbp} does not exist")
                    else:
                        title = parse_source_title(kbp.read_text(encoding="utf-8"))
                        if "PLACEHOLDER" in title:
                            cit_errors.append(f"{ff.name}: cited passage {ref} has PLACEHOLDER in source_title")
                else:
                    cit_errors.append(f"{ff.name}: unknown citation prefix in {ref!r}")

        if cit_errors:
            record_fail("Citations: every fused citation resolves", "; ".join(cit_errors))
        elif cit_missing:
            record_missing("Citations: every fused citation resolves", "; ".join(cit_missing))
        else:
            record_pass("Citations: every fused citation resolves")

    # ----------------------------------------------------------- Demo hygiene
    if not args.kb_dir.is_dir():
        record_missing("Demo hygiene: no PLACEHOLDER passage in kb-dir", f"kb directory {args.kb_dir} does not exist")
    else:
        placeholders: list[str] = []
        for p in sorted(args.kb_dir.glob("*.md")):
            title = parse_source_title(p.read_text(encoding="utf-8"))
            if "PLACEHOLDER" in title:
                placeholders.append(f"{p.name} ({title!r})")
        if placeholders:
            record_fail("Demo hygiene: no PLACEHOLDER passage in kb-dir", f"PLACEHOLDER passages found: {', '.join(placeholders)}")
        else:
            record_pass("Demo hygiene: no PLACEHOLDER passage in kb-dir")

    # ------------------------------------------------------------- Disclaimer
    if not args.fused_dir.is_dir() or not list(args.fused_dir.glob("*.json")):
        record_missing("Disclaimer: exact text from SoT 8.4", f"no fused files in {args.fused_dir}")
    else:
        disc_errors: list[str] = []
        for ff in sorted(args.fused_dir.glob("*.json")):
            doc, err = load_json(ff)
            if err:
                disc_errors.append(err)
                continue
            disc = doc.get("disclaimer")
            if disc != SOT_DISCLAIMER:
                disc_errors.append(f"{ff.name}: got {disc!r}")
        if not disc_errors:
            record_pass("Disclaimer: exact text from SoT 8.4 on all fused files")
        else:
            record_fail("Disclaimer: exact text from SoT 8.4 on all fused files", "; ".join(disc_errors))

    # ---------------------------------------------------------------- Output
    all_passed = True
    for status, name, reason in results:
        if status == "PASS":
            print(f"PASS {name}")
        elif status == "MISSING":
            all_passed = False
            print(f"MISSING {name}: {reason}")
        else:
            all_passed = False
            print(f"FAIL {name}: {reason}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
