"""tests/golden/representation_*.json: one FAIL and one UNVERIFIABLE example
per rule R1-R8 (CLE v0.3 section 3.1).

`expected` in each file is written from the design, not from this
implementation; `recorded_inputs_sha256` is this implementation's own digest,
pinned so a port can compare.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from cle.representation import (
    CheckResult,
    PropertyVocabulary,
    RepresentationHistory,
    check_r1,
    check_r2,
    check_r3,
    check_r4,
    check_r5,
    check_r6,
    check_r7,
    check_r8,
)

GOLDEN = Path(__file__).parent / "golden"
FILES = sorted(GOLDEN.glob("representation_*.json"))


def _run(rule: str, inputs: dict[str, Any]) -> list[CheckResult]:
    def hist(key: str) -> RepresentationHistory | None:
        return RepresentationHistory.from_dict(inputs[key]) if key in inputs else None

    history = hist("history")
    assert history is not None
    if rule == "R1":
        return check_r1(history)
    if rule == "R2":
        return check_r2(history)
    if rule == "R3":
        vocab = inputs.get("vocabulary")
        return check_r3(
            history, None if vocab is None else PropertyVocabulary.from_dict(vocab)
        )
    if rule == "R4":
        return check_r4(history)
    if rule == "R5":
        return check_r5(history)
    if rule == "R6":
        return check_r6(history, hist("previous"))
    if rule == "R7":
        return check_r7(history, inputs.get("eligibility"))
    target = hist("target")
    assert target is not None
    return check_r8(history, target, inputs["state_map"], inputs["morphism_map"])


def test_every_rule_has_a_fail_and_an_unverifiable_example() -> None:
    seen: set[tuple[str, str]] = set()
    for path in FILES:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for entry in doc["expected"]:
            seen.add((doc["rule"], entry["status"]))
    for rule in (f"R{n}" for n in range(1, 9)):
        assert (rule, "FAIL") in seen
        assert (rule, "UNVERIFIABLE") in seen


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_golden_case(path: Path) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    results = _run(doc["rule"], doc["inputs"])
    got = [
        {
            "status": r.status,
            "reason_code": r.reason_code,
            "locations": [loc.to_dict() for loc in r.locations],
        }
        for r in results
    ]
    assert got == doc["expected"]
    assert all(r.rule == doc["rule"] for r in results)
    assert results[0].inputs_sha256 == doc["recorded_inputs_sha256"]
    # run again from the same file: bit-identical, inputs_sha256 included
    assert _run(doc["rule"], doc["inputs"]) == results
