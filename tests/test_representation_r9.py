"""R9 obligation transport (EXP-RAG-CTP001 v0.3 sections 3 and 5): unit tests."""

from __future__ import annotations

from collections.abc import Mapping
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
    verify_history,
)

P = "c1.condition"
STAGES = ["f1", "f2", "f3"]
RANK = {"PASS": 0, "UNVERIFIABLE": 1, "FAIL": 2}


def history(declared: Mapping[str, str | None]) -> RepresentationHistory:
    """Three stages; ``declared[stage]`` is "preserved", "lost" or None (silent)."""
    states = tuple(RepresentationState(s, "h", "k", s) for s in "KXYZ")
    ends = {"f1": ("K", "X"), "f2": ("X", "Y"), "f3": ("Y", "Z")}
    morphisms = tuple(
        RepresentationMorphism(
            stage,
            ends[stage][0],
            ends[stage][1],
            "generator",
            preserved=(P,) if declared[stage] == "preserved" else (),
            lost=(P,) if declared[stage] == "lost" else (),
        )
        for stage in STAGES
    )
    return RepresentationHistory(
        "h", "t", Ref("hext", "v", seal_status="SEAL_OK"), states, morphisms, ()
    ).seal()


def evidence(**by_stage: str) -> dict[str, list[dict[str, str]]]:
    return {
        stage: [
            {
                "property": P,
                "status": status,
                "basis": "evidence",
                "source": "verifier",
                "evidence_ref": f"ref:{stage}",
            }
        ]
        for stage, status in by_stage.items()
    }


def run(
    declared: Mapping[str, str | None],
    ev: Any = None,
    mode: str = "M1",
    applicability: dict[str, str] | None = None,
    **kw: Any,
) -> list[CheckResult]:
    return check_obligation_transport(
        history(declared),
        kw.pop("stages", STAGES),
        kw.pop("obligations", [P]),
        applicability or {"c1": "applicable"},
        ev,
        mode,
        **kw,
    )


def worst(results: list[CheckResult]) -> str:
    return max((r.status for r in results), key=lambda s: RANK[s])


def codes(results: list[CheckResult]) -> list[str]:
    return sorted(r.reason_code for r in results if r.reason_code)


def places(results: list[CheckResult]) -> list[str]:
    return [loc.id for r in results for loc in r.locations]


# The nine cells of v0.3 section 3, one stage (f1) with the others fine.
OK = {"f2": "preserved", "f3": "preserved"}
CELLS = [
    ("lost", "lost", "FAIL", "OBLIGATION_LOST_BY_EVIDENCE"),
    ("preserved", "lost", "FAIL", "PRESERVED_CONTRADICTED_BY_EVIDENCE"),
    ("lost", "preserved", "UNVERIFIABLE", "DECLARED_LOST_CONTRADICTED_BY_EVIDENCE"),
    ("preserved", "preserved", "PASS", None),
    ("lost", None, "FAIL", "OBLIGATION_DECLARED_LOST"),
    ("preserved", None, "PASS", None),
    (None, "lost", "FAIL", "OBLIGATION_LOST_BY_EVIDENCE"),
    (None, "preserved", "PASS", None),
    (None, None, "UNVERIFIABLE", "OBLIGATION_CARRY_MISSING"),
]


@pytest.mark.parametrize(("decl", "ev", "status", "code"), CELLS)
def test_the_nine_cells_in_m2(
    decl: str | None, ev: str | None, status: str, code: str | None
) -> None:
    ev_doc = (
        evidence(f1=ev, f2="preserved", f3="preserved")
        if ev
        else evidence(f2="preserved", f3="preserved")
    )
    results = run({"f1": decl, "f2": "preserved", "f3": "preserved"}, ev_doc, "M2")
    assert worst(results) == status
    assert codes(results) == ([code] if code else [])
    assert places(results) == (["f1"] if code else [])


