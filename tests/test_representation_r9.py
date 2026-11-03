"""R9 obligation transport (EXP-RAG-CTP001 v0.3 sections 3 and 5): unit tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

import pytest

from cle.representation import (
    CheckResult,
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
FINE = {"f1": "preserved", "f2": "preserved", "f3": "preserved"}
LOST = {"f1": "lost", "f2": "lost", "f3": "lost"}


def history(
    declared: Mapping[str, str | None],
    *,
    both: tuple[str, ...] = (),
    identity: bool = True,
    seal: Literal["SEAL_OK", "SEAL_FAIL"] | None = "SEAL_OK",
) -> RepresentationHistory:
    """Three stages. ``declared[stage]``: "preserved", "lost" or None (silent);
    ``both`` lists the stages that list the property in both ``preserved`` and ``lost``.
    The identity on K names the vocabulary (``P`` and ``c1.modality``)."""
    states = tuple(RepresentationState(s, "h", "k", s) for s in "KXYZ")
    ends = {"f1": ("K", "X"), "f2": ("X", "Y"), "f3": ("Y", "Z")}
    morphisms = [
        RepresentationMorphism(
            stage,
            ends[stage][0],
            ends[stage][1],
            "generator",
            preserved=(P,) if declared[stage] == "preserved" or stage in both else (),
            lost=(P,) if declared[stage] == "lost" or stage in both else (),
        )
        for stage in STAGES
    ]
    if identity:
        morphisms.append(
            RepresentationMorphism(
                "iK", "K", "K", "identity", preserved=(P, "c1.modality")
            )
        )
    return RepresentationHistory(
        "h", "t", Ref("hext", "v", seal_status=seal), states, tuple(morphisms), ()
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
    applicability: Mapping[str, str] | None = None,
    *,
    h: RepresentationHistory | None = None,
    **kw: Any,
) -> list[CheckResult]:
    return check_obligation_transport(
        h or history(declared),
        kw.pop("stages", STAGES),
        kw.pop("obligations", [P]),
        applicability or {"c1": "applicable"},
        ev,
        mode,
    )


def worst(results: list[CheckResult]) -> str:
    return max((r.status for r in results), key=lambda s: RANK[s])


def codes(results: list[CheckResult]) -> list[str]:
    return sorted(r.reason_code for r in results if r.reason_code)


def places(results: list[CheckResult]) -> list[str]:
    return sorted(loc.id for r in results for loc in r.locations)


def warns(results: list[CheckResult]) -> list[tuple[str, str]]:
    return [(w.reason_code, w.location.id) for r in results for w in r.warnings]


# The nine cells of v0.3 section 3, one stage (f1) with the others fine.
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
    rest = {"f2": "preserved", "f3": "preserved"}
    doc = evidence(f1=ev, **rest) if ev else evidence(**rest)
    results = run({"f1": decl, **rest}, doc, "M2")
    assert worst(results) == status
    assert codes(results) == ([code] if code else [])
    assert places(results) == (["f1"] if code else [])


@pytest.mark.parametrize("decl", ["lost", "preserved", None])
def test_m1_ignores_the_evidence(decl: str | None) -> None:
    rest = {"f2": "preserved", "f3": "preserved"}
    m1 = run({"f1": decl, **rest}, evidence(f1="lost", f2="lost", f3="lost"), "M1")
    assert (
        worst(m1) == {"lost": "FAIL", "preserved": "PASS", None: "UNVERIFIABLE"}[decl]
    )


# --- the state changes of section 5 -------------------------------------------


def test_p_to_l_is_a_fail_at_that_stage_and_a_loss_carried_on_is_silent() -> None:
    results = run({"f1": "preserved", "f2": "lost", "f3": "lost"})
    assert [(r.status, r.reason_code) for r in results] == [
        ("FAIL", "OBLIGATION_DECLARED_LOST")
    ]
    assert places(results) == ["f2"]
    assert results[0].detail is None


def test_p_to_u_is_unverifiable_at_that_stage_and_u_to_u_is_silent() -> None:
    results = run({"f1": "preserved", "f2": None, "f3": None})
    assert [(r.status, r.reason_code) for r in results] == [
        ("UNVERIFIABLE", "OBLIGATION_CARRY_MISSING")
    ]
    assert places(results) == ["f2"]


def test_u_to_l_is_a_fail_with_the_last_known_preserved_stage() -> None:
    results = run({"f1": "preserved", "f2": None, "f3": "lost"})
    fail = [r for r in results if r.status == "FAIL"]
    assert [r.reason_code for r in fail] == ["OBLIGATION_DECLARED_LOST"]
    assert places(fail) == ["f3"]
    assert fail[0].detail == {"last_known_preserved": "f1"}
    assert worst(results) == "FAIL"
    assert fail[0].to_dict()["detail"] == {"last_known_preserved": "f1"}


def test_u_to_l_from_the_start_has_no_last_known_preserved() -> None:
    results = run({"f1": None, "f2": "lost", "f3": "lost"})
    fail = [r for r in results if r.status == "FAIL"]
    assert fail[0].detail == {"last_known_preserved": None}
    assert fail[0].to_dict()["detail"] == {"last_known_preserved": None}
    assert places(fail) == ["f2"]


def test_l_to_p_keeps_the_fail_and_warns_without_a_new_finding() -> None:
    results = run({"f1": "lost", "f2": "preserved", "f3": "preserved"})
    assert [(r.status, r.reason_code) for r in results] == [
        ("FAIL", "OBLIGATION_DECLARED_LOST")
    ]
    assert places(results) == ["f1"]
    assert warns(results) == [("OBLIGATION_RESTORED", "f2")]
    assert "detail" not in results[0].to_dict()


def test_a_drop_after_a_restoration_is_a_new_fail() -> None:
    results = run({"f1": "lost", "f2": "preserved", "f3": "lost"})
    assert places(results) == ["f1", "f3"]


def test_l_to_u_gives_no_finding() -> None:
    results = run({"f1": "lost", "f2": None, "f3": None})
    assert [(r.status, r.reason_code) for r in results] == [
        ("FAIL", "OBLIGATION_DECLARED_LOST")
    ]
    assert places(results) == ["f1"]


def test_all_findings_are_given_and_the_value_is_the_worst() -> None:
    results = run(
        {"f1": "lost", "f2": None, "f3": None}, obligations=[P, "c1.modality"]
    )
    assert worst(results) == "FAIL"
    assert [r.status for r in results] == ["FAIL", "UNVERIFIABLE"]


# --- unusable declarations and evidence ---------------------------------------


def test_a_contradictory_declaration_is_absent_and_a_finding() -> None:
    results = run(FINE, h=history(FINE, both=("f2",)))
    assert sorted((r.status, r.reason_code) for r in results) == [
        ("UNVERIFIABLE", "DECLARATION_CONTRADICTORY"),
        ("UNVERIFIABLE", "OBLIGATION_CARRY_MISSING"),
    ]
    assert places(results) == ["f2", "f2"]
    assert worst(results) == "UNVERIFIABLE"  # not counted as lost


def test_a_contradictory_declaration_with_evidence_uses_the_evidence() -> None:
    h = history(FINE, both=("f1",))
    kept = run(FINE, evidence(f1="preserved"), "M2", h=h)
    assert codes(kept) == ["DECLARATION_CONTRADICTORY"]
    dropped = run(FINE, evidence(f1="lost"), "M2", h=h)
    assert codes(dropped) == [
        "DECLARATION_CONTRADICTORY",
        "OBLIGATION_LOST_BY_EVIDENCE",
    ]
    assert worst(dropped) == "FAIL"


def test_missing_evidence_ref_makes_the_evidence_absent_and_is_a_finding() -> None:
    ev = evidence(f1="preserved")
    ev["f1"][0]["evidence_ref"] = ""
    lost = run({**FINE, "f1": "lost"}, ev, "M2")
    assert worst(lost) == "FAIL"
    assert codes(lost) == ["EVIDENCE_REF_MISSING", "OBLIGATION_DECLARED_LOST"]
    kept = run(FINE, ev, "M2")
    assert worst(kept) == "UNVERIFIABLE"
    assert codes(kept) == ["EVIDENCE_REF_MISSING"]
    assert places(kept) == ["f1"]


def test_a_stage_listed_twice_does_not_repeat_a_location() -> None:
    ev = evidence(f1="preserved")
    ev["f1"][0]["evidence_ref"] = ""
    results = run(FINE, ev, "M2", stages=["f1", "f1"])
    assert places(results) == ["f1"]


def test_evidence_that_is_not_basis_evidence_is_ignored() -> None:
    ev = evidence(f1="lost")
    ev["f1"][0]["basis"] = "declared"
    assert worst(run(FINE, ev, "M2")) == "PASS"


# --- applicability ------------------------------------------------------------


def test_not_applicable_is_skipped_and_undetermined_is_annotated() -> None:
    assert worst(run(LOST, applicability={"c1": "not_applicable"})) == "PASS"
    marked = run(LOST, applicability={"c1": "undetermined"})
    assert worst(marked) == "FAIL"
    assert warns(marked) == [("APPLICABILITY_UNDETERMINED", "f1")]
    quiet = run(FINE, applicability={"c1": "undetermined"})
    assert worst(quiet) == "PASS"
    assert not any(r.warnings for r in quiet)


def test_the_note_goes_only_with_findings_on_the_undetermined_constraint() -> None:
    h = history(LOST)
    results = check_obligation_transport(
        h,
        STAGES,
        [P, "c2.scope"],
        {"c1": "undetermined", "c2": "applicable"},
    )
    # c2.scope is not in the vocabulary: its finding is not annotated
    assert "VOCABULARY_UNRESOLVED" in codes(results)
    assert set(warns(results)) == {("APPLICABILITY_UNDETERMINED", "f1")}


def test_a_constraint_missing_from_applicability_counts_as_applicable() -> None:
    assert worst(run(LOST, applicability={})) == "FAIL"


def test_a_stage_that_is_not_in_the_history_has_no_declaration() -> None:
    results = run(FINE, stages=["f1", "nope"])
    assert codes(results) == ["OBLIGATION_CARRY_MISSING"]
    assert places(results) == ["nope"]


# --- the history's vocabulary -------------------------------------------------


def test_an_obligation_the_history_vocabulary_does_not_name_is_unresolved() -> None:
    results = run(FINE, obligations=["c1.unknown"])
    assert [(r.status, r.reason_code) for r in results] == [
        ("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")
    ]
    assert worst(run(FINE)) == "PASS"


@pytest.mark.parametrize(
    "h",
    [
        history(FINE, identity=False),
        history(FINE, seal=None),
        history(FINE, seal="SEAL_FAIL"),
    ],
    ids=["no-identity", "seal-missing", "seal-failed"],
)
def test_no_usable_history_vocabulary_is_unresolved_never_skipped(
    h: RepresentationHistory,
) -> None:
    for obligations in ([P], []):
        results = run(FINE, h=h, obligations=obligations)
        assert [(r.status, r.reason_code) for r in results] == [
            ("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")
        ]


# --- defects, scope, determinism ----------------------------------------------


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
    ],
)
def test_defective_inputs_are_results_not_exceptions(
    kw: dict[str, Any], field: str
) -> None:
    results = check_obligation_transport(
        history(FINE),
        kw.get("stages", STAGES),
        kw.get("obligations", [P]),
        kw.get("applicability", {"c1": "applicable"}),
        kw.get("ev"),
        kw.get("mode", "M1"),
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


def test_r9_is_not_in_verify_history_and_the_history_is_untouched() -> None:
    h = history(FINE)
    before = h.to_dict()
    check_obligation_transport(h, STAGES, [P], {"c1": "applicable"})
    assert h.to_dict() == before
    assert all(r.rule != "R9" for r in verify_history(h))


def test_the_result_is_deterministic() -> None:
    a = run(LOST, evidence(f1="lost"), "M2")
    b = run(LOST, evidence(f1="lost"), "M2")
    assert [r.to_dict() for r in a] == [r.to_dict() for r in b]
