"""Knowledge delta generation.

Owns describing a crystallized artifact as a `KnowledgeDelta` — the
audit/summary record `cle.commit_candidate` wraps into a
`HEKBCommitCandidate`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)
from cle.crystallization import Artifact
from cle.identity import deterministic_id


@runtime_checkable
class KnowledgeDeltaGenerator(Protocol):
    """A crystallized artifact -> the `KnowledgeDelta` describing it."""

    def generate(self, artifact: Artifact) -> KnowledgeDelta: ...


@dataclass(frozen=True, slots=True)
class ArtifactKnowledgeDeltaGenerator:
    """RFC-CLE003 Phase 3, Step 3 (KnowledgeDelta generation: NEW/UPDATE).

    Maps each of the four `Artifact` shapes onto the `KnowledgeDeltaKind`
    the existing ABI already defines — no new kind is introduced:

    - `Concept` (brand new)      -> `CONCEPT_CREATED` ("NEW")
    - `ConceptDelta` (evolving)  -> `CONCEPT_UPDATED` ("UPDATE"; "REINFORCE"
      is not a separate kind — it is a `CONCEPT_UPDATED` delta whose
      `ConceptDelta.reinforcement_count` is already the observable signal
      for how many times this concept has been reinforced)
    - `Category` (grouped)       -> `CATEGORY_FORMED`
    - `CategoryRelation` (morphism between categories) -> `CATEGORY_RELATED`

    "MERGE" (RFC-CLE004's Category Evolution Tracking, Phase 4) has no
    representation here deliberately: fusing two categories into one is a
    multi-artifact evolution decision, not something derivable from a
    single `Artifact` in isolation. See `docs/RFC_ALIGNMENT.md`.
    """

    def generate(self, artifact: Artifact) -> KnowledgeDelta:
        if isinstance(artifact, Concept):
            return KnowledgeDelta(
                id=deterministic_id("delta", "concept_created", artifact.id),
                kind=KnowledgeDeltaKind.CONCEPT_CREATED,
                concept=artifact,
                provenance=artifact.provenance,
            )
        if isinstance(artifact, ConceptDelta):
            delta_id = deterministic_id(
                "delta",
                "concept_updated",
                artifact.concept_id,
                artifact.centroid_shift,
                artifact.reinforcement_count,
                artifact.source_trajectory_id,
            )
            return KnowledgeDelta(
                id=delta_id,
                kind=KnowledgeDeltaKind.CONCEPT_UPDATED,
                concept_delta=artifact,
                provenance=artifact.provenance,
            )
        if isinstance(artifact, Category):
            return KnowledgeDelta(
                id=deterministic_id("delta", "category_formed", artifact.id),
                kind=KnowledgeDeltaKind.CATEGORY_FORMED,
                category=artifact,
                provenance=artifact.provenance,
            )
        assert isinstance(artifact, CategoryRelation)
        return KnowledgeDelta(
            id=deterministic_id("delta", "category_related", artifact.id),
            kind=KnowledgeDeltaKind.CATEGORY_RELATED,
            category_relation=artifact,
            provenance=artifact.provenance,
        )


__all__ = ["ArtifactKnowledgeDeltaGenerator", "KnowledgeDeltaGenerator"]
