"""`CLEEngine` and its seven pipeline stages (CLE v3 spec §3/§4.2)."""

from __future__ import annotations

import math
from unittest import mock

import pytest

from cle.errors import NoStrategyConfigured
from cle.runtime.engine import (
    CLEEngine,
    _category_from_point_cloud,
    _coordinates_of,
    apply_functors,
    compress_cognitive_structure,
    extract_invariants,
    normalize,
    prove_conformance,
    three_view_pullback,
)
from cle.runtime.models import InvariantSignature, LiftResult, ProofCertificate
from conftest import FakeMeaningState, FakeStabilizedTrajectory

_EPS = 1.5


def _trajectory(
    points: tuple[tuple[float, ...], ...], trajectory_id: str = "t"
) -> FakeStabilizedTrajectory:
    states = tuple(
        FakeMeaningState(
            frame_id="F", step_index=i, time_s=float(i), theta=p, basin_id=None
        )
        for i, p in enumerate(points)
    )
    return FakeStabilizedTrajectory(
        trajectory_id=trajectory_id,
        frame_id="F",
        basin_id=None,
        states=states,
        centroid=points[0] if points else (),
        covariance=(),
        dwell_steps=len(points),
        dwell_seconds=float(len(points)),
    )


_TRIANGLE_POINTS = ((0.0, 0.0), (1.0, 0.0), (0.5, 0.9))


# --- Stage 1: normalize ------------------------------------------------------


def test_normalize_is_deterministic_for_equal_coordinates() -> None:
    a = _trajectory(_TRIANGLE_POINTS, "a")
    b = _trajectory(_TRIANGLE_POINTS, "b")  # different id, same coordinates
    hash_a, coords_a = normalize(a)
    hash_b, coords_b = normalize(b)
    assert hash_a == hash_b
    assert coords_a == coords_b


def test_normalize_differs_for_different_coordinates() -> None:
    hash_a, _ = normalize(_trajectory(_TRIANGLE_POINTS))
    hash_b, _ = normalize(_trajectory(((0.0, 0.0), (2.0, 0.0))))
    assert hash_a != hash_b


# --- _coordinates_of ---------------------------------------------------------


def test_coordinates_of_a_trajectory_uses_its_states() -> None:
    coords = _coordinates_of(_trajectory(_TRIANGLE_POINTS))
    assert coords == _TRIANGLE_POINTS


def test_coordinates_of_a_centroid_only_object() -> None:
    class WithCentroid:
        centroid = (1.0, 2.0)

    assert _coordinates_of(WithCentroid()) == ((1.0, 2.0),)


def test_coordinates_of_a_bare_vector() -> None:
    assert _coordinates_of((3.0, 4.0)) == ((3.0, 4.0),)


def test_coordinates_of_an_unsupported_shape_raises() -> None:
    with pytest.raises(TypeError, match="cannot derive point-cloud coordinates"):
        _coordinates_of(object())


# --- Stage 2: apply_functors --------------------------------------------------


def test_apply_functors_returns_a_valid_identity_functor() -> None:
    category = _category_from_point_cloud(_TRIANGLE_POINTS, eps=_EPS)
    functor = apply_functors(category)
    assert functor.source is category
    assert functor.target is category
    for obj in category.objects:
        assert functor.apply_object(obj) == obj


# --- Stage 3: three_view_pullback --------------------------------------------


def test_three_view_pullback_of_identical_categories_is_all_morphisms() -> None:
    category = _category_from_point_cloud(((0.0, 0.0), (1.0, 0.0)), eps=_EPS)
    shared = three_view_pullback(category, category, category)
    assert shared == frozenset(category.morphisms.values())


# --- Stage 5: extract_invariants ---------------------------------------------


def test_extract_invariants_of_a_filled_triangle_has_no_first_betti_number() -> None:
    category = _category_from_point_cloud(_TRIANGLE_POINTS, eps=_EPS)
    invariants = extract_invariants(category, max_dimension=2)
    assert (invariants.betti_0, invariants.betti_1, invariants.betti_2) == (1, 0, 0)


def test_extract_invariants_of_two_isolated_points() -> None:
    category = _category_from_point_cloud(((0.0, 0.0), (100.0, 100.0)), eps=1.0)
    invariants = extract_invariants(category, max_dimension=1)
    assert invariants.betti_0 == 2


# --- Stage 6: compress_cognitive_structure ------------------------------------


