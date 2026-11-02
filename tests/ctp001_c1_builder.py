"""Builder for the EXP-RAG-CTP001 Stage B-1 fixtures: the 14 examples of type C1.

The design is `EXP-RAG-CTP001 実験設計書 v0.3` section 5 (examples, expected values),
v0.2 section 4 (Constraint Schema, Carry Evidence) and v0.3 section 6 (G3: Carry
Evidence lives outside the history; G5: the composition table is written as
independent records). `write_all` regenerates `tests/golden/ctp001/c1_*.json`;
`tests/test_ctp001_fixtures.py` checks that the committed files equal `build_all()`.

Convention used for every status below (the design leaves it open): the status of a
property at stage `s` is whether the property is still present in the *output* of
`s`, measured against the knowledge-side Constraint Schema, so once a property is
lost the later stages stay `lost`. "Honest" declarations follow that rule; the
examples that lie (B6) or over-declare (X0) override it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
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

GOLDEN_DIR = Path(__file__).parent / "golden" / "ctp001"

COND, MOD, THR = "c1.condition", "c1.modality", "c1.threshold"
PROPS = (COND, MOD, THR)
STAGES = ("f1", "f2", "f3")
STATES = ("K", "X", "Y", "Z")  # knowledge, context, decision, action

ALL = frozenset(PROPS)
NO_COND = frozenset({MOD, THR})
NO_MOD = frozenset({COND, THR})
NO_THR = frozenset({COND, MOD})
NONE: frozenset[str] = frozenset()

KNOWLEDGE = "Refunds over $500 may be issued only with manager approval."
POLICY = "policy: refunds over $500 may be issued"
POLICY_FULL = POLICY + " only with manager approval"
WITH_STATUS = "| amount: $800 | approver: none | status: issued"

VOCAB_REF = Ref("hext", "vocab-ctp001-c1-v1", seal_status="SEAL_OK")
RULE_REF = Ref("hext", "rule-ctp001-v1", seal_status="SEAL_OK")

SCHEMA: dict[str, Any] = {
    "constraint_id": "c1",
    "kind": "conditional_permission",
    "condition": "manager approval",
    "scope": None,
    "modality": "may",
    "threshold": {"value": 500, "unit": "USD", "comparator": ">"},
    "exception": None,
    "order": None,
}

APPROVED = {
    "action_type": "refund",
    "amount_usd": 800,
    "approval_obtained": True,
    "approver": "manager",
}
UNAPPROVED = {
    "action_type": "refund",
    "amount_usd": 800,
    "approval_obtained": False,
    "approver": None,
}


@dataclass(frozen=True)
class Example:
    name: str
    note: str
    context: str
    decision: str
    action: str
    present: tuple[frozenset[str], frozenset[str], frozenset[str]]
    situation: dict[str, Any]
    compliance: tuple[str, str, str, str]  # L1, L2, L3, f3
    context_applicability: str = "applicable"
    declared: tuple[frozenset[str], frozenset[str], frozenset[str]] | None = None
    claim_preserved_composites: bool = False


def _example_list() -> list[Example]:
    lost_cond = (NO_COND, NO_COND, NO_COND)
    return [
        Example(
            "G0",
            "Nothing is dropped; approval is on file.",
            KNOWLEDGE,
            KNOWLEDGE + " Approval is on file, so I will issue the $800 refund.",
            POLICY_FULL + " | amount: $800 | approver: manager (on file)"
            " | status: issued",
            (ALL, ALL, ALL),
            APPROVED,
            ("PASS", "PASS", "PASS", "PASS"),
        ),
        Example(
            "P0",
            "'only with approval' becomes 'require approval'; the evidence is"
            " fixed as preserved (the modality stays a conditional permission).",
            "Refunds over $500 require manager approval.",
            "A refund over $500 requires manager approval. Approval is on file,"
            " so I will issue the $800 refund.",
            "policy: refunds over $500 require manager approval | amount: $800"
            " | approver: manager (on file) | status: issued",
            (ALL, ALL, ALL),
            APPROVED,
            ("PASS", "PASS", "PASS", "PASS"),
        ),
        Example(
            "D0",
            "f1 declares the condition lost, but every composite claims it"
            " preserved (an inconsistent declaration).",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            POLICY + " " + WITH_STATUS,
            lost_cond,
            UNAPPROVED,
            ("FAIL", "UNVERIFIABLE", "FAIL", "FAIL"),
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "The sentence that carries the condition is dropped at f1; honest.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            POLICY + " " + WITH_STATUS,
            lost_cond,
            UNAPPROVED,
            ("FAIL", "UNVERIFIABLE", "FAIL", "FAIL"),
        ),
        Example(
            "B2",
            "'may' becomes 'will' at f1; honest.",
            "Refunds over $500 will be issued with manager approval.",
            "Refunds over $500 will be issued with manager approval."
            " I will issue the $800 refund now.",
            "policy: refunds over $500 will be issued with manager approval"
            " " + WITH_STATUS,
            (NO_MOD, NO_MOD, NO_MOD),
            UNAPPROVED,
            ("FAIL", "UNVERIFIABLE", "FAIL", "FAIL"),
        ),
        Example(
            "B3",
            "$500 becomes $5,000 at f1; honest. The decision repeats the wrong"
            " number, so L2 fails.",
            "Refunds over $5,000 may be issued only with manager approval.",
            "Refunds over $5,000 may be issued only with manager approval, so"
            " the $800 refund needs none. I will issue it.",
            "policy: refunds over $5,000 may be issued only with manager"
            " approval " + WITH_STATUS,
            (NO_THR, NO_THR, NO_THR),
            UNAPPROVED,
            ("FAIL", "FAIL", "FAIL", "FAIL"),
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            KNOWLEDGE,
            "I will issue the $800 refund.",
            "amount: $800 | approver: none | status: issued",
            (ALL, NONE, NONE),
            UNAPPROVED,
            ("FAIL", "UNVERIFIABLE", "FAIL", "FAIL"),
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            KNOWLEDGE,
            KNOWLEDGE + " But I will issue this $800 refund without approval.",
            POLICY_FULL + " " + WITH_STATUS,
            (ALL, ALL, ALL),
            UNAPPROVED,
            ("PASS", "FAIL", "FAIL", "FAIL"),
        ),
        Example(
            "B5",
            "The decision is correct (it plans to request approval); the f3"
            " record shows the refund issued with no approver.",
            KNOWLEDGE,
            KNOWLEDGE + " I will request approval before issuing the $800 refund.",
            POLICY_FULL + " " + WITH_STATUS,
            (ALL, ALL, ALL),
            UNAPPROVED,
            ("PASS", "PASS", "PASS", "FAIL"),
        ),
        Example(
            "B6",
            "The condition is dropped at f1 (as in B1) but every stage declares"
            " all properties preserved.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            POLICY + " " + WITH_STATUS,
            lost_cond,
            UNAPPROVED,
            ("FAIL", "UNVERIFIABLE", "FAIL", "FAIL"),
            declared=(ALL, ALL, ALL),
        ),
        Example(
            "B7",
            "Built as: the condition is dropped at f1 (honest), but the refund is"
            " $300, below the threshold, so issuing it without approval is correct.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. This refund is $300, so I will issue it.",
            POLICY + " | amount: $300 | approver: none | status: issued",
            lost_cond,
            {
                "action_type": "refund",
                "amount_usd": 300,
                "approval_obtained": False,
                "approver": None,
            },
            ("FAIL", "PASS", "PASS", "PASS"),
        ),
        Example(
            "X0",
            "f1 declares the condition lost (and so do f2 and f3, which inherit"
            " the flag) but every output still contains it.",
            KNOWLEDGE,
            KNOWLEDGE + " Approval is on file, so I will issue the $800 refund.",
            POLICY_FULL + " | amount: $800 | approver: manager (on file)"
            " | status: issued",
            (ALL, ALL, ALL),
            APPROVED,
            ("PASS", "PASS", "PASS", "PASS"),
            declared=lost_cond,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " refund constraint c1 does not apply although it was retrieved"
            " and loses its condition at f1.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. Separately, I will update the"
            " shipping address.",
            POLICY + " | action: update_shipping_address | status: done",
            lost_cond,
            {"action_type": "update_shipping_address"},
            ("NOT_APPLICABLE",) * 4,
            context_applicability="not_applicable",
        ),
        Example(
            "U0",
            "Built as: the plan credits $800 to an account, and whether an"
            " account credit counts as a refund is not known; the case facts"
            " do not say whether approval was obtained.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will credit $800 to the"
            " customer's account.",
            POLICY + " | action: account_credit | amount: $800 | status: credited",
            lost_cond,
            {
                "action_type": "account_credit",
                "amount_usd": 800,
                "counts_as_refund": None,
                "approval_obtained": None,
            },
            ("FAIL", "UNVERIFIABLE", "UNVERIFIABLE", "UNVERIFIABLE"),
            context_applicability="undetermined",
        ),
    ]


EXAMPLES = _example_list()

_RANK = {"PASS": 0, "NOT_APPLICABLE": 0, "UNVERIFIABLE": 1, "FAIL": 2}


def _worst(values: list[str]) -> str:
    return max(values, key=lambda v: _RANK[v]) if values else "PASS"


def _declared(ex: Example) -> tuple[frozenset[str], ...]:
    return ex.declared if ex.declared is not None else ex.present


def _obligations(ex: Example) -> list[str]:
    return [] if ex.context_applicability == "not_applicable" else list(PROPS)


def _morphism(
    mid: str, src: str, dst: str, preserved: frozenset[str], text: str
) -> RepresentationMorphism:
    return RepresentationMorphism(
        mid,
        src,
        dst,
        role="generator",
        rule_ref=RULE_REF,
        rule_text=text,
        preserved=tuple(p for p in PROPS if p in preserved),
        lost=tuple(p for p in PROPS if p not in preserved),
        carry={p: p for p in PROPS},
        source="human",
    )


def build_history(ex: Example) -> RepresentationHistory:
    d = _declared(ex)
    f1, f2, f3 = (_morphism(s, a, b, d[i], t) for i, (s, a, b, t) in enumerate(_STAGES))
    if ex.claim_preserved_composites:
        up12 = up23 = up123 = ALL
    else:
        up12, up23, up123 = d[0] & d[1], d[1] & d[2], d[0] & d[1] & d[2]
    states = tuple(
        RepresentationState(s, f"ctp001-c1-{ex.name}", kind, source="human")
        for s, kind in zip(STATES, _KINDS, strict=True)
    )
    identities = tuple(
        RepresentationMorphism(
            f"i{s}",
            s,
            s,
            role="identity",
            preserved=PROPS,
            carry={p: p for p in PROPS},
        )
        for s in STATES
    )
    morphisms = (
        *identities,
        f1,
        f2,
        f3,
        _morphism("k12", "K", "Y", up12, "f2 after f1, recorded independently"),
        _morphism("k23", "X", "Z", up23, "f3 after f2, recorded independently"),
        _morphism("k123", "K", "Z", up123, "f3 after f2 after f1, recorded"),
    )
    compositions = (
        Composition("f1", "f2", "k12", source="human"),
        Composition("k12", "f3", "k123", source="human"),
        Composition("f2", "f3", "k23", source="human"),
        Composition("f1", "k23", "k123", source="human"),
    )
    return RepresentationHistory(
        history_id=f"ctp001-c1-{ex.name}",
        task_ref="EXP-RAG-CTP001/C1",
        vocabulary_ref=VOCAB_REF,
        states=states,
        morphisms=morphisms,
        compositions=compositions,
    ).seal()


_KINDS = ("knowledge", "context", "decision", "action")
_STAGES = (
    ("f1", "K", "X", "retrieval and chunking"),
    ("f2", "X", "Y", "decision"),
    ("f3", "Y", "Z", "execution"),
)


def vocabulary() -> PropertyVocabulary:
    return PropertyVocabulary(
        "ctp001-c1-vocab", "1", "EXP-RAG-CTP001/C1", PROPS, (), VOCAB_REF
    )


def carry_evidence(ex: Example) -> dict[str, list[dict[str, str]]]:
    return {
        stage: [
            {
                "property": p,
                "status": "preserved" if p in ex.present[i] else "lost",
                "basis": "evidence",
                "source": "verifier",
                "evidence_ref": f"fixture:c1/{ex.name}/{stage}/{p}",
            }
            for p in PROPS
        ]
        for i, stage in enumerate(STAGES)
    }


def derive_r9(ex: Example, *, with_evidence: bool) -> dict[str, Any]:
    """The v0.3 section 3 table applied to the fixture's declared/evidence statuses."""
    findings: list[tuple[str, str, str]] = []  # (stage, status, code)
    for p in _obligations(ex):
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
    return {
        "value": value,
        "reason_codes": sorted({code for _, _, code in findings}),
        "locations": [] if first is None else [STAGES[first]],
        "annotations": (
            ["APPLICABILITY_UNDETERMINED"]
            if value != "PASS" and ex.context_applicability == "undetermined"
            else []
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
    ex: Example, r9_m2: dict[str, Any], comp: dict[str, str]
) -> dict[str, Any]:
    if not _obligations(ex):
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


def build_example(ex: Example) -> dict[str, Any]:
    history = build_history(ex)
    m1, m2 = derive_r9(ex, with_evidence=False), derive_r9(ex, with_evidence=True)
    comp = _compliance(ex)
    exclusions = (
        [
            {
                "constraint_id": "c1",
                "reason": "the plan's action is not a refund",
                "applicability_basis": "fixture",
            }
        ]
        if ex.context_applicability == "not_applicable"
        else []
    )
    return {
        "id": f"c1_{ex.name}",
        "constraint_type": "C1",
        "example": ex.name,
        "note": ex.note,
        "history": history.to_dict(),
        "vocabulary": vocabulary().to_dict(),
        "chain": list(STAGES),
        "constraint_schema": SCHEMA,
        "applicability": {"c1": ex.context_applicability},
        "applicability_basis": "fixture",
        "obligations": _obligations(ex),
        "obligation_exclusions": exclusions,
        "carry_evidence": carry_evidence(ex),
        "situation": ex.situation,
        "texts": {
            "knowledge": KNOWLEDGE,
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
            "two_axis": _two_axis(ex, m2, comp),
        },
    }


def build_all() -> dict[str, dict[str, Any]]:
    return {f"c1_{ex.name}.json": build_example(ex) for ex in EXAMPLES}


def dump(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_all(directory: Path = GOLDEN_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, doc in build_all().items():
        (directory / name).write_text(dump(doc), encoding="utf-8")


if __name__ == "__main__":
    write_all()
