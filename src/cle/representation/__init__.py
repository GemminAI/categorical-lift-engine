"""Representation-history verification (CLE v0.3, phases R0a and R0b).

Experimental and independently removable: nothing outside this package
imports it, and it changes no `cle.abi` type nor `FiniteCategory`/`Functor`.
"""

from __future__ import annotations

from cle.representation.canonical import canonical_json, sha256_hex
from cle.representation.checks import (
    CHECKER,
    check_r1,
    check_r2,
    check_r3,
    check_r4,
    check_r5,
    check_r6,
    check_r7,
    check_r8,
    complete_identities,
    derive_unit_compositions,
    finite_category_of,
    verify_history,
)
from cle.representation.model import (
    AbandonedBranch,
    CheckerInfo,
    CheckResult,
    CheckWarning,
    Composition,
    Invertibility,
    Location,
    PropertyVocabulary,
    Ref,
    RepresentationError,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
    Span,
    aggregate,
)

__all__ = [
    "CHECKER",
    "AbandonedBranch",
    "CheckResult",
    "CheckWarning",
    "CheckerInfo",
    "Composition",
    "Invertibility",
    "Location",
    "PropertyVocabulary",
    "Ref",
    "RepresentationError",
    "RepresentationHistory",
    "RepresentationMorphism",
    "RepresentationState",
    "Span",
    "aggregate",
    "canonical_json",
    "check_r1",
    "check_r2",
    "check_r3",
    "check_r4",
    "check_r5",
    "check_r6",
    "check_r7",
    "check_r8",
    "complete_identities",
    "derive_unit_compositions",
    "finite_category_of",
    "sha256_hex",
    "verify_history",
]
