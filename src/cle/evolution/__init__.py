"""Category Evolution Tracking (CET) — RFC-CLE004, Phase 4.

**Experimental.** Per direction, this phase optimizes for discovering the
right shape for knowledge-evolution tracking, not for a minimal ABI: every
type here is new, lives outside `cle.abi` on purpose, and is expected to be
revised or removed as the discovery continues. Each type and the concrete
tracker below are independently deterministic, independently testable, and
removable without touching `cle.abi`, `cle.concept`, `cle.homotopy`, or
`cle.crystallization`/`cle.knowledge_delta`/`cle.commit_candidate` — deleting
this package end-to-end breaks nothing upstream. See `docs/RFC_ALIGNMENT.md`
for the full rationale behind every design choice below.

Scope of this milestone: `EvolutionEventType.BIRTH` / `DEATH` / `DRIFT`, and
`CategoryEvolutionTracker.detect_evolution` / `apply_events`. `MERGE`,
`SPLIT`, and `trace_lineage` are declared (`EvolutionEventType` names all
five, matching RFC-CLE004 §4 exactly) but not yet constructible or
implemented — deferred to a follow-up milestone, once a pushout/pullback
mechanism exists to detect them honestly rather than guessed at.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from cle.abi.inputs import Vector
from cle.abi.outputs import MorphismType
from cle.geometry import euclidean_distance
from cle.identity import deterministic_id


class EvolutionEventType(StrEnum):
    """RFC-CLE004 §4's five evolution events, named 1:1 for future alignment.

    Only `BIRTH`, `DEATH`, `DRIFT` are produced by this milestone's
    `GeometricEvolutionTracker` — see module docstring.
    """

    BIRTH = "birth"
    DEATH = "death"
    MERGE = "merge"
    SPLIT = "split"
    DRIFT = "drift"


@dataclass(frozen=True, slots=True)
class NodeState:
    """A node's identity and position at one point in time.

    Deliberately smaller than `Concept`/`ConceptDelta` (`cle.abi.outputs`):
    for the purpose of detecting whether a node exists and where it is, it
    does not matter whether it is currently represented as a freshly
    discovered `Concept` or a reinforced `ConceptDelta` — both reduce to
    "this id, at this position." Building a `NodeState` from either is the
    caller's job (a `Concept.centroid` directly, or a prior `NodeState`'s
    centroid plus a `ConceptDelta.centroid_shift`); `cle.evolution` does not
    depend on `cle.concept` to stay independently removable.
    """

    node_id: str
    centroid: Vector


@dataclass(frozen=True, slots=True)
class AncestryLink:
    """RFC-CLE004 §4: a lineage edge to one parent node.

    `morphism_type` reuses Phase 1's `cle.abi.outputs.MorphismType`
    (RFC-CLE004's own examples — "canonical_inclusion", "pushout_projection"
    — map onto the existing `INCLUSION`/`PUSHOUT_CANONICAL` members) rather
    than introducing a second, parallel string vocabulary for the same
    concept.
    """

    parent_node_id: str
    morphism_type: MorphismType
    weight: float


@dataclass(frozen=True, slots=True)
class EvolutionEvent:
    """RFC-CLE004 §4: one detected structural change between two snapshots.

    `betti_delta` is `cle.homotopy`'s Betti numbers finally given somewhere
    to go (RFC-CLE002's `ObjectNode.betti_numbers` gap, flagged and
    deliberately deferred in the Phase 2 and Phase 3 reviews) — but this
    milestone's `GeometricEvolutionTracker` always sets it to `()`, since
    computing it would require re-running `EpsilonGraphBettiAnalyzer` over
    each node's trajectory, which `NodeState` does not carry (see its own
    docstring). The field exists so a future milestone can populate it
    without another ABI-shaped change.
    """

    event_id: str
    event_type: EvolutionEventType
    source_node_ids: tuple[str, ...]
    target_node_ids: tuple[str, ...]
    ancestry_links: tuple[AncestryLink, ...]
    betti_delta: tuple[int, ...]
    confidence_score: float
    timestamp_utc: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be in [0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class LineageSnapshot:
    """RFC-CLE004 §4: the DAG's structural skeleton at one point in time.

    Deliberately minimal, matching the RFC exactly: ids only, no geometry —
    `NodeState` carries the geometry `detect_evolution` needs; this type is
    only ever bookkeeping for `apply_events`'s replay chain.
    """

    snapshot_id: str
    timestamp_utc: str
    active_node_ids: tuple[str, ...]
    active_morphism_ids: tuple[str, ...] = ()
    parent_snapshot_id: str | None = None


@runtime_checkable
class CategoryEvolutionTracker(Protocol):
    """RFC-CLE004 §5's `CategoryEvolutionTrackingProtocol`, this milestone's slice.

    `trace_lineage` is not declared here yet: with only `BIRTH`/`DEATH`/
    `DRIFT` producible, every node has at most one trivial parent (or none),
    so a lineage trace has nothing genuine to demonstrate until `MERGE`/
    `SPLIT` exist. Adding it to this Protocol now would mean shipping an
    untested, unmotivated method — deferred to the same follow-up milestone
    as `MERGE`/`SPLIT`, additively, once it can be tested against a real
    multi-parent case.
    """

    def detect_evolution(
        self,
        previous_nodes: tuple[NodeState, ...],
        current_nodes: tuple[NodeState, ...],
    ) -> tuple[EvolutionEvent, ...]: ...

    def apply_events(
        self,
        previous_snapshot: LineageSnapshot,
        events: tuple[EvolutionEvent, ...],
    ) -> LineageSnapshot: ...


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _drift_confidence(distance: float, tolerance: float) -> float:
    """Monotonically increasing in `distance`, bounded to `[0, 1)`.

    Same saturating shape as `cle.commit_candidate`'s confidence formula
    (`distance / (distance + tolerance)`), reimplemented locally rather than
    imported: it is a different module's private detail, and duplicating
    four lines keeps `cle.evolution` removable without touching
    `cle.commit_candidate`.
    """
    return distance / (distance + tolerance)


@dataclass(frozen=True, slots=True)
class GeometricEvolutionTracker:
    """`BIRTH`/`DEATH`/`DRIFT` detection from two `NodeState` snapshots.

    - `BIRTH`: a node id present in `current_nodes` but not `previous_nodes`.
    - `DEATH`: a node id present in `previous_nodes` but not `current_nodes`.
    - `DRIFT`: a node id present in both, whose centroid moved more than
      `drift_tolerance` (Euclidean distance, `cle.geometry`).

    `BIRTH`/`DEATH` get `confidence_score=1.0` — presence or absence in a
    `NodeState` sequence is a hard fact, not a volume-of-evidence estimate
    (the same reasoning `cle.commit_candidate.ObservationalCommitCandidateBuilder`
    already applies to a `CategoryRelation`'s confidence). `DRIFT`'s
    confidence saturates with how far past `drift_tolerance` the movement
    is, and its `metadata` records the raw `distance`/`tolerance` so the
    event is self-explanatory without recomputing anything — "optimize for
    discovery" read as: make evolution observable, not just detectable.

    Returned events are sorted by `(event_type, affected node ids)`, not by
    `previous_nodes`/`current_nodes` iteration order: the caller's ordering
    of either sequence is not part of this tracker's determinism contract,
    the same lesson the Phase 2 review's tie-break fix already established
    for `FunctorialConceptLift`.

    `timestamp_utc` comes from an injectable `clock_utc` callable (default:
    real UTC time), the same pattern `ObservationalCommitCandidateBuilder`
    already uses for `created_at_ns` — the deterministic parts of an event
    (`event_id`, `event_type`, node ids, `confidence_score`) are what "same
    input -> same output" is tested against, not wall-clock time.
    """

    drift_tolerance: float = 0.0
    clock_utc: Callable[[], str] = field(default=_utc_now)

    def __post_init__(self) -> None:
        if self.drift_tolerance < 0.0:
            raise ValueError("drift_tolerance must be greater than or equal to zero")

    def detect_evolution(
        self,
        previous_nodes: tuple[NodeState, ...],
        current_nodes: tuple[NodeState, ...],
    ) -> tuple[EvolutionEvent, ...]:
        previous_by_id = {node.node_id: node for node in previous_nodes}
        current_by_id = {node.node_id: node for node in current_nodes}
        timestamp = self.clock_utc()

        events = [
            self._birth(node_id, timestamp)
            for node_id in current_by_id.keys() - previous_by_id.keys()
        ]
        events += [
            self._death(node_id, timestamp)
            for node_id in previous_by_id.keys() - current_by_id.keys()
        ]
        for node_id in previous_by_id.keys() & current_by_id.keys():
            drift = self._drift(
                node_id, previous_by_id[node_id], current_by_id[node_id], timestamp
            )
            if drift is not None:
                events.append(drift)

        def sort_key(
            event: EvolutionEvent,
        ) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
            return (event.event_type, event.source_node_ids, event.target_node_ids)

        return tuple(sorted(events, key=sort_key))

    def apply_events(
        self,
        previous_snapshot: LineageSnapshot,
        events: tuple[EvolutionEvent, ...],
    ) -> LineageSnapshot:
        active = set(previous_snapshot.active_node_ids)
        for event in events:
            if event.event_type is EvolutionEventType.BIRTH:
                active |= set(event.target_node_ids)
            elif event.event_type is EvolutionEventType.DEATH:
                active -= set(event.source_node_ids)
        return LineageSnapshot(
            # Hash on each event's own `event_id` (already timestamp-free —
            # see `_birth`/`_death`/`_drift`), not the `EvolutionEvent`
            # objects themselves: their `repr()` includes `timestamp_utc`,
            # which would otherwise couple `snapshot_id` to wall-clock time.
            snapshot_id=deterministic_id(
                "snapshot",
                previous_snapshot.snapshot_id,
                tuple(event.event_id for event in events),
            ),
            timestamp_utc=self.clock_utc(),
            active_node_ids=tuple(sorted(active)),
            active_morphism_ids=previous_snapshot.active_morphism_ids,
            parent_snapshot_id=previous_snapshot.snapshot_id,
        )

    def _birth(self, node_id: str, timestamp: str) -> EvolutionEvent:
        return EvolutionEvent(
            event_id=deterministic_id("evolution", "birth", node_id),
            event_type=EvolutionEventType.BIRTH,
            source_node_ids=(),
            target_node_ids=(node_id,),
            ancestry_links=(),
            betti_delta=(),
            confidence_score=1.0,
            timestamp_utc=timestamp,
        )

    def _death(self, node_id: str, timestamp: str) -> EvolutionEvent:
        return EvolutionEvent(
            event_id=deterministic_id("evolution", "death", node_id),
            event_type=EvolutionEventType.DEATH,
            source_node_ids=(node_id,),
            target_node_ids=(),
            ancestry_links=(),
            betti_delta=(),
            confidence_score=1.0,
            timestamp_utc=timestamp,
        )

    def _drift(
        self,
        node_id: str,
        previous: NodeState,
        current: NodeState,
        timestamp: str,
    ) -> EvolutionEvent | None:
        distance = euclidean_distance(previous.centroid, current.centroid)
        if distance <= self.drift_tolerance:
            return None
        return EvolutionEvent(
            event_id=deterministic_id(
                "evolution", "drift", node_id, previous.centroid, current.centroid
            ),
            event_type=EvolutionEventType.DRIFT,
            source_node_ids=(node_id,),
            target_node_ids=(node_id,),
            ancestry_links=(),
            betti_delta=(),
            confidence_score=_drift_confidence(distance, self.drift_tolerance),
            timestamp_utc=timestamp,
            metadata={"distance": distance, "tolerance": self.drift_tolerance},
        )


__all__ = [
    "AncestryLink",
    "CategoryEvolutionTracker",
    "EvolutionEvent",
    "EvolutionEventType",
    "GeometricEvolutionTracker",
    "LineageSnapshot",
    "NodeState",
]
