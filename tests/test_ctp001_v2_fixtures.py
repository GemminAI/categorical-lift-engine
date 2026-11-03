"""EXP-RAG-CTP001 on the canonical Schema (`Constraint Schema 仕様 v0.4`):
`tests/golden/ctp001_v2/`.

The 84 new fixtures, the old-property-to-path map and its gaps check. R1/R2 must PASS
and R3 must FAIL only on D0. What R9, compliance and the two-axis class give on the
new fixtures is step 6 and is not checked here.
"""

from __future__ import annotations

import json
import re
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
from ctp001_builder import GOLDEN_DIR, STAGES, dump
from ctp001_schema_graph import (
    SCHEMA_GRAPH_VERSION,
    TEMPLATE_BY_ID,
    TEMPLATES,
    aggregate,
    path_id,
)
from ctp001_v2_builder import (
    CHANGED,
    FORM_MIGRATIONS,
    GOLDEN_V2_DIR,
    QUANTITY,
    build_all,
    canonical_schema,
    detect_old_forms,
    distinct_paths,
    migration_map,
    migration_md,
    old_properties,
)

FILES = sorted(GOLDEN_V2_DIR.glob("c[1-6]_*.json"))
OLD_FILES = sorted(GOLDEN_DIR.glob("c[1-6]_*.json"))
RANK = {"PASS": 0, "UNVERIFIABLE": 1, "FAIL": 2}


def _load(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


def _worst(results: list[CheckResult]) -> str:
    return max((r.status for r in results), key=lambda s: RANK[s])


def _schemas(doc: dict[str, Any]) -> list[dict[str, Any]]:
    s = doc["constraint_schema"]
    return s if isinstance(s, list) else [s]


def test_the_new_fixtures_are_the_84_of_the_old_directory() -> None:
    assert len(FILES) == 84
    assert [p.name for p in FILES] == [p.name for p in OLD_FILES]
    assert set(build_all()) == {p.name for p in FILES}


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_file_is_what_the_builder_writes(path: Path) -> None:
    assert path.read_text(encoding="utf-8") == dump(build_all()[path.name])


def test_the_migration_files_are_what_the_builder_writes() -> None:
    written = json.dumps(migration_map(), indent=2, sort_keys=True, ensure_ascii=False)
    assert (GOLDEN_V2_DIR / "migration_map.json").read_text("utf-8") == written + "\n"
    assert (GOLDEN_V2_DIR / "MIGRATION.md").read_text("utf-8") == migration_md()


# --- R1, R2, R3 ---------------------------------------------------------------


def _run(doc: dict[str, Any]) -> dict[str, list[CheckResult]]:
    history = RepresentationHistory.from_dict(doc["history"])
    vocabulary = PropertyVocabulary.from_dict(doc["vocabulary"])
    return {
        "r1": check_r1(history),
        "r2": check_r2(history),
        "r3": check_r3(history, vocabulary),
    }


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
    assert sorted({r.reason_code for r in results if r.reason_code}) == sorted(
        expected["reason_codes"]
    )


def test_only_d0_fails_r3_in_every_type() -> None:
    failing = {p.stem for p in FILES if _worst(_run(_load(p))["r3"]) == "FAIL"}
    assert failing == {f"c{n}_D0" for n in range(1, 7)}


# --- the shape of a new fixture ------------------------------------------------


SCHEMA_FIELDS = {
    "constraint_id",
    "constraint_kind",
    "condition",
    "scope",
    "modality",
    "threshold",
    "exception",
    "ordering",
}
KINDS = {
    "conditional_permission",
    "scope_restriction",
    "prohibition",
    "ordering",
    "exception",
}
DECIMAL = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]+)?")


