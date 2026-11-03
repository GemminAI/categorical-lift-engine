"""R9 reads a property's constraint from the vocabulary's entries, and only there.

The name of a property (a `path_id` has no dot; an old name has one) and its label say
nothing about which constraint it belongs to. An entry that cannot be read is
UNVERIFIABLE (`VOCABULARY_UNRESOLVED`, the reason in `detail`), never a guess.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from cle.representation import (
    CheckResult,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
    check_obligation_transport,
)
from ctp001_builder import GOLDEN_DIR
from ctp001_legacy import legacy_constraints, legacy_vocabulary
from ctp001_v2_builder import GOLDEN_V2_DIR
from ctp001_v2_r9 import MODES, r9_evidence, run_r9

STAGES = ["f1", "f2", "f3"]
A, B = "path:aaa", "path:bbb"  # path ids: no dot


def _history(*props: str, lost: tuple[str, ...] = ()) -> RepresentationHistory:
    states = tuple(RepresentationState(s, "h", "k", s) for s in "KXYZ")
    ends = {"f1": ("K", "X"), "f2": ("X", "Y"), "f3": ("Y", "Z")}
    morphisms = tuple(
        RepresentationMorphism(
            stage,
            *ends[stage],
            "generator",
            preserved=tuple(p for p in props if p not in lost),
            lost=lost,
        )
        for stage in STAGES
    )
    return RepresentationHistory(
        "h", "t", Ref("hext", "v", seal_status="SEAL_OK"), states, morphisms, ()
    ).seal()


def _vocab(
    props: tuple[str, ...], constraints: tuple[tuple[str, str], ...]
) -> PropertyVocabulary:
    return PropertyVocabulary(
        "v", "1", "t", props, (), Ref("hext", "v", seal_status="SEAL_OK"), constraints
    )


def _run(
    props: tuple[str, ...],
    constraints: tuple[tuple[str, str], ...],
    applicability: dict[str, str],
    *,
    lost: tuple[str, ...] = (),
    obligations: list[str] | None = None,
) -> list[CheckResult]:
    return check_obligation_transport(
        _history(*props, lost=lost),
        _vocab(props, constraints),
        STAGES,
        props if obligations is None else obligations,
        applicability,
    )


def _status_codes(results: list[CheckResult]) -> list[tuple[str, str | None]]:
    return [(r.status, r.reason_code) for r in results]


def _reasons(results: list[CheckResult]) -> list[str]:
    return sorted(str(r.detail["reason"]) for r in results if r.detail)


# --- the constraint comes from the entry ----------------------------------------


def test_a_path_id_without_a_dot_is_identified_by_its_entry() -> None:
    skipped = _run((A,), ((A, "c1"),), {"c1": "not_applicable"}, lost=(A,))
    assert _status_codes(skipped) == [("PASS", None)]
    judged = _run((A,), ((A, "c1"),), {"c1": "applicable"}, lost=(A,))
    assert _status_codes(judged) == [("FAIL", "OBLIGATION_DECLARED_LOST")]
    noted = _run((A,), ((A, "c1"),), {"c1": "undetermined"}, lost=(A,))
    assert [w.reason_code for r in noted for w in r.warnings] == [
        "APPLICABILITY_UNDETERMINED"
    ]


def test_the_name_is_never_taken_apart() -> None:
    """`c1.modality` is mapped to c2: c1's applicability does not apply to it."""
    name = "c1.modality"
    results = _run(
        (name,),
        ((name, "c2"),),
        {"c1": "not_applicable", "c2": "applicable"},
        lost=(name,),
    )
    assert _status_codes(results) == [("FAIL", "OBLIGATION_DECLARED_LOST")]
    skipped = _run(
        (name,),
        ((name, "c2"),),
        {"c1": "applicable", "c2": "not_applicable"},
        lost=(name,),
    )
    assert _status_codes(skipped) == [("PASS", None)]


