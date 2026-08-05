"""`NaturalTransformation` — naturality square (spec v2.0.0 §4)."""

from __future__ import annotations

import pytest

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Functor, Morphism
from cle.topology.natural_transformation import NaturalTransformation


def _walking_arrow(prefix: str) -> FiniteCategory:
    a, b = f"{prefix}A", f"{prefix}B"
    id_a, id_b = Morphism(f"id_{a}", a, a), Morphism(f"id_{b}", b, b)
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


def _two_object_target() -> FiniteCategory:
    """D: two objects P, Q, with an isomorphism-shaped pair of arrows."""
    id_p, id_q = Morphism("id_P", "P", "P"), Morphism("id_Q", "Q", "Q")
    up, down = Morphism("up", "P", "Q"), Morphism("down", "Q", "P")
    return FiniteCategory(
        objects=frozenset({"P", "Q"}),
        morphisms={"id_P": id_p, "id_Q": id_q, "up": up, "down": down},
        composition={
            ("id_P", "id_P"): "id_P",
            ("id_Q", "id_Q"): "id_Q",
            ("up", "id_P"): "up",
            ("id_Q", "up"): "up",
            ("down", "id_Q"): "down",
            ("id_P", "down"): "down",
            ("down", "up"): "id_P",
            ("up", "down"): "id_Q",
        },
    )


def test_identity_natural_transformation_holds() -> None:
    c = _walking_arrow("")
    d = _two_object_target()
    functor = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    identity_component = NaturalTransformation(
        source_functor=functor,
        target_functor=functor,
        components={"A": "id_P", "B": "id_Q"},
    )
    assert identity_component.component_at("A") == "id_P"


def _target_with_a_twist_and_a_parallel_arrow() -> FiniteCategory:
    """P, Q with `up: P->Q`, a second endomorphism `twist: P->P` (!= id_P),
    and a second, distinct `up2: P->Q` that `up . twist` deliberately
    equals — the parallel arrow a naturality-square violation needs, with
    both endpoints still valid."""
    p, q = "P", "Q"
    id_p, id_q = Morphism("id_P", p, p), Morphism("id_Q", q, q)
    up, up2 = Morphism("up", p, q), Morphism("up2", p, q)
    twist = Morphism("twist", p, p)
    return FiniteCategory(
        objects=frozenset({p, q}),
        morphisms={"id_P": id_p, "id_Q": id_q, "up": up, "up2": up2, "twist": twist},
        composition={
            ("id_P", "id_P"): "id_P",
            ("id_Q", "id_Q"): "id_Q",
            ("up", "id_P"): "up",
            ("id_Q", "up"): "up",
            ("id_P", "twist"): "twist",
            ("twist", "id_P"): "twist",
            ("up", "twist"): "up2",
        },
    )


def test_naturality_square_violation_is_rejected() -> None:
    c = _walking_arrow("")
    d = _target_with_a_twist_and_a_parallel_arrow()
    functor = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    with pytest.raises(FunctorialityViolation, match="naturality square fails"):
        NaturalTransformation(
            source_functor=functor,
            target_functor=functor,
            # eta_A = twist (a valid P->P component, just not id_P): the
            # square G(f).eta_A = up.twist = up2, but eta_B.F(f) = id_Q.up
            # = up, so up2 != up must be caught.
            components={"A": "twist", "B": "id_Q"},
        )


def test_rejects_functors_with_different_source_categories() -> None:
    c = _walking_arrow("")
    other = _walking_arrow("other_")
    d = _two_object_target()
    functor_c = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    functor_other = Functor(
        source=other,
        target=d,
        object_map={"other_A": "P", "other_B": "Q"},
        morphism_map={"id_other_A": "id_P", "id_other_B": "id_Q", "other_f": "up"},
    )
    with pytest.raises(ValueError, match="share one source category"):
        NaturalTransformation(
            source_functor=functor_c,
            target_functor=functor_other,
            components={"A": "id_P", "B": "id_Q"},
        )


def test_rejects_functors_with_different_target_categories() -> None:
    c = _walking_arrow("")
    d = _two_object_target()
    other_d = _walking_arrow("other_d_")
    functor_to_d = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    functor_to_other_d = Functor(
        source=c,
        target=other_d,
        object_map={"A": "other_d_A", "B": "other_d_B"},
        morphism_map={"id_A": "id_other_d_A", "id_B": "id_other_d_B", "f": "other_d_f"},
    )
    with pytest.raises(ValueError, match="share one target category"):
        NaturalTransformation(
            source_functor=functor_to_d,
            target_functor=functor_to_other_d,
            components={"A": "id_P", "B": "id_Q"},
        )


def test_rejects_a_missing_component() -> None:
    c = _walking_arrow("")
    d = _two_object_target()
    functor = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    with pytest.raises(FunctorialityViolation, match="no component"):
        NaturalTransformation(
            source_functor=functor,
            target_functor=functor,
            components={"A": "id_P"},  # B missing
        )


def test_rejects_a_component_with_the_wrong_endpoints() -> None:
    c = _walking_arrow("")
    d = _two_object_target()
    functor = Functor(
        source=c,
        target=d,
        object_map={"A": "P", "B": "Q"},
        morphism_map={"id_A": "id_P", "id_B": "id_Q", "f": "up"},
    )
    with pytest.raises(FunctorialityViolation, match="must be a morphism"):
        NaturalTransformation(
            source_functor=functor,
            target_functor=functor,
            components={"A": "up", "B": "id_Q"},  # eta_A goes P->Q, not P->P
        )
