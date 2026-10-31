"""CLI: python -m decision.run --fusion-dir ... --kb-dir ... --out-dir ... --cache-dir ... --mode ... --retriever ...

Modes (never silently falls back):
  template  deterministic writer, no network. Does not write the cache.
  llm       OpenRouter writer (needs OPENROUTER_API_KEY; model from DECISION_MODEL). Writes the cache.
  cache     use artifacts/decisions/T-xxx.json only if its input_hash matches, else error.
  auto      cache hit -> cache; else OPENROUTER_API_KEY present -> llm; else error.
Tenders with no findings and no rings always use the template (no LLM call, nothing to explain)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from decision import write
from decision.retrieve import (DEFAULT_TOP_K, PassageError, build_queries, load_passages, make_retriever, retrieve)
from decision.validate import DecisionValidationError, validate_decision

DISCLAIMER = "Risk indicators only; not a finding of wrongdoing. Recommendation requires human review."
MODES = ("cache", "llm", "template", "auto")
# Independent of fusion (SoT D5): the deterministic risk -> decision mapping (SoT 8.3), re-checked on every input.
DECISION_BY_RISK = {"low": "clear", "medium": "review", "high": "escalate"}


class DecisionError(Exception):
    pass


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_input_hash(fusion: dict, retrieved: write.Retrieved, retriever_name: str, model: str) -> str:
    material = {
        "fusion": fusion,
        "retrieved": {k: [[p.passage_id, p.content_hash] for p, _ in hits] for k, hits in sorted(retrieved.items())},
        "prompt_version": write.PROMPT_VERSION,
        "retriever": retriever_name,
        "model": model,
    }
    return hashlib.sha256(canonical(material).encode("utf-8")).hexdigest()


def _retrieved_summary(retrieved: write.Retrieved) -> dict:
    return {k: [{"passage_id": p.passage_id, "score": s} for p, s in hits] for k, hits in retrieved.items()}


def _load_cache(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DecisionError(f"corrupt cache file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DecisionError(f"corrupt cache file {path}: top-level JSON value must be an object")
    return data


def _cache_usable(entry: dict | None, input_hash: str) -> bool:
    return entry is not None and entry.get("input_hash") == input_hash


def _decide_one(fusion: dict, retrieved: write.Retrieved, input_hash: str, retriever_name: str, *,
                mode: str, cache_path: Path, placeholder_ids: set[str], model: str,
                transport: write.Transport = write.urllib_transport) -> tuple[dict, str]:
    """Returns (text_fields, decision_source)."""
    tid = fusion["tender_id"]
    allowed = write.allowed_refs(fusion["_inputs"], retrieved)

    if not write.has_evidence(fusion):
        return write.write_template(fusion, retrieved), "template"

    entry = _load_cache(cache_path)
    effective = mode
    if mode == "auto":
        if _cache_usable(entry, input_hash):
            effective = "cache"
        elif os.environ.get("OPENROUTER_API_KEY"):
            effective = "llm"
        else:
            raise DecisionError(
                f"{tid}: DECISION_MODE=auto found no matching cached decision and OPENROUTER_API_KEY is not set. "
                "Set DECISION_MODE=template to use the deterministic template writer, or set OPENROUTER_API_KEY.")

    if effective == "template":
        return write.write_template(fusion, retrieved), "template"

    if effective == "cache":
        if entry is None:
            raise DecisionError(f"{tid}: no cached decision at {cache_path}")
        if entry.get("input_hash") != input_hash:
            raise DecisionError(f"{tid}: cached decision is stale (input_hash mismatch) at {cache_path}")
        fields = {"reasoning": entry.get("reasoning"), "recommended_actions": entry.get("recommended_actions")}
        derived = validate_decision(fields, allowed, placeholder_ids, fusion["decision"])  # re-validate on load
        if entry.get("citations") != derived:
            raise DecisionValidationError([f"{tid}: cached citations do not match refs in cached text"])
        return fields, "cache"

    if effective == "llm":
        out = write.write_llm(fusion, retrieved, placeholder_ids, model=model, transport=transport)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "input_hash": input_hash, "decision_source": "llm", "retriever": retriever_name,
            "model": out["model"], "reasoning": out["reasoning"],
            "recommended_actions": out["recommended_actions"], "citations": out["citations"],
            "retrieved": _retrieved_summary(retrieved),
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"reasoning": out["reasoning"], "recommended_actions": out["recommended_actions"]}, "llm"

    raise DecisionError(f"unknown mode {effective!r}")


def run(fusion_dir: Path, kb_dir: Path, out_dir: Path, cache_dir: Path, *, mode: str, retriever_name: str,
        min_score: float | None = None, top_k: int = DEFAULT_TOP_K, allow_placeholder: bool = False,
        transport: write.Transport = write.urllib_transport) -> list[Path]:
    if mode not in MODES:
        raise DecisionError(f"unknown mode {mode!r}; choose one of {', '.join(MODES)}")
    if not fusion_dir.is_dir():
        raise DecisionError(f"missing fusion directory: {fusion_dir}")
    files = sorted(fusion_dir.glob("T-*.json"))
    if not files:
        raise DecisionError(f"no T-*.json files in {fusion_dir}")

    passages = load_passages(kb_dir)
    placeholder_ids = set() if allow_placeholder else {p.passage_id for p in passages if p.placeholder}
    retriever = make_retriever(retriever_name)
    model = write.resolve_model()
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for ff in files:
        fusion = json.loads(ff.read_text(encoding="utf-8"))
        tid = fusion["tender_id"]
        if not isinstance(tid, str) or not re.fullmatch(r"T-\d{3}", tid) or ff.stem != tid:
            raise DecisionError(f"{ff}: tender_id {tid!r} must match T-NNN and the file name")
        if DECISION_BY_RISK.get(fusion["risk_level"]) != fusion["decision"]:
            raise DecisionError(f"{tid}: decision {fusion['decision']!r} does not match risk_level "
                                f"{fusion['risk_level']!r} (expected {DECISION_BY_RISK.get(fusion['risk_level'])!r})")
        retrieved = retrieve(build_queries(fusion["_inputs"]), passages, retriever, top_k=top_k,
                             min_score=min_score, allow_placeholder=allow_placeholder)
        input_hash = compute_input_hash(fusion, retrieved, retriever.name, model)
        fields, source = _decide_one(fusion, retrieved, input_hash, retriever.name, mode=mode,
                                     cache_path=cache_dir / f"{tid}.json", placeholder_ids=placeholder_ids,
                                     model=model, transport=transport)
        citations = validate_decision(fields, write.allowed_refs(fusion["_inputs"], retrieved), placeholder_ids,
                                      fusion["decision"])

        final = {k: v for k, v in fusion.items() if k != "_inputs"}
        final.update({"reasoning": fields["reasoning"], "citations": citations,
                      "recommended_actions": fields["recommended_actions"],
                      "decision_source": source, "disclaimer": DISCLAIMER})
        ordered = ["tender_id", "title", "risk_level", "rule_finding_ids", "graph_flag_ring_ids", "linked_vendors",
                   "summary", "decision", "reasoning", "citations", "recommended_actions", "decision_source", "disclaimer"]
        final = {k: final[k] for k in ordered}
        out = out_dir / f"{tid}.json"
        out.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(out)
        print(f"decision {tid}: risk={final['risk_level']} decision={final['decision']} "
              f"source={source} retriever={retriever.name} citations={len(citations)} -> {out}")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="decision.run")
    ap.add_argument("--fusion-dir", type=Path, required=True)
    ap.add_argument("--kb-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--cache-dir", type=Path, required=True)
    ap.add_argument("--mode", choices=MODES, required=True)
    ap.add_argument("--retriever", choices=("embedding", "keyword"), required=True)
    ap.add_argument("--min-score", type=float, default=None, help="minimum similarity (default depends on retriever)")
    ap.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ap.add_argument("--allow-placeholder", action="store_true", help="tests only: allow PLACEHOLDER passages")
    args = ap.parse_args(argv)
    try:
        run(args.fusion_dir, args.kb_dir, args.out_dir, args.cache_dir, mode=args.mode,
            retriever_name=args.retriever, min_score=args.min_score, top_k=args.top_k,
            allow_placeholder=args.allow_placeholder)
    except (DecisionError, DecisionValidationError, PassageError, write.LLMError) as exc:
        print(f"decision error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
