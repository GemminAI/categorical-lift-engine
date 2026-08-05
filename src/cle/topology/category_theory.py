"""General categorical functor with composition — spec v2.0.0 §4.2.

    F: C -> D
    1. Object projection:      forall A in C, F(A) in D
    2. Morphism preservation:  forall f: A -> B in C, F(f): F(A) -> F(B) in D
    3. Composition law:        F(g . f) = F(g) . F(f)

`FiniteCategory` is a small, explicit finite category: objects, named
morphisms (each with a source/target object), and a composition table
supplied by the caller as a fact about the category (this class validates
it, it does not derive it). This is deliberately more structure than
`cle.abi.outputs.Category` (a bare set of `concept_ids`) carries — that type
and `cle.functor.CanonicalInclusionFunctorConstructor` remain the fast path
for the narrower inclusion-functor case; this module is the general
construction the spec's axioms actually describe.
"""

from __future__ import annotations

from dataclasses import dataclass

from cle.errors import FunctorialityViolation

Obj = str


@dataclass(frozen=True, slots=True)
class Morphism:
    name: str
    source: Obj
    target: Obj


@dataclass(frozen=True, slots=True)
class FiniteCategory:
    """Objects, named morphisms, and an explicit composition table.

    ``composition`` maps ``(g_name, f_name) -> h_name`` for ``g . f`` where
    ``f: A -> B`` and ``g: B -> C``. Identities must appear explicitly as
    morphisms, per the usual category-theory convention — this class does
    not synthesize them.
    """

    objects: frozenset[Obj]
    morphisms: dict[str, Morphism]
    composition: dict[tuple[str, str], str]

    def __post_init__(self) -> None:
        for morphism in self.morphisms.values():
            missing_endpoint = (
                morphism.source not in self.objects
                or morphism.target not in self.objects
            )
            if missing_endpoint:
                raise ValueError(
                    f"morphism {morphism.name!r} references an object "
                    "outside this category"
                )
        for (g_name, f_name), h_name in self.composition.items():
            g, f, h = (
                self.morphisms[g_name],
                self.morphisms[f_name],
                self.morphisms[h_name],
            )
            if f.target != g.source:
                raise ValueError(f"{g_name!r} . {f_name!r} is not composable")
            if h.source != f.source or h.target != g.target:
                raise ValueError(
                    f"composition {g_name!r} . {f_name!r} must equal {h_name!r}"
                )

    def compose(self, g_name: str, f_name: str) -> str:
        return self.composition[(g_name, f_name)]


@dataclass(frozen=True, slots=True)
class Functor:
    """F: C -> D, validated against all three functor axioms at construction."""

    source: FiniteCategory
    target: FiniteCategory
    object_map: dict[Obj, Obj]
    morphism_map: dict[str, str]

    def __post_init__(self) -> None:
        for obj in self.source.objects:
            if obj not in self.object_map:
                raise FunctorialityViolation(
                    f"object {obj!r} has no image under F"
                )
            if self.object_map[obj] not in self.target.objects:
                raise FunctorialityViolation(
                    f"F({obj!r}) = {self.object_map[obj]!r} is not an object "
                    "of the target category"
                )

        for name, morphism in self.source.morphisms.items():
            if name not in self.morphism_map:
                raise FunctorialityViolation(
                    f"morphism {name!r} has no image under F"
                )
            image_name = self.morphism_map[name]
            if image_name not in self.target.morphisms:
                raise FunctorialityViolation(
                    f"F({name!r}) = {image_name!r} is not a morphism of the "
                    "target category"
                )
            image = self.target.morphisms[image_name]
            if image.source != self.object_map[morphism.source]:
                raise FunctorialityViolation(
                    f"F({name!r}) must start at F({morphism.source!r})"
                )
            if image.target != self.object_map[morphism.target]:
                raise FunctorialityViolation(
                    f"F({name!r}) must end at F({morphism.target!r})"
                )

        for (g_name, f_name), h_name in self.source.composition.items():
            f_image = self.morphism_map[f_name]
            g_image = self.morphism_map[g_name]
            h_image = self.morphism_map[h_name]
            composed_image = self.target.compose(g_image, f_image)
            if composed_image != h_image:
                raise FunctorialityViolation(
                    f"F({g_name!r} . {f_name!r}) = {composed_image!r}, but "
                    f"F({g_name!r}) . F({f_name!r}) should equal "
                    f"F({h_name!r}) = {h_image!r}"
                )

    def apply_object(self, obj: Obj) -> Obj:
        return self.object_map[obj]

    def apply_morphism(self, name: str) -> str:
        return self.morphism_map[name]

    def compose_with(self, other: Functor) -> Functor:
        """G . F: C -> E, given F: C -> D (self) and G: D -> E (other).

        A composite of functors is itself a functor — a categorical theorem,
        not an assumption here: building the composite maps and constructing
        a new `Functor` from them re-runs all three axiom checks above
        against the composite, so the theorem is checked, not merely relied
        upon.
        """
        if self.target is not other.source:
            raise ValueError("compose_with requires self.target is other.source")
        composite_objects = {
            obj: other.apply_object(self.apply_object(obj))
            for obj in self.source.objects
        }
        composite_morphisms = {
            name: other.apply_morphism(self.apply_morphism(name))
            for name in self.source.morphisms
        }
        return Functor(
            source=self.source,
            target=other.target,
            object_map=composite_objects,
            morphism_map=composite_morphisms,
        )


__all__ = ["FiniteCategory", "Functor", "Morphism", "Obj"]
