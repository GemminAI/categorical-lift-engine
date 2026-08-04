"""`GeometricEvolutionTracker` — Category Evolution Tracking (RFC-CLE004, Phase 4).

Experimental module (see `cle.evolution`'s own docstring and
`docs/RFC_ALIGNMENT.md`): all five `EvolutionEventType`s, `apply_events`,
and `trace_lineage` are covered.
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


def _tracker(
    drift_tolerance: float = 0.0, merge_split_tolerance: float = 0.0
) -> GeometricEvolutionTracker:
    return GeometricEvolutionTracker(
        drift_tolerance=drift_tolerance,
        merge_split_tolerance=merge_split_tolerance,
        clock_utc=lambda: _FIXED_TIME,
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


def test_negative_merge_split_tolerance_is_rejected_at_construction() -> None:
    with pytest.raises(
        ValueError, match="merge_split_tolerance must be greater than or equal to zero"
    ):
        GeometricEvolutionTracker(merge_split_tolerance=-1.0)


# --- detect_evolution: MERGE -------------------------------------------------


def test_two_dying_nodes_near_one_born_node_are_a_merge() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (
        NodeState(node_id="a", centroid=(0.0, 0.0)),
        NodeState(node_id="b", centroid=(1.0, 0.0)),
    )
    current = (NodeState(node_id="c", centroid=(0.5, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    (event,) = events
    assert event.event_type is EvolutionEventType.MERGE
    assert event.source_node_ids == ("a", "b")
    assert event.target_node_ids == ("c",)


def test_merge_ancestry_links_split_weight_equally_among_parents() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (
        NodeState(node_id="a", centroid=(0.0, 0.0)),
        NodeState(node_id="b", centroid=(1.0, 0.0)),
    )
    current = (NodeState(node_id="c", centroid=(0.5, 0.0)),)

    (event,) = tracker.detect_evolution(previous, current)

    assert len(event.ancestry_links) == 2
    assert {link.parent_node_id for link in event.ancestry_links} == {"a", "b"}
    assert all(link.weight == 0.5 for link in event.ancestry_links)
    assert all(
        link.morphism_type is MorphismType.PUSHOUT_CANONICAL
        for link in event.ancestry_links
    )


def test_merge_confidence_decreases_with_average_distance() -> None:
    def confidence_for(offset: float) -> float:
        tracker = _tracker(merge_split_tolerance=2.0)
        previous = (
            NodeState(node_id="a", centroid=(-offset, 0.0)),
            NodeState(node_id="b", centroid=(offset, 0.0)),
        )
        current = (NodeState(node_id="c", centroid=(0.0, 0.0)),)
        (event,) = tracker.detect_evolution(previous, current)
        return event.confidence_score

    confidences = [confidence_for(offset) for offset in (0.1, 0.5, 1.0, 1.9)]

    # Larger offset -> larger average distance -> lower confidence.
    assert confidences == sorted(confidences, reverse=True)
    assert len(set(confidences)) == len(confidences)
    assert all(0.0 <= c <= 1.0 for c in confidences)


def test_single_dying_node_near_a_born_node_is_not_a_merge() -> None:
    # Only one parent candidate: this is a coincidental DEATH + BIRTH, not
    # a merge (a merge requires >= 2 sources by definition).
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (NodeState(node_id="a", centroid=(0.0, 0.0)),)
    current = (NodeState(node_id="c", centroid=(0.1, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    event_types = {event.event_type for event in events}
    assert EvolutionEventType.MERGE not in event_types
    assert event_types == {EvolutionEventType.DEATH, EvolutionEventType.BIRTH}


def test_merge_split_tolerance_zero_disables_merge_detection() -> None:
    tracker = _tracker(merge_split_tolerance=0.0)
    previous = (
        NodeState(node_id="a", centroid=(0.0, 0.0)),
        NodeState(node_id="b", centroid=(0.01, 0.0)),
    )
    current = (NodeState(node_id="c", centroid=(0.005, 0.0)),)

    events = tracker.detect_evolution(previous, current)

    event_types = {event.event_type for event in events}
    assert EvolutionEventType.MERGE not in event_types
    assert event_types == {EvolutionEventType.DEATH, EvolutionEventType.BIRTH}


# --- detect_evolution: SPLIT -------------------------------------------------


def test_one_dying_node_near_two_born_nodes_is_a_split() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (NodeState(node_id="a", centroid=(0.5, 0.0)),)
    current = (
        NodeState(node_id="b", centroid=(0.0, 0.0)),
        NodeState(node_id="c", centroid=(1.0, 0.0)),
    )

    events = tracker.detect_evolution(previous, current)

    assert len(events) == 1
    (event,) = events
    assert event.event_type is EvolutionEventType.SPLIT
    assert event.source_node_ids == ("a",)
    assert event.target_node_ids == ("b", "c")


def test_split_ancestry_links_each_carry_full_weight() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (NodeState(node_id="a", centroid=(0.5, 0.0)),)
    current = (
        NodeState(node_id="b", centroid=(0.0, 0.0)),
        NodeState(node_id="c", centroid=(1.0, 0.0)),
    )

    (event,) = tracker.detect_evolution(previous, current)

    assert len(event.ancestry_links) == 2
    assert all(link.parent_node_id == "a" for link in event.ancestry_links)
    assert all(link.weight == 1.0 for link in event.ancestry_links)
    assert all(
        link.morphism_type is MorphismType.PULLBACK_CANONICAL
        for link in event.ancestry_links
    )


def test_merge_is_resolved_before_split_so_ids_are_not_double_claimed() -> None:
    # a merges into c; d splits into e/f. Distinct groups, no id shared.
    tracker = _tracker(merge_split_tolerance=1.0)
    previous = (
        NodeState(node_id="a1", centroid=(0.0, 0.0)),
        NodeState(node_id="a2", centroid=(1.0, 0.0)),
        NodeState(node_id="d", centroid=(10.5, 0.0)),
    )
    current = (
        NodeState(node_id="c", centroid=(0.5, 0.0)),
        NodeState(node_id="e", centroid=(10.0, 0.0)),
        NodeState(node_id="f", centroid=(11.0, 0.0)),
    )

    events = tracker.detect_evolution(previous, current)

    event_types = [event.event_type for event in events]
    assert event_types.count(EvolutionEventType.MERGE) == 1
    assert event_types.count(EvolutionEventType.SPLIT) == 1
    merge_event = next(e for e in events if e.event_type is EvolutionEventType.MERGE)
    split_event = next(e for e in events if e.event_type is EvolutionEventType.SPLIT)
    assert merge_event.source_node_ids == ("a1", "a2")
    assert split_event.target_node_ids == ("e", "f")


# --- apply_events with MERGE / SPLIT -----------------------------------------


def test_apply_events_consolidates_merge_sources_into_target() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("a", "b")
    )
    previous_nodes = (
        NodeState(node_id="a", centroid=(0.0, 0.0)),
        NodeState(node_id="b", centroid=(1.0, 0.0)),
    )
    current_nodes = (NodeState(node_id="c", centroid=(0.5, 0.0)),)
    events = tracker.detect_evolution(previous_nodes, current_nodes)

    new_snapshot = tracker.apply_events(previous_snapshot, events)

    assert new_snapshot.active_node_ids == ("c",)


def test_apply_events_distributes_split_source_into_targets() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    previous_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME, active_node_ids=("a",)
    )
    previous_nodes = (NodeState(node_id="a", centroid=(0.5, 0.0)),)
    current_nodes = (
        NodeState(node_id="b", centroid=(0.0, 0.0)),
        NodeState(node_id="c", centroid=(1.0, 0.0)),
    )
    events = tracker.detect_evolution(previous_nodes, current_nodes)

    new_snapshot = tracker.apply_events(previous_snapshot, events)

    assert set(new_snapshot.active_node_ids) == {"b", "c"}


# --- trace_lineage ------------------------------------------------------------


def test_trace_lineage_of_a_birth_is_empty() -> None:
    tracker = _tracker()
    birth = tracker._birth("root", _FIXED_TIME)

    links = tracker.trace_lineage("root", (birth,))

    assert links == ()


def test_trace_lineage_follows_a_merge_to_its_parents() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    birth_a = tracker._birth("a", _FIXED_TIME)
    birth_b = tracker._birth("b", _FIXED_TIME)
    merge = tracker._merge(
        ["a", "b"],
        "c",
        {"a": NodeState("a", (0.0, 0.0)), "b": NodeState("b", (1.0, 0.0))},
        {"c": NodeState("c", (0.5, 0.0))},
        _FIXED_TIME,
    )

    links = tracker.trace_lineage("c", (birth_a, birth_b, merge))

    assert {link.parent_node_id for link in links} == {"a", "b"}


def test_trace_lineage_follows_multi_generation_chain() -> None:
    # a --split--> b, c ; b --merge(with d)--> e
    tracker = _tracker(merge_split_tolerance=1.0)
    split = tracker._split(
        "a",
        ["b", "c"],
        {"a": NodeState("a", (0.0, 0.0))},
        {"b": NodeState("b", (-1.0, 0.0)), "c": NodeState("c", (1.0, 0.0))},
        _FIXED_TIME,
    )
    birth_d = tracker._birth("d", _FIXED_TIME)
    merge = tracker._merge(
        ["b", "d"],
        "e",
        {"b": NodeState("b", (-1.0, 0.0)), "d": NodeState("d", (5.0, 0.0))},
        {"e": NodeState("e", (2.0, 0.0))},
        _FIXED_TIME,
    )

    links = tracker.trace_lineage("e", (split, birth_d, merge), depth=10)

    assert {link.parent_node_id for link in links} == {"a", "b", "d"}


def test_trace_lineage_respects_depth_limit() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    split = tracker._split(
        "a",
        ["b", "c"],
        {"a": NodeState("a", (0.0, 0.0))},
        {"b": NodeState("b", (-1.0, 0.0)), "c": NodeState("c", (1.0, 0.0))},
        _FIXED_TIME,
    )
    birth_d = tracker._birth("d", _FIXED_TIME)
    merge = tracker._merge(
        ["b", "d"],
        "e",
        {"b": NodeState("b", (-1.0, 0.0)), "d": NodeState("d", (5.0, 0.0))},
        {"e": NodeState("e", (2.0, 0.0))},
        _FIXED_TIME,
    )

    shallow = tracker.trace_lineage("e", (split, birth_d, merge), depth=1)
    deep = tracker.trace_lineage("e", (split, birth_d, merge), depth=10)

    assert {link.parent_node_id for link in shallow} == {"b", "d"}
    assert {link.parent_node_id for link in deep} == {"a", "b", "d"}


def test_trace_lineage_is_deterministic() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)
    birth_a = tracker._birth("a", _FIXED_TIME)
    birth_b = tracker._birth("b", _FIXED_TIME)
    merge = tracker._merge(
        ["a", "b"],
        "c",
        {"a": NodeState("a", (0.0, 0.0)), "b": NodeState("b", (1.0, 0.0))},
        {"c": NodeState("c", (0.5, 0.0))},
        _FIXED_TIME,
    )

    first = tracker.trace_lineage("c", (birth_a, birth_b, merge))
    second = tracker.trace_lineage("c", (birth_a, birth_b, merge))

    assert first == second


def test_trace_lineage_of_unknown_node_is_empty() -> None:
    tracker = _tracker()

    assert tracker.trace_lineage("nonexistent", ()) == ()


def test_trace_lineage_ignores_death_and_drift_events() -> None:
    # DEATH/DRIFT never assign a new identity, so they must not be indexed
    # as ancestry-producing events.
    tracker = _tracker()
    birth = tracker._birth("a", _FIXED_TIME)
    death = tracker._death("z", _FIXED_TIME)
    drift = tracker._drift(
        "a", NodeState("a", (0.0, 0.0)), NodeState("a", (5.0, 0.0)), _FIXED_TIME
    )
    assert drift is not None

    links = tracker.trace_lineage("a", (birth, death, drift))

    assert links == ()


def test_trace_lineage_does_not_requeue_an_already_visited_ancestor() -> None:
    # Synthetic log (not a physically realistic single evolution history) —
    # built purely to exercise the revisit guard: "a" is reachable directly
    # from "c" (depth 1) and again from "b" (depth 2). The guard must skip
    # re-queuing "a" the second time without breaking traversal past it: "y"
    # (reachable only via "b") must still be found.
    tracker = _tracker(merge_split_tolerance=1.0)

    def node(node_id: str, x: float) -> NodeState:
        return NodeState(node_id, (x, 0.0))

    birth_a = tracker._birth("a", _FIXED_TIME)
    birth_y = tracker._birth("y", _FIXED_TIME)
    merge_b = tracker._merge(
        ["a", "y"],
        "b",
        {"a": node("a", 0.0), "y": node("y", 2.0)},
        {"b": node("b", 1.0)},
        _FIXED_TIME,
    )
    merge_c = tracker._merge(
        ["a", "b"],
        "c",
        {"a": node("a", 0.0), "b": node("b", 1.0)},
        {"c": node("c", 0.5)},
        _FIXED_TIME,
    )

    links = tracker.trace_lineage("c", (birth_a, birth_y, merge_b, merge_c), depth=10)

    assert {link.parent_node_id for link in links} == {"a", "b", "y"}


# --- coverage: merge/split boundary branches ---------------------------------


def test_merge_and_split_detection_is_skipped_with_only_births() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)

    current = (NodeState(node_id="a", centroid=(0.0, 0.0)),)
    events = tracker.detect_evolution((), current)

    assert len(events) == 1
    assert events[0].event_type is EvolutionEventType.BIRTH


def test_merge_and_split_detection_is_skipped_with_only_deaths() -> None:
    tracker = _tracker(merge_split_tolerance=1.0)

    previous = (NodeState(node_id="a", centroid=(0.0, 0.0)),)
    events = tracker.detect_evolution(previous, ())

    assert len(events) == 1
    assert events[0].event_type is EvolutionEventType.DEATH


def test_merge_finds_no_group_when_all_candidates_are_out_of_tolerance() -> None:
    tracker = _tracker(merge_split_tolerance=0.5)
    previous = (
        NodeState(node_id="a", centroid=(0.0, 0.0)),
        NodeState(node_id="b", centroid=(1.0, 0.0)),
    )
    current = (NodeState(node_id="c", centroid=(100.0, 100.0)),)

    events = tracker.detect_evolution(previous, current)

    event_types = {event.event_type for event in events}
    assert EvolutionEventType.MERGE not in event_types
    assert event_types == {EvolutionEventType.DEATH, EvolutionEventType.BIRTH}


def test_split_finds_no_group_when_all_candidates_are_out_of_tolerance() -> None:
    tracker = _tracker(merge_split_tolerance=0.5)
    previous = (NodeState(node_id="a", centroid=(0.0, 0.0)),)
    current = (
        NodeState(node_id="b", centroid=(100.0, 0.0)),
        NodeState(node_id="c", centroid=(200.0, 0.0)),
    )

    events = tracker.detect_evolution(previous, current)

    event_types = {event.event_type for event in events}
    assert EvolutionEventType.SPLIT not in event_types
    assert event_types == {EvolutionEventType.DEATH, EvolutionEventType.BIRTH}
