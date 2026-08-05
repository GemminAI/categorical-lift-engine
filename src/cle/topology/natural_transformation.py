"""Natural transformation between two functors sharing source and target.

A natural transformation is category theory's standard, single, unambiguous
construction — unlike terms such as "knowledge density" or the spec's
"Gaussian-Markov Kernel" bandwidth (which need a caller-supplied parameter),
naturality has exactly one textbook definition, so it is implemented here in
full rather than reported as underspecified.

Given `F, G: C -> D`, a natural transformation `eta` assigns to every object
`A` of `C` a morphism `eta_A: F(A) -> G(A)` of `D`, such that for every
morphism `f: A -> B` in `C` the naturality square commutes:

    G(f) . eta_A = eta_B . F(f)

Composition on the `D` side is read off `target.compose`, exactly as
`cle.topology.category_theory.Functor` reads it for the functor axioms.
"""

from __future__ import annotations

from dataclasses import dataclass

from cle.errors import FunctorialityViolation
from cle.topology.category_theory import Functor, Obj


@dataclass(frozen=True, slots=True)
class NaturalTransformation:
    """eta: F => G, validated against the naturality square at construction."""

    source_functor: Functor
    target_functor: Functor
    components: dict[Obj, str]

    def __post_init__(self) -> None:
        if self.source_functor.source is not self.target_functor.source:
            raise ValueError("both functors must share one source category")
        if self.source_functor.target is not self.target_functor.target:
            raise ValueError("both functors must share one target category")

        category_c = self.source_functor.source
        category_d = self.source_functor.target

        for obj in category_c.objects:
            if obj not in self.components:
                raise FunctorialityViolation(
                    f"natural transformation has no component at object {obj!r}"
                )
            component = category_d.morphisms[self.components[obj]]
            expected_source = self.source_functor.apply_object(obj)
            expected_target = self.target_functor.apply_object(obj)
            endpoints_match = (
                component.source == expected_source
                and component.target == expected_target
            )
            if not endpoints_match:
                raise FunctorialityViolation(
                    f"component at {obj!r} must be a morphism "
                    f"F({obj!r}) -> G({obj!r}) in the target category"
                )

        for name, morphism in category_c.morphisms.items():
            eta_a = self.components[morphism.source]
            eta_b = self.components[morphism.target]
            f_image = self.source_functor.apply_morphism(name)
            g_image = self.target_functor.apply_morphism(name)
            left = category_d.compose(g_image, eta_a)
            right = category_d.compose(eta_b, f_image)
            if left != right:
                raise FunctorialityViolation(
                    f"naturality square fails at {name!r}: "
                    f"G(f).eta_A = {left!r} but eta_B.F(f) = {right!r}"
                )

    def component_at(self, obj: Obj) -> str:
        return self.components[obj]


__all__ = ["NaturalTransformation"]
