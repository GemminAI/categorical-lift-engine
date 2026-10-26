"""R0b: behaviour of each verifier beyond the golden examples."""

from __future__ import annotations

from dataclasses import replace

import pytest

from cle.errors import FunctorialityViolation
from cle.representation import (
    AbandonedBranch,
    CheckResult,
    Composition,
    Invertibility,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    Span,
    aggregate,
    check_r1,
    check_r2,
    check_r3,
    check_r4,
    check_r5,
    check_r6,
    check_r7,
    check_r8,
    complete_identities,
    finite_category_of,
    verify_history,
)
from cle.topology.category_theory import FiniteCategory, Functor, Morphism
from representation_builders import (
    PROPS,
    VOCAB_REF,
    chain,
    history,
    ident,
    invertible_pair,
    mor,
    state,
    vocab,
)


def codes(results: list[CheckResult]) -> list[tuple[str, str | None]]:
    return [(r.status, r.reason_code) for r in results]


def locs(results: list[CheckResult], code: str) -> list[tuple[str, str, str | None]]:
    return [
        (loc.kind, loc.id, loc.field)
        for r in results
        if r.reason_code == code
        for loc in r.locations
    ]


def ok(status: str = "PASS") -> list[tuple[str, None]]:
    return [(status, None)]


# ---------------------------------------------------------------- whole history


def test_clean_history_passes_r1_to_r5_and_r7() -> None:
    h = chain()
    out = verify_history(h, vocabulary=vocab(), eligibility={})
    assert [(r.rule, r.status) for r in out] == [
        ("R1", "PASS"),
        ("R2", "PASS"),
        ("R3", "PASS"),
        ("R4", "PASS"),
        ("R5", "PASS"),
        ("R6", "UNVERIFIABLE"),
        ("R7", "PASS"),
    ]
    assert aggregate(out) == "UNVERIFIABLE"


def test_chained_second_version_passes_r6() -> None:
    v1 = chain()
    v2 = replace(v1, prev_history_hash=v1.history_hash).seal()
    out = verify_history(v2, vocabulary=vocab(), eligibility={}, previous=v1)
    assert aggregate(out) == "PASS"


def test_results_are_reproducible_bit_for_bit() -> None:
    h = chain()
    a = verify_history(h, vocabulary=vocab(), eligibility={})
    b = verify_history(chain(), vocabulary=vocab(), eligibility={})
    assert a == b
    assert [r.inputs_sha256 for r in a] == [r.inputs_sha256 for r in b]
    changed = verify_history(
        chain(states=[state("A"), state("B"), state("C", description="d")]),
        vocabulary=vocab(),
        eligibility={},
    )
    assert changed[0].inputs_sha256 != a[0].inputs_sha256


# ------------------------------------------------------------------------- R1


def test_r1_duplicates_and_bad_identity_and_unresolved_composition() -> None:
    h = history(
        [state("A"), state("A"), state("B")],
        [
            mor("f", "A", "B"),
            mor("f", "A", "B"),
            mor("j", "A", "B", role="identity"),
        ],
        [Composition("f", "nope", "f"), Composition("nope", "f", "zzz")],
        identities=False,
    )
    out = check_r1(h)
    assert ("FAIL", "DUPLICATE_ID") in codes(out)
    assert locs(out, "DUPLICATE_ID") == [("state", "A", None), ("morphism", "f", None)]
    assert locs(out, "ENDPOINT_MISMATCH") == [("morphism", "j", "target_state_id")]
    assert locs(out, "MORPHISM_UNRESOLVED") == [
        ("composition", "f|nope", "second"),
        ("composition", "nope|f", "first"),
        ("composition", "nope|f", "result"),
    ]
    assert aggregate(out) == "FAIL"


def test_r1_source_state_unresolved_is_located() -> None:
    out = check_r1(history([state("B")], [mor("f", "Z", "B")]))
    assert locs(out, "STATE_UNRESOLVED") == [("morphism", "f", "source_state_id")]


