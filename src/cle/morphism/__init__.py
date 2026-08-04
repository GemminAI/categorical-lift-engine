"""Morphism lifting.

Owns discovering the categorical morphisms implied by a single Functorial
Lift's object — the second half of RFC-CLE001 §3.1's functor
$\\mathcal{F}: \\mathcal{M}_{\\text{proj}} \\to \\mathcal{C}_{\\text{concept}}$,
which must act on morphisms as well as objects for functoriality
($\\mathcal{F}(\\text{id}_A) = \\text{id}_{\\mathcal{F}(A)}$) to hold.

Added for RFC-CLE001 Phase 1 (Functorial Lift Engine): the original skeleton
had no module for this — `cle.functor`/`cle.natural_transformation` operate
one level up, on `CategoryRelation`s between whole `Category` values, not on
morphisms between individual concepts. See `docs/RFC_ALIGNMENT.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cle.abi.inputs import HEKBConceptLike
from cle.abi.outputs import Concept, ConceptDelta, ConceptMorphism, MorphismType
from cle.identity import deterministic_id


@runtime_checkable
class MorphismLiftStrategy(Protocol):
    """A lifted concept artifact -> the morphism(s) it participates in.

    `matched_prior` is the existing HEKB concept the artifact was resolved
    against, if any (the same value a `ConceptDiscoveryStrategy` would have
    consulted) — `None` when the artifact is a brand-new `Concept` with no
    prior evidence to relate to.
    """

    def lift(
        self,
        artifact: Concept | ConceptDelta,
        *,
        matched_prior: HEKBConceptLike | None,
    ) -> tuple[ConceptMorphism, ...]: ...


def _object_id(artifact: Concept | ConceptDelta) -> str:
    return artifact.id if isinstance(artifact, Concept) else artifact.concept_id


@dataclass(frozen=True, slots=True)
class IdentityInclusionMorphismLift:
    """The minimal morphism structure every Functorial Lift carries.

    Every lifted object has an identity morphism — a category axiom, true
    regardless of whether the object is new or reinforced — so `lift` always
    returns at least one `ConceptMorphism` of `MorphismType.IDENTITY`. When
    `matched_prior` is given, a second `ConceptMorphism` of
    `MorphismType.INCLUSION` records evidence flowing from the prior concept
    into the (possibly refined) lifted object.

    This does not attempt homotopy equivalence, pullback, or pushout
    morphisms — those require trajectory-level topology (RFC-CLE001 §3.2,
    §3.3) that is Phase 2/4's concern (HPIA, CET), not Phase 1's.
    """

    def lift(
        self,
        artifact: Concept | ConceptDelta,
        *,
        matched_prior: HEKBConceptLike | None,
    ) -> tuple[ConceptMorphism, ...]:
        object_id = _object_id(artifact)
        identity = ConceptMorphism(
            morphism_id=deterministic_id("morphism", "identity", object_id),
            source_id=object_id,
            target_id=object_id,
            morphism_type=MorphismType.IDENTITY,
            provenance=artifact.provenance,
        )
        if matched_prior is None:
            return (identity,)
        inclusion = ConceptMorphism(
            morphism_id=deterministic_id(
                "morphism", "inclusion", matched_prior.id, object_id
            ),
            source_id=matched_prior.id,
            target_id=object_id,
            morphism_type=MorphismType.INCLUSION,
            provenance=artifact.provenance,
        )
        return (identity, inclusion)


__all__ = ["IdentityInclusionMorphismLift", "MorphismLiftStrategy"]
