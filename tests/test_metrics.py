"""cle.metrics -- unit and edge-case coverage for the five metrics.

Answer-known calibration scenarios (item 8 of the brief) live in
tests/test_metrics_calibration.py instead; this file covers the ordinary
and edge-case paths each function needs for its own correctness."""

from __future__ import annotations

import pytest

from cle.errors import FunctorialityViolation
from cle.metrics import (
    InMemoryHEKBSink,
    LineageRecord,
    TransformationClaim,
    canonical_record_hash,
    cet_lineage_integrity,
    entropic_reduction,
    functorial_invariance_score,
    hekb_transaction_yield,
    homotopy_class_determinism,
)
from cle.topology.category_theory import FiniteCategory, Functor, Morphism
from cle.topology.natural_transformation import NaturalTransformation

# --- shared fixtures: a tiny 2-object category with an explicit identity ---


def _pair_category() -> FiniteCategory:
    return FiniteCategory(
        objects=frozenset({"A", "B"}),
        morphisms={
            "id_A": Morphism("id_A", "A", "A"),
            "id_B": Morphism("id_B", "B", "B"),
            "f": Morphism("f", "A", "B"),
        },
        composition={
            ("id_A", "id_A"): "id_A",
            ("id_B", "id_B"): "id_B",
            ("f", "id_A"): "f",
            ("id_B", "f"): "f",
        },
    )


# --- 1. functorial_invariance_score -----------------------------------------


def test_fis_identity_functor_scores_one() -> None:
    category = _pair_category()

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B"},
        morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
        source_identities={"A": "id_A", "B": "id_B"},
        target_identities={"A": "id_A", "B": "id_B"},
    )

    assert score == 1.0


def test_fis_is_none_with_nothing_to_check() -> None:
    empty = FiniteCategory(objects=frozenset(), morphisms={}, composition={})

    score = functorial_invariance_score(
        source=empty,
        target=empty,
        object_map={},
        morphism_map={},
        source_identities={},
        target_identities={},
    )

    assert score is None


def test_fis_missing_object_map_entry_counts_as_unsatisfied() -> None:
    category = _pair_category()

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map={"A": "A"},  # "B" missing
        morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
        source_identities={"A": "id_A", "B": "id_B"},
        target_identities={"A": "id_A", "B": "id_B"},
    )

    assert score is not None
    assert score < 1.0


def test_fis_missing_morphism_map_entry_fails_composition_checks() -> None:
    category = _pair_category()

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B"},
        morphism_map={"id_A": "id_A", "id_B": "id_B"},  # "f" missing
        source_identities={"A": "id_A", "B": "id_B"},
        target_identities={"A": "id_A", "B": "id_B"},
    )

    assert score is not None
    assert score < 1.0


# --- 2. homotopy_class_determinism -------------------------------------------


def test_determinism_is_one_when_all_results_match() -> None:
    assert homotopy_class_determinism(["x", "x", "x"]) == 1.0


def test_determinism_is_fractional_when_some_results_differ() -> None:
    assert homotopy_class_determinism(["x", "x", "y"]) == pytest.approx(2 / 3)


def test_determinism_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        homotopy_class_determinism([])


# --- 3. entropic_reduction ----------------------------------------------------


def test_entropic_reduction_zero_for_injective_quotient() -> None:
    weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    quotient = {"a": "a", "b": "b", "c": "c", "d": "d"}

    assert entropic_reduction(weights, quotient) == pytest.approx(0.0)


def test_entropic_reduction_one_bit_for_pairwise_merge_of_four_uniform() -> None:
    weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    quotient = {"a": "ab", "b": "ab", "c": "cd", "d": "cd"}

    assert entropic_reduction(weights, quotient) == pytest.approx(1.0)


def test_entropic_reduction_rejects_non_positive_total_weight() -> None:
    with pytest.raises(ValueError, match="positive"):
        entropic_reduction({"a": 0.0}, {"a": "a"})


