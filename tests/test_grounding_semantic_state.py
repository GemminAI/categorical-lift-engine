"""cle.grounding.semantic_state -- GroundedState construction and lexical
affinity, plus its own determinism (byte-stability, not just ranking
purity -- the same distinction cognitive-port-selector's Architecture
Review drew this session)."""

from __future__ import annotations

import json

from cle.grounding.five_w1h import FiveW1HOverrides, extract_five_w1h
from cle.grounding.semantic_state import build_grounded_state
from cle.grounding.sok import SOKOverrides, build_sok


def _state(
    prompt: str = "軌跡が不安定なので安定化してほしい。",
    goal: str = "stabilize trajectory",
    **sok_kwargs,
):  # type: ignore[no-untyped-def]
    five_w1h = extract_five_w1h(prompt, goal, FiveW1HOverrides())
    sok = build_sok(
        five_w1h, SOKOverrides(**sok_kwargs), default_knowledge_reference="test-ref"
    )
    return build_grounded_state(prompt, goal, five_w1h, sok)


def test_fingerprint_fields_are_tuples_not_frozensets() -> None:
    state = _state()
    for field in (
        "fingerprint",
        "goal_fingerprint",
        "subject_fingerprint",
        "observer_fingerprint",
        "knowledge_fingerprint",
    ):
        assert isinstance(getattr(state, field), tuple)


def test_fingerprint_fields_are_sorted() -> None:
    state = _state()
    for field in (
        "fingerprint",
        "goal_fingerprint",
        "subject_fingerprint",
        "observer_fingerprint",
        "knowledge_fingerprint",
    ):
        value = getattr(state, field)
        assert list(value) == sorted(value)


def test_point_cloud_fields_are_populated() -> None:
    state = _state(subject="a real subject")
    assert len(state.concept_points) > 0
    assert len(state.subject_points) > 0
    assert len(state.observer_points) > 0
    assert len(state.knowledge_points) > 0


def test_jaccard_similarity_favors_matching_text_over_unrelated_text() -> None:
    state = _state()
    matching = state.jaccard_similarity(state.prompt)
    unrelated = state.jaccard_similarity("completely unrelated ascii text zzz")
    assert 0.0 <= unrelated < matching <= 1.0


def test_subject_jaccard_similarity_responds_to_subject_text() -> None:
    state = _state(subject="決定論的な検証テキスト")
    assert state.subject_jaccard_similarity(
        "決定論的な検証テキスト"
    ) > state.subject_jaccard_similarity("zzz000 unrelated")


def test_goal_jaccard_similarity_responds_to_goal_text() -> None:
    state = _state(goal="a very specific goal statement")
    assert state.goal_jaccard_similarity(
        "a very specific goal statement"
    ) > state.goal_jaccard_similarity("zzz000 unrelated")


def test_observer_jaccard_similarity_responds_to_observer_text() -> None:
    state = _state(observer="a very specific observer")
    assert state.observer_jaccard_similarity(
        "a very specific observer"
    ) > state.observer_jaccard_similarity("zzz000 unrelated")


def test_knowledge_jaccard_similarity_responds_to_knowledge_text() -> None:
    state = _state(knowledge_reference="a very specific knowledge reference")
    assert state.knowledge_jaccard_similarity(
        "a very specific knowledge reference"
    ) > state.knowledge_jaccard_similarity("zzz000 unrelated")


def test_jaccard_both_empty_is_zero() -> None:
    """`_jaccard`'s empty/empty branch: unreachable via the public
    `GroundedState` API (every field falls back to the literal string
    "unspecified" rather than "", so `self.fingerprint` is never actually
    empty) -- tested directly against the private helper for its own
    documented edge-case behavior."""
    from cle.grounding.semantic_state import _jaccard

    assert _jaccard((), ()) == 0.0


def test_json_serialization_is_stable_across_rebuilds() -> None:
    serializations = {
        json.dumps(_state(subject="Japan_Govt").model_dump(), sort_keys=True)
        for _ in range(10)
    }
    assert len(serializations) == 1


def test_different_subject_produces_different_state() -> None:
    a = _state(subject="Japan_Govt")
    b = _state(subject="Private_Corp")
    assert a.sok.subject != b.sok.subject
    assert a.subject_fingerprint != b.subject_fingerprint
    assert a.subject_points != b.subject_points
