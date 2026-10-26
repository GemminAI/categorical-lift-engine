"""CLE v0.4 decisions (D-01 .. D-25), one test group per decision.

The golden files ``tests/golden/representation_D*.json`` hold the
fixed examples of the decisions that changed an implementation behaviour.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from cle.representation import (
    AbandonedBranch,
    CheckResult,
    Composition,
    Invertibility,
    Location,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    Span,
    canonical_json,
    check_r1,
    check_r2,
    check_r3,
    check_r4,
    check_r5,
    check_r6,
    check_r7,
    check_r8,
    derive_unit_compositions,
    verify_history,
)
from cle.representation.checks import _Index
from representation_builders import (
    PROPS,
    chain,
    history,
    ident,
    invertible_pair,
    mor,
    state,
    vocab,
)


def anything(value: Any) -> Any:
    return value


def broke(obj: Any, **changes: Any) -> Any:
    return replace(obj, **changes)


def codes(results: list[CheckResult]) -> set[tuple[str, str | None]]:
    return {(r.status, r.reason_code) for r in results}


def at(results: list[CheckResult], code: str) -> list[tuple[str, str, str | None]]:
    return [
        (x.kind, x.id, x.field)
        for r in results
        if r.reason_code == code
        for x in r.locations
    ]


# ------------------------------------------------------------------ D-01 / A-2
def test_d01_inverse_pair_does_not_fail_r6_even_with_a_previous_version() -> None:
    v1 = invertible_pair()
    v2 = replace(v1, prev_history_hash=v1.history_hash).seal()
    assert [r.status for r in check_r6(v2, v1)] == ["PASS"]


def test_d01_version_chain_cycle_through_the_previous_version() -> None:
    # a real cycle needs a hash fixed point; with a forged declared hash the
    # chain "v2 -> v1 -> v2" can be written down
    v1 = replace(chain(), prev_history_hash="FORGED")
    v2 = replace(chain(), prev_history_hash=v1.compute_hash(), history_hash="FORGED")
    out = check_r6(v2, v1)
    assert at(out, "VERSION_CYCLE") == [("field", "h", "prev_history_hash")]


# ------------------------------------------------------------------ D-02 / A-1
def test_d02_unit_terms_do_not_count_as_independent_records() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("k", "A", "C", role="composite"),
        ],
        compositions=[
            Composition("f", "g", "k"),
            Composition("ia", "f", "f"),
            Composition("f", "ib", "f"),
        ],
    )
    assert codes(check_r2(h)) == {("UNVERIFIABLE", "COMPOSITE_BY_CONSTRUCTION")}


def test_d02_an_independent_result_with_non_identity_inputs_counts() -> None:
    assert codes(check_r2(chain())) == {("PASS", None)}
    identity_result = invertible_pair()
    # f then r gives an identity: not independent (the result is an identity)
    assert codes(check_r2(identity_result)) == {
        ("UNVERIFIABLE", "COMPOSITE_BY_CONSTRUCTION")
    }


# ------------------------------------------------------------- D-03 / D-15
def test_d03_d15_every_finding_is_reported_and_the_rule_is_the_worst() -> None:
    h = chain(
        morphisms=[
            mor(
                "f",
                "A",
                "B",
                lost=("order",),
                invertibility=Invertibility("invertible", "zz"),
            ),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ]
    )
    out = check_r4(h)
    assert codes(out) == {
        ("FAIL", "INVERTIBLE_WITH_LOSS"),
        ("UNVERIFIABLE", "INVERSE_UNRESOLVED"),
    }
    assert out[0].status == "FAIL"


# ------------------------------------------------------------------- D-04
def test_d04_a_dangling_reference_only_affects_the_part_that_uses_it() -> None:
    h = history(
        [state(x) for x in "ABCD"],
        [
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("h", "C", "D"),
            mor("k", "A", "C"),
            mor("m", "B", "D"),
            mor("p", "A", "D"),
            mor("q", "A", "D"),
        ],
        [
            Composition("f", "g", "k"),
            Composition("g", "h", "m"),
            Composition("k", "h", "p"),
            Composition("f", "m", "q"),
            Composition("f", "nope", "k"),
        ],
    )
    out = verify_history(h, vocabulary=vocab(), eligibility={})
    assert ("UNVERIFIABLE", "MORPHISM_UNRESOLVED") in codes(out)
    assert ("FAIL", "ASSOCIATIVITY_VIOLATION") in codes(out)
    assert {r.status for r in check_r4(h)} == {"PASS"}


# ------------------------------------------------------------------- D-05
def test_d05_derived_unit_terms_are_marked_recomputed_by_the_verifier() -> None:
    h = chain()
    derived = derive_unit_compositions(h)
    assert derived
    for term in derived:
        assert term.basis == "recomputed"
        assert term.source == "verifier"
        assert term.evidence[0].kind == "checker_output"
    # nothing written is repeated; writing the terms out changes no verdict
    written = {(c.first, c.second) for c in h.compositions}
    assert not written & {(t.first, t.second) for t in derived}
    full = replace(h, compositions=(*h.compositions, *derived)).seal()
    assert codes(verify_history(full, vocabulary=vocab(), eligibility={})) == codes(
        verify_history(h, vocabulary=vocab(), eligibility={})
    )
    assert derive_unit_compositions(full) == ()


def test_d05_derivation_covers_missing_identities_and_defective_input() -> None:
    no_ident = history([state("A"), state("B")], [mor("f", "A", "B")], identities=False)
    assert derive_unit_compositions(no_ident) == ()
    only_source = history(
        [state("A"), state("B")], [ident("A"), mor("f", "A", "B")], identities=False
    )
    assert [(t.first, t.second) for t in derive_unit_compositions(only_source)] == [
        ("ia", "f"),
        ("ia", "ia"),
    ]
    only_target = history(
        [state("A"), state("B")], [ident("B"), mor("f", "A", "B")], identities=False
    )
    assert [(t.first, t.second) for t in derive_unit_compositions(only_target)] == [
        ("f", "ib"),
        ("ib", "ib"),
    ]
    bad = broke(chain(), task_ref=5)
    assert derive_unit_compositions(bad) == ()
    assert Composition("a", "b", "c").source == "unknown"


# ------------------------------------------------------------- D-06 (golden)
def test_d06_only_a_sealed_vocabulary_reaches_the_ordinary_checks() -> None:
    h = chain()
    for seal, expected in (
        (None, "SEAL_STATUS_MISSING"),
        ("SEAL_FAIL", "VOCABULARY_UNRESOLVED"),
    ):
        v = PropertyVocabulary(
            "vocab", "1", "t", PROPS, (), Ref("hext", "vocab-v1", anything(seal))
        )
        assert codes(check_r3(h, v)) == {("UNVERIFIABLE", expected)}
    assert codes(check_r3(h, vocab())) == {("PASS", None)}


# ------------------------------------------------------------------- D-07
def test_d07_seal_and_validity_are_read_from_the_ref_alone() -> None:
    import inspect

    assert list(inspect.signature(check_r5).parameters) == ["history"]
    ev = Ref("checker_output", "e", "SEAL_OK", "CHECKED_BY_TOOL", "c", "1")
    h = chain(
        morphisms=[
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("k", "A", "C", verification="VERIFIED", evidence=(ev,)),
        ]
    )
    assert codes(check_r5(h)) == {("PASS", None)}


# ------------------------------------------------------------------- D-08
def test_d08_the_order_of_the_state_list_has_no_meaning() -> None:
    sp = [Span("s1", 0, 1), Span("s1", 2, 3), Span("s1", 4, 5)]
    states = [state(x, s) for x, s in zip("ABC", sp, strict=True)]
    forward = chain(states=states)
    backward = chain(states=list(reversed(states)))
    assert codes(check_r7(forward, {"s1": True})) == {("PASS", None)}
    assert codes(check_r7(backward, {"s1": True})) == {("PASS", None)}
    overlap = chain(
        states=[state("A", Span("s1", 0, 3)), state("B", Span("s1", 2, 3)), state("C")]
    )
    assert codes(check_r7(overlap, {"s1": True})) == {("PASS", None)}


# ------------------------------------------------------------------- D-09
def test_d09_no_identity_in_the_source_is_r2s_finding_not_r8s() -> None:
    src = history([state("A"), state("B")], [mor("f", "A", "B")], identities=False)
    dst = history([state("A2"), state("B2")], [mor("f2", "A2", "B2")], identities=False)
    out = check_r8(src, dst, {"A": "A2", "B": "B2"}, {"f": "f2"})
    assert codes(out) == {("PASS", None)}
    assert ("UNVERIFIABLE", "IDENTITY_MISSING") in codes(check_r2(src))


# ------------------------------------------------------------------- D-10
def test_d10_identity_endpoints_are_r1_and_content_is_r3() -> None:
    bad_ends = chain()
    bad_ends = replace(
        bad_ends,
        morphisms=tuple(
            replace(m, target_state_id="B") if m.morphism_id == "ia" else m
            for m in bad_ends.morphisms
        ),
    )
    assert ("FAIL", "ENDPOINT_MISMATCH") in codes(check_r1(bad_ends))
    lossy = replace(ident("A"), lost=("order",))
    h = chain()
    h = replace(
        h, morphisms=(*(m for m in h.morphisms if m.morphism_id != "ia"), lossy)
    )
    assert ("FAIL", "IDENTITY_MALFORMED") in codes(check_r3(h, vocab()))


# ------------------------------------------------------------------- D-11
def test_d11_a_null_rule_ref_is_unverifiable_for_every_morphism() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", rule_ref=None),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ]
    )
    assert at(check_r5(h), "RULE_UNREFERENCED") == [("morphism", "f", "rule_ref")]


# ------------------------------------------------------------------- D-13
def test_d13_verified_without_evidence_is_fail_not_unverifiable() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("k", "A", "C", verification="VERIFIED"),
        ]
    )
    assert codes(check_r5(h)) == {("FAIL", "VERIFIED_WITHOUT_EVIDENCE")}


# ------------------------------------------------------------------- D-14
def test_d14_partial_means_a_source_element_has_no_image() -> None:
    src = chain()
    smap = {"A": "A2", "B": "B2", "C": "C2"}
    mmap = {m.morphism_id: m.morphism_id + "2" for m in src.morphisms}
    dst = history(
        [state("A2"), state("B2"), state("C2")],
        [
            mor(
                m.morphism_id + "2",
                m.source_state_id + "2",
                m.target_state_id + "2",
                role=m.role,
                rule_ref=m.rule_ref,
                carry=m.carry,
                preserved=m.preserved,
            )
            for m in src.morphisms
        ],
        [Composition("f2", "g2", "k2")],
        identities=False,
    )
    ok = check_r8(src, dst, smap, mmap)
    assert codes(ok) == {("PASS", None)}
    assert ok[0].warnings == ()
    extra = check_r8(src, dst, {**smap, "Z": "Z2"}, {**mmap, "zz": "zz2"})
    assert codes(extra) == {("PASS", None)}
    assert [(w.reason_code, w.location.id) for w in extra[0].warnings] == [
        ("MAP_EXTRA_ENTRY", "Z"),
        ("MAP_EXTRA_ENTRY", "zz"),
    ]
    missing = check_r8(src, dst, smap, {k: v for k, v in mmap.items() if k != "g"})
    assert codes(missing) == {("UNVERIFIABLE", "FUNCTOR_PARTIAL")}


# ------------------------------------------------------- D-16 .. D-18, D-21..24
def test_d16_undeclared_only_for_non_identity_morphisms_in_compositions() -> None:
    lonely = mor("z", "A", "B", preserved=("shape",))
    h = chain(
        morphisms=[mor("f", "A", "B"), mor("g", "B", "C"), mor("k", "A", "C"), lonely]
    )
    assert ("UNVERIFIABLE", "PROPERTY_UNDECLARED") not in codes(check_r3(h, vocab()))


def test_d17_partial_carry_is_unverifiable() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", carry={"shape": "shape"}),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ]
    )
    assert codes(check_r3(h, vocab())) == {("UNVERIFIABLE", "CARRY_MISSING")}


def test_d21_identity_carry_null_reads_as_identity_map() -> None:
    h = chain()
    h = replace(
        h,
        morphisms=tuple(
            replace(m, carry=None) if m.role == "identity" else m for m in h.morphisms
        ),
    )
    assert codes(check_r3(h, vocab())) == {("PASS", None)}


def test_d22_d24_image_outside_target_and_no_inverse_terms() -> None:
    src = chain()
    dst = chain()
    out = check_r8(
        src,
        dst,
        {"A": "Q", "B": "B", "C": "C"},
        {m.morphism_id: m.morphism_id for m in src.morphisms},
    )
    assert ("FAIL", "FUNCTOR_IMAGE_UNRESOLVED") in codes(out)
    assert ("UNVERIFIABLE", "INVERSE_UNRESOLVED") in codes(
        check_r4(invertible_pair(compositions=[]))
    )


def test_d23_r8_skips_source_entries_that_do_not_chain() -> None:
    src = chain(compositions=[Composition("g", "f", "k")])
    dst = chain()
    ident_map = {m.morphism_id: m.morphism_id for m in src.morphisms}
    out = check_r8(src, dst, {"A": "A", "B": "B", "C": "C"}, ident_map)
    assert codes(out) == {("PASS", None)}
    assert ("FAIL", "COMPOSITION_ENDPOINT_MISMATCH") in codes(check_r1(src))


# ------------------------------------------------------------------- D-25
def test_d25_branch_shape_is_in_the_type_and_the_canonical_json() -> None:
    b = AbandonedBranch("b1", ("S", "R"), ("x",))
    assert b.to_dict() == {
        "branch_id": "b1",
        "morphism_ids": ["x"],
        "state_ids": ["R", "S"],
    }
    assert AbandonedBranch.from_dict(b.to_dict()).to_dict() == b.to_dict()
    assert canonical_json(b.to_dict()) == (
        '{"branch_id":"b1","morphism_ids":["x"],"state_ids":["R","S"]}'
    )
    assert "state_ids" in (AbandonedBranch.__doc__ or "")


# ------------------------------------------------------------------- D-12
def test_d12_type_defects_are_results_not_exceptions() -> None:
    h = chain()
    variants: dict[str, Any] = {
        "task_ref": broke(h, task_ref=5),
        "history_id": broke(h, history_id=5),
        "vocabulary_ref": broke(h, vocabulary_ref="x"),
        "prev": broke(h, prev_history_hash=3),
        "state": broke(h, states=(*h.states, 7)),
        "state_field": broke(h, states=(broke(h.states[0], kind=1),)),
        "span": broke(
            h, states=(broke(h.states[0], span=Span("s", anything(1.5), 2)),)
        ),
        "span_type": broke(h, states=(broke(h.states[0], span="x"),)),
        "morphism": broke(h, morphisms=(*h.morphisms, None)),
        "preserved": broke(h, morphisms=(broke(h.morphisms[0], preserved=None),)),
        "carry": broke(h, morphisms=(broke(h.morphisms[0], carry=5),)),
        "carry_values": broke(
            h, morphisms=(broke(h.morphisms[0], carry=anything({"p": 1})),)
        ),
        "evidence": broke(h, morphisms=(broke(h.morphisms[0], evidence=(1,)),)),
        "rule_ref": broke(h, morphisms=(broke(h.morphisms[0], rule_ref=1),)),
        "invertibility": broke(h, morphisms=(broke(h.morphisms[0], invertibility=1),)),
        "inverse_id": broke(
            h,
            morphisms=(
                broke(
                    h.morphisms[0],
                    invertibility=Invertibility("invertible", anything(3)),
                ),
            ),
        ),
        "composition": broke(h, compositions=(*h.compositions, "x")),
        "composition_field": broke(
            h, compositions=(Composition("f", anything(1), "k"),)
        ),
        "composition_evidence": broke(
            h, compositions=(Composition("f", "g", "k", evidence=anything((3,))),)
        ),
        "branch": broke(h, abandoned_branches=(5,)),
        "branch_ids": broke(
            h, abandoned_branches=(AbandonedBranch("b", anything((1,)), ()),)
        ),
        "branch_id": broke(
            h, abandoned_branches=(AbandonedBranch(anything(2), (), ()),)
        ),
    }
    for name, bad in variants.items():
        for rule in (check_r1, check_r2, check_r4, check_r5):
            out = rule(bad)
            assert codes(out) == {("FAIL", "INPUT_TYPE_INVALID")}, (name, rule)
        assert codes(check_r3(bad, vocab())) == {("FAIL", "INPUT_TYPE_INVALID")}
        assert codes(check_r6(bad)) == {("FAIL", "INPUT_TYPE_INVALID")}
        assert codes(check_r6(h, bad)) == {("FAIL", "INPUT_TYPE_INVALID")}
        assert codes(check_r7(bad, {})) == {("FAIL", "INPUT_TYPE_INVALID")}
        assert codes(check_r8(bad, h, {}, {})) == {("FAIL", "INPUT_TYPE_INVALID")}
        assert codes(verify_history(bad))  # no exception
    assert codes(check_r1(anything("nope"))) == {("FAIL", "INPUT_TYPE_INVALID")}


def test_d12_other_arguments_with_the_wrong_type() -> None:
    h = chain()
    broken_vocab: Any = PropertyVocabulary(
        "v", "1", "t", anything((1,)), (), Ref("hext", "vocab-v1")
    )
    assert codes(check_r3(h, broken_vocab)) == {("FAIL", "INPUT_TYPE_INVALID")}
    assert codes(check_r3(h, anything("x"))) == {("FAIL", "INPUT_TYPE_INVALID")}
    assert codes(check_r7(h, anything({"s1": "yes"}))) == {
        ("FAIL", "INPUT_TYPE_INVALID")
    }
    assert codes(check_r7(h, anything({"s1": 1}))) == {("FAIL", "INPUT_TYPE_INVALID")}
    assert codes(check_r8(h, h, anything({"A": 1}), {})) == {
        ("FAIL", "INPUT_TYPE_INVALID")
    }
    assert codes(check_r8(h, h, {}, anything("x"))) == {("FAIL", "INPUT_TYPE_INVALID")}
    assert Location("field", "h", "x").field == "x"


_ids = st.sampled_from(["A", "B", "C", "x", "x", "", "Z"])


@st.composite
def _broken_histories(draw: st.DrawFn) -> RepresentationHistory:
    """Histories with dangling references, duplicate ids and odd values."""
    states = [
        state(draw(_ids), span)
        for span in draw(
            st.lists(
                st.one_of(
                    st.none(),
                    st.builds(
                        Span,
                        st.sampled_from(["s1", "s2"]),
                        st.integers(-2, 5),
                        st.integers(-2, 5),
                    ),
                ),
                max_size=4,
            )
        )
    ]
    names = ["f", "g", "h", "f", ""]
    morphisms = [
        mor(
            draw(st.sampled_from(names)),
            draw(_ids),
            draw(_ids),
            role=draw(
                st.sampled_from(["generator", "identity", "composite", "inverse_claim"])
            ),
            rule_ref=draw(
                st.sampled_from([None, Ref("hext", "r", "SEAL_OK"), Ref("hext", "r")])
            ),
            preserved=tuple(
                draw(st.lists(st.sampled_from(["p", "q", "zz"]), max_size=3))
            ),
            lost=tuple(draw(st.lists(st.sampled_from(["p", "i"]), max_size=2))),
            carry=draw(st.sampled_from([None, {}, {"p": "q"}, {"p": "p", "q": "q"}])),
            verification=draw(st.sampled_from(["UNVERIFIED", "VERIFIED"])),
            evidence=tuple(
                draw(
                    st.lists(
                        st.sampled_from(
                            [
                                Ref("theorem_name", "T"),
                                Ref("hext", "e", "SEAL_OK", "CHECKED_BY_TOOL"),
                                Ref("hext", "e", "SEAL_FAIL", "REFUTED"),
                                Ref("hext", "e"),
                            ]
                        ),
                        max_size=2,
                    )
                )
            ),
            invertibility=Invertibility(
                draw(st.sampled_from(["unknown", "invertible"])),
                draw(st.sampled_from([None, "f", "g", "nope"])),
            ),
        )
        for _ in range(draw(st.integers(0, 5)))
    ]
    comps = [
        Composition(
            draw(st.sampled_from(names)),
            draw(st.sampled_from(names)),
            draw(st.sampled_from(names)),
        )
        for _ in range(draw(st.integers(0, 6)))
    ]
    branches = [
        AbandonedBranch(
            draw(st.sampled_from(["b", "c"])),
            tuple(draw(st.lists(_ids, max_size=2))),
            tuple(draw(st.lists(st.sampled_from(names), max_size=2))),
        )
        for _ in range(draw(st.integers(0, 2)))
    ]
    return RepresentationHistory(
        "h",
        "t",
        draw(st.sampled_from([Ref("hext", "vocab-v1"), Ref("hext", "other")])),
        tuple(states),
        tuple(morphisms),
        tuple(comps),
        tuple(branches),
        draw(st.sampled_from([None, "deadbeef"])),
        draw(st.sampled_from(["", "deadbeef"])),
    )


@settings(max_examples=250, deadline=None)
@given(
    _broken_histories(),
    _broken_histories(),
    st.sampled_from([None, {}, {"s1": True}, {"s1": False, "s2": True}]),
    st.sampled_from([None, vocab()]),
)
def test_d12_no_exception_on_broken_histories(
    a: RepresentationHistory,
    b: RepresentationHistory,
    eligibility: dict[str, bool] | None,
    vocabulary: PropertyVocabulary | None,
) -> None:
    results = verify_history(
        a, vocabulary=vocabulary, eligibility=eligibility, previous=b
    )
    assert {r.rule for r in results} == {f"R{n}" for n in range(1, 8)}
    for r in results:
        assert r.status == "PASS" or (r.reason_code and r.locations)
    names = sorted({m.morphism_id for m in a.morphisms} | {"zz"})
    sids = sorted({s.state_id for s in a.states} | {"Q"})
    for sm, mm in itertools.product(
        [dict.fromkeys(sids, "A"), {}],
        [dict.fromkeys(names, "f"), {names[0]: "nope"}, {}],
    ):
        check_r8(a, b, sm, mm)
    derive_unit_compositions(a)
    _Index(a)


# ------------------------------------------------- D-15 audit across R1..R8
def test_d15_r5_reports_refuted_and_seal_failed_rule_together() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor(
                "k",
                "A",
                "C",
                verification="VERIFIED",
                rule_ref=Ref("hext", "rule", "SEAL_FAIL"),
                evidence=(Ref("hext", "e", "SEAL_OK", "REFUTED"), Ref("hext", "e2")),
            ),
        ]
    )
    out = check_r5(h)
    assert {c for _, c in codes(out)} == {
        "VERIFIED_ON_REFUTED",
        "RULE_SEAL_FAILED",
        "SEAL_STATUS_MISSING",
    }


def test_d15_r4_reports_missing_identity_and_endpoint_mismatch_together() -> None:
    base = invertible_pair()
    h = replace(
        base,
        morphisms=tuple(
            replace(m, source_state_id="A", target_state_id="A")
            if m.morphism_id == "r"
            else m
            for m in base.morphisms
            if m.morphism_id != "ia"
        ),
    )
    assert codes(check_r4(h)) == {
        ("FAIL", "INVERSE_ENDPOINT_MISMATCH"),
        ("UNVERIFIABLE", "IDENTITY_MISSING"),
    }


def test_d15_r4_missing_identity_still_reports_absent_terms() -> None:
    base = invertible_pair(compositions=[Composition("f", "r", "ia")])
    h = replace(
        base, morphisms=tuple(m for m in base.morphisms if m.morphism_id != "ib")
    )
    assert codes(check_r4(h)) == {
        ("UNVERIFIABLE", "IDENTITY_MISSING"),
        ("UNVERIFIABLE", "INVERSE_ONE_SIDED"),
    }


def test_d15_r8_identity_with_wrong_endpoints_is_also_not_preserved() -> None:
    src = chain()
    dst = chain()
    mm = {m.morphism_id: m.morphism_id for m in src.morphisms}
    mm["ia"] = "f"  # an identity sent to a morphism A -> B
    out = check_r8(src, dst, {"A": "A", "B": "B", "C": "C"}, mm)
    assert codes(out) == {
        ("FAIL", "FUNCTOR_ENDPOINT_MISMATCH"),
        ("FAIL", "IDENTITY_NOT_PRESERVED"),
    }
