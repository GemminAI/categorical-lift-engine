"""A point sequence tagged with which semantic space it lives in.

CLE's topology pipeline (this package) and the five metrics in
`cle.metrics` both end up operating on bare point clouds — a `(T, d)`
array of coordinates. Those coordinates can come from two semantic spaces
that must never be mixed: MSR's theta-space (`StabilizedTrajectoryLike`'s
`states[i].theta`) and NVS-Kernel's 64-dimensional hidden-state space
(`position_64d`, as recorded by `/experiment/observe-38-ports`). Distance,
centroid, and the topology this package computes are meaningless across
that boundary — a Vietoris-Rips complex built from a mix of the two would
silently compute nonsense, since nothing about a raw `(T, d)` numpy array
says which space it came from.

`SpacedPointSequence` is the one input type everything downstream reads:
it carries `space_id` so a caller can refuse to compare two sequences
from different spaces, instead of discovering the mistake downstream (or
never discovering it at all).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from cle.abi.inputs import StabilizedTrajectoryLike
from cle.errors import DimensionMismatch, NonFiniteValue


@dataclass(frozen=True, slots=True)
class SpacedPointSequence:
    """`T` ordered points in one named semantic space.

    ``space_id`` vs. ``frame_id`` — orthogonal, not redundant:

    - ``space_id`` names the *kind* of space the points live in (e.g.
      ``"msr.theta"``, ``"nvs.hidden64"``). It is fixed by which upstream
      system produced the points and never changes meaning at runtime.
      This is the field `cle.topology`/`cle.metrics` check before
      comparing, merging, or computing any distance between two
      sequences — comparing two different ``space_id``s is always a bug,
      never a valid operation.
    - ``frame_id`` names *which instance* of that space's coordinate
      system a specific point was measured relative to — e.g. which MSR
      potential-field version was active (`FieldPriorLike.version` already
      exists upstream to let a caller detect a field-version mismatch).
      Two `SpacedPointSequence`s can legitimately share one ``space_id``
      (both ``"msr.theta"``) while carrying different ``frame_id``s
      (different field instances); their raw coordinates are still not
      safely comparable without reconciling the frame first, but that is
      a separate, coarser-grained check than ``space_id`` — this type
      carries both so neither check can be skipped by accident.

    ``points`` is ``(T, d)`` float64: `T` instants, each a `d`-dimensional
    coordinate. ``order`` is `T` integers giving each row's position in the
    original sequence (e.g. MSR's own `step_index`) — kept explicit rather
    than assumed from array order, since nothing about a bare numpy array
    enforces that rows 0..T-1 are already sorted. ``provenance`` is the
    free-form lineage trail carried over from the upstream value (e.g.
    `StabilizedTrajectoryLike.provenance`).
    """

    space_id: str
    frame_id: str
    points: NDArray[np.float64]
    order: tuple[int, ...]
    provenance: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.points.ndim != 2:
            raise DimensionMismatch(
                f"points must be a (T, d) array, got shape {self.points.shape!r}"
            )
        if self.points.shape[0] != len(self.order):
            raise DimensionMismatch(
                f"order has {len(self.order)} entries but points has "
                f"{self.points.shape[0]} rows"
            )
        if not np.isfinite(self.points).all():
            raise NonFiniteValue(
                f"points for space_id={self.space_id!r} contains a NaN or "
                "infinite coordinate"
            )

    @classmethod
    def from_stabilized_trajectory(
        cls, trajectory: StabilizedTrajectoryLike
    ) -> SpacedPointSequence:
        """MSR -> CLE's one fixed binding: always ``space_id="msr.theta"``.

        `StabilizedTrajectoryLike` is CLE's only Protocol-typed input that
        carries raw per-step coordinates (`.states[i].theta`), and every
        one of those coordinates is, by construction of the Protocol
        itself (`cle.abi.inputs`), MSR's theta-space — so this is the one
        place `space_id` is a constant, not a parameter.
        """
        points = np.array(
            [state.theta for state in trajectory.states], dtype=np.float64
        )
        if points.ndim == 1:
            points = points.reshape(len(trajectory.states), 0)
        order = tuple(state.step_index for state in trajectory.states)
        return cls(
            space_id="msr.theta",
            frame_id=trajectory.frame_id,
            points=points,
            order=order,
            provenance=trajectory.provenance,
        )


__all__ = ["SpacedPointSequence"]