def test_finite_category_of_wraps_existing_exceptions() -> None:
    good = finite_category_of(chain())
    assert isinstance(good, FiniteCategory)
    assert good.compose("g", "f") == "k"
    bad_endpoint = history([state("A")], [mor("f", "A", "Z")])
    r = finite_category_of(bad_endpoint)
    assert isinstance(r, CheckResult) and r.status == "FAIL"
    assert r.reason_code == "FINITE_CATEGORY_REJECTED"
    missing = chain(compositions=[Composition("f", "nope", "k")])
    assert isinstance(finite_category_of(missing), CheckResult)
    not_composable = chain(compositions=[Composition("g", "f", "k")])
    assert isinstance(finite_category_of(not_composable), CheckResult)
    # the wrapped class itself still raises, unchanged
    with pytest.raises(ValueError):
        FiniteCategory(frozenset({"A"}), {"f": Morphism("f", "A", "Z")}, {})


# ------------------------------------------------------------------------- R2


def test_r2_missing_composition_pair_and_no_compositions_at_all() -> None:
    h = chain(compositions=[])
    out = check_r2(h)
    assert locs(out, "COMPOSITION_UNDEFINED") == [("composition", "f|g", None)]
    assert locs(out, "COMPOSITE_BY_CONSTRUCTION") == [("field", "h", "compositions")]
    assert aggregate(out) == "UNVERIFIABLE"


def test_r2_duplicate_identity_and_functionality_and_unit_law() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
            ident("A").__class__("ia2", "A", "A", role="identity"),
        ],
        compositions=[
            Composition("f", "g", "k"),
            Composition("f", "g", "f"),
            Composition("ia", "f", "g"),
            Composition("g", "ic", "f"),
            Composition("ia", "ia", "ia"),
        ],
    )
    out = check_r2(h)
    assert locs(out, "DUPLICATE_IDENTITY") == [("state", "A", None)]
    assert locs(out, "COMPOSITION_NOT_FUNCTIONAL") == [("composition", "f|g", None)]
    assert locs(out, "UNIT_LAW_VIOLATION") == [
        ("composition", "g|ic", None),
        ("composition", "ia|f", None),
    ]


def test_r2_unit_entries_that_are_correct_pass() -> None:
    h = chain(
        compositions=[
            Composition("f", "g", "k"),
            Composition("ia", "f", "f"),
            Composition("g", "ic", "g"),
        ]
    )
    assert codes(check_r2(h)) == ok()


def test_r2_composition_with_unresolved_or_non_composable_morphisms_is_skipped() -> (
    None
):
    h = chain(
        compositions=[
            Composition("f", "g", "k"),
            Composition("nope", "g", "k"),
            Composition("g", "f", "k"),
        ]
    )
    assert codes(check_r2(h)) == ok()


def test_r2_associativity_ignores_undefined_intermediate_terms() -> None:
    h = history(
        [state(x) for x in "ABCD"],
        [
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("h", "C", "D"),
            mor("k", "A", "C"),
        ],
        [Composition("f", "g", "k")],
    )
    out = check_r2(h)
    assert codes(out) == [("UNVERIFIABLE", "COMPOSITION_UNDEFINED")]
    assert locs(out, "COMPOSITION_UNDEFINED") == [
        ("composition", "g|h", None),
        ("composition", "k|h", None),
    ]


def test_r2_associativity_holds_on_a_consistent_square() -> None:
    h = history(
        [state(x) for x in "ABCD"],
        [
            mor("f", "A", "B"),
            mor("g", "B", "C"),
            mor("h", "C", "D"),
            mor("k", "A", "C"),
            mor("m", "B", "D"),
            mor("p", "A", "D"),
        ],
        [
            Composition("f", "g", "k"),
            Composition("g", "h", "m"),
            Composition("k", "h", "p"),
            Composition("f", "m", "p"),
        ],
    )
    assert codes(check_r2(h)) == ok()


def test_r2_identity_results_do_not_count_as_independent_records() -> None:
    out = check_r2(invertible_pair())
    assert codes(out) == [("UNVERIFIABLE", "COMPOSITE_BY_CONSTRUCTION")]
    assert locs(out, "COMPOSITE_BY_CONSTRUCTION") == [("field", "h", "compositions")]


# ------------------------------------------------------------------------- R3


def test_r3_vocabulary_unresolved_cases() -> None:
    h = chain()
    assert codes(check_r3(h, None)) == [("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")]
    other = PropertyVocabulary("v", "1", "t", PROPS, (), Ref("hext", "different"))
    assert codes(check_r3(h, other)) == [("UNVERIFIABLE", "VOCABULARY_UNRESOLVED")]


