"""R0a: canonical JSON, content IDs, the section 2 types, CheckResult."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from cle.errors import CLEError
from cle.representation import (
    AbandonedBranch,
    CheckerInfo,
    CheckResult,
    Composition,
    Invertibility,
    Location,
    PropertyVocabulary,
    Ref,
    RepresentationError,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
    Span,
    aggregate,
    canonical_json,
    sha256_hex,
)
from representation_builders import chain, ident, mor, state, vocab

CHK = CheckerInfo("t", "0")


def test_canonical_json_sorted_compact_unicode() -> None:
    assert canonical_json({"b": [1, "é"], "a": None}) == '{"a":null,"b":[1,"é"]}'
    expected = hashlib.sha256(b'{"a":1}').hexdigest()
    assert sha256_hex({"a": 1}) == expected


@pytest.mark.parametrize(
    "bad", [1.5, {"a": [0.0]}, {1: "x"}, {"a": {"b": (1, 2.5)}}, {"a": object()}]
)
def test_canonical_json_rejects_floats_and_foreign_types(bad: Any) -> None:
    with pytest.raises(TypeError):
        canonical_json(bad)


def test_content_ids_ignore_the_id_field_and_order() -> None:
    a = state("x").with_id()
    b = RepresentationState("other", "h", "kind").with_id()
    assert a.state_id == b.state_id == a.compute_id()
    m1 = mor("", "A", "B", preserved=("shape", "count")).with_id()
    m2 = mor("zzz", "A", "B", preserved=("count", "shape")).with_id()
    assert m1.morphism_id == m2.morphism_id
    assert m1.morphism_id != mor("", "A", "C").with_id().morphism_id


def test_history_hash_excludes_itself_and_changes_with_content() -> None:
    h = chain()
    assert h.history_hash == h.compute_hash()
    assert h.seal() == h
    other = chain(states=[state("A"), state("B"), state("C", description="x")])
    assert other.history_hash != h.history_hash


def test_history_hash_independent_of_recording_order() -> None:
    h = chain()
    shuffled = RepresentationHistory(
        history_id=h.history_id,
        task_ref=h.task_ref,
        vocabulary_ref=h.vocabulary_ref,
        states=tuple(reversed(h.states)),
        morphisms=tuple(reversed(h.morphisms)),
        compositions=tuple(reversed(h.compositions)),
    )
    assert shuffled.compute_hash() == h.compute_hash()


def test_round_trip_through_dict() -> None:
    h = RepresentationHistory(
        history_id="h",
        task_ref="t",
        vocabulary_ref=Ref("hext", "v", "SEAL_OK", "UNCHECKED", "n", "1"),
        states=(RepresentationState("A", "h", "k", span=Span("s", 1, 2)),),
        morphisms=(
            mor(
                "f",
                "A",
                "A",
                lost=("order",),
                evidence=(Ref("theorem_name", "T"),),
                invertibility=Invertibility("not_invertible"),
            ),
        ),
        compositions=(
            Composition("f", "f", "f", "recomputed", (Ref("history", "x"),)),
        ),
        abandoned_branches=(AbandonedBranch("b", ("A",), ("f",)),),
        prev_history_hash="p",
    ).seal()
    # preserved/lost are sets: to_dict sorts them, so compare canonical forms
    back = RepresentationHistory.from_dict(h.to_dict())
    assert back.to_dict() == h.to_dict()
    assert back.compute_hash() == h.history_hash
    v = vocab()
    assert PropertyVocabulary.from_dict(v.to_dict()).to_dict() == v.to_dict()
    here = Location("morphism", "f", "carry")
    assert Location.from_dict(here.to_dict()) == here
    assert Location.from_dict({"kind": "state", "id": "A"}).field is None
    bare = RepresentationHistory.from_dict(
        {
            "history_id": "h",
            "task_ref": "t",
            "vocabulary_ref": {"kind": "hext", "value": "v"},
            "states": [{"state_id": "A", "history_id": "h", "kind": "k"}],
            "morphisms": [
                {"morphism_id": "f", "source_state_id": "A", "target_state_id": "A"}
            ],
        }
    )
    assert bare.morphisms[0].role == "generator"
    assert bare.morphisms[0].carry is None
    assert bare.compositions == () and bare.history_hash == ""


def test_to_dict_has_no_floats() -> None:
    canonical_json(chain().to_dict())
    canonical_json(ident("A").to_dict())


@pytest.mark.parametrize(
    "build",
    [
        lambda: Ref("nope", "x"),  # type: ignore[arg-type]
        lambda: Ref("hext", "x", seal_status="MAYBE"),  # type: ignore[arg-type]
        lambda: Ref("hext", "x", validity="MAYBE"),  # type: ignore[arg-type]
        lambda: RepresentationState("a", "h", "k", source="bot"),  # type: ignore[arg-type]
        lambda: RepresentationState("a", "h", "k", verification="OK"),  # type: ignore[arg-type]
        lambda: Invertibility("sure"),  # type: ignore[arg-type]
        lambda: RepresentationMorphism("f", "A", "B", role="other"),  # type: ignore[arg-type]
        lambda: RepresentationMorphism("f", "A", "B", source="x"),  # type: ignore[arg-type]
        lambda: RepresentationMorphism("f", "A", "B", verification="x"),  # type: ignore[arg-type]
        lambda: Composition("f", "g", "h", basis="guess"),  # type: ignore[arg-type]
        lambda: Location("elsewhere", "x"),  # type: ignore[arg-type]
    ],
)
def test_unknown_enum_values_are_refused(build: Any) -> None:
    with pytest.raises(RepresentationError):
        build()


def test_error_is_a_cle_error_and_value_error() -> None:
    assert issubclass(RepresentationError, CLEError)
    assert issubclass(RepresentationError, ValueError)


def _result(status: str, code: str | None, locs: tuple[Location, ...]) -> CheckResult:
    return CheckResult("R1", status, code, locs, "0" * 64, CHK)  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["FAIL", "UNVERIFIABLE"])
def test_fail_and_unverifiable_require_code_and_location(status: str) -> None:
    here = (Location("state", "A"),)
    assert _result(status, "X", here).reason_code == "X"
    with pytest.raises(RepresentationError):
        _result(status, None, here)
    with pytest.raises(RepresentationError):
        _result(status, "", here)
    with pytest.raises(RepresentationError):
        _result(status, "X", ())


def test_pass_carries_no_code_and_rule_status_are_checked() -> None:
    assert _result("PASS", None, ()).status == "PASS"
    with pytest.raises(RepresentationError):
        _result("PASS", "X", ())
    with pytest.raises(RepresentationError):
        _result("MAYBE", None, ())
    with pytest.raises(RepresentationError):
        CheckResult("R9", "PASS", None, (), "0", CHK)  # type: ignore[arg-type]


def test_check_result_to_dict() -> None:
    d = _result("FAIL", "X", (Location("field", "h", "f"),)).to_dict()
    assert d["locations"] == [{"kind": "field", "id": "h", "field": "f"}]
    assert d["checker"] == {"name": "t", "version": "0"}
    canonical_json(d)


def test_aggregate_never_counts_unverifiable_as_pass() -> None:
    here = (Location("state", "A"),)
    p = _result("PASS", None, ())
    u = _result("UNVERIFIABLE", "X", here)
    f = _result("FAIL", "X", here)
    assert aggregate([]) == "PASS"
    assert aggregate([p, p]) == "PASS"
    assert aggregate([p, u]) == "UNVERIFIABLE"
    assert aggregate([u, f, p]) == "FAIL"
