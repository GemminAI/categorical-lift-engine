"""Minimal geometric primitives shared by more than one concrete implementation.

Not a math library — this holds only functions actually reused across
stages (currently: `cle.homotopy`). Anything used by exactly one module
stays private to that module, per this repository's "no unnecessary
abstraction" convention. Phase 1's `cle.concept` keeps its own private
Euclidean-distance helper rather than being refactored to use this one, so
each phase's already-reviewed code stays untouched (see
`docs/RFC_ALIGNMENT.md`).
"""

from __future__ import annotations

import math

from cle.abi.inputs import Vector


def euclidean_distance(a: Vector, b: Vector) -> float:
    """The Euclidean distance between two vectors of equal dimension.

    Callers validate shape *before* calling this — `_graph_betti_numbers`
    in `cle.homotopy` already checks every coordinate shares one dimension
    up front, so this function never sees a mismatch to reject in practice.
    It stays a plain, unvalidated arithmetic primitive rather than
    duplicating a check every caller has already made: `zip(..., strict=True)`
    raises `ValueError` on a length mismatch that reaches here regardless.
    """
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


__all__ = ["euclidean_distance"]
