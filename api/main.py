"""
Tender Integrity MVP — FastAPI Backend

Serves tender analysis data by reading from file-based artifacts.
Set ``MOCK=1`` to read from ``mocks/`` instead of ``artifacts/``.
"""

from __future__ import annotations

import os
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from api.loaders import (
    is_mock_mode,
    list_fused_ids,
    load_fused,
    load_graph,
    load_rules,
    load_tender_clauses,
)
from api.passages import load_passage


# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tender Integrity API",
    version="0.1.0",
    description="Read-only API serving tender risk analysis artifacts.",
)

app.add_middleware(GZipMiddleware, minimum_size=1024)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory state (confirmation ticks) ─────────────────────────────────────

# tender_id -> updated rules dict (so POST confirm mutations survive GET)
_rules_overrides: dict[str, dict[str, Any]] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _error(status: int, message: str, code: str = "not_found") -> HTTPException:
    return HTTPException(status_code=status, detail={"error": message, "code": code})


def _get_rules(tender_id: str) -> dict[str, Any] | None:
    """Return rules with any in-memory overrides applied."""
    if tender_id in _rules_overrides:
        return _rules_overrides[tender_id]
    return load_rules(tender_id)


# ── Models ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str


class TenderSummary(BaseModel):
    tender_id: str
    title: str
    risk_level: str
    decision: str


class ConfirmResponse(BaseModel):
    tender_id: str
    atom_id: str
    formalization_status: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(mode="mock" if is_mock_mode() else "live")


@app.get("/api/tenders", response_model=list[TenderSummary])
def list_tenders():
    """Aggregate tender summaries from fused outputs."""
    ids = list_fused_ids()
    results: list[TenderSummary] = []
    for tid in ids:
        fused = load_fused(tid)
        if fused is None:
            continue
        results.append(
            TenderSummary(
                tender_id=fused["tender_id"],
                title=fused.get("title", ""),
                risk_level=fused["risk_level"],
                decision=fused["decision"],
            )
        )
    return results


@app.get("/api/tenders/{tender_id}/analysis")
def tender_analysis(tender_id: str):
    """Return combined rules, clauses, and fused decision for a tender."""
    fused = load_fused(tender_id)
    if fused is None:
        raise _error(404, f"Tender {tender_id} not found")

    rules = _get_rules(tender_id)

    # Clause texts: real clause list from data/tenders/<id>.json, else rules atoms
    clauses = load_tender_clauses(tender_id)
    if not clauses and rules and "atoms" in rules:
        seen_clauses: set[str] = set()
        for atom in rules["atoms"]:
            cid = atom["clause_id"]
            if cid not in seen_clauses:
                seen_clauses.add(cid)
                clauses.append({
                    "clause_id": cid,
                    "text": atom.get("source_text", ""),
                })

    # Guideline passages cited by the fused decision, read from kb/passages
    passages: list[dict[str, Any]] = []
    seen_passages: set[str] = set()
    for cite in fused.get("citations", []):
        if cite.get("kind") == "guideline" and cite["ref"] not in seen_passages:
            seen_passages.add(cite["ref"])
            passages.append(load_passage(cite["ref"]))

    return {
        "fused": fused,
        "rules": rules,
        "clauses": clauses,
        "passages": passages,
    }


@app.get("/api/tenders/{tender_id}/graph")
def tender_graph(tender_id: str):
    """
    Return the Cytoscape graph data plus the highlighted path
    for the linked vendor in this tender.
    """
    fused = load_fused(tender_id)
    if fused is None:
        raise _error(404, f"Tender {tender_id} not found")

    graph_data = load_graph()
    if graph_data is None:
        raise _error(404, "Graph data not available")

    # Determine the highlighted path for this tender's linked vendors
    highlighted_paths: list[dict[str, Any]] = []
    linked = fused.get("linked_vendors", [])
    linked_vendor_ids = {lv["vendor_id"] for lv in linked}

    for path_entry in graph_data.get("paths", []):
        if path_entry.get("from") in linked_vendor_ids:
            highlighted_paths.append(path_entry)

    # Filter rings relevant to this tender
    ring_ids = set(fused.get("graph_flag_ring_ids", []))
    relevant_rings = [
        r for r in graph_data.get("rings", [])
        if r["ring_id"] in ring_ids
    ]

    return {
        "graph": graph_data.get("graph", {}),
        "highlighted_paths": highlighted_paths,
        "rings": relevant_rings,
        "vendor_scores": graph_data.get("vendor_scores", {}),
        "metrics": graph_data.get("metrics", {}),
    }


@app.post("/api/tenders/{tender_id}/atoms/{atom_id}/confirm", response_model=ConfirmResponse)
def confirm_atom(tender_id: str, atom_id: str):
    """
    Mark an atom's tender as having confirmed formalization.
    In-memory update — restarting the server resets this.
    """
    rules = _get_rules(tender_id)
    if rules is None:
        raise _error(404, f"Tender {tender_id} not found")

    # Verify the atom exists
    atom_found = False
    for atom in rules.get("atoms", []):
        if atom["id"] == atom_id:
            atom_found = True
            break

    if not atom_found:
        raise _error(404, f"Atom {atom_id} not found in tender {tender_id}")

    # Update formalization_status
    import copy
    updated = copy.deepcopy(rules)
    updated["formalization_status"] = "confirmed"
    _rules_overrides[tender_id] = updated

    return ConfirmResponse(
        tender_id=tender_id,
        atom_id=atom_id,
        formalization_status="confirmed",
    )


# ── Static UI Serving ────────────────────────────────────────────────────────
ui_dist_dir = os.environ.get("UI_DIST", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ui_dist")))
if os.path.isdir(ui_dist_dir):
    @app.get("/assets/{file_path:path}")
    def serve_assets(file_path: str):
        full_path = os.path.join(ui_dist_dir, "assets", file_path)
        if os.path.isfile(full_path):
            return FileResponse(full_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
        raise HTTPException(status_code=404, detail="Asset not found")

    @app.get("/{file_path:path}")
    def serve_ui(file_path: str):
        if file_path.startswith("api/") or file_path == "api":
            raise HTTPException(status_code=404, detail="Not found")
        
        target = os.path.join(ui_dist_dir, file_path)
        if file_path and os.path.isfile(target):
            return FileResponse(target, headers={"Cache-Control": "no-cache"})
        
        if not file_path or "." not in file_path:
            index_path = os.path.join(ui_dist_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
        
        raise HTTPException(status_code=404, detail="Not found")

    @app.get("/")
    def serve_root():
        index_path = os.path.join(ui_dist_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, headers={"Cache-Control": "no-cache"})
        raise HTTPException(status_code=404, detail="Not found")
