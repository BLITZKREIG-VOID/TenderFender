"""
TenderFender – CLI Orchestrator and Safe Output Writer (P2)
===========================================================
Usage
-----
    python -m synth.generator [options]

Options
-------
    --vendors INT     Total vendors to generate (default 200, min 103)
    --tenders INT     Total tenders to generate (default 300, min 25)
    --seed    INT     Random seed (default 42)
    --output-dir PATH Output directory (default data/)

Safe-write protocol
-------------------
1. Generate all data in memory.
2. Verify all data in memory (VerificationError -> abort, no files touched).
3. Write each file to a .tmp sibling first.
4. Rename all .tmp files to final names atomically (per-file).
5. If any rename fails, attempt rollback of already-renamed files.

Only these six files are ever written:
    {output_dir}/vendors.csv
    {output_dir}/directors.csv
    {output_dir}/vendor_directors.csv
    {output_dir}/tenders.csv
    {output_dir}/bids.csv
    {output_dir}/labels.json

No other files are created or modified.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

from synth.generate import generate_all, MIN_TENDERS
from synth.verify import VerificationError, verify_all


# ---------------------------------------------------------------------------
# Minimum valid configuration
# ---------------------------------------------------------------------------

MIN_VENDORS = 103   # must accommodate R-1 (45,46,47) and R-2 (100,101,102,103)
# MIN_TENDERS is 25: 3 demo + 12 R-2 + 10 R-3 tenders.



# ---------------------------------------------------------------------------
# CSV / JSON serialisers (standard library only)
# ---------------------------------------------------------------------------

def _rows_to_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    """Serialise list-of-dicts to CSV string with stable column order."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# Stable column orders matching SOURCE_OF_TRUTH.md §7 schemas

VENDORS_FIELDS = [
    "vendor_id", "name", "turnover_cr", "years_experience",
    "registration_class", "address_id", "contact_id",
]
DIRECTORS_FIELDS = ["person_id", "name"]
VENDOR_DIRECTORS_FIELDS = ["vendor_id", "person_id"]
TENDERS_FIELDS = [
    "tender_id", "buyer_id", "title", "estimated_value_cr",
    "bid_days", "open_date",
]
BIDS_FIELDS = [
    "tender_id", "vendor_id", "bid_amount_cr", "bid_ratio",
    "rank", "won", "submitted_at",
]


def _build_file_contents(
    data: dict[str, Any],
) -> dict[str, str]:
    """
    Convert in-memory data to file contents strings.

    Returns a dict: filename_stem -> content_string.
    """
    return {
        "vendors.csv": _rows_to_csv(data["vendors"], VENDORS_FIELDS),
        "directors.csv": _rows_to_csv(data["directors"], DIRECTORS_FIELDS),
        "vendor_directors.csv": _rows_to_csv(
            data["vendor_directors"], VENDOR_DIRECTORS_FIELDS
        ),
        "tenders.csv": _rows_to_csv(data["tenders"], TENDERS_FIELDS),
        "bids.csv": _rows_to_csv(data["bids"], BIDS_FIELDS),
        "labels.json": json.dumps(data["labels"], indent=2, ensure_ascii=False),
    }


# ---------------------------------------------------------------------------
# Safe output writer
# ---------------------------------------------------------------------------

