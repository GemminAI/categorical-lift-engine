"""RFC-CLE005 §2.1 Functoriality Invariance, adapted to this repository's model.

`CanonicalInclusionFunctorConstructor` has no explicit `compose` operation,
so `F(g∘f) = F(g)∘F(f)` cannot be tested literally. What *is* testable, and
what this repository's inclusion-functor model must satisfy for
functoriality to mean anything here: subset inclusion is transitive, so
whenever `A ⊆ B` and `B ⊆ C` both produce a functor, `A ⊆ C` must too — and
`construct` must raise `FunctorialityViolation` in precisely the cases
where no subset relationship exists, never fabricating one.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cle.abi.outputs import Category, CategoryRelation
from cle.errors import FunctorialityViolation
from cle.functor import CanonicalInclusionFunctorConstructor

_constructor = CanonicalInclusionFunctorConstructor()

_concept_id = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=6
)


@st.composite
def _nested_concept_id_triples(
    draw: st.DrawFn,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Three concept-id tuples with A subseteq B subseteq C, by construction.

    Built as growing prefixes of one shared, unique universe list — subset
    inclusion holds by the definition of "prefix", not by luck.
    """
    universe = draw(st.lists(_concept_id, min_size=1, max_size=12, unique=True))
    n = len(universe)
    size_a = draw(st.integers(min_value=1, max_value=n))
    size_b = draw(st.integers(min_value=size_a, max_value=n))
    size_c = draw(st.integers(min_value=size_b, max_value=n))
    return (
        tuple(universe[:size_a]),
        tuple(universe[:size_b]),
        tuple(universe[:size_c]),
    )


def _category(category_id: str, concept_ids: tuple[str, ...]) -> Category:
    return Category(
        id=category_id, label=None, concept_ids=concept_ids, structure_kind="cluster"
    )


@given(triple=_nested_concept_id_triples())
@settings(max_examples=200)
def test_inclusion_functors_compose_transitively(
    triple: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
) -> None:
    ids_a, ids_b, ids_c = triple
    cat_a, cat_b, cat_c = (
        _category("A", ids_a),
        _category("B", ids_b),
        _category("C", ids_c),
    )

    relation_ab = _constructor.construct(cat_a, cat_b)
    relation_bc = _constructor.construct(cat_b, cat_c)
    # Transitivity of subset inclusion: A subseteq B subseteq C implies
    # A subseteq C, so this direct hop must succeed too — never raise
    # just because it was reached by composition rather than directly.
    relation_ac = _constructor.construct(cat_a, cat_c)

    for relation in (relation_ab, relation_bc, relation_ac):
        assert isinstance(relation, CategoryRelation)
        assert relation.relation_kind == "functor"


@given(triple=_nested_concept_id_triples())
@settings(max_examples=200)
def test_functor_construction_is_deterministic(
    triple: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]],
) -> None:
    ids_a, ids_b, _ = triple
    cat_a, cat_b = _category("A", ids_a), _category("B", ids_b)

    first = _constructor.construct(cat_a, cat_b)
    second = _constructor.construct(cat_a, cat_b)

    assert first == second


@given(
    source_ids=st.lists(_concept_id, min_size=1, max_size=6, unique=True),
    target_ids=st.lists(_concept_id, min_size=1, max_size=6, unique=True),
)
@settings(max_examples=300)
def test_construct_succeeds_iff_source_is_a_subset_of_target(
    source_ids: list[str], target_ids: list[str]
) -> None:
    cat_source = _category("S", tuple(source_ids))
    cat_target = _category("T", tuple(target_ids))
    is_subset = set(source_ids) <= set(target_ids)

    if is_subset:
        relation = _constructor.construct(cat_source, cat_target)
        assert relation.relation_kind == "functor"
    else:
        with pytest.raises(FunctorialityViolation):
            _constructor.construct(cat_source, cat_target)
