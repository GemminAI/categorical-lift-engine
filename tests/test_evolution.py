"""`GeometricEvolutionTracker` — Category Evolution Tracking (RFC-CLE004, Phase 4).

Experimental module (see `cle.evolution`'s own docstring and
`docs/RFC_ALIGNMENT.md`): this milestone covers BIRTH/DEATH/DRIFT detection
and snapshot replay only. MERGE/SPLIT/trace_lineage are deferred.
"""

from __future__ import annotations

import pytest

from cle.abi.outputs import MorphismType
from cle.evolution import (
    AncestryLink,
    CategoryEvolutionTracker,
    EvolutionEvent,
    EvolutionEventType,
    GeometricEvolutionTracker,
    LineageSnapshot,
    NodeState,
)

_FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _tracker(drift_tolerance: float = 0.0) -> GeometricEvolutionTracker:
    return GeometricEvolutionTracker(
        drift_tolerance=drift_tolerance, clock_utc=lambda: _FIXED_TIME
    )


def test_tracker_satisfies_the_protocol() -> None:
    assert isinstance(_tracker(), CategoryEvolutionTracker)


# --- shape / construction ---------------------------------------------------


def test_node_state_is_a_plain_id_and_position() -> None:
    node = NodeState(node_id="n1", centroid=(1.0, 2.0))
    assert node.node_id == "n1"
    assert node.centroid == (1.0, 2.0)


def test_ancestry_link_reuses_morphism_type() -> None:
    link = AncestryLink(
        parent_node_id="p1", morphism_type=MorphismType.INCLUSION, weight=1.0
    )
    assert link.morphism_type is MorphismType.INCLUSION


def test_lineage_snapshot_defaults() -> None:
    snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("n1",)
    )
    assert snapshot.active_morphism_ids == ()
    assert snapshot.parent_snapshot_id is None


def test_evolution_event_rejects_out_of_bounds_confidence() -> None:
    with pytest.raises(ValueError, match=r"confidence_score must be in \[0.0, 1.0\]"):
        EvolutionEvent(
            event_id="e1",
            event_type=EvolutionEventType.BIRTH,
            source_node_ids=(),
            target_node_ids=("n1",),
            ancestry_links=(),
            betti_delta=(),
            confidence_score=1.5,
            timestamp_utc=_FIXED_TIME,
        )


def test_all_five_evolution_event_types_are_named() -> None:
    # RFC-CLE004 §4's full taxonomy is declared even though only three are
    # producible this milestone.
    assert {member.value for member in EvolutionEventType} == {
        "birth",
        "death",
        "merge",
        "split",
        "drift",
    }


# --- detect_evolution: BIRTH / DEATH ----------------------------------------


def test_new_node_is_a_birth_event() -> None:
    tracker = _tracker()
    previous = ()
    current = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    (event,) = events
    assert event.event_type is EvolutionEventType.BIRTH
    assert event.source_node_ids == ()
    assert event.target_node_ids == ("n1",)
    assert event.confidence_score == 1.0


def test_removed_node_is_a_death_event() -> None:
    tracker = _tracker()
    previous = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    current = ()

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    (event,) = events
    assert event.event_type is EvolutionEventType.DEATH
    assert event.source_node_ids == ("n1",)
    assert event.target_node_ids == ()
    assert event.confidence_score == 1.0


def test_unchanged_node_yields_no_events() -> None:
    tracker = _tracker()
    nodes = (NodeState(node_id="n1", centroid=(1.0, 1.0)),)

    events = tracker.detect_evolution(nodes, nodes)

    assert events == ()


# --- detect_evolution: DRIFT -------------------------------------------------


