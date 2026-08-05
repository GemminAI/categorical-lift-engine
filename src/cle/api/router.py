"""Thin HTTP controllers — Phase 1.

Every handler below does exactly three things: unpack the request into the
shape the reused domain function already expects, call that function, wrap
the result. No categorical-theory algorithm, no cognition logic, and no
error-to-status mapping lives here — failures propagate as the domain's own
`cle.errors.CLEError` subclasses (or `FiniteCategory`'s `ValueError`) and are
translated to HTTP responses by the exception handlers registered in
`cle.api.app`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from cle.api.models import (
    CompressRequest,
    CompressResponse,
    FiniteCategoryInput,
    HealthResponse,
    InvariantSignatureModel,
    LiftRequest,
    LiftResponse,
    MorphismModel,
    ProofCertificateModel,
    PullbackRequest,
    PullbackResponse,
    RecoverRequest,
    RecoverResponse,
)
from cle.compression import measure_compression
from cle.runtime.engine import CLEEngine
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.topology.three_view_pullback import compute_common_invariant_subgraph
from cle.version import __version__

router = APIRouter()

_default_engine = CLEEngine()


def get_engine() -> CLEEngine:
    """Dependency-injection point for `CLEEngine`.

    The default instance has no `recovery_engine`/`hekb_store` configured —
    those are outbound ports (`cle.ports.recovery.ThreeViewRecoveryLike`,
    `cle.runtime.hekb_store`) owned by whatever composes CLE into a running
    system (HEKB v2), not by this API. Override via
    `app.dependency_overrides[get_engine]` to inject a configured instance.
    """
    return _default_engine


def _finite_category(model: FiniteCategoryInput) -> FiniteCategory:
    """Wire-format -> `FiniteCategory`. Field mapping only, no category theory."""
    morphisms = {m.name: Morphism(m.name, m.source, m.target) for m in model.morphisms}
    composition = {(entry.g, entry.f): entry.h for entry in model.composition}
    return FiniteCategory(
        objects=frozenset(model.objects), morphisms=morphisms, composition=composition
    )


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="cle", version=__version__)


@router.post("/lift", response_model=LiftResponse)
def lift(
    request: LiftRequest, engine: CLEEngine = Depends(get_engine)  # noqa: B008
) -> LiftResponse:
    result = engine.lift(
        request.concept,
        request.subject_context,
        request.observer_context,
        request.human_knowledge_context,
    )
    return LiftResponse(
        concept_id=result.concept_id,
        normalized_hash=result.normalized_hash,
        morphisms=sorted(result.morphisms),
        pullback_limit=result.pullback_limit,
        pushout_colimit=result.pushout_colimit,
        invariants=InvariantSignatureModel(
            betti_0=result.invariants.betti_0,
            betti_1=result.invariants.betti_1,
            betti_2=result.invariants.betti_2,
            euler_characteristic=result.invariants.euler_characteristic,
        ),
        compression_ratio=result.compression_ratio,
        semantic_closure=result.semantic_closure,
        proof=ProofCertificateModel(
            is_valid=result.proof.is_valid,
            boundary_condition_verified=result.proof.boundary_condition_verified,
            functor_axioms_satisfied=result.proof.functor_axioms_satisfied,
            proof_trace=list(result.proof.proof_trace),
        ),
    )


@router.post("/pullback", response_model=PullbackResponse)
def pullback(request: PullbackRequest) -> PullbackResponse:
    shared = compute_common_invariant_subgraph(
        _finite_category(request.subject),
        _finite_category(request.observer),
        _finite_category(request.knowledge),
    )
    return PullbackResponse(
        shared_morphisms=[
            MorphismModel(name=m.name, source=m.source, target=m.target)
            for m in sorted(shared, key=lambda morphism: morphism.name)
        ]
    )


@router.post("/recover", response_model=RecoverResponse)
def recover(
    request: RecoverRequest, engine: CLEEngine = Depends(get_engine)  # noqa: B008
) -> RecoverResponse:
    result = engine.recover(request.subject, request.observer, request.knowledge)
    return RecoverResponse(
        recovered_state_id=result.recovered_state_id,
        reconstructed_closure=result.reconstructed_closure,
        three_view_discrepancy=result.three_view_discrepancy,
        converged=result.converged,
    )


@router.post("/compress", response_model=CompressResponse)
def compress(request: CompressRequest) -> CompressResponse:
    result = measure_compression(request.raw_context, request.lifted_morphism_set)
    return CompressResponse(
        raw_size=result.raw_size,
        lifted_size=result.lifted_size,
        ratio=result.ratio,
        meets_target=result.meets_target,
    )


__all__ = ["get_engine", "router"]