def test_several_paths_of_one_constraint_share_its_applicability() -> None:
    results = _run(
        (A, B),
        ((A, "c1"), (B, "c1")),
        {"c1": "undetermined"},
        lost=(A, B),
    )
    assert _status_codes(results) == [("FAIL", "OBLIGATION_DECLARED_LOST")]
    assert len({w.location.field for r in results for w in r.warnings}) == 2
    skipped = _run(
        (A, B), ((A, "c1"), (B, "c1")), {"c1": "not_applicable"}, lost=(A, B)
    )
    assert _status_codes(skipped) == [("PASS", None)]


def test_two_constraints_are_told_apart() -> None:
    results = _run(
        (A, B),
        ((A, "c1"), (B, "c2")),
        {"c1": "not_applicable", "c2": "applicable"},
        lost=(A, B),
    )
    assert [loc.field for r in results for loc in r.locations] == [B]


def test_the_label_is_not_an_input(tmp_path: Path) -> None:
    doc = json.loads((GOLDEN_V2_DIR / "c6_B2.json").read_text(encoding="utf-8"))
    other = json.loads(json.dumps(doc))
    for d in other["path_definitions"].values():
        d["path_label"] = "renamed." + d["path_label"]
    for entries in other["carry_evidence"].values():
        for e in entries:
            e["path_label"] = "renamed." + e["path_label"]
    assert r9_evidence(doc) == r9_evidence(other)
    for mode in MODES:
        assert [r.to_dict() for r in run_r9(doc, mode)] == [
            r.to_dict() for r in run_r9(other, mode)
        ]


# --- entries that cannot be read: UNVERIFIABLE with the reason -------------------


def _unresolved(results: list[CheckResult]) -> None:
    assert {(r.status, r.reason_code) for r in results} == {
        ("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")
    }


def test_a_path_the_vocabulary_does_not_name() -> None:
    results = _run((A,), ((A, "c1"),), {"c1": "applicable"}, obligations=[B])
    _unresolved(results)
    assert _reasons(results) == ["PROPERTY_NOT_IN_VOCABULARY"]
    assert results[0].detail == {
        "reason": "PROPERTY_NOT_IN_VOCABULARY",
        "property": B,
    }


def test_a_path_with_no_entry() -> None:
    results = _run((A, B), ((A, "c1"),), {"c1": "applicable"}, obligations=[B])
    _unresolved(results)
    assert _reasons(results) == ["CONSTRAINT_ENTRY_MISSING"]


def test_a_name_with_entries_for_different_constraints() -> None:
    results = _run((A,), ((A, "c1"), (A, "c2")), {"c1": "applicable"})
    _unresolved(results)
    assert _reasons(results) == ["CONSTRAINT_ENTRY_CONFLICT"]


def test_a_repeated_entry_is_a_duplicate() -> None:
    results = _run((A,), ((A, "c1"), (A, "c1")), {"c1": "applicable"})
    _unresolved(results)
    assert _reasons(results) == ["CONSTRAINT_ENTRY_DUPLICATE"]


def test_a_defect_in_one_entry_leaves_the_other_obligations_judged() -> None:
    results = _run(
        (A, B), ((A, "c1"), (B, "c1"), (B, "c2")), {"c1": "applicable"}, lost=(A,)
    )
    assert {(r.status, r.reason_code) for r in results} == {
        ("FAIL", "OBLIGATION_DECLARED_LOST"),
        ("UNVERIFIABLE", "VOCABULARY_UNRESOLVED"),
    }


def test_an_unverified_seal_still_stops_before_the_entries() -> None:
    vocab = replace(
        _vocab((A,), ((A, "c1"),)), ref=Ref("hext", "v", seal_status="SEAL_FAIL")
    )
    results = check_obligation_transport(
        _history(A), vocab, STAGES, [A], {"c1": "applicable"}
    )
    assert _status_codes(results) == [("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")]
    assert results[0].detail is None  # the existing finding, unchanged


# --- the old names go through the adapter, and only through it --------------------


