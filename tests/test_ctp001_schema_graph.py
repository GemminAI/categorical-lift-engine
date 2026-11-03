"""EXP-RAG-CTP001 Schema Graph (`Constraint Schema 仕様 v0.3` sections 3-4, v0.3.1).

The templates, the `path_id` and the aggregation rule of the path state.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ctp001_schema_graph import (
    SCHEMA_GRAPH_VERSION,
    TEMPLATE_BY_FIELD,
    TEMPLATE_BY_ID,
    TEMPLATES,
    aggregate,
    path_id,
    path_label,
    paths_of,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA: dict[str, Any] = {
    "constraint_id": "c5",
    "kind": "exception",
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
    "order": None,
}


def test_the_six_templates_and_their_components() -> None:
    assert SCHEMA_GRAPH_VERSION == "1"
    assert {t.template_id: t.components for t in TEMPLATES} == {
        "T.condition": ("condition",),
        "T.scope": ("scope",),
        "T.modality": ("modality",),
        "T.threshold": ("quantity", "value", "unit", "comparator"),
        "T.exception": ("exempt",),
        "T.ordering": ("action", "after", "after_edge"),
    }
    assert set(TEMPLATE_BY_ID) == {t.template_id for t in TEMPLATES}
    assert set(TEMPLATE_BY_FIELD) == {
        "condition",
        "scope",
        "modality",
        "threshold",
        "exception",
        "order",
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
    assert [len(p.components) for p in paths] == [1, 4, 1]
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
