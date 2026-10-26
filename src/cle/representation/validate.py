"""Type checks on the records a verifier receives (v0.4 D-12).

The record classes check enum values when they are built, but Python does not
check field types. A verifier must not raise on a defective input, so each
rule first asks these functions whether the values have the annotated types;
a defect is reported as FAIL ``INPUT_TYPE_INVALID`` with its location.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cle.representation.model import (
    AbandonedBranch,
    Composition,
    Invertibility,
    Location,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
    Span,
)


def _strs(value: Any) -> bool:
    return isinstance(value, (tuple, list)) and all(isinstance(x, str) for x in value)


def _int(value: Any) -> bool:
    return type(value) is int


def _ref(value: Any) -> bool:
    return isinstance(value, Ref) and isinstance(value.value, str)


def _refs(value: Any) -> bool:
    return isinstance(value, (tuple, list)) and all(_ref(r) for r in value)


def _hid(history: Any) -> str:
    hid = getattr(history, "history_id", "?")
    return hid if isinstance(hid, str) else "?"


def history_defects(history: Any) -> list[Location]:
    if not isinstance(history, RepresentationHistory):
        return [Location("field", "?", "history")]
    where = _hid(history)
    out: list[Location] = []

    def bad(field: str) -> None:
        out.append(Location("field", where, field))

    if not isinstance(history.history_id, str):
        bad("history_id")
    if not isinstance(history.task_ref, str):
        bad("task_ref")
    if not _ref(history.vocabulary_ref):
        bad("vocabulary_ref")
    if history.prev_history_hash is not None and not isinstance(
        history.prev_history_hash, str
    ):
        bad("prev_history_hash")
    for state in history.states:
        sid = getattr(state, "state_id", "?")
        sid = sid if isinstance(sid, str) else "?"
        ok = isinstance(state, RepresentationState) and all(
            isinstance(x, str)
            for x in (state.state_id, state.history_id, state.kind, state.description)
        )
        span = getattr(state, "span", None)
        if span is not None and not (
            isinstance(span, Span)
            and isinstance(span.session_id, str)
            and _int(span.p_start)
            and _int(span.p_end)
        ):
            ok = False
        if not ok:
            out.append(Location("state", sid))
    for m in history.morphisms:
        mid = getattr(m, "morphism_id", "?")
        mid = mid if isinstance(mid, str) else "?"
        ok = isinstance(m, RepresentationMorphism) and all(
            isinstance(x, str)
            for x in (m.morphism_id, m.source_state_id, m.target_state_id, m.rule_text)
        )
        if isinstance(m, RepresentationMorphism):
            carry = m.carry
            ok = (
                ok
                and _strs(m.preserved)
                and _strs(m.lost)
                and (
                    carry is None
                    or (
                        isinstance(carry, Mapping)
                        and all(
                            isinstance(k, str) and isinstance(v, str)
                            for k, v in carry.items()
                        )
                    )
                )
                and _refs(m.evidence)
                and (m.rule_ref is None or _ref(m.rule_ref))
                and isinstance(m.invertibility, Invertibility)
                and (
                    m.invertibility.inverse_morphism_id is None
                    or isinstance(m.invertibility.inverse_morphism_id, str)
                )
            )
        if not ok:
            out.append(Location("morphism", mid))
    for c in history.compositions:
        ok = (
            isinstance(c, Composition)
            and all(isinstance(x, str) for x in (c.first, c.second, c.result))
            and _refs(c.evidence)
        )
        if not ok:
            first = getattr(c, "first", "?")
            second = getattr(c, "second", "?")
            out.append(
                Location(
                    "composition",
                    f"{first}|{second}"
                    if isinstance(first, str) and isinstance(second, str)
                    else "?",
                )
            )
    for b in history.abandoned_branches:
        ok = (
            isinstance(b, AbandonedBranch)
            and isinstance(b.branch_id, str)
            and _strs(b.state_ids)
            and _strs(b.morphism_ids)
        )
        if not ok:
            bid = getattr(b, "branch_id", "?")
            out.append(
                Location(
                    "field", bid if isinstance(bid, str) else "?", "abandoned_branches"
                )
            )
    return out


def vocabulary_defects(vocabulary: Any, where: str) -> list[Location]:
    if vocabulary is None:
        return []
    ok = (
        isinstance(vocabulary, PropertyVocabulary)
        and _strs(vocabulary.properties)
        and _strs(vocabulary.information)
        and _ref(vocabulary.ref)
    )
    return [] if ok else [Location("field", where, "vocabulary")]


def eligibility_defects(eligibility: Any, where: str) -> list[Location]:
    if eligibility is None:
        return []
    ok = isinstance(eligibility, Mapping) and all(
        isinstance(k, str) and isinstance(v, bool) for k, v in eligibility.items()
    )
    return [] if ok else [Location("field", where, "eligibility")]


def map_defects(value: Any, where: str, field: str) -> list[Location]:
    ok = isinstance(value, Mapping) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    )
    return [] if ok else [Location("field", where, field)]
