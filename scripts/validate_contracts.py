#!/usr/bin/env python3
"""Validate contract examples, mocks, artifacts, data files and KB front matter against contracts/schemas.

Prints one OK/FAIL line per file (with error paths) and exits non-zero if anything fails.
Usage: python scripts/validate_contracts.py [--root DIR]
"""

from __future__ import annotations

from pathlib import Path
import argparse
import sys
import json
import re
from decision.validate import REF_RE
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
DECISION_BY_RISK = {"low": "clear", "medium": "review", "high": "escalate"}
KIND_BY_PREFIX = {"KB-": "guideline", "F-": "finding", "R-": "ring"}
CANONICAL_REF_RE = re.compile(r"^KB-\d{3}$|^F-[1-9]\d*$|^R-[1-9]\d*$")


def load_schemas(schema_dir: Path) -> tuple[dict[str, dict], Registry]:
    schemas, registry = {}, Registry()
    for path in sorted(schema_dir.glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schemas[path.stem] = schema
        registry = registry.with_resource(path.name, Resource.from_contents(schema))
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def schema_errors(validator: Draft202012Validator, instance) -> list[str]:
    out = []
    for e in sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path))):
        loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
        out.append(f"{loc}: {e.message[:200]}")
    return out


# ---- extra checks JSON Schema cannot express -------------------------------------------------

def check_fused(doc: dict, name: str) -> list[str]:
    errs = []
    if DECISION_BY_RISK.get(doc.get("risk_level")) != doc.get("decision"):
        errs.append(f"decision {doc.get('decision')!r} inconsistent with risk_level {doc.get('risk_level')!r} "
                    "(low->clear, medium->review, high->escalate)")
    if name.startswith("T-") and doc.get("tender_id") != name.split(".")[0]:
        errs.append(f"tender_id {doc.get('tender_id')!r} does not match file name {name}")
    cited = set()
    for c in doc.get("citations", []):
        ref, kind = c.get("ref", ""), c.get("kind")
        if not CANONICAL_REF_RE.match(ref):
            errs.append(f"citation {ref!r} is not canonical (^KB-\\d{{3}}$|^F-[1-9]\\d*$|^R-[1-9]\\d*$)")
        cited.add(ref)
        prefix = next((p for p in KIND_BY_PREFIX if ref.startswith(p)), None)
        if prefix is None or KIND_BY_PREFIX[prefix] != kind:
            errs.append(f"citation {ref!r} has kind {kind!r}, expected {KIND_BY_PREFIX.get(prefix)!r}")
        if kind == "finding" and ref not in doc.get("rule_finding_ids", []):
            errs.append(f"cited finding {ref} is not in rule_finding_ids")
        if kind == "ring" and ref not in doc.get("graph_flag_ring_ids", []):
            errs.append(f"cited ring {ref} is not in graph_flag_ring_ids")
    if len(cited) != len(doc.get("citations", [])):
        errs.append("duplicate citations")
    text = " ".join([doc.get("reasoning", ""), *doc.get("recommended_actions", [])])
    found_refs = REF_RE.findall(text)
    for ref in sorted(set(found_refs)):
        if ref not in cited:
            errs.append(f"{ref} appears in reasoning/actions but is missing from citations")
        elif not CANONICAL_REF_RE.match(ref):
            errs.append(f"{ref} appears in reasoning/actions but is not a canonical reference")
    for lv in doc.get("linked_vendors", []):
        if lv.get("ring_id") not in doc.get("graph_flag_ring_ids", []):
            errs.append(f"linked vendor {lv.get('vendor_id')} ring {lv.get('ring_id')} not in graph_flag_ring_ids")
    return errs


