"""Category construction.

Owns grouping knowledge artifacts into categorical structures. Not every
lift produces a category — most produce a bare `Concept`/`ConceptDelta`
with no categorical grouping yet — so `construct` may decline.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBContextLike
from cle.abi.outputs import Category, Concept, ConceptDelta


@runtime_checkable
class CategoryConstructor(Protocol):
    """A discovered/evolved artifact -> a `Category`, or `None` if none applies."""

    def construct(
        self,
        artifact: Concept | ConceptDelta,
        *,
        hekb_context: HEKBContextLike | None,
    ) -> Category | None: ...


__all__ = ["CategoryConstructor"]
