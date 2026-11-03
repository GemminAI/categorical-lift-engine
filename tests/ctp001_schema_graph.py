"""Canonical Schema Graph of EXP-RAG-CTP001 (`Constraint Schema 仕様 v0.3` section 3).

The six path templates, the names of the components each one requires, and the
`path_id` of a Graph Path. This is data and two small pure functions; it knows no
fixture. `schema_graph_version` "1" is the version frozen by v0.3.1 section 4.

* A path is identified by `path_id` (v0.3 section 4, 1):
  `"path:" + sha256(JCS({constraint_id, template_id, schema_graph_version}))`. The
  label (`c5.threshold`) is for display and is never an input of the id.
* A component is one required part of the template. The set of components is fixed by
  the template and is never reduced to fit a stage's output (v0.3.1 section 1).
* The state of a path is aggregated from its components, L over U over P
  (v0.3.1 section 1); no judgement is involved.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cle.representation import sha256_hex

SCHEMA_GRAPH_VERSION = "1"
STATES = ("P", "L", "U")


@dataclass(frozen=True)
class Template:
    template_id: str
    schema_field: str  # the field of the Constraint Schema that instantiates it
    edges: tuple[str, ...]  # the relations of v0.3 section 3, for the record
    components: tuple[str, ...]  # required parts, in a fixed order
    # against the old property of the same field (v0.3 section 6, 6): is the
    # unit of the obligation the same, or does it change
    granularity: str


TEMPLATES: tuple[Template, ...] = (
    Template(
        "T.condition",
        "condition",
        ("REQUIRES_CONDITION",),
        ("condition",),
        "same",
    ),
    Template("T.scope", "scope", ("RESTRICTED_TO",), ("scope",), "same"),
    Template("T.modality", "modality", ("HAS_MODALITY",), ("modality",), "same"),
    Template(
        "T.threshold",
        "threshold",
        ("HAS_THRESHOLD", "ON_QUANTITY", "VALUE", "UNIT", "CMP"),
        ("quantity", "value", "unit", "comparator"),
        "changed",
    ),
    Template("T.exception", "exception", ("EXCEPT",), ("exempt",), "same"),
    Template(
        "T.ordering",
        "order",
        ("AFTER",),
        ("action", "after", "after_edge"),
        "changed",
    ),
)
TEMPLATE_BY_ID: dict[str, Template] = {t.template_id: t for t in TEMPLATES}
TEMPLATE_BY_FIELD: dict[str, Template] = {t.schema_field: t for t in TEMPLATES}


def path_id(
    constraint_id: str,
    template_id: str,
    schema_graph_version: str = SCHEMA_GRAPH_VERSION,
) -> str:
    """v0.3 section 4, 1. The material is three strings; the keys are sorted by JCS."""
    return "path:" + sha256_hex(
        {
            "constraint_id": constraint_id,
            "template_id": template_id,
            "schema_graph_version": schema_graph_version,
        }
    )


def path_label(constraint_id: str, template_id: str) -> str:
    """Display only (v0.3.1 section 3): `c5.threshold`."""
    return f"{constraint_id}.{template_id.removeprefix('T.')}"


@dataclass(frozen=True)
class GraphPath:
    path_id: str
    label: str
    constraint_id: str
    template_id: str
    constraint_value: Any  # the constraint's value for the template's field
    schema_graph_version: str

    @property
    def components(self) -> tuple[str, ...]:
        return TEMPLATE_BY_ID[self.template_id].components

    def definition(self) -> dict[str, Any]:
        """The R9 vocabulary entry (v0.3 section 4, 5; v0.3.1 section 3)."""
        return {
            "path_label": self.label,
            "constraint_id": self.constraint_id,
            "template_id": self.template_id,
            "constraint_value": self.constraint_value,
            "schema_graph_version": self.schema_graph_version,
        }


def paths_of(schema: dict[str, Any]) -> tuple[GraphPath, ...]:
    """The paths of one Constraint Schema: one per non-null field, template order."""
    cid = schema["constraint_id"]
    return tuple(
        GraphPath(
            path_id(cid, t.template_id),
            path_label(cid, t.template_id),
            cid,
            t.template_id,
            schema[t.schema_field],
            SCHEMA_GRAPH_VERSION,
        )
        for t in TEMPLATES
        if schema[t.schema_field] is not None
    )


def aggregate(states: Iterable[str]) -> str:
    """v0.3.1 section 1: L if any component is L, else U if any is U, else P."""
    seen = set(states)
    if not seen <= set(STATES):
        raise ValueError(f"unknown component state(s): {sorted(seen - set(STATES))}")
    if not seen:
        raise ValueError("a path has at least one component")
    if "L" in seen:
        return "L"
    return "U" if "U" in seen else "P"
