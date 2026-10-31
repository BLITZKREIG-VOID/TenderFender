import pytest

from decision.validate import DecisionValidationError, validate_decision

ALLOWED = {"KB-001", "F-1", "R-1"}


def ok(reasoning="Finding [F-1] and ring [R-1] per [KB-001].", actions=("Review [F-1].",)):
    return {"reasoning": reasoning, "recommended_actions": list(actions)}


def test_citations_derived_from_text_with_kinds():
    cites = validate_decision(ok(), ALLOWED, set())
    assert cites == [{"ref": "KB-001", "kind": "guideline"}, {"ref": "F-1", "kind": "finding"},
                     {"ref": "R-1", "kind": "ring"}]


def test_no_refs_means_no_citations():
    assert validate_decision(ok("Nothing to cite.", ["Do nothing."]), ALLOWED, set()) == []


def test_unknown_ref_rejected():
    with pytest.raises(DecisionValidationError, match="KB-777"):
        validate_decision(ok("See [KB-777]."), ALLOWED, set())
    with pytest.raises(DecisionValidationError, match="F-9"):
        validate_decision(ok(actions=["Check F-9."]), ALLOWED, set())


def test_placeholder_ref_rejected():
    with pytest.raises(DecisionValidationError, match="placeholder passage cited: KB-901"):
        validate_decision(ok("See [KB-901]."), ALLOWED | {"KB-901"}, {"KB-901"})


@pytest.mark.parametrize("text", ["The vendor is corrupt.", "They are GUILTY.", "This proves illegality.",
                                  "The bidder committed fraud."])
def test_forbidden_wording_rejected(text):
    with pytest.raises(DecisionValidationError, match="forbidden wording"):
        validate_decision(ok(text), ALLOWED, set())


def test_official_titles_with_corruption_not_rejected():
    validate_decision(ok("Per the Prevention of Corruption Act [KB-001]."), ALLOWED, set())


def test_empty_fields_rejected():
    with pytest.raises(DecisionValidationError):
        validate_decision({"reasoning": "", "recommended_actions": []}, ALLOWED, set())
    with pytest.raises(DecisionValidationError):
        validate_decision({"reasoning": "x"}, ALLOWED, set())
