"""R0b: the R1-R8 verifiers of CLE v0.3 section 3, and the section 4 aggregate.

Each ``check_rN`` returns a list of `CheckResult`: one PASS result when nothing
was found, otherwise one result per distinct ``(status, reason_code)`` with all
its locations (FAIL results first). A rule is PASS only when it found nothing
that is FAIL *and* nothing it could not verify.

CLE judges structure, never the mathematical validity of the evidence:
``seal_status`` and ``validity`` on a `Ref` are read as given (C4-3).
Where the design is ambiguous the check leans to UNVERIFIABLE; every such
choice is listed in ``docs/representation_ambiguities.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from cle.representation.canonical import sha256_hex
from cle.representation.model import (
    CheckerInfo,
    CheckResult,
    CheckWarning,
    Composition,
    Location,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    RepresentationMorphism,
    RuleId,
    Status,
)
from cle.representation.validate import (
    eligibility_defects,
    history_defects,
    map_defects,
    vocabulary_defects,
)
from cle.topology.category_theory import FiniteCategory, Morphism
from cle.version import __version__

CHECKER = CheckerInfo("cle.representation", f"{__version__}+representation-r0")

Finding = tuple[Status, str, Location]


def _loc(kind: Any, id_: str, field: str | None = None) -> Location:
    return Location(kind, id_, field)


def _pair(first: str, second: str) -> Location:
    return Location("composition", f"{first}|{second}")


def _defect_results(rule: RuleId, defects: Sequence[Location]) -> list[CheckResult]:
    """v0.4 D-12: a defective input is a result, never an exception."""
    digest = sha256_hex({"defects": [d.to_dict() for d in defects]})
    return [
        CheckResult(rule, "FAIL", "INPUT_TYPE_INVALID", tuple(defects), digest, CHECKER)
    ]


def _results(
    rule: RuleId,
    inputs: Mapping[str, Any],
    findings: Sequence[Finding],
    warnings: Sequence[CheckWarning] = (),
) -> list[CheckResult]:
    digest = sha256_hex(dict(inputs))
    extra = tuple(warnings)
    groups: dict[tuple[Status, str], list[Location]] = {}
    for status, code, location in findings:
        locations = groups.setdefault((status, code), [])
        if location not in locations:
            locations.append(location)
    if not groups:
        return [CheckResult(rule, "PASS", None, (), digest, CHECKER, extra)]
    ordered = sorted(groups.items(), key=lambda kv: (kv[0][0] != "FAIL", kv[0][1]))
    return [
        CheckResult(rule, status, code, tuple(locations), digest, CHECKER, extra)
        for (status, code), locations in ordered
    ]


class _Index:
    """Lookup tables over one history. The first record with a given id wins."""

    def __init__(self, history: RepresentationHistory) -> None:
        self.history = history
        self.states: dict[str, Any] = {}
        self.morphisms: dict[str, RepresentationMorphism] = {}
        self.duplicate_states: list[str] = []
        self.duplicate_morphisms: list[str] = []
        for state in history.states:
            if state.state_id in self.states:
                self.duplicate_states.append(state.state_id)
            else:
                self.states[state.state_id] = state
        for morphism in history.morphisms:
            if morphism.morphism_id in self.morphisms:
                self.duplicate_morphisms.append(morphism.morphism_id)
            else:
                self.morphisms[morphism.morphism_id] = morphism
        self.table: dict[tuple[str, str], list[str]] = {}
        for c in history.compositions:
            self.table.setdefault((c.first, c.second), []).append(c.result)
        self.identities: dict[str, list[str]] = {}
        for mid in sorted(self.morphisms):
            if self.is_identity(self.morphisms[mid]):
                self.identities.setdefault(
                    self.morphisms[mid].source_state_id, []
                ).append(mid)

    def is_identity(self, m: RepresentationMorphism) -> bool:
        return (
            m.role == "identity"
            and m.source_state_id == m.target_state_id
            and m.source_state_id in self.states
        )

    def identity_of(self, state_id: str) -> str | None:
        ids = self.identities.get(state_id)
        return ids[0] if ids else None

    def compose(self, first: str, second: str) -> str | None:
        """``second`` after ``first``. Unit laws are derived, not looked up."""
        f, g = self.morphisms.get(first), self.morphisms.get(second)
        if f is None or g is None:
            return None
        if self.is_identity(f):
            return second
        if self.is_identity(g):
            return first
        results = self.table.get((first, second))
        return results[0] if results else None

    def non_identities(self) -> list[RepresentationMorphism]:
        return [
            self.morphisms[mid]
            for mid in sorted(self.morphisms)
            if not self.is_identity(self.morphisms[mid])
        ]


def finite_category_of(
    history: RepresentationHistory,
) -> FiniteCategory | CheckResult:
    """Wrap the existing `FiniteCategory` constructor (R1, section 3).

    Builds the category from the declared states, morphisms and composition
    table, unchanged. Its construction-time exceptions are returned as a FAIL
    `CheckResult` instead of being raised; `FiniteCategory` itself is not
    modified.
    """
    try:
        return FiniteCategory(
            objects=frozenset(s.state_id for s in history.states),
            morphisms={
                m.morphism_id: Morphism(
                    m.morphism_id, m.source_state_id, m.target_state_id
                )
                for m in history.morphisms
            },
            composition={(c.second, c.first): c.result for c in history.compositions},
        )
    except (ValueError, KeyError) as error:
        digest = sha256_hex({"history": history.to_dict()})
        return CheckResult(
            "R1",
            "FAIL",
            "FINITE_CATEGORY_REJECTED",
            (_loc("field", history.history_id, f"finite_category: {error}"),),
            digest,
            CHECKER,
        )


# --------------------------------------------------------------------------
# R1  endpoints
# --------------------------------------------------------------------------


def check_r1(history: RepresentationHistory) -> list[CheckResult]:
    defects = history_defects(history)
    if defects:
        return _defect_results("R1", defects)
    idx = _Index(history)
    findings: list[Finding] = []
    for sid in sorted(set(idx.duplicate_states)):
        findings.append(("FAIL", "DUPLICATE_ID", _loc("state", sid)))
    for mid in sorted(set(idx.duplicate_morphisms)):
        findings.append(("FAIL", "DUPLICATE_ID", _loc("morphism", mid)))
    for mid in sorted(idx.morphisms):
        m = idx.morphisms[mid]
        for field, sid in (
            ("source_state_id", m.source_state_id),
            ("target_state_id", m.target_state_id),
        ):
            if sid not in idx.states:
                findings.append(
                    ("UNVERIFIABLE", "STATE_UNRESOLVED", _loc("morphism", mid, field))
                )
        if m.role == "identity" and m.source_state_id != m.target_state_id:
            findings.append(
                ("FAIL", "ENDPOINT_MISMATCH", _loc("morphism", mid, "target_state_id"))
            )
    for c in history.compositions:
        f, g, h = (idx.morphisms.get(x) for x in (c.first, c.second, c.result))
        unresolved = [
            name
            for name, found in (("first", f), ("second", g), ("result", h))
            if found is None
        ]
        for name in unresolved:
            findings.append(
                (
                    "UNVERIFIABLE",
                    "MORPHISM_UNRESOLVED",
                    Location("composition", f"{c.first}|{c.second}", name),
                )
            )
        if (
            f is not None
            and g is not None
            and h is not None
            and not (
                f.target_state_id == g.source_state_id
                and h.source_state_id == f.source_state_id
                and h.target_state_id == g.target_state_id
            )
        ):
            findings.append(
                ("FAIL", "COMPOSITION_ENDPOINT_MISMATCH", _pair(c.first, c.second))
            )
    return _results("R1", {"history": history.to_dict()}, findings)


# --------------------------------------------------------------------------
# R2  associativity and unit laws
# --------------------------------------------------------------------------


def check_r2(history: RepresentationHistory) -> list[CheckResult]:
    defects = history_defects(history)
    if defects:
        return _defect_results("R2", defects)
    idx = _Index(history)
    findings: list[Finding] = []
    for sid in sorted(idx.states):
        ids = idx.identities.get(sid, [])
        if not ids:
            findings.append(("UNVERIFIABLE", "IDENTITY_MISSING", _loc("state", sid)))
        elif len(ids) > 1:
            findings.append(("FAIL", "DUPLICATE_IDENTITY", _loc("state", sid)))
    for (a, b), results in sorted(idx.table.items()):
        if len(set(results)) > 1:
            findings.append(("FAIL", "COMPOSITION_NOT_FUNCTIONAL", _pair(a, b)))
        f, g = idx.morphisms.get(a), idx.morphisms.get(b)
        if f is None or g is None or f.target_state_id != g.source_state_id:
            continue
        expected = b if idx.is_identity(f) else a if idx.is_identity(g) else None
        if expected is not None and any(r != expected for r in results):
            findings.append(("FAIL", "UNIT_LAW_VIOLATION", _pair(a, b)))

    plain = idx.non_identities()
    for f in plain:
        for g in plain:
            if (
                f.target_state_id == g.source_state_id
                and f.target_state_id in idx.states
                and (f.morphism_id, g.morphism_id) not in idx.table
            ):
                findings.append(
                    (
                        "UNVERIFIABLE",
                        "COMPOSITION_UNDEFINED",
                        _pair(f.morphism_id, g.morphism_id),
                    )
                )
    for f in plain:
        for g in plain:
            if f.target_state_id != g.source_state_id:
                continue
            for h in plain:
                if g.target_state_id != h.source_state_id:
                    continue
                k = idx.compose(f.morphism_id, g.morphism_id)
                m = idx.compose(g.morphism_id, h.morphism_id)
                if k is None or m is None:
                    continue
                left = idx.compose(k, h.morphism_id)
                right = idx.compose(f.morphism_id, m)
                if left is not None and right is not None and left != right:
                    findings.append(
                        ("FAIL", "ASSOCIATIVITY_VIOLATION", _pair(k, h.morphism_id))
                    )
                    findings.append(
                        ("FAIL", "ASSOCIATIVITY_VIOLATION", _pair(f.morphism_id, m))
                    )

    # v0.4 D-02: both inputs non-identity and the result neither composite
    # nor identity; unit-law terms never count.
    independent = any(
        (f := idx.morphisms.get(c.first)) is not None
        and (g := idx.morphisms.get(c.second)) is not None
        and (r := idx.morphisms.get(c.result)) is not None
        and not idx.is_identity(f)
        and not idx.is_identity(g)
        and r.role not in ("composite", "identity")
        for c in history.compositions
    )
    if not independent:
        mechanical = [
            _pair(c.first, c.second)
            for c in history.compositions
            if (r := idx.morphisms.get(c.result)) is not None
            and r.role == "composite"
            and not any(
                (x := idx.morphisms.get(n)) is not None and idx.is_identity(x)
                for n in (c.first, c.second)
            )
        ]
        for location in mechanical or [
            _loc("field", history.history_id, "compositions")
        ]:
            findings.append(("UNVERIFIABLE", "COMPOSITE_BY_CONSTRUCTION", location))
    return _results("R2", {"history": history.to_dict()}, findings)


# --------------------------------------------------------------------------
# R3  preserved / lost through composition (necessary condition only)
# --------------------------------------------------------------------------


def _carry_of(m: RepresentationMorphism, idx: _Index) -> dict[str, str] | None:
    if m.carry is not None:
        return dict(m.carry)
    if idx.is_identity(m):
        return {p: p for p in m.preserved}
    return None


def check_r3(
    history: RepresentationHistory, vocabulary: PropertyVocabulary | None
) -> list[CheckResult]:
    """Necessary-condition check of preserved/lost composition, not a proof.

    preserved(g.f) must be inside { p in preserved(f) | carry_f(p) in
    preserved(g) }, and lost(g.f) must contain lost(f) and carry_f^-1(lost(g)).
    Passing means no violation was found among the *declared* sets; it does
    not show the declarations are true.
    """
    defects = [
        *history_defects(history),
        *vocabulary_defects(vocabulary, str(getattr(history, "history_id", "?"))),
    ]
    if defects:
        return _defect_results("R3", defects)
    inputs = {
        "history": history.to_dict(),
        "vocabulary": None if vocabulary is None else vocabulary.to_dict(),
    }
    idx = _Index(history)
    findings: list[Finding] = []
    here = _loc("field", history.history_id, "vocabulary_ref")
    if vocabulary is None or vocabulary.ref.value != history.vocabulary_ref.value:
        findings.append(("UNVERIFIABLE", "VOCABULARY_UNRESOLVED", here))
        return _results("R3", inputs, findings)
    # v0.4 D-06: only a sealed (SEAL_OK) vocabulary reaches the ordinary checks
    if vocabulary.ref.seal_status is None:
        findings.append(("UNVERIFIABLE", "SEAL_STATUS_MISSING", here))
        return _results("R3", inputs, findings)
    if vocabulary.ref.seal_status != "SEAL_OK":
        findings.append(("UNVERIFIABLE", "VOCABULARY_UNRESOLVED", here))
        return _results("R3", inputs, findings)

    properties = set(vocabulary.properties)
    names = properties | set(vocabulary.information)
    used: set[str] = set()
    for c in history.compositions:
        used.update((c.first, c.second, c.result))

    for mid in sorted(idx.morphisms):
        m = idx.morphisms[mid]
        mentioned = {*m.preserved, *m.lost, *(m.carry or {}), *(m.carry or {}).values()}
        for field, values in (
            ("preserved", set(m.preserved)),
            ("lost", set(m.lost)),
            ("carry", mentioned - set(m.preserved) - set(m.lost)),
        ):
            if not values <= names:
                findings.append(
                    (
                        "UNVERIFIABLE",
                        "VOCABULARY_UNRESOLVED",
                        _loc("morphism", mid, field),
                    )
                )
        if idx.is_identity(m) and (m.lost or set(m.preserved) != properties):
            findings.append(
                ("FAIL", "IDENTITY_MALFORMED", _loc("morphism", mid, "preserved"))
            )
        if (
            mid in used
            and not idx.is_identity(m)
            and properties - set(m.preserved) - set(m.lost)
        ):
            findings.append(
                (
                    "UNVERIFIABLE",
                    "PROPERTY_UNDECLARED",
                    _loc("morphism", mid, "preserved"),
                )
            )

    for c in history.compositions:
        f, g, h = (idx.morphisms.get(x) for x in (c.first, c.second, c.result))
        if f is None or g is None or h is None:
            continue
        if not (
            f.target_state_id == g.source_state_id
            and h.source_state_id == f.source_state_id
            and h.target_state_id == g.target_state_id
        ):
            continue
        carry = _carry_of(f, idx)
        if carry is None:
            findings.append(
                (
                    "UNVERIFIABLE",
                    "CARRY_MISSING",
                    _loc("morphism", f.morphism_id, "carry"),
                )
            )
            carry = {}
            carry_known = False
        else:
            carry_known = True
        preserved_f, preserved_g = set(f.preserved), set(g.preserved)
        for p in sorted(h.preserved):
            if p not in preserved_f:
                findings.append(
                    (
                        "FAIL",
                        "PRESERVED_NOT_CARRIED",
                        _loc("morphism", h.morphism_id, "preserved"),
                    )
                )
            elif carry_known and p not in carry:
                findings.append(
                    (
                        "UNVERIFIABLE",
                        "CARRY_MISSING",
                        _loc("morphism", f.morphism_id, "carry"),
                    )
                )
            elif carry_known and carry[p] not in preserved_g:
                findings.append(
                    (
                        "FAIL",
                        "PRESERVED_NOT_CARRIED",
                        _loc("morphism", h.morphism_id, "preserved"),
                    )
                )
        lost_h = set(h.lost)
        if not set(f.lost) <= lost_h:
            findings.append(
                ("FAIL", "LOST_NOT_PROPAGATED", _loc("morphism", h.morphism_id, "lost"))
            )
        pulled_back = {q for q, image in carry.items() if image in set(g.lost)}
        if not pulled_back <= lost_h:
            findings.append(
                ("FAIL", "LOST_NOT_PROPAGATED", _loc("morphism", h.morphism_id, "lost"))
            )
    return _results("R3", inputs, findings)


# --------------------------------------------------------------------------
# R4  inverses
# --------------------------------------------------------------------------


def check_r4(history: RepresentationHistory) -> list[CheckResult]:
    """An empty ``lost`` is necessary for invertibility, never sufficient:
    PASS needs both g.f = id_source and f.g = id_target in the table."""
    defects = history_defects(history)
    if defects:
        return _defect_results("R4", defects)
    idx = _Index(history)
    findings: list[Finding] = []
    for mid in sorted(idx.morphisms):
        f = idx.morphisms[mid]
        if f.invertibility.claim != "invertible":
            continue
        if f.lost:
            findings.append(
                ("FAIL", "INVERTIBLE_WITH_LOSS", _loc("morphism", mid, "lost"))
            )
        inverse_id = f.invertibility.inverse_morphism_id
        g = idx.morphisms.get(inverse_id) if inverse_id is not None else None
        if g is None:
            findings.append(
                (
                    "UNVERIFIABLE",
                    "INVERSE_UNRESOLVED",
                    _loc("morphism", mid, "invertibility"),
                )
            )
            continue
        if not (
            g.source_state_id == f.target_state_id
            and g.target_state_id == f.source_state_id
        ):
            findings.append(
                (
                    "FAIL",
                    "INVERSE_ENDPOINT_MISMATCH",
                    _loc("morphism", mid, "invertibility"),
                )
            )
            continue
        missing_identity = False
        for sid in sorted({f.source_state_id, f.target_state_id}):
            if idx.identity_of(sid) is None:
                missing_identity = True
                findings.append(
                    ("UNVERIFIABLE", "IDENTITY_MISSING", _loc("state", sid))
                )
        if missing_identity:
            continue
        sides = (
            ("g_after_f", mid, g.morphism_id, f.source_state_id),
            ("f_after_g", g.morphism_id, mid, f.target_state_id),
        )
        absent: list[str] = []
        for name, first, second, state_id in sides:
            result = idx.compose(first, second)
            if result is None:
                absent.append(name)
            elif result not in idx.identities.get(state_id, []):
                findings.append(("FAIL", "INVERSE_NOT_IDENTITY", _pair(first, second)))
        if len(absent) == len(sides):
            for _, first, second, _state in sides:
                findings.append(
                    ("UNVERIFIABLE", "INVERSE_UNRESOLVED", _pair(first, second))
                )
        else:
            for name, first, second, _state in sides:
                if name in absent:
                    findings.append(
                        (
                            "UNVERIFIABLE",
                            "INVERSE_ONE_SIDED",
                            Location("composition", f"{first}|{second}", name),
                        )
                    )
    return _results("R4", {"history": history.to_dict()}, findings)


# --------------------------------------------------------------------------
# R5  evidence
# --------------------------------------------------------------------------

_CHECKED = ("CHECKED_BY_TOOL", "CHECKED_BY_HUMAN")


def check_r5(history: RepresentationHistory) -> list[CheckResult]:
    """Reads seal_status / validity as given; never judges the evidence."""
    defects = history_defects(history)
    if defects:
        return _defect_results("R5", defects)
    idx = _Index(history)
    findings: list[Finding] = []
    for mid in sorted(idx.morphisms):
        m = idx.morphisms[mid]
        identity = idx.is_identity(m)
        if m.rule_ref is None and not identity:
            findings.append(
                ("UNVERIFIABLE", "RULE_UNREFERENCED", _loc("morphism", mid, "rule_ref"))
            )
        if m.verification != "VERIFIED":
            continue
        if any(ref.validity == "REFUTED" for ref in m.evidence):
            findings.append(
                ("FAIL", "VERIFIED_ON_REFUTED", _loc("morphism", mid, "evidence"))
            )
            continue
        if m.rule_ref is not None and m.rule_ref.seal_status == "SEAL_FAIL":
            findings.append(
                ("FAIL", "RULE_SEAL_FAILED", _loc("morphism", mid, "rule_ref"))
            )
            continue
        if m.rule_ref is not None and m.rule_ref.seal_status is None:
            findings.append(
                (
                    "UNVERIFIABLE",
                    "SEAL_STATUS_MISSING",
                    _loc("morphism", mid, "rule_ref"),
                )
            )
        candidates = [r for r in m.evidence if r.kind in ("hext", "checker_output")]
        if any(
            r.seal_status == "SEAL_OK" and r.validity in _CHECKED for r in candidates
        ):
            continue
        where = _loc("morphism", mid, "evidence")
        if not m.evidence:
            findings.append(("FAIL", "VERIFIED_WITHOUT_EVIDENCE", where))
            continue
        # v0.4 D-19: a broken seal is FAIL even when other evidence is name-only
        # or has no seal result; those are still reported (D-03).
        broken = any(r.seal_status == "SEAL_FAIL" for r in candidates)
        unresolved = False
        if not candidates:
            unresolved = True
            findings.append(("UNVERIFIABLE", "EVIDENCE_NAME_ONLY", where))
        elif any(r.seal_status is None for r in candidates):
            unresolved = True
            findings.append(("UNVERIFIABLE", "SEAL_STATUS_MISSING", where))
        if broken or not unresolved:
            findings.append(("FAIL", "VERIFIED_WITHOUT_EVIDENCE", where))
    return _results("R5", {"history": history.to_dict()}, findings)


# --------------------------------------------------------------------------
# R6  dead ends kept, history is a DAG
# --------------------------------------------------------------------------


def check_r6(
    history: RepresentationHistory,
    previous: RepresentationHistory | None = None,
) -> list[CheckResult]:
    defects = [
        *history_defects(history),
        *([] if previous is None else history_defects(previous)),
    ]
    if defects:
        return _defect_results("R6", defects)
    inputs = {
        "history": history.to_dict(),
        "previous": None if previous is None else previous.to_dict(),
    }
    findings: list[Finding] = []
    here = _loc("field", history.history_id, "prev_history_hash")
    # v0.4 D-01: the DAG is the chain of versions; the graph of states and
    # morphisms may have cycles (inverses, mutual conversions).
    own = {history.compute_hash(), history.history_hash} - {""}
    if history.prev_history_hash in own:
        findings.append(("FAIL", "VERSION_CYCLE", here))
    if history.prev_history_hash is None:
        findings.append(("UNVERIFIABLE", "NO_PRIOR_VERSION", here))
    elif previous is None or previous.compute_hash() != history.prev_history_hash:
        findings.append(("UNVERIFIABLE", "PREV_HISTORY_UNRESOLVED", here))
    else:
        if previous.prev_history_hash in own:
            findings.append(("FAIL", "VERSION_CYCLE", here))
        idx = _Index(history)
        branches = {b.branch_id: b for b in history.abandoned_branches}
        # v0.4 D-20: "remains" means the same id and the same content
        for s in sorted(previous.states, key=lambda s: s.state_id):
            now_state = idx.states.get(s.state_id)
            if now_state is None:
                findings.append(("FAIL", "ELEMENT_DROPPED", _loc("state", s.state_id)))
            elif now_state.to_dict() != s.to_dict():
                findings.append(
                    ("FAIL", "ELEMENT_REWRITTEN", _loc("state", s.state_id))
                )
        for m in sorted(previous.morphisms, key=lambda m: m.morphism_id):
            now_morphism = idx.morphisms.get(m.morphism_id)
            if now_morphism is None:
                findings.append(
                    ("FAIL", "ELEMENT_DROPPED", _loc("morphism", m.morphism_id))
                )
            elif now_morphism.to_dict() != m.to_dict():
                findings.append(
                    ("FAIL", "ELEMENT_REWRITTEN", _loc("morphism", m.morphism_id))
                )
        for b in sorted(previous.abandoned_branches, key=lambda b: b.branch_id):
            now = branches.get(b.branch_id)
            if (
                now is None
                or not set(b.state_ids) <= set(now.state_ids)
                or not set(b.morphism_ids) <= set(now.morphism_ids)
            ):
                findings.append(
                    (
                        "FAIL",
                        "BRANCH_DROPPED",
                        _loc("field", b.branch_id, "abandoned_branches"),
                    )
                )
    return _results("R6", inputs, findings)


# --------------------------------------------------------------------------
# R7  token spans
# --------------------------------------------------------------------------


def check_r7(
    history: RepresentationHistory, eligibility: Mapping[str, bool] | None
) -> list[CheckResult]:
    defects = [
        *history_defects(history),
        *eligibility_defects(eligibility, str(getattr(history, "history_id", "?"))),
    ]
    if defects:
        return _defect_results("R7", defects)
    inputs = {
        "history": history.to_dict(),
        "eligibility": None if eligibility is None else dict(eligibility),
    }
    idx = _Index(history)
    findings: list[Finding] = []
    for sid in sorted(idx.states):
        span = idx.states[sid].span
        if span is None:
            continue
        where = _loc("state", sid, "span")
        verdict = None if eligibility is None else eligibility.get(span.session_id)
        if verdict is None:
            findings.append(("UNVERIFIABLE", "ELIGIBILITY_MISSING", where))
        elif not verdict:
            findings.append(("FAIL", "SPAN_ON_INELIGIBLE", where))
        if span.p_start < 0 or span.p_start > span.p_end:
            findings.append(("FAIL", "SPAN_ORDER", where))
    for mid in sorted(idx.morphisms):
        m = idx.morphisms[mid]
        if m.role not in ("generator", "composite"):
            continue
        a, b = idx.states.get(m.source_state_id), idx.states.get(m.target_state_id)
        if a is None or b is None or a.span is None or b.span is None:
            continue
        if a.span.session_id == b.span.session_id and a.span.p_start > b.span.p_start:
            findings.append(
                ("FAIL", "SPAN_ORDER", _loc("morphism", mid, "source_state_id"))
            )
    return _results("R7", inputs, findings)


# --------------------------------------------------------------------------
# R8  functoriality between two histories
# --------------------------------------------------------------------------


def check_r8(
    source: RepresentationHistory,
    target: RepresentationHistory,
    state_map: Mapping[str, str],
    morphism_map: Mapping[str, str],
) -> list[CheckResult]:
    """Does the map preserve endpoints, identities and composition?

    Identity preservation is checked here directly (the existing `Functor`
    has no such check). If the target has no identity recorded for the image
    state the term cannot be checked: UNVERIFIABLE
    (IDENTITY_PRESERVATION_UNCHECKED).
    """
    defects = [
        *history_defects(source),
        *history_defects(target),
        *map_defects(state_map, str(getattr(source, "history_id", "?")), "state_map"),
        *map_defects(
            morphism_map, str(getattr(source, "history_id", "?")), "morphism_map"
        ),
    ]
    if defects:
        return _defect_results("R8", defects)
    inputs = {
        "source": source.to_dict(),
        "target": target.to_dict(),
        "state_map": dict(state_map),
        "morphism_map": dict(morphism_map),
    }
    src, dst = _Index(source), _Index(target)
    findings: list[Finding] = []
    # v0.4 D-14: entries for elements the source does not have are ignored
    # and reported as warnings; FUNCTOR_PARTIAL means a source element has no image.
    warnings = [
        CheckWarning("MAP_EXTRA_ENTRY", _loc("state", sid, "state_map"))
        for sid in sorted(set(state_map) - set(src.states))
    ] + [
        CheckWarning("MAP_EXTRA_ENTRY", _loc("morphism", mid, "morphism_map"))
        for mid in sorted(set(morphism_map) - set(src.morphisms))
    ]
    for sid in sorted(src.states):
        if sid not in state_map:
            findings.append(("UNVERIFIABLE", "FUNCTOR_PARTIAL", _loc("state", sid)))
        elif state_map[sid] not in dst.states:
            findings.append(("FAIL", "FUNCTOR_IMAGE_UNRESOLVED", _loc("state", sid)))
    for mid in sorted(src.morphisms):
        m = src.morphisms[mid]
        if mid not in morphism_map:
            findings.append(("UNVERIFIABLE", "FUNCTOR_PARTIAL", _loc("morphism", mid)))
            continue
        image = dst.morphisms.get(morphism_map[mid])
        if image is None:
            findings.append(("FAIL", "FUNCTOR_IMAGE_UNRESOLVED", _loc("morphism", mid)))
            continue
        expected = (state_map.get(m.source_state_id), state_map.get(m.target_state_id))
        if None not in expected and expected != (
            image.source_state_id,
            image.target_state_id,
        ):
            findings.append(
                ("FAIL", "FUNCTOR_ENDPOINT_MISMATCH", _loc("morphism", mid))
            )
        elif (
            src.is_identity(m)
            and expected[0] is not None
            and not (dst.is_identity(image) and image.source_state_id == expected[0])
        ):
            if dst.identity_of(expected[0]) is None:
                findings.append(
                    (
                        "UNVERIFIABLE",
                        "IDENTITY_PRESERVATION_UNCHECKED",
                        _loc("morphism", mid),
                    )
                )
            else:
                findings.append(
                    ("FAIL", "IDENTITY_NOT_PRESERVED", _loc("morphism", mid))
                )
    for c in source.compositions:
        sf, sg = src.morphisms.get(c.first), src.morphisms.get(c.second)
        # v0.4 D-23: R8 presumes R1 holds for the source; skip entries that
        # do not chain there (R1 reports them)
        if sf is None or sg is None or sf.target_state_id != sg.source_state_id:
            continue
        images = [morphism_map.get(x) for x in (c.first, c.second, c.result)]
        if any(i is None or i not in dst.morphisms for i in images):
            continue
        ff, fg, fh = (str(i) for i in images)
        if dst.morphisms[ff].target_state_id != dst.morphisms[fg].source_state_id:
            continue
        composed = dst.compose(ff, fg)
        if composed is None:
            findings.append(
                ("UNVERIFIABLE", "COMPOSITION_UNDEFINED", _pair(c.first, c.second))
            )
        elif composed != fh:
            findings.append(
                ("FAIL", "FUNCTOR_COMPOSITION_NOT_PRESERVED", _pair(c.first, c.second))
            )
    return _results("R8", inputs, findings, warnings)


# --------------------------------------------------------------------------
# whole history
# --------------------------------------------------------------------------


def verify_history(
    history: RepresentationHistory,
    *,
    vocabulary: PropertyVocabulary | None = None,
    eligibility: Mapping[str, bool] | None = None,
    previous: RepresentationHistory | None = None,
) -> list[CheckResult]:
    """R1-R7 over one history (R8 needs two histories: call `check_r8`)."""
    return [
        *check_r1(history),
        *check_r2(history),
        *check_r3(history, vocabulary),
        *check_r4(history),
        *check_r5(history),
        *check_r6(history, previous),
        *check_r7(history, eligibility),
    ]


def derive_unit_compositions(
    history: RepresentationHistory,
) -> tuple[Composition, ...]:
    """The unit-law terms the checks derive (v0.4 D-05), written out.

    For each non-identity ``f: A -> B``: ``id_A`` then ``f`` is ``f``, and
    ``f`` then ``id_B`` is ``f``; for each identity, ``id`` then ``id`` is
    ``id``. Terms the recorder already wrote are not repeated. Each derived
    term has ``basis="recomputed"``, ``source="verifier"`` and this checker as
    evidence. A history with type defects yields nothing.
    """
    if history_defects(history):
        return ()
    idx = _Index(history)
    evidence = (
        Ref(
            kind="checker_output",
            value=sha256_hex({"checker": CHECKER.to_dict(), "terms": "unit-law"}),
            name=CHECKER.name,
            version=CHECKER.version,
        ),
    )
    out: list[Composition] = []
    for mid in sorted(idx.morphisms):
        m = idx.morphisms[mid]
        if idx.is_identity(m):
            pairs = [(mid, mid)] if idx.identity_of(m.source_state_id) == mid else []
        else:
            before = idx.identity_of(m.source_state_id)
            after = idx.identity_of(m.target_state_id)
            pairs = [(before, mid), (mid, after)] if before and after else []
            if before and not after:
                pairs = [(before, mid)]
            if after and not before:
                pairs = [(mid, after)]
        for first, second in pairs:
            if first is None or second is None or (first, second) in idx.table:
                continue
            result = mid
            out.append(
                Composition(first, second, result, "recomputed", evidence, "verifier")
            )
    return tuple(out)


def complete_identities(
    history: RepresentationHistory,
    vocabulary: PropertyVocabulary,
    *,
    generator_name: str,
    generator_version: str,
) -> RepresentationHistory:
    """Add a verifier-made identity morphism to every state lacking one.

    Section 2.6: ``source="verifier"`` and the generator's name and version
    in ``evidence``, so they can be told apart from identities the recorder
    wrote. Returns a new sealed version chained to ``history`` by
    ``prev_history_hash``; nothing is rewritten.
    """
    idx = _Index(history)
    added: list[RepresentationMorphism] = []
    for state in sorted(history.states, key=lambda s: s.state_id):
        if idx.identity_of(state.state_id) is not None:
            continue
        reference = Ref(
            kind="checker_output",
            value=sha256_hex(
                {
                    "generator": generator_name,
                    "version": generator_version,
                    "state_id": state.state_id,
                }
            ),
            name=generator_name,
            version=generator_version,
        )
        added.append(
            RepresentationMorphism(
                morphism_id="",
                source_state_id=state.state_id,
                target_state_id=state.state_id,
                role="identity",
                rule_text="identity (added by verifier)",
                preserved=tuple(vocabulary.properties),
                carry={p: p for p in vocabulary.properties},
                evidence=(reference,),
                source="verifier",
            ).with_id()
        )
    return replace(
        history,
        morphisms=(*history.morphisms, *added),
        prev_history_hash=history.compute_hash(),
        history_hash="",
    ).seal()


__all__ = [
    "CHECKER",
    "check_r1",
    "check_r2",
    "check_r3",
    "check_r4",
    "check_r5",
    "check_r6",
    "check_r7",
    "check_r8",
    "complete_identities",
    "derive_unit_compositions",
    "finite_category_of",
    "verify_history",
]
