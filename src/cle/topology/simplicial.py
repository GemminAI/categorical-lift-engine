"""Vietoris-Rips simplicial complex, boundary operators, Betti numbers.

SensOS Core Value & Architectural Specification v2.0.0 §4.1:

    VR_eps(G)   Vietoris-Rips complex of a point cloud at scale eps
    beta_k = dim(H_k) = dim(ker(d_k) / im(d_{k+1}))
    d_k . d_{k+1} = 0   (boundary operator)

Unlike `cle.homotopy.EpsilonGraphBettiAnalyzer` (a deliberately scoped,
graph-only b_0/b_1 approximation — see that module's docstring), this module
builds the full simplicial complex — vertices, edges, triangles, tetrahedra,
... up to `max_dimension` — as the clique complex of the eps-neighbourhood
graph, and computes Betti numbers via the boundary operators' matrix
rank/nullity, exactly as the spec's equation states. It is new machinery,
kept alongside (not replacing) the existing graph analyzer, which remains
the cheaper approximation for callers who only need b_0/b_1 at graph cost.

Complexity is combinatorial in the eps-graph's clique count, appropriate for
the trajectory-scale point clouds this analyzes (the same scale
`EpsilonGraphBettiAnalyzer` targets), not for large general point clouds.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from cle.abi.inputs import Vector
from cle.errors import DimensionMismatch
from cle.geometry import assert_finite, euclidean_distance

Simplex = tuple[int, ...]


def _clique_complex(
    count: int, adjacency: list[set[int]], *, max_dimension: int
) -> dict[int, tuple[Simplex, ...]]:
    """The clique complex of an arbitrary graph, shared by every caller that
    builds a `VietorisRipsComplex` — whether the adjacency comes from a
    Euclidean eps-threshold (the point-cloud case) or from a category's own
    morphism graph (CLE v3 Stage 5, which has no coordinates to threshold).

    A k-simplex is a (k+1)-clique. Cliques are enumerated by extending each
    (k-1)-simplex with a common neighbour greater than its own last vertex,
    so every clique is emitted exactly once.
    """
    simplices: dict[int, tuple[Simplex, ...]] = {0: tuple((i,) for i in range(count))}
    previous_level: tuple[Simplex, ...] = simplices[0]
    for dimension in range(1, max_dimension + 1):
        next_level: list[Simplex] = []
        for simplex in previous_level:
            common: set[int] | None = None
            for vertex in simplex:
                neighbours = adjacency[vertex]
                common = neighbours if common is None else common & neighbours
            if not common:
                continue
            for candidate in sorted(v for v in common if v > simplex[-1]):
                next_level.append((*simplex, candidate))
        if not next_level:
            break
        simplices[dimension] = tuple(next_level)
        previous_level = simplices[dimension]
    return simplices


class VietorisRipsComplex:
    """The clique complex of the eps-neighbourhood graph over a point cloud.

    A k-simplex is a (k+1)-clique of the graph connecting any two points at
    Euclidean distance <= eps — the standard Vietoris-Rips construction, not
    an approximation of it.
    """

    __slots__ = ("_simplices_by_dimension",)

    def __init__(
        self, coordinates: tuple[Vector, ...], eps: float, *, max_dimension: int
    ) -> None:
        if max_dimension < 0:
            raise ValueError("max_dimension must be non-negative")
        count = len(coordinates)
        if count:
            dimension = len(coordinates[0])
            if any(len(point) != dimension for point in coordinates):
                raise DimensionMismatch(
                    "all coordinates must share the same dimension"
                )
            for point in coordinates:
                assert_finite(point)

        adjacency: list[set[int]] = [set() for _ in range(count)]
        for i in range(count):
            for j in range(i + 1, count):
                if euclidean_distance(coordinates[i], coordinates[j]) <= eps:
                    adjacency[i].add(j)
                    adjacency[j].add(i)

        self._simplices_by_dimension = _clique_complex(
            count, adjacency, max_dimension=max_dimension
        )

    @classmethod
    def from_adjacency(
        cls, count: int, edges: tuple[tuple[int, int], ...], *, max_dimension: int
    ) -> VietorisRipsComplex:
        """Build the clique complex directly from a graph, bypassing distance.

        For inputs (e.g. a category's morphism graph) that have no natural
        coordinates or metric to threshold — the graph *is* the input.
        """
        if max_dimension < 0:
            raise ValueError("max_dimension must be non-negative")
        adjacency: list[set[int]] = [set() for _ in range(count)]
        for left, right in edges:
            adjacency[left].add(right)
            adjacency[right].add(left)
        instance = cls.__new__(cls)
        instance._simplices_by_dimension = _clique_complex(
            count, adjacency, max_dimension=max_dimension
        )
        return instance

    def simplices(self, dimension: int) -> tuple[Simplex, ...]:
        return self._simplices_by_dimension.get(dimension, ())

    @property
    def max_dimension_reached(self) -> int:
        return max(self._simplices_by_dimension, default=0)


def boundary_matrix(
    complex_: VietorisRipsComplex, dimension: int
) -> NDArray[np.float64]:
    """The boundary operator d_k: C_k -> C_{k-1}, as a signed incidence matrix.

        d_k[v0,...,vk] = sum_i (-1)^i [v0,...,v_i-hat,...,vk]

    the standard alternating-sum simplicial boundary, over vertex-index-
    sorted simplices, which fixes one orientation convention consistently
    across the whole complex.
    """
    if dimension < 1:
        raise ValueError("dimension must be >= 1 (d_0 is not defined)")
    domain = complex_.simplices(dimension)
    codomain = complex_.simplices(dimension - 1)
    codomain_index = {simplex: index for index, simplex in enumerate(codomain)}
    matrix = np.zeros((len(codomain), len(domain)), dtype=np.float64)
    for column, simplex in enumerate(domain):
        for i in range(len(simplex)):
            face = simplex[:i] + simplex[i + 1 :]
            row = codomain_index[face]
            matrix[row, column] += (-1.0) ** i
    return matrix


def betti_numbers(
    complex_: VietorisRipsComplex, *, max_dimension: int
) -> tuple[int, ...]:
    """beta_k = dim(ker d_k) - dim(im d_{k+1}), for k = 0..max_dimension.

    d_0 is the zero map C_0 -> 0 by convention, so ker(d_0) = C_0: every
    vertex is a 0-cycle.
    """
    betti: list[int] = []
    for k in range(max_dimension + 1):
        count_k = len(complex_.simplices(k))
        if count_k == 0:
            betti.append(0)
            continue
        rank_k = (
            int(np.linalg.matrix_rank(boundary_matrix(complex_, k))) if k >= 1 else 0
        )
        kernel_k = count_k - rank_k
        next_simplices = complex_.simplices(k + 1)
        rank_next = (
            int(np.linalg.matrix_rank(boundary_matrix(complex_, k + 1)))
            if next_simplices
            else 0
        )
        betti.append(kernel_k - rank_next)
    return tuple(betti)


__all__ = ["Simplex", "VietorisRipsComplex", "betti_numbers", "boundary_matrix"]
