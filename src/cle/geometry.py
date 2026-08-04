"""Minimal geometric primitives shared by more than one concrete implementation.

Not a math library — this holds only functions actually reused across
stages (currently: `cle.homotopy`, `cle.concept`). Anything used by exactly
one module stays private to that module, per this repository's "no
unnecessary abstraction" convention.
"""

from __future__ import annotations

import math

from cle.abi.inputs import Vector
from cle.errors import NonFiniteValue


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


def assert_finite(vector: Vector) -> None:
    """Raise `NonFiniteValue` if any component of `vector` is NaN or infinite.

    Added for RFC-CLE005 §4.1's NaN/Inf fault-injection requirement, after
    confirming empirically that neither `FunctorialConceptLift` nor
    `EpsilonGraphBettiAnalyzer` rejected a NaN/Inf coordinate before this
    existed — both silently propagated it instead of failing loudly. Call
    this at the point raw, externally-supplied coordinates first enter a
    computation, not on every intermediate value derived from already
    validated ones.
    """
    if any(not math.isfinite(component) for component in vector):
        raise NonFiniteValue(f"vector contains a NaN or infinite component: {vector!r}")


__all__ = ["assert_finite", "euclidean_distance"]