def _check_canonical(sc: dict[str, Any]) -> None:
    """Constraint Schema 仕様 v0.4 section 2: the fields and their types."""
    assert set(sc) == SCHEMA_FIELDS
    assert isinstance(sc["constraint_id"], str)
    assert sc["constraint_kind"] in KINDS
    for f in ("condition", "scope"):
        assert sc[f] is None or isinstance(sc[f], str)
    assert sc["modality"] in {None, "may", "must", "must_not"}
    thr = sc["threshold"]
    if thr is not None:
        assert set(thr) == {"quantity", "value", "unit", "comparator"}
        assert isinstance(thr["quantity"], str) and thr["quantity"]
        assert isinstance(thr["value"], str) and DECIMAL.fullmatch(thr["value"])
        assert isinstance(thr["unit"], str) and thr["unit"]
        assert thr["comparator"] in {">", ">=", "<", "<=", "=="}
    if sc["exception"] is not None:
        assert set(sc["exception"]) == {"exempt"}
        assert isinstance(sc["exception"]["exempt"], str)
    if sc["ordering"] is not None:
        assert set(sc["ordering"]) == {"action", "after"}
        assert all(isinstance(v, str) and v for v in sc["ordering"].values())


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_schema_is_in_the_canonical_form(path: Path) -> None:
    for sc in _schemas(_load(path)):
        _check_canonical(sc)
        assert detect_old_forms(sc) == set()


def test_the_c4_quantity_and_the_ordering_after_name_the_same_event() -> None:
    """Section 4: C4's threshold quantity points at the `after` event (weak check:
    they share a content word; the pointing itself is not a field of the schema)."""
    sc = _schemas(_load(GOLDEN_V2_DIR / "c4_G0.json"))[0]
    quantity = set(sc["threshold"]["quantity"].split())
    assert quantity & set(sc["ordering"]["after"].split())


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_vocabulary_and_definitions_are_paths(path: Path) -> None:
    doc = _load(path)
    vocab = list(PropertyVocabulary.from_dict(doc["vocabulary"]).properties)
    defs = doc["path_definitions"]
    assert doc["schema_graph_version"] == SCHEMA_GRAPH_VERSION
    assert vocab == sorted(defs)
    fields = ("condition", "scope", "modality", "threshold", "exception", "ordering")
    expected_count = sum(1 for sc in _schemas(doc) for f in fields if sc[f] is not None)
    assert len(vocab) == expected_count
    for pid, d in defs.items():
        assert set(d) == {
            "path_label",
            "constraint_id",
            "template_id",
            "constraint_value",
            "schema_graph_version",
        }
        assert d["schema_graph_version"] == SCHEMA_GRAPH_VERSION
        assert pid == path_id(d["constraint_id"], d["template_id"])
        assert d["path_label"] == (
            f"{d['constraint_id']}.{d['template_id'].removeprefix('T.')}"
        )
    assert set(doc["obligations"]) <= set(vocab)
    assert doc["obligations"] == sorted(doc["obligations"])


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_components_are_fixed_by_the_template_and_aggregate_by_the_rule(
    path: Path,
) -> None:
    doc = _load(path)
    defs = doc["path_definitions"]
    assert list(doc["carry_evidence"]) == list(STAGES)
    for entries in doc["carry_evidence"].values():
        assert [e["property"] for e in entries] == sorted(defs)
        for e in entries:
            template = TEMPLATE_BY_ID[defs[e["property"]]["template_id"]]
            comps = e["components"]
            # the number of components comes from the template, never reduced
            assert [c["name"] for c in comps] == list(template.components)
            assert all(c["status"] in {"P", "L", "U"} for c in comps)
            assert all(c["evidence_ref"] for c in comps)
            assert all((c["reason"] is None) == (c["status"] == "P") for c in comps)
            state = aggregate(c["status"] for c in comps)
            assert e["path_state"] == state
            assert e["status"] == ("preserved" if state == "P" else "lost")
            assert (e["basis"], e["source"]) == ("evidence", "verifier")
            assert e["path_label"] == defs[e["property"]]["path_label"]


