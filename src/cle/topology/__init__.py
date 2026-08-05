"""Full simplicial topology and general categorical structures.

SensOS Core Value & Architectural Specification v2.0.0 §4: Vietoris-Rips
simplicial complex, boundary operators, Betti numbers via rank/nullity,
general functors with composition, natural transformations, and an
invariant signature grounded in the spec's own Betti-number invariants.

This coexists with, and does not replace, the pre-existing
`cle.homotopy.EpsilonGraphBettiAnalyzer` (a deliberately scoped, cheaper
graph-only b_0/b_1 approximation) and `cle.functor.CanonicalInclusionFunctorConstructor`
(a narrower functor derivable from bare `concept_ids` sets alone). Those
stay the fast path for callers who only need what they already compute;
this package is the full mathematics the spec's §4 equations describe.
"""

from __future__ import annotations

from cle.topology.category_theory import FiniteCategory, Functor, Morphism
from cle.topology.invariant_signature import (
    InvariantSignature,
    compute_invariant_signature,
)
from cle.topology.natural_transformation import NaturalTransformation
from cle.topology.pushout import categorical_pushout
from cle.topology.simplicial import (
    Simplex,
    VietorisRipsComplex,
    betti_numbers,
    boundary_matrix,
)
from cle.topology.three_view_pullback import (
    ThreeViewPullbackEngine,
    compute_common_invariant_subgraph,
)

__all__ = [
    "FiniteCategory",
    "Functor",
    "InvariantSignature",
    "Morphism",
    "NaturalTransformation",
    "Simplex",
    "ThreeViewPullbackEngine",
    "VietorisRipsComplex",
    "betti_numbers",
    "boundary_matrix",
    "categorical_pushout",
    "compute_common_invariant_subgraph",
    "compute_invariant_signature",
]
