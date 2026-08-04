"""RFC-CLE005 §2.2 Homotopy Path Equivalence, generalized via Hypothesis.

Phase 2's own tests already proved isometry invariance on hand-picked
shapes (a square, a triangle) and hand-picked transformations. This
generalizes the same claim to random point clouds and random
rotation/translation/reflection/reordering, closer to what a real fuzz
pass demands.

Boundary-flakiness is filtered out, not ignored: right at the `eps`
boundary, floating-point rotation/translation arithmetic can genuinely
move a pairwise distance from one side of `<=` to the other — that would
be testing float rounding, not Betti-number invariance, so any generated
point cloud whose pairwise distances land within `_MARGIN` of `_EPS` is
skipped via `assume()`.
"""

from __future__ import annotations

import math

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cle.geometry import euclidean_distance
from cle.homotopy import EpsilonGraphBettiAnalyzer

Point = tuple[float, float]

_analyzer = EpsilonGraphBettiAnalyzer()
_EPS = 1.0
_MARGIN = 0.05

_coordinate = st.floats(
    min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False, width=32
)


def _point_clouds(
    min_size: int = 1, max_size: int = 6
) -> st.SearchStrategy[list[Point]]:
    return st.lists(
        st.tuples(_coordinate, _coordinate), min_size=min_size, max_size=max_size
    )


def _safely_away_from_eps_boundary(points: list[Point]) -> bool:
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if abs(euclidean_distance(points[i], points[j]) - _EPS) <= _MARGIN:
                return False
    return True


def _rotate(points: list[Point], radians: float) -> tuple[Point, ...]:
    cos_t, sin_t = math.cos(radians), math.sin(radians)
    return tuple((x * cos_t - y * sin_t, x * sin_t + y * cos_t) for x, y in points)


@given(points=_point_clouds(), angle=st.floats(min_value=0.0, max_value=2 * math.pi))
@settings(max_examples=200)
def test_betti_numbers_invariant_under_random_rotation(
    points: list[Point], angle: float
) -> None:
    assume(_safely_away_from_eps_boundary(points))
    rotated = _rotate(points, angle)

    assert _analyzer.compute_betti_numbers(
        tuple(points), eps=_EPS
    ) == _analyzer.compute_betti_numbers(rotated, eps=_EPS)


@given(points=_point_clouds(), offset=st.tuples(_coordinate, _coordinate))
@settings(max_examples=200)
def test_betti_numbers_invariant_under_random_translation(
    points: list[Point], offset: Point
) -> None:
    assume(_safely_away_from_eps_boundary(points))
    translated = tuple((x + offset[0], y + offset[1]) for x, y in points)

    assert _analyzer.compute_betti_numbers(
        tuple(points), eps=_EPS
    ) == _analyzer.compute_betti_numbers(translated, eps=_EPS)


@given(points=_point_clouds())
@settings(max_examples=200)
def test_betti_numbers_invariant_under_reflection(points: list[Point]) -> None:
    assume(_safely_away_from_eps_boundary(points))
    reflected = tuple((-x, y) for x, y in points)

    assert _analyzer.compute_betti_numbers(
        tuple(points), eps=_EPS
    ) == _analyzer.compute_betti_numbers(reflected, eps=_EPS)


@given(points=_point_clouds(min_size=2))
@settings(max_examples=200)
def test_betti_numbers_invariant_under_point_reordering(points: list[Point]) -> None:
    assume(_safely_away_from_eps_boundary(points))
    reordered = tuple(reversed(points))

    assert _analyzer.compute_betti_numbers(
        tuple(points), eps=_EPS
    ) == _analyzer.compute_betti_numbers(reordered, eps=_EPS)
