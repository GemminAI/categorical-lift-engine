"""5W1H extraction -- relocated from cognitive-port-selector alongside the
module itself. Same test names/behavior, ported not reinvented."""

from __future__ import annotations

from cle.grounding.five_w1h import FiveW1HOverrides, extract_five_w1h


def test_explicit_override_wins_over_derivation() -> None:
    result = extract_five_w1h(
        "prompt text", "goal text", FiveW1HOverrides(who="explicit-who")
    )
    assert result.who.value == "explicit-who"
    assert result.who.source == "explicit"


def test_what_derives_from_goal() -> None:
    result = extract_five_w1h("prompt", "the stated goal")
    assert result.what.value == "the stated goal"
    assert result.what.source == "derived"


def test_why_derives_from_prompt() -> None:
    result = extract_five_w1h("the prompt text", "goal")
    assert result.why.value == "the prompt text"
    assert result.why.source == "derived"


def test_how_derives_from_first_sentence() -> None:
    result = extract_five_w1h("First sentence. Second sentence.", "goal")
    assert result.how.value == "First sentence"
    assert result.how.source == "derived"


def test_when_derived_from_date_pattern() -> None:
    result = extract_five_w1h("scheduled for 2026-08-12", "goal")
    assert result.when.value == "2026-08-12"
    assert result.when.source == "derived"


def test_when_unspecified_without_a_date() -> None:
    result = extract_five_w1h("no date here", "goal")
    assert result.when.value == "unspecified"
    assert result.when.source == "unspecified"


def test_where_derived_from_location_pattern() -> None:
    result = extract_five_w1h("meeting at Tokyo", "goal")
    assert result.where.value == "Tokyo"
    assert result.where.source == "derived"


def test_who_is_unspecified_without_override() -> None:
    result = extract_five_w1h("no who signal", "goal")
    assert result.who.value == "unspecified"
    assert result.who.source == "unspecified"


def test_empty_prompt_and_goal_yield_unspecified_fields() -> None:
    result = extract_five_w1h("", "")
    assert result.what.value == "unspecified"
    assert result.why.value == "unspecified"
    assert result.how.value == "unspecified"


def test_deterministic_extraction() -> None:
    a = extract_five_w1h("同じprompt 2026-08-12", "同じgoal")
    b = extract_five_w1h("同じprompt 2026-08-12", "同じgoal")
    assert a == b
