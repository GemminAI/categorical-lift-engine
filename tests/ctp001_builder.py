"""Builder for the EXP-RAG-CTP001 fixtures: 14 examples of each type C1-C6.

The design is `EXP-RAG-CTP001 実験設計書 v0.3` section 5 (examples, expected values),
v0.2 section 4 (Constraint Schema, Carry Evidence) and v0.3 section 6 (G3: Carry
Evidence lives outside the history; G5: the composition table is written as
independent records). `write_all` regenerates `tests/golden/ctp001/c<n>_*.json`;
`tests/test_ctp001_fixtures.py` checks that the committed files equal `build_all()`.

The data (the six types and their examples) is in `ctp001_types.py`; nothing here
knows a particular type.

Convention used for every status below (the design leaves it open): the status of a
property at stage `s` is whether the property is still present in the *output* of
`s`, measured against the knowledge-side Constraint Schema, so once a property is
lost the later stages stay `lost`. "Honest" declarations follow that rule; the
examples that lie (B6) or over-declare (X0) override it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cle.representation import (
    Composition,
    PropertyVocabulary,
    Ref,
    RepresentationHistory,
    RepresentationMorphism,
    RepresentationState,
)
from ctp001_model import ConstraintType, Example
from ctp001_types import TYPES, examples_of

GOLDEN_DIR = Path(__file__).parent / "golden" / "ctp001"
STAGES = ("f1", "f2", "f3")
STATES = ("K", "X", "Y", "Z")  # knowledge, context, decision, action
RULE_REF = Ref("hext", "rule-ctp001-v1", seal_status="SEAL_OK")

_RANK = {"PASS": 0, "NOT_APPLICABLE": 0, "UNVERIFIABLE": 1, "FAIL": 2}
_KINDS = ("knowledge", "context", "decision", "action")
_STAGE_ROWS = (
    ("f1", "K", "X", "retrieval and chunking"),
    ("f2", "X", "Y", "decision"),
    ("f3", "Y", "Z", "execution"),
)


def _worst(values: list[str]) -> str:
    return max(values, key=lambda v: _RANK[v]) if values else "PASS"


def _vocab_ref(t: ConstraintType) -> Ref:
    return Ref("hext", f"vocab-ctp001-{t.cid}-v1", seal_status="SEAL_OK")


def _declared(ex: Example) -> tuple[frozenset[str], ...]:
    return ex.declared if ex.declared is not None else ex.present


def _applicability(t: ConstraintType, ex: Example) -> dict[str, str]:
    if ex.applicabilities is not None:
        return dict(ex.applicabilities)
    return {cid: ex.context_applicability for cid in t.constraint_ids}


def _obligations(t: ConstraintType, ex: Example) -> list[str]:
    """Properties of the constraints that are not `not_applicable` (v0.3 section 2)."""
    app = _applicability(t, ex)
    return [p for p in t.props if app[p.split(".")[0]] != "not_applicable"]


def _morphism(
    t: ConstraintType,
    mid: str,
    src: str,
    dst: str,
    preserved: frozenset[str],
    text: str,
) -> RepresentationMorphism:
    return RepresentationMorphism(
        mid,
        src,
        dst,
        role="generator",
        rule_ref=RULE_REF,
        rule_text=text,
        preserved=tuple(p for p in t.props if p in preserved),
        lost=tuple(p for p in t.props if p not in preserved),
        carry={p: p for p in t.props},
        source="human",
    )


def build_history(t: ConstraintType, ex: Example) -> RepresentationHistory:
    props = frozenset(t.props)
    d = _declared(ex)
    f1, f2, f3 = (
        _morphism(t, s, a, b, d[i], text)
        for i, (s, a, b, text) in enumerate(_STAGE_ROWS)
    )
    if ex.claim_preserved_composites:
        up12 = up23 = up123 = props
    else:
        up12, up23, up123 = d[0] & d[1], d[1] & d[2], d[0] & d[1] & d[2]
    hid = f"ctp001-{t.cid}-{ex.name}"
    states = tuple(
        RepresentationState(s, hid, kind, source="human")
        for s, kind in zip(STATES, _KINDS, strict=True)
    )
    identities = tuple(
        RepresentationMorphism(
            f"i{s}",
            s,
            s,
            role="identity",
            preserved=t.props,
            carry={p: p for p in t.props},
        )
        for s in STATES
    )
    morphisms = (
        *identities,
        f1,
        f2,
        f3,
        _morphism(t, "k12", "K", "Y", up12, "f2 after f1, recorded independently"),
        _morphism(t, "k23", "X", "Z", up23, "f3 after f2, recorded independently"),
        _morphism(t, "k123", "K", "Z", up123, "f3 after f2 after f1, recorded"),
    )
    compositions = (
        Composition("f1", "f2", "k12", source="human"),
        Composition("k12", "f3", "k123", source="human"),
        Composition("f2", "f3", "k23", source="human"),
        Composition("f1", "k23", "k123", source="human"),
    )
    return RepresentationHistory(
        history_id=hid,
        task_ref=f"EXP-RAG-CTP001/{t.label}",
        vocabulary_ref=_vocab_ref(t),
        states=states,
        morphisms=morphisms,
        compositions=compositions,
    ).seal()


def vocabulary(t: ConstraintType) -> PropertyVocabulary:
    return PropertyVocabulary(
        f"ctp001-{t.cid}-vocab",
        "1",
        f"EXP-RAG-CTP001/{t.label}",
        t.props,
        (),
        _vocab_ref(t),
    )


def carry_evidence(t: ConstraintType, ex: Example) -> dict[str, list[dict[str, str]]]:
    return {
        stage: [
            {
                "property": p,
                "status": "preserved" if p in ex.present[i] else "lost",
                "basis": "evidence",
                "source": "verifier",
                "evidence_ref": f"fixture:{t.cid}/{ex.name}/{stage}/{p}",
            }
            for p in t.props
        ]
        for i, stage in enumerate(STAGES)
    }


def derive_r9(t: ConstraintType, ex: Example, *, with_evidence: bool) -> dict[str, Any]:
    """The v0.3 section 3 table applied to the fixture's declared/evidence statuses."""
    findings: list[tuple[str, str, str]] = []  # (stage, status, code)
    for p in _obligations(t, ex):
        for i, stage in enumerate(STAGES):
            declared_lost = p not in _declared(ex)[i]
            if not with_evidence:
                if declared_lost:
                    findings.append((stage, "FAIL", "OBLIGATION_DECLARED_LOST"))
                continue
            evidence_lost = p not in ex.present[i]
            if declared_lost and evidence_lost:
                findings.append((stage, "FAIL", "OBLIGATION_LOST_BY_EVIDENCE"))
            elif evidence_lost:
                findings.append((stage, "FAIL", "PRESERVED_CONTRADICTED_BY_EVIDENCE"))
            elif declared_lost:
                findings.append(
                    (stage, "UNVERIFIABLE", "DECLARED_LOST_CONTRADICTED_BY_EVIDENCE")
                )
    value = _worst([status for _, status, _ in findings])
    first = min((STAGES.index(s) for s, _, _ in findings), default=None)
    undetermined = "undetermined" in _applicability(t, ex).values()
    return {
        "value": value,
        "reason_codes": sorted({code for _, _, code in findings}),
        "locations": [] if first is None else [STAGES[first]],
        "annotations": (
            ["APPLICABILITY_UNDETERMINED"] if value != "PASS" and undetermined else []
        ),
    }


