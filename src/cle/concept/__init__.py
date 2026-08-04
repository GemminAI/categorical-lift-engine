"""Concept discovery and concept evolution.

Owns turning one stabilized trajectory into either a brand-new `Concept`
(novel stabilization) or a `ConceptDelta` against an existing one
(reinforcement/refinement) — never both, and never a raw observation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBContextLike, StabilizedTrajectoryLike
from cle.abi.outputs import Concept, ConceptDelta


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


__all__ = ["ConceptDiscoveryStrategy"]
