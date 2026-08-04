"""`IdentityInclusionMorphismLift` — morphism lifting (RFC-CLE001 Phase 1)."""

from __future__ import annotations

from cle.abi.outputs import Concept, ConceptDelta, MorphismType
from cle.morphism import IdentityInclusionMorphismLift, MorphismLiftStrategy
from conftest import FakeHEKBConcept


def _concept(concept_id: str = "concept-1") -> Concept:
    return Concept(
        id=concept_id,
        frame_id="F",
        centroid=(1.0, 2.0),
        hessian=None,
        provenance=("obs-1",),
    )


def _concept_delta(concept_id: str = "concept-1") -> ConceptDelta:
    return ConceptDelta(
        concept_id=concept_id,
        frame_id="F",
        centroid_shift=(0.1, 0.1),
        provenance=("obs-2",),
    )


def test_identity_inclusion_morphism_lift_satisfies_the_protocol() -> None:
    assert isinstance(IdentityInclusionMorphismLift(), MorphismLiftStrategy)


def test_new_concept_with_no_prior_yields_only_its_identity_morphism() -> None:
    lift = IdentityInclusionMorphismLift()
    concept = _concept()

    morphisms = lift.lift(concept, matched_prior=None)

    assert len(morphisms) == 1
    (identity,) = morphisms
    assert identity.morphism_type is MorphismType.IDENTITY
    assert identity.source_id == concept.id
    assert identity.target_id == concept.id


def test_reinforced_concept_yields_identity_and_inclusion_from_prior() -> None:
    lift = IdentityInclusionMorphismLift()
    delta = _concept_delta()
    prior = FakeHEKBConcept(id="prior-concept", centroid=(0.9, 1.9))

    identity, inclusion = lift.lift(delta, matched_prior=prior)

    assert identity.morphism_type is MorphismType.IDENTITY
    assert identity.source_id == delta.concept_id
    assert identity.target_id == delta.concept_id

    assert inclusion.morphism_type is MorphismType.INCLUSION
    assert inclusion.source_id == prior.id
    assert inclusion.target_id == delta.concept_id


def test_morphism_lift_is_deterministic() -> None:
    lift = IdentityInclusionMorphismLift()
    concept = _concept()
    prior = FakeHEKBConcept(id="prior-concept", centroid=(0.9, 1.9))

    first = lift.lift(concept, matched_prior=prior)
    second = lift.lift(concept, matched_prior=prior)

    assert first == second