@pytest.mark.parametrize(("decl", "ev", "status", "code"), CELLS)
def test_m1_ignores_the_evidence(
    decl: str | None, ev: str | None, status: str, code: str | None
) -> None:
    ev_doc = evidence(f1="lost", f2="lost", f3="lost")
    m1 = run({"f1": decl, "f2": "preserved", "f3": "preserved"}, ev_doc, "M1")
    no_evidence = {"lost": "FAIL", "preserved": "PASS", None: "UNVERIFIABLE"}
    assert worst(m1) == no_evidence[decl]
    if decl is None:
        assert codes(m1) == ["OBLIGATION_CARRY_MISSING"]


def test_a_loss_carried_on_is_reported_once_at_the_first_stage() -> None:
    results = run({"f1": "preserved", "f2": "lost", "f3": "lost"})
    assert places(results) == ["f2"]


def test_a_return_to_preserved_keeps_the_fail_and_a_new_drop_is_reported() -> None:
    results = run({"f1": "lost", "f2": "preserved", "f3": "lost"})
    assert worst(results) == "FAIL"
    assert sorted(places(results)) == ["f1", "f3"]
    assert worst(run({"f1": "lost", "f2": "preserved", "f3": "preserved"})) == "FAIL"


def test_unverifiable_then_fail_is_reported_again() -> None:
    ev = evidence(f1="preserved", f2="lost", f3="lost")
    results = run({"f1": "lost", "f2": "lost", "f3": "lost"}, ev, "M2")
    assert worst(results) == "FAIL"
    assert sorted(places(results)) == ["f1", "f2"]


def test_all_findings_are_given_and_the_value_is_the_worst() -> None:
    results = run(
        {"f1": "lost", "f2": None, "f3": None},
        obligations=[P, "c1.modality"],
    )
    assert worst(results) == "FAIL"
    assert [r.status for r in results] == ["FAIL", "UNVERIFIABLE"]


def test_missing_evidence_ref_counts_as_no_evidence_and_is_a_finding() -> None:
    ev = evidence(f1="preserved")
    ev["f1"][0]["evidence_ref"] = ""
    lost = run({"f1": "lost", "f2": "preserved", "f3": "preserved"}, ev, "M2")
    assert worst(lost) == "FAIL"
    assert codes(lost) == ["EVIDENCE_REF_MISSING", "OBLIGATION_DECLARED_LOST"]
    assert sorted(r.status for r in lost) == ["FAIL", "UNVERIFIABLE"]
    kept = run({"f1": "preserved", "f2": "preserved", "f3": "preserved"}, ev, "M2")
    assert worst(kept) == "UNVERIFIABLE"
    assert codes(kept) == ["EVIDENCE_REF_MISSING"]
    assert places(kept) == ["f1"]


def test_not_applicable_is_skipped_and_undetermined_is_annotated() -> None:
    lost = {"f1": "lost", "f2": "lost", "f3": "lost"}
    skipped = run(lost, applicability={"c1": "not_applicable"})
    assert worst(skipped) == "PASS"
    marked = run(lost, applicability={"c1": "undetermined"})
    assert worst(marked) == "FAIL"
    assert [w.reason_code for r in marked for w in r.warnings] == [
        "APPLICABILITY_UNDETERMINED"
    ]
    quiet = run(
        {"f1": "preserved", "f2": "preserved", "f3": "preserved"},
        applicability={"c1": "undetermined"},
    )
    assert worst(quiet) == "PASS"
    assert not any(r.warnings for r in quiet)


def test_a_constraint_missing_from_applicability_counts_as_applicable() -> None:
    results = run({"f1": "lost", "f2": "lost", "f3": "lost"}, applicability={})
    assert worst(results) == "FAIL"


def test_a_stage_that_is_not_in_the_history_has_no_declaration() -> None:
    results = run(
        {"f1": "preserved", "f2": "preserved", "f3": "preserved"}, stages=["f1", "nope"]
    )
    assert codes(results) == ["OBLIGATION_CARRY_MISSING"]
    assert places(results) == ["nope"]