def check_rules(doc: dict, name: str) -> list[str]:
    errs = []
    if name.startswith("T-") and doc.get("tender_id") != name.split(".")[0]:
        errs.append(f"tender_id {doc.get('tender_id')!r} does not match file name {name}")
    for a in doc.get("atoms", []):
        if not a.get("id", "").startswith(a.get("clause_id", "\0") + "."):
            errs.append(f"atom {a.get('id')} does not belong to clause {a.get('clause_id')}")
    ids = [f.get("finding_id") for f in doc.get("findings", [])]
    if len(ids) != len(set(ids)):
        errs.append("duplicate finding_id")
    if any(f.get("type") == "contradiction" for f in doc.get("findings", [])) and doc.get("qualifying_vendors"):
        errs.append("qualifying_vendors must be empty when the rule set is unsatisfiable")
    return errs


def parse_front_matter(raw: str) -> dict:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("front matter must start with '---'")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("front matter not closed with '---'") from None
    meta: dict = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"bad front matter line: {line!r}")
        k, v = (s.strip() for s in line.split(":", 1))
        meta[k] = [x.strip() for x in v[1:-1].split(",") if x.strip()] if v.startswith("[") and v.endswith("]") else v
    return meta


# ---- driver ----------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--file", type=Path, help="Optional specific fused JSON file to validate")
    parsed = ap.parse_args(argv)
    root = parsed.root
    schemas, registry = load_schemas(root / "contracts" / "schemas")
    validators = {n: Draft202012Validator(s, registry=registry) for n, s in schemas.items()}

    results: list[tuple[str, list[str]]] = []
    failed = 0
    def check(path: Path, schema: str, extra=None, *, array_of: bool = False) -> None:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            results.append((rel, [f"invalid JSON: {exc}"]))
            return
        v = validators[schema]
        if array_of:
            errs = [] if isinstance(doc, list) else ["<root>: expected an array of atoms"]
            for i, item in enumerate(doc if isinstance(doc, list) else []):
                errs += [f"[{i}]/{e}" for e in schema_errors(v, item)]
        else:
            errs = schema_errors(v, doc)
            if not errs and extra:
                errs = extra(doc, path.name)
        results.append((f"{rel}  [{schema}]", errs))

    if parsed.file:
        check(parsed.file, "fused", check_fused)
    else:
        ex = root / "contracts" / "examples"
        check(ex / "ir_atom.json", "ir_atom")
        for p in sorted(ex.glob("rules_T-*.json")):
            check(p, "rules_output", check_rules)
        check(ex / "graph_output.json", "graph_output")
        for p in sorted(ex.glob("fused_T-*.json")):
            check(p, "fused", check_fused)
        for name in ("tender", "kb_passage", "labels"):
            check(ex / f"{name}.json", name)

        for base in ("mocks", "artifacts"):
            d = root / base
            for p in sorted((d / "rules").glob("T-*.json")):
                check(p, "rules_output", check_rules)
            if (d / "graph" / "graph_output.json").is_file():
                check(d / "graph" / "graph_output.json", "graph_output")
            for p in sorted((d / "fused").glob("T-*.json")):
                check(p, "fused", check_fused)

        data = root / "data"
        if (data / "labels.json").is_file():
            check(data / "labels.json", "labels")
        for p in sorted((data / "tenders").glob("T-*.json")):
            check(p, "tender")
        for p in sorted((data / "tenders").glob("ir_T-*.json")):
            check(p, "ir_atom", array_of=True)

        kb = root / "kb" / "passages"
        if kb.is_dir():
            for p in sorted(kb.glob("KB-*.md")):
                rel = f"{p.relative_to(root)}  [kb_passage]"
                try:
                    meta = parse_front_matter(p.read_text(encoding="utf-8"))
                    errs = schema_errors(validators["kb_passage"], meta)
                    if not errs and meta["passage_id"] != p.stem:
                        errs = [f"passage_id {meta['passage_id']} does not match file name"]
                except ValueError as exc:
                    errs = [str(exc)]
                results.append((rel, errs))
    failed = 0
    for label, errs in results:
        if errs:
            failed += 1
            print(f"FAIL {label}")
            for e in errs:
                print(f"     - {e}")
        else:
            print(f"OK   {label}")
    print(f"\n{len(results) - failed}/{len(results)} files valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
