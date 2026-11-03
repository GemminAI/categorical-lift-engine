"""Builder for `tests/golden/ctp001_v2/`: the 84 fixtures on the Schema Graph.

Steps 2-5 of `Constraint Schema 仕様 v0.4` (the canonical form). The texts, the
declared and evidence statuses and the applicability of the 84 examples are those of
`tests/ctp001_types.py` (the old fixtures, untouched); what changes is the unit:

* the Constraint Schema is written in the canonical notation (v0.4 section 2);
* the obligation is a Graph Path (`ctp001_schema_graph.py`), not a field, so the
  vocabulary, the obligations, the declarations (`preserved`/`lost`) and the Carry
  Evidence are keyed by `path_id`;
* each Carry Evidence entry holds `components`; the state of the path is aggregated
  from them by the v0.4 section 6 rule, nothing else.

A component's state is decided from the break type of the example and the component
it breaks, written out in `CHANGED` below: a property that is lost at a stage loses
all components of its path (`ABSENT_IN_OUTPUT`; for `T.exception` that is `exempt`
and `except_edge`, v0.4 section 7.4) unless `CHANGED` names the component(s) that
changed. The expected values are derived from that and the old R9 table, never from
the output of R9.
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
from ctp001_builder import (
    _KINDS,
    _STAGE_ROWS,
    RULE_REF,
    STAGES,
    STATES,
    _applicability,
    _compliance,
    _obligations,
    _r3,
    _two_axis,
    _worst,
    dump,
)
from ctp001_model import ConstraintType, Example
from ctp001_schema_graph import (
    SCHEMA_GRAPH_VERSION,
    TEMPLATE_BY_FIELD,
    TEMPLATES,
    GraphPath,
    aggregate,
    paths_of,
)
from ctp001_types import TYPES, examples_of

GOLDEN_V2_DIR = Path(__file__).parent / "golden" / "ctp001_v2"

# v0.4 section 2.1 asks for the quantity a threshold compares; the old fixtures'
# schemas had none. One quantity per constraint that has a threshold.
QUANTITY = {
    "c1": "refund amount",
    "c3": "record age",
    "c4": "approving reviewers",
    "c5": "time since last rotation",
}
# Sentences of the new fixtures that differ from the old ones (the old fixtures' texts
# are untouched). Each puts back a clause that the example's break does not drop, so
# that a component the Carry Evidence calls preserved is attested in the stage's text.
# (type, example, text field) -> (the old text, the new text). The expected values
# are built from the statuses, not from the text, so none of them moves.
TEXT_FIXES: dict[tuple[str, str, str], tuple[str, str]] = {
    # the break is c1's condition; c1's modality stays and is stated again at f2
    ("c1", "B7", "f2_decision"): (
        "Refunds above $500 are escalated to a team lead, so I will request"
        " approval from the team lead before issuing the $800 refund.",
        "Refunds over $500 may be issued. Refunds above $500 are escalated to a"
        " team lead, so I will request approval from the team lead before"
        " issuing the $800 refund.",
    ),
    # the break is the number (90 -> 900); the exception stays and is stated at f2
    ("c5", "B3", "f2_decision"): (
        "Passwords must be rotated every 900 days, so the 120-day-old password"
        " needs no rotation. I will leave it.",
        "Passwords must be rotated every 900 days, except for service accounts,"
        " so the 120-day-old password needs no rotation. I will leave it.",
    ),
    # the break is c1's number; c2's modality stays and is stated again at f2
    ("c6", "B3", "f2_decision"): (
        "Refunds over $5,000 may be issued only with manager approval, so the"
        " $800 refund needs none. I will issue it and export the records to"
        " EU-region storage.",
        "Refunds over $5,000 may be issued only with manager approval, so the"
        " $800 refund needs none. Customer records may be exported only to"
        " EU-region storage. I will issue it and export the records to"
        " EU-region storage.",
    ),
    # the break is c1's condition; c2's modality stays at f2 and f3 (c2 is not
    # applicable, the plan exports nothing, but the policy it states is unchanged)
    ("c6", "U0", "f2_decision"): (
        "Refunds over $500 may be issued. I will credit $800 to the customer's"
        " account.",
        "Refunds over $500 may be issued. Customer records may be exported. I"
        " will credit $800 to the customer's account.",
    ),
    ("c6", "U0", "f3_action"): (
        "policy: refunds over $500 may be issued | action: account_credit |"
        " amount: $800 | status: credited",
        "policy: refunds over $500 may be issued; customer records may be"
        " exported | action: account_credit | amount: $800 | status: credited",
    ),
}


def text_of(cid: str, name: str, field: str, text: str) -> str:
    """The text of a new fixture: the old one, or its fix."""
    fix = TEXT_FIXES.get((cid, name, field))
    if fix is None:
        return text
    assert fix[0] == text, (cid, name, field)
    return fix[1]


ABSENT = "ABSENT_IN_OUTPUT"
# (type, example, old property) -> (components that changed, reason). Every other lost
# property is absent from the output of the stage: all its components are L.
CHANGED: dict[tuple[str, str, str], tuple[tuple[str, ...], str]] = {
    ("c1", "B2", "c1.modality"): (("modality",), "MODALITY_CHANGED"),
    ("c1", "B3", "c1.threshold"): (("value",), "VALUE_CHANGED"),
    ("c2", "B2", "c2.modality"): (("modality",), "MODALITY_CHANGED"),
    ("c2", "B3", "c2.scope"): (("scope",), "SCOPE_CHANGED"),
    ("c3", "B2", "c3.modality"): (("modality",), "MODALITY_CHANGED"),
    ("c3", "B3", "c3.threshold"): (("value",), "VALUE_CHANGED"),
    ("c4", "B2", "c4.order"): (("after_edge",), "ORDER_REVERSED"),
    ("c4", "B3", "c4.threshold"): (("value",), "VALUE_CHANGED"),
    ("c5", "B2", "c5.modality"): (("modality",), "MODALITY_CHANGED"),
    ("c5", "B3", "c5.threshold"): (("value",), "VALUE_CHANGED"),
    ("c6", "B2", "c1.modality"): (("modality",), "MODALITY_CHANGED"),
    ("c6", "B3", "c1.threshold"): (("value",), "VALUE_CHANGED"),
}


# v0.6 section 2: the subject of each constraint (a required field, not a component, so
# `schema_graph_version` and every `path_id` stay as they were). C6 holds C1 and C2.
SUBJECTS = {
    "c1": "refunds",
    "c2": "customer records",
    "c3": "records",
    "c4": "production deployment",
    "c5": "passwords",
}


# v0.4 section 10, for the schema's own fields: old kind names to canonical ones
KIND_RENAMES = {"order": "ordering", "exception_rule": "exception"}


# v0.5 section 10: only a C4 schema's threshold quantity is linked to its ordering event
APPLIES_TO_TYPE = "C4"


def canonical_schema(
    schema: dict[str, Any],
    quantity: str | None = None,
    constraint_type: str | None = None,
) -> dict[str, Any]:
    """A Constraint Schema in any old form, in the canonical form (v0.4 sections 2, 10;
    v0.6 section 2.1 for `applies_to`, which is `None` unless given or migrated).

    One rule per row of the section 10 table that concerns a schema: `kind` is
    `constraint_kind`, the kind names `order` and `exception_rule` are `ordering` and
    `exception`, the field `order` is `ordering`, `cmp` is `comparator`, `"must not"`
    is `must_not`, an `exception` string is `{exempt}`, a numeric `value` is a decimal
    string and a threshold without `quantity` gets the one given. A quantity is never
    guessed: a threshold without one and no `quantity` argument is an error. A schema
    that holds both a threshold and an ordering and no `applies_to` gets
    `"ordering.after"` when its `constraint_type` is C4 (v0.5 section 10); any other
    schema is left as it is.
    """
    out = dict(schema)
    if "kind" in out:
        out["constraint_kind"] = KIND_RENAMES.get(out["kind"], out["kind"])
        del out["kind"]
    else:
        out["constraint_kind"] = KIND_RENAMES.get(
            out["constraint_kind"], out["constraint_kind"]
        )
    if "order" in out:
        out["ordering"] = out.pop("order")
    if out["modality"] == "must not":
        out["modality"] = "must_not"
    thr = out["threshold"]
    if thr is not None:
        thr = dict(thr)
        if "cmp" in thr:
            thr["comparator"] = thr.pop("cmp")
        if "quantity" not in thr:
            if quantity is None:
                raise ValueError("a threshold without a quantity needs one given")
            thr["quantity"] = quantity
        thr["value"] = str(thr["value"])
        thr.setdefault("applies_to", None)
        out["threshold"] = {
            k: thr[k] for k in ("quantity", "value", "unit", "comparator", "applies_to")
        }
    thr = out["threshold"]
    if (
        constraint_type == APPLIES_TO_TYPE
        and thr is not None
        and out["ordering"] is not None
        and thr["applies_to"] is None
    ):
        thr["applies_to"] = "ordering.after"
    if isinstance(out["exception"], str):
        out["exception"] = {"exempt": out["exception"]}
    return out


def fixture_schema(
    schema: dict[str, Any], constraint_type: str | None = None
) -> dict[str, Any]:
    """The canonical form of an old fixture's schema (the quantity is `QUANTITY`).

    A schema without a `subject` gets the one of `SUBJECTS` (v0.6 section 10).
    """
    out = canonical_schema(
        schema, QUANTITY.get(schema["constraint_id"]), constraint_type
    )
    out.setdefault("subject", SUBJECTS[schema["constraint_id"]])
    return out


def old_property_path(schema: dict[str, Any], field: str) -> GraphPath:
    """The one path an old `<constraint_id>.<field>` property becomes."""
    template = TEMPLATE_BY_FIELD[KIND_RENAMES.get(field, field)]  # old `c4.order`
    (path,) = [p for p in paths_of(schema) if p.template_id == template.template_id]
    return path


# v0.4 section 10: every old name or type and the canonical form it becomes.
# `in_old_fixtures` says whether the 84 old fixtures (or the 191ba3f ones, for the last
# two) still hold the old form; `source` is the section of the spec that says it.
FORM_MIGRATIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "threshold_cmp",
        "old": "`cmp` (v0.3 section 3)",
        "canonical": "`comparator`",
        "in_old_fixtures": False,
        "source": "v0.4 section 10",
    },
    {
        "id": "ordering_field",
        "old": "field `order` (v0.1 section 1)",
        "canonical": "field `ordering`, template `T.ordering`",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "kind_order",
        "old": "kind `order` (v0.1)",
        "canonical": "kind `ordering`",
        "in_old_fixtures": False,
        "source": "v0.4 section 10",
    },
    {
        "id": "label_c4_order",
        "old": "`path_label` `c4.order` (old property name)",
        "canonical": "`path_label` `c4.ordering`",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "kind_exception_rule",
        "old": "kind `exception_rule` (v0.1)",
        "canonical": "kind `exception`",
        "in_old_fixtures": False,
        "source": "v0.4 section 10",
    },
    {
        "id": "exception_string",
        "old": "field `exception` is a string",
        "canonical": "`{exempt}`",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "value_numeric",
        "old": "`threshold.value` is a number",
        "canonical": "a decimal string",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "threshold_no_quantity",
        "old": "`threshold` without `quantity`",
        "canonical": "`quantity` is added",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "modality_must_not",
        "old": '`modality` `"must not"`',
        "canonical": "`must_not`",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "ordering_components",
        "old": "`T.ordering` components spelled differently in v0.3 and v0.3.1",
        "canonical": "`action`, `after`, `after_edge`",
        "in_old_fixtures": False,
        "source": "v0.4 section 10",
    },
    {
        "id": "exception_components",
        "old": "`T.exception` components `exempt` only (v0.3)",
        "canonical": "`exempt`, `except_edge`",
        "in_old_fixtures": False,
        "source": "v0.4 section 10",
    },
    {
        "id": "property_names",
        "old": "old property names (`c1.condition`, ...)",
        "canonical": "`path_id` (identity), `path_label` (display); table below",
        "in_old_fixtures": True,
        "source": "v0.4 section 10",
    },
    {
        "id": "threshold_applies_to_missing",
        "old": f"constraint type {APPLIES_TO_TYPE}: no link from threshold quantity"
        " to ordering event (v0.4 and before)",
        "canonical": '`threshold.applies_to` is `"ordering.after"`',
        "in_old_fixtures": True,
        "source": "v0.5 section 10",
    },
    {
        "id": "subject_missing",
        "old": "no `subject` in the constraint (v0.5 and before)",
        "canonical": "`subject` is added",
        "in_old_fixtures": True,
        "source": "v0.6 section 10",
    },
    {
        "id": "kind_key",
        "old": "schema key `kind` (old fixtures)",
        "canonical": "`constraint_kind`",
        "in_old_fixtures": True,
        "source": "v0.4 section 2 (not a row of section 10)",
    },
)


def detect_old_forms(
    schema: dict[str, Any], constraint_type: str | None = None
) -> set[str]:
    """The ids of `FORM_MIGRATIONS` whose old form a Constraint Schema still holds."""
    found: set[str] = set()
    if (
        constraint_type == APPLIES_TO_TYPE
        and schema.get("threshold") is not None
        and (schema.get("ordering") or schema.get("order")) is not None
        and schema["threshold"].get("applies_to") is None
    ):
        found.add("threshold_applies_to_missing")
    if "subject" not in schema:
        found.add("subject_missing")
    if "kind" in schema:
        found.add("kind_key")
    kind = schema.get("kind", schema.get("constraint_kind"))
    if kind == "order":
        found.add("kind_order")
    if kind == "exception_rule":
        found.add("kind_exception_rule")
    if "order" in schema:
        found.add("ordering_field")
    if schema.get("modality") == "must not":
        found.add("modality_must_not")
    if isinstance(schema.get("exception"), str):
        found.add("exception_string")
    thr = schema.get("threshold")
    if thr is not None:
        if "cmp" in thr:
            found.add("threshold_cmp")
        if "quantity" not in thr:
            found.add("threshold_no_quantity")
        if not isinstance(thr["value"], str):
            found.add("value_numeric")
    return found


class V2Type:
    """One constraint type on the Schema Graph."""

    def __init__(self, old: ConstraintType) -> None:
        self.old = old
        self.schemas = tuple(fixture_schema(s, old.label) for s in old.schemas)
        by_cid = {s["constraint_id"]: s for s in self.schemas}
        self.old_to_path: dict[str, GraphPath] = {
            p: old_property_path(by_cid[p.split(".")[0]], p.split(".")[1])
            for p in old.props
        }
        paths = sorted((gp for s in self.schemas for gp in paths_of(s)), key=_id)
        self.paths: tuple[GraphPath, ...] = tuple(paths)
        # the type the shared helpers of the old builder take: props are path ids
        self.as_type = ConstraintType(
            old.cid,
            self.schemas,
            tuple(gp.path_id for gp in self.paths),
            old.knowledge,
            old.exclusion_reasons,
        )

    def path_ids(self, props: frozenset[str] | set[str]) -> frozenset[str]:
        return frozenset(self.old_to_path[p].path_id for p in props)


def _id(path: GraphPath) -> str:
    return path.path_id


# ---------------------------------------------------------------- component states


def path_state_of(components: list[dict[str, Any]]) -> str:
    """The state of a path from its components (v0.4 section 6)."""
    return aggregate(c["status"] for c in components)


def component_states(
    t: V2Type, ex: Example, stage_index: int, prop: str
) -> list[dict[str, Any]]:
    """The components of the path of `prop` at a stage (decided from the break type)."""
    path = t.old_to_path[prop]
    lost = prop not in ex.present[stage_index]
    changed, reason = CHANGED.get((t.old.cid, ex.name, prop), ((), ABSENT))
    stage = STAGES[stage_index]
    out: list[dict[str, Any]] = []
    for name in path.components:
        broken = lost and (not changed or name in changed)
        out.append(
            {
                "name": name,
                "status": "L" if broken else "P",
                "evidence_ref": (
                    f"fixture:{t.old.cid}/{ex.name}/{stage}/{path.label}#{name}"
                ),
                "reason": reason if broken else None,
            }
        )
    return out


def carry_evidence(t: V2Type, ex: Example) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for i, stage in enumerate(STAGES):
        entries = []
        for path in t.paths:
            (prop,) = [
                p for p, gp in t.old_to_path.items() if gp.path_id == path.path_id
            ]
            comps = component_states(t, ex, i, prop)
            state = path_state_of(comps)
            entries.append(
                {
                    "property": path.path_id,
                    "path_label": path.label,
                    "path_state": state,
                    "status": "preserved" if state == "P" else "lost",
                    "basis": "evidence",
                    "source": "verifier",
                    "evidence_ref": (
                        f"fixture:{t.old.cid}/{ex.name}/{stage}/{path.label}"
                    ),
                    "components": comps,
                }
            )
        out[stage] = entries
    return out


def evidence_present(
    evidence: dict[str, list[dict[str, Any]]],
) -> tuple[frozenset[str], ...]:
    return tuple(
        frozenset(e["property"] for e in evidence[s] if e["path_state"] == "P")
        for s in STAGES
    )


# ---------------------------------------------------------------- history, vocabulary


def _vocab_ref(t: V2Type) -> Ref:
    return Ref("hext", f"vocab-ctp001v2-{t.old.cid}-v1", seal_status="SEAL_OK")


def vocabulary(t: V2Type) -> PropertyVocabulary:
    return PropertyVocabulary(
        f"ctp001v2-{t.old.cid}-vocab",
        "1",
        f"EXP-RAG-CTP001/{t.old.label}/schema-graph-v{SCHEMA_GRAPH_VERSION}",
        t.as_type.props,
        (),
        _vocab_ref(t),
        tuple((gp.path_id, gp.constraint_id) for gp in t.paths),
    )


def build_history(
    t: V2Type, ex: Example, declared: tuple[frozenset[str], ...]
) -> RepresentationHistory:
    ty = t.as_type
    props = frozenset(ty.props)
    f1, f2, f3 = (
        _morphism(ty, s, a, b, declared[i], text)
        for i, (s, a, b, text) in enumerate(_STAGE_ROWS)
    )
    if ex.claim_preserved_composites:
        up12 = up23 = up123 = props
    else:
        up12 = declared[0] & declared[1]
        up23 = declared[1] & declared[2]
        up123 = declared[0] & declared[1] & declared[2]
    hid = f"ctp001v2-{t.old.cid}-{ex.name}"
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
            preserved=ty.props,
            carry={p: p for p in ty.props},
        )
        for s in STATES
    )
    morphisms = (
        *identities,
        f1,
        f2,
        f3,
        _morphism(ty, "k12", "K", "Y", up12, "f2 after f1, recorded independently"),
        _morphism(ty, "k23", "X", "Z", up23, "f3 after f2, recorded independently"),
        _morphism(ty, "k123", "K", "Z", up123, "f3 after f2 after f1, recorded"),
    )
    compositions = (
        Composition("f1", "f2", "k12", source="human"),
        Composition("k12", "f3", "k123", source="human"),
        Composition("f2", "f3", "k23", source="human"),
        Composition("f1", "k23", "k123", source="human"),
    )
    return RepresentationHistory(
        history_id=hid,
        task_ref=f"EXP-RAG-CTP001/{t.old.label}/schema-graph-v{SCHEMA_GRAPH_VERSION}",
        vocabulary_ref=_vocab_ref(t),
        states=states,
        morphisms=morphisms,
        compositions=compositions,
    ).seal()


def _morphism(
    ty: ConstraintType,
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
        preserved=tuple(p for p in ty.props if p in preserved),
        lost=tuple(p for p in ty.props if p not in preserved),
        carry={p: p for p in ty.props},
        source="human",
    )


# ---------------------------------------------------------------- expected values


def derive_r9(
    t: V2Type,
    ex: Example,
    obligations: list[str],
    declared: tuple[frozenset[str], ...],
    present: tuple[frozenset[str], ...],
    *,
    with_evidence: bool,
) -> dict[str, Any]:
    """The old R9 table at the path level (same rule as the old builder)."""
    findings: list[tuple[str, str, str, str]] = []  # (stage, status, code, path_id)
    for p in obligations:
        for i, stage in enumerate(STAGES):
            declared_lost = p not in declared[i]
            if not with_evidence:
                if declared_lost:
                    findings.append((stage, "FAIL", "OBLIGATION_DECLARED_LOST", p))
                continue
            evidence_lost = p not in present[i]
            if declared_lost and evidence_lost:
                findings.append((stage, "FAIL", "OBLIGATION_LOST_BY_EVIDENCE", p))
            elif evidence_lost:
                findings.append(
                    (stage, "FAIL", "PRESERVED_CONTRADICTED_BY_EVIDENCE", p)
                )
            elif declared_lost:
                findings.append(
                    (stage, "UNVERIFIABLE", "DECLARED_LOST_CONTRADICTED_BY_EVIDENCE", p)
                )
    cid_of = {gp.path_id: gp.constraint_id for gp in t.paths}
    app = _applicability(t.old, ex)
    value = _worst([status for _, status, _, _ in findings])
    first = min((STAGES.index(s) for s, _, _, _ in findings), default=None)
    undetermined = any(app[cid_of[p]] == "undetermined" for *_, p in findings)
    return {
        "value": value,
        "reason_codes": sorted({code for _, _, code, _ in findings}),
        "locations": [] if first is None else [STAGES[first]],
        "annotations": ["APPLICABILITY_UNDETERMINED"] if undetermined else [],
    }


def build_example(t: V2Type, ex: Example) -> dict[str, Any]:
    old = t.old
    declared_old = ex.declared if ex.declared is not None else ex.present
    declared = tuple(t.path_ids(d) for d in declared_old)
    evidence = carry_evidence(t, ex)
    present = evidence_present(evidence)
    app = _applicability(old, ex)
    obligations = sorted(t.old_to_path[p].path_id for p in _obligations(old, ex))
    m1 = derive_r9(t, ex, obligations, declared, present, with_evidence=False)
    m2 = derive_r9(t, ex, obligations, declared, present, with_evidence=True)
    comp = _compliance(ex)
    exclusions = [
        {
            "constraint_id": cid,
            "reason": old.exclusion_reasons[cid],
            "applicability_basis": "fixture",
        }
        for cid in old.constraint_ids
        if app[cid] == "not_applicable"
    ]
    return {
        "id": f"{old.cid}_{ex.name}",
        "constraint_type": old.label,
        "example": ex.name,
        "note": ex.note,
        "schema_graph_version": SCHEMA_GRAPH_VERSION,
        "history": build_history(t, ex, declared).to_dict(),
        "vocabulary": vocabulary(t).to_dict(),
        "path_definitions": {gp.path_id: gp.definition() for gp in t.paths},
        "chain": list(STAGES),
        "constraint_schema": t.schemas[0] if len(t.schemas) == 1 else list(t.schemas),
        "applicability": app,
        "applicability_basis": "fixture",
        "obligations": obligations,
        "obligation_exclusions": exclusions,
        "carry_evidence": evidence,
        "situation": ex.situation,
        "texts": {
            "knowledge": old.knowledge,
            "f1_context": text_of(old.cid, ex.name, "f1_context", ex.context),
            "f2_decision": text_of(old.cid, ex.name, "f2_decision", ex.decision),
            "f3_action": text_of(old.cid, ex.name, "f3_action", ex.action),
        },
        "expected": {
            "r1": {"value": "PASS"},
            "r2": {"value": "PASS"},
            "r3": _r3(ex),
            "r9": {"m1": m1, "m2": m2},
            "compliance": comp,
            "two_axis": _two_axis(old, ex, m2, comp),
        },
    }


V2_TYPES: tuple[V2Type, ...] = tuple(V2Type(t) for t in TYPES)


def build_all() -> dict[str, dict[str, Any]]:
    return {
        f"{t.old.cid}_{ex.name}.json": build_example(t, ex)
        for t in V2_TYPES
        for ex in examples_of(t.old.cid)
    }


# ---------------------------------------------------------------- step 5: the map


def old_properties() -> list[str]:
    return sorted({p for t in V2_TYPES for p in t.old.props})


def distinct_paths() -> list[GraphPath]:
    seen: dict[str, GraphPath] = {}
    for t in V2_TYPES:
        for gp in t.paths:
            seen.setdefault(gp.path_id, gp)
    return sorted(seen.values(), key=lambda g: (g.constraint_id, g.template_id))


def migration_map() -> dict[str, Any]:
    """Old property -> new path, and where each new path comes from."""
    by_old: dict[str, GraphPath] = {}
    for t in V2_TYPES:
        by_old.update(t.old_to_path)
    mappings = []
    for prop in old_properties():
        gp = by_old[prop]
        template = next(x for x in TEMPLATES if x.template_id == gp.template_id)
        mappings.append(
            {
                "old_property": prop,
                "paths": [
                    {
                        "path_id": gp.path_id,
                        "path_label": gp.label,
                        "template_id": gp.template_id,
                        "granularity": template.granularity,
                    }
                ],
            }
        )
    new_paths = [
        {
            "path_id": gp.path_id,
            "path_label": gp.label,
            "template_id": gp.template_id,
            "origin": {
                "kind": "migrated",
                "old_properties": sorted(
                    p for p, g in by_old.items() if g.path_id == gp.path_id
                ),
            },
        }
        for gp in distinct_paths()
    ]
    return {
        "schema_graph_version": SCHEMA_GRAPH_VERSION,
        "spec": "Constraint Schema 仕様 v0.6 section 10",
        "form_migrations": [dict(f) for f in FORM_MIGRATIONS],
        "granularity_changed_templates": [
            t.template_id for t in TEMPLATES if t.granularity == "changed"
        ],
        "mappings": mappings,
        "new_paths": new_paths,
    }


def migration_md() -> str:
    m = migration_map()
    rows = "\n".join(
        f"| `{x['old_property']}` | `{x['paths'][0]['path_label']}` "
        f"| `{x['paths'][0]['template_id']}` | {x['paths'][0]['granularity']} |"
        for x in m["mappings"]
    )
    new_rows = "\n".join(
        f"| `{n['path_label']}` | `{n['path_id'][:16]}...` "
        f"| {', '.join(f'`{p}`' for p in n['origin']['old_properties'])} |"
        for n in m["new_paths"]
    )
    comps = "\n".join(
        f"| `{t.template_id}` | {', '.join(f'`{c}`' for c in t.components)} "
        f"| {t.granularity} |"
        for t in TEMPLATES
    )
    forms = "\n".join(
        f"| {f['old']} | {f['canonical']} | {'yes' if f['in_old_fixtures'] else 'no'} "
        f"| {f['source']} |"
        for f in m["form_migrations"]
    )
    return f"""# Migration: old forms to the canonical form (Constraint Schema v0.6)

