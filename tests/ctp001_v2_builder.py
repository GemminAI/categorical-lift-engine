"""Builder for `tests/golden/ctp001_v2/`: the 84 fixtures on the Schema Graph.

Steps 2-5 of `Constraint Schema 仕様 v0.3` section 6. The texts, the declared and
evidence statuses and the applicability of the 84 examples are those of
`tests/ctp001_types.py` (the old fixtures, untouched); what changes is the unit:

* the Constraint Schema is written in the v0.2 notation (section 2);
* the obligation is a Graph Path (`ctp001_schema_graph.py`), not a field, so the
  vocabulary, the obligations, the declarations (`preserved`/`lost`) and the Carry
  Evidence are keyed by `path_id`;
* each Carry Evidence entry holds `components` (v0.3 section 5); the state of the
  path is aggregated from them by the v0.3.1 section 1 rule, nothing else.

A component's state is decided from the break type of the example and the component
it breaks, written out in `CHANGED` below: a property that is lost at a stage loses
all components of its path (`ABSENT_IN_OUTPUT`) unless `CHANGED` names the
component(s) that changed. The expected values are derived from that and the v0.3
section 3 table, never from the output of R9.
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

# Step 2: v0.1 section 1.1 asks for the quantity a threshold compares; the fixtures'
# schemas had none. One quantity per constraint that has a threshold.
QUANTITY = {
    "c1": "refund amount",
    "c3": "record age",
    "c4": "approving reviewers",
    "c5": "time since last rotation",
}
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


def v02_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The Constraint Schema in the v0.2 notation (and v0.1 section 1's value forms).

    `threshold` gains `quantity`, its `value` is a decimal string (v0.1 section 1.1,
    so that JCS holds no number); `modality` is `must_not`; `exception` is
    `{exempt}` (v0.1 section 1). The kind names `ordering` and `exception` are
    already the fixtures' names.
    """
    out = dict(schema)
    if out["modality"] == "must not":
        out["modality"] = "must_not"
    if out["threshold"] is not None:
        thr = out["threshold"]
        out["threshold"] = {
            "quantity": QUANTITY[out["constraint_id"]],
            "value": str(thr["value"]),
            "unit": thr["unit"],
            "comparator": thr["comparator"],
        }
    if out["exception"] is not None:
        out["exception"] = {"exempt": out["exception"]}
    return out


def old_property_path(schema: dict[str, Any], field: str) -> GraphPath:
    """The one path an old `<constraint_id>.<field>` property becomes."""
    template = TEMPLATE_BY_FIELD[field]
    (path,) = [p for p in paths_of(schema) if p.template_id == template.template_id]
    return path


class V2Type:
    """One constraint type on the Schema Graph."""

    def __init__(self, old: ConstraintType) -> None:
        self.old = old
        self.schemas = tuple(v02_schema(s) for s in old.schemas)
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
            state = aggregate(c["status"] for c in comps)
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
    """The v0.3 section 3 table at the path level (same rule as the old builder)."""
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
    return f"""# Migration: old properties to Schema Graph paths

`Constraint Schema 仕様 v0.3` section 6, step 5 (frozen by v0.3.1). The same table in a
machine-readable form is `migration_map.json`; both are written by
`tests/ctp001_v2_builder.py` and `tests/test_ctp001_v2_fixtures.py` checks that they are
what the builder writes and that nothing is missing in either direction.

Old fixtures: `tests/golden/ctp001/` (the obligation is a property
`<constraint_id>.<field>`). New fixtures: this directory (the obligation is a Graph
Path, identified by `path_id`; `path_label` is for display only).
`schema_graph_version` is `"{m["schema_graph_version"]}"`.

## Templates and their required components

| Template | Components | Granularity against the old property |
|---|---|---|
{comps}

"same": the old property and the new path are the same unit, so the result of R9 on
the old property and on the path must agree (step 6). "changed": the old property is
one unit, the path is a structure of several components (`T.threshold`: quantity,
value, unit, comparator; `T.ordering`: action, after and the direction of the AFTER
edge), so an example may differ (step 6, not done here).

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
