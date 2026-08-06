"""CLE v3 — Concept Lifting Runtime.

A single runtime (`CLEEngine.lift`/`lift_many`/`compare`/`recover`) replacing
CLE v2's independent math utilities (`Functor`, pullback, invariants,
compression, natural transformation) as standalone call sites. Those
modules are not removed — `CLEEngine` composes them — see
`cle.runtime.engine` for what each pipeline stage reuses.
"""

from __future__ import annotations

from cle.runtime.engine import CLEEngine
from cle.runtime.models import (
    InvariantComparison,
    InvariantSignature,
    LiftResult,
    ProofCertificate,
    RecoveredContext,
)

__all__ = [
    "CLEEngine",
    "InvariantComparison",
    "InvariantSignature",
    "LiftResult",
    "ProofCertificate",
    "RecoveredContext",
]
