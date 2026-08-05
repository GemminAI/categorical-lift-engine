"""`FiniteCategory` / `Functor` / composition (spec v2.0.0 §4.2)."""

from __future__ import annotations

import pytest

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Functor, Morphism


def _walking_arrow(prefix: str) -> FiniteCategory:
    """The free category on a single arrow f: A -> B, plus identities."""
    a, b = f"{prefix}A", f"{prefix}B"
    id_a = Morphism(f"id_{a}", a, a)
    id_b = Morphism(f"id_{b}", b, b)
    f = Morphism(f"{prefix}f", a, b)
    return FiniteCategory(
        objects=frozenset({a, b}),
        morphisms={id_a.name: id_a, id_b.name: id_b, f.name: f},
        composition={
            (id_a.name, id_a.name): id_a.name,
            (id_b.name, id_b.name): id_b.name,
            (f.name, id_a.name): f.name,
            (id_b.name, f.name): f.name,
        },
    )


def test_category_rejects_a_morphism_referencing_an_unknown_object() -> None:
    stray = Morphism("f", "A", "Z")
    with pytest.raises(ValueError, match="outside this category"):
        FiniteCategory(objects=frozenset({"A"}), morphisms={"f": stray}, composition={})


def test_category_rejects_a_non_composable_pair() -> None:
    f = Morphism("f", "A", "B")
    g = Morphism("g", "C", "D")
    h = Morphism("h", "A", "D")
    with pytest.raises(ValueError, match="not composable"):
        FiniteCategory(
            objects=frozenset({"A", "B", "C", "D"}),
            morphisms={"f": f, "g": g, "h": h},
            composition={("g", "f"): "h"},
        )


def test_category_rejects_an_inconsistent_composition_target() -> None:
    f = Morphism("f", "A", "B")
    g = Morphism("g", "B", "C")
    wrong = Morphism("wrong", "A", "A")
    with pytest.raises(ValueError, match="must equal"):
        FiniteCategory(
            objects=frozenset({"A", "B", "C"}),
            morphisms={"f": f, "g": g, "wrong": wrong},
            composition={("g", "f"): "wrong"},
        )


def test_identity_functor_satisfies_all_three_axioms() -> None:
    category = _walking_arrow("")
    identity = Functor(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B"},
        morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
    )
    assert identity.apply_object("A") == "A"
    assert identity.apply_morphism("f") == "f"


def test_functor_rejects_an_object_with_no_image() -> None:
    category = _walking_arrow("")
    with pytest.raises(FunctorialityViolation, match="no image"):
        Functor(
            source=category,
            target=category,
            object_map={"A": "A"},  # B missing
            morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
        )


def test_functor_rejects_an_object_mapped_outside_the_target_category() -> None:
    category = _walking_arrow("")
    with pytest.raises(FunctorialityViolation, match="not an object"):
        Functor(
            source=category,
            target=category,
            object_map={"A": "A", "B": "not-a-real-object"},
            morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
        )


def test_functor_rejects_a_morphism_with_no_image() -> None:
    category = _walking_arrow("")
    with pytest.raises(FunctorialityViolation, match="morphism 'f' has no image"):
        Functor(
            source=category,
            target=category,
            object_map={"A": "A", "B": "B"},
            morphism_map={"id_A": "id_A", "id_B": "id_B"},  # f missing
        )


def test_functor_rejects_a_morphism_mapped_to_a_nonexistent_morphism() -> None:
    category = _walking_arrow("")
    with pytest.raises(FunctorialityViolation, match="not a morphism"):
        Functor(
            source=category,
            target=category,
            object_map={"A": "A", "B": "B"},
            morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "not-a-real-morphism"},
        )


def test_functor_rejects_a_morphism_landing_at_the_wrong_object() -> None:
    category = _walking_arrow("")
    with pytest.raises(FunctorialityViolation, match="must start at"):
        Functor(
            source=category,
            target=category,
            object_map={"A": "B", "B": "A"},  # swapped
            morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
        )


def _composable_pair() -> FiniteCategory:
    """A -f-> B -g-> C, with h = g . f made an explicit third morphism."""
    a, b, c = "A", "B", "C"
    id_a = Morphism("id_A", a, a)
    id_b = Morphism("id_B", b, b)
    id_c = Morphism("id_C", c, c)
    f, g, h = Morphism("f", a, b), Morphism("g", b, c), Morphism("h", a, c)
    return FiniteCategory(
        objects=frozenset({a, b, c}),
        morphisms={"id_A": id_a, "id_B": id_b, "id_C": id_c, "f": f, "g": g, "h": h},
        composition={
            ("id_A", "id_A"): "id_A",
            ("id_B", "id_B"): "id_B",
            ("id_C", "id_C"): "id_C",
            ("f", "id_A"): "f",
            ("id_B", "f"): "f",
            ("g", "id_B"): "g",
            ("id_C", "g"): "g",
            ("h", "id_A"): "h",
            ("id_C", "h"): "h",
            ("g", "f"): "h",
        },
    )


