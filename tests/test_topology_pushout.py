"""`categorical_pushout` (CLE v3 spec §3.4)."""

from __future__ import annotations

import pytest

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.topology.pushout import categorical_pushout


def test_pushout_of_disjoint_categories_is_their_union() -> None:
    shared = Morphism("shared", "A", "B")
    category_s = FiniteCategory(
        objects=frozenset({"A", "B"}), morphisms={"shared": shared}, composition={}
    )
    only_o = Morphism("only_o", "C", "D")
    category_o = FiniteCategory(
        objects=frozenset({"C", "D"}), morphisms={"only_o": only_o}, composition={}
    )
    result = categorical_pushout(category_s, category_o)
    assert result.objects == frozenset({"A", "B", "C", "D"})
    assert result.morphisms == {"shared": shared, "only_o": only_o}


def test_pushout_identifies_shared_members_without_duplication() -> None:
    shared = Morphism("shared", "A", "B")
    category_s = FiniteCategory(
        objects=frozenset({"A", "B"}), morphisms={"shared": shared}, composition={}
    )
    category_o = FiniteCategory(
        objects=frozenset({"A", "B"}), morphisms={"shared": shared}, composition={}
    )
    result = categorical_pushout(category_s, category_o)
    assert result.morphisms == {"shared": shared}


def test_pushout_rejects_a_morphism_gluing_conflict() -> None:
    category_s = FiniteCategory(
        objects=frozenset({"A", "B"}),
        morphisms={"m": Morphism("m", "A", "B")},
        composition={},
    )
    category_o = FiniteCategory(
        objects=frozenset({"A", "C"}),
        morphisms={"m": Morphism("m", "A", "C")},
        composition={},
    )
    with pytest.raises(FunctorialityViolation, match="gluing conflict at morphism"):
        categorical_pushout(category_s, category_o)


def test_pushout_rejects_a_composition_gluing_conflict() -> None:
    """`f` and `g` are shared, identical morphisms in both categories (so no
    morphism-level conflict), but each category disagrees on what `g . f`
    composes to -- a genuine composition-level gluing conflict."""
    a, b, c = "A", "B", "C"
    f = Morphism("f", a, b)
    g = Morphism("g", b, c)
    h1 = Morphism("h1", a, c)
    h2 = Morphism("h2", a, c)
    category_s = FiniteCategory(
        objects=frozenset({a, b, c}),
        morphisms={"f": f, "g": g, "h1": h1},
        composition={("g", "f"): "h1"},
    )
    category_o = FiniteCategory(
        objects=frozenset({a, b, c}),
        morphisms={"f": f, "g": g, "h2": h2},
        composition={("g", "f"): "h2"},
    )
    with pytest.raises(FunctorialityViolation, match="gluing conflict at composition"):
        categorical_pushout(category_s, category_o)


def test_pushout_union_preserves_non_conflicting_composition_entries() -> None:
    a, b = "A", "B"
    id_a, id_b = Morphism("id_A", a, a), Morphism("id_B", b, b)
    category_s = FiniteCategory(
        objects=frozenset({a}),
        morphisms={"id_A": id_a},
        composition={("id_A", "id_A"): "id_A"},
    )
    category_o = FiniteCategory(
        objects=frozenset({b}),
        morphisms={"id_B": id_b},
        composition={("id_B", "id_B"): "id_B"},
    )
    result = categorical_pushout(category_s, category_o)
    assert result.composition == {("id_A", "id_A"): "id_A", ("id_B", "id_B"): "id_B"}
