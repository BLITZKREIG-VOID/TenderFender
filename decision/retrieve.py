"""Passage loading and top-k retrieval over kb/passages (SoT 8.4 RAG rules)."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TOP_K = 4
DEFAULT_MIN_SCORE = {"embedding": 0.30, "keyword": 0.04}
DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_MODEL_CACHE = ".cache/models"

STOPWORDS = frozenset("""
a an and are as at be been but by can could do does for from has have if in into is it its may must
no not of on or shall should such than that the their then there these they this to was were which
will with within would any all each per also only
""".split())


class PassageError(Exception):
    pass


@dataclass(frozen=True)
class Passage:
    passage_id: str
    source_title: str
    source_url: str
    section: str
    retrieved: str
    topics: tuple[str, ...]
    text: str
    path: str = ""

    @property
    def placeholder(self) -> bool:
        return "PLACEHOLDER" in self.source_title

    @property
    def content_hash(self) -> str:
        blob = "\n".join([self.passage_id, self.source_title, self.source_url, self.section,
                          self.retrieved, ",".join(self.topics), self.text])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def metadata(self) -> dict:
        return {"passage_id": self.passage_id, "source_title": self.source_title,
                "source_url": self.source_url, "section": self.section,
                "retrieved": self.retrieved, "topics": list(self.topics)}


def parse_passage(raw: str, path: str = "") -> Passage:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PassageError(f"{path}: front matter must start with '---'")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise PassageError(f"{path}: front matter is not closed with '---'") from None
    meta: dict[str, object] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise PassageError(f"{path}: bad front matter line: {line!r}")
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = tuple(v.strip() for v in value[1:-1].split(",") if v.strip())
        else:
            meta[key] = value
    for required in ("passage_id", "source_title", "source_url", "section", "retrieved", "topics"):
        if required not in meta:
            raise PassageError(f"{path}: missing front matter field {required!r}")
    if not re.fullmatch(r"KB-\d{3}", str(meta["passage_id"])):
        raise PassageError(f"{path}: bad passage_id {meta['passage_id']!r}")
    return Passage(
        passage_id=str(meta["passage_id"]), source_title=str(meta["source_title"]),
        source_url=str(meta["source_url"]), section=str(meta["section"]),
        retrieved=str(meta["retrieved"]), topics=tuple(meta["topics"]),  # type: ignore[arg-type]
        text="\n".join(lines[end + 1:]).strip(), path=path,
    )


def load_passages(kb_dir: Path) -> list[Passage]:
    """Missing or empty directory is allowed: returns []."""
    if not kb_dir.is_dir():
        return []
    passages = [parse_passage(p.read_text(encoding="utf-8"), str(p)) for p in sorted(kb_dir.glob("KB-*.md"))]
    ids = [p.passage_id for p in passages]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise PassageError(f"duplicate passage ids: {sorted(dupes)}")
    return passages


def build_queries(inputs: dict) -> dict[str, str]:
    """One query per finding (type + explanation + source texts) and one per linked ring."""
    queries: dict[str, str] = {}
    for f in inputs["findings"]:
        queries[f["finding_id"]] = " ".join(
            [f["type"].replace("_", " "), f["explanation"], *f["source_texts"]])
    for r in inputs["rings"]:
        queries[r["ring_id"]] = " ".join(
            [*(t.replace("_", " ") for t in r["link_types"]), "collusive bidding ring"])
    return queries


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1 and t not in STOPWORDS}


def _passage_text(p: Passage) -> str:
    return " ".join([p.source_title, " ".join(p.topics), p.text])


class KeywordRetriever:
    name = "keyword"

    def scores(self, queries: list[str], passages: list[Passage]) -> list[list[float]]:
        ptoks = [_tokens(_passage_text(p)) for p in passages]
        out = []
        for q in queries:
            qt = _tokens(q)
            row = []
            for pt in ptoks:
                union = qt | pt
                row.append(len(qt & pt) / len(union) if union else 0.0)
            out.append(row)
        return out


class EmbeddingRetriever:
    name = "embedding"

    def __init__(self, model_name: str | None = None, cache_dir: str | None = None):
        import numpy as np
        from sentence_transformers import SentenceTransformer
        self._np = np
        cache = cache_dir or os.environ.get("SENTENCE_TRANSFORMERS_HOME") or DEFAULT_MODEL_CACHE
        self._model = SentenceTransformer(model_name or os.environ.get("EMBEDDING_MODEL", DEFAULT_MODEL),
                                          cache_folder=cache)

    def _embed(self, texts: list[str]):
        np = self._np
        vecs = np.asarray(self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False),
                          dtype="float64")
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vecs / norms

    def scores(self, queries: list[str], passages: list[Passage]) -> list[list[float]]:
        if not passages or not queries:
            return [[] for _ in queries]
        sims = self._embed(queries) @ self._embed([_passage_text(p) for p in passages]).T
        return sims.tolist()


def make_retriever(name: str):
    if name == "keyword":
        return KeywordRetriever()
    if name == "embedding":
        return EmbeddingRetriever()
    raise ValueError(f"unknown retriever {name!r}; use 'embedding' or 'keyword'")


def retrieve(queries: dict[str, str], passages: list[Passage], retriever, *, top_k: int = DEFAULT_TOP_K,
             min_score: float | None = None, allow_placeholder: bool = False) -> dict[str, list[tuple[Passage, float]]]:
    """Top-k passages per query key, score >= min_score, ordered by (-score, passage_id).

    PLACEHOLDER passages are excluded unless allow_placeholder (tests only)."""
    if min_score is None:
        min_score = DEFAULT_MIN_SCORE[retriever.name]
    pool = [p for p in passages if allow_placeholder or not p.placeholder]
    keys = list(queries)
    result: dict[str, list[tuple[Passage, float]]] = {k: [] for k in keys}
    if not pool or not keys:
        return result
    matrix = retriever.scores([queries[k] for k in keys], pool)
    for key, row in zip(keys, matrix):
        ranked = sorted(zip(pool, row), key=lambda pr: (-pr[1], pr[0].passage_id))
        result[key] = [(p, round(float(s), 6)) for p, s in ranked[:top_k] if s >= min_score]
    return result
