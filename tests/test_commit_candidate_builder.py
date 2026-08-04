"""`ObservationalCommitCandidateBuilder` — CommitCandidate generation (RFC-CLE003)."""

from __future__ import annotations

import pytest

from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)
from cle.commit_candidate import (
    CommitCandidateBuilder,
    ObservationalCommitCandidateBuilder,
)


def _concept_delta_for(dwell_steps: float) -> KnowledgeDelta:
    concept = Concept(
        id="c1",
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=None,
        invariants={"dwell_steps": dwell_steps},
    )
    return KnowledgeDelta(
        id=f"delta-{dwell_steps}",
        kind=KnowledgeDeltaKind.CONCEPT_CREATED,
        concept=concept,
    )


def _reinforcement_delta_for(reinforcement_count: int) -> KnowledgeDelta:
    concept_delta = ConceptDelta(
        concept_id="c1",
        frame_id="F",
        centroid_shift=None,
        reinforcement_count=reinforcement_count,
    )
    return KnowledgeDelta(
        id="delta-2",
        kind=KnowledgeDeltaKind.CONCEPT_UPDATED,
        concept_delta=concept_delta,
    )


def _category_delta_for(concept_ids: tuple[str, ...]) -> KnowledgeDelta:
    category = Category(
        id="cat-1", label=None, concept_ids=concept_ids, structure_kind="cluster"
    )
    return KnowledgeDelta(
        id="delta-3", kind=KnowledgeDeltaKind.CATEGORY_FORMED, category=category
    )


def test_builder_satisfies_the_protocol() -> None:
    assert isinstance(
        ObservationalCommitCandidateBuilder(clock_ns=lambda: 0), CommitCandidateBuilder
    )


def test_confidence_is_always_within_bounds() -> None:
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)

    for dwell_steps in (0.0, 1.0, 5.0, 1000.0):
        candidate = builder.build(
            _concept_delta_for(dwell_steps), source_trajectory_id="t"
        )
        assert 0.0 <= candidate.confidence <= 1.0


def test_confidence_is_monotonically_increasing_with_dwell_steps() -> None:
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)

    confidences = [
        builder.build(_concept_delta_for(x), source_trajectory_id="t").confidence
        for x in (0.0, 1.0, 5.0, 20.0, 100.0)
    ]

    assert confidences == sorted(confidences)
    assert len(set(confidences)) == len(confidences)  # strictly increasing


def test_confidence_is_monotonically_increasing_with_reinforcement_count() -> None:
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)

    confidences = [
        builder.build(
            _reinforcement_delta_for(count), source_trajectory_id="t"
        ).confidence
        for count in (1, 2, 5, 10, 50)
    ]

    assert confidences == sorted(confidences)
    assert len(set(confidences)) == len(confidences)


def test_confidence_is_monotonically_increasing_with_category_size() -> None:
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)

    confidences = [
        builder.build(
            _category_delta_for(tuple(f"c{i}" for i in range(n))),
            source_trajectory_id="t",
        ).confidence
        for n in (1, 2, 5, 10)
    ]

    assert confidences == sorted(confidences)
    assert len(set(confidences)) == len(confidences)


def test_category_relation_confidence_is_always_exactly_one() -> None:
    relation = CategoryRelation(
        id="rel-1",
        source_category_id="cat-src",
        target_category_id="cat-tgt",
        relation_kind="functor",
    )
    delta = KnowledgeDelta(
        id="delta-4",
        kind=KnowledgeDeltaKind.CATEGORY_RELATED,
        category_relation=relation,
    )
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)

    candidate = builder.build(delta, source_trajectory_id="t")

    assert candidate.confidence == 1.0


def test_confidence_half_life_is_configurable() -> None:
    delta = _concept_delta_for(dwell_steps=5.0)
    low_half_life = ObservationalCommitCandidateBuilder(
        confidence_half_life=1.0, clock_ns=lambda: 0
    )
    high_half_life = ObservationalCommitCandidateBuilder(
        confidence_half_life=50.0, clock_ns=lambda: 0
    )

    low = low_half_life.build(delta, source_trajectory_id="t").confidence
    high = high_half_life.build(delta, source_trajectory_id="t").confidence

    # Same evidence, smaller half_life -> closer to saturation -> higher confidence.
    assert low > high


def test_clock_is_injectable_and_not_called_at_construction() -> None:
    calls = []

    def fake_clock() -> int:
        calls.append(1)
        return 42

    builder = ObservationalCommitCandidateBuilder(clock_ns=fake_clock)
    assert calls == []  # not called just by constructing the builder

    candidate = builder.build(_concept_delta_for(1.0), source_trajectory_id="t")

    assert candidate.created_at_ns == 42
    assert len(calls) == 1


def test_default_clock_is_the_real_wall_clock() -> None:
    import time

    builder = ObservationalCommitCandidateBuilder()

    assert builder.clock_ns is time.time_ns


def test_same_input_and_fixed_clock_produce_a_byte_identical_candidate() -> None:
    delta = _concept_delta_for(dwell_steps=3.0)
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 1_000)

    first = builder.build(delta, source_trajectory_id="traj-1")
    second = builder.build(delta, source_trajectory_id="traj-1")

    assert first == second


def test_candidate_id_is_deterministic_and_content_addressed() -> None:
    builder = ObservationalCommitCandidateBuilder(clock_ns=lambda: 0)
    delta_a = _concept_delta_for(dwell_steps=3.0)
    delta_b = _concept_delta_for(dwell_steps=7.0)

    candidate_a1 = builder.build(delta_a, source_trajectory_id="traj-1")
    candidate_a2 = builder.build(delta_a, source_trajectory_id="traj-1")
    candidate_b = builder.build(delta_b, source_trajectory_id="traj-1")

    assert candidate_a1.id == candidate_a2.id
    assert candidate_a1.id != candidate_b.id


def test_zero_confidence_half_life_is_rejected_at_construction() -> None:
    with pytest.raises(
        ValueError, match="confidence_half_life must be greater than zero"
    ):
        ObservationalCommitCandidateBuilder(confidence_half_life=0.0)


def test_negative_confidence_half_life_is_rejected_at_construction() -> None:
    with pytest.raises(
        ValueError, match="confidence_half_life must be greater than zero"
    ):
        ObservationalCommitCandidateBuilder(confidence_half_life=-5.0)


def test_positive_confidence_half_life_is_accepted() -> None:
    # Existing behavior unchanged for valid configuration.
    builder = ObservationalCommitCandidateBuilder(
        confidence_half_life=5.0, clock_ns=lambda: 0
    )

    candidate = builder.build(_concept_delta_for(5.0), source_trajectory_id="t")

    assert candidate.confidence == 0.5