def test_r3_names_outside_the_vocabulary_and_undeclared_properties() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", preserved=("shape", "weird"), carry={"shape": "zz"}),
            mor("g", "B", "C", preserved=("shape",)),
            mor("k", "A", "C", preserved=(), lost=("count",)),
        ]
    )
    out = check_r3(h, vocab())
    assert locs(out, "VOCABULARY_UNRESOLVED") == [
        ("morphism", "f", "preserved"),
        ("morphism", "f", "carry"),
    ]
    assert locs(out, "PROPERTY_UNDECLARED") == [
        ("morphism", "f", "preserved"),
        ("morphism", "g", "preserved"),
        ("morphism", "k", "preserved"),
    ]


def test_r3_malformed_identity() -> None:
    bad = replace(ident("A"), lost=("order",))
    short = replace(ident("B"), preserved=("shape",))
    h = chain(morphisms=[mor("f", "A", "B"), mor("g", "B", "C"), mor("k", "A", "C")])
    h = replace(
        h,
        morphisms=(
            *(m for m in h.morphisms if m.morphism_id not in ("ia", "ib")),
            bad,
            short,
        ),
    ).seal()
    assert locs(check_r3(h, vocab()), "IDENTITY_MALFORMED") == [
        ("morphism", "ia", "preserved"),
        ("morphism", "ib", "preserved"),
    ]


def test_r3_carry_failures_and_lost_pullback() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", carry={"shape": "count", "count": "shape"}),
            mor("g", "B", "C", preserved=("shape",), lost=("count",)),
            mor("k", "A", "C", preserved=("shape", "count")),
        ]
    )
    out = check_r3(h, vocab())
    assert ("FAIL", "PRESERVED_NOT_CARRIED") in codes(out)
    assert locs(out, "PRESERVED_NOT_CARRIED") == [("morphism", "k", "preserved")]
    # carry_f(shape)=count is lost in g, so shape must be lost in k
    assert ("morphism", "k", "lost") in locs(out, "LOST_NOT_PROPAGATED")


def test_r3_partial_carry_is_unverifiable_not_fail() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", carry={"shape": "shape"}),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ]
    )
    assert locs(check_r3(h, vocab()), "CARRY_MISSING") == [("morphism", "f", "carry")]


def test_r3_identity_without_carry_acts_as_identity_map() -> None:
    no_carry = replace(ident("A"), carry=None)
    h = chain()
    h = replace(
        h,
        morphisms=(*(m for m in h.morphisms if m.morphism_id != "ia"), no_carry),
        compositions=(Composition("f", "g", "k"), Composition("ia", "f", "f")),
    ).seal()
    assert codes(check_r3(h, vocab())) == ok()


def test_r3_skips_compositions_with_unresolved_or_mismatched_morphisms() -> None:
    h = chain(
        compositions=[
            Composition("f", "g", "k"),
            Composition("f", "nope", "k"),
            Composition("g", "f", "k"),
        ]
    )
    assert codes(check_r3(h, vocab())) == ok()


# ------------------------------------------------------------------------- R4


def test_r4_pass_needs_both_sides() -> None:
    assert codes(check_r4(invertible_pair())) == ok()


def test_r4_unresolved_inverse_and_endpoints_and_missing_identity() -> None:
    no_inverse = invertible_pair(
        morphisms=[mor("f", "A", "B", invertibility=Invertibility("invertible"))],
        compositions=[],
    )
    assert locs(check_r4(no_inverse), "INVERSE_UNRESOLVED") == [
        ("morphism", "f", "invertibility")
    ]
    ghost = invertible_pair(
        morphisms=[mor("f", "A", "B", invertibility=Invertibility("invertible", "zz"))],
        compositions=[],
    )
    assert codes(check_r4(ghost)) == [("UNVERIFIABLE", "INVERSE_UNRESOLVED")]
    wrong = invertible_pair(
        morphisms=[
            mor("f", "A", "B", invertibility=Invertibility("invertible", "r")),
            mor("r", "A", "B", role="inverse_claim"),
        ],
        compositions=[],
    )
    assert codes(check_r4(wrong)) == [("FAIL", "INVERSE_ENDPOINT_MISMATCH")]
    base = invertible_pair()
    lacking = replace(
        base,
        morphisms=tuple(m for m in base.morphisms if m.morphism_id != "ia"),
    )
    assert locs(check_r4(lacking), "IDENTITY_MISSING") == [("state", "A", None)]