def test_moved_node_beyond_tolerance_is_a_drift_event() -> None:
    tracker = _tracker(drift_tolerance=0.5)
    previous = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    current = (NodeState(node_id="n1", centroid=(1.0, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    (event,) = events
    assert event.event_type is EvolutionEventType.DRIFT
    assert event.source_node_ids == ("n1",)
    assert event.target_node_ids == ("n1",)
    assert event.metadata["distance"] == 1.0
    assert event.metadata["tolerance"] == 0.5


def test_movement_exactly_at_tolerance_is_not_drift() -> None:
    # Boundary is inclusive on the "no drift" side: distance <= tolerance.
    tracker = _tracker(drift_tolerance=1.0)
    previous = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    current = (NodeState(node_id="n1", centroid=(1.0, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    assert events == ()


def test_zero_tolerance_flags_any_movement() -> None:
    tracker = _tracker(drift_tolerance=0.0)
    previous = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    current = (NodeState(node_id="n1", centroid=(1e-6, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    assert events[0].event_type is EvolutionEventType.DRIFT
    assert events[0].confidence_score == 1.0


def test_drift_confidence_increases_with_distance_beyond_tolerance() -> None:
    tracker = _tracker(drift_tolerance=1.0)

    def confidence_for(distance: float) -> float:
        previous = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
        current = (NodeState(node_id="n1", centroid=(distance, 0.0)),)
        (event,) = tracker.detect_evolution(previous, current)
        return event.confidence_score

    confidences = [confidence_for(d) for d in (1.1, 2.0, 10.0, 1000.0)]

    assert confidences == sorted(confidences)
    assert len(set(confidences)) == len(confidences)
    assert all(0.0 <= c <= 1.0 for c in confidences)


def test_no_drift_when_no_tolerance_configured_and_no_movement() -> None:
    tracker = _tracker(drift_tolerance=0.0)
    nodes = (NodeState(node_id="n1", centroid=(5.0, 5.0)),)

    events = tracker.detect_evolution(nodes, nodes)

    assert events == ()


# --- determinism -------------------------------------------------------------


def test_detection_is_deterministic() -> None:
    tracker = _tracker(drift_tolerance=0.1)
    previous = (
        NodeState(node_id="n1", centroid=(0.0, 0.0)),
        NodeState(node_id="n2", centroid=(5.0, 5.0)),
    )
    current = (
        NodeState(node_id="n1", centroid=(1.0, 0.0)),  # drift
        NodeState(node_id="n3", centroid=(9.0, 9.0)),  # birth (n2 died)
    )

    first = tracker.detect_evolution(previous, current)
    second = tracker.detect_evolution(previous, current)

    assert first == second


def test_event_order_does_not_depend_on_input_order() -> None:
    tracker = _tracker(drift_tolerance=0.1)
    previous = (
        NodeState(node_id="n1", centroid=(0.0, 0.0)),
        NodeState(node_id="n2", centroid=(5.0, 5.0)),
    )
    current_forward = (
        NodeState(node_id="n1", centroid=(1.0, 0.0)),
        NodeState(node_id="n3", centroid=(9.0, 9.0)),
    )
    current_reversed = tuple(reversed(current_forward))

    forward = tracker.detect_evolution(previous, current_forward)
    reversed_result = tracker.detect_evolution(
        tuple(reversed(previous)), current_reversed
    )

    assert forward == reversed_result


def test_event_id_is_deterministic_and_excludes_timestamp() -> None:
    tracker_a = GeometricEvolutionTracker(clock_utc=lambda: "2026-01-01T00:00:00+00:00")
    tracker_b = GeometricEvolutionTracker(clock_utc=lambda: "2099-12-31T23:59:59+00:00")
    current = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)

    (event_a,) = tracker_a.detect_evolution((), current)
    (event_b,) = tracker_b.detect_evolution((), current)

    assert event_a.event_id == event_b.event_id
    assert event_a.timestamp_utc != event_b.timestamp_utc


# --- apply_events -------------------------------------------------------------


def test_apply_events_adds_births_and_removes_deaths() -> None:
    tracker = _tracker()
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("n1", "n2")
    )
    previous_nodes = (
        NodeState(node_id="n1", centroid=(0.0, 0.0)),
        NodeState(node_id="n2", centroid=(0.0, 0.0)),
    )
    current_nodes = (
        NodeState(node_id="n1", centroid=(0.0, 0.0)),
        NodeState(node_id="n3", centroid=(0.0, 0.0)),
    )
    events = tracker.detect_evolution(previous_nodes, current_nodes)

    new_snapshot = tracker.apply_events(previous_snapshot, events)

    assert set(new_snapshot.active_node_ids) == {"n1", "n3"}
    assert new_snapshot.parent_snapshot_id == "s0"


def test_apply_events_is_unaffected_by_drift() -> None:
    tracker = _tracker(drift_tolerance=0.1)
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("n1",)
    )
    previous_nodes = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    current_nodes = (NodeState(node_id="n1", centroid=(1.0, 0.0)),)
    events = tracker.detect_evolution(previous_nodes, current_nodes)
    assert events[0].event_type is EvolutionEventType.DRIFT

    new_snapshot = tracker.apply_events(previous_snapshot, events)

    assert new_snapshot.active_node_ids == ("n1",)


def test_apply_events_preserves_morphism_ids() -> None:
    tracker = _tracker()
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0",
        timestamp_utc=_FIXED_TIME,
        active_node_ids=("n1",),
        active_morphism_ids=("m1",),
    )

    new_snapshot = tracker.apply_events(previous_snapshot, ())

    assert new_snapshot.active_morphism_ids == ("m1",)
    assert new_snapshot.active_node_ids == ("n1",)


def test_apply_events_is_deterministic() -> None:
    tracker = _tracker()
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("n1",)
    )
    events = tracker.detect_evolution(
        (NodeState(node_id="n1", centroid=(0.0, 0.0)),),
        (NodeState(node_id="n2", centroid=(0.0, 0.0)),),
    )

    first = tracker.apply_events(previous_snapshot, events)
    second = tracker.apply_events(previous_snapshot, events)

    assert first == second


# --- configuration validation -------------------------------------------------


def test_negative_drift_tolerance_is_rejected_at_construction() -> None:
    with pytest.raises(
        ValueError, match="drift_tolerance must be greater than or equal to zero"
    ):
        GeometricEvolutionTracker(drift_tolerance=-1.0)


def test_zero_drift_tolerance_is_accepted() -> None:
    tracker = GeometricEvolutionTracker(drift_tolerance=0.0)
    assert tracker.drift_tolerance == 0.0


def test_default_clock_is_a_real_utc_timestamp() -> None:
    import datetime as datetime_module

    tracker = GeometricEvolutionTracker()
    before = datetime_module.datetime.now(datetime_module.UTC)

    current = (NodeState(node_id="n1", centroid=(0.0, 0.0)),)
    (event,) = tracker.detect_evolution((), current)

    parsed = datetime_module.datetime.fromisoformat(event.timestamp_utc)
    assert parsed >= before