def _old(name: str) -> dict[str, Any]:
    return _load(GOLDEN_DIR / name)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_new_statuses_carry_the_old_ones(path: Path) -> None:
    """Each old property and its path say the same thing at every stage."""
    doc, old = _load(path), _old(path.name)
    old_to_path = {
        m["old_property"]: m["paths"][0]["path_label"]
        for m in migration_map()["mappings"]
    }
    label_to_id = {d["path_label"]: pid for pid, d in doc["path_definitions"].items()}
    for stage in STAGES:
        new = {e["path_label"]: e["status"] for e in doc["carry_evidence"][stage]}
        for e in old["carry_evidence"][stage]:
            assert new[old_to_path[e["property"]]] == e["status"]
    assert doc["obligations"] == sorted(
        label_to_id[old_to_path[p]] for p in old["obligations"]
    )
    assert doc["applicability"] == old["applicability"]
    assert doc["texts"] == old["texts"]
    assert doc["expected"] == old["expected"]


def test_partial_breaks_name_the_component_that_broke() -> None:
    for (cid, name, prop), (broken, _reason) in CHANGED.items():
        doc = _load(GOLDEN_V2_DIR / f"{cid}_{name}.json")
        label = prop.replace(".order", ".ordering")
        entry = next(e for e in doc["carry_evidence"]["f1"] if e["path_label"] == label)
        assert entry["path_state"] == "L"
        lost = {c["name"] for c in entry["components"] if c["status"] == "L"}
        assert lost == set(broken)
        # a path that is only partly broken still has components that are preserved
        assert len(lost) < len(entry["components"]) or len(entry["components"]) == 1


def test_a_lost_clause_loses_every_component_of_the_path() -> None:
    doc = _load(GOLDEN_V2_DIR / "c3_B1.json")
    for stage in STAGES:
        for e in doc["carry_evidence"][stage]:
            assert {c["status"] for c in e["components"]} == {"L"}
            assert {c["reason"] for c in e["components"]} == {"ABSENT_IN_OUTPUT"}


# --- step 5: the migration map -------------------------------------------------


def test_every_old_property_has_a_path_and_every_path_has_an_origin() -> None:
    mmap = _load(GOLDEN_V2_DIR / "migration_map.json")
    old_from_files = {
        p for f in OLD_FILES for p in _load(f)["vocabulary"]["properties"]
    }
    new_from_files = {
        pid: d["path_label"]
        for f in FILES
        for pid, d in _load(f)["path_definitions"].items()
    }
    mapped = {m["old_property"]: m["paths"] for m in mmap["mappings"]}
    assert set(mapped) == old_from_files == set(old_properties())
    assert all(paths for paths in mapped.values())  # at least one path each
    mapped_ids = {p["path_id"]: p["path_label"] for ps in mapped.values() for p in ps}
    for pid, label in mapped_ids.items():
        assert new_from_files[pid] == label
    origins = {n["path_id"]: n["origin"] for n in mmap["new_paths"]}
    assert set(origins) == set(new_from_files)  # no path without an origin
    for pid, origin in origins.items():
        if origin["kind"] == "migrated":
            assert origin["old_properties"]
            assert all(
                pid in {p["path_id"] for p in mapped[o]}
                for o in origin["old_properties"]
            )
        else:
            assert origin["kind"] == "added"
            assert origin["reason"]
    # a migrated path is the image of the old properties that name it, and only those
    for old_prop, paths in mapped.items():
        for p in paths:
            assert old_prop in origins[p["path_id"]]["old_properties"]


def test_granularity_follows_the_template() -> None:
    mmap = _load(GOLDEN_V2_DIR / "migration_map.json")
    for m in mmap["mappings"]:
        for p in m["paths"]:
            assert p["granularity"] == TEMPLATE_BY_ID[p["template_id"]].granularity
    changed = {
        p["template_id"]
        for m in mmap["mappings"]
        for p in m["paths"]
        if p["granularity"] == "changed"
    }
    assert (
        changed
        == {"T.threshold", "T.ordering"}
        == set(mmap["granularity_changed_templates"])
    )
    same = {
        p["template_id"]
        for m in mmap["mappings"]
        for p in m["paths"]
        if p["granularity"] == "same"
    }
    assert same == {t.template_id for t in TEMPLATES} - changed


