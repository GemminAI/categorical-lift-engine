"""EXP-RAG-CTP001 step 6 on the Schema Graph fixtures (`Constraint Schema 仕様 v0.4`).

1. R9 on the 84 new fixtures in M1 and M2 equals the builder's expectation.
2. Old (property) against new (path) R9: the same result where the unit is the same.
3. (the sentence audit is in `test_ctp001_v2_audit.py`)
4. The two-axis class follows from R9's M2 value and the overall compliance.

The value of a compliance judgement itself is not checked here: it is the Constraint
Verifier's stage, so those cells stay as the fixtures hold them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ctp001_builder import GOLDEN_DIR, STAGES
from ctp001_v2_builder import CHANGED, GOLDEN_V2_DIR
from ctp001_v2_r9 import (
    MODES,
    R9_EVIDENCE_FIELDS,
    findings,
    r9_applicability,
    r9_evidence,
    run_r9,
    summary,
)

FILES = sorted(GOLDEN_V2_DIR.glob("c[1-6]_*.json"))
CELLS = [(p, m) for p in FILES for m in MODES]
CELL_IDS = [f"{p.stem}-{m}" for p, m in CELLS]
MAP: dict[str, Any] = json.loads(
    (GOLDEN_V2_DIR / "migration_map.json").read_text(encoding="utf-8")
)
OLD_TO_PATH_LABEL = {
    m["old_property"]: m["paths"][0]["path_label"] for m in MAP["mappings"]
}
SAME_TEMPLATES = {"T.condition", "T.scope", "T.modality", "T.exception"}
CHANGED_TEMPLATES = {"T.threshold", "T.ordering"}


def _load(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


# --- 1. R9 on the new fixtures ---------------------------------------------------


@pytest.mark.parametrize(("path", "mode"), CELLS, ids=CELL_IDS)
def test_r9_on_the_new_fixtures_matches_the_builder(path: Path, mode: str) -> None:
    doc = _load(path)
    got = summary(run_r9(doc, mode), doc["chain"])
    assert got == doc["expected"]["r9"][mode.lower()]


def test_r9_receives_the_state_per_path_and_stage_and_nothing_of_the_parts() -> None:
    doc = _load(GOLDEN_V2_DIR / "c4_B2.json")
    sent = r9_evidence(doc)
    assert set(sent) == set(STAGES)
    for entries in sent.values():
        assert all(tuple(e) == R9_EVIDENCE_FIELDS for e in entries)
    flat = json.dumps(sent)
    for name in ("components", "after_edge", "path_state", "path_label", "T.ordering"):
        assert name not in flat
    # the stages' declarations are the morphisms' preserved/lost, over path ids
    for m in doc["history"]["morphisms"]:
        assert all(p.startswith("path:") for p in (*m["preserved"], *m["lost"]))


def test_r9_cannot_tell_the_components_apart() -> None:
    """Dropping the parts changes nothing: two docs that differ only in which
    component broke, with the same path state, give R9 the same result."""
    doc = _load(GOLDEN_V2_DIR / "c4_B3.json")  # the value of the threshold changed
    other = json.loads(json.dumps(doc))
    for entries in other["carry_evidence"].values():
        for e in entries:
            for c in e["components"]:
                if c["status"] == "L":
                    c["name"] = "renamed"
    assert r9_evidence(doc) == r9_evidence(other)
    for mode in MODES:
        assert findings(run_r9(doc, mode)) == findings(run_r9(other, mode))


def test_the_applicability_is_keyed_by_path_for_r9() -> None:
    doc = _load(GOLDEN_V2_DIR / "c6_U0.json")
    keyed = r9_applicability(doc)
    assert set(keyed) == set(doc["path_definitions"])
    assert {keyed[p] for p in keyed} == {"undetermined", "not_applicable"}
    # the constraint-keyed map of the fixture does not reach R9 (a path id has no dot)
    assert not set(doc["applicability"]) & set(doc["vocabulary"]["properties"])


# --- 2. old against new ----------------------------------------------------------


def _old(name: str) -> dict[str, Any]:
    return _load(GOLDEN_DIR / name)


def _by_label(doc: dict[str, Any]) -> dict[str, str]:
    return {d["path_label"]: pid for pid, d in doc["path_definitions"].items()}


def _renamed(
    old_doc: dict[str, Any], new_doc: dict[str, Any], mode: str
) -> dict[str, set[Any]]:
    """The old findings, keyed by the path that the old property became."""
    label_to_id = _by_label(new_doc)
    raw = findings(run_r9(old_doc, mode))
    return {label_to_id[OLD_TO_PATH_LABEL[p]]: f for p, f in raw.items()}


def _templates(doc: dict[str, Any]) -> dict[str, str]:
    return {pid: d["template_id"] for pid, d in doc["path_definitions"].items()}


@pytest.mark.parametrize(("path", "mode"), CELLS, ids=CELL_IDS)
def test_same_unit_paths_give_the_result_of_the_old_property(
    path: Path, mode: str
) -> None:
    """condition, scope, modality, exception: per example, mode, stage and path."""
    new_doc, old_doc = _load(path), _old(path.name)
    old = _renamed(old_doc, new_doc, mode)
    new = findings(run_r9(new_doc, mode))
    templates = _templates(new_doc)
    same = {p for p, t in templates.items() if t in SAME_TEMPLATES}
    for pid in same:
        assert new.get(pid, set()) == old.get(pid, set()), (
            path.stem,
            mode,
            new_doc["path_definitions"][pid]["path_label"],
        )


def _differences() -> list[tuple[str, str, str, str]]:
    """(example, mode, stage, path label) where a changed-granularity path differs."""
    out = []
    for path, mode in CELLS:
        new_doc, old_doc = _load(path), _old(path.name)
        old = _renamed(old_doc, new_doc, mode)
        new = findings(run_r9(new_doc, mode))
        for pid, template in _templates(new_doc).items():
            if template not in CHANGED_TEMPLATES:
                continue
            a, b = old.get(pid, set()), new.get(pid, set())
            for stage in STAGES:
                if {f for f in a if f[0] == stage} != {f for f in b if f[0] == stage}:
                    label = new_doc["path_definitions"][pid]["path_label"]
                    out.append((path.stem, mode, stage, label))
    return out


def test_changed_granularity_paths_differ_from_the_old_property_nowhere() -> None:
    """threshold and ordering: no example, mode or stage gives a different result.

    The path state is the aggregate of its components, a lost component loses the
    path, and the old property was lost exactly then; so the components change what
    the Carry Evidence says about *why* (below), not what R9 finds.
    """
    assert _differences() == []


def _lost_components(doc: dict[str, Any], label: str, stage: str) -> list[str]:
    entry = next(e for e in doc["carry_evidence"][stage] if e["path_label"] == label)
    return [c["name"] for c in entry["components"] if c["status"] != "P"]


def test_a_partial_break_names_the_component_and_r9_finds_the_same_loss() -> None:
    """The cases where the granularity matters: one component of a threshold or of the
    ordering breaks. R9 finds the path lost at f1, as it found the old property."""
    seen = []
    for (cid, name, prop), (broken, _reason) in CHANGED.items():
        label = OLD_TO_PATH_LABEL[prop]
        doc = _load(GOLDEN_V2_DIR / f"{cid}_{name}.json")
        template = next(
            d["template_id"]
            for d in doc["path_definitions"].values()
            if d["path_label"] == label
        )
        if template not in CHANGED_TEMPLATES:
            continue
        assert _lost_components(doc, label, "f1") == list(broken)
        seen.append((f"{cid}_{name}", label, broken))
        old_doc = _old(f"{cid}_{name}.json")
        pid = _by_label(doc)[label]
        for mode in MODES:
            new = findings(run_r9(doc, mode))[pid]
            assert any(f[0] == "f1" and f[2] == "FAIL" for f in new)
            assert new == _renamed(old_doc, doc, mode)[pid]
    assert sorted(seen) == [
        ("c1_B3", "c1.threshold", ("value",)),
        ("c3_B3", "c3.threshold", ("value",)),
        ("c4_B2", "c4.ordering", ("after_edge",)),
        ("c4_B3", "c4.threshold", ("value",)),
        ("c5_B3", "c5.threshold", ("value",)),
        ("c6_B3", "c1.threshold", ("value",)),
    ]


# --- 4. the two axes -------------------------------------------------------------

RETENTION = {"PASS": "CARRIED", "FAIL": "LOST", "UNVERIFIABLE": "UNDETERMINED"}
ADHERENCE = {
    "PASS": "COMPLIED",
    "FAIL": "VIOLATED",
    "UNVERIFIABLE": "UNDETERMINED",
}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_two_axis_follows_from_r9_m2_and_the_overall_compliance(path: Path) -> None:
    doc = _load(path)
    axes = doc["expected"]["two_axis"]
    overall = doc["expected"]["compliance"]["overall"]
    m2 = doc["expected"]["r9"]["m2"]["value"]
    # R9's own M2 value, not the builder's copy of it
    assert summary(run_r9(doc, "M2"), doc["chain"])["value"] == m2
    if not doc["obligations"]:
        assert overall == "NOT_APPLICABLE"
        assert axes == {
            "retention": "NOT_APPLICABLE",
            "compliance": "NOT_APPLICABLE",
            "class": None,
            "undetermined_axes": [],
        }
        return
    retention, adherence = RETENTION[m2], ADHERENCE[overall]
    assert axes["retention"] == retention
    assert axes["compliance"] == adherence
    undetermined = [
        a
        for a, v in (("retention", retention), ("compliance", adherence))
        if v == "UNDETERMINED"
    ]
    assert axes["undetermined_axes"] == undetermined
    assert axes["class"] == (
        "UNDETERMINED" if undetermined else f"{retention}_{adherence}"
    )


def test_all_five_classes_and_the_not_applicable_case_occur() -> None:
    classes = {_load(p)["expected"]["two_axis"]["class"] for p in FILES}
    assert classes == {
        "CARRIED_COMPLIED",
        "CARRIED_VIOLATED",
        "LOST_COMPLIED",
        "LOST_VIOLATED",
        "UNDETERMINED",
        None,
    }


@pytest.mark.skip(
    reason="the value of the compliance judgements is the Constraint Verifier's stage"
)
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_compliance_values(path: Path) -> None:
    raise AssertionError("checked once the Constraint Verifier exists")