def test_r4_no_terms_at_all_and_not_identity_on_other_side() -> None:
    none = invertible_pair(compositions=[])
    out = check_r4(none)
    assert locs(out, "INVERSE_UNRESOLVED") == [
        ("composition", "f|r", None),
        ("composition", "r|f", None),
    ]
    swapped = invertible_pair(
        compositions=[Composition("f", "r", "ib"), Composition("r", "f", "ib")]
    )
    assert locs(check_r4(swapped), "INVERSE_NOT_IDENTITY") == [
        ("composition", "f|r", None)
    ]


def test_r4_only_invertible_claims_are_examined() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", invertibility=Invertibility("not_invertible")),
            mor("g", "B", "C", invertibility=Invertibility("unknown")),
            mor("k", "A", "C"),
        ]
    )
    assert codes(check_r4(h)) == ok()


def test_r4_an_empty_lost_alone_does_not_pass() -> None:
    h = chain(
        morphisms=[
            mor("f", "A", "B", invertibility=Invertibility("invertible", "g")),
            mor("g", "B", "C"),
            mor("k", "A", "C"),
        ]
    )
    assert codes(check_r4(h)) == [("FAIL", "INVERSE_ENDPOINT_MISMATCH")]
    pair = invertible_pair(compositions=[])
    assert aggregate(check_r4(pair)) == "UNVERIFIABLE"


def test_r4_identity_claims_itself_as_inverse() -> None:
    h = chain()
    self_inverse = replace(ident("A"), invertibility=Invertibility("invertible", "ia"))
    h = replace(
        h,
        morphisms=(*(m for m in h.morphisms if m.morphism_id != "ia"), self_inverse),
    ).seal()
    assert codes(check_r4(h)) == ok()


# ------------------------------------------------------------------------- R5


def ev(validity: str | None, seal: str | None = "SEAL_OK", kind: str = "hext") -> Ref:
    return Ref(kind, "e", seal_status=seal, validity=validity)  # type: ignore[arg-type]


def r5(**kw: object) -> list[CheckResult]:
    return check_r5(
        chain(
            morphisms=[
                mor("f", "A", "B"),
                mor("g", "B", "C"),
                mor("k", "A", "C", **kw),
            ]
        )
    )


def test_r5_verified_with_sealed_checked_evidence_passes() -> None:
    for validity in ("CHECKED_BY_TOOL", "CHECKED_BY_HUMAN"):
        for kind in ("hext", "checker_output"):
            out = r5(verification="VERIFIED", evidence=(ev(validity, kind=kind),))
            assert codes(out) == ok()


def test_r5_failures_and_unverifiables() -> None:
    cases = {
        "refuted": (
            dict(
                verification="VERIFIED",
                evidence=(ev("CHECKED_BY_TOOL"), ev("REFUTED")),
            ),
            ("FAIL", "VERIFIED_ON_REFUTED"),
        ),
        "rule seal fail": (
            dict(
                verification="VERIFIED",
                rule_ref=Ref("hext", "r", seal_status="SEAL_FAIL"),
                evidence=(ev("CHECKED_BY_TOOL"),),
            ),
            ("FAIL", "RULE_SEAL_FAILED"),
        ),
        "no evidence": (
            dict(verification="VERIFIED"),
            ("FAIL", "VERIFIED_WITHOUT_EVIDENCE"),
        ),
        "seal fail": (
            dict(
                verification="VERIFIED", evidence=(ev("CHECKED_BY_TOOL", "SEAL_FAIL"),)
            ),
            ("FAIL", "VERIFIED_WITHOUT_EVIDENCE"),
        ),
        "validity unknown": (
            dict(verification="VERIFIED", evidence=(ev(None),)),
            ("FAIL", "VERIFIED_WITHOUT_EVIDENCE"),
        ),
        "name only": (
            dict(
                verification="VERIFIED", evidence=(Ref("theorem_name", "Pigeonhole"),)
            ),
            ("UNVERIFIABLE", "EVIDENCE_NAME_ONLY"),
        ),
        "history ref only": (
            dict(verification="VERIFIED", evidence=(Ref("history", "x"),)),
            ("UNVERIFIABLE", "EVIDENCE_NAME_ONLY"),
        ),
        "seal not supplied": (
            dict(verification="VERIFIED", evidence=(ev("CHECKED_BY_TOOL", None),)),
            ("UNVERIFIABLE", "SEAL_STATUS_MISSING"),
        ),
        "rule seal not supplied": (
            dict(
                verification="VERIFIED",
                rule_ref=Ref("hext", "r"),
                evidence=(ev("CHECKED_BY_TOOL"),),
            ),
            ("UNVERIFIABLE", "SEAL_STATUS_MISSING"),
        ),
    }
    for name, (kw, expected) in cases.items():
        assert codes(r5(**kw)) == [expected], name  # type: ignore[arg-type]


