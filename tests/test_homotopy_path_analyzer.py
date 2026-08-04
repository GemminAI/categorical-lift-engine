"""`EpsilonGraphBettiAnalyzer` — Homotopy Path Analyzer (RFC-CLE001 Phase 2).

Three groups of tests, matching the requested methodology:

1. Mathematical validation — hand-constructed point clouds whose Betti
   numbers are known by direct graph-theoretic reasoning, not guessed.
2. Invariance properties — *why* `b_0`/`b_1` are genuine topological
   invariants: they are computed from an eps-neighborhood graph built only
   from pairwise distances, so any transformation that preserves pairwise
   distances (translation, rotation, reflection) must preserve them, and
   the graph doesn't care what order the points arrive in either.
3. `paths_are_homotopic` — the Betti-equality proxy this analyzer implements.
"""

from __future__ import annotations

import math

import pytest

from cle.abi.inputs import StabilizedTrajectoryLike
from cle.errors import DimensionMismatch
from cle.homotopy import (
    EpsilonGraphBettiAnalyzer,
    HomotopyAnalyzer,
    HomotopyPathAnalyzer,
)
from conftest import FakeMeaningState, FakeStabilizedTrajectory

Vector = tuple[float, ...]

# A 4-point square, side length 1.0, diagonal sqrt(2) ~= 1.414.
_SQUARE = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
# Radius that connects sides (distance 1.0) but not diagonals (~1.414).
_SQUARE_EPS = 1.05

# An equilateral triangle, side length 1.0.
_TRIANGLE = ((0.0, 0.0), (1.0, 0.0), (0.5, math.sqrt(3) / 2))
_TRIANGLE_EPS = 1.1

# The square's first 3 points (an open chain, not closed into a ring) plus
# one far outlier: no loop, one isolated point, at `_SQUARE_EPS`.
_BROKEN_SQUARE = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (50.0, 50.0))


def _trajectory_from(
    points: tuple[Vector, ...], trajectory_id: str
) -> FakeStabilizedTrajectory:
    states = tuple(
        FakeMeaningState(
            frame_id="F", step_index=i, time_s=float(i), theta=p, basin_id=None
        )
        for i, p in enumerate(points)
    )
    return FakeStabilizedTrajectory(
        trajectory_id=trajectory_id,
        frame_id="F",
        basin_id=None,
        states=states,
        centroid=points[0],
        covariance=((1.0, 0.0), (0.0, 1.0)),
        dwell_steps=len(points),
        dwell_seconds=float(len(points)) * 0.1,
    )


def test_epsilon_graph_betti_analyzer_satisfies_the_protocol() -> None:
    assert isinstance(EpsilonGraphBettiAnalyzer(), HomotopyPathAnalyzer)


def test_betti_analyzer_does_not_falsely_satisfy_homotopy_analyzer() -> None:
    # Regression test for the architectural review finding: `HomotopyAnalyzer`
    # and `HomotopyPathAnalyzer` used to share the method name `is_homotopic`,
    # which made `EpsilonGraphBettiAnalyzer` structurally (and wrongly) satisfy
    # `isinstance(x, HomotopyAnalyzer)` too — `@runtime_checkable` only checks
    # method *names*, not signatures. Renaming to `paths_are_homotopic` closes
    # that false positive.
    assert not isinstance(EpsilonGraphBettiAnalyzer(), HomotopyAnalyzer)


# --- 1. Mathematical validation -------------------------------------------


def test_empty_point_cloud_has_zero_betti_numbers() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    assert analyzer.compute_betti_numbers((), eps=1.0) == (0, 0)


def test_single_point_is_one_component_with_no_cycle() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    assert analyzer.compute_betti_numbers(((0.0, 0.0),), eps=1.0) == (1, 0)


def test_two_distant_points_are_two_separate_components() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()
    points = ((0.0, 0.0), (100.0, 100.0))

    assert analyzer.compute_betti_numbers(points, eps=1.0) == (2, 0)


def test_four_points_in_a_ring_have_one_genuine_loop() -> None:
    # Square with only its 4 sides connected (not the diagonals): a clean
    # 4-cycle with no triangle to fill in, so b_1 = 1 is unambiguously
    # correct — V=4, E=4, C=1 -> b_1 = E - V + C = 1.
    analyzer = EpsilonGraphBettiAnalyzer()

    assert analyzer.compute_betti_numbers(_SQUARE, eps=_SQUARE_EPS) == (1, 1)


def test_three_mutually_close_points_report_a_spurious_cycle_by_design() -> None:
    # Three mutually-close points form a filled triangle geometrically (no
    # real hole), but this analyzer only builds the 1-skeleton graph, never
    # filling in the 2-simplex — so it reports b_1=1 here, an upper bound on
    # the true simplicial-complex answer of b_1=0. This is the documented
    # scope limitation (EpsilonGraphBettiAnalyzer's docstring), demonstrated
    # directly rather than left as an unproven claim.
    analyzer = EpsilonGraphBettiAnalyzer()

    assert analyzer.compute_betti_numbers(_TRIANGLE, eps=_TRIANGLE_EPS) == (1, 1)


def test_dimension_mismatch_between_points_is_rejected() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()

    with pytest.raises(DimensionMismatch):
        analyzer.compute_betti_numbers(((0.0, 0.0), (1.0, 1.0, 1.0)), eps=1.0)


# --- 2. Invariance properties ----------------------------------------------


def _translate(points: tuple[Vector, ...], offset: Vector) -> tuple[Vector, ...]:
    return tuple(
        tuple(p + o for p, o in zip(point, offset, strict=True)) for point in points
    )


