"""`CanonicalInclusionFunctorConstructor` — functor construction (RFC-CLE001)."""

from __future__ import annotations

import pytest

from cle.abi.outputs import Category, CategoryRelation
from cle.errors import FunctorialityViolation
from cle.functor import CanonicalInclusionFunctorConstructor, FunctorConstructor


def test_canonical_inclusion_functor_constructor_satisfies_the_protocol() -> None:
    assert isinstance(CanonicalInclusionFunctorConstructor(), FunctorConstructor)


def test_constructs_a_functor_when_source_concepts_are_a_subset_of_target() -> None:
    source = Category(
        id="cat-source",
        label=None,
        concept_ids=("c1", "c2"),
        structure_kind="cluster",
        provenance=("obs-1",),
    )
    target = Category(
        id="cat-target",
        label=None,
        concept_ids=("c1", "c2", "c3"),
        structure_kind="cluster",
        provenance=("obs-2",),
    )
    constructor = CanonicalInclusionFunctorConstructor()

    relation = constructor.construct(source, target)

    assert isinstance(relation, CategoryRelation)
    assert relation.source_category_id == source.id
    assert relation.target_category_id == target.id
    assert relation.relation_kind == "functor"
    assert relation.provenance == source.provenance + target.provenance


def test_functor_construction_is_deterministic() -> None:
    source = Category(
        id="cat-source", label=None, concept_ids=("c1",), structure_kind="cluster"
    )
    target = Category(
        id="cat-target",
        label=None,
        concept_ids=("c1", "c2"),
        structure_kind="cluster",
    )
    constructor = CanonicalInclusionFunctorConstructor()

    first = constructor.construct(source, target)
    second = constructor.construct(source, target)

    assert first == second


def test_raises_when_source_concepts_are_not_included_in_target() -> None:
    source = Category(
        id="cat-source",
        label=None,
        concept_ids=("c1", "c-missing"),
        structure_kind="cluster",
    )
    target = Category(
        id="cat-target", label=None, concept_ids=("c1",), structure_kind="cluster"
    )
    constructor = CanonicalInclusionFunctorConstructor()

    with pytest.raises(FunctorialityViolation):
        constructor.construct(source, target)
