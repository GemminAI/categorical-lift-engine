"""`ArtifactKnowledgeDeltaGenerator` — KnowledgeDelta generation (RFC-CLE003)."""

from __future__ import annotations

from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    KnowledgeDeltaKind,
)
from cle.knowledge_delta import ArtifactKnowledgeDeltaGenerator, KnowledgeDeltaGenerator


def test_generator_satisfies_the_protocol() -> None:
    assert isinstance(ArtifactKnowledgeDeltaGenerator(), KnowledgeDeltaGenerator)


def test_concept_generates_a_concept_created_delta() -> None:
    concept = Concept(
        id="c1", frame_id="F", centroid=(1.0, 2.0), hessian=None, provenance=("o1",)
    )
    generator = ArtifactKnowledgeDeltaGenerator()

    delta = generator.generate(concept)

    assert delta.kind is KnowledgeDeltaKind.CONCEPT_CREATED
    assert delta.concept is concept
    assert delta.concept_delta is None
    assert delta.category is None
    assert delta.category_relation is None
    assert delta.provenance == concept.provenance


def test_concept_delta_generates_a_concept_updated_delta() -> None:
    # REINFORCE is represented as UPDATE, not a separate kind: the evidence
    # (reinforcement_count) lives on the payload, not on KnowledgeDeltaKind.
    concept_delta = ConceptDelta(
        concept_id="c1",
        frame_id="F",
        centroid_shift=(0.1, 0.1),
        reinforcement_count=5,
        provenance=("o1",),
    )
    generator = ArtifactKnowledgeDeltaGenerator()

    delta = generator.generate(concept_delta)

    assert delta.kind is KnowledgeDeltaKind.CONCEPT_UPDATED
    assert delta.concept_delta is concept_delta
    assert delta.concept_delta.reinforcement_count == 5


def test_category_generates_a_category_formed_delta() -> None:
    category = Category(
        id="cat-1", label=None, concept_ids=("c1", "c2"), structure_kind="cluster"
    )
    generator = ArtifactKnowledgeDeltaGenerator()

    delta = generator.generate(category)

    assert delta.kind is KnowledgeDeltaKind.CATEGORY_FORMED
    assert delta.category is category


def test_category_relation_generates_a_category_related_delta() -> None:
    relation = CategoryRelation(
        id="rel-1",
        source_category_id="cat-src",
        target_category_id="cat-tgt",
        relation_kind="functor",
    )
    generator = ArtifactKnowledgeDeltaGenerator()

    delta = generator.generate(relation)

    assert delta.kind is KnowledgeDeltaKind.CATEGORY_RELATED
    assert delta.category_relation is relation


def test_generation_is_deterministic() -> None:
    concept = Concept(id="c1", frame_id="F", centroid=(1.0, 2.0), hessian=None)
    generator = ArtifactKnowledgeDeltaGenerator()

    first = generator.generate(concept)
    second = generator.generate(concept)

    assert first == second


def test_delta_ids_are_consistent_with_content() -> None:
    # Delta consistency: two concept-delta events for the same concept_id
    # but different observable content (reinforcement_count) get different
    # ids, while identical content always gets the same id.
    generator = ArtifactKnowledgeDeltaGenerator()
    base = ConceptDelta(concept_id="c1", frame_id="F", centroid_shift=None)
    reinforced_once = ConceptDelta(
        concept_id="c1", frame_id="F", centroid_shift=None, reinforcement_count=1
    )
    reinforced_twice = ConceptDelta(
        concept_id="c1", frame_id="F", centroid_shift=None, reinforcement_count=2
    )

    delta_base = generator.generate(base)
    delta_once = generator.generate(reinforced_once)
    delta_twice = generator.generate(reinforced_twice)

    assert delta_base.id == delta_once.id  # reinforcement_count defaults to 1
    assert delta_once.id != delta_twice.id
