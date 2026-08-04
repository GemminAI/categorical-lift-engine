"""Categorical Lift Engine (CLE) — SensOS's optional Knowledge Generation extension.

CLE turns stabilized semantic trajectories into reusable knowledge. It is
not a measurement engine and not part of any runtime loop: the OSS stack
(`semantic-annotator-core`, Meaning Mapper, Meaning Space Runtime) is
complete and fully functional without it. See
`docs/BOUNDARIES.md` for what CLE owns and what it must never do.

CLE accepts only stabilized runtime artifacts (`StabilizedTrajectory`,
`MeaningState` history) and produces only knowledge artifacts (`Concept`,
`ConceptDelta`, `Category`, `CategoryRelation`, `KnowledgeDelta`,
`HEKBCommitCandidate`). It never writes directly into HEKB.
"""

from __future__ import annotations

from cle.abi.inputs import (
    FieldPriorLike,
    HEKBConceptLike,
    HEKBContextLike,
    MeaningStateLike,
    StabilizedTrajectoryLike,
)
from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    ConceptMorphism,
    HEKBCommitCandidate,
    KnowledgeDelta,
    KnowledgeDeltaKind,
    MorphismType,
)
from cle.categorical_lift.engine import CategoricalLiftEngine
from cle.category import CategoryConstructor
from cle.commit_candidate import CommitCandidateBuilder
from cle.concept import ConceptDiscoveryStrategy, FunctorialConceptLift
from cle.crystallization import KnowledgeCrystallizer
from cle.errors import (
    CLEError,
    DimensionMismatch,
    FunctorialityViolation,
    InvalidTrajectory,
    NoStrategyConfigured,
    NotStabilized,
)
from cle.functor import CanonicalInclusionFunctorConstructor, FunctorConstructor
from cle.homotopy import HomotopyAnalyzer
from cle.knowledge_delta import KnowledgeDeltaGenerator
from cle.morphism import IdentityInclusionMorphismLift, MorphismLiftStrategy
from cle.natural_transformation import NaturalTransformationAnalyzer
from cle.ports.commit import CommitSink
from cle.quotient import QuotientConstructor
from cle.version import __version__

__all__ = [
    "CLEError",
    "CanonicalInclusionFunctorConstructor",
    "CategoricalLiftEngine",
    "Category",
    "CategoryConstructor",
    "CategoryRelation",
    "CommitCandidateBuilder",
    "CommitSink",
    "Concept",
    "ConceptDelta",
    "ConceptDiscoveryStrategy",
    "ConceptMorphism",
    "DimensionMismatch",
    "FieldPriorLike",
    "FunctorConstructor",
    "FunctorialConceptLift",
    "FunctorialityViolation",
    "HEKBCommitCandidate",
    "HEKBConceptLike",
    "HEKBContextLike",
    "HomotopyAnalyzer",
    "IdentityInclusionMorphismLift",
    "InvalidTrajectory",
    "KnowledgeCrystallizer",
    "KnowledgeDelta",
    "KnowledgeDeltaGenerator",
    "KnowledgeDeltaKind",
    "MeaningStateLike",
    "MorphismLiftStrategy",
    "MorphismType",
    "NaturalTransformationAnalyzer",
    "NoStrategyConfigured",
    "NotStabilized",
    "QuotientConstructor",
    "StabilizedTrajectoryLike",
    "__version__",
]
