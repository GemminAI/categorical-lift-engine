"""Homotopy analysis.

Owns deciding whether two concepts are homotopic: continuously deformable
into one another, i.e. the same underlying knowledge reached by different
evidence paths. This is the equivalence relation `cle.quotient` collapses.

Two Protocols live here at two different granularities:

- `HomotopyAnalyzer` (pre-existing): compares two already-crystallized HEKB
  concepts by `.id`/`.centroid` alone.
- `HomotopyPathAnalyzer` (added Phase 2, RFC-CLE001 §3.3 / RFC-CLE002 HPIA):
  compares raw trajectory coordinate paths via topological (Betti-number)
  invariants — the level of detail real homotopy analysis needs, which
  `HomotopyAnalyzer`'s id/centroid-only shape cannot carry. See
  `docs/RFC_ALIGNMENT.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBConceptLike, StabilizedTrajectoryLike, Vector
from cle.errors import DimensionMismatch
from cle.geometry import euclidean_distance


@runtime_checkable
class HomotopyAnalyzer(Protocol):
    """`True` when two concepts are the same knowledge under continuous deformation."""

    def is_homotopic(self, a: HEKBConceptLike, b: HEKBConceptLike) -> bool: ...


@runtime_checkable
class HomotopyPathAnalyzer(Protocol):
    """RFC-CLE002 HPIA: point-cloud topology of a trajectory's coordinate path.

    `compute_betti_numbers` operates on a raw point cloud (any coordinate
    sequence, not necessarily a trajectory) so it composes independently of
    the ABI; `paths_are_homotopic` is the trajectory-level convenience
    RFC-CLE001 §3.3 actually asks for.

    Named `paths_are_homotopic`, not `is_homotopic`, deliberately: this
    Protocol lives in the same module as `HomotopyAnalyzer` above, and
    `@runtime_checkable` `isinstance()` checks only verify that a method of
    the given *name* exists — it does not check parameter count or types.
    A method named `is_homotopic` here would make any implementation of
    this Protocol also structurally (and wrongly) satisfy
    `isinstance(x, HomotopyAnalyzer)`, despite an incompatible 3-argument
    signature — confirmed to raise `TypeError` at the call site if actually
    invoked as a `HomotopyAnalyzer`. See `docs/RFC_ALIGNMENT.md`.
    """

    def compute_betti_numbers(
        self, coordinates: tuple[Vector, ...], eps: float
    ) -> tuple[int, ...]: ...

    def paths_are_homotopic(
        self,
        trajectory_a: StabilizedTrajectoryLike,
        trajectory_b: StabilizedTrajectoryLike,
        tolerance: float,
    ) -> bool: ...


class _UnionFind:
    """The textbook disjoint-set structure — path-compressed, unranked.

    Deliberately this small and no smaller/larger: it is the entire
    "graph library" this phase needs, not a general graph package.
    """

    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, node: int) -> int:
        while self._parent[node] != node:
            self._parent[node] = self._parent[self._parent[node]]
            node = self._parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_a] = root_b


def _graph_betti_numbers(
    coordinates: tuple[Vector, ...], eps: float
) -> tuple[int, int]:
    count = len(coordinates)
    if count == 0:
        return (0, 0)
    dim = len(coordinates[0])
    if any(len(point) != dim for point in coordinates):
        raise DimensionMismatch(
            "all coordinates must share the same dimension to form a graph"
        )
    union_find = _UnionFind(count)
    edge_count = 0
    for i in range(count):
        for j in range(i + 1, count):
            if euclidean_distance(coordinates[i], coordinates[j]) <= eps:
                edge_count += 1
                union_find.union(i, j)
    component_count = len({union_find.find(i) for i in range(count)})
    return (component_count, edge_count - count + component_count)


@dataclass(frozen=True, slots=True)
class EpsilonGraphBettiAnalyzer:
    """The Betti numbers of a point cloud's eps-neighborhood *graph*.

    RFC-CLE001 Phase 2 (Homotopy Path Analyzer), scoped to the minimum
    mathematics RFC-CLE002 requires, deliberately without a persistent-
    homology or simplicial-complex library:

    - One vertex per coordinate; an edge between any two points at
      Euclidean distance <= `eps` (a single-scale Vietoris-Rips *graph*,
      not the full Vietoris-Rips simplicial complex — no filtration, no
      2-simplices).
    - `b_0` = number of connected components. Exact, and equal to the full
      simplicial complex's `b_0` at the same scale — connectivity doesn't
      depend on which higher simplices exist.
    - `b_1` = `edges - vertices + components`: the graph's circuit rank, an
      exact fact of graph theory (the graph's own first Betti number,
      treating it as a 1-dimensional CW complex).

    Caveat, stated rather than hidden: this `b_1` is an **upper bound** on,
    not identical to, the full Vietoris-Rips simplicial complex's `b_1`.
    Three mutually-close points count as one cycle here even though a real
    simplicial complex would fill the triangle (a 2-simplex) and cap it off
    to `b_1 = 0`. Detecting fillable triangles needs 2-simplices and real
    simplicial homology — exactly the "topology library" this phase is
    scoped not to build (see `tests/test_homotopy_path_analyzer.py`, which
    has a case demonstrating this known, deliberate discrepancy directly).

    `paths_are_homotopic` decides equivalence by Betti-tuple equality at a
    shared scale (`tolerance`). Betti numbers are homotopy invariants: unequal
    Betti numbers *proves* two trajectories are not homotopy-equivalent;
    equal Betti numbers is evidence, not proof (distinct spaces can share
    Betti numbers). That is the necessary-condition proxy RFC-CLE005 §2.2's
    determinism test needs — not a full homotopy-equivalence decision
    procedure.
    """

    def compute_betti_numbers(
        self, coordinates: tuple[Vector, ...], eps: float
    ) -> tuple[int, ...]:
        return _graph_betti_numbers(coordinates, eps)

    def paths_are_homotopic(
        self,
        trajectory_a: StabilizedTrajectoryLike,
        trajectory_b: StabilizedTrajectoryLike,
        tolerance: float,
    ) -> bool:
        coordinates_a = tuple(state.theta for state in trajectory_a.states)
        coordinates_b = tuple(state.theta for state in trajectory_b.states)
        return self.compute_betti_numbers(
            coordinates_a, tolerance
        ) == self.compute_betti_numbers(coordinates_b, tolerance)


__all__ = ["EpsilonGraphBettiAnalyzer", "HomotopyAnalyzer", "HomotopyPathAnalyzer"]
