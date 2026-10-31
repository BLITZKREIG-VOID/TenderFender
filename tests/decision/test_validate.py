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


@pytest.mark.parametrize("text", ["See [KB-12].", "Per KB-0042 rule", "Per kb-004", "See R-01.", "See F-1a."])
def test_malformed_refs_rejected(text):
    allowed = {"F-1", "R-1", "KB-004"}
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok(text), allowed, set())
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok(actions=[text]), allowed, set())


def test_valid_bracketed_refs_accepted():
    cites = validate_decision(ok("See [KB-004] [F-1] [R-1]."), {"F-1", "R-1", "KB-004"}, set())
    assert [c["ref"] for c in cites] == ["KB-004", "F-1", "R-1"]


# ---------------------------------------------------------------- hardening (D18)

@pytest.mark.parametrize("text", [
    "See KB\u2011777.",          # U+2011 non-breaking hyphen
    "Check F\u20139.",           # en-dash
    "Check F\u20149.",           # em-dash
    "See KB\uff0d777.",          # full-width hyphen
    "See KB 777.",               # space instead of hyphen
    "See \uff2b\uff22-777.",     # full-width letters
    "See R \u2212 7.",           # minus sign with spaces
])
def test_lookalike_refs_rejected(text):
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok(text), ALLOWED, set())
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok(actions=[text]), ALLOWED, set())


def test_lookalike_of_valid_ref_is_not_accepted_as_canonical():
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok("See KB\u2011001."), ALLOWED, set())
    with pytest.raises(DecisionValidationError, match="malformed or unknown reference"):
        validate_decision(ok("See KB 001."), ALLOWED, set())


def test_zero_width_character_rejected():
    with pytest.raises(DecisionValidationError, match="invisible format character U\\+200B"):
        validate_decision(ok("They are gu\u200bilty."), ALLOWED, set())
    with pytest.raises(DecisionValidationError, match="invisible format character"):
        validate_decision(ok(actions=["Review\u2060 it."]), ALLOWED, set())


@pytest.mark.parametrize("text", ["GFR Rule 173 applies.", "Form 5 was filed.", "FY 2024 budget.",
                                  "Section 3 of the Act.", "Rule 173", "for 3 years", "Refer to Rs 5 lakh."])
def test_ordinary_words_are_not_refs(text):
    assert validate_decision(ok(text, ["Review."]), ALLOWED, set()) == []


@pytest.mark.parametrize("text", ["The vendor acted corruptly.", "The bidder is fraudulent.",
                                  "These bids are clearly fraudulent.", "He was guilty.",
                                  "That PROVES illegal conduct."])
def test_more_forbidden_wording_rejected(text):
    with pytest.raises(DecisionValidationError, match="forbidden wording"):
        validate_decision(ok(text), ALLOWED, set())


def test_fullwidth_lookalike_forbidden_wording_rejected():
    with pytest.raises(DecisionValidationError, match="forbidden wording"):
        validate_decision(ok("The vendor is \uff47\uff55\uff49\uff4c\uff54\uff59."), ALLOWED, set())


def test_corruption_act_and_fraud_indicators_allowed():
    validate_decision(ok("Prevention of Corruption Act, 1988 lists fraud risk indicators."), ALLOWED, set())


@pytest.mark.parametrize("phrase", ["No further action", "no action required", "Proceed with award",
                                    "No review needed", "no  further   review", "Safe to award"])
@pytest.mark.parametrize("decision", ["review", "escalate"])
def test_review_escalate_reject_contradicting_text(phrase, decision):
    with pytest.raises(DecisionValidationError, match="contradicts decision"):
        validate_decision(ok(f"Overall: {phrase}."), ALLOWED, set(), decision)
    with pytest.raises(DecisionValidationError, match="contradicts decision"):
        validate_decision(ok(actions=[phrase]), ALLOWED, set(), decision)


@pytest.mark.parametrize("phrase", ["Escalate to the authority", "Suspend the tender now"])
def test_clear_rejects_contradicting_text(phrase):
    with pytest.raises(DecisionValidationError, match="contradicts decision"):
        validate_decision(ok(actions=[phrase]), ALLOWED, set(), "clear")


def test_contradiction_phrases_allowed_for_matching_decision():
    validate_decision(ok(actions=["No action required beyond standard procurement review."]), ALLOWED, set(), "clear")
    validate_decision(ok(actions=["Escalate to the vigilance authority."]), ALLOWED, set(), "escalate")
