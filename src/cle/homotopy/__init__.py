"""Homotopy analysis.

Owns deciding whether two concepts are homotopic: continuously deformable
into one another, i.e. the same underlying knowledge reached by different
evidence paths. This is the equivalence relation `cle.quotient` collapses.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBConceptLike


@runtime_checkable
class HomotopyAnalyzer(Protocol):
    """`True` when two concepts are the same knowledge under continuous deformation."""

    def is_homotopic(self, a: HEKBConceptLike, b: HEKBConceptLike) -> bool: ...


__all__ = ["HomotopyAnalyzer"]