def test_r5_unverified_with_rule_ref_needs_nothing_and_identity_needs_no_rule() -> None:
    assert codes(r5(verification="UNVERIFIED")) == ok()
    verified_identity = replace(
        ident("A"),
        verification="VERIFIED",
        evidence=(ev("CHECKED_BY_TOOL", kind="checker_output"),),
    )
    h = chain()
    h = replace(
        h,
        morphisms=(
            *(m for m in h.morphisms if m.morphism_id != "ia"),
            verified_identity,
        ),
    ).seal()
    assert codes(check_r5(h)) == ok()


# ------------------------------------------------------------------------- R6


def test_r6_unresolved_previous_version() -> None:
    v1 = chain()
    v2 = replace(v1, prev_history_hash=v1.history_hash).seal()
    assert codes(check_r6(v2)) == [("UNVERIFIABLE", "PREV_HISTORY_UNRESOLVED")]
    other = chain(states=[state("A"), state("B"), state("C", description="x")])
    assert codes(check_r6(v2, other)) == [("UNVERIFIABLE", "PREV_HISTORY_UNRESOLVED")]


def test_r6_dropped_states_and_morphisms_and_shrunk_branch() -> None:
    v1 = history(
        [state("A"), state("X"), state("Y")],
        [mor("x", "A", "X"), mor("y", "A", "Y")],
        branches=[AbandonedBranch("b1", ("X", "Y"), ("x", "y")), AbandonedBranch("b2")],
    )
    v2 = history(
        [state("A"), state("X")],
        [mor("x", "A", "X")],
        branches=[AbandonedBranch("b1", ("X",), ("x",)), AbandonedBranch("b2")],
        prev=v1.history_hash,
    )
    out = check_r6(v2, v1)
    assert locs(out, "ELEMENT_DROPPED") == [
        ("state", "Y", None),
        ("morphism", "iy", None),
        ("morphism", "y", None),
    ]
    assert locs(out, "BRANCH_DROPPED") == [("field", "b1", "abandoned_branches")]
    grown = history(
        [state("A"), state("X"), state("Y")],
        [mor("x", "A", "X"), mor("y", "A", "Y")],
        branches=[
            AbandonedBranch("b1", ("X", "Y"), ("x",)),
            AbandonedBranch("b2"),
        ],
        prev=v1.history_hash,
    )
    assert locs(check_r6(grown, v1), "BRANCH_DROPPED") == [
        ("field", "b1", "abandoned_branches")
    ]


def test_r6_cycles_are_failures_but_identities_and_inverse_claims_are_not() -> None:
    cyc = history(
        [state("A"), state("B"), state("C")],
        [mor("f", "A", "B"), mor("g", "B", "A"), mor("h", "B", "C")],
    )
    out = check_r6(cyc)
    assert locs(out, "CYCLE") == [("state", "A", None), ("state", "B", None)]
    selfloop = history([state("A")], [mor("s", "A", "A")])
    assert locs(check_r6(selfloop), "CYCLE") == [("state", "A", None)]
    inverse_ok = invertible_pair()
    assert "CYCLE" not in [r.reason_code for r in check_r6(inverse_ok)]
    assert "CYCLE" not in [r.reason_code for r in check_r6(chain())]


# ------------------------------------------------------------------------- R7


def sp(a: int, b: int, s: str = "s1") -> Span:
    return Span(s, a, b)


