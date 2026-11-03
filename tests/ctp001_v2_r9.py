"""R9 on the fixtures, old (properties) and new (Graph Paths), for the step 6 tests.

`Constraint Schema 仕様 v0.4` section 9: R9 receives the state of the evidence per path
and per stage (`preserved`/`lost`, with `evidence_ref`) and the declarations of the
stages. It does not receive the path's meaning, the components or the natural
language, so the Carry Evidence is cut down to the five fields R9 reads before it is
passed, and the `components`, `path_state` and `path_label` stay behind.
"""

from __future__ import annotations

from typing import Any

from cle.representation import (
    CheckResult,
    PropertyVocabulary,
    RepresentationHistory,
    check_obligation_transport,
)

R9_EVIDENCE_FIELDS = ("property", "status", "basis", "source", "evidence_ref")
MODES = ("M1", "M2")


def r9_evidence(doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The Carry Evidence as R9 receives it: no components, no label, no state."""
    return {
        stage: [{k: e[k] for k in R9_EVIDENCE_FIELDS} for e in entries]
        for stage, entries in doc["carry_evidence"].items()
    }


def r9_applicability(doc: dict[str, Any]) -> dict[str, str]:
    """The applicability R9 reads, keyed by what R9 reads it by.

    R9 takes the constraint id of an obligation to be the part of its name before the
    first dot. An old property (`c1.modality`) has one; a `path_id` has none, so its
    whole name is the key and each path gets the applicability of its constraint.
    """
    paths = doc.get("path_definitions")
    if paths is None:
        return dict(doc["applicability"])
    return {pid: doc["applicability"][d["constraint_id"]] for pid, d in paths.items()}


def run_r9(doc: dict[str, Any], mode: str) -> list[CheckResult]:
    return check_obligation_transport(
        RepresentationHistory.from_dict(doc["history"]),
        PropertyVocabulary.from_dict(doc["vocabulary"]),
        doc["chain"],
        doc["obligations"],
        r9_applicability(doc),
        r9_evidence(doc),
        mode,
    )


def summary(results: list[CheckResult], chain: list[str]) -> dict[str, Any]:
    """The value, the sorted reason codes, the first location and the notes."""
    rank = {"PASS": 0, "UNVERIFIABLE": 1, "FAIL": 2}
    stages = {loc.id for r in results for loc in r.locations}
    return {
        "value": max((r.status for r in results), key=lambda s: rank[s]),
        "reason_codes": sorted({r.reason_code for r in results if r.reason_code}),
        "locations": [s for s in chain if s in stages],
        "annotations": sorted({w.reason_code for r in results for w in r.warnings}),
    }


Finding = tuple[str, str, str, str, tuple[tuple[str, str | None], ...]]


def findings(results: list[CheckResult]) -> dict[str, set[Finding]]:
    """R9's findings and warnings per obligation: (stage, kind, status, code, detail).

    `kind` is "finding" or "warning"; a warning has no status of its own.
    """
    out: dict[str, set[Finding]] = {}
    for r in results:
        detail = tuple(sorted((r.detail or {}).items()))
        for loc in r.locations:
            assert loc.field is not None
            out.setdefault(loc.field, set()).add(
                (loc.id, "finding", r.status, str(r.reason_code), detail)
            )
        for w in r.warnings:
            assert w.location.field is not None
            out.setdefault(w.location.field, set()).add(
                (w.location.id, "warning", "-", w.reason_code, ())
            )
    return out