def _safe_write(output_dir: Path, file_contents: dict[str, str]) -> None:
    """
    Write files using a tmp-then-rename strategy.

    Raises RuntimeError with context on failure; attempts rollback.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    tmp_paths: dict[str, Path] = {}
    final_paths: dict[str, Path] = {}

    for filename, content in file_contents.items():
        final_path = output_dir / filename
        tmp_path = output_dir / (filename + ".tmp")
        tmp_paths[filename] = tmp_path
        final_paths[filename] = final_path

    # Step 1: write all .tmp files
    try:
        for filename, content in file_contents.items():
            tmp_paths[filename].write_text(content, encoding="utf-8")
    except OSError as exc:
        # Clean up any written tmps
        for tp in tmp_paths.values():
            tp.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to write temporary files: {exc}") from exc

    # Step 2: rename .tmp -> final, track what succeeded for rollback
    renamed: list[tuple[Path, Path]] = []  # (final, backup)  — had pre-existing version
    created: list[Path] = []              # finals that had no pre-existing version
    backup_paths: dict[str, Path] = {}

    for filename in file_contents:
        tmp_path = tmp_paths[filename]
        final_path = final_paths[filename]
        backup_path = output_dir / (filename + ".bak")
        backup_paths[filename] = backup_path

        # Backup existing file if present; record newly-created files separately
        if final_path.exists():
            try:
                final_path.replace(backup_path)
            except OSError as exc:
                # Rollback tmps written so far
                for tp in tmp_paths.values():
                    tp.unlink(missing_ok=True)
                # Restore any backups already made
                for fp, bp in renamed:
                    if bp.exists():
                        bp.replace(fp)
                # Remove any files we created from nothing (D13)
                for fp in created:
                    fp.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Failed to backup '{final_path}': {exc}"
                ) from exc
        else:
            # No pre-existing version: track so rollback can unlink if needed (D13)
            created.append(final_path)

        # Rename tmp -> final
        try:
            tmp_path.replace(final_path)
            if final_path not in created:
                renamed.append((final_path, backup_path))
        except OSError as exc:
            # Rollback: remove any tmps still pending
            for tp in tmp_paths.values():
                tp.unlink(missing_ok=True)
            # Restore backups of already-renamed files
            for fp, bp in renamed:
                if bp.exists():
                    bp.replace(fp)
            # Restore the CURRENT file's backup: its original was moved to .bak
            # before the rename attempt, so it is now absent unless we restore it.
            if backup_path.exists():
                backup_path.replace(final_path)
            # Unlink any finals that were newly created from nothing (D13)
            for fp in created:
                fp.unlink(missing_ok=True)
            raise RuntimeError(
                f"Failed to rename '{tmp_path}' -> '{final_path}': {exc}"
            ) from exc

    # Step 3: remove backups (success)
    for bp in backup_paths.values():
        if bp.exists():
            bp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m synth.generator",
        description="TenderFender P2: Synthetic data generator.",
    )
    parser.add_argument(
        "--vendors",
        type=int,
        default=200,
        help=f"Number of vendors (default 200, min {MIN_VENDORS})",
    )
    parser.add_argument(
        "--tenders",
        type=int,
        default=300,
        help=f"Number of tenders (default 300, min {MIN_TENDERS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default 42)",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory (default: data/)",
    )
    return parser


def run(
    num_vendors: int = 200,
    num_tenders: int = 300,
    seed: int = 42,
    output_dir: str | Path = "data",
) -> dict[str, Any]:
    """
    Programmatic entry point (used by tests and CLI).

    Returns the generated data dict if successful.
    Raises ValueError for invalid config, VerificationError for data issues.
    """
    # Validate configuration before touching any files
    if num_vendors < MIN_VENDORS:
        raise ValueError(
            f"--vendors must be >= {MIN_VENDORS}, got {num_vendors}"
        )
    if num_tenders < MIN_TENDERS:
        raise ValueError(
            f"--tenders must be >= {MIN_TENDERS}, got {num_tenders}"
        )

    print(
        f"[synth] Generating: vendors={num_vendors}, tenders={num_tenders}, "
        f"seed={seed}, output_dir={output_dir}"
    )

    # Step 1: generate in memory
    data = generate_all(num_vendors=num_vendors, num_tenders=num_tenders, seed=seed)

    # Step 2: verify in memory (raises VerificationError if any check fails)
    verify_all(data, num_vendors=num_vendors, num_tenders=num_tenders)

    # Step 3: serialise
    file_contents = _build_file_contents(data)

    # Step 4: safe write
    out = Path(output_dir)
    _safe_write(out, file_contents)

    # Report summary
    labels = data["labels"]
    print(
        f"[synth] Done. "
        f"vendors={len(data['vendors'])}, "
        f"directors={len(data['directors'])}, "
        f"vendor_director_pairs={len(data['vendor_directors'])}, "
        f"tenders={len(data['tenders'])}, "
        f"bids={len(data['bids'])}, "
        f"rings={len(labels['rings'])}"
    )

    return data


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        run(
            num_vendors=args.vendors,
            num_tenders=args.tenders,
            seed=args.seed,
            output_dir=args.output_dir,
        )
    except (ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"IO ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
