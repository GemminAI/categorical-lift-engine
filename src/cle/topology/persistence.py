"""Persistent homology (H0, H1) over the full Vietoris-Rips filtration.

`cle.topology.simplicial.betti_numbers` computes Betti numbers at one fixed
`eps` -- a single slice of the filtration. This module computes the whole
filtration's persistence diagram (every simplex's birth/death scale across
all `eps`), which is what the calibration tests in this phase actually need
(e.g. "the circle has exactly one long-lived H1 bar", a statement about the
*whole* filtration, not one scale).

`PersistenceDiagram` and `delay_embed` are pure numpy -- importing this
module never requires `ripser` or `persim`. Only `compute_persistence_diagram`
(ripser) and `bottleneck_distance` (persim) need them, and each raises
`TopologyExtraNotInstalled` with an actionable message if the optional
``[topology]`` extra (both MIT-licensed) is not installed, rather than a
bare `ImportError` deep in a third-party stack trace.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from cle.abi.inputs import StabilizedTrajectoryLike, Vector
from cle.errors import CLEError


class TopologyExtraNotInstalled(CLEError):
    """`ripser` or `persim` is required for this call but not installed.

    Install with the ``topology`` extra: ``pip install
    "categorical-lift-engine[topology]"`` (or ``uv sync --extra topology``
    in this repository). Both are MIT-licensed and optional -- nothing
    else in `cle.topology` depends on them.
    """


@dataclass(frozen=True, slots=True)
class PersistenceDiagram:
    """Birth/death pairs per homology dimension, from one VR filtration.

    ``diagrams[k]`` is an ``(N_k, 2)`` float64 array of ``(birth, death)``
    pairs for dimension `k`. A `death` of `+inf` is a feature that never
    dies within the filtration (always present for `H_0`: the single
    class representing "eventually everything is one component").
    """

    diagrams: dict[int, NDArray[np.float64]]

    def betti_numbers(self, eps: float) -> tuple[int, ...]:
        """`Betti_k(eps)` = how many dimension-`k` features are alive at `eps`.

        A pair is alive at `eps` when ``birth <= eps < death`` -- the
        standard persistence-diagram reading of a single-scale Betti
        number, for every dimension this diagram has, in order.
        """
        if not self.diagrams:
            return ()
        max_dimension = max(self.diagrams)
        betti: list[int] = []
        for dimension in range(max_dimension + 1):
            pairs = self.diagrams.get(dimension, np.zeros((0, 2)))
            if pairs.size == 0:
                betti.append(0)
                continue
            alive = (pairs[:, 0] <= eps) & (eps < pairs[:, 1])
            betti.append(int(np.count_nonzero(alive)))
        return tuple(betti)

    def total_persistence(self, dimension: int) -> float:
        """Sum of ``death - birth`` over dimension `dimension`'s finite pairs.

        Infinite-death pairs (always present for `H_0`) are excluded --
        their "persistence" is not a finite quantity to sum.
        """
        return float(np.sum(self._finite_lifetimes(dimension)))

    def max_persistence(self, dimension: int) -> float:
        """Longest finite lifetime (``death - birth``) at dimension `dimension`.

        `0.0` if there are no finite pairs at that dimension (including
        when the dimension is absent entirely).
        """
        lifetimes = self._finite_lifetimes(dimension)
        return float(np.max(lifetimes)) if lifetimes.size else 0.0

    def _finite_lifetimes(self, dimension: int) -> NDArray[np.float64]:
        pairs = self.diagrams.get(dimension, np.zeros((0, 2)))
        if pairs.size == 0:
            return np.zeros(0)
        finite = pairs[np.isfinite(pairs[:, 1])]
        return finite[:, 1] - finite[:, 0]


def compute_persistence_diagram(
    points: NDArray[np.float64], *, max_dimension: int = 1
) -> PersistenceDiagram:
    """The Vietoris-Rips persistence diagram of a point cloud, via `ripser`.

    `points` is `(T, d)`. Computes `H_0 .. H_{max_dimension}`. Requires the
    ``topology`` extra; raises `TopologyExtraNotInstalled` if `ripser` is
    not importable.
    """
    try:
        import ripser
    except ImportError as exc:
        raise TopologyExtraNotInstalled(
            "compute_persistence_diagram requires ripser (the 'topology' "
            "extra); it is not installed"
        ) from exc
    result = ripser.ripser(np.asarray(points, dtype=np.float64), maxdim=max_dimension)
    diagrams = {
        dimension: np.asarray(diagram, dtype=np.float64)
        for dimension, diagram in enumerate(result["dgms"])
    }
    return PersistenceDiagram(diagrams=diagrams)


def bottleneck_distance(
    a: PersistenceDiagram, b: PersistenceDiagram, dimension: int
) -> float:
    """The bottleneck distance between `a` and `b`'s diagrams at `dimension`.

    Requires the ``topology`` extra; raises `TopologyExtraNotInstalled` if
    `persim` is not importable. A dimension absent from either diagram is
    treated as an empty diagram at that dimension (not an error).
    """
    try:
        import persim
    except ImportError as exc:
        raise TopologyExtraNotInstalled(
            "bottleneck_distance requires persim (the 'topology' extra); "
            "it is not installed"
        ) from exc
    diagram_a = a.diagrams.get(dimension, np.zeros((0, 2)))
    diagram_b = b.diagrams.get(dimension, np.zeros((0, 2)))
    return float(persim.bottleneck(diagram_a, diagram_b))


def delay_embed(x: NDArray[np.float64], m: int, tau: int) -> NDArray[np.float64]:
    """Takens time-delay embedding: `(T, d)` -> `(T-(m-1)*tau, m*d)`.

    Row `i` of the result is ``concat(x[i], x[i+tau], ..., x[i+(m-1)*tau])``
    -- `m` delayed copies of the signal, `tau` steps apart, stacked into one
    wider row per surviving time index.
    """
    if m < 1:
        raise ValueError(f"m must be >= 1, got {m}")
    if tau < 1:
        raise ValueError(f"tau must be >= 1, got {tau}")
    points = np.asarray(x, dtype=np.float64)
    if points.ndim != 2:
        raise ValueError(f"x must be a (T, d) array, got shape {points.shape!r}")
    length = points.shape[0] - (m - 1) * tau
    if length < 1:
        raise ValueError(
            f"not enough rows to embed: T={points.shape[0]}, (m-1)*tau={(m - 1) * tau}"
        )
    return np.stack(
        [np.concatenate([points[i + k * tau] for k in range(m)]) for i in range(length)]
    )


@dataclass(frozen=True, slots=True)
class PersistenceHomotopyAnalyzer:
    """CLE's operational definition of "two trajectories are homotopic".

    Implements `cle.homotopy.HomotopyPathAnalyzer`'s shape, not
    `HomotopyAnalyzer`'s: `HomotopyAnalyzer.is_homotopic` takes two
    `HEKBConceptLike` values, which carry only a single `centroid` point
    each -- not a point cloud, so no persistence diagram can be built from
    one. `HomotopyPathAnalyzer` already carries the full coordinate path
    (`StabilizedTrajectoryLike.states[i].theta`) this class needs.

    `paths_are_homotopic(a, b, tolerance)` here means: the bottleneck
    distance between `a` and `b`'s `H_0` diagrams is `<= tolerance`, AND
    likewise for `H_1`. This is CLE's chosen operational proxy for
    "the same shape" -- **not** mathematical homotopy equivalence, and not
    even the weaker claim `EpsilonGraphBettiAnalyzer.paths_are_homotopic`
    makes (single-scale Betti-tuple equality). It is a strictly more
    faithful proxy than that one, because it compares the *whole*
    filtration via bottleneck distance rather than one `eps` slice, but it
    remains a proxy: a small bottleneck distance is evidence of similar
    shape, not a decision procedure for homotopy equivalence.
    """

    max_dimension: int = 1

    def compute_betti_numbers(
        self, coordinates: tuple[Vector, ...], eps: float
    ) -> tuple[int, ...]:
        points = np.asarray(coordinates, dtype=np.float64)
        diagram = compute_persistence_diagram(points, max_dimension=self.max_dimension)
        return diagram.betti_numbers(eps)

    def paths_are_homotopic(
        self,
        trajectory_a: StabilizedTrajectoryLike,
        trajectory_b: StabilizedTrajectoryLike,
        tolerance: float,
    ) -> bool:
        diagram_a = compute_persistence_diagram(
            np.array([state.theta for state in trajectory_a.states]),
            max_dimension=self.max_dimension,
        )
        diagram_b = compute_persistence_diagram(
            np.array([state.theta for state in trajectory_b.states]),
            max_dimension=self.max_dimension,
        )
        return all(
            bottleneck_distance(diagram_a, diagram_b, dimension) <= tolerance
            for dimension in range(self.max_dimension + 1)
        )


__all__ = [
    "PersistenceDiagram",
    "PersistenceHomotopyAnalyzer",
    "TopologyExtraNotInstalled",
    "bottleneck_distance",
    "compute_persistence_diagram",
    "delay_embed",
]
