"""CLE v3 strict ABI — spec v3.0.0 §4.1.

`InvariantSignature` lives in `cle.topology.invariant_signature` (Stage 5
already owns computing it); it is re-exported here only so every v3 ABI
type has one import location, per the spec's §4.1 type list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cle.topology.invariant_signature import InvariantSignature

__all__ = [
    "InvariantComparison",
    "InvariantSignature",
    "LiftResult",
    "ProofCertificate",
    "RecoveredContext",
]


@dataclass(frozen=True, slots=True)
class ProofCertificate:
    is_valid: bool
    boundary_condition_verified: bool
    functor_axioms_satisfied: bool
    proof_trace: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LiftResult:
    concept_id: str
    normalized_hash: str
    morphisms: frozenset[tuple[str, str, str]]
    pullback_limit: dict[str, Any]
    pushout_colimit: dict[str, Any]
    invariants: InvariantSignature
    compression_ratio: float
    semantic_closure: dict[str, Any]
    proof: ProofCertificate


@dataclass(frozen=True, slots=True)
class InvariantComparison:
    concept_a_id: str
    concept_b_id: str
    is_isomorphic: bool
    homology_distance: float
    shared_invariants: InvariantSignature
    mapping_functor_exists: bool


@dataclass(frozen=True, slots=True)
class RecoveredContext:
    recovered_state_id: str
    reconstructed_closure: dict[str, Any] = field(default_factory=dict)
    three_view_discrepancy: float = 0.0
    converged: bool = False
