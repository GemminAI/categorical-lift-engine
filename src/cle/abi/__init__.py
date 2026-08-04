"""The CLE ABI: frozen inputs (structural, read-only) and outputs (owned, frozen).

See `cle.abi.inputs` for what CLE reads from Meaning Space Runtime / HEKB
without importing either, and `cle.abi.outputs` for the six knowledge
artifacts CLE produces.
"""

from __future__ import annotations

from cle.abi.inputs import (
    FieldPriorLike,
    HEKBConceptLike,
    HEKBContextLike,
    Matrix,
    MeaningStateLike,
    StabilizedTrajectoryLike,
    Vector,
)
from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    HEKBCommitCandidate,
    KnowledgeDelta,
    KnowledgeDeltaKind,
)

__all__ = [
    "Category",
    "CategoryRelation",
    "Concept",
    "ConceptDelta",
    "FieldPriorLike",
    "HEKBCommitCandidate",
    "HEKBConceptLike",
    "HEKBContextLike",
    "KnowledgeDelta",
    "KnowledgeDeltaKind",
    "Matrix",
    "MeaningStateLike",
    "StabilizedTrajectoryLike",
    "Vector",
]
