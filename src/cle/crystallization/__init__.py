"""Knowledge crystallization.

Owns the semantic-abstraction pass that finalizes a lift's artifact into its
immutable, committable form — the last step before it is described as a
`KnowledgeDelta`. Crystallization does not change *what* was discovered
(that is `cle.concept`/`cle.category`'s job); it normalizes and finalizes it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from cle.abi.outputs import Category, CategoryRelation, Concept, ConceptDelta

Artifact = Concept | ConceptDelta | Category | CategoryRelation


@runtime_checkable
class KnowledgeCrystallizer(Protocol):
    """A lift's raw artifact -> its finalized, committable form."""

    def crystallize(self, artifact: Artifact) -> Artifact: ...


def _deduplicate_provenance(provenance: tuple[str, ...]) -> tuple[str, ...]:
    """First-occurrence-order dedup: keep the sequence, drop repeats.

    Not a sort — provenance is an evidence trail, and reordering it would
    discard whatever sequencing the upstream stage encoded (e.g. a
    `CanonicalInclusionFunctorConstructor`'s `source.provenance +
    target.provenance` can legitimately repeat an id both sides already
    shared).
    """
    return tuple(dict.fromkeys(provenance))


@dataclass(frozen=True, slots=True)
class ProvenanceCanonicalizingCrystallizer:
    """RFC-CLE003 Phase 3, Step 1 (ConceptCandidate generation).

    "Crystallization does not change *what* was discovered... it normalizes
    and finalizes it" (module docstring) — scoped here to the one
    finalization step that is both meaningful and available from a single
    `Artifact` alone: deduplicating its `provenance`. A double-counted
    observation id (e.g. from `CategoryRelation.provenance` combining two
    categories that already shared evidence) would otherwise let the same
    piece of evidence inflate confidence twice downstream in
    `CommitCandidateBuilder`.

    Everything else on the artifact is untouched: crystallization is a
    finalization pass, not a re-interpretation of *what* `cle.concept`/
    `cle.category`/`cle.functor` already decided.
    """

    def crystallize(self, artifact: Artifact) -> Artifact:
        return replace(
            artifact, provenance=_deduplicate_provenance(artifact.provenance)
        )


__all__ = [
    "Artifact",
    "KnowledgeCrystallizer",
    "ProvenanceCanonicalizingCrystallizer",
]
