"""EXP-RAG-CTP001 Schema Graph (`Constraint Schema 仕様 v0.4` sections 4-6).

The templates, the `path_id` and the aggregation rule of the path state, including the
boundary vectors V1-V8 of section 6.1 (`golden/ctp001_v2/aggregation_vectors.json`).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ctp001_schema_graph import (
    EDGE_COMPONENTS,
    SCHEMA_GRAPH_VERSION,
    TEMPLATE_BY_FIELD,
    TEMPLATE_BY_ID,
    TEMPLATES,
    aggregate,
    aggregate_path,
    path_id,
    path_label,
    paths_of,
)
from ctp001_v2_builder import path_state_of

ROOT = Path(__file__).resolve().parent.parent
SCHEMA: dict[str, Any] = {
    "constraint_id": "c5",
    "constraint_kind": "exception",
    "condition": None,
    "scope": None,
    "modality": "must",
    "threshold": {
        "quantity": "time since last rotation",
        "value": "90",
        "unit": "days",
        "comparator": ">=",
    },
    "exception": {"exempt": "service accounts"},
    "ordering": None,
}


def test_the_six_templates_and_their_components() -> None:
    assert SCHEMA_GRAPH_VERSION == "1"
    assert {t.template_id: t.components for t in TEMPLATES} == {
        "T.condition": ("condition",),
        "T.scope": ("scope",),
        "T.modality": ("modality",),
        "T.threshold": ("quantity", "value", "unit", "comparator"),
        "T.exception": ("exempt", "except_edge"),
        "T.ordering": ("action", "after", "after_edge"),
    }
    assert set(TEMPLATE_BY_ID) == {t.template_id for t in TEMPLATES}
    assert set(TEMPLATE_BY_FIELD) == {
        "condition",
        "scope",
        "modality",
        "threshold",
        "exception",
        "ordering",
    }
    assert {t.granularity for t in TEMPLATES} == {"same", "changed"}


def test_path_id_is_the_sha256_of_the_sorted_compact_json() -> None:
    material = (
        '{"constraint_id":"c5","schema_graph_version":"1","template_id":"T.threshold"}'
    )
    expected = "path:" + hashlib.sha256(material.encode("utf-8")).hexdigest()
    assert path_id("c5", "T.threshold") == expected
    assert path_id("c5", "T.threshold", "1") == expected


def test_path_id_depends_on_its_three_strings_only() -> None:
    base = path_id("c5", "T.threshold", "1")
    assert path_id("c5", "T.threshold", "2") != base  # Path Versioning
    assert path_id("c4", "T.threshold", "1") != base
    assert path_id("c5", "T.modality", "1") != base


def test_path_id_does_not_depend_on_display_names_or_ordering() -> None:
    reordered = dict(reversed(list(SCHEMA.items())))
    changed_text = {
        **SCHEMA,
        "exception": {"exempt": "robot accounts"},
        "threshold": {**SCHEMA["threshold"], "quantity": "age of the password"},
    }
    ids = [p.path_id for p in paths_of(SCHEMA)]
    assert {p.path_id for p in paths_of(reordered)} == set(ids)
    assert {p.path_id for p in paths_of(changed_text)} == set(ids)
    one = paths_of(SCHEMA)[0]
    assert replace(one, label="anything else").path_id == one.path_id
    assert path_label("c5", "T.threshold") == "c5.threshold"
    assert all(p.label not in p.path_id for p in paths_of(SCHEMA))


def test_paths_of_makes_one_path_per_non_null_field_with_its_components() -> None:
    paths = paths_of(SCHEMA)
    assert [p.template_id for p in paths] == [
        "T.modality",
        "T.threshold",
        "T.exception",
    ]
    assert [len(p.components) for p in paths] == [1, 4, 2]
    assert {p.schema_graph_version for p in paths} == {"1"}
    assert paths[1].definition() == {
        "path_label": "c5.threshold",
        "constraint_id": "c5",
        "template_id": "T.threshold",
        "constraint_value": SCHEMA["threshold"],
        "schema_graph_version": "1",
    }


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        (["P"], "P"),
        (["P", "P", "P", "P"], "P"),
        (["P", "U", "P"], "U"),
        (["L", "P"], "L"),
        (["U", "L"], "L"),  # L over U
        (["U", "U"], "U"),
        (["P", "P", "L", "U"], "L"),
    ],
)
def test_aggregation_is_l_over_u_over_p(states: list[str], expected: str) -> None:
    assert aggregate(states) == expected
    assert aggregate(reversed(states)) == expected


def test_aggregation_refuses_unknown_and_empty() -> None:
    with pytest.raises(ValueError, match="unknown"):
        aggregate(["P", "X"])
    with pytest.raises(ValueError, match="at least one"):
        aggregate([])


SCRIPT = """
import json
from ctp001_v2_builder import V2_TYPES
print(json.dumps({t.old.cid: [p.path_id for p in t.paths] for t in V2_TYPES}))
"""


def _fresh(hash_seed: str) -> str:
    env = {
        **os.environ,
        "PYTHONHASHSEED": hash_seed,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")]),
    }
    return subprocess.run(
        [sys.executable, "-c", SCRIPT],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_path_ids_are_identical_in_two_fresh_processes() -> None:
    assert _fresh("1") == _fresh("2")


# --- v0.4 section 6.1: the boundary vectors ------------------------------------

VECTORS: dict[str, Any] = json.loads(
    (ROOT / "tests" / "golden" / "ctp001_v2" / "aggregation_vectors.json").read_text(
        encoding="utf-8"
    )
)
V_IDS = [v["id"] for v in VECTORS["vectors"]]


def _entries(states: dict[str, str]) -> list[dict[str, Any]]:
    return [{"name": n, "status": s} for n, s in states.items()]


def test_the_vectors_are_v1_to_v8_over_the_four_threshold_components() -> None:
    assert [f"V{i}" for i in range(1, 9)] == V_IDS
    assert (
        tuple(VECTORS["threshold_components"])
        == TEMPLATE_BY_ID["T.threshold"].components
    )
    for v in VECTORS["vectors"]:
        assert v["template_id"] == "T.threshold"
        assert list(v["components"]) == list(VECTORS["threshold_components"])


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=V_IDS)
def test_every_aggregation_function_agrees_with_the_vector(
    vector: dict[str, Any],
) -> None:
    states = vector["components"]
    expected = vector["path_state"]
    assert aggregate(states.values()) == expected
    assert aggregate_path(vector["template_id"], states) == expected
    assert path_state_of(_entries(states)) == expected  # the builder's own function
    # the order of the components does not matter
    assert (
        aggregate_path(vector["template_id"], dict(reversed(states.items())))
        == expected
    )


def test_v4_l_takes_priority_over_u() -> None:
    """V4: value L, unit U -> L, not U (section 6, 1)."""
    v = next(v for v in VECTORS["vectors"] if v["id"] == "V4")
    assert v["components"]["value"] == "L"
    assert v["components"]["unit"] == "U"
    assert aggregate_path("T.threshold", v["components"]) == "L"


def test_v7_l_takes_priority_over_u() -> None:
    """V7: quantity U, comparator L -> L, not U (section 6, 1)."""
    v = next(v for v in VECTORS["vectors"] if v["id"] == "V7")
    assert v["components"]["quantity"] == "U"
    assert v["components"]["comparator"] == "L"
    assert aggregate_path("T.threshold", v["components"]) == "L"


def test_a_template_with_one_component_is_its_component() -> None:
    group = VECTORS["single_component_templates"]
    assert {len(TEMPLATE_BY_ID[t].components) for t in group["templates"]} == {1}
    for template_id in group["templates"]:
        (name,) = TEMPLATE_BY_ID[template_id].components
        for case in group["cases"]:
            assert (
                aggregate_path(template_id, {name: case["component"]})
                == (case["path_state"])
            )
            assert case["path_state"] == case["component"]


_MULTI = VECTORS["multi_component_templates"]


@pytest.mark.parametrize("case", _MULTI, ids=[str(i) for i in range(len(_MULTI))])
def test_t_ordering_and_t_exception_follow_the_same_rule(case: dict[str, Any]) -> None:
    assert aggregate_path(case["template_id"], case["components"]) == case["path_state"]
    assert path_state_of(_entries(case["components"])) == case["path_state"]


def test_the_three_template_sizes_of_section_6_1_are_covered() -> None:
    sizes = {len(TEMPLATE_BY_ID[c["template_id"]].components) for c in _MULTI}
    sizes |= {len(TEMPLATE_BY_ID["T.threshold"].components)}
    sizes |= {1}
    assert sizes == {1, 2, 3, 4}
    assert {c["template_id"] for c in _MULTI} == {"T.ordering", "T.exception"}


def test_edge_preservation_a_surviving_leaf_does_not_make_the_path_p() -> None:
    """Section 6, 2: every edge component is a component, so its loss is the path's."""
    assert {"comparator", "except_edge", "after_edge"} == EDGE_COMPONENTS
    for template in TEMPLATES:
        for edge in EDGE_COMPONENTS & set(template.components):
            states = {c: "P" for c in template.components}
            assert aggregate_path(template.template_id, states) == "P"
            assert aggregate_path(template.template_id, {**states, edge: "L"}) == "L"
            assert aggregate_path(template.template_id, {**states, edge: "U"}) == "U"
    assert {e for t in TEMPLATES for e in EDGE_COMPONENTS & set(t.components)} == (
        EDGE_COMPONENTS
    )


def test_aggregate_path_refuses_a_reduced_or_invented_component_set() -> None:
    with pytest.raises(ValueError, match="components"):
        aggregate_path("T.threshold", {"value": "P", "unit": "P"})
    with pytest.raises(ValueError, match="components"):
        aggregate_path("T.exception", {"exempt": "P"})  # no leaf-only exception
    with pytest.raises(ValueError, match="components"):
        aggregate_path("T.condition", {"condition": "P", "extra": "P"})
