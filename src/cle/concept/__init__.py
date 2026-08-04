"""Concept discovery and concept evolution.

Owns turning one stabilized trajectory into either a brand-new `Concept`
(novel stabilization) or a `ConceptDelta` against an existing one
(reinforcement/refinement) — never both, and never a raw observation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBConceptLike, HEKBContextLike, StabilizedTrajectoryLike
from cle.abi.outputs import Concept, ConceptDelta
from cle.errors import DimensionMismatch
from cle.identity import deterministic_id


@runtime_checkable
class ConceptDiscoveryStrategy(Protocol):
    """Trajectory -> new `Concept` or evolving `ConceptDelta`.

    Implementations decide novelty using `trajectory.is_novel` and, when
    available, `hekb_context` — this repository defines the interface only;
    the categorical-theory judgment of "is this really new" is left to a
    concrete strategy, not fabricated here.
    """

    def discover(
        self,
        trajectory: StabilizedTrajectoryLike,
        *,
        hekb_context: HEKBContextLike | None,
    ) -> Concept | ConceptDelta: ...


def _validate_covariance_shape(trajectory: StabilizedTrajectoryLike) -> int:
    dim = len(trajectory.centroid)
    covariance = trajectory.covariance
    if len(covariance) != dim or any(len(row) != dim for row in covariance):
        raise DimensionMismatch(
            f"trajectory {trajectory.trajectory_id!r} has centroid of dimension "
            f"{dim} but covariance shape {len(covariance)}x"
            f"{len(covariance[0]) if covariance else 0}"
        )
    return dim


def _euclidean_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b):
        raise DimensionMismatch(
            f"cannot compare vectors of dimension {len(a)} and {len(b)}"
        )
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def _match_radius(trajectory: StabilizedTrajectoryLike, dim: int) -> float:
    """Two standard deviations of the trajectory's own spread — a
    trajectory-relative match radius, not an arbitrary fixed constant.

    A zero (or zero-dimensional) trace collapses to a zero radius rather
    than dividing by zero.
    """
    trace = sum(trajectory.covariance[i][i] for i in range(dim))
    if trace <= 0.0:
        return 0.0
    return 2.0 * math.sqrt(trace / dim)


def _closest_known_concept(
    trajectory: StabilizedTrajectoryLike,
    hekb_context: HEKBContextLike,
    dim: int,
) -> HEKBConceptLike | None:
    radius = _match_radius(trajectory, dim)
    candidates = hekb_context.concepts_near(trajectory.centroid, radius=radius)
    if not candidates:
        return None
    known = [c for c in candidates if c.centroid is not None]
    if not known:
        return candidates[0]
    return min(
        known,
        key=lambda c: (
            _euclidean_distance(trajectory.centroid, c.centroid)
            if c.centroid is not None
            else math.inf
        ),
    )


@dataclass(frozen=True, slots=True)
class FunctorialConceptLift:
    """Object lifting: `StabilizedTrajectory` -> `Concept` | `ConceptDelta`.

    RFC-CLE001 §3.1's Functorial Lift acting on objects: the trajectory
    (an object of $\\mathcal{M}_{\\text{proj}}$) becomes a concept (an object
    of $\\mathcal{C}_{\\text{concept}}$). Novelty follows `trajectory.is_novel`
    exactly as `ConceptDiscoveryStrategy` already documents:

    - `is_novel` is `True` -> a brand-new `Concept`, with a deterministic id
      derived from `(frame_id, centroid)` (RFC-CLE005 §3.2 lift-determinism).
    - `is_novel` is `False` -> a `ConceptDelta` against the concept
      `hekb_context` resolves the trajectory's centroid to (nearest known
      concept within a radius derived from the trajectory's own covariance),
      falling back to a deterministic id derived from `basin_id` when no
      `hekb_context` is supplied or nothing is found near enough.
    """

    def discover(
        self,
        trajectory: StabilizedTrajectoryLike,
        *,
        hekb_context: HEKBContextLike | None,
    ) -> Concept | ConceptDelta:
        dim = _validate_covariance_shape(trajectory)

        if not trajectory.is_novel:
            matched = (
                _closest_known_concept(trajectory, hekb_context, dim)
                if hekb_context is not None
                else None
            )
            if matched is not None:
                concept_id = matched.id
                shift = (
                    tuple(
                        t - m
                        for t, m in zip(
                            trajectory.centroid, matched.centroid, strict=True
                        )
                    )
                    if matched.centroid is not None
                    else None
                )
            else:
                concept_id = deterministic_id(
                    "concept", trajectory.frame_id, trajectory.basin_id
                )
                shift = None
            return ConceptDelta(
                concept_id=concept_id,
                frame_id=trajectory.frame_id,
                centroid_shift=shift,
                source_trajectory_id=trajectory.trajectory_id,
                provenance=trajectory.provenance,
            )

        object_id = deterministic_id(
            "concept", trajectory.frame_id, trajectory.centroid
        )
        invariants = {
            "dwell_steps": float(trajectory.dwell_steps),
            "dwell_seconds": trajectory.dwell_seconds,
            "state_count": float(len(trajectory.states)),
        }
        return Concept(
            id=object_id,
            frame_id=trajectory.frame_id,
            centroid=trajectory.centroid,
            hessian=trajectory.covariance,
            invariants=invariants,
            source_trajectory_id=trajectory.trajectory_id,
            provenance=trajectory.provenance,
        )


__all__ = ["ConceptDiscoveryStrategy", "FunctorialConceptLift"]