def test_compress_cognitive_structure_produces_a_ratio_and_a_closure() -> None:
    category = _category_from_point_cloud(_TRIANGLE_POINTS, eps=_EPS)
    invariants = extract_invariants(category, max_dimension=2)
    ratio, closure = compress_cognitive_structure(invariants, category, "x" * 500)
    assert ratio > 0.0
    assert closure["betti"] == (1, 0, 0)
    assert closure["euler_characteristic"] == 1


# --- Stage 7: prove_conformance ------------------------------------------------


def test_prove_conformance_on_a_filled_triangle_is_valid() -> None:
    category = _category_from_point_cloud(_TRIANGLE_POINTS, eps=_EPS)
    proof = prove_conformance(category, max_dimension=2)
    assert proof.is_valid
    assert proof.boundary_condition_verified
    assert proof.functor_axioms_satisfied
    assert any("verified" in line for line in proof.proof_trace)


def test_prove_conformance_on_isolated_points_has_no_higher_simplices() -> None:
    category = _category_from_point_cloud(((0.0, 0.0), (100.0, 100.0)), eps=1.0)
    proof = prove_conformance(category, max_dimension=2)
    assert proof.is_valid


def test_prove_conformance_reports_a_boundary_composition_failure() -> None:
    """d_k . d_{k+1} = 0 always holds for a real simplicial complex; forcing
    the failure branch (via a patched comparison) is the only way to
    exercise the defensive report path at all."""
    category = _category_from_point_cloud(_TRIANGLE_POINTS, eps=_EPS)
    with mock.patch("cle.runtime.engine.np.allclose", return_value=False):
        proof = prove_conformance(category, max_dimension=2)
    assert not proof.is_valid
    assert not proof.boundary_condition_verified
    assert any("failed" in line for line in proof.proof_trace)


# --- CLEEngine.lift ------------------------------------------------------------


def test_lift_without_views_uses_the_concepts_own_category() -> None:
    engine = CLEEngine(eps=_EPS)
    result = engine.lift(_trajectory(_TRIANGLE_POINTS))
    assert result.invariants.betti_0 == 1
    assert result.proof.is_valid
    assert result.pullback_limit == {"morphisms": []}


def test_lift_with_three_views_uses_pullback_and_pushout() -> None:
    engine = CLEEngine(eps=_EPS)
    concept = _trajectory(_TRIANGLE_POINTS)
    subject = _trajectory(((0.0, 0.0), (1.0, 0.0)))
    observer = _trajectory(((0.0, 0.0), (1.0, 0.0)))
    knowledge = _trajectory(((0.0, 0.0), (1.0, 0.0)))
    result = engine.lift(concept, subject, observer, knowledge)
    assert result.pullback_limit["morphisms"]  # subject/observer/knowledge fully agree
    assert result.pushout_colimit["objects"] == ["v0", "v1"]


def test_lift_is_deterministic_for_the_same_concept() -> None:
    engine = CLEEngine(eps=_EPS)
    concept_a = _trajectory(_TRIANGLE_POINTS, "a")
    concept_b = _trajectory(_TRIANGLE_POINTS, "b")
    result_a = engine.lift(concept_a)
    result_b = engine.lift(concept_b)
    assert result_a.concept_id == result_b.concept_id
    assert result_a.normalized_hash == result_b.normalized_hash


def test_lift_calls_the_configured_hekb_store() -> None:
    calls: list[object] = []

    class RecordingStore:
        def store(self, lift_result: object) -> bool:
            calls.append(lift_result)
            return True

    engine = CLEEngine(eps=_EPS, hekb_store=RecordingStore())
    result = engine.lift(_trajectory(_TRIANGLE_POINTS))
    assert calls == [result]


# --- CLEEngine.lift_many -------------------------------------------------------


def test_lift_many_sequential_matches_individual_lifts() -> None:
    engine = CLEEngine(eps=_EPS)
    concepts = [
        _trajectory(_TRIANGLE_POINTS, "a"),
        _trajectory(((0.0, 0.0), (2.0, 0.0)), "b"),
    ]
    sequential = engine.lift_many(concepts, parallel=False)
    individual = [engine.lift(c) for c in concepts]
    assert [r.concept_id for r in sequential] == [r.concept_id for r in individual]


def test_lift_many_parallel_matches_sequential() -> None:
    engine = CLEEngine(eps=_EPS)
    concepts = [
        _trajectory(_TRIANGLE_POINTS, "a"),
        _trajectory(((0.0, 0.0), (2.0, 0.0)), "b"),
    ]
    parallel = engine.lift_many(concepts, parallel=True)
    sequential = engine.lift_many(concepts, parallel=False)
    assert {r.concept_id for r in parallel} == {r.concept_id for r in sequential}


