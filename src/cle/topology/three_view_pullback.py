"""Three-View Pullback — CLE side of the Three-View Constraint (三視点拘束).

    P_recovery = Pullback(F_S: C_S -> D, F_O: C_O -> D, F_H: C_H -> D)

`P_recovery`'s objects are the maximal non-contradictory invariant
sub-context shared across Subject, Observer, and Human-Knowledge views.

The directive's own Python signature for this engine takes three
`FiniteCategory` values and no explicit functors or common target `D` --
so rather than inventing new `Functor` objects the signature has no room
for, this reuses the same convention `cle.topology.category_theory.Functor`
already relies on elsewhere: a morphism *name* shared across categories
denotes one arrow of the common target `D` that each view's (implicit)
functor maps onto. Under that convention, the pullback's defining
condition -- "F_S, F_O, F_H agree on this arrow" -- is exactly "a morphism
of this name is present, with identical endpoints, in more than one input
category" and "functor consistency" is exactly rejecting a name that
appears with *disagreeing* endpoints instead of silently treating the two
occurrences as unrelated.
"""

from __future__ import annotations

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import FiniteCategory, Morphism


def compute_common_invariant_subgraph(
    category_s: FiniteCategory,
    category_o: FiniteCategory,
    category_h: FiniteCategory,
) -> set[Morphism]:
    """The pullback morphism set: arrows every one of the three views agrees on.

    Raises `FunctorialityViolation` if a morphism name is shared across two
    or more of the three categories with disagreeing source/target -- a
    genuine functor inconsistency, not a coincidence to ignore.
    """
    occurrences: dict[str, list[Morphism]] = {}
    for category in (category_s, category_o, category_h):
        for name, morphism in category.morphisms.items():
            occurrences.setdefault(name, []).append(morphism)

    for name, morphisms in occurrences.items():
        first = morphisms[0]
        for other in morphisms[1:]:
            if other != first:
                raise FunctorialityViolation(
                    f"morphism {name!r} disagrees across views: "
                    f"{first!r} vs {other!r}"
                )

    names_s = set(category_s.morphisms)
    names_o = set(category_o.morphisms)
    names_h = set(category_h.morphisms)
    common_names = names_s & names_o & names_h
    return {category_s.morphisms[name] for name in common_names}


class ThreeViewPullbackEngine:
    """Stateless facade over `compute_common_invariant_subgraph`."""

    __slots__ = ()

    def compute_common_invariant_subgraph(
        self,
        category_s: FiniteCategory,
        category_o: FiniteCategory,
        category_h: FiniteCategory,
    ) -> set[Morphism]:
        return compute_common_invariant_subgraph(category_s, category_o, category_h)


__all__ = ["ThreeViewPullbackEngine", "compute_common_invariant_subgraph"]
