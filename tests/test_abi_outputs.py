from __future__ import annotations

import pytest

from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    HEKBCommitCandidate,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)


def make_concept(concept_id: str = "concept-1") -> Concept:
    return Concept(
        id=concept_id,
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=None,
        invariants={"depth": 1.0},
        source_trajectory_id="traj-1",
        provenance=("obs-1",),
    )


def test_concept_dimension() -> None:
    concept = make_concept()
    assert concept.dimension == 2


def test_concept_delta_defaults() -> None:
    delta = ConceptDelta(concept_id="concept-1", frame_id="F", centroid_shift=None)
    assert delta.reinforcement_count == 1
    assert delta.updated_invariants == {}


def test_category_requires_at_least_one_concept() -> None:
    with pytest.raises(ValueError, match="at least one concept_id"):
        Category(id="cat-1", label=None, concept_ids=(), structure_kind="generic")


def test_category_relation_construction() -> None:
    relation = CategoryRelation(
        id="rel-1",
        source_category_id="cat-1",
        target_category_id="cat-2",
        relation_kind="functor",
    )
    assert relation.relation_kind == "functor"


def test_knowledge_delta_requires_exactly_one_payload() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        KnowledgeDelta(id="kd-1", kind=KnowledgeDeltaKind.CONCEPT_CREATED)


def test_knowledge_delta_rejects_two_payloads() -> None:
    concept = make_concept()
    delta = ConceptDelta(concept_id="concept-1", frame_id="F", centroid_shift=None)
    with pytest.raises(ValueError, match="exactly one"):
        KnowledgeDelta(
            id="kd-1",
            kind=KnowledgeDeltaKind.CONCEPT_CREATED,
            concept=concept,
            concept_delta=delta,
        )


def make_created_delta(concept: Concept, delta_id: str = "kd-1") -> KnowledgeDelta:
    return KnowledgeDelta(
        id=delta_id, kind=KnowledgeDeltaKind.CONCEPT_CREATED, concept=concept
    )


def test_knowledge_delta_rejects_kind_payload_mismatch() -> None:
    concept = make_concept()
    with pytest.raises(ValueError, match="does not match its payload"):
        KnowledgeDelta(
            id="kd-1", kind=KnowledgeDeltaKind.CONCEPT_UPDATED, concept=concept
        )


def test_knowledge_delta_payload_property() -> None:
    concept = make_concept()
    delta = make_created_delta(concept)
    assert delta.payload is concept


def test_knowledge_delta_payload_guard_is_unreachable_through_the_public_api() -> None:
    # __post_init__ guarantees exactly one payload field is populated; the
    # only way to observe .payload's defensive AssertionError is to bypass
    # that guarantee directly on an already-constructed (frozen) instance.
    delta = make_created_delta(make_concept())
    object.__setattr__(delta, "concept", None)

    with pytest.raises(AssertionError, match="unreachable"):
        _ = delta.payload


def test_hekb_commit_candidate_confidence_bounds() -> None:
    concept = make_concept()
    delta = make_created_delta(concept)
    candidate = HEKBCommitCandidate(
        id="cand-1",
        delta=delta,
        confidence=0.5,
        source_trajectory_id="traj-1",
        created_at_ns=1_000,
    )
    assert candidate.confidence == 0.5

    with pytest.raises(ValueError, match="confidence"):
        HEKBCommitCandidate(
            id="cand-2",
            delta=delta,
            confidence=1.5,
            source_trajectory_id="traj-1",
            created_at_ns=1_000,
        )
