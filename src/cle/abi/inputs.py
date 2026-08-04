"""The CLE input ABI: structural shapes for what CLE reads, never imports.

CLE has no direct dependency on Meaning Space Runtime, Meaning Mapper, or
HEKB internals. Every value CLE receives from a neighbour is described here
as a :class:`typing.Protocol` — a shape, not a shared class — so that
`msr.abi.StabilizedTrajectory` (or any other object of the same shape)
satisfies these Protocols without CLE importing `msr`. This is the same
convention `meaning-space-runtime`'s own `msr.adapters.hekb.ConceptLike`
already uses for its one upstream dependency (RFC-MSR01 Section 4: "any
object satisfying a port's shape MAY be bound").

=========================  ================================================
:class:`MeaningStateLike`  One snapshot in a stabilized trajectory's history
:class:`StabilizedTrajectoryLike`  CLE's primary input — MSR -> CLE (slow loop)
:class:`FieldPriorLike`    Optional: the runtime field prior CLE lifted from
:class:`HEKBContextLike`   Optional: existing HEKB concepts, for evolution vs. discovery
=========================  ================================================

CLE MUST NOT accept raw observations or `MeaningMeasurement` — only these
already-stabilized shapes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]


@runtime_checkable
class MeaningStateLike(Protocol):
    """One snapshot in a `StabilizedTrajectoryLike.states` history.

    Structurally identical to `msr.abi.MeaningState`, read-only.
    """

    @property
    def frame_id(self) -> str: ...

    @property
    def step_index(self) -> int: ...

    @property
    def time_s(self) -> float: ...

    @property
    def theta(self) -> Vector: ...

    @property
    def basin_id(self) -> str | None: ...


@runtime_checkable
class StabilizedTrajectoryLike(Protocol):
    """CLE's primary and required input: a trajectory MSR considers stabilized.

    Structurally identical to `msr.abi.StabilizedTrajectory`, read-only. CLE
    reads this shape; it does not import `msr.abi` to type-check it.
    """

    @property
    def trajectory_id(self) -> str: ...

    @property
    def frame_id(self) -> str: ...

    @property
    def basin_id(self) -> str | None: ...

    @property
    def states(self) -> tuple[MeaningStateLike, ...]: ...

    @property
    def centroid(self) -> Vector: ...

    @property
    def covariance(self) -> Matrix: ...

    @property
    def dwell_steps(self) -> int: ...

    @property
    def dwell_seconds(self) -> float: ...

    @property
    def provenance(self) -> tuple[str, ...]: ...

    @property
    def is_novel(self) -> bool: ...


@runtime_checkable
class FieldPriorLike(Protocol):
    """Optional context: the runtime field prior the trajectory was lifted from.

    Minimal by design — CLE does not recompute or interpret the potential
    field (that is MSR's `Φ`); it only reads enough to attribute a
    crystallization to the field version it was produced under.
    """

    @property
    def frame_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    @property
    def version(self) -> int: ...


@runtime_checkable
class HEKBConceptLike(Protocol):
    """One existing HEKB concept, as read for evolution-vs-discovery decisions.

    Structurally identical to what `msr.adapters.hekb.ConceptLike` already
    expects downstream (`.id`, `.centroid`), extended with the optional
    geometry CLE's own `Concept` output also carries.
    """

    @property
    def id(self) -> str: ...

    @property
    def centroid(self) -> Vector | None: ...


@runtime_checkable
class HEKBContextLike(Protocol):
    """Optional HEKB context: what concepts already exist, for this frame.

    CLE never queries HEKB directly (no dependency on HEKB internals); a host
    process supplies this Protocol, typically backed by a read-only HEKB
    query result.
    """

    def concepts_near(
        self, centroid: Vector, *, radius: float
    ) -> tuple[HEKBConceptLike, ...]: ...


__all__ = [
    "FieldPriorLike",
    "HEKBConceptLike",
    "HEKBContextLike",
    "Matrix",
    "MeaningStateLike",
    "StabilizedTrajectoryLike",
    "Vector",
]
