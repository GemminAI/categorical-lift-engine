"""`FunctorialConceptLift` — object lifting (RFC-CLE001 Phase 1)."""

from __future__ import annotations

import pytest

from cle.abi.outputs import Concept, ConceptDelta
from cle.concept import ConceptDiscoveryStrategy, FunctorialConceptLift
from cle.errors import DimensionMismatch, InvalidTrajectory
from conftest import (
    FakeHEKBConcept,
    FakeHEKBContext,
    FakeInconsistentTrajectory,
    FakeStabilizedTrajectory,
)


def test_functorial_concept_lift_satisfies_the_protocol() -> None:
    assert isinstance(FunctorialConceptLift(), ConceptDiscoveryStrategy)


def test_novel_trajectory_lifts_to_a_new_concept(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = FunctorialConceptLift()

    concept = engine.discover(stabilized_trajectory, hekb_context=None)

    assert isinstance(concept, Concept)
    assert concept.frame_id == stabilized_trajectory.frame_id
    assert concept.centroid == stabilized_trajectory.centroid
    assert concept.hessian == stabilized_trajectory.covariance
    assert concept.source_trajectory_id == stabilized_trajectory.trajectory_id
    assert concept.provenance == stabilized_trajectory.provenance
    assert concept.invariants["state_count"] == float(len(stabilized_trajectory.states))


def test_novel_lift_is_deterministic(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = FunctorialConceptLift()

    first = engine.discover(stabilized_trajectory, hekb_context=None)
    second = engine.discover(stabilized_trajectory, hekb_context=None)

    assert first == second


def test_reinforcing_trajectory_without_context_falls_back_to_basin_id(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = FunctorialConceptLift()

    delta = engine.discover(reinforcing_trajectory, hekb_context=None)

    assert isinstance(delta, ConceptDelta)
    assert delta.centroid_shift is None
    # deterministic: same basin_id -> same fallback concept_id every time
    again = engine.discover(reinforcing_trajectory, hekb_context=None)
    assert delta.concept_id == again.concept_id  # type: ignore[union-attr]


def test_reinforcing_trajectory_matches_known_concept_by_centroid(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    known = FakeHEKBConcept(id="hekb-concept-1", centroid=(1.0, 2.0))
    context = FakeHEKBContext(near=(known,))
    engine = FunctorialConceptLift()

    delta = engine.discover(reinforcing_trajectory, hekb_context=context)

    assert isinstance(delta, ConceptDelta)
    assert delta.concept_id == known.id
    assert delta.centroid_shift is not None
    expected_shift = tuple(
        t - k
        for t, k in zip(reinforcing_trajectory.centroid, known.centroid, strict=True)  # type: ignore[arg-type]
    )
    assert delta.centroid_shift == expected_shift


def test_reinforcing_trajectory_with_centroid_less_candidate_uses_its_id(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    known = FakeHEKBConcept(id="hekb-concept-no-centroid", centroid=None)
    context = FakeHEKBContext(near=(known,))
    engine = FunctorialConceptLift()

    delta = engine.discover(reinforcing_trajectory, hekb_context=context)

    assert isinstance(delta, ConceptDelta)
    assert delta.concept_id == known.id
    assert delta.centroid_shift is None


def test_reinforcing_trajectory_picks_the_nearest_of_several_candidates(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    near = FakeHEKBConcept(id="near", centroid=(1.1, 2.1))
    far = FakeHEKBConcept(id="far", centroid=(50.0, 50.0))
    context = FakeHEKBContext(near=(far, near))
    engine = FunctorialConceptLift()

    delta = engine.discover(reinforcing_trajectory, hekb_context=context)

    assert isinstance(delta, ConceptDelta)
    assert delta.concept_id == near.id


def test_reinforcing_trajectory_with_no_nearby_candidates_falls_back(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    context = FakeHEKBContext(near=())
    engine = FunctorialConceptLift()

    delta = engine.discover(reinforcing_trajectory, hekb_context=context)

    assert isinstance(delta, ConceptDelta)
    assert delta.centroid_shift is None


def test_tied_candidates_break_ties_deterministically_by_id(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    tied_a = FakeHEKBConcept(id="z-concept", centroid=(1.1, 2.1))
    tied_b = FakeHEKBConcept(id="a-concept", centroid=(1.1, 2.1))
    engine = FunctorialConceptLift()

    # Same trajectory, same candidates, only the host's return order differs
    # — the match must not depend on that order (RFC-CLE005 §3.2).
    first = engine.discover(
        reinforcing_trajectory, hekb_context=FakeHEKBContext(near=(tied_a, tied_b))
    )
    second = engine.discover(
        reinforcing_trajectory, hekb_context=FakeHEKBContext(near=(tied_b, tied_a))
    )

    assert isinstance(first, ConceptDelta)
    assert isinstance(second, ConceptDelta)
    assert first.concept_id == second.concept_id == "a-concept"


def test_reinforcing_trajectory_without_basin_id_or_match_is_rejected(
    reinforcing_trajectory_without_basin_id: FakeInconsistentTrajectory,
) -> None:
    engine = FunctorialConceptLift()

    with pytest.raises(InvalidTrajectory):
        engine.discover(reinforcing_trajectory_without_basin_id, hekb_context=None)


def test_dimension_mismatch_between_centroid_and_covariance_is_rejected(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    from dataclasses import replace

    bad_trajectory = replace(stabilized_trajectory, covariance=((1.0, 0.0),))
    engine = FunctorialConceptLift()

    with pytest.raises(DimensionMismatch):
        engine.discover(bad_trajectory, hekb_context=None)


def test_dimension_mismatch_with_wrong_row_length_is_rejected(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    from dataclasses import replace

    bad_trajectory = replace(
        stabilized_trajectory, covariance=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    )
    engine = FunctorialConceptLift()

    with pytest.raises(DimensionMismatch):
        engine.discover(bad_trajectory, hekb_context=None)


def test_dimension_mismatch_between_trajectory_and_matched_concept_centroid(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    mismatched = FakeHEKBConcept(id="wrong-dim", centroid=(1.0, 2.0, 3.0))
    context = FakeHEKBContext(near=(mismatched,))
    engine = FunctorialConceptLift()

    with pytest.raises(DimensionMismatch):
        engine.discover(reinforcing_trajectory, hekb_context=context)


def test_zero_trace_covariance_uses_zero_radius(
    reinforcing_trajectory: FakeStabilizedTrajectory,
) -> None:
    from dataclasses import replace

    zero_covariance_trajectory = replace(
        reinforcing_trajectory, covariance=((0.0, 0.0), (0.0, 0.0))
    )
    known = FakeHEKBConcept(id="hekb-concept-1", centroid=(1.0, 2.0))
    context = FakeHEKBContext(near=(known,))
    engine = FunctorialConceptLift()

    # radius collapses to 0.0; concepts_near is a fake that returns `near`
    # unconditionally, so the match still resolves — this exercises the
    # zero-trace branch of the radius heuristic without asserting on a real
    # host's filtering behaviour (out of scope for this repository).
    delta = engine.discover(zero_covariance_trajectory, hekb_context=context)

    assert isinstance(delta, ConceptDelta)
    assert delta.concept_id == known.id
