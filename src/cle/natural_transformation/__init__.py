"""Natural transformation analysis.

Owns analyzing a mapping between two functors — two `CategoryRelation`
values sharing a source and target category — and, when one exists,
expressing it as a higher-order `CategoryRelation`
(`relation_kind="natural_transformation"`).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import CategoryRelation


@runtime_checkable
class NaturalTransformationAnalyzer(Protocol):
    """Two functorial `CategoryRelation`s -> the transformation between them, if any."""

    def analyze(
        self, source: CategoryRelation, target: CategoryRelation
    ) -> CategoryRelation | None: ...


__all__ = ["NaturalTransformationAnalyzer"]
