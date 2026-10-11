"""tests/golden/*.json -- fixed reference values for a future Rust port.

Each file pairs a small input with this Python implementation's exact
output, floats stored as `repr()` strings (not JSON numbers) so the exact
decimal text is preserved. These tests only confirm Python's *own*
current implementation still reproduces them -- a Rust port compares its
own output against the same files independently, outside this repo.

Betti numbers and other integers must match exactly; persistence-diagram
and other float values are compared with a small tolerance (`math.isclose`),
since a cross-language, cross-library bottleneck/VR computation is not
expected to reproduce every ULP of Python's own ripser build.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from cle.metrics import (
    InMemoryHEKBSink,
    LineageRecord,
    canonical_record_hash,
    cet_lineage_integrity,
    entropic_reduction,
    functorial_invariance_score,
    hekb_transaction_yield,
)
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.topology.persistence import compute_persistence_diagram, delay_embed

_GOLDEN_DIR = Path(__file__).parent / "golden"


def _load(name: str) -> dict[str, Any]:
    result: dict[str, Any] = json.loads((_GOLDEN_DIR / name).read_text())
    return result


def test_persistence_octagon_matches_golden_reference() -> None:
    golden = _load("persistence_octagon.json")
    points = np.array(
        [[float(x), float(y)] for x, y in golden["input"]["points"]],
        dtype=np.float64,
    )

    diagram = compute_persistence_diagram(
        points, max_dimension=golden["input"]["max_dimension"]
    )

    for dimension_str, expected_pairs in golden["output"]["diagrams"].items():
        actual_pairs = diagram.diagrams[int(dimension_str)]
        assert len(actual_pairs) == len(expected_pairs)
        for (actual_birth, actual_death), (expected_birth, expected_death) in zip(
            actual_pairs, expected_pairs, strict=True
        ):
            assert math.isclose(actual_birth, float(expected_birth), abs_tol=1e-9)
            assert math.isclose(actual_death, float(expected_death), abs_tol=1e-9) or (
                math.isinf(actual_death) and math.isinf(float(expected_death))
            )

    for eps_str, expected_betti in golden["output"]["betti_numbers"].items():
        assert diagram.betti_numbers(float(eps_str)) == tuple(expected_betti)

    assert math.isclose(
        diagram.total_persistence(1),
        float(golden["output"]["total_persistence_dim1"]),
        abs_tol=1e-9,
    )
    assert math.isclose(
        diagram.max_persistence(1),
        float(golden["output"]["max_persistence_dim1"]),
        abs_tol=1e-9,
    )


def _category_from_golden(spec: dict[str, Any]) -> FiniteCategory:
    return FiniteCategory(
        objects=frozenset(spec["objects"]),
        morphisms={
            m["name"]: Morphism(m["name"], m["source"], m["target"])
            for m in spec["morphisms"]
        },
        composition={
            tuple(key.split(",")): value for key, value in spec["composition"].items()
        },
    )


def test_functorial_invariance_score_matches_golden_reference() -> None:
    golden = _load("metrics.json")["functorial_invariance_score"]
    category = _category_from_golden(golden["input"]["category"])

    score = functorial_invariance_score(
        source=category,
        target=category,
        object_map=golden["input"]["object_map"],
        morphism_map=golden["input"]["morphism_map"],
        source_identities=golden["input"]["source_identities"],
        target_identities=golden["input"]["target_identities"],
    )

    assert score == float(golden["output"])


def test_entropic_reduction_matches_golden_reference() -> None:
    golden = _load("metrics.json")["entropic_reduction"]
    weights = {k: float(v) for k, v in golden["input"]["weights"].items()}

    delta = entropic_reduction(weights, golden["input"]["quotient"])

    assert math.isclose(delta, float(golden["output"]), abs_tol=1e-12)


def test_cet_lineage_integrity_matches_golden_reference() -> None:
    golden = _load("metrics.json")["cet_lineage_integrity"]
    genesis_content = golden["input"]["records"][0]["content"]
    assert canonical_record_hash(genesis_content) == golden["genesis_hash"]

    records = tuple(
        LineageRecord(
            content=r["content"],
            prev_hash=(
                None
                if r["prev_hash"] is None
                else canonical_record_hash(genesis_content)
            ),
        )
        for r in golden["input"]["records"]
    )

    assert cet_lineage_integrity(records) == float(golden["output"])


def test_hekb_transaction_yield_matches_golden_reference() -> None:
    golden = _load("metrics.json")["hekb_transaction_yield"]
    sink = InMemoryHEKBSink()
    for submission in golden["input"]["submissions"]:
        sink.submit(submission["candidate_id"], accept=submission["accept"])

    assert hekb_transaction_yield(sink) == float(golden["output"])


def test_delay_embed_matches_golden_reference() -> None:
    golden = _load("metrics.json")["delay_embed"]
    x = np.array(
        [[float(v) for v in row] for row in golden["input"]["x"]], dtype=np.float64
    )

    embedded = delay_embed(x, m=golden["input"]["m"], tau=golden["input"]["tau"])

    expected = [[float(v) for v in row] for row in golden["output"]]
    assert embedded.tolist() == expected