def test_the_human_readable_map_names_every_old_property_and_path() -> None:
    text = (GOLDEN_V2_DIR / "MIGRATION.md").read_text(encoding="utf-8")
    for prop in old_properties():
        assert f"`{prop}`" in text
    for gp in distinct_paths():
        assert f"`{gp.label}`" in text


def test_path_counts_per_template() -> None:
    counts: dict[str, int] = {}
    for gp in distinct_paths():
        counts[gp.template_id] = counts.get(gp.template_id, 0) + 1
    assert counts == {
        "T.condition": 1,
        "T.scope": 1,
        "T.modality": 4,
        "T.threshold": 4,
        "T.exception": 1,
        "T.ordering": 1,
    }


@pytest.mark.skip(reason="step 6: R9, compliance and two-axis on the new fixtures")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_r9_compliance_and_two_axis_content(path: Path) -> None:
    raise AssertionError("checked in step 6 (old vs new R9)")


# --- step 3: T.exception states from the text (section 7.4) -----------------------

EXEMPT = "service accounts"
# section 8.4, exception expressions v1
EXCEPT_EXPR = re.compile(
    r"\b(except|except for|excluding|other than|with the exception of|exempt|"
    r"excepted|does not apply to)\b",
    re.IGNORECASE,
)
STAGE_TEXT = {"f1": "f1_context", "f2": "f2_decision", "f3": "f3_action"}
# (example, stage) whose carried state (from the old fixtures) disagrees with what
# section 7.4 gives from the stage's own text. Not resolved either way: choosing one
# would move the carried statuses or the old R9 expectation (step 6).
UNRESOLVED = {("c5_B3", "f2")}


def _exception_states(text: str) -> dict[str, str]:
    """Section 7.4 read off the stage's own text, independent of the builder.

    The exempt is the schema's `service accounts`; an exception expression counts only
    in the same clause as it (a clause is a sentence, `;` or `|` separated).
    """
    clauses = re.split(r"[.;|]", text)
    exempt = any(EXEMPT in c.lower() for c in clauses)
    related = any(EXEMPT in c.lower() and EXCEPT_EXPR.search(c) for c in clauses)
    if not exempt:
        return {"exempt": "L", "except_edge": "L"}  # row 2
    return {"exempt": "P", "except_edge": "P" if related else "L"}  # rows 1 and 3


@pytest.mark.parametrize(
    "path", sorted(GOLDEN_V2_DIR.glob("c5_*.json")), ids=lambda p: p.stem
)
def test_exception_components_follow_section_7_4(path: Path) -> None:
    doc = _load(path)
    (pid,) = [
        p
        for p, d in doc["path_definitions"].items()
        if d["template_id"] == "T.exception"
    ]
    for stage, key in STAGE_TEXT.items():
        entry = next(e for e in doc["carry_evidence"][stage] if e["property"] == pid)
        got = {c["name"]: c["status"] for c in entry["components"]}
        assert list(got) == ["exempt", "except_edge"]
        from_text = _exception_states(doc["texts"][key])
        if (path.stem, stage) in UNRESOLVED:
            assert got != from_text  # carried P/P, the text has no `service accounts`
            continue
        assert got == from_text, (path.stem, stage)
        # every example is decided: none is U (row 4 has no example among the 84)
        assert "U" not in got.values()
        assert entry["path_state"] == ("P" if set(got.values()) == {"P"} else "L")


def test_every_c5_exception_break_is_the_exempt_going_missing() -> None:
    """Rows 3 and 4 (exempt present, relation missing or unidentifiable) have no
    example among the 84: the only break of the exception is the exempt being absent,
    so `exempt` and `except_edge` always break together."""
    for path in sorted(GOLDEN_V2_DIR.glob("c5_*.json")):
        doc = _load(path)
        for entries in doc["carry_evidence"].values():
            for e in entries:
                if e["path_label"] == "c5.exception":
                    assert len({c["status"] for c in e["components"]}) == 1


# --- step 4: the section 10 forms ------------------------------------------------


