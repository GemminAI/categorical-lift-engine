"""Calibration tests: answer-known inputs for cle.metrics + cle.topology.

A deviation here means an implementation error, not a modeling choice --
every expected value below is derivable by hand, not tuned to match
whatever the code happened to produce.

The circle-has-one-H1-bar and two-blobs-have-two-H0-bars calibrations
(also part of this phase's brief) already live in
tests/test_topology_persistence.py (test_circle_has_exactly_one_long_lived_h1_bar,
test_circle_has_exactly_one_infinite_h0_bar,
test_two_distant_blobs_have_two_long_h0_bars) -- not duplicated here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

from cle.metrics import (
    LineageRecord,
    TransformationClaim,
    canonical_record_hash,
    cet_lineage_integrity,
    entropic_reduction,
    functorial_invariance_score,
    homotopy_class_determinism,
)
from cle.topology.category_theory import FiniteCategory, Functor, Morphism

# --- Functorial Invariance Score: identity vs. a composition-breaking map --


def _square_category() -> FiniteCategory:
    """A -f-> B -g-> C, plus identities. h := g . f."""
    return FiniteCategory(
        objects=frozenset({"A", "B", "C"}),
        morphisms={
            "id_A": Morphism("id_A", "A", "A"),
            "id_B": Morphism("id_B", "B", "B"),
            "id_C": Morphism("id_C", "C", "C"),
            "f": Morphism("f", "A", "B"),
            "g": Morphism("g", "B", "C"),
            "h": Morphism("h", "A", "C"),
        },
        composition={
            ("id_A", "id_A"): "id_A",
            ("id_B", "id_B"): "id_B",
            ("id_C", "id_C"): "id_C",
            ("f", "id_A"): "f",
            ("id_B", "f"): "f",
            ("g", "id_B"): "g",
            ("id_C", "g"): "g",
            ("g", "f"): "h",
            ("h", "id_A"): "h",
            ("id_C", "h"): "h",
        },
    )


def test_fis_identity_functor_is_exactly_one() -> None:
    category = _square_category()
    identities = {"A": "id_A", "B": "id_B", "C": "id_C"}

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B", "C": "C"},
        morphism_map={name: name for name in category.morphisms},
        source_identities=identities,
        target_identities=identities,
    )

    assert score == 1.0


def test_fis_deliberately_broken_composition_is_below_one() -> None:
    category = _square_category()
    identities = {"A": "id_A", "B": "id_B", "C": "id_C"}
    # Every identity and every OTHER composable pair maps correctly; only
    # ("g", "f") -> "h" is deliberately wrong: h is mapped to "id_C"
    # instead of the true composite "h", breaking exactly one check.
    broken_morphism_map = {name: name for name in category.morphisms}
    broken_morphism_map["h"] = "id_C"

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map={"A": "A", "B": "B", "C": "C"},
        morphism_map=broken_morphism_map,
        source_identities=identities,
        target_identities=identities,
    )

    assert score is not None
    assert 0.0 < score < 1.0


# --- Entropic Reduction: injective quotient vs. a 4-into-2 uniform merge ---


def test_entropic_reduction_zero_for_an_injective_quotient() -> None:
    weights = {f"x{i}": 1.0 for i in range(4)}
    quotient = {f"x{i}": f"x{i}" for i in range(4)}  # no merging at all

    assert entropic_reduction(weights, quotient) == pytest.approx(0.0, abs=1e-12)


def test_entropic_reduction_one_bit_for_four_uniform_merged_into_two() -> None:
    # H(X) = log2(4) = 2 bits (4 uniform elements); H(X/~) = log2(2) = 1
    # bit (2 uniform classes of weight 2 each) -> Delta = 2 - 1 = 1 bit,
    # by hand, independent of entropic_reduction's own implementation.
    weights = {"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0}
    quotient = {"a": "class-1", "b": "class-1", "c": "class-2", "d": "class-2"}

    assert entropic_reduction(weights, quotient) == pytest.approx(1.0, abs=1e-12)


# --- CET Lineage Integrity: one tampered record lowers the score below 1 --


def test_lineage_integrity_below_one_after_tampering_with_one_record() -> None:
    genesis = LineageRecord(content="genesis", prev_hash=None)
    second = LineageRecord(content="second", prev_hash=canonical_record_hash("genesis"))
    third = LineageRecord(content="third", prev_hash=canonical_record_hash("second"))
    intact_chain = (genesis, second, third)
    assert cet_lineage_integrity(intact_chain) == 1.0

    # Tamper with exactly one record's content, after the chain was built:
    # "second"'s own prev_hash still points at the *original* genesis
    # content, but "third"'s prev_hash was computed over the *original*
    # "second" content, which no longer matches the tampered one.
    tampered_second = LineageRecord(
        content="second-TAMPERED", prev_hash=canonical_record_hash("genesis")
    )
    tampered_chain = (genesis, tampered_second, third)

    tampered_score = cet_lineage_integrity(tampered_chain)
    assert tampered_score is not None
    assert tampered_score < 1.0


def test_lineage_integrity_below_one_for_a_non_commuting_transformation_claim() -> None:
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
    non_commuting_claim = TransformationClaim(
        source_functor=identity_functor,
        target_functor=identity_functor,
        components={"A": "id_A", "B": "f"},  # f: A->B is not B->B
    )
    record = LineageRecord(
        content="genesis", prev_hash=None, transformation_claim=non_commuting_claim
    )

    score = cet_lineage_integrity((record,))
    assert score is not None
    assert score < 1.0


# --- Homotopy Class Determinism: 3 real processes, 3 real PYTHONHASHSEEDs -


_DIAGRAM_SCRIPT = textwrap.dedent(
    """
    import numpy as np
    from cle.topology.persistence import compute_persistence_diagram

    rng = np.random.default_rng(42)
    theta = np.linspace(0, 2 * np.pi, 20, endpoint=False)
    points = np.stack([np.cos(theta), np.sin(theta)], axis=1)

    diagram = compute_persistence_diagram(points, max_dimension=1)
    rows = []
    for dimension in sorted(diagram.diagrams):
        pairs = sorted(tuple(pair) for pair in diagram.diagrams[dimension].tolist())
        rows.append((dimension, tuple(repr(pair) for pair in pairs)))
    print(repr(tuple(rows)))
    """
)


def _run_in_subprocess_with_hashseed(hashseed: str) -> str:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hashseed
    result = subprocess.run(
        [sys.executable, "-c", _DIAGRAM_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result.stdout.strip()


def test_homotopy_class_determinism_across_three_processes_and_hashseeds() -> None:
    serialized_results = [
        _run_in_subprocess_with_hashseed(seed) for seed in ("0", "1", "987654321")
    ]

    assert homotopy_class_determinism(serialized_results) == 1.0