def test_old_names_with_the_adapter_give_the_same_result_as_before() -> None:
    props = ("c1.condition", "c1.modality")
    with_adapter = check_obligation_transport(
        _history(*props, lost=props[:1]),
        _vocab(props, legacy_constraints(props)),
        STAGES,
        props,
        {"c1": "undetermined"},
    )
    assert _status_codes(with_adapter) == [("FAIL", "OBLIGATION_DECLARED_LOST")]
    assert [w.reason_code for r in with_adapter for w in r.warnings] == [
        "APPLICABILITY_UNDETERMINED"
    ]


def test_old_names_without_the_adapter_are_unverifiable_not_guessed() -> None:
    props = ("c1.condition",)
    results = check_obligation_transport(
        _history(*props, lost=props),
        _vocab(props, ()),  # names only
        STAGES,
        props,
        {"c1": "applicable"},
    )
    _unresolved(results)
    assert _reasons(results) == ["CONSTRAINT_ENTRY_MISSING"]


def test_the_adapter_makes_one_entry_per_old_name() -> None:
    assert legacy_constraints(("c4.order", "c6x.y.z")) == (
        ("c4.order", "c4"),
        ("c6x.y.z", "c6x"),
    )
    doc = json.loads((GOLDEN_DIR / "c4_G0.json").read_text(encoding="utf-8"))
    voc = legacy_vocabulary(doc)
    assert dict(voc.constraints) == {"c4.order": "c4", "c4.threshold": "c4"}
    assert "constraints" not in doc["vocabulary"]  # the old file is untouched


# --- the vocabulary type -----------------------------------------------------------


def test_constraints_are_part_of_the_vocabulary_content() -> None:
    voc = _vocab((A, B), ((B, "c2"), (A, "c1")))
    d = voc.to_dict()
    assert d["constraints"] == [[A, "c1"], [B, "c2"]]  # sorted: a stable content
    assert PropertyVocabulary.from_dict(d) == _vocab((A, B), ((A, "c1"), (B, "c2")))


def test_a_vocabulary_without_entries_is_written_as_before() -> None:
    d = _vocab((A,), ()).to_dict()
    assert "constraints" not in d
    assert PropertyVocabulary.from_dict(d).constraints == ()


@pytest.mark.parametrize(
    "bad",
    [[(A, "c1", "x")], [(A, 1)], ["ab"], "x"],
)
def test_malformed_entries_are_an_input_defect(bad: Any) -> None:
    vocab = replace(_vocab((A,), ()), constraints=bad)
    results = check_obligation_transport(
        _history(A), vocab, STAGES, [A], {"c1": "applicable"}
    )
    assert _status_codes(results) == [("FAIL", "INPUT_TYPE_INVALID")]
    assert [loc.field for loc in results[0].locations] == ["vocabulary"]


# --- the fixtures: R9 gives what it gave before the change -------------------------

FROZEN: dict[str, Any] = json.loads(
    (Path(__file__).parent / "golden" / "r9_results_3dca61a.json").read_text(
        encoding="utf-8"
    )
)


def _without_digest(results: list[CheckResult]) -> list[dict[str, Any]]:
    # `inputs_sha256` covers the vocabulary, which now holds the entries
    out = [r.to_dict() for r in results]
    for d in out:
        d.pop("inputs_sha256")
    return out


def test_the_frozen_results_cover_168_cells_of_each_kind() -> None:
    assert len(FROZEN) == 336
    assert {k.split("/")[0] for k in FROZEN} == {"ctp001", "ctp001_v2"}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "path", sorted(GOLDEN_DIR.glob("c[1-6]_*.json")), ids=lambda p: p.stem
)
def test_old_fixtures_r9_is_unchanged_through_the_adapter(
    path: Path, mode: str
) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    got = _without_digest(run_r9(doc, mode, legacy=True))
    assert got == FROZEN[f"ctp001/{path.name}/{mode}"]


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "path", sorted(GOLDEN_V2_DIR.glob("c[1-6]_*.json")), ids=lambda p: p.stem
)
def test_new_fixtures_r9_is_unchanged_with_constraint_keyed_applicability(
    path: Path, mode: str
) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    got = _without_digest(run_r9(doc, mode))
    assert got == FROZEN[f"ctp001_v2/{path.name}/{mode}"]
