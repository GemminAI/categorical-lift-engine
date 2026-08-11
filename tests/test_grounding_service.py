"""cle.grounding.service.ground -- the causal-path acceptance test.

STEP 7 requirement (CLE-rebuild directive): S/O/K(t) change -> Semantic
State change -> [downstream Selection] ranking/Active Subset change. This
test proves the first, CLE-internal half of that chain -- S/O/K(t) change
reaching CLE's real geometric engine (Betti numbers, compression ratio),
not merely being recorded on the response. The second half (CPS Selection
responding to CLE's output) is proved in cognitive-port-selector's own
test suite against this service, not here.
"""

from __future__ import annotations

from cle.grounding.five_w1h import FiveW1HOverrides
from cle.grounding.service import ground
from cle.grounding.sok import SOKOverrides

_PROMPT = "軌跡が不安定なので安定化してほしい。"
_GOAL = "stabilize trajectory"


def test_ground_returns_real_lift_result_not_a_stub() -> None:
    result = ground(_PROMPT, _GOAL)
    assert result.lift.concept_id.startswith("concept:")
    assert result.lift.proof.functor_axioms_satisfied is True


def test_ground_is_deterministic_for_identical_input() -> None:
    a = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="fixed-subject"))
    b = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="fixed-subject"))
    assert a.lift.concept_id == b.lift.concept_id
    assert a.lift.invariants == b.lift.invariants
    assert a.lift.compression_ratio == b.lift.compression_ratio
    assert a.semantic_state == b.semantic_state


def test_subject_change_causally_shifts_betti_numbers() -> None:
    """The acceptance criterion: S/O/K(t) is not just recorded on the
    response (it always was, trivially) -- it reaches CLE's real
    topological computation. Betti numbers are a hard, unfakeable proof:
    they come from `VietorisRipsComplex`/`betti_numbers` over the actual
    point cloud, with no path for the SOK string to influence them except
    through genuinely producing a different point cloud."""
    result_a = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="Japan_Govt"))
    result_b = ground(
        _PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="Private_Corp")
    )

    assert (
        result_a.semantic_state.subject_points != result_b.semantic_state.subject_points
    )
    assert result_a.lift.invariants != result_b.lift.invariants


def test_subject_change_causally_shifts_compression_ratio() -> None:
    result_a = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="Japan_Govt"))
    result_b = ground(
        _PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="Private_Corp")
    )
    assert result_a.lift.compression_ratio != result_b.lift.compression_ratio


def test_observer_change_causally_shifts_betti_numbers() -> None:
    result_a = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(observer="Observer_A"))
    result_b = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(observer="Observer_B"))
    assert result_a.lift.invariants != result_b.lift.invariants


def test_knowledge_reference_reaches_state_not_pushout_invariants() -> None:
    """Asymmetric by CLE's own pre-existing design, not a defect introduced
    here: `CLEEngine.lift()`'s `pushout_category` is
    `categorical_pushout(subject_category, observer_category)` -- a
    2-input operation (Stage 4, `cle.topology.pushout`) that never reads
    `knowledge_category`. Knowledge only feeds `three_view_pullback`
    (Stage 3). So Betti numbers/compression_ratio are, correctly,
    insensitive to Knowledge alone -- this is CLE's existing pushout
    definition, unchanged by Grounding, not something this module can or
    should alter. What Grounding *does* guarantee is that a Knowledge
    change reaches its own point cloud in GroundedState (proof it wasn't
    silently dropped before reaching the engine boundary)."""
    result_a = ground(
        _PROMPT, _GOAL, sok_overrides=SOKOverrides(knowledge_reference="K_2026")
    )
    result_b = ground(
        _PROMPT, _GOAL, sok_overrides=SOKOverrides(knowledge_reference="K_1999")
    )

    assert (
        result_a.semantic_state.knowledge_points
        != result_b.semantic_state.knowledge_points
    )
    # Documented, not silently passed over: this is the current *known
    # limitation*, not a false claim of causality.
    assert result_a.lift.invariants == result_b.lift.invariants
    assert result_a.lift.compression_ratio == result_b.lift.compression_ratio


def test_no_sok_change_isolated_to_subject_axis() -> None:
    """Diagnostic requirement: changing only Subject must not silently
    also move Observer/Knowledge's own point clouds (the axes are
    independent inputs, not derived from each other)."""
    result_a = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="A"))
    result_b = ground(_PROMPT, _GOAL, sok_overrides=SOKOverrides(subject="B"))
    assert (
        result_a.semantic_state.observer_points
        == result_b.semantic_state.observer_points
    )
    assert (
        result_a.semantic_state.knowledge_points
        == result_b.semantic_state.knowledge_points
    )


def test_prompt_change_causally_shifts_concept_points() -> None:
    result_a = ground("プロンプトA", "goal")
    result_b = ground("プロンプトB全く違う内容です", "goal")
    assert (
        result_a.semantic_state.concept_points != result_b.semantic_state.concept_points
    )


def test_five_w1h_overrides_reach_grounded_state() -> None:
    result = ground(
        _PROMPT, _GOAL, five_w1h_overrides=FiveW1HOverrides(who="explicit-who")
    )
    assert result.semantic_state.five_w1h.who.value == "explicit-who"
    assert (
        result.semantic_state.sok.subject == "explicit-who"
    )  # SOK derives subject from who
