from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from rules.checks import run_checks
from rules.compile_llm import compile_tender
from rules.ir import Atom, load_atoms

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_schemas(schema_dir: Path) -> tuple[dict[str, Any], Registry]:
    schemas: dict[str, Any] = {}
    registry = Registry()
    for path in sorted(schema_dir.glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schemas[path.stem] = schema
        registry = registry.with_resource(path.name, Resource.from_contents(schema))
        if "$id" in schema:
            registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P1 Rule Checker")
    parser.add_argument("--tender", type=str, help="Single tender ID (e.g. T-001)")
    parser.add_argument("--all", action="store_true", help="Process all demo tenders")
    parser.add_argument("--data-dir", type=str, default="data", help="Data directory")
    parser.add_argument("--out-dir", type=str, default="artifacts/rules", help="Output directory")
    parser.add_argument("--write-cache", action="store_true", help="Write compiled IR to cache")

    args = parser.parse_args(argv)

    rules_use_cache = os.environ.get("RULES_USE_CACHE", "1")
    if args.write_cache and rules_use_cache == "1":
        sys.stderr.write("Error: --write-cache cannot be used when RULES_USE_CACHE=1\n")
        return 1

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    schema_dir = REPO_ROOT / "contracts" / "schemas"

    try:
        schemas, registry = load_schemas(schema_dir)
    except Exception as e:
        sys.stderr.write(f"Error loading schemas: {e}\n")
        return 1

    atom_validator = Draft202012Validator(schemas["ir_atom"], registry=registry)
    output_validator = Draft202012Validator(schemas["rules_output"], registry=registry)

    if args.tender:
        tender_file = data_dir / "tenders" / f"{args.tender}.json"
        if not tender_file.exists():
            sys.stderr.write(f"Error: Tender file not found: {tender_file}\n")
            return 1
        tender_files = [tender_file]
    else:
        tender_files = sorted((data_dir / "tenders").glob("T-*.json"))
        if not tender_files:
            sys.stderr.write(f"Error: No demo tenders found in {data_dir / 'tenders'}\n")
            return 1

    vendors_csv = data_dir / "vendors.csv"
    if not vendors_csv.exists():
        sys.stderr.write(f"Error: Vendors file not found: {vendors_csv}\n")
        return 1

    try:
        with open(vendors_csv, mode="r", encoding="utf-8") as f:
            vendors = list(csv.DictReader(f))
    except Exception as e:
        sys.stderr.write(f"Error reading {vendors_csv}: {e}\n")
        return 1

    success = True
    for tender_path in tender_files:
        tender_id = tender_path.stem
        try:
            tender_data = json.loads(tender_path.read_text(encoding="utf-8"))
        except Exception as e:
            sys.stderr.write(f"Error reading tender file {tender_path}: {e}\n")
            success = False
            continue

        tender_clauses = {c["clause_id"]: c["text"] for c in tender_data.get("clauses", [])}

        atoms: list[Atom] = []
        cache_file = data_dir / "tenders" / f"ir_{tender_id}.json"

        if rules_use_cache == "1":
            if not cache_file.exists():
                sys.stderr.write(f"Error: Cached IR file not found: {cache_file}\n")
                success = False
                continue

            try:
                atoms = load_atoms(cache_file)
            except Exception as e:
                sys.stderr.write(f"Error loading cache {cache_file}: {e}\n")
                success = False
                continue

            # Validate each atom against contracts/schemas/ir_atom.json
            atom_errors = []
            for atom in atoms:
                atom_dict = atom.model_dump()
                for err in atom_validator.iter_errors(atom_dict):
                    atom_errors.append(f"Atom {atom.id}: {err.message}")

            if atom_errors:
                sys.stderr.write(f"Schema errors in cache {cache_file}:\n" + "\n".join(atom_errors) + "\n")
                success = False
                continue

            # Verify every atom.clause_id exists in the tender and atom.source_text == that clause's text exactly
            clause_match_errors = []
            for atom in atoms:
                if atom.clause_id not in tender_clauses:
                    clause_match_errors.append(
                        f"Atom {atom.id} references clause {atom.clause_id} which does not exist in {tender_id}"
                    )
                elif atom.source_text != tender_clauses[atom.clause_id]:
                    clause_match_errors.append(
                        f"Atom {atom.id} source_text does not match clause {atom.clause_id} text exactly"
                    )

            if clause_match_errors:
                sys.stderr.write(f"Validation errors in {tender_id}:\n" + "\n".join(clause_match_errors) + "\n")
                success = False
                continue

        else:
            try:
                atoms = compile_tender(tender_data)
            except Exception as e:
                sys.stderr.write(f"Error compiling tender {tender_id}: {e}\n")
                success = False
                continue

            if args.write_cache:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump([a.model_dump() for a in atoms], f, indent=2, ensure_ascii=False)
                        f.write("\n")
                except Exception as e:
                    sys.stderr.write(f"Error writing cache {cache_file}: {e}\n")
                    success = False
                    continue

        # Run checks
        try:
            check_result = run_checks(atoms, vendors)
        except Exception as e:
            sys.stderr.write(f"Error running checks for {tender_id}: {e}\n")
            success = False
            continue

        output = {
            "tender_id": tender_id,
            "formalization_status": "unconfirmed",
            "atoms": [a.model_dump() for a in atoms],
            "findings": check_result["findings"],
            "qualifying_vendors": check_result["qualifying_vendors"],
            "vendors_evaluated": check_result["vendors_evaluated"],
        }

        # Validate output schema
        out_errors = list(output_validator.iter_errors(output))
        if out_errors:
            for err in out_errors:
                loc = "/".join(str(p) for p in err.absolute_path) or "<root>"
                sys.stderr.write(f"Schema error in {tender_id}: {loc}: {err.message}\n")
            success = False
            continue

        # If any contradiction finding, qualifying_vendors must be empty
        has_contradiction = any(f.get("type") == "contradiction" for f in output["findings"])
        if has_contradiction and len(output["qualifying_vendors"]) > 0:
            sys.stderr.write(
                f"Error in {tender_id}: contradiction finding present but qualifying_vendors is not empty\n"
            )
            success = False
            continue

        # Write output file
        out_file = out_dir / f"{tender_id}.json"
        try:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            sys.stderr.write(f"Error writing output {out_file}: {e}\n")
            success = False
            continue

        # Print one line per tender
        findings_list = output["findings"]
        if findings_list:
            findings_str = (
                f"findings={len(findings_list)} ["
                + ", ".join(
                    f"{f['type']} clause_ids={f['clause_ids']} detail='{f['proof']['detail']}'"
                    for f in findings_list
                )
                + "]"
            )
        else:
            findings_str = "findings=0"

        out_path_str = str(out_file).replace("\\", "/")
        print(
            f"{tender_id}: {findings_str} qualifying_vendors={output['qualifying_vendors']} "
            f"vendors_evaluated={output['vendors_evaluated']} -> {out_path_str}"
        )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