def test_r7_pass_order_and_cross_state_order() -> None:
    good = history(
        [state("A", sp(0, 2)), state("B", sp(3, 5)), state("C")],
        [mor("f", "A", "B")],
    )
    assert codes(check_r7(good, {"s1": True})) == ok()
    bad_span = history([state("A", sp(5, 2)), state("B", sp(-1, 0))], [])
    out = check_r7(bad_span, {"s1": True})
    assert locs(out, "SPAN_ORDER") == [("state", "A", "span"), ("state", "B", "span")]
    reversed_ = history(
        [state("A", sp(10, 12)), state("B", sp(3, 5))], [mor("f", "A", "B")]
    )
    assert locs(check_r7(reversed_, {"s1": True}), "SPAN_ORDER") == [
        ("morphism", "f", "source_state_id")
    ]
    other_session = history(
        [state("A", sp(10, 12)), state("B", sp(3, 5, "s2"))], [mor("f", "A", "B")]
    )
    assert codes(check_r7(other_session, {"s1": True, "s2": True})) == ok()
    inv = history(
        [state("A", sp(10, 12)), state("B", sp(3, 5))],
        [mor("r", "A", "B", role="inverse_claim")],
    )
    assert codes(check_r7(inv, {"s1": True})) == ok()
    unresolved = history([state("A", sp(0, 1))], [mor("f", "A", "Z")])
    assert codes(check_r7(unresolved, {"s1": True})) == ok()
    no_span = history([state("A"), state("B", sp(0, 1))], [mor("f", "A", "B")])
    assert codes(check_r7(no_span, {"s1": True})) == ok()


def test_r7_missing_verdict_for_one_session() -> None:
    h = history([state("A", Span("s1", 0, 1)), state("B", Span("s2", 0, 1))], [])
    out = check_r7(h, {"s1": True})
    assert locs(out, "ELIGIBILITY_MISSING") == [("state", "B", "span")]
    assert codes(check_r7(history([state("A")], []), None)) == ok()


# ------------------------------------------------------------------------- R8


def twin(suffix: str = "2", *, identities: bool = True) -> RepresentationHistory:
    s = suffix
    return history(
        [state(f"A{s}"), state(f"B{s}"), state(f"C{s}")],
        [
            mor(f"f{s}", f"A{s}", f"B{s}"),
            mor(f"g{s}", f"B{s}", f"C{s}"),
            mor(f"k{s}", f"A{s}", f"C{s}"),
        ],
        [Composition(f"f{s}", f"g{s}", f"k{s}")],
        identities=identities,
    )


SMAP = {"A": "A2", "B": "B2", "C": "C2"}
MMAP = {
    "f": "f2",
    "g": "g2",
    "k": "k2",
    "ia": "ia2",
    "ib": "ib2",
    "ic": "ic2",
}


def test_r8_faithful_map_passes() -> None:
    assert codes(check_r8(chain(), twin(), SMAP, MMAP)) == ok()


def test_r8_images_endpoints_identities() -> None:
    src = chain()
    out = check_r8(src, twin(), {**SMAP, "A": "nope"}, MMAP)
    assert locs(out, "FUNCTOR_IMAGE_UNRESOLVED") == [("state", "A", None)]
    out = check_r8(src, twin(), SMAP, {**MMAP, "f": "nope"})
    assert locs(out, "FUNCTOR_IMAGE_UNRESOLVED") == [("morphism", "f", None)]
    out = check_r8(src, twin(), SMAP, {**MMAP, "f": "g2"})
    assert locs(out, "FUNCTOR_ENDPOINT_MISMATCH") == [("morphism", "f", None)]
    out = check_r8(src, twin(), SMAP, {**MMAP, "ia": "f2"})
    assert locs(out, "FUNCTOR_ENDPOINT_MISMATCH") == [("morphism", "ia", None)]
    out = check_r8(src, twin(), SMAP, {**MMAP, "ia": "ib2"})
    assert locs(out, "FUNCTOR_ENDPOINT_MISMATCH") == [("morphism", "ia", None)]


