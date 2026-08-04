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

All five `EvolutionEventType` members are now constructible:
`BIRTH`/`DEATH`/`DRIFT` from simple id-membership and centroid distance;
`MERGE`/`SPLIT` from a nearest-centroid grouping heuristic (see
`GeometricEvolutionTracker`'s own docstring) — explicitly a heuristic, not a
verified categorical pushout/pullback, since `NodeState` carries only an id
and a position, never the full trajectory a rigorous pullback/pushout
construction would need. `trace_lineage` walks the ancestry graph these
events form.
"""

from __future__ import annotations

import math
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
    """RFC-CLE004 §4's five evolution events, named 1:1 for future alignment."""

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
    caller's job; `cle.evolution` does not depend on `cle.concept` to stay
    independently removable.

    Precondition, not validated here: a `tuple[NodeState, ...]` passed to
    `GeometricEvolutionTracker` must not contain two entries with the same
    `node_id`. Node identity uniqueness is a property the *producer* of a
    snapshot is responsible for (a `Concept.id`/`ConceptDelta.concept_id` is
    already unique by construction in `cle.concept`) — `cle.evolution`
    intentionally does not re-derive or re-validate that upstream
    invariant. If violated, `GeometricEvolutionTracker` resolves the
    duplicate by last-occurrence-wins, silently and without warning; this
    is undefined behavior from the caller's perspective, not a documented
    contract, and callers must not rely on which occurrence wins.
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

    `weight` is a contribution fraction, interpreted per producing event:
    a `MERGE`'s links (`PUSHOUT_CANONICAL`) each carry `1 / len(sources)`,
    since multiple parents jointly explain one child; a `SPLIT`'s links
    (`PULLBACK_CANONICAL`) each carry `1.0`, since one parent alone fully
    explains each child.
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
    each node's trajectory, which `NodeState` does not carry. A direct,
    disclosed consequence: `DRIFT` here is a geometric-proximity signal —
    it cannot distinguish "the same concept moved a little" from "this id
    was reused for something now topologically different," because no
    Betti/homotopy check is actually performed. Likewise `BIRTH`/`DEATH`
    are syntactic id-membership facts, not independent verification that
    RFC-CLE004 §3's homotopy-novelty / persistence-decay conditions hold —
    they trust that whatever assigned `node_id`s upstream already made
    that judgment.
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
    """RFC-CLE004 §5's `CategoryEvolutionTrackingProtocol`, in full."""

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

    def trace_lineage(
        self,
        node_id: str,
        event_log: tuple[EvolutionEvent, ...],
        *,
        depth: int,
    ) -> tuple[AncestryLink, ...]: ...


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _saturating_confidence(evidence: float, half_life: float) -> float:
    """Monotonically increasing in `evidence`, bounded to `[0, 1)`.

    Same saturating shape as `cle.commit_candidate`'s confidence formula,
    reimplemented locally rather than imported: it is a different module's
    private detail, and duplicating a few lines keeps `cle.evolution`
    removable without touching `cle.commit_candidate`.
    """
    return evidence / (evidence + half_life)


def _proximity_confidence(average_distance: float, tolerance: float) -> float:
    """Monotonically *decreasing* in `average_distance`, bounded to `[0, 1]`.

    Opposite shape from `_saturating_confidence` on purpose: a MERGE/SPLIT
    hypothesis gets *more* credible the *closer* the observed centroids are
    to the merge/split point, not less. `1.0 - average_distance / tolerance`
    is `1.0` at zero distance and `0.0` exactly at the tolerance boundary —
    values beyond the boundary are never passed in, since the grouping step
    that calls this only admits candidates already within `tolerance`.
    """
    return max(0.0, 1.0 - average_distance / tolerance)


@dataclass(frozen=True, slots=True)
class GeometricEvolutionTracker:
    """`BIRTH`/`DEATH`/`MERGE`/`SPLIT`/`DRIFT` detection from two `NodeState` snapshots.

    - `BIRTH`: a node id in `current_nodes` but not `previous_nodes`, not
      claimed by a `MERGE`/`SPLIT` below.
    - `DEATH`: a node id in `previous_nodes` but not `current_nodes`, not
      claimed by a `MERGE`/`SPLIT` below.
    - `DRIFT`: a node id present in both, whose centroid moved more than
      `drift_tolerance`.
    - `MERGE`: **heuristic**, not a verified pushout. Two or more died node
      ids whose centroids each have the *same* born node id as their
      nearest neighbor, within `merge_split_tolerance`, are reported as
      merging into it. This is a proximity coincidence, not confirmation
      that a real categorical pushout occurred — `NodeState` carries no
      trajectory data to verify that. Disabled by default
      (`merge_split_tolerance=0.0`): merge/split inference is opt-in.
    - `SPLIT`: **heuristic**, the mirror of `MERGE` — one died node id
      whose centroid is the nearest died neighbor of two or more born node
      ids, within `merge_split_tolerance`.

    Every died/born id can be claimed by at most one `MERGE` or `SPLIT`;
    whatever remains unclaimed becomes plain `DEATH`/`BIRTH`. `MERGE` is
    resolved before `SPLIT`, so an id cannot appear in both.

    `BIRTH`/`DEATH` get `confidence_score=1.0` — presence or absence in a
    `NodeState` sequence is a hard fact. `DRIFT`'s confidence saturates
    *upward* with distance past `drift_tolerance` (more movement is more
    evidence it is real drift, not noise). `MERGE`/`SPLIT`'s confidence
    saturates *downward* with distance from the exact merge/split point
    (closer centroids are stronger evidence for the heuristic's
    hypothesis) — `_saturating_confidence` and `_proximity_confidence` are
    deliberately different shapes for this reason, not one formula reused
    two ways.

    Returned events are sorted by `(event_type, source_node_ids,
    target_node_ids)`, independent of `previous_nodes`/`current_nodes`
    iteration order or of Python's hash-randomized set iteration — verified
    directly (same output across four different `PYTHONHASHSEED` values in
    the Phase 4 architecture review).

    `timestamp_utc` comes from an injectable `clock_utc` callable (default:
    real UTC time). `event_id`/`snapshot_id` are always derived only from
    semantic content, never from `timestamp_utc` — verified directly
    (two trackers with different injected clocks produce identical
    `event_id`s and different `timestamp_utc`s for the same detection).

    `apply_events`'s `snapshot_id` depends on the order of the `events`
    tuple it is given — a documented precondition, not a bug: it expects
    `events` in the order `detect_evolution` returns them (its own
    determinism contract is order-*independent* of the input `NodeState`
    sequences, but the *output* order is itself part of `apply_events`'
    input contract). `MERGE`/`SPLIT` events change `active_node_ids`
    exactly like `BIRTH`/`DEATH` do (sources removed, targets added) —
    `DRIFT` never changes it.
    """

    drift_tolerance: float = 0.0
    merge_split_tolerance: float = 0.0
    clock_utc: Callable[[], str] = field(default=_utc_now)

    def __post_init__(self) -> None:
        if self.drift_tolerance < 0.0:
            raise ValueError("drift_tolerance must be greater than or equal to zero")
        if self.merge_split_tolerance < 0.0:
            raise ValueError(
                "merge_split_tolerance must be greater than or equal to zero"
            )

    def detect_evolution(
        self,
        previous_nodes: tuple[NodeState, ...],
        current_nodes: tuple[NodeState, ...],
    ) -> tuple[EvolutionEvent, ...]:
        previous_by_id = {node.node_id: node for node in previous_nodes}
        current_by_id = {node.node_id: node for node in current_nodes}
        timestamp = self.clock_utc()

        died = previous_by_id.keys() - current_by_id.keys()
        born = current_by_id.keys() - previous_by_id.keys()
        persisted = previous_by_id.keys() & current_by_id.keys()

        merges: list[EvolutionEvent] = []
        splits: list[EvolutionEvent] = []
        claimed_died: set[str] = set()
        claimed_born: set[str] = set()
        if self.merge_split_tolerance > 0.0:
            merges, claimed_died, claimed_born = self._detect_merges(
                died, born, previous_by_id, current_by_id, timestamp
            )
            splits, split_died, split_born = self._detect_splits(
                died - claimed_died,
                born - claimed_born,
                previous_by_id,
                current_by_id,
                timestamp,
            )
            claimed_died |= split_died
            claimed_born |= split_born

        events: list[EvolutionEvent] = [*merges, *splits]
        events += [self._birth(node_id, timestamp) for node_id in born - claimed_born]
        events += [self._death(node_id, timestamp) for node_id in died - claimed_died]
        for node_id in persisted:
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
            active -= set(event.source_node_ids)
            active |= set(event.target_node_ids)
        return LineageSnapshot(
            # Hash on each event's own `event_id` (already timestamp-free),
            # not the `EvolutionEvent` objects themselves: their `repr()`
            # includes `timestamp_utc`, which would otherwise couple
            # `snapshot_id` to wall-clock time.
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

    def trace_lineage(
        self,
        node_id: str,
        event_log: tuple[EvolutionEvent, ...],
        *,
        depth: int = 10,
    ) -> tuple[AncestryLink, ...]:
        """Walk backward from `node_id` through `event_log`'s ancestry links.

        Only `BIRTH`/`MERGE`/`SPLIT` events assign identity (a `target_node_id`
        that did not exist before); `DEATH` removes identity and `DRIFT`
        preserves it without creating ancestry, so neither is indexed here.
        Breadth-first, cycle-safe (a `parent_node_id` already visited is
        never re-queued — RFC-CLE004 §6's DAG assumption, not verified
        here), bounded to `depth` hops, matching RFC-CLE004 §5's default.
        """
        events_by_target: dict[str, list[EvolutionEvent]] = {}
        for event in event_log:
            if event.event_type in (
                EvolutionEventType.BIRTH,
                EvolutionEventType.MERGE,
                EvolutionEventType.SPLIT,
            ):
                for target_id in event.target_node_ids:
                    events_by_target.setdefault(target_id, []).append(event)

        collected: list[AncestryLink] = []
        visited = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for current_id in sorted(frontier):
                for event in events_by_target.get(current_id, ()):
                    for link in event.ancestry_links:
                        collected.append(link)
                        if link.parent_node_id not in visited:
                            next_frontier.add(link.parent_node_id)
            visited |= next_frontier
            frontier = next_frontier

        return tuple(
            sorted(
                collected,
                key=lambda link: (link.parent_node_id, link.morphism_type),
            )
        )

    def _nearest(
        self,
        centroid: Vector,
        candidate_ids: set[str],
        lookup_by_id: dict[str, NodeState],
    ) -> tuple[str | None, float]:
        best_id: str | None = None
        best_distance = math.inf
        for candidate_id in sorted(candidate_ids):
            distance = euclidean_distance(centroid, lookup_by_id[candidate_id].centroid)
            if distance < best_distance:
                best_distance = distance
                best_id = candidate_id
        return best_id, best_distance

    def _detect_merges(
        self,
        died: set[str],
        born: set[str],
        previous_by_id: dict[str, NodeState],
        current_by_id: dict[str, NodeState],
        timestamp: str,
    ) -> tuple[list[EvolutionEvent], set[str], set[str]]:
        if not died or not born:
            return [], set(), set()

        groups: dict[str, list[str]] = {}
        for died_id in sorted(died):
            nearest_born_id, distance = self._nearest(
                previous_by_id[died_id].centroid, born, current_by_id
            )
            if nearest_born_id is not None and distance <= self.merge_split_tolerance:
                groups.setdefault(nearest_born_id, []).append(died_id)

        merges: list[EvolutionEvent] = []
        claimed_died: set[str] = set()
        claimed_born: set[str] = set()
        for target_id, source_ids in sorted(groups.items()):
            if len(source_ids) < 2:
                continue
            merges.append(
                self._merge(
                    sorted(source_ids),
                    target_id,
                    previous_by_id,
                    current_by_id,
                    timestamp,
                )
            )
            claimed_died.update(source_ids)
            claimed_born.add(target_id)
        return merges, claimed_died, claimed_born

    def _detect_splits(
        self,
        died: set[str],
        born: set[str],
        previous_by_id: dict[str, NodeState],
        current_by_id: dict[str, NodeState],
        timestamp: str,
    ) -> tuple[list[EvolutionEvent], set[str], set[str]]:
        if not died or not born:
            return [], set(), set()

        groups: dict[str, list[str]] = {}
        for born_id in sorted(born):
            nearest_died_id, distance = self._nearest(
                current_by_id[born_id].centroid, died, previous_by_id
            )
            if nearest_died_id is not None and distance <= self.merge_split_tolerance:
                groups.setdefault(nearest_died_id, []).append(born_id)

        splits: list[EvolutionEvent] = []
        claimed_died: set[str] = set()
        claimed_born: set[str] = set()
        for source_id, target_ids in sorted(groups.items()):
            if len(target_ids) < 2:
                continue
            splits.append(
                self._split(
                    source_id,
                    sorted(target_ids),
                    previous_by_id,
                    current_by_id,
                    timestamp,
                )
            )
            claimed_died.add(source_id)
            claimed_born.update(target_ids)
        return splits, claimed_died, claimed_born

    def _merge(
        self,
        source_ids: list[str],
        target_id: str,
        previous_by_id: dict[str, NodeState],
        current_by_id: dict[str, NodeState],
        timestamp: str,
    ) -> EvolutionEvent:
        target_centroid = current_by_id[target_id].centroid
        distances = [
            euclidean_distance(previous_by_id[sid].centroid, target_centroid)
            for sid in source_ids
        ]
        average_distance = sum(distances) / len(distances)
        weight = 1.0 / len(source_ids)
        return EvolutionEvent(
            event_id=deterministic_id(
                "evolution", "merge", tuple(source_ids), target_id
            ),
            event_type=EvolutionEventType.MERGE,
            source_node_ids=tuple(source_ids),
            target_node_ids=(target_id,),
            ancestry_links=tuple(
                AncestryLink(
                    parent_node_id=sid,
                    morphism_type=MorphismType.PUSHOUT_CANONICAL,
                    weight=weight,
                )
                for sid in source_ids
            ),
            betti_delta=(),
            confidence_score=_proximity_confidence(
                average_distance, self.merge_split_tolerance
            ),
            timestamp_utc=timestamp,
            metadata={
                "average_distance": average_distance,
                "tolerance": self.merge_split_tolerance,
            },
        )

    def _split(
        self,
        source_id: str,
        target_ids: list[str],
        previous_by_id: dict[str, NodeState],
        current_by_id: dict[str, NodeState],
        timestamp: str,
    ) -> EvolutionEvent:
        source_centroid = previous_by_id[source_id].centroid
        distances = [
            euclidean_distance(source_centroid, current_by_id[tid].centroid)
            for tid in target_ids
        ]
        average_distance = sum(distances) / len(distances)
        return EvolutionEvent(
            event_id=deterministic_id(
                "evolution", "split", source_id, tuple(target_ids)
            ),
            event_type=EvolutionEventType.SPLIT,
            source_node_ids=(source_id,),
            target_node_ids=tuple(target_ids),
            ancestry_links=tuple(
                AncestryLink(
                    parent_node_id=source_id,
                    morphism_type=MorphismType.PULLBACK_CANONICAL,
                    weight=1.0,
                )
                for _ in target_ids
            ),
            betti_delta=(),
            confidence_score=_proximity_confidence(
                average_distance, self.merge_split_tolerance
            ),
            timestamp_utc=timestamp,
            metadata={
                "average_distance": average_distance,
                "tolerance": self.merge_split_tolerance,
            },
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
            confidence_score=_saturating_confidence(distance, self.drift_tolerance),
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