def _r3(ex: Example) -> dict[str, Any]:
    if ex.claim_preserved_composites:
        return {
            "value": "FAIL",
            "reason_codes": ["LOST_NOT_PROPAGATED", "PRESERVED_NOT_CARRIED"],
        }
    return {"value": "PASS", "reason_codes": []}


def _compliance(ex: Example) -> dict[str, str]:
    l1, l2, l3, f3 = ex.compliance
    judged = [v for v in (l2, l3, f3) if v != "NOT_APPLICABLE"]
    overall = _worst(judged) if judged else "NOT_APPLICABLE"
    return {"L1": l1, "L2": l2, "L3": l3, "f3": f3, "overall": overall}


def _two_axis(
    t: ConstraintType, ex: Example, r9_m2: dict[str, Any], comp: dict[str, str]
) -> dict[str, Any]:
    if not _obligations(t, ex):
        return {
            "retention": "NOT_APPLICABLE",
            "compliance": "NOT_APPLICABLE",
            "class": None,
            "undetermined_axes": [],
        }
    retention = {"PASS": "CARRIED", "FAIL": "LOST", "UNVERIFIABLE": "UNDETERMINED"}[
        r9_m2["value"]
    ]
    adherence = {
        "PASS": "COMPLIED",
        "FAIL": "VIOLATED",
        "UNVERIFIABLE": "UNDETERMINED",
    }[comp["overall"]]
    undetermined = [
        axis
        for axis, v in (("retention", retention), ("compliance", adherence))
        if v == "UNDETERMINED"
    ]
    cls = "UNDETERMINED" if undetermined else f"{retention}_{adherence}"
    return {
        "retention": retention,
        "compliance": adherence,
        "class": cls,
        "undetermined_axes": undetermined,
    }


def build_example(t: ConstraintType, ex: Example) -> dict[str, Any]:
    history = build_history(t, ex)
    m1 = derive_r9(t, ex, with_evidence=False)
    m2 = derive_r9(t, ex, with_evidence=True)
    comp = _compliance(ex)
    app = _applicability(t, ex)
    exclusions = [
        {
            "constraint_id": cid,
            "reason": t.exclusion_reasons[cid],
            "applicability_basis": "fixture",
        }
        for cid in t.constraint_ids
        if app[cid] == "not_applicable"
    ]
    return {
        "id": f"{t.cid}_{ex.name}",
        "constraint_type": t.label,
        "example": ex.name,
        "note": ex.note,
        "history": history.to_dict(),
        "vocabulary": vocabulary(t).to_dict(),
        "chain": list(STAGES),
        "constraint_schema": t.schemas[0] if len(t.schemas) == 1 else list(t.schemas),
        "applicability": app,
        "applicability_basis": "fixture",
        "obligations": _obligations(t, ex),
        "obligation_exclusions": exclusions,
        "carry_evidence": carry_evidence(t, ex),
        "situation": ex.situation,
        "texts": {
            "knowledge": t.knowledge,
            "f1_context": ex.context,
            "f2_decision": ex.decision,
            "f3_action": ex.action,
        },
        "expected": {
            "r1": {"value": "PASS"},
            "r2": {"value": "PASS"},
            "r3": _r3(ex),
            "r9": {"m1": m1, "m2": m2},
            "compliance": comp,
            "two_axis": _two_axis(t, ex, m2, comp),
        },
    }


def build_all() -> dict[str, dict[str, Any]]:
    return {
        f"{t.cid}_{ex.name}.json": build_example(t, ex)
        for t in TYPES
        for ex in examples_of(t.cid)
    }


def dump(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_all(directory: Path = GOLDEN_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, doc in build_all().items():
        (directory / name).write_text(dump(doc), encoding="utf-8")


if __name__ == "__main__":
    write_all()
