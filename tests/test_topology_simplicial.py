"""`VietorisRipsComplex` / boundary operators / Betti numbers (spec v2.0.0 §4.1)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from cle.errors import DimensionMismatch, NonFiniteValue
from cle.topology.simplicial import VietorisRipsComplex, betti_numbers, boundary_matrix

Vector = tuple[float, ...]

# Three mutually close points: EpsilonGraphBettiAnalyzer counts a spurious
# cycle here (b_1 = 1, its documented upper-bound caveat). The real
# simplicial complex fills the triangle with a 2-simplex, so b_1 = 0.
_TRIANGLE: tuple[Vector, ...] = ((0.0, 0.0), (1.0, 0.0), (0.5, math.sqrt(3) / 2))
_TRIANGLE_EPS = 1.1

# Octahedron vertices: adjacent (non-antipodal) pairs at distance sqrt(2),
# antipodal pairs at distance 2. At an eps between them, this triangulates a
# hollow 2-sphere: b_0=1 (connected), b_1=0 (no unfilled cycles, genus 0),
# b_2=1 (one enclosed 2-dimensional void).
_OCTAHEDRON: tuple[Vector, ...] = (
    (1.0, 0.0, 0.0),
    (-1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, -1.0),
)
_OCTAHEDRON_EPS = 1.5


def test_empty_point_cloud_has_only_a_trivial_zero_simplex_level() -> None:
    complex_ = VietorisRipsComplex((), eps=1.0, max_dimension=2)
    assert complex_.simplices(0) == ()
    assert betti_numbers(complex_, max_dimension=2) == (0, 0, 0)


def test_two_isolated_points_form_two_components_and_no_cycles() -> None:
    complex_ = VietorisRipsComplex(((0.0, 0.0), (10.0, 10.0)), eps=1.0, max_dimension=1)
    assert betti_numbers(complex_, max_dimension=1) == (2, 0)


def test_a_single_edge_is_one_component_and_no_cycle() -> None:
    complex_ = VietorisRipsComplex(((0.0, 0.0), (0.5, 0.0)), eps=1.0, max_dimension=1)
    assert complex_.simplices(1) == ((0, 1),)
    assert betti_numbers(complex_, max_dimension=1) == (1, 0)


def test_filled_triangle_has_no_first_betti_number_unlike_graph_approximation() -> None:
    complex_ = VietorisRipsComplex(_TRIANGLE, eps=_TRIANGLE_EPS, max_dimension=2)
    assert complex_.simplices(2) == ((0, 1, 2),)
    assert betti_numbers(complex_, max_dimension=2) == (1, 0, 0)


def test_octahedron_triangulates_a_hollow_sphere_with_beta_2_equal_one() -> None:
    complex_ = VietorisRipsComplex(_OCTAHEDRON, eps=_OCTAHEDRON_EPS, max_dimension=3)
    # No antipodal pair is connected, so no tetrahedron (3-simplex) can form.
    assert complex_.simplices(3) == ()
    assert betti_numbers(complex_, max_dimension=2) == (1, 0, 1)


def test_boundary_operator_composition_vanishes_on_the_filled_triangle() -> None:
    """The fundamental theorem d_k . d_{k+1} = 0, checked numerically."""
    complex_ = VietorisRipsComplex(_TRIANGLE, eps=_TRIANGLE_EPS, max_dimension=2)
    d1 = boundary_matrix(complex_, 1)
    d2 = boundary_matrix(complex_, 2)
    assert np.allclose(d1 @ d2, 0.0)


def test_boundary_operator_composition_vanishes_on_the_octahedron() -> None:
    complex_ = VietorisRipsComplex(_OCTAHEDRON, eps=_OCTAHEDRON_EPS, max_dimension=3)
    d1 = boundary_matrix(complex_, 1)
    d2 = boundary_matrix(complex_, 2)
    assert np.allclose(d1 @ d2, 0.0)


def test_boundary_matrix_rejects_dimension_zero() -> None:
    complex_ = VietorisRipsComplex(_TRIANGLE, eps=_TRIANGLE_EPS, max_dimension=2)
    with pytest.raises(ValueError, match="dimension"):
        boundary_matrix(complex_, 0)


def test_rejects_mismatched_dimensions() -> None:
    with pytest.raises(DimensionMismatch):
        VietorisRipsComplex(((0.0, 0.0), (1.0, 0.0, 0.0)), eps=1.0, max_dimension=1)


def test_rejects_negative_max_dimension() -> None:
    with pytest.raises(ValueError, match="max_dimension"):
        VietorisRipsComplex(_TRIANGLE, eps=1.0, max_dimension=-1)


def test_rejects_non_finite_coordinates() -> None:
    with pytest.raises(NonFiniteValue):
        VietorisRipsComplex(((0.0, float("nan")),), eps=1.0, max_dimension=1)


def test_from_adjacency_rejects_negative_max_dimension() -> None:
    with pytest.raises(ValueError, match="max_dimension"):
        VietorisRipsComplex.from_adjacency(2, ((0, 1),), max_dimension=-1)


def test_max_dimension_reached_is_bounded_by_construction() -> None:
    complex_ = VietorisRipsComplex(((0.0, 0.0),), eps=1.0, max_dimension=5)
    assert complex_.max_dimension_reached == 0
