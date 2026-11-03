"""EXP-RAG-CTP001 Stage B: the 84 fixtures (constraint types C1-C6, 14 examples each).

`tests/golden/ctp001/c<n>_*.json`, designed in `EXP-RAG-CTP001 実験設計書 v0.3`
section 5. What runs today: R1, R2 (must PASS) and R3 (value and reason codes,
the test of hypothesis H1) on the existing verifiers, plus the *shape* of the
R9, compliance and two-axis expectations. R9 and the Constraint Verifier do not
exist yet (Stage C), so their content is not checked.
"""

from __future__ import annotations

import hashlib
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
    check_obligation_transport,
    check_r1,
    check_r2,
    check_r3,
)
from ctp001_builder import GOLDEN_DIR, STAGES, build_all, dump
from ctp001_legacy import legacy_vocabulary

ROOT = Path(__file__).resolve().parent.parent
TYPE_IDS = ["c1", "c2", "c3", "c4", "c5", "c6"]
FILES = sorted(GOLDEN_DIR.glob("c[1-6]_*.json"))
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


def test_there_are_84_fixtures_fourteen_per_type() -> None:
    assert sorted(p.stem for p in FILES) == sorted(
        f"{t}_{n}" for t in TYPE_IDS for n in NAMES
    )
    assert set(build_all()) == {p.name for p in FILES}


# The 13 C1 files that were written before the builder took other types (bbb3f27).
# B7 is not in the list: it was rebuilt (an $800 refund, another internal rule).
C1_BEFORE = {
    "B1": "1a687fdbc38a2350954d9b9fbcc4cfcbf5bfe07a899c2c431cd63d493b12c6ed",
    "B2": "57707c395f9a974387bbdf7198a8a30282f5f4ea94b7f29fd1a555668f18f4c3",
    "B3": "5a5e51b3f7d9c444990e7a376752b60a6503bf0e14664fffab25862791bcb0e4",
    "B4a": "3953da16c7c7f340dc37bc2c457b250ed9bf38eb41c417d62831ebf85d01e1b6",
    "B4b": "b92fccb800e411cf27a714b78538567610fa2ccff36e8f56d001a7bf9cb4d9f2",
    "B5": "7d007da67f6c9f923a8840b2428097966d46c50a45e704ccf3dcfbbc34970d87",
    "B6": "87af63a870db641be0d0b661f9ee2843cd5db22408d656803fa454ba6ce3cfa0",
    "D0": "17b3607ec0d85fe89ba224fc7da21fb6621ba4c87c5563a0e367fb3518b3e0fc",
    "G0": "b6d18f3e6997e6a940d821b74ea683d529f0c9a01837cd23506e9c7aaedcca1e",
    "N0": "77acbf6ab8b8b1e0a0644503f3d1fb57c17affe64ed42bd51edc3dbf6055305e",
    "P0": "ebcbbe4779202b11365e4eb7e65cdf334348c96c7bb1dc1cb42a4521f2df2e1e",
    "U0": "1ca5664ec4d43ed51e7ac2e96bd91a9466af30dbd8d50adae90f87c0021f3524",
    "X0": "0f7bdd722415f741b23947843ac65d5c48538720303af91c457f6babb49c2c32",
}


@pytest.mark.parametrize("name", sorted(C1_BEFORE))
def test_the_thirteen_c1_files_other_than_b7_are_unchanged(name: str) -> None:
    data = (GOLDEN_DIR / f"c1_{name}.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == C1_BEFORE[name]


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


def test_only_d0_fails_r3_in_every_type() -> None:
    """Hypothesis H1: R3 fails the inconsistent declaration (D0) and nothing else."""
    failing = {p.stem for p in FILES if _worst(_run(_load(p))["r3"]) == "FAIL"}
    assert failing == {f"{t}_D0" for t in TYPE_IDS}


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
    props = list(PropertyVocabulary.from_dict(doc["vocabulary"]).properties)
    schemas = doc["constraint_schema"]
    schemas = schemas if isinstance(schemas, list) else [schemas]
    ids = [sc["constraint_id"] for sc in schemas]
    assert doc["constraint_type"] == path.stem[:2].upper()
    assert ids == (["c1", "c2"] if path.stem[:2] == "c6" else [path.stem[:2]])
    # the properties are exactly the non-null fields of the schemas
    fields = ("condition", "scope", "modality", "threshold", "exception", "order")
    assert props == sorted(
        f"{sc['constraint_id']}.{f}" for sc in schemas for f in fields if sc[f]
    )
    assert doc["chain"] == list(STAGES)
    assert doc["applicability_basis"] == "fixture"
    assert list(doc["applicability"]) == ids
    assert set(doc["applicability"].values()) <= {
        "applicable",
        "undetermined",
        "not_applicable",
    }
    assert set(doc["obligations"]) <= set(props)
    assert set(doc["carry_evidence"]) == set(STAGES)
    for entries in doc["carry_evidence"].values():
        assert [e["property"] for e in entries] == props
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
    excluded = [e["constraint_id"] for e in doc["obligation_exclusions"]]
    assert excluded == [
        c for c, v in doc["applicability"].items() if v == "not_applicable"
    ]
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
@pytest.mark.parametrize("cid", TYPE_IDS)
def test_expectations_equal_the_design_table(cid: str, name: str) -> None:
    doc = _load(GOLDEN_DIR / f"{cid}_{name}.json")
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


def _r9(doc: dict[str, Any], mode: str) -> list[CheckResult]:
    return check_obligation_transport(
        RepresentationHistory.from_dict(doc["history"]),
        legacy_vocabulary(doc),  # old names: through the migration adapter
        doc["chain"],
        doc["obligations"],
        doc["applicability"],
        doc["carry_evidence"],
        mode,
    )


@pytest.mark.parametrize("mode", ["m1", "m2"])
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_r9_matches_expected(path: Path, mode: str) -> None:
    doc = _load(path)
    results = _r9(doc, mode.upper())
    expected = doc["expected"]["r9"][mode]
    assert _worst(results) == expected["value"]
    assert sorted({r.reason_code for r in results if r.reason_code}) == sorted(
        expected["reason_codes"]
    )
    stages = {loc.id for r in results for loc in r.locations}
    assert [s for s in STAGES if s in stages] == expected["locations"]
    assert stages <= set(STAGES)
    assert sorted({w.reason_code for r in results for w in r.warnings}) == sorted(
        expected["annotations"]
    )


@pytest.mark.skip(reason="the Constraint Verifier and the two-axis step are Stage C")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_compliance_and_two_axis_content(path: Path) -> None:
    raise AssertionError("checked once the Constraint Verifier exists")


# --- determinism across processes ---------------------------------------------

SCRIPT = """
import json, sys
from pathlib import Path
from cle.representation import (
    PropertyVocabulary, RepresentationHistory, check_r1, check_r2, check_r3,
)
out = {}
for path in sorted(Path(sys.argv[1]).glob("c[1-6]_*.json")):
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
    assert len(json.loads(first)) == len(NAMES) * len(TYPE_IDS)