def test_lift_many_of_an_empty_list_is_empty() -> None:
    engine = CLEEngine(eps=_EPS)
    assert engine.lift_many([]) == []


# --- CLEEngine.compare ----------------------------------------------------------


def test_compare_identical_concepts_are_isomorphic() -> None:
    engine = CLEEngine(eps=_EPS)
    a = engine.lift(_trajectory(_TRIANGLE_POINTS, "a"))
    b = engine.lift(_trajectory(_TRIANGLE_POINTS, "b"))
    comparison = engine.compare(a, b)
    assert comparison.is_isomorphic
    assert comparison.homology_distance == pytest.approx(0.0)
    assert comparison.mapping_functor_exists


def test_compare_different_topology_is_not_isomorphic() -> None:
    engine = CLEEngine(eps=_EPS)
    a = engine.lift(_trajectory(_TRIANGLE_POINTS))
    b = engine.lift(_trajectory(((0.0, 0.0), (100.0, 100.0))))
    comparison = engine.compare(a, b)
    assert not comparison.is_isomorphic
    assert comparison.homology_distance == pytest.approx(math.sqrt(1.0))


def test_compare_reports_no_functor_when_a_is_not_included_in_b() -> None:
    engine = CLEEngine(eps=_EPS)
    small = engine.lift(_trajectory(((0.0, 0.0), (1.0, 0.0))))
    larger = engine.lift(_trajectory(((0.0, 0.0), (1.0, 0.0), (5.0, 5.0))))
    # small's objects ARE a subset of larger's -> functor exists this direction
    forward = engine.compare(small, larger)
    assert forward.mapping_functor_exists
    # larger's objects are NOT a subset of small's -> no functor this direction
    backward = engine.compare(larger, small)
    assert not backward.mapping_functor_exists


def test_compare_with_no_morphisms_on_either_side_reports_no_functor() -> None:
    empty = LiftResult(
        concept_id="concept:empty",
        normalized_hash="normalized:empty",
        morphisms=frozenset(),
        pullback_limit={},
        pushout_colimit={},
        invariants=InvariantSignature.from_betti((0,)),
        compression_ratio=1.0,
        semantic_closure={},
        proof=ProofCertificate(
            is_valid=True,
            boundary_condition_verified=True,
            functor_axioms_satisfied=True,
        ),
    )
    engine = CLEEngine(eps=_EPS)
    comparison = engine.compare(empty, empty)
    assert not comparison.mapping_functor_exists


# --- CLEEngine.recover -----------------------------------------------------------


Vector = tuple[float, ...]


class _FakeRecoveryEngine:
    """Structurally identical to nvs_kernel's ThreeViewTrajectoryRecovery."""

    def recover_state(
        self,
        current_x: Vector,
        x_subject: Vector,
        x_observer: Vector,
        x_human: Vector,
        *,
        steps: int = 20,
        lr: float = 0.05,
    ) -> Vector:
        weight = 1.0 / 3.0
        return tuple(
            weight * s + weight * o + weight * h
            for s, o, h in zip(x_subject, x_observer, x_human, strict=True)
        )

    def compute_recovery_gradient(
        self, current_x: Vector, x_subject: Vector, x_observer: Vector, x_human: Vector
    ) -> Vector:
        return tuple(0.0 for _ in current_x)


def test_recover_without_a_configured_engine_raises() -> None:
    engine = CLEEngine(eps=_EPS)
    with pytest.raises(NoStrategyConfigured, match="recovery_engine"):
        engine.recover((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))


def test_recover_bridges_the_pullback_with_the_recovery_engine() -> None:
    engine = CLEEngine(eps=_EPS, recovery_engine=_FakeRecoveryEngine())
    result = engine.recover((1.0, 0.0), (0.0, 1.0), (0.0, 0.0))
    assert result.converged
    assert result.recovered_state_id.startswith("recovered:")
    assert result.reconstructed_closure["recovered_state"]


def test_recover_discrepancy_is_zero_when_all_three_views_fully_agree() -> None:
    engine = CLEEngine(eps=_EPS, recovery_engine=_FakeRecoveryEngine())
    same = (1.0, 0.0)
    result = engine.recover(same, same, same)
    assert result.three_view_discrepancy == pytest.approx(0.0)