def test_entropic_reduction_ignores_zero_weight_elements_in_entropy() -> None:
    weights = {"a": 1.0, "b": 0.0}
    quotient = {"a": "a", "b": "b"}

    # b's weight is 0: contributes nothing to either entropy term, and the
    # 0 * log2(0) term must not raise or produce NaN.
    assert entropic_reduction(weights, quotient) == pytest.approx(0.0)


# --- 4. cet_lineage_integrity --------------------------------------------------


def _valid_transformation_claim() -> TransformationClaim:
    category = FiniteCategory(
        objects=frozenset({"A"}),
        morphisms={"id_A": Morphism("id_A", "A", "A")},
        composition={("id_A", "id_A"): "id_A"},
    )
    identity_functor = Functor(
        source=category,
        target=category,
        object_map={"A": "A"},
        morphism_map={"id_A": "id_A"},
    )
    return TransformationClaim(
        source_functor=identity_functor,
        target_functor=identity_functor,
        components={"A": "id_A"},
    )


def test_lineage_integrity_is_one_for_an_intact_chain() -> None:
    first = LineageRecord(content="genesis", prev_hash=None)
    second = LineageRecord(content="second", prev_hash=canonical_record_hash("genesis"))

    assert cet_lineage_integrity((first, second)) == 1.0


def test_lineage_integrity_empty_chain_is_none() -> None:
    assert cet_lineage_integrity(()) is None


def test_lineage_integrity_first_record_must_have_no_prev_hash() -> None:
    tampered_first = LineageRecord(content="genesis", prev_hash="not-none")

    score = cet_lineage_integrity((tampered_first,))

    assert score is not None
    assert score < 1.0


def test_lineage_integrity_valid_transformation_claim_does_not_lower_score() -> None:
    record = LineageRecord(
        content="genesis",
        prev_hash=None,
        transformation_claim=_valid_transformation_claim(),
    )

    assert cet_lineage_integrity((record,)) == 1.0


def test_lineage_integrity_broken_transformation_claim_lowers_score() -> None:
    category = FiniteCategory(
        objects=frozenset({"A", "B"}),
        morphisms={
            "id_A": Morphism("id_A", "A", "A"),
            "id_B": Morphism("id_B", "B", "B"),
            "f": Morphism("f", "A", "B"),
        },
        composition={
            ("id_A", "id_A"): "id_A",
            ("id_B", "id_B"): "id_B",
            ("f", "id_A"): "f",
            ("id_B", "f"): "f",
        },
    )
    identity_functor = Functor(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B"},
        morphism_map={"id_A": "id_A", "id_B": "id_B", "f": "f"},
    )
    # Components deliberately wrong at "B": claims eta_B = "f" (A -> B),
    # which cannot be a component F(B) -> G(B) = B -> B.
    broken_claim = TransformationClaim(
        source_functor=identity_functor,
        target_functor=identity_functor,
        components={"A": "id_A", "B": "f"},
    )
    record = LineageRecord(
        content="genesis", prev_hash=None, transformation_claim=broken_claim
    )

    # Sanity: confirm the claim really is invalid on its own terms, not
    # just assumed to be.
    with pytest.raises(FunctorialityViolation):
        NaturalTransformation(
            source_functor=broken_claim.source_functor,
            target_functor=broken_claim.target_functor,
            components=broken_claim.components,
        )

    score = cet_lineage_integrity((record,))
    assert score is not None
    assert score < 1.0


# --- 5. hekb_transaction_yield -------------------------------------------------


def test_hekb_yield_is_one_vacuously_for_an_empty_sink() -> None:
    assert hekb_transaction_yield(InMemoryHEKBSink()) == 1.0


def test_hekb_yield_is_fractional_for_mixed_outcomes() -> None:
    sink = InMemoryHEKBSink()
    sink.submit("c1", accept=True)
    sink.submit("c2", accept=False)
    sink.submit("c3", accept=True)

    assert hekb_transaction_yield(sink) == pytest.approx(2 / 3)


def test_hekb_yield_is_one_when_everything_is_committed() -> None:
    sink = InMemoryHEKBSink()
    sink.submit("c1", accept=True)

    assert hekb_transaction_yield(sink) == 1.0
