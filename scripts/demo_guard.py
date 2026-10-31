#!/usr/bin/env python3
"""Demo guard: safety checks before running or demonstrating TenderFender (SoT 13 D17).

Fails loudly (non-zero exit) if:
1. Any passage in kb/passages/ has PLACEHOLDER in source_title.
2. Any artifacts/fused/*.json has decision_source == 'template' and lacks the template note.
3. Any required fused file (T-001, T-002, T-003) is missing.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEMPLATE_NOTE = "Template reasoning: generated from a fixed template, not written by the AI model."


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TenderFender demo guard")
    ap.add_argument(
        "--kb-dir",
        type=Path,
        default=Path(os.environ.get("KB_DIR", "kb/passages")),
        help="Path to KB passages directory",
    )
    ap.add_argument(
        "--fused-dir",
        type=Path,
        default=Path(os.environ.get("FUSED_DIR", "artifacts/fused")),
        help="Path to fused decisions directory",
    )
    parsed = ap.parse_args(argv)

    if os.environ.get("DEMO") == "0":
        print("demo_guard: DEMO=0; skipping demo guard.")
        return 0

    errors: list[str] = []

    # 1. Knowledge base check: no PLACEHOLDER passages
    kb_dir = parsed.kb_dir
    if kb_dir.is_dir():
        for p in sorted(kb_dir.glob("*.md")):
            try:
                title = parse_source_title(p.read_text(encoding="utf-8"))
            except OSError as exc:
                errors.append(f"Could not read passage file {p}: {exc}")
                continue
            if "PLACEHOLDER" in title:
                errors.append(
                    f"KB passage {p} has PLACEHOLDER in source_title: {title!r}"
                )

    # 2. Required fused files exist: T-001, T-002, T-003
    fused_dir = parsed.fused_dir
    for tid in ("T-001", "T-002", "T-003"):
        target = fused_dir / f"{tid}.json"
        if not target.is_file():
            errors.append(f"Required fused file missing: {target}")

    # 3. If decision_source == 'template', must contain the template note
    if fused_dir.is_dir():
        for p in sorted(fused_dir.glob("*.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                errors.append(f"Failed to read/parse {p}: {exc}")
                continue
            if doc.get("decision_source") == "template":
                reasoning = doc.get("reasoning", "")
                if TEMPLATE_NOTE not in reasoning:
                    errors.append(
                        f"{p} has decision_source='template' but reasoning lacks template note"
                    )

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print("demo_guard: all demo safety checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
