"""Cognitive compression ratio — spec v2.0.0 §4.3.

    R_compress = Size(Raw Context) / Size(Lifted Morphism Set)   target >= 10:1

"Size" is not defined by the specification beyond the ratio itself. This
measures serialized byte length (``len(repr(...).encode("utf-8"))``) on both
sides of the ratio — the same unit for numerator and denominator, which is
what makes the ratio meaningful — not a claim that byte length is the only
valid interpretation of "size".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CompressionResult:
    raw_size: int
    lifted_size: int

    @property
    def ratio(self) -> float:
        if self.lifted_size == 0:
            return float("inf") if self.raw_size > 0 else 0.0
        return self.raw_size / self.lifted_size

    @property
    def meets_target(self) -> bool:
        """R_compress >= 10:1, per spec §4.3."""
        return self.ratio >= 10.0


def measure_compression(
    raw_context: Any, lifted_morphism_set: Any
) -> CompressionResult:
    raw_size = len(repr(raw_context).encode("utf-8"))
    lifted_size = len(repr(lifted_morphism_set).encode("utf-8"))
    return CompressionResult(raw_size=raw_size, lifted_size=lifted_size)


__all__ = ["CompressionResult", "measure_compression"]
