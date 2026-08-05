"""Categorical pushout — CLE v3 spec §3.4, Stage 4 `categorical_pushout`.

    Q_synthesis = Pushout(G_S: P -> C_S, G_O: P -> C_O)

The gluing maps G_S, G_O are the inclusions of the common substructure P
into C_S and C_O respectively — exactly the situation
`cle.topology.three_view_pullback.compute_common_invariant_subgraph`
establishes: P's morphisms are literally common members (by value) of both
input categories. Under inclusion gluing, the pushout is the union of
objects and morphisms, with members shared by both categories identified
automatically by frozen-dataclass value equality; a name present in both
categories with *disagreeing* value is a genuine gluing conflict, rejected
rather than silently resolved by picking one side.
"""

from __future__ import annotations

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Morphism


def categorical_pushout(
    category_s: FiniteCategory, category_o: FiniteCategory
) -> FiniteCategory:
    """Q_synthesis: the union of `category_s` and `category_o`, glued along
    whatever they already share.
    """
    objects = category_s.objects | category_o.objects

    morphisms: dict[str, Morphism] = dict(category_s.morphisms)
    for name, morphism in category_o.morphisms.items():
        if name in morphisms and morphisms[name] != morphism:
            raise FunctorialityViolation(
                f"pushout gluing conflict at morphism {name!r}: "
                f"{morphisms[name]!r} vs {morphism!r}"
            )
        morphisms[name] = morphism

    composition: dict[tuple[str, str], str] = dict(category_s.composition)
    for key, value in category_o.composition.items():
        if key in composition and composition[key] != value:
            raise FunctorialityViolation(
                f"pushout gluing conflict at composition {key!r}: "
                f"{composition[key]!r} vs {value!r}"
            )
        composition[key] = value

    return FiniteCategory(objects=objects, morphisms=morphisms, composition=composition)


__all__ = ["categorical_pushout"]
