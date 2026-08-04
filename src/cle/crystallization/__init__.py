"""Knowledge crystallization.

Owns the semantic-abstraction pass that finalizes a lift's artifact into its
immutable, committable form — the last step before it is described as a
`KnowledgeDelta`. Crystallization does not change *what* was discovered
(that is `cle.concept`/`cle.category`'s job); it normalizes and finalizes it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import Category, CategoryRelation, Concept, ConceptDelta

Artifact = Concept | ConceptDelta | Category | CategoryRelation


@runtime_checkable
class KnowledgeCrystallizer(Protocol):
    """A lift's raw artifact -> its finalized, committable form."""

    def crystallize(self, artifact: Artifact) -> Artifact: ...


__all__ = ["Artifact", "KnowledgeCrystallizer"]
