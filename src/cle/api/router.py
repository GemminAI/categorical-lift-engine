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
    FiveW1HFieldModel,
    FiveW1HModel,
    GroundedStateModel,
    GroundRequest,
    GroundResponse,
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
    SOKModel,
)
from cle.compression import measure_compression
from cle.grounding.five_w1h import FiveW1HOverrides
from cle.grounding.semantic_state import GroundedState
from cle.grounding.service import GroundingResult, ground
from cle.grounding.sok import SOKOverrides
from cle.runtime.engine import CLEEngine
from cle.runtime.models import LiftResult
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.topology.three_view_pullback import compute_common_invariant_subgraph
from cle.version import __version__

router = APIRouter()

_default_engine = CLEEngine()


def get_engine() -> CLEEngine:
    """Dependency-injection point for `CLEEngine`.

    The default instance has no `recovery_engine`/`hekb_store` configured —
    both are generic outbound hooks (`cle.ports.recovery.ThreeViewRecoveryLike`,
    and `CLEEngine`'s duck-typed `hekb_store: Any` slot) that a real HEKB
    client satisfies structurally; CLE holds no concrete store implementation
    of its own. Owned by whatever composes CLE into a running system, not by
    this API. A production composition root calls
    `cle.api.app.create_app(recovery_engine=..., hekb_store=...)` to get an
    app already wired to a configured instance; tests override this
    dependency directly via `app.dependency_overrides[get_engine]`.
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


def _lift_response(result: LiftResult) -> LiftResponse:
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


@router.post("/lift", response_model=LiftResponse)
def lift(
    request: LiftRequest,
    engine: CLEEngine = Depends(get_engine),  # noqa: B008
) -> LiftResponse:
    result = engine.lift(
        request.concept,
        request.subject_context,
        request.observer_context,
        request.human_knowledge_context,
    )
    return _lift_response(result)


def _grounded_state_response(state: GroundedState) -> GroundedStateModel:
    return GroundedStateModel(
        prompt=state.prompt,
        goal=state.goal,
        five_w1h=FiveW1HModel(
            who=FiveW1HFieldModel(
                value=state.five_w1h.who.value, source=state.five_w1h.who.source
            ),
            what=FiveW1HFieldModel(
                value=state.five_w1h.what.value, source=state.five_w1h.what.source
            ),
            when=FiveW1HFieldModel(
                value=state.five_w1h.when.value, source=state.five_w1h.when.source
            ),
            where=FiveW1HFieldModel(
                value=state.five_w1h.where.value, source=state.five_w1h.where.source
            ),
            why=FiveW1HFieldModel(
                value=state.five_w1h.why.value, source=state.five_w1h.why.source
            ),
            how=FiveW1HFieldModel(
                value=state.five_w1h.how.value, source=state.five_w1h.how.source
            ),
        ),
        sok=SOKModel(
            subject=state.sok.subject,
            subject_source=state.sok.subject_source,
            observer=state.sok.observer,
            observer_source=state.sok.observer_source,
            knowledge_reference=state.sok.knowledge_reference,
            knowledge_reference_source=state.sok.knowledge_reference_source,
        ),
        fingerprint=list(state.fingerprint),
        goal_fingerprint=list(state.goal_fingerprint),
        subject_fingerprint=list(state.subject_fingerprint),
        observer_fingerprint=list(state.observer_fingerprint),
        knowledge_fingerprint=list(state.knowledge_fingerprint),
    )


@router.post("/ground", response_model=GroundResponse)
def ground_endpoint(
    request: GroundRequest,
    engine: CLEEngine = Depends(get_engine),  # noqa: B008
) -> GroundResponse:
    """Input -> Semantic Grounding -> S/O/K(t) + GroundedState -> CLEEngine.lift().

    Uses the same `engine` dependency as `/lift` and `/recover` (so a
    composition root's configured `recovery_engine`/`hekb_store` also
    apply here) -- Grounding calls the engine's existing `lift`, it does
    not bypass it.
    """
    result: GroundingResult = ground(
        request.prompt,
        request.goal,
        five_w1h_overrides=FiveW1HOverrides(**request.five_w1h_overrides.model_dump()),
        sok_overrides=SOKOverrides(**request.sok_overrides.model_dump()),
        default_knowledge_reference=request.default_knowledge_reference,
        embedding_dimension=request.embedding_dimension,
        engine=engine,
    )
    return GroundResponse(
        semantic_state=_grounded_state_response(result.semantic_state),
        lift=_lift_response(result.lift),
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
    request: RecoverRequest,
    engine: CLEEngine = Depends(get_engine),  # noqa: B008
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
