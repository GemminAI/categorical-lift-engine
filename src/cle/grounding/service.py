"""`ground()`: Input -> Semantic Grounding -> S/O/K(t) + GroundedState ->
CLEEngine.lift(). The causal path this package exists to establish.

Before this module, `CLEEngine.lift(concept, subject_context,
observer_context, human_knowledge_context)` was a real, tested, working
pipeline with no real caller: every existing test hand-built synthetic
point clouds directly. `ground()` is the first producer of those four
arguments from an actual Prompt/Goal, via `cle.grounding.embedding`.

`ground()` does not reimplement anything `CLEEngine` already does --
Stage 1-7 (`normalize`, `apply_functors`, `three_view_pullback`,
`categorical_pushout`, `extract_invariants`,
`compress_cognitive_structure`, `prove_conformance`) are unchanged, called
exactly as `POST /lift` already calls them. This module's only job is
producing real arguments for them from text.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cle.grounding.embedding import PointCloud
from cle.grounding.five_w1h import FiveW1HOverrides, extract_five_w1h
from cle.grounding.semantic_state import GroundedState, build_grounded_state
from cle.grounding.sok import SOKOverrides, build_sok
from cle.runtime.engine import CLEEngine
from cle.runtime.models import LiftResult


class GroundingResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    semantic_state: GroundedState
    lift: LiftResult


def ground(
    prompt: str,
    goal: str,
    *,
    five_w1h_overrides: FiveW1HOverrides | None = None,
    sok_overrides: SOKOverrides | None = None,
    default_knowledge_reference: str = "unspecified",
    embedding_dimension: int = 8,
    engine: CLEEngine | None = None,
) -> GroundingResult:
    five_w1h = extract_five_w1h(prompt, goal, five_w1h_overrides)
    sok = build_sok(
        five_w1h, sok_overrides, default_knowledge_reference=default_knowledge_reference
    )
    semantic_state = build_grounded_state(
        prompt, goal, five_w1h, sok, embedding_dimension=embedding_dimension
    )

    engine = engine if engine is not None else CLEEngine()
    lift_result = engine.lift(
        concept=PointCloud.from_vectors(semantic_state.concept_points),
        subject_context=PointCloud.from_vectors(semantic_state.subject_points),
        observer_context=PointCloud.from_vectors(semantic_state.observer_points),
        human_knowledge_context=PointCloud.from_vectors(
            semantic_state.knowledge_points
        ),
    )

    return GroundingResult(semantic_state=semantic_state, lift=lift_result)


__all__ = ["GroundingResult", "ground"]
