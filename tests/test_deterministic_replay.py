"""RFC-CLE005 §3.2 / end-to-end pipeline validation.

The first test in this repository that wires all four implemented phases
into one call chain: Phase 1 (object + morphism lifting) -> Phase 2
(topology) -> Phase 3 (crystallization -> delta -> commit candidate) ->
Phase 4 (evolution detection -> snapshot replay). Every prior test exercised
exactly one phase's concrete classes in isolation; nothing before this
proved the full chain composes and stays deterministic end to end.

"Same input -> same output" is checked at *every* stage, not just the
final one — a bug that cancels itself out by the last step would pass a
final-output-only check and still be a real bug.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cle.abi.outputs import Concept
from cle.commit_candidate import ObservationalCommitCandidateBuilder
from cle.concept import FunctorialConceptLift
from cle.crystallization import ProvenanceCanonicalizingCrystallizer
from cle.evolution import GeometricEvolutionTracker, LineageSnapshot, NodeState
from cle.homotopy import EpsilonGraphBettiAnalyzer
from cle.knowledge_delta import ArtifactKnowledgeDeltaGenerator
from cle.morphism import IdentityInclusionMorphismLift

Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]

_FIXED_TIME_NS = 1_700_000_000_000_000_000
_FIXED_TIME_UTC = "2026-01-01T00:00:00+00:00"


@dataclass(frozen=True, slots=True)
class _FakeMeaningState:
    frame_id: str
    step_index: int
    time_s: float
    theta: Vector
    basin_id: str | None


@dataclass(frozen=True, slots=True)
class _FakeStabilizedTrajectory:
    trajectory_id: str
    frame_id: str
    basin_id: str | None
    states: tuple[_FakeMeaningState, ...]
    centroid: Vector
    covariance: Matrix
    dwell_steps: int
    dwell_seconds: float
    provenance: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_novel(self) -> bool:
        return self.basin_id is None


def _trajectory() -> _FakeStabilizedTrajectory:
    states = tuple(
        _FakeMeaningState(
            frame_id="F",
            step_index=i,
            time_s=float(i) * 0.1,
            theta=theta,
            basin_id=None,
        )
        for i, theta in enumerate(
            [(0.0, 0.0), (0.3, 0.1), (0.6, 0.0), (1.0, 0.2), (1.3, 0.1)]
        )
    )
    return _FakeStabilizedTrajectory(
        trajectory_id="traj-e2e",
        frame_id="F",
        basin_id=None,
        states=states,
        centroid=(0.6, 0.08),
        covariance=((0.2, 0.0), (0.0, 0.1)),
        dwell_steps=5,
        dwell_seconds=0.5,
        provenance=("obs-1", "obs-2", "obs-3"),
    )


@dataclass(frozen=True, slots=True)
class _PipelineResult:
    concept_id: str
    concept_invariants: tuple[tuple[str, float], ...]
    morphism_ids: tuple[str, ...]
    betti_numbers: tuple[int, ...]
    delta_id: str
    candidate_id: str
    candidate_confidence: float
    evolution_event_ids: tuple[str, ...]
    snapshot_id: str
    snapshot_active_node_ids: tuple[str, ...]


def _run_pipeline(trajectory: _FakeStabilizedTrajectory) -> _PipelineResult:
    # Phase 1: object lifting + morphism lifting.
    concept = FunctorialConceptLift().discover(trajectory, hekb_context=None)
    morphisms = IdentityInclusionMorphismLift().lift(concept, matched_prior=None)

    # Phase 2: topology (not yet wired downstream — see RFC_ALIGNMENT.md's
    # Betti-number-has-no-ABI-home gap — but its own determinism is part of
    # this pipeline's contract too).
    coordinates = tuple(state.theta for state in trajectory.states)
    betti = EpsilonGraphBettiAnalyzer().compute_betti_numbers(coordinates, eps=0.5)

    # Phase 3: crystallize -> delta -> commit candidate.
    crystallized = ProvenanceCanonicalizingCrystallizer().crystallize(concept)
    delta = ArtifactKnowledgeDeltaGenerator().generate(crystallized)
    candidate = ObservationalCommitCandidateBuilder(
        clock_ns=lambda: _FIXED_TIME_NS
    ).build(delta, source_trajectory_id=trajectory.trajectory_id)

    # Phase 4: evolution detection against an empty prior snapshot (this
    # concept is being born), then replay into a new snapshot.
    tracker = GeometricEvolutionTracker(clock_utc=lambda: _FIXED_TIME_UTC)
    assert isinstance(crystallized, Concept)
    node = NodeState(node_id=crystallized.id, centroid=crystallized.centroid)
    events = tracker.detect_evolution((), (node,))
    initial_snapshot = LineageSnapshot(
        snapshot_id="s0", timestamp_utc=_FIXED_TIME_UTC, active_node_ids=()
    )
    new_snapshot = tracker.apply_events(initial_snapshot, events)

    return _PipelineResult(
        concept_id=crystallized.id,
        concept_invariants=tuple(sorted(crystallized.invariants.items())),
        morphism_ids=tuple(m.morphism_id for m in morphisms),
        betti_numbers=betti,
        delta_id=delta.id,
        candidate_id=candidate.id,
        candidate_confidence=candidate.confidence,
        evolution_event_ids=tuple(e.event_id for e in events),
        snapshot_id=new_snapshot.snapshot_id,
        snapshot_active_node_ids=new_snapshot.active_node_ids,
    )


def test_full_pipeline_is_deterministic_end_to_end() -> None:
    trajectory = _trajectory()

    first = _run_pipeline(trajectory)
    second = _run_pipeline(trajectory)

    assert first == second


def test_full_pipeline_stage_by_stage_reproducibility() -> None:
    # Same claim as above, but asserted per-field so a failure names the
    # exact stage that broke determinism rather than just "not equal".
    trajectory = _trajectory()

    first = _run_pipeline(trajectory)
    second = _run_pipeline(trajectory)

    assert first.concept_id == second.concept_id
    assert first.concept_invariants == second.concept_invariants
    assert first.morphism_ids == second.morphism_ids
    assert first.betti_numbers == second.betti_numbers
    assert first.delta_id == second.delta_id
    assert first.candidate_id == second.candidate_id
    assert first.candidate_confidence == second.candidate_confidence
    assert first.evolution_event_ids == second.evolution_event_ids
    assert first.snapshot_id == second.snapshot_id
    assert first.snapshot_active_node_ids == second.snapshot_active_node_ids


def test_full_pipeline_produces_a_birth_event_for_a_novel_trajectory() -> None:
    result = _run_pipeline(_trajectory())

    assert result.snapshot_active_node_ids == (result.concept_id,)
    assert len(result.evolution_event_ids) == 1


def test_full_pipeline_confidence_is_bounded() -> None:
    result = _run_pipeline(_trajectory())

    assert 0.0 <= result.candidate_confidence <= 1.0


def test_full_pipeline_betti_numbers_are_well_formed() -> None:
    result = _run_pipeline(_trajectory())

    assert len(result.betti_numbers) == 2
    assert all(isinstance(n, int) and n >= 0 for n in result.betti_numbers)