def _composable_pair_with_a_spare_parallel_arrow() -> FiniteCategory:
    """Same as `_composable_pair`, plus a second, distinct A -> C morphism
    `h2`, with its own identity laws so it type-checks like any other
    morphism — it just isn't anyone's `g . f` composite."""
    base = _composable_pair()
    h2 = Morphism("h2", "A", "C")
    return FiniteCategory(
        objects=base.objects,
        morphisms={**base.morphisms, "h2": h2},
        composition={
            **base.composition,
            ("h2", "id_A"): "h2",
            ("id_C", "h2"): "h2",
        },
    )


def test_functor_rejects_a_composition_law_violation() -> None:
    """F maps f, g consistently but sends h to a *different*, endpoint-valid
    A -> C morphism than the target category's actual g'-after-f' composite,
    breaking axiom 3 specifically (not the endpoint check of axiom 2)."""
    source = _composable_pair()
    target = _composable_pair_with_a_spare_parallel_arrow()
    with pytest.raises(FunctorialityViolation, match=r"F\('g' \. 'f'\)"):
        Functor(
            source=source,
            target=target,
            object_map={"A": "A", "B": "B", "C": "C"},
            morphism_map={
                "id_A": "id_A",
                "id_B": "id_B",
                "id_C": "id_C",
                "f": "f",
                "g": "g",
                "h": "h2",  # wrong: target's g . f is "h", not "h2"
            },
        )


def test_functor_rejects_a_morphism_ending_at_the_wrong_object() -> None:
    source = _walking_arrow("")
    id_a, id_b = Morphism("id_A", "A", "A"), Morphism("id_B", "B", "B")
    id_c = Morphism("id_C", "C", "C")
    wrong = Morphism("wrong", "A", "C")  # starts at F(A)=A correctly, ends at C not B
    target = FiniteCategory(
        objects=frozenset({"A", "B", "C"}),
        morphisms={"id_A": id_a, "id_B": id_b, "id_C": id_c, "wrong": wrong},
        composition={
            ("id_A", "id_A"): "id_A",
            ("id_B", "id_B"): "id_B",
            ("id_C", "id_C"): "id_C",
            ("wrong", "id_A"): "wrong",
            ("id_C", "wrong"): "wrong",
        },
    )
    with pytest.raises(FunctorialityViolation, match="must end at"):
        Functor(
            source=source,
            target=target,
            object_map={"A": "A", "B": "B"},
            morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "wrong"},
        )


def test_functor_composition_is_itself_a_valid_functor() -> None:
    c = _walking_arrow("c_")
    d = _walking_arrow("d_")
    e = _walking_arrow("e_")

    f_to_d = Functor(
        source=c,
        target=d,
        object_map={"c_A": "d_A", "c_B": "d_B"},
        morphism_map={"id_c_A": "id_d_A", "id_c_B": "id_d_B", "c_f": "d_f"},
    )
    g_to_e = Functor(
        source=d,
        target=e,
        object_map={"d_A": "e_A", "d_B": "e_B"},
        morphism_map={"id_d_A": "id_e_A", "id_d_B": "id_e_B", "d_f": "e_f"},
    )
    composite = f_to_d.compose_with(g_to_e)
    assert composite.source is c
    assert composite.target is e
    assert composite.apply_object("c_A") == "e_A"
    assert composite.apply_morphism("c_f") == "e_f"


def test_compose_with_rejects_mismatched_middle_category() -> None:
    c = _walking_arrow("c_")
    d = _walking_arrow("d_")
    e = _walking_arrow("e_")
    identity_c = Functor(
        source=c,
        target=c,
        object_map={"c_A": "c_A", "c_B": "c_B"},
        morphism_map={"id_c_A": "id_c_A", "id_c_B": "id_c_B", "c_f": "c_f"},
    )
    unrelated = Functor(
        source=d,
        target=e,
        object_map={"d_A": "e_A", "d_B": "e_B"},
        morphism_map={"id_d_A": "id_e_A", "id_d_B": "id_e_B", "d_f": "e_f"},
    )
    with pytest.raises(ValueError, match="compose_with requires"):
        identity_c.compose_with(unrelated)