def test_every_old_form_in_the_old_fixtures_is_a_row_of_the_map() -> None:
    rows = {
        f["id"]: f
        for f in _load(GOLDEN_V2_DIR / "migration_map.json")["form_migrations"]
    }
    assert set(rows) == {f["id"] for f in FORM_MIGRATIONS}
    seen: set[str] = set()
    for f in OLD_FILES:
        schemas = _schemas(_load(f))
        for sc in schemas:
            forms = detect_old_forms(sc)
            assert forms <= set(rows), forms - set(rows)
            seen |= forms
    # a row claiming the old fixtures hold the form really finds it there
    # (property names and the label are checked through the property map instead)
    structural = {"property_names", "label_c4_order"}
    claimed = {i for i, r in rows.items() if r["in_old_fixtures"]} - structural
    assert claimed == seen
    assert "label_c4_order" in rows and any(
        p.endswith(".order") for p in old_properties()
    )


def test_every_old_form_is_canonical_after_migration() -> None:
    """Each old form, alone, becomes the canonical one; the result is section 2."""
    base: dict[str, Any] = {
        "constraint_id": "cx",
        "kind": "prohibition",
        "condition": None,
        "scope": None,
        "modality": None,
        "threshold": None,
        "exception": None,
        "order": None,
    }
    cases: dict[str, dict[str, Any]] = {
        "threshold_cmp": {"threshold": {"value": "5", "unit": "u", "cmp": ">"}},
        "ordering_field": {"order": {"action": "a", "after": "b"}},
        "kind_order": {"kind": "order", "order": {"action": "a", "after": "b"}},
        "kind_exception_rule": {"kind": "exception_rule"},
        "exception_string": {"exception": "robots"},
        "value_numeric": {"threshold": {"value": 5, "unit": "u", "comparator": "<="}},
        "threshold_no_quantity": {
            "threshold": {"value": "5", "unit": "u", "comparator": "=="}
        },
        "modality_must_not": {"modality": "must not"},
        "kind_key": {},
    }
    handled = set(cases)
    for form_id, change in cases.items():
        old = {**base, **change}
        assert form_id in detect_old_forms(old)
        new = canonical_schema(old, quantity="q")
        _check_canonical(new)
        assert detect_old_forms(new) == set()
    # the canonical form is a fixed point
    again = canonical_schema(new, quantity="q")
    assert again == new
    # forms that are not a schema value are checked elsewhere in this file
    elsewhere = {
        "ordering_components",
        "exception_components",
        "property_names",
        "label_c4_order",
    }
    assert handled | elsewhere == {f["id"] for f in FORM_MIGRATIONS}


def test_a_missing_quantity_is_never_guessed() -> None:
    old = {
        "constraint_id": "cx",
        "kind": "prohibition",
        "condition": None,
        "scope": None,
        "modality": "must not",
        "threshold": {"value": 1, "unit": "u", "comparator": "<"},
        "exception": None,
        "order": None,
    }
    with pytest.raises(ValueError, match="quantity"):
        canonical_schema(old)
    assert canonical_schema(old, "q")["threshold"] == {
        "quantity": "q",
        "value": "1",
        "unit": "u",
        "comparator": "<",
    }


def test_the_new_fixtures_use_the_one_quantity_per_threshold_constraint() -> None:
    for path in FILES:
        for sc in _schemas(_load(path)):
            if sc["threshold"] is not None:
                assert sc["threshold"]["quantity"] == QUANTITY[sc["constraint_id"]]


def test_exception_and_ordering_components_are_the_canonical_ones() -> None:
    assert TEMPLATE_BY_ID["T.exception"].components == ("exempt", "except_edge")
    assert TEMPLATE_BY_ID["T.ordering"].components == ("action", "after", "after_edge")
    names = {
        tuple(c["name"] for c in e["components"])
        for path in FILES
        for entries in _load(path)["carry_evidence"].values()
        for e in entries
    }
    assert ("exempt", "except_edge") in names
    assert ("exempt",) not in names
