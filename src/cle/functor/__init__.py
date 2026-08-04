"""Functor construction.

Owns building a structure-preserving mapping from one `Category` to another,
expressed as a `CategoryRelation` with `relation_kind="functor"`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import Category, CategoryRelation


@runtime_checkable
class FunctorConstructor(Protocol):
    """Two categories -> the functorial `CategoryRelation` between them."""

    def construct(self, source: Category, target: Category) -> CategoryRelation: ...


__all__ = ["FunctorConstructor"]