def test_a_property_both_preserved_and_lost_counts_as_lost() -> None:
    h = history({"f1": "lost", "f2": "preserved", "f3": "preserved"})
    both = RepresentationMorphism(
        "f1", "K", "X", "generator", preserved=(P,), lost=(P,)
    )
    h = RepresentationHistory(
        h.history_id,
        h.task_ref,
        h.vocabulary_ref,
        h.states,
        (both, *h.morphisms[1:]),
        (),
    )
    results = check_obligation_transport(h, STAGES, [P], {"c1": "applicable"})
    assert codes(results) == ["OBLIGATION_DECLARED_LOST"]


def vocab(*props: str) -> PropertyVocabulary:
    return PropertyVocabulary(
        "v", "1", "t", props, (), Ref("hext", "v", seal_status="SEAL_OK")
    )


def test_vocabulary_unresolved() -> None:
    fine = {"f1": "preserved", "f2": "preserved", "f3": "preserved"}
    results = run(fine, vocabulary=vocab("c1.modality"))
    assert codes(results) == ["VOCABULARY_UNRESOLVED"]
    assert worst(run(fine, vocabulary=vocab(P))) == "PASS"


FINE = {"f1": "preserved", "f2": "preserved", "f3": "preserved"}


@pytest.mark.parametrize(
    ("kw", "field"),
    [
        ({"stages": "f1"}, "stages"),
        ({"stages": [1]}, "stages"),
        ({"obligations": "c1.condition"}, "obligations"),
        ({"obligations": [3]}, "obligations"),
        ({"applicability": []}, "applicability"),
        ({"applicability": {"c1": "maybe"}}, "applicability"),
        ({"applicability": {1: "applicable"}}, "applicability"),
        ({"ev": 5}, "carry_evidence"),
        ({"ev": {1: []}}, "carry_evidence"),
        ({"ev": {"f1": 5}}, "carry_evidence"),
        ({"ev": {"f1": [5]}}, "carry_evidence"),
        ({"ev": {"f1": [{"property": 1, "status": "lost"}]}}, "carry_evidence"),
        ({"ev": {"f1": [{"property": P, "status": "maybe"}]}}, "carry_evidence"),
        ({"mode": "M3"}, "mode"),
        ({"vocabulary": "x"}, "vocabulary"),
    ],
)
def test_defective_inputs_are_results_not_exceptions(
    kw: dict[str, Any], field: str
) -> None:
    ev = kw.pop("ev", None)
    mode = kw.pop("mode", "M1")
    applicability = kw.pop("applicability", None)
    h = history(FINE)
    results = check_obligation_transport(
        h,
        kw.get("stages", STAGES),
        kw.get("obligations", [P]),
        applicability if applicability is not None else {"c1": "applicable"},
        ev,
        mode,
        kw.get("vocabulary"),
    )
    assert [(r.status, r.reason_code) for r in results] == [
        ("FAIL", "INPUT_TYPE_INVALID")
    ]
    assert [loc.field for loc in results[0].locations] == [field]


def test_a_defective_history_is_a_result() -> None:
    results = check_obligation_transport("nope", STAGES, [P], {})  # type: ignore[arg-type]
    assert [(r.status, r.reason_code) for r in results] == [
        ("FAIL", "INPUT_TYPE_INVALID")
    ]


def test_evidence_that_is_not_basis_evidence_is_ignored() -> None:
    ev = evidence(f1="lost")
    ev["f1"][0]["basis"] = "declared"
    assert worst(run(FINE, ev, "M2")) == "PASS"


def test_r9_is_not_in_verify_history_and_the_history_is_untouched() -> None:
    h = history(FINE)
    before = h.to_dict()
    check_obligation_transport(h, STAGES, [P], {"c1": "applicable"})
    assert h.to_dict() == before
    assert all(r.rule != "R9" for r in verify_history(h))


def test_the_result_is_deterministic() -> None:
    a = run({"f1": "lost", "f2": "lost", "f3": "lost"}, evidence(f1="lost"), "M2")
    b = run({"f1": "lost", "f2": "lost", "f3": "lost"}, evidence(f1="lost"), "M2")
    assert [r.to_dict() for r in a] == [r.to_dict() for r in b]
