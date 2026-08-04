"""Functor construction.

Owns building a structure-preserving mapping from one `Category` to another,
expressed as a `CategoryRelation` with `relation_kind="functor"`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cle.abi.outputs import Category, CategoryRelation
from cle.errors import FunctorialityViolation
from cle.identity import deterministic_id


@runtime_checkable
class FunctorConstructor(Protocol):
    """Two categories -> the functorial `CategoryRelation` between them."""

    def construct(self, source: Category, target: Category) -> CategoryRelation: ...


@dataclass(frozen=True, slots=True)
class CanonicalInclusionFunctorConstructor:
    """The canonical inclusion functor between two categories, when one exists.

    RFC-CLE001 §3.1 Phase 1 (Functorial Lift Engine): given only the two
    frozen `Category` values (a set of `concept_ids` each, per the existing
    ABI — no explicit object-to-object mapping is available), the only
    structure-preserving map derivable without fabricating evidence is the
    inclusion functor: `source` includes into `target` when every concept
    `source` references is also referenced by `target`. Functoriality then
    holds automatically — an inclusion never remaps an identity morphism,
    and never has two ways to compose the same pair of arrows — so no
    separate functoriality check is needed beyond the subset test itself.

    Raises `FunctorialityViolation` when `source.concept_ids` is not a
    subset of `target.concept_ids`: no canonical functor can be derived
    from concept-id sets alone in that case (RFC-CLE002 §5's
    `FUNCTORIALITY_VIOLATION`, see `docs/RFC_ALIGNMENT.md`).
    """

    def construct(self, source: Category, target: Category) -> CategoryRelation:
        missing = set(source.concept_ids) - set(target.concept_ids)
        if missing:
            raise FunctorialityViolation(
                f"category {source.id!r} does not include into {target.id!r}: "
                f"concept_ids {sorted(missing)} are missing from the target"
            )
        return CategoryRelation(
            id=deterministic_id("functor", source.id, target.id),
            source_category_id=source.id,
            target_category_id=target.id,
            relation_kind="functor",
            provenance=source.provenance + target.provenance,
        )


__all__ = ["CanonicalInclusionFunctorConstructor", "FunctorConstructor"]
