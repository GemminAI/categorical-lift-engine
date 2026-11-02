"""EXP-RAG-CTP001 Stage B-1: the 14 fixtures of constraint type C1.

`tests/golden/ctp001/c1_*.json`, designed in `EXP-RAG-CTP001 実験設計書 v0.3`
section 5. What runs today: R1, R2 (must PASS) and R3 (value and reason codes,
the test of hypothesis H1) on the existing verifiers, plus the *shape* of the
R9, compliance and two-axis expectations. R9 and the Constraint Verifier do not
exist yet (Stage C), so their content is not checked.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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
)
from ctp001_c1_builder import GOLDEN_DIR, PROPS, STAGES, build_all, dump

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(GOLDEN_DIR.glob("c1_*.json"))
NAMES = ["B1", "B2", "B3", "B4a", "B4b", "B5", "B6", "B7"]
NAMES += ["D0", "G0", "N0", "P0", "U0", "X0"]
RANK = {"PASS": 0, "UNVERIFIABLE": 1, "FAIL": 2}


def _load(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


def _worst(results: list[CheckResult]) -> str:
    """v0.3 section 3 (report F13): the value of a rule is its worst result."""
    return max((r.status for r in results), key=lambda s: RANK[s])


def _run(doc: dict[str, Any]) -> dict[str, list[CheckResult]]:
    history = RepresentationHistory.from_dict(doc["history"])
    vocabulary = PropertyVocabulary.from_dict(doc["vocabulary"])
    return {
        "r1": check_r1(history),
        "r2": check_r2(history),
        "r3": check_r3(history, vocabulary),
    }


def test_there_are_fourteen_c1_fixtures() -> None:
    assert sorted(p.stem for p in FILES) == sorted(f"c1_{n}" for n in NAMES)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_file_is_what_the_builder_writes(path: Path) -> None:
    assert path.read_text(encoding="utf-8") == dump(build_all()[path.name])


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_r1_and_r2_pass(path: Path) -> None:
    doc = _load(path)
    results = _run(doc)
    for rule in ("r1", "r2"):
        assert doc["expected"][rule]["value"] == "PASS"
        assert _worst(results[rule]) == "PASS", [
            (r.status, r.reason_code) for r in results[rule]
        ]


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_r3_matches_expected(path: Path) -> None:
    doc = _load(path)
    results = _run(doc)["r3"]
    expected = doc["expected"]["r3"]
    assert _worst(results) == expected["value"]
    codes = sorted({r.reason_code for r in results if r.reason_code})
    assert codes == expected["reason_codes"]


def test_only_d0_fails_r3() -> None:
    """Hypothesis H1: R3 fails the inconsistent declaration (D0) and nothing else."""
    failing = {p.stem for p in FILES if _worst(_run(_load(p))["r3"]) == "FAIL"}
    assert failing == {"c1_D0"}


# --- shape of the expectations that Stage C will check ------------------------

R9_VALUES = {"PASS", "FAIL", "UNVERIFIABLE"}
R9_CODES = {
    "OBLIGATION_DECLARED_LOST",
    "OBLIGATION_LOST_BY_EVIDENCE",
    "PRESERVED_CONTRADICTED_BY_EVIDENCE",
    "DECLARED_LOST_CONTRADICTED_BY_EVIDENCE",
    "OBLIGATION_CARRY_MISSING",
}
JUDGEMENTS = {"PASS", "FAIL", "UNVERIFIABLE", "NOT_APPLICABLE"}
CLASSES = {
    "CARRIED_COMPLIED",
    "CARRIED_VIOLATED",
    "LOST_COMPLIED",
    "LOST_VIOLATED",
    "UNDETERMINED",
}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_expectation_shapes(path: Path) -> None:
    doc = _load(path)
    assert doc["chain"] == list(STAGES)
    assert doc["applicability_basis"] == "fixture"
    assert doc["applicability"]["c1"] in {
        "applicable",
        "undetermined",
        "not_applicable",
    }
    assert set(doc["obligations"]) <= set(PROPS)
    assert set(doc["carry_evidence"]) == set(STAGES)
    for entries in doc["carry_evidence"].values():
        assert [e["property"] for e in entries] == list(PROPS)
        for e in entries:
            assert e["status"] in {"preserved", "lost"}
            assert (e["basis"], e["source"]) == ("evidence", "verifier")
            assert e["evidence_ref"]
    assert set(doc["texts"]) == {
        "knowledge",
        "f1_context",
        "f2_decision",
        "f3_action",
    }
    expected = doc["expected"]
    for mode in ("m1", "m2"):
        r9 = expected["r9"][mode]
        assert r9["value"] in R9_VALUES
        assert set(r9["reason_codes"]) <= R9_CODES
        assert set(r9["locations"]) <= set(STAGES)
        assert (r9["value"] == "PASS") == (not r9["reason_codes"])
        assert set(r9["annotations"]) <= {"APPLICABILITY_UNDETERMINED"}
    compliance = expected["compliance"]
    assert set(compliance) == {"L1", "L2", "L3", "f3", "overall"}
    assert set(compliance.values()) <= JUDGEMENTS
    axes = expected["two_axis"]
    assert axes["class"] in CLASSES | {None}
    assert (axes["class"] is None) == (not doc["obligations"])
    assert set(axes["undetermined_axes"]) <= {"retention", "compliance"}


# The v0.3 section 5 table, written out independently of the builder: the m1/m2
# values, the location, the codes where the table names them, the overall
# compliance and the two-axis class.
SECTION5: dict[str, tuple[str, str, str | None, str | None, str, str | None]] = {
    "G0": ("PASS", "PASS", None, None, "PASS", "CARRIED_COMPLIED"),
    "P0": ("PASS", "PASS", None, None, "PASS", "CARRIED_COMPLIED"),
    "D0": ("FAIL", "FAIL", "f1", "ok", "FAIL", "LOST_VIOLATED"),
    "B1": ("FAIL", "FAIL", "f1", "ok", "FAIL", "LOST_VIOLATED"),
    "B2": ("FAIL", "FAIL", "f1", "ok", "FAIL", "LOST_VIOLATED"),
    "B3": ("FAIL", "FAIL", "f1", "ok", "FAIL", "LOST_VIOLATED"),
    "B4a": ("FAIL", "FAIL", "f2", None, "FAIL", "LOST_VIOLATED"),
    "B4b": ("PASS", "PASS", None, None, "FAIL", "CARRIED_VIOLATED"),
    "B5": ("PASS", "PASS", None, None, "FAIL", "CARRIED_VIOLATED"),
    "B6": ("PASS", "FAIL", "f1", None, "FAIL", "LOST_VIOLATED"),
    "B7": ("FAIL", "FAIL", "f1", None, "PASS", "LOST_COMPLIED"),
    "X0": ("FAIL", "UNVERIFIABLE", "f1", None, "PASS", "UNDETERMINED"),
    "N0": ("PASS", "PASS", None, None, "NOT_APPLICABLE", None),
    "U0": ("FAIL", "FAIL", "f1", None, "UNVERIFIABLE", "UNDETERMINED"),
}


@pytest.mark.parametrize("name", NAMES)
def test_expectations_equal_the_design_table(name: str) -> None:
    doc = _load(GOLDEN_DIR / f"c1_{name}.json")
    m1_value, m2_value, location, codes, overall, cls = SECTION5[name]
    expected = doc["expected"]
    assert expected["r9"]["m1"]["value"] == m1_value
    assert expected["r9"]["m2"]["value"] == m2_value
    assert expected["compliance"]["overall"] == overall
    assert expected["two_axis"]["class"] == cls
    for mode in ("m1", "m2"):
        if location is not None and expected["r9"][mode]["value"] != "PASS":
            assert expected["r9"][mode]["locations"] == [location]
    if codes == "ok":
        assert expected["r9"]["m1"]["reason_codes"] == ["OBLIGATION_DECLARED_LOST"]
        assert expected["r9"]["m2"]["reason_codes"] == ["OBLIGATION_LOST_BY_EVIDENCE"]
    if name == "B6":
        assert expected["r9"]["m2"]["reason_codes"] == [
            "PRESERVED_CONTRADICTED_BY_EVIDENCE"
        ]
    if name == "X0":
        assert expected["r9"]["m2"]["reason_codes"] == [
            "DECLARED_LOST_CONTRADICTED_BY_EVIDENCE"
        ]
    if name == "U0":
        assert expected["r9"]["m1"]["annotations"] == ["APPLICABILITY_UNDETERMINED"]


@pytest.mark.skip(reason="R9 と Verifier は Stage C")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_r9_compliance_and_two_axis_content(path: Path) -> None:
    raise AssertionError("checked once R9 and the Constraint Verifier exist")


# --- determinism across processes ---------------------------------------------

SCRIPT = """
import json, sys
from pathlib import Path
from cle.representation import (
    PropertyVocabulary, RepresentationHistory, check_r1, check_r2, check_r3,
)
out = {}
for path in sorted(Path(sys.argv[1]).glob("c1_*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    h = RepresentationHistory.from_dict(doc["history"])
    v = PropertyVocabulary.from_dict(doc["vocabulary"])
    out[path.name] = [
        [r.to_dict() for r in check(*args)]
        for check, args in ((check_r1, (h,)), (check_r2, (h,)), (check_r3, (h, v)))
    ]
print(json.dumps(out, sort_keys=True))
"""


def _fresh_process(hash_seed: str) -> str:
    env = {
        **os.environ,
        "PYTHONHASHSEED": hash_seed,
        "PYTHONPATH": str(ROOT / "src"),
    }
    done = subprocess.run(
        [sys.executable, "-c", SCRIPT, str(GOLDEN_DIR)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


def test_two_fresh_processes_give_identical_results() -> None:
    first, second = _fresh_process("1"), _fresh_process("2")
    assert first == second
    assert len(json.loads(first)) == len(NAMES)
