"""`HEKBStore` / `InMemorySCHEngine` (CLE v3 spec §5/§5.1)."""

from __future__ import annotations

import pytest

from cle.runtime.hekb_store import HEKBStore, InMemorySCHEngine
from cle.runtime.models import InvariantSignature, LiftResult, ProofCertificate


def _lift_result() -> LiftResult:
    return LiftResult(
        concept_id="concept:abc",
        normalized_hash="normalized:xyz",
        morphisms=frozenset({("v0", "v1", "edge")}),
        pullback_limit={"morphisms": []},
        pushout_colimit={"objects": ["v0", "v1"], "morphisms": ["e_0_1"]},
        invariants=InvariantSignature.from_betti((1, 0, 0)),
        compression_ratio=12.5,
        semantic_closure={"betti": (1, 0, 0)},
        proof=ProofCertificate(
            is_valid=True,
            boundary_condition_verified=True,
            functor_axioms_satisfied=True,
        ),
    )


def test_store_writes_morphisms_and_invariants() -> None:
    store = HEKBStore(sch_engine=InMemorySCHEngine())
    result = _lift_result()
    assert store.store(result) is True
    assert store.morphisms_for(result.concept_id) == result.morphisms
    assert store.invariants_for(result.concept_id) == result.invariants


def test_store_caches_l7_closure_and_l6_morphism() -> None:
    sch = InMemorySCHEngine()
    store = HEKBStore(sch_engine=sch)
    result = _lift_result()
    store.store(result)
    assert sch.get_l7_closure(result.normalized_hash) == result.semantic_closure
    assert sch.get_l6_morphism(result.concept_id) == result.pushout_colimit


def test_morphisms_for_unknown_concept_is_none() -> None:
    store = HEKBStore(sch_engine=InMemorySCHEngine())
    assert store.morphisms_for("nope") is None
    assert store.invariants_for("nope") is None


def test_l7_closure_rejects_non_positive_ttl() -> None:
    sch = InMemorySCHEngine()
    with pytest.raises(ValueError, match="ttl_seconds"):
        sch.put_l7_closure(key="k", closure={}, ttl_seconds=0)


def test_l7_closure_expires_after_ttl() -> None:
    sch = InMemorySCHEngine()
    sch.put_l7_closure(key="k", closure={"a": 1}, ttl_seconds=1)
    sch._l7_closures["k"].expires_at = 0.0  # force expiry deterministically
    assert sch.get_l7_closure("k") is None


def test_l7_closure_missing_key_is_none() -> None:
    sch = InMemorySCHEngine()
    assert sch.get_l7_closure("missing") is None


def test_l6_morphism_missing_key_is_none() -> None:
    sch = InMemorySCHEngine()
    assert sch.get_l6_morphism("missing") is None
