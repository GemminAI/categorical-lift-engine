from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cle.abi.inputs import HEKBContextLike, StabilizedTrajectoryLike
from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    HEKBCommitCandidate,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)
from cle.categorical_lift.engine import CategoricalLiftEngine
from cle.crystallization import Artifact
from cle.errors import NoStrategyConfigured, NotStabilized
from conftest import FakeStabilizedTrajectory


@dataclass
class FakeConceptDiscovery:
    def discover(
        self,
        trajectory: StabilizedTrajectoryLike,
        *,
        hekb_context: HEKBContextLike | None = None,
    ) -> Concept | ConceptDelta:
        return Concept(
            id=f"concept-from-{trajectory.trajectory_id}",
            frame_id=trajectory.frame_id,
            centroid=trajectory.centroid,
            hessian=None,
            source_trajectory_id=trajectory.trajectory_id,
            provenance=trajectory.provenance,
        )


@dataclass
class FakeCategoryConstructor:
    should_form_category: bool = False

    def construct(
        self,
        artifact: Concept | ConceptDelta,
        *,
        hekb_context: HEKBContextLike | None = None,
    ) -> Category | None:
        if not self.should_form_category:
            return None
        if isinstance(artifact, Concept):
            concept_id = artifact.id
        else:
            concept_id = artifact.concept_id
        return Category(
            id=f"category-for-{concept_id}",
            label=None,
            concept_ids=(concept_id,),
            structure_kind="generic",
        )


@dataclass
class FakeCrystallizer:
    calls: list[Artifact] = field(default_factory=list)

    def crystallize(self, artifact: Artifact) -> Artifact:
        self.calls.append(artifact)
        return artifact


@dataclass
class FakeKnowledgeDeltaGenerator:
    counter: int = 0

    def generate(self, artifact: Artifact) -> KnowledgeDelta:
        self.counter += 1
        kd_id = f"kd-{self.counter}"
        if isinstance(artifact, Concept):
            return KnowledgeDelta(
                id=kd_id, kind=KnowledgeDeltaKind.CONCEPT_CREATED, concept=artifact
            )
        if isinstance(artifact, ConceptDelta):
            return KnowledgeDelta(
                id=kd_id,
                kind=KnowledgeDeltaKind.CONCEPT_UPDATED,
                concept_delta=artifact,
            )
        if isinstance(artifact, Category):
            return KnowledgeDelta(
                id=kd_id, kind=KnowledgeDeltaKind.CATEGORY_FORMED, category=artifact
            )
        assert isinstance(artifact, CategoryRelation)
        return KnowledgeDelta(
            id=kd_id,
            kind=KnowledgeDeltaKind.CATEGORY_RELATED,
            category_relation=artifact,
        )


@dataclass
class FakeCommitCandidateBuilder:
    counter: int = 0

    def build(
        self, delta: KnowledgeDelta, *, source_trajectory_id: str
    ) -> HEKBCommitCandidate:
        self.counter += 1
        return HEKBCommitCandidate(
            id=f"cand-{self.counter}",
            delta=delta,
            confidence=1.0,
            source_trajectory_id=source_trajectory_id,
            created_at_ns=self.counter,
        )


@dataclass
class FakeCommitSink:
    received: list[HEKBCommitCandidate] = field(default_factory=list)

    def submit(self, candidate: HEKBCommitCandidate) -> None:
        self.received.append(candidate)


def _fully_configured_engine(**overrides: object) -> CategoricalLiftEngine:
    defaults: dict[str, object] = {
        "concept_discovery": FakeConceptDiscovery(),
        "knowledge_delta_generator": FakeKnowledgeDeltaGenerator(),
        "commit_candidate_builder": FakeCommitCandidateBuilder(),
    }
    defaults.update(overrides)
    return CategoricalLiftEngine(**defaults)  # type: ignore[arg-type]


def test_lift_without_category_constructor_yields_one_candidate(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = _fully_configured_engine()

    candidates = engine.lift(stabilized_trajectory)

    assert len(candidates) == 1
    assert candidates[0].delta.kind == KnowledgeDeltaKind.CONCEPT_CREATED
    assert candidates[0].source_trajectory_id == stabilized_trajectory.trajectory_id


def test_lift_with_category_constructor_yields_two_candidates(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = _fully_configured_engine(
        category_constructor=FakeCategoryConstructor(should_form_category=True)
    )

    candidates = engine.lift(stabilized_trajectory)

    assert len(candidates) == 2
    kinds = {candidate.delta.kind for candidate in candidates}
    assert kinds == {
        KnowledgeDeltaKind.CONCEPT_CREATED,
        KnowledgeDeltaKind.CATEGORY_FORMED,
    }


def test_lift_declining_category_constructor_yields_one_candidate(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = _fully_configured_engine(
        category_constructor=FakeCategoryConstructor(should_form_category=False)
    )

    candidates = engine.lift(stabilized_trajectory)

    assert len(candidates) == 1


def test_lift_passes_every_artifact_through_crystallizer(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    crystallizer = FakeCrystallizer()
    engine = _fully_configured_engine(
        category_constructor=FakeCategoryConstructor(should_form_category=True),
        crystallizer=crystallizer,
    )

    engine.lift(stabilized_trajectory)

    assert len(crystallizer.calls) == 2


def test_lift_submits_every_candidate_to_commit_sink_when_configured(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    sink = FakeCommitSink()
    engine = _fully_configured_engine(commit_sink=sink)

    candidates = engine.lift(stabilized_trajectory)

    assert sink.received == list(candidates)


def test_lift_does_not_touch_commit_sink_when_unconfigured(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    # No commit_sink passed: lift() must not raise, and must not require one.
    engine = _fully_configured_engine()
    candidates = engine.lift(stabilized_trajectory)
    assert len(candidates) == 1


def test_lift_rejects_unstabilized_trajectory(
    unstabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = _fully_configured_engine()

    with pytest.raises(NotStabilized, match="not a stabilized trajectory"):
        engine.lift(unstabilized_trajectory)


def test_lift_rejects_trajectory_with_positive_dwell_but_no_states() -> None:
    # dwell_steps > 0 alone is not sufficient: a trajectory truthfully
    # reporting a dwell but carrying no recorded states is malformed, not
    # merely unstabilized, and must fail the same way.
    trajectory = FakeStabilizedTrajectory(
        trajectory_id="traj-malformed",
        frame_id="F",
        basin_id=None,
        states=(),
        centroid=(0.0,),
        covariance=((1.0,),),
        dwell_steps=3,
        dwell_seconds=0.3,
    )
    engine = _fully_configured_engine()

    with pytest.raises(NotStabilized, match="has no states"):
        engine.lift(trajectory)


@pytest.mark.parametrize(
    "overrides",
    [
        {"concept_discovery": None},
        {"knowledge_delta_generator": None},
        {"commit_candidate_builder": None},
    ],
)
def test_lift_raises_when_a_required_strategy_is_missing(
    stabilized_trajectory: FakeStabilizedTrajectory, overrides: dict[str, object]
) -> None:
    engine = _fully_configured_engine(**overrides)

    with pytest.raises(NoStrategyConfigured):
        engine.lift(stabilized_trajectory)


def test_engine_with_no_strategies_at_all_raises_on_first_missing_stage(
    stabilized_trajectory: FakeStabilizedTrajectory,
) -> None:
    engine = CategoricalLiftEngine()

    with pytest.raises(NoStrategyConfigured, match="concept_discovery"):
        engine.lift(stabilized_trajectory)