def test_r8_identity_must_go_to_an_identity() -> None:
    src = chain()
    stray = twin()
    stray = replace(stray, morphisms=(*stray.morphisms, mor("w2", "A2", "A2"))).seal()
    out = check_r8(src, stray, SMAP, {**MMAP, "ia": "w2"})
    assert locs(out, "IDENTITY_NOT_PRESERVED") == [("morphism", "ia", None)]
    no_identity = twin(identities=False)
    out = check_r8(src, no_identity, SMAP, {**MMAP, "ia": "f2", "ib": "g2", "ic": "k2"})
    assert locs(out, "FUNCTOR_ENDPOINT_MISMATCH")
    bare = replace(
        no_identity, morphisms=(*no_identity.morphisms, mor("w2", "A2", "A2"))
    ).seal()
    out = check_r8(src, bare, SMAP, {**MMAP, "ia": "w2"})
    assert locs(out, "IDENTITY_PRESERVATION_UNCHECKED") == [("morphism", "ia", None)]
    assert ("UNVERIFIABLE", "IDENTITY_PRESERVATION_UNCHECKED") in codes(out)


def test_r8_composition_undefined_in_target_and_skips() -> None:
    src = chain()
    out = check_r8(src, twin(), SMAP, {**MMAP, "k": "f2"})
    assert locs(out, "FUNCTOR_COMPOSITION_NOT_PRESERVED") == [
        ("composition", "f|g", None)
    ]
    target = history(
        [state("A2"), state("B2"), state("C2")],
        [mor("f2", "A2", "B2"), mor("g2", "B2", "C2"), mor("k2", "A2", "C2")],
    )
    out = check_r8(src, target, SMAP, MMAP)
    assert locs(out, "COMPOSITION_UNDEFINED") == [("composition", "f|g", None)]
    bent = check_r8(src, twin(), SMAP, {**MMAP, "g": "f2"})
    assert not locs(bent, "COMPOSITION_UNDEFINED")
    unmapped = check_r8(src, twin(), SMAP, {k: v for k, v in MMAP.items() if k != "g"})
    assert locs(unmapped, "FUNCTOR_PARTIAL") == [("morphism", "g", None)]


def test_r8_agrees_with_the_existing_functor_on_what_it_does_check() -> None:
    src_cat = finite_category_of(chain())
    dst_cat = finite_category_of(twin())
    assert isinstance(src_cat, FiniteCategory) and isinstance(dst_cat, FiniteCategory)
    Functor(src_cat, dst_cat, dict(SMAP), dict(MMAP))
    with pytest.raises(FunctorialityViolation):
        Functor(src_cat, dst_cat, dict(SMAP), {**MMAP, "k": "f2"})


# ------------------------------------------------------- identity completion


def test_complete_identities_marks_the_verifier_and_chains_the_version() -> None:
    bare = history([state("A"), state("B")], [mor("f", "A", "B")], identities=False)
    done = complete_identities(
        bare, vocab(), generator_name="gen", generator_version="9"
    )
    assert done.prev_history_hash == bare.compute_hash()
    assert done.history_hash == done.compute_hash()
    added = [m for m in done.morphisms if m.role == "identity"]
    assert len(added) == 2
    for m in added:
        assert m.source == "verifier"
        assert m.preserved == PROPS and m.lost == ()
        assert m.morphism_id == m.compute_id()
        (ref,) = m.evidence
        assert (ref.kind, ref.name, ref.version) == ("checker_output", "gen", "9")
    assert codes(check_r2(done))[0][1] != "IDENTITY_MISSING"
    assert not locs(check_r2(done), "IDENTITY_MISSING")
    assert not locs(check_r3(done, vocab()), "IDENTITY_MALFORMED")
    # nothing is rewritten, and a recorder's own identity is left alone
    again = complete_identities(
        done, vocab(), generator_name="gen", generator_version="9"
    )
    assert again.morphisms == done.morphisms
    mixed = history(
        [state("A"), state("B")], [mor("f", "A", "B"), ident("A")], identities=False
    )
    out = complete_identities(mixed, vocab(), generator_name="g", generator_version="1")
    sources = {
        m.source_state_id: m.source for m in out.morphisms if m.role == "identity"
    }
    assert sources == {"A": "unknown", "B": "verifier"}
    assert done.vocabulary_ref == VOCAB_REF


def test_r2_composition_result_that_does_not_exist_is_not_followed() -> None:
    h = history(
        [state(x) for x in "ABCD"],
        [mor("f", "A", "B"), mor("g", "B", "C"), mor("h", "C", "D")],
        [Composition("f", "g", "ghost"), Composition("g", "h", "m")],
    )
    out = check_r2(h)
    assert not locs(out, "ASSOCIATIVITY_VIOLATION")
