"""`ThreeViewPullbackEngine` / `compute_common_invariant_subgraph`."""

from __future__ import annotations

import pytest

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.topology.three_view_pullback import (
    ThreeViewPullbackEngine,
    compute_common_invariant_subgraph,
)

_AB = frozenset({"A", "B"})


def _category(
    morphisms: dict[str, Morphism], objects: frozenset[str]
) -> FiniteCategory:
    return FiniteCategory(objects=objects, morphisms=morphisms, composition={})


def test_shared_morphism_present_in_all_three_views_is_recovered() -> None:
    shared = Morphism("shared", "A", "B")
    category_s = _category({"shared": shared}, _AB)
    category_o = _category({"shared": shared}, _AB)
    category_h = _category({"shared": shared}, _AB)
    common = compute_common_invariant_subgraph(category_s, category_o, category_h)
    assert common == {shared}


def test_morphism_present_in_only_two_views_is_not_in_the_common_subgraph() -> None:
    shared = Morphism("shared", "A", "B")
    only_in_s = Morphism("only_s", "A", "B")
    category_s = _category({"shared": shared, "only_s": only_in_s}, _AB)
    category_o = _category({"shared": shared}, _AB)
    category_h = _category({"shared": shared}, _AB)
    common = compute_common_invariant_subgraph(category_s, category_o, category_h)
    assert common == {shared}


def test_empty_categories_yield_an_empty_common_subgraph() -> None:
    empty = _category({}, frozenset({"A"}))
    common = compute_common_invariant_subgraph(empty, empty, empty)
    assert common == set()


def test_disjoint_categories_yield_an_empty_common_subgraph() -> None:
    category_s = _category({"s_only": Morphism("s_only", "A", "B")}, _AB)
    category_o = _category({"o_only": Morphism("o_only", "A", "B")}, _AB)
    category_h = _category({"h_only": Morphism("h_only", "A", "B")}, _AB)
    common = compute_common_invariant_subgraph(category_s, category_o, category_h)
    assert common == set()


def test_disagreeing_endpoints_for_the_same_name_raise_functoriality_error() -> None:
    category_s = _category({"m": Morphism("m", "A", "B")}, _AB)
    category_o = _category({"m": Morphism("m", "A", "C")}, frozenset({"A", "C"}))
    category_h = _category({}, frozenset({"A"}))
    with pytest.raises(FunctorialityViolation, match="disagrees across views"):
        compute_common_invariant_subgraph(category_s, category_o, category_h)


def test_engine_facade_delegates_to_the_function() -> None:
    shared = Morphism("shared", "A", "B")
    category_s = _category({"shared": shared}, _AB)
    category_o = _category({"shared": shared}, _AB)
    category_h = _category({"shared": shared}, _AB)
    engine = ThreeViewPullbackEngine()
    result = engine.compute_common_invariant_subgraph(
        category_s, category_o, category_h
    )
    assert result == {shared}
