import pytest

from decision.retrieve import (KeywordRetriever, PassageError, build_queries, load_passages, parse_passage, retrieve)
from tests.decision.conftest import make_fusion


def test_parse_front_matter_and_topics(kb_dir):
    ps = {p.passage_id: p for p in load_passages(kb_dir)}
    assert set(ps) == {"KB-901", "KB-902", "KB-903", "KB-904"}
    assert ps["KB-901"].topics == ("eligibility", "turnover") and ps["KB-901"].placeholder
    assert ps["KB-901"].text.startswith("Eligibility criteria")


def test_bad_front_matter_raises():
    with pytest.raises(PassageError):
        parse_passage("no front matter")
    with pytest.raises(PassageError, match="missing front matter field"):
        parse_passage("---\npassage_id: KB-001\n---\nbody")


def test_missing_or_empty_kb_dir_allowed(tmp_path):
    assert load_passages(tmp_path / "nope") == []
    (tmp_path / "kb").mkdir()
    assert load_passages(tmp_path / "kb") == []


def test_queries_one_per_finding_and_ring():
    q = build_queries(make_fusion()["_inputs"])
    assert set(q) == {"F-1", "R-1"}
    assert "tailored eligibility" in q["F-1"] and "Only Class-A contractors" in q["F-1"]
    assert "shared director" in q["R-1"] and "collusive bidding ring" in q["R-1"]


def test_placeholder_excluded_by_default(kb_dir):
    q = build_queries(make_fusion()["_inputs"])
    res = retrieve(q, load_passages(kb_dir), KeywordRetriever(), min_score=0.0)
    assert res == {"F-1": [], "R-1": []}


def test_top4_ordering_and_threshold(kb_dir):
    ps = load_passages(kb_dir)
    q = build_queries(make_fusion()["_inputs"])
    res = retrieve(q, ps, KeywordRetriever(), min_score=0.0, allow_placeholder=True)
    assert len(res["F-1"]) == 4  # top-4 cap with 4 passages
    ids = [p.passage_id for p, _ in res["F-1"]]
    assert ids[0] == "KB-901" and ids[-1] == "KB-904"
    scores = [s for _, s in res["F-1"]]
    assert scores == sorted(scores, reverse=True)
    assert [p.passage_id for p, _ in res["R-1"]][0] == "KB-903"

    capped = retrieve(q, ps, KeywordRetriever(), top_k=2, min_score=0.0, allow_placeholder=True)
    assert len(capped["F-1"]) == 2

    strict = retrieve(q, ps, KeywordRetriever(), min_score=scores[0], allow_placeholder=True)
    assert [p.passage_id for p, _ in strict["F-1"]] == ["KB-901"]  # only the best clears the threshold
    none = retrieve(q, ps, KeywordRetriever(), min_score=0.99, allow_placeholder=True)
    assert none == {"F-1": [], "R-1": []}


def test_retrieval_is_deterministic(kb_dir):
    ps = load_passages(kb_dir)
    q = build_queries(make_fusion()["_inputs"])
    a = retrieve(q, ps, KeywordRetriever(), min_score=0.0, allow_placeholder=True)
    b = retrieve(q, list(reversed(ps)), KeywordRetriever(), min_score=0.0, allow_placeholder=True)
    assert a == b
