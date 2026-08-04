"""`ProvenanceCanonicalizingCrystallizer` — Knowledge Crystallization (RFC-CLE003)."""

from __future__ import annotations

from cle.abi.outputs import Category, CategoryRelation, Concept, ConceptDelta
from cle.crystallization import (
    KnowledgeCrystallizer,
    ProvenanceCanonicalizingCrystallizer,
)


def test_crystallizer_satisfies_the_protocol() -> None:
    assert isinstance(ProvenanceCanonicalizingCrystallizer(), KnowledgeCrystallizer)


def test_deduplicates_concept_provenance_preserving_order() -> None:
    concept = Concept(
        id="c1",
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=None,
        provenance=("obs-1", "obs-2", "obs-1", "obs-3", "obs-2"),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    result = crystallizer.crystallize(concept)

    assert isinstance(result, Concept)
    assert result.provenance == ("obs-1", "obs-2", "obs-3")


def test_deduplicates_concept_delta_provenance() -> None:
    delta = ConceptDelta(
        concept_id="c1",
        frame_id="F",
        centroid_shift=(0.1, 0.1),
        provenance=("obs-1", "obs-1"),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    result = crystallizer.crystallize(delta)

    assert isinstance(result, ConceptDelta)
    assert result.provenance == ("obs-1",)


def test_deduplicates_category_provenance() -> None:
    category = Category(
        id="cat-1",
        label=None,
        concept_ids=("c1", "c2"),
        structure_kind="cluster",
        provenance=("obs-1", "obs-2", "obs-1"),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    result = crystallizer.crystallize(category)

    assert isinstance(result, Category)
    assert result.provenance == ("obs-1", "obs-2")


def test_deduplicates_category_relation_provenance() -> None:
    # The realistic source of duplicates: a functor's provenance combines
    # both endpoint categories' provenance, which can overlap.
    relation = CategoryRelation(
        id="rel-1",
        source_category_id="cat-src",
        target_category_id="cat-tgt",
        relation_kind="functor",
        provenance=("obs-1", "obs-2", "obs-2", "obs-3"),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    result = crystallizer.crystallize(relation)

    assert isinstance(result, CategoryRelation)
    assert result.provenance == ("obs-1", "obs-2", "obs-3")


def test_leaves_all_other_fields_unchanged() -> None:
    concept = Concept(
        id="c1",
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=((0.1, 0.0), (0.0, 0.1)),
        invariants={"dwell_steps": 3.0},
        source_trajectory_id="traj-1",
        provenance=("obs-1",),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    result = crystallizer.crystallize(concept)

    assert isinstance(result, Concept)
    assert result.id == concept.id
    assert result.frame_id == concept.frame_id
    assert result.centroid == concept.centroid
    assert result.hessian == concept.hessian
    assert result.invariants == concept.invariants
    assert result.source_trajectory_id == concept.source_trajectory_id


def test_crystallization_is_idempotent_and_deterministic() -> None:
    # Same input -> same candidate: crystallizing an already-crystallized
    # artifact (or the same artifact twice) yields an identical result.
    concept = Concept(
        id="c1",
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=None,
        provenance=("obs-1", "obs-2", "obs-1"),
    )
    crystallizer = ProvenanceCanonicalizingCrystallizer()

    once = crystallizer.crystallize(concept)
    twice = crystallizer.crystallize(once)
    again = crystallizer.crystallize(concept)

    assert once == twice == again