Section 10 of `Constraint Schema 仕様 v0.6`, which keeps the rows of v0.4 and v0.5
section 10 and adds its own; the Source column says which version each row is from.
The same tables in a machine-readable
form are in `migration_map.json`; both are written by `tests/ctp001_v2_builder.py` and
`tests/test_ctp001_v2_fixtures.py` checks that they are what the builder writes, that
every old form the 84 old fixtures hold is a row below, and that nothing is missing in
either direction.

Old fixtures: `tests/golden/ctp001/` (the obligation is a property
`<constraint_id>.<field>`). New fixtures: this directory (the obligation is a Graph
Path, identified by `path_id`; `path_label` is for display only).
`schema_graph_version` is `"{m["schema_graph_version"]}"`.

## Old names and types to the canonical form

"In the old fixtures" says whether the 84 old fixtures still hold the old form.

| Old form | Canonical form | In the old fixtures | Source |
|---|---|---|---|
{forms}

## Templates and their required components

| Template | Components | Granularity against the old property |
|---|---|---|
{comps}

"same": the old property and the new path are the same unit, so the result of R9 on
the old property and on the path must agree (step 6, not done here). "changed": the
old property is one unit, the path is a structure of several components
(`T.threshold`: quantity, value, unit, comparator; `T.ordering`: action, after and the
direction of the AFTER edge), so an example may differ (step 6, not done here).
`T.exception` gains `except_edge` in v0.4; its unit is still one property, so it stays
"same".

## Old property to new path

| Old property | New path (label) | Template | Granularity |
|---|---|---|---|
{rows}

Every old property maps to exactly one path ({len(m["mappings"])} properties).

## New paths and their origin

| Path (label) | `path_id` | Comes from |
|---|---|---|
{new_rows}

Every new path comes from an old property; no path was added as new
({len(m["new_paths"])} paths). C6 holds C1 and C2, so it reuses their paths (the
`path_id` depends on the constraint id, the template id and the version only).
"""


# ---------------------------------------------------------------- writing


def write_all(directory: Path = GOLDEN_V2_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, doc in build_all().items():
        (directory / name).write_text(dump(doc), encoding="utf-8")
    (directory / "migration_map.json").write_text(
        json.dumps(migration_map(), indent=2, sort_keys=True, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (directory / "MIGRATION.md").write_text(migration_md(), encoding="utf-8")


if __name__ == "__main__":
    write_all()