def _rotate_2d(points: tuple[Vector, ...], radians: float) -> tuple[Vector, ...]:
    cos_t, sin_t = math.cos(radians), math.sin(radians)
    return tuple((x * cos_t - y * sin_t, x * sin_t + y * cos_t) for x, y in points)


def _reflect_x(points: tuple[Vector, ...]) -> tuple[Vector, ...]:
    return tuple((-x, y) for x, y in points)


def test_betti_numbers_are_invariant_under_translation() -> None:
    # The eps-graph is built purely from pairwise distances, and
    # ||(. + t) - (. + t)|| == ||. - .|| for any offset t — translating
    # every point cannot change which pairs are within eps of each other.
    analyzer = EpsilonGraphBettiAnalyzer()
    translated = _translate(_SQUARE, (37.5, -12.0))

    assert analyzer.compute_betti_numbers(
        translated, eps=_SQUARE_EPS
    ) == analyzer.compute_betti_numbers(_SQUARE, eps=_SQUARE_EPS)


def test_betti_numbers_are_invariant_under_rotation() -> None:
    # Rotation preserves pairwise Euclidean distance exactly, so the
    # eps-graph — and therefore its Betti numbers — cannot change either.
    analyzer = EpsilonGraphBettiAnalyzer()
    rotated = _rotate_2d(_SQUARE, math.pi / 5)

    assert analyzer.compute_betti_numbers(
        rotated, eps=_SQUARE_EPS
    ) == analyzer.compute_betti_numbers(_SQUARE, eps=_SQUARE_EPS)


def test_betti_numbers_are_invariant_under_reflection() -> None:
    # A reflection is also an isometry (distance-preserving), same argument
    # as rotation/translation above.
    analyzer = EpsilonGraphBettiAnalyzer()
    reflected = _reflect_x(_SQUARE)

    assert analyzer.compute_betti_numbers(
        reflected, eps=_SQUARE_EPS
    ) == analyzer.compute_betti_numbers(_SQUARE, eps=_SQUARE_EPS)


def test_betti_numbers_are_invariant_under_point_reordering() -> None:
    # The graph's vertex/edge/component counts depend only on the *set* of
    # pairwise distances, never on the order points are listed in.
    analyzer = EpsilonGraphBettiAnalyzer()
    reordered = tuple(reversed(_SQUARE))

    assert analyzer.compute_betti_numbers(
        reordered, eps=_SQUARE_EPS
    ) == analyzer.compute_betti_numbers(_SQUARE, eps=_SQUARE_EPS)


def test_betti_numbers_are_not_scale_invariant_without_rescaling_eps() -> None:
    # Documented boundary of the invariance above: scaling changes pairwise
    # distances, so without also rescaling `eps`, the graph — and Betti
    # numbers — can and do change. Not a bug: this analyzer never claimed
    # scale invariance, only isometry invariance.
    analyzer = EpsilonGraphBettiAnalyzer()
    scaled = tuple((10.0 * x, 10.0 * y) for x, y in _SQUARE)

    assert analyzer.compute_betti_numbers(scaled, eps=_SQUARE_EPS) == (4, 0)


# --- 3. paths_are_homotopic --------------------------------------------------


def test_paths_are_homotopic_true_for_matching_betti_signatures() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()
    trajectory_a: StabilizedTrajectoryLike = _trajectory_from(_SQUARE, "loop-a")
    trajectory_b: StabilizedTrajectoryLike = _trajectory_from(
        _rotate_2d(_SQUARE, math.pi / 3), "loop-b"
    )

    assert analyzer.paths_are_homotopic(
        trajectory_a, trajectory_b, tolerance=_SQUARE_EPS
    )


def test_paths_are_homotopic_is_reflexive() -> None:
    analyzer = EpsilonGraphBettiAnalyzer()
    trajectory = _trajectory_from(_SQUARE, "loop")

    assert analyzer.paths_are_homotopic(trajectory, trajectory, tolerance=_SQUARE_EPS)


def test_paths_are_homotopic_false_for_differing_betti_signatures() -> None:
    # The loop (b_1=1) vs. two distant points (b_0=2, b_1=0): definitely not
    # homotopy-equivalent, and this is provable, not a guess, because Betti
    # numbers are homotopy invariants — differing Betti numbers is a
    # sufficient condition for non-equivalence.
    analyzer = EpsilonGraphBettiAnalyzer()
    loop = _trajectory_from(_SQUARE, "loop")
    disconnected = _trajectory_from(((0.0, 0.0), (100.0, 100.0)), "disconnected")

    assert not analyzer.paths_are_homotopic(loop, disconnected, tolerance=_SQUARE_EPS)


def test_paths_are_homotopic_depends_on_the_shared_tolerance() -> None:
    # The same pair — a genuine loop vs. a chain-plus-outlier — flips
    # verdict as `tolerance` changes: at 1.05 the loop's ring (b_1=1) differs
    # from the broken shape's chain-plus-isolated-point (b_0=2, b_1=0), so
    # they're not homotopic; at 0.001 every distance in both shapes exceeds
    # the tolerance, so both degrade to 4 isolated points (b_0=4, b_1=0) and
    # become indistinguishable. Not a bug: this analyzer only ever claimed
    # isometry invariance, never scale invariance (see the scale test above).
    analyzer = EpsilonGraphBettiAnalyzer()
    loop = _trajectory_from(_SQUARE, "loop")
    broken = _trajectory_from(_BROKEN_SQUARE, "broken")

    assert not analyzer.paths_are_homotopic(loop, broken, tolerance=_SQUARE_EPS)
    assert analyzer.paths_are_homotopic(loop, broken, tolerance=0.001)
