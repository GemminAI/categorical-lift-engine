"""cle.topology.persistence -- persistence diagrams, delay embedding, and
the bottleneck-distance operational definition of "homotopic"."""

from __future__ import annotations

import math
import sys

import numpy as np
import pytest

from cle.topology.persistence import (
    PersistenceDiagram,
    PersistenceHomotopyAnalyzer,
    TopologyExtraNotInstalled,
    bottleneck_distance,
    compute_persistence_diagram,
    delay_embed,
)
from conftest import FakeMeaningState, FakeStabilizedTrajectory

Vector = tuple[float, ...]


def _circle(n: int = 40, *, seed: int = 42, noise: float = 0.02) -> np.ndarray:
    rng = np.random.default_rng(seed)
    theta = np.linspace(0, 2 * math.pi, n, endpoint=False)
    points = np.stack([np.cos(theta), np.sin(theta)], axis=1)
    return points + rng.normal(scale=noise, size=points.shape)


def _two_blobs(n_each: int = 20, *, gap: float = 10.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    blob_a = rng.normal(loc=(0.0, 0.0), scale=0.05, size=(n_each, 2))
    blob_b = rng.normal(loc=(gap, 0.0), scale=0.05, size=(n_each, 2))
    return np.concatenate([blob_a, blob_b])


def _trajectory_from(
    points: np.ndarray, trajectory_id: str
) -> FakeStabilizedTrajectory:
    states = tuple(
        FakeMeaningState(
            frame_id="F", step_index=i, time_s=float(i), theta=tuple(p), basin_id=None
        )
        for i, p in enumerate(points)
    )
    return FakeStabilizedTrajectory(
        trajectory_id=trajectory_id,
        frame_id="F",
        basin_id=None,
        states=states,
        centroid=tuple(points[0]),
        covariance=((1.0, 0.0), (0.0, 1.0)),
        dwell_steps=len(points),
        dwell_seconds=float(len(points)) * 0.1,
    )


# --- compute_persistence_diagram: calibrated, answer-known inputs ----------


def test_circle_has_exactly_one_long_lived_h1_bar() -> None:
    diagram = compute_persistence_diagram(_circle(), max_dimension=1)
    h1 = diagram.diagrams[1]

    assert h1.shape[0] == 1
    lifetime = h1[0, 1] - h1[0, 0]
    assert lifetime > 1.0  # the ring's hole: a long-lived loop, not noise


def test_circle_has_exactly_one_infinite_h0_bar() -> None:
    diagram = compute_persistence_diagram(_circle(), max_dimension=1)
    h0 = diagram.diagrams[0]

    assert np.isinf(h0[:, 1]).sum() == 1


def test_two_distant_blobs_have_two_long_h0_bars() -> None:
    # One point cloud, two well-separated clusters: exactly one H0 bar is
    # infinite (ripser's convention — the final all-encompassing component)
    # and exactly one more finite H0 bar is long (the inter-blob merge
    # distance, ~= gap), both far longer than every within-blob bar
    # (~= 0.05-scale noise).
    diagram = compute_persistence_diagram(_two_blobs(gap=10.0), max_dimension=1)
    h0 = diagram.diagrams[0]
    finite = h0[np.isfinite(h0[:, 1])]
    lifetimes = np.sort(finite[:, 1] - finite[:, 0])

    assert np.isinf(h0[:, 1]).sum() == 1
    assert lifetimes[-1] > 5.0  # the merge-the-two-blobs bar
    assert lifetimes[-2] < 1.0  # every other bar is within-blob noise scale


def test_single_point_has_no_h1_features() -> None:
    diagram = compute_persistence_diagram(np.zeros((1, 2)), max_dimension=1)

    assert diagram.diagrams[1].shape[0] == 0


# --- PersistenceDiagram summary methods -------------------------------------


def test_betti_numbers_at_eps_reads_the_circle_correctly() -> None:
    diagram = compute_persistence_diagram(_circle(), max_dimension=1)
    # At a scale inside the H1 bar's lifetime, exactly one loop and one
    # component should be alive.
    h1 = diagram.diagrams[1]
    mid_scale = (h1[0, 0] + h1[0, 1]) / 2

    assert diagram.betti_numbers(mid_scale) == (1, 1)


def test_betti_numbers_empty_diagram_is_empty_tuple() -> None:
    diagram = PersistenceDiagram(diagrams={})

    assert diagram.betti_numbers(eps=1.0) == ()


def test_betti_numbers_zero_for_a_dimension_with_no_pairs() -> None:
    # dimension 1 present but with zero pairs (e.g. a single point's H1):
    # betti_numbers must report 0 there, not skip or error.
    diagram = PersistenceDiagram(
        diagrams={0: np.array([[0.0, np.inf]]), 1: np.zeros((0, 2))}
    )

    assert diagram.betti_numbers(eps=1.0) == (1, 0)


def test_total_persistence_excludes_infinite_bars() -> None:
    diagram = PersistenceDiagram(diagrams={0: np.array([[0.0, 1.0], [0.0, np.inf]])})

    assert diagram.total_persistence(0) == pytest.approx(1.0)


def test_max_persistence_is_zero_when_no_finite_pairs() -> None:
    diagram = PersistenceDiagram(diagrams={0: np.array([[0.0, np.inf]])})

    assert diagram.max_persistence(0) == 0.0


def test_max_persistence_is_zero_for_absent_dimension() -> None:
    diagram = PersistenceDiagram(diagrams={0: np.array([[0.0, 1.0]])})

    assert diagram.max_persistence(5) == 0.0


def test_max_persistence_picks_the_longest_finite_bar() -> None:
    diagram = PersistenceDiagram(diagrams={1: np.array([[0.0, 0.5], [0.1, 2.1]])})

    assert diagram.max_persistence(1) == pytest.approx(2.0)


# --- bottleneck_distance -----------------------------------------------------


def test_bottleneck_distance_is_zero_for_identical_diagrams() -> None:
    diagram = compute_persistence_diagram(_circle(), max_dimension=1)

    assert bottleneck_distance(diagram, diagram, dimension=1) == pytest.approx(0.0)


def test_bottleneck_distance_treats_absent_dimension_as_empty() -> None:
    diagram = PersistenceDiagram(diagrams={0: np.array([[0.0, 1.0]])})

    # dimension 1 absent from this diagram -> compared against an empty
    # diagram, not an error.
    distance = bottleneck_distance(diagram, diagram, dimension=1)
    assert distance == pytest.approx(0.0)


# --- delay_embed -------------------------------------------------------------


def test_delay_embed_output_shape() -> None:
    x = np.arange(10 * 3, dtype=np.float64).reshape(10, 3)
    embedded = delay_embed(x, m=4, tau=2)

    assert embedded.shape == (10 - (4 - 1) * 2, 4 * 3)


def test_delay_embed_rows_concatenate_the_right_delayed_copies() -> None:
    x = np.arange(6).reshape(6, 1).astype(np.float64)
    embedded = delay_embed(x, m=2, tau=2)

    # row i = concat(x[i], x[i+2]) for i in 0..3
    assert embedded.tolist() == [[0.0, 2.0], [1.0, 3.0], [2.0, 4.0], [3.0, 5.0]]


def test_delay_embed_rejects_m_below_one() -> None:
    with pytest.raises(ValueError, match="m must be"):
        delay_embed(np.zeros((5, 2)), m=0, tau=1)


def test_delay_embed_rejects_tau_below_one() -> None:
    with pytest.raises(ValueError, match="tau must be"):
        delay_embed(np.zeros((5, 2)), m=2, tau=0)


def test_delay_embed_rejects_non_2d_input() -> None:
    with pytest.raises(ValueError, match="must be a"):
        delay_embed(np.zeros(5), m=2, tau=1)


def test_delay_embed_rejects_too_few_rows_for_the_requested_embedding() -> None:
    with pytest.raises(ValueError, match="not enough rows"):
        delay_embed(np.zeros((3, 2)), m=5, tau=2)


# --- PersistenceHomotopyAnalyzer --------------------------------------------


def test_persistence_homotopy_analyzer_compute_betti_numbers() -> None:
    analyzer = PersistenceHomotopyAnalyzer()
    coordinates: tuple[Vector, ...] = tuple(tuple(p) for p in _circle())
    h1 = compute_persistence_diagram(_circle(), max_dimension=1).diagrams[1]
    mid_scale = float((h1[0, 0] + h1[0, 1]) / 2)

    assert analyzer.compute_betti_numbers(coordinates, eps=mid_scale) == (1, 1)


def test_persistence_homotopy_true_for_identical_shapes() -> None:
    analyzer = PersistenceHomotopyAnalyzer()
    circle_points = _circle()
    trajectory_a = _trajectory_from(circle_points, "circle-a")
    trajectory_b = _trajectory_from(circle_points, "circle-b")

    assert analyzer.paths_are_homotopic(trajectory_a, trajectory_b, tolerance=0.3)


def test_persistence_homotopy_false_for_different_shapes() -> None:
    analyzer = PersistenceHomotopyAnalyzer()
    circle_trajectory = _trajectory_from(_circle(), "circle")
    blobs_trajectory = _trajectory_from(_two_blobs(), "blobs")

    assert not analyzer.paths_are_homotopic(
        circle_trajectory, blobs_trajectory, tolerance=0.3
    )


# --- TopologyExtraNotInstalled -----------------------------------------------


def test_compute_persistence_diagram_raises_actionable_error_without_ripser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "ripser", None)

    with pytest.raises(TopologyExtraNotInstalled, match="topology"):
        compute_persistence_diagram(np.zeros((3, 2)))


def test_bottleneck_distance_raises_actionable_error_without_persim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "persim", None)
    diagram = PersistenceDiagram(diagrams={0: np.array([[0.0, 1.0]])})

    with pytest.raises(TopologyExtraNotInstalled, match="topology"):
        bottleneck_distance(diagram, diagram, dimension=0)
