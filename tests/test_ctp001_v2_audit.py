"""The sentences of the new fixtures hold the evidence of every preserved component.

`ctp001_v2_audit.py` is a plain string audit with the phrase tables of
`Constraint Schema 仕様 v0.4` section 8; it is not the Constraint Verifier. What the
v0.4 tables settle ("first" and "afterwards" in an ordering, an imperative sentence,
the `conditional_permission` equivalents) is not a defect of a sentence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ctp001_v2_audit import attested, audit, clauses, read_comparator, read_modality
from ctp001_v2_builder import GOLDEN_V2_DIR, TEXT_FIXES

FILES = sorted(GOLDEN_V2_DIR.glob("c[1-6]_*.json"))


def _load(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return doc


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_preserved_component_is_attested_in_its_stage_text(path: Path) -> None:
    assert audit(_load(path)) == []


def test_the_audit_found_exactly_the_sentences_that_were_fixed() -> None:
    """With the old sentences put back, the audit names the six cells and no other."""
    found = set()
    for path in FILES:
        doc = _load(path)
        key = (path.stem[:2], path.stem[3:])
        for (cid, name, field), (old, new) in TEXT_FIXES.items():
            if (cid, name) == key:
                assert doc["texts"][field] == new
                doc["texts"][field] = old
        for stage, label, comp, _ in audit(doc):
            found.add((path.stem, stage, label, comp))
    assert found == {
        ("c1_B7", "f2", "c1.modality", "modality"),
        ("c5_B3", "f2", "c5.exception", "exempt"),
        ("c5_B3", "f2", "c5.exception", "except_edge"),
        ("c6_B3", "f2", "c2.modality", "modality"),
        ("c6_U0", "f2", "c2.modality", "modality"),
        ("c6_U0", "f3", "c2.modality", "modality"),
    }


# For each fixed example: the component the break targets (lost at f1) and the one
# that was put back (preserved at every stage, so not the target).
TARGET_AND_RESTORED = {
    "c1_B7": (("c1.condition", "condition"), ("c1.modality", "modality")),
    "c5_B3": (("c5.threshold", "value"), ("c5.exception", "exempt")),
    "c6_B3": (("c1.threshold", "value"), ("c2.modality", "modality")),
    "c6_U0": (("c1.condition", "condition"), ("c2.modality", "modality")),
}


@pytest.mark.parametrize("name", sorted(TARGET_AND_RESTORED))
def test_a_restored_clause_is_never_the_component_the_break_targets(name: str) -> None:
    doc = _load(GOLDEN_V2_DIR / f"{name}.json")
    (t_label, t_comp), (r_label, r_comp) = TARGET_AND_RESTORED[name]

    def status(stage: str, label: str, comp: str) -> str:
        entry = next(
            e for e in doc["carry_evidence"][stage] if e["path_label"] == label
        )
        return str(next(c["status"] for c in entry["components"] if c["name"] == comp))

    for stage in ("f1", "f2", "f3"):
        assert status(stage, t_label, t_comp) == "L"
        assert status(stage, r_label, r_comp) == "P"
    assert {k[2] for k in TEXT_FIXES if f"{k[0]}_{k[1]}" == name} <= {
        "f2_decision",
        "f3_action",
    }


def test_the_old_fixtures_sentences_are_not_touched() -> None:
    from ctp001_builder import GOLDEN_DIR

    for path in FILES:
        old = _load(GOLDEN_DIR / path.name)["texts"]
        fixed = {f for (c, n, f) in TEXT_FIXES if f"{c}_{n}.json" == path.name}
        assert {k for k in old if old[k] != _load(path)["texts"][k]} == fixed


# --- what the v0.4 tables settle is not a defect -----------------------------------


@pytest.mark.parametrize(
    ("clause", "expected"),
    [
        ("rotate passwords every 90 days", "must"),  # imperative
        ("policy: rotate passwords every 90 days", "must"),
        ("refunds over $500 require manager approval", "must"),
        ("records must not be deleted", "must_not"),
        ("do not delete records", "must_not"),
        ("customer records may be exported", "may"),
        ("refunds will be issued", None),  # will: not a modality
        ("records should be exported", None),  # should: weak, matches none
        ("avoid deleting records", None),  # avoid: weak prohibition
    ],
)
def test_modality_reading_follows_section_8_2(
    clause: str, expected: str | None
) -> None:
    assert read_modality(clause) == expected


def test_conditional_permission_equivalents_give_may_but_only_there() -> None:
    text = "Refunds over $500 require manager approval."
    assert attested(
        "T.modality", "modality", "c1", "conditional_permission", "may", text
    )
    assert not attested("T.modality", "modality", "c1", "prohibition", "may", text)


@pytest.mark.parametrize(
    ("text", "component", "ok"),
    [
        (
            "Production deployment requires approval from two reviewers first.",
            "after_edge",
            True,
        ),
        ("Deploy to production only after two reviewers approve.", "after_edge", True),
        (
            "Deploy to production and get two reviewers to approve afterwards.",
            "after_edge",
            False,
        ),
        (
            "Deploy to production and get two reviewers to approve afterwards.",
            "action",
            True,
        ),
        (
            "Deploy to production and get two reviewers to approve afterwards.",
            "after",
            True,
        ),
        ("Production deployments are done with the release script.", "action", True),
        ("Production deployments are done with the release script.", "after", False),
    ],
)
def test_ordering_follows_section_8_3(text: str, component: str, ok: bool) -> None:
    order = {"action": "deploy to production", "after": "reviewers approve"}
    assert attested("T.ordering", component, "c4", "ordering", order, text) is ok


def test_comparator_reading_follows_section_8_1() -> None:
    q = "refund amount"
    assert read_comparator("refunds over 500", q) == ">"
    assert read_comparator("at least 2", q) == ">="
    assert read_comparator("records younger than 30 days", "record age") == "<"
    assert read_comparator("rotated every 90 days", "time since last rotation") == ">="
    assert read_comparator("every 90 days", q) is None  # only an elapsed time
    assert read_comparator("approved by 2 reviewers", "approving reviewers") == ">="
    assert read_comparator("roughly 90 days", "record age") is None


def test_a_changed_number_still_attests_the_other_parts_of_the_threshold() -> None:
    thr = {
        "quantity": "refund amount",
        "value": "500",
        "unit": "USD",
        "comparator": ">",
    }
    text = "Refunds over $5,000 may be issued."
    assert not attested(
        "T.threshold", "value", "c1", "conditional_permission", thr, text
    )
    for comp in ("unit", "quantity", "comparator"):
        assert attested("T.threshold", comp, "c1", "conditional_permission", thr, text)


def test_clauses_normalise_numbers_and_cut_at_semicolons_and_bars() -> None:
    assert clauses("Refunds over $5,000 need two approvals. Done; ok | x") == [
        "refunds over $5000 need 2 approvals",
        "done",
        "ok",
        "x",
    ]
