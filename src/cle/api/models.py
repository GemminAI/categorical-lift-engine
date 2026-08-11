"""Request/response models for the CLE FastAPI service — Phase 1.

Every model here is a wire-format mirror of a `cle.runtime`/`cle.topology`/
`cle.compression` type; no computation happens in this module. `ConceptInput`
in particular is shaped only so it satisfies `cle.runtime.engine._coordinates_of`'s
`.states[i].theta` duck-type — a pydantic `BaseModel` supports attribute
access, so an instance of it can be handed to `CLEEngine.lift`/`.recover`
directly, with no conversion function of our own.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MeaningStatePoint(BaseModel):
    theta: list[float]


class ConceptInput(BaseModel):
    """A point cloud, shaped to satisfy the `.states[i].theta` duck-type
    `cle.runtime.engine._coordinates_of` reads from a `StabilizedTrajectoryLike`.
    """

    states: list[MeaningStatePoint]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class LiftRequest(BaseModel):
    concept: ConceptInput
    subject_context: ConceptInput | None = None
    observer_context: ConceptInput | None = None
    human_knowledge_context: ConceptInput | None = None


class InvariantSignatureModel(BaseModel):
    betti_0: int
    betti_1: int
    betti_2: int
    euler_characteristic: int


class ProofCertificateModel(BaseModel):
    is_valid: bool
    boundary_condition_verified: bool
    functor_axioms_satisfied: bool
    proof_trace: list[str]


class LiftResponse(BaseModel):
    concept_id: str
    normalized_hash: str
    morphisms: list[tuple[str, str, str]]
    pullback_limit: dict[str, Any]
    pushout_colimit: dict[str, Any]
    invariants: InvariantSignatureModel
    compression_ratio: float
    semantic_closure: dict[str, Any]
    proof: ProofCertificateModel


class MorphismModel(BaseModel):
    name: str
    source: str
    target: str


class CompositionEntry(BaseModel):
    g: str
    f: str
    h: str


class FiniteCategoryInput(BaseModel):
    objects: list[str]
    morphisms: list[MorphismModel]
    composition: list[CompositionEntry] = Field(default_factory=list)


class PullbackRequest(BaseModel):
    subject: FiniteCategoryInput
    observer: FiniteCategoryInput
    knowledge: FiniteCategoryInput


class PullbackResponse(BaseModel):
    shared_morphisms: list[MorphismModel]


class RecoverRequest(BaseModel):
    subject: ConceptInput
    observer: ConceptInput
    knowledge: ConceptInput


class RecoverResponse(BaseModel):
    recovered_state_id: str
    reconstructed_closure: dict[str, Any]
    three_view_discrepancy: float
    converged: bool


class CompressRequest(BaseModel):
    raw_context: Any
    lifted_morphism_set: Any


class CompressResponse(BaseModel):
    raw_size: int
    lifted_size: int
    ratio: float
    meets_target: bool


class FiveW1HFieldModel(BaseModel):
    value: str
    source: str


class FiveW1HModel(BaseModel):
    who: FiveW1HFieldModel
    what: FiveW1HFieldModel
    when: FiveW1HFieldModel
    where: FiveW1HFieldModel
    why: FiveW1HFieldModel
    how: FiveW1HFieldModel


class SOKModel(BaseModel):
    subject: str
    subject_source: str
    observer: str
    observer_source: str
    knowledge_reference: str
    knowledge_reference_source: str


class FiveW1HOverridesInput(BaseModel):
    who: str | None = None
    what: str | None = None
    when: str | None = None
    where: str | None = None
    why: str | None = None
    how: str | None = None


class SOKOverridesInput(BaseModel):
    subject: str | None = None
    observer: str | None = None
    knowledge_reference: str | None = None


class GroundRequest(BaseModel):
    prompt: str
    goal: str
    five_w1h_overrides: FiveW1HOverridesInput = Field(
        default_factory=FiveW1HOverridesInput
    )
    sok_overrides: SOKOverridesInput = Field(default_factory=SOKOverridesInput)
    default_knowledge_reference: str = "unspecified"
    embedding_dimension: int = Field(default=8, ge=1, le=64)


class GroundedStateModel(BaseModel):
    prompt: str
    goal: str
    five_w1h: FiveW1HModel
    sok: SOKModel
    fingerprint: list[str]
    goal_fingerprint: list[str]
    subject_fingerprint: list[str]
    observer_fingerprint: list[str]
    knowledge_fingerprint: list[str]


class GroundResponse(BaseModel):
    semantic_state: GroundedStateModel
    lift: LiftResponse
