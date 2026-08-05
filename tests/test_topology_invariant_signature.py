"""`InvariantSignature` (CLE v3 spec §4.1/§4.2)."""

from __future__ import annotations

import math

from cle.topology.invariant_signature import (
    InvariantSignature,
    compute_invariant_signature,
)

Vector = tuple[float, ...]

_TRIANGLE: tuple[Vector, ...] = ((0.0, 0.0), (1.0, 0.0), (0.5, math.sqrt(3) / 2))


def test_signature_of_a_filled_triangle_matches_its_betti_numbers() -> None:
    signature = compute_invariant_signature(_TRIANGLE, eps=1.1, max_dimension=2)
    assert (signature.betti_0, signature.betti_1, signature.betti_2) == (1, 0, 0)
    assert signature.euler_characteristic == 1


def test_equal_signatures_match() -> None:
    left = InvariantSignature.from_betti((1, 0, 0))
    right = InvariantSignature.from_betti((1, 0, 0))
    assert left.matches(right)


def test_unequal_signatures_do_not_match() -> None:
    left = InvariantSignature.from_betti((1, 0, 0))
    right = InvariantSignature.from_betti((2, 0, 0))
    assert not left.matches(right)


def test_from_betti_pads_missing_dimensions_with_zero() -> None:
    signature = InvariantSignature.from_betti((3,))
    assert signature.betti_0 == 3
    assert signature.betti_1 == 0
    assert signature.betti_2 == 0
    assert signature.euler_characteristic == 3


def test_euler_characteristic_formula() -> None:
    signature = InvariantSignature.from_betti((1, 2, 3))
    assert signature.euler_characteristic == 1 - 2 + 3
