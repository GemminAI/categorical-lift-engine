"""`CategoricalLiftEngine` — the orchestrator, and CLE's only entry point.

This is composition, not computation: the engine wires the nine stage
strategies together in a fixed order and validates its input and output
shapes. It contains no categorical-theory algorithm of its own — every
`Protocol` it calls is supplied by the caller, and a required stage left
unconfigured raises `NoStrategyConfigured` rather than silently doing
nothing. This is the deliberate skeleton/interface boundary this repository
stops at (see `docs/RFC_ALIGNMENT.md`).
"""

from __future__ import annotations

from dataclasses import dataclass

from cle.abi.inputs import HEKBContextLike, StabilizedTrajectoryLike
from cle.abi.outputs import HEKBCommitCandidate
from cle.category import CategoryConstructor
from cle.commit_candidate import CommitCandidateBuilder
from cle.concept import ConceptDiscoveryStrategy
from cle.crystallization import Artifact, KnowledgeCrystallizer
from cle.errors import NoStrategyConfigured, NotStabilized
from cle.knowledge_delta import KnowledgeDeltaGenerator
from cle.ports.commit import CommitSink


def _validate_trajectory(trajectory: StabilizedTrajectoryLike) -> None:
    """CLE accepts only stabilized runtime artifacts — never raw observations."""
    if trajectory.dwell_steps <= 0:
        raise NotStabilized(
            f"trajectory {trajectory.trajectory_id!r} has dwell_steps="
            f"{trajectory.dwell_steps}, not a stabilized trajectory"
        )
    if not trajectory.states:
        raise NotStabilized(f"trajectory {trajectory.trajectory_id!r} has no states")


@dataclass(frozen=True, slots=True)
class CategoricalLiftEngine:
    """Composes the nine Categorical Lift stages into one `lift()` call.

    Three stages are required to reach a `HEKBCommitCandidate` at all
    (`concept_discovery`, `knowledge_delta_generator`,
    `commit_candidate_builder`); the rest are optional refinements that are
    skipped, not faked, when unconfigured. `homotopy`/`quotient`/`functor`/
    `natural_transformation` strategies are not parameters of this engine —
    they are inputs to a `category_constructor` implementation, which owns
    deciding when and how to use them.
    """

    concept_discovery: ConceptDiscoveryStrategy | None = None
    knowledge_delta_generator: KnowledgeDeltaGenerator | None = None
    commit_candidate_builder: CommitCandidateBuilder | None = None
    category_constructor: CategoryConstructor | None = None
    crystallizer: KnowledgeCrystallizer | None = None
    commit_sink: CommitSink | None = None

    def lift(
        self,
        trajectory: StabilizedTrajectoryLike,
        *,
        hekb_context: HEKBContextLike | None = None,
    ) -> tuple[HEKBCommitCandidate, ...]:
        """StabilizedTrajectory -> zero or more `HEKBCommitCandidate` proposals.

        Produces one candidate for the discovered/evolved concept, plus one
        more if `category_constructor` forms a `Category` from it. Never
        writes to HEKB itself: candidates are returned, and — only if
        `commit_sink` is configured — also submitted to it.
        """
        _validate_trajectory(trajectory)
        if self.concept_discovery is None:
            raise NoStrategyConfigured("concept_discovery strategy is not configured")
        if self.knowledge_delta_generator is None:
            raise NoStrategyConfigured(
                "knowledge_delta_generator strategy is not configured"
            )
        if self.commit_candidate_builder is None:
            raise NoStrategyConfigured(
                "commit_candidate_builder strategy is not configured"
            )

        concept_artifact = self.concept_discovery.discover(
            trajectory, hekb_context=hekb_context
        )
        artifacts: list[Artifact] = [concept_artifact]

        if self.category_constructor is not None:
            category = self.category_constructor.construct(
                concept_artifact, hekb_context=hekb_context
            )
            if category is not None:
                artifacts.append(category)

        if self.crystallizer is not None:
            crystallizer = self.crystallizer
            artifacts = [crystallizer.crystallize(artifact) for artifact in artifacts]

        candidates: list[HEKBCommitCandidate] = []
        for artifact in artifacts:
            delta = self.knowledge_delta_generator.generate(artifact)
            candidate = self.commit_candidate_builder.build(
                delta, source_trajectory_id=trajectory.trajectory_id
            )
            candidates.append(candidate)

        if self.commit_sink is not None:
            for candidate in candidates:
                self.commit_sink.submit(candidate)

        return tuple(candidates)


__all__ = ["CategoricalLiftEngine"]
