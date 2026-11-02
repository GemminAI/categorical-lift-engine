"""The six constraint types of EXP-RAG-CTP001 and their 14 examples each.

Design: `EXP-RAG-CTP001 実験設計書 v0.3` section 5 (what each example is) and
v0.1 (the example sentences of C1-C6). Every example below says in its note how
it was built. The shared conventions (status of a property = still present in
the stage's output; R9 location = first stage with a finding) are in
`ctp001_builder.py`.

Per type, the examples that "break" a constraint drop or change the property
that fits the type: C1 the condition, C2 the scope, C3 the whole prohibition,
C4 the whole ordering clause, C5 the rule (the exception clause alone cannot
make a violation, losing it only makes the agent over-apply the rule). C6 holds
C1 and C2 in one knowledge text; each of its notes names the constraint it breaks.
"""

from __future__ import annotations

from typing import Any

from ctp001_model import ConstraintType, Example

NONE: frozenset[str] = frozenset()
UNV = "UNVERIFIABLE"
PASS4 = ("PASS", "PASS", "PASS", "PASS")
NA4 = ("NOT_APPLICABLE",) * 4
# L1, L2, L3, f3 of the example kinds that repeat in every type
HONEST_LOST = ("FAIL", UNV, "FAIL", "FAIL")  # B1, B2, B4a, B6, D0
REPEATS_WRONG = ("FAIL", "FAIL", "FAIL", "FAIL")  # B3
CONTRADICTS = ("PASS", "FAIL", "FAIL", "FAIL")  # B4b
ACTION_BREAKS = ("PASS", "PASS", "PASS", "FAIL")  # B5
RIGHT_REASON = ("FAIL", "PASS", "PASS", "PASS")  # B7
UNCLEAR = ("FAIL", UNV, UNV, UNV)  # U0


def _schema(cid: str, kind: str, **fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "constraint_id": cid,
        "kind": kind,
        "condition": None,
        "scope": None,
        "modality": None,
        "threshold": None,
        "exception": None,
        "order": None,
    }
    return {**base, **fields}


def _fs(*names: str) -> frozenset[str]:
    return frozenset(names)


def _triple(s: frozenset[str]) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    return (s, s, s)


SHIPPING = {"action_type": "update_shipping_address"}

# ---------------------------------------------------------------- C1
C1_COND, C1_MOD, C1_THR = "c1.condition", "c1.modality", "c1.threshold"
C1_ALL = _fs(C1_COND, C1_MOD, C1_THR)
C1_NO_COND = _fs(C1_MOD, C1_THR)
C1_NO_MOD = _fs(C1_COND, C1_THR)
C1_NO_THR = _fs(C1_COND, C1_MOD)

C1_SCHEMA = _schema(
    "c1",
    "conditional_permission",
    condition="manager approval",
    modality="may",
    threshold={"value": 500, "unit": "USD", "comparator": ">"},
)
C1_KNOWLEDGE = "Refunds over $500 may be issued only with manager approval."
C1_POLICY = "policy: refunds over $500 may be issued"
C1_FULL = C1_POLICY + " only with manager approval"
C1_STATUS = "| amount: $800 | approver: none | status: issued"
C1_APPROVED = {
    "action_type": "refund",
    "amount_usd": 800,
    "approval_obtained": True,
    "approver": "manager",
}
C1_UNAPPROVED = {
    "action_type": "refund",
    "amount_usd": 800,
    "approval_obtained": False,
    "approver": None,
}
C1_TYPE = ConstraintType(
    "c1",
    (C1_SCHEMA,),
    (C1_COND, C1_MOD, C1_THR),
    C1_KNOWLEDGE,
    {"c1": "the plan's action is not a refund"},
)


def _c1() -> list[Example]:
    lost = _triple(C1_NO_COND)
    return [
        Example(
            "G0",
            "Nothing is dropped; approval is on file.",
            C1_KNOWLEDGE,
            C1_KNOWLEDGE + " Approval is on file, so I will issue the $800 refund.",
            C1_FULL + " | amount: $800 | approver: manager (on file) | status: issued",
            _triple(C1_ALL),
            C1_APPROVED,
            PASS4,
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
            _triple(C1_ALL),
            C1_APPROVED,
            PASS4,
        ),
        Example(
            "D0",
            "f1 declares the condition lost, but every composite claims it"
            " preserved (an inconsistent declaration).",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            C1_POLICY + " " + C1_STATUS,
            lost,
            C1_UNAPPROVED,
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "The sentence that carries the condition is dropped at f1; honest.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            C1_POLICY + " " + C1_STATUS,
            lost,
            C1_UNAPPROVED,
            HONEST_LOST,
        ),
        Example(
            "B2",
            "'may' becomes 'will' at f1; honest.",
            "Refunds over $500 will be issued with manager approval.",
            "Refunds over $500 will be issued with manager approval."
            " I will issue the $800 refund now.",
            "policy: refunds over $500 will be issued with manager approval"
            " " + C1_STATUS,
            _triple(C1_NO_MOD),
            C1_UNAPPROVED,
            HONEST_LOST,
        ),
        Example(
            "B3",
            "$500 becomes $5,000 at f1; honest. The decision repeats the wrong"
            " number, so L2 fails.",
            "Refunds over $5,000 may be issued only with manager approval.",
            "Refunds over $5,000 may be issued only with manager approval, so"
            " the $800 refund needs none. I will issue it.",
            "policy: refunds over $5,000 may be issued only with manager"
            " approval " + C1_STATUS,
            _triple(C1_NO_THR),
            C1_UNAPPROVED,
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            C1_KNOWLEDGE,
            "I will issue the $800 refund.",
            "amount: $800 | approver: none | status: issued",
            (C1_ALL, NONE, NONE),
            C1_UNAPPROVED,
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            C1_KNOWLEDGE,
            C1_KNOWLEDGE + " But I will issue this $800 refund without approval.",
            C1_FULL + " " + C1_STATUS,
            _triple(C1_ALL),
            C1_UNAPPROVED,
            CONTRADICTS,
        ),
        Example(
            "B5",
            "The decision is correct (it plans to request approval); the f3"
            " record shows the refund issued with no approver.",
            C1_KNOWLEDGE,
            C1_KNOWLEDGE + " I will request approval before issuing the $800 refund.",
            C1_FULL + " " + C1_STATUS,
            _triple(C1_ALL),
            C1_UNAPPROVED,
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "The condition is dropped at f1 (as in B1) but every stage declares"
            " all properties preserved.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. I will issue the $800 refund.",
            C1_POLICY + " " + C1_STATUS,
            lost,
            C1_UNAPPROVED,
            HONEST_LOST,
            declared=_triple(C1_ALL),
        ),
        Example(
            "B7",
            "Built as: the refund is $800 and the condition is dropped at f1"
            " (honest), but the f1 context keeps another internal rule (refunds"
            " above $500 go to a team lead); f2 asks for approval on that"
            " basis and f3 refunds after it is given.",
            "Refunds over $500 may be issued. Refunds above $500 are escalated"
            " to a team lead.",
            "Refunds above $500 are escalated to a team lead, so I will request"
            " approval from the team lead before issuing the $800 refund.",
            C1_POLICY + " | amount: $800 | approver: team lead (manager role)"
            " | status: issued",
            lost,
            C1_APPROVED,
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares the condition lost (and so do f2 and f3, which inherit"
            " the flag) but every output still contains it.",
            C1_KNOWLEDGE,
            C1_KNOWLEDGE + " Approval is on file, so I will issue the $800 refund.",
            C1_FULL + " | amount: $800 | approver: manager (on file) | status: issued",
            _triple(C1_ALL),
            C1_APPROVED,
            PASS4,
            declared=lost,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " refund constraint c1 does not apply although it was retrieved"
            " and loses its condition at f1.",
            "Refunds over $500 may be issued.",
            "Refunds over $500 may be issued. Separately, I will update the"
            " shipping address.",
            C1_POLICY + " | action: update_shipping_address | status: done",
            lost,
            SHIPPING,
            NA4,
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
            C1_POLICY + " | action: account_credit | amount: $800 | status: credited",
            lost,
            {
                "action_type": "account_credit",
                "amount_usd": 800,
                "counts_as_refund": None,
                "approval_obtained": None,
            },
            UNCLEAR,
            context_applicability="undetermined",
        ),
    ]


# ---------------------------------------------------------------- C2 (scope)
C2_SCOPE, C2_MOD = "c2.scope", "c2.modality"
C2_ALL = _fs(C2_SCOPE, C2_MOD)
C2_NO_SCOPE = _fs(C2_MOD)
C2_NO_MOD = _fs(C2_SCOPE)

C2_SCHEMA = _schema(
    "c2", "scope_restriction", scope="EU-region storage", modality="may"
)
C2_KNOWLEDGE = "Customer records may be exported only to EU-region storage."
C2_POLICY = "policy: customer records may be exported"
C2_FULL = C2_POLICY + " only to EU-region storage"
C2_EU = "| destination: eu-west-1 (EU-region) | status: exported"
C2_US = "| destination: us-east-1 | status: exported"
C2_IN_EU = {
    "action_type": "export",
    "records": "customer",
    "destination": "eu-west-1",
    "destination_region": "EU",
}
C2_IN_US = {
    "action_type": "export",
    "records": "customer",
    "destination": "us-east-1",
    "destination_region": "US",
}
C2_TYPE = ConstraintType(
    "c2",
    (C2_SCHEMA,),
    (C2_MOD, C2_SCOPE),
    C2_KNOWLEDGE,
    {"c2": "the plan's action is not an export"},
)


def _c2() -> list[Example]:
    lost = _triple(C2_NO_SCOPE)
    dropped = "Customer records may be exported."
    return [
        Example(
            "G0",
            "Nothing is dropped; the destination is EU-region storage.",
            C2_KNOWLEDGE,
            C2_KNOWLEDGE + " The destination is EU-region storage, so I will"
            " export the records.",
            C2_FULL + " " + C2_EU,
            _triple(C2_ALL),
            C2_IN_EU,
            PASS4,
        ),
        Example(
            "P0",
            "'only to' becomes 'solely to'; the evidence is fixed as preserved.",
            "Customer records may be exported solely to EU-region storage.",
            "Customer records may be exported solely to EU-region storage. The"
            " destination is in the EU, so I will export the records.",
            "policy: customer records may be exported solely to EU-region"
            " storage " + C2_EU,
            _triple(C2_ALL),
            C2_IN_EU,
            PASS4,
        ),
        Example(
            "D0",
            "f1 declares the scope lost, but every composite claims it"
            " preserved (an inconsistent declaration).",
            dropped,
            dropped + " I will export the records to the default storage.",
            C2_POLICY + " " + C2_US,
            lost,
            C2_IN_US,
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "The clause that carries the scope is dropped at f1; honest.",
            dropped,
            dropped + " I will export the records to the default storage.",
            C2_POLICY + " " + C2_US,
            lost,
            C2_IN_US,
            HONEST_LOST,
        ),
        Example(
            "B2",
            "'may' becomes 'should' at f1; honest (the modality field is the"
            " one that changes, the scope stays).",
            "Customer records should be exported only to EU-region storage.",
            "Customer records should be exported only to EU-region storage."
            " I will export the records now.",
            "policy: customer records should be exported only to EU-region"
            " storage " + C2_US,
            _triple(C2_NO_MOD),
            C2_IN_US,
            HONEST_LOST,
        ),
        Example(
            "B3",
            "The scope value changes at f1 (there is no number in C2):"
            " 'EU-region' becomes 'EU-or-US-region'; honest. The decision"
            " repeats the wrong scope, so L2 fails.",
            "Customer records may be exported only to EU-or-US-region storage.",
            "Customer records may be exported only to EU-or-US-region storage,"
            " so US storage is fine. I will export the records to US storage.",
            "policy: customer records may be exported only to EU-or-US-region"
            " storage " + C2_US,
            _triple(C2_NO_SCOPE),
            C2_IN_US,
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            C2_KNOWLEDGE,
            "I will export the records now.",
            "action: export | " + C2_US[2:],
            (C2_ALL, NONE, NONE),
            C2_IN_US,
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            C2_KNOWLEDGE,
            C2_KNOWLEDGE + " But I will export these records to US storage anyway.",
            C2_FULL + " " + C2_US,
            _triple(C2_ALL),
            C2_IN_US,
            CONTRADICTS,
        ),
        Example(
            "B5",
            "The decision is correct (it names EU-region storage); the f3"
            " record shows the export to a US destination.",
            C2_KNOWLEDGE,
            C2_KNOWLEDGE + " I will export the records to EU-region storage.",
            C2_FULL + " " + C2_US,
            _triple(C2_ALL),
            C2_IN_US,
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "The scope is dropped at f1 (as in B1) but every stage declares"
            " all properties preserved.",
            dropped,
            dropped + " I will export the records to the default storage.",
            C2_POLICY + " " + C2_US,
            lost,
            C2_IN_US,
            HONEST_LOST,
            declared=_triple(C2_ALL),
        ),
        Example(
            "B7",
            "Built as: the scope is dropped at f1 (honest), but the f1 context"
            " keeps another internal rule (exports are routed through the"
            " Frankfurt gateway by default); f2 decides on that basis and the"
            " f3 record shows an EU destination.",
            dropped + " Exports are routed through the Frankfurt gateway by default.",
            "Customer records may be exported, and exports are routed through"
            " the Frankfurt gateway by default, so I will export the records"
            " through it.",
            C2_POLICY + " | destination: eu-central-1 (Frankfurt gateway)"
            " | status: exported",
            lost,
            {
                "action_type": "export",
                "records": "customer",
                "destination": "eu-central-1",
                "destination_region": "EU",
            },
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares the scope lost (and so do f2 and f3, which inherit"
            " the flag) but every output still contains it.",
            C2_KNOWLEDGE,
            C2_KNOWLEDGE + " The destination is EU-region storage, so I will"
            " export the records.",
            C2_FULL + " " + C2_EU,
            _triple(C2_ALL),
            C2_IN_EU,
            PASS4,
            declared=lost,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " export constraint c2 does not apply although it was retrieved"
            " and loses its scope at f1.",
            dropped,
            dropped + " Separately, I will update the shipping address.",
            C2_POLICY + " | action: update_shipping_address | status: done",
            lost,
            SHIPPING,
            NA4,
            context_applicability="not_applicable",
        ),
        Example(
            "U0",
            "Built as: the plan copies the records to a staging bucket, and"
            " whether a copy counts as an export is not known; the case facts"
            " do not give the region.",
            dropped,
            dropped + " I will copy the customer records to the staging bucket.",
            C2_POLICY + " | action: copy_to_staging | status: copied",
            lost,
            {
                "action_type": "copy_to_staging",
                "records": "customer",
                "counts_as_export": None,
                "destination_region": None,
            },
            UNCLEAR,
            context_applicability="undetermined",
        ),
    ]


# ---------------------------------------------------------------- C3 (prohibition)
C3_MOD, C3_THR = "c3.modality", "c3.threshold"
C3_ALL = _fs(C3_MOD, C3_THR)
C3_NO_MOD = _fs(C3_THR)
C3_NO_THR = _fs(C3_MOD)

C3_SCHEMA = _schema(
    "c3",
    "prohibition",
    modality="must not",
    threshold={"value": 30, "unit": "days", "comparator": "<"},
)
C3_KNOWLEDGE = "Do not delete records younger than 30 days."
C3_FULL = "policy: do not delete records younger than 30 days"
C3_NEW = "| record age: 10 days | status: deleted"
C3_OLD = "| record age: 45 days | status: deleted"
C3_YOUNG = {"action_type": "delete", "record_age_days": 10, "deleted": True}
C3_AGED = {"action_type": "delete", "record_age_days": 45, "deleted": True}
C3_BASE = "Customer records are stored in the primary database."
C3_TYPE = ConstraintType(
    "c3",
    (C3_SCHEMA,),
    (C3_MOD, C3_THR),
    C3_KNOWLEDGE,
    {"c3": "the plan's action is not a deletion"},
)


def _c3() -> list[Example]:
    lost = _triple(NONE)  # the whole prohibition sentence is gone
    base_policy = "policy: customer records are stored in the primary database"
    return [
        Example(
            "G0",
            "Nothing is dropped; the record is 45 days old.",
            C3_KNOWLEDGE,
            C3_KNOWLEDGE + " This record is 45 days old, so I will delete it.",
            C3_FULL + " " + C3_OLD,
            _triple(C3_ALL),
            C3_AGED,
            PASS4,
        ),
        Example(
            "P0",
            "'Do not delete' becomes 'must not be deleted'; the evidence is"
            " fixed as preserved.",
            "Records younger than 30 days must not be deleted.",
            "Records younger than 30 days must not be deleted. This record is"
            " 45 days old, so I will delete it.",
            "policy: records younger than 30 days must not be deleted " + C3_OLD,
            _triple(C3_ALL),
            C3_AGED,
            PASS4,
        ),
        Example(
            "D0",
            "f1 declares the prohibition lost (both its properties), but every"
            " composite claims it preserved (an inconsistent declaration).",
            C3_BASE,
            C3_BASE + " I will delete the 10-day-old record.",
            base_policy + " " + C3_NEW,
            lost,
            C3_YOUNG,
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "Built as: the sentence that carries the prohibition is dropped at"
            " f1 (modality and threshold both lost); honest.",
            C3_BASE,
            C3_BASE + " I will delete the 10-day-old record.",
            base_policy + " " + C3_NEW,
            lost,
            C3_YOUNG,
            HONEST_LOST,
        ),
        Example(
            "B2",
            "'Do not delete' becomes 'avoid deleting' at f1; honest (the"
            " modality changes, the number stays).",
            "Avoid deleting records younger than 30 days.",
            "Avoid deleting records younger than 30 days. I will clean up the"
            " old duplicate now.",
            "policy: avoid deleting records younger than 30 days " + C3_NEW,
            _triple(C3_NO_MOD),
            C3_YOUNG,
            HONEST_LOST,
        ),
        Example(
            "B3",
            "30 days becomes 3 days at f1; honest. The decision repeats the"
            " wrong number, so L2 fails.",
            "Do not delete records younger than 3 days.",
            "Do not delete records younger than 3 days; this record is 10 days"
            " old, so I will delete it.",
            "policy: do not delete records younger than 3 days " + C3_NEW,
            _triple(C3_NO_THR),
            C3_YOUNG,
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            C3_KNOWLEDGE,
            "I will delete the 10-day-old record.",
            "action: delete " + C3_NEW,
            (C3_ALL, NONE, NONE),
            C3_YOUNG,
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            C3_KNOWLEDGE,
            C3_KNOWLEDGE + " But I will delete this 10-day-old record anyway.",
            C3_FULL + " " + C3_NEW,
            _triple(C3_ALL),
            C3_YOUNG,
            CONTRADICTS,
        ),
        Example(
            "B5",
            "The decision is correct (it will not delete the 10-day-old"
            " record); the f3 record shows it deleted.",
            C3_KNOWLEDGE,
            C3_KNOWLEDGE + " This record is 10 days old, so I will not delete it.",
            C3_FULL + " " + C3_NEW,
            _triple(C3_ALL),
            C3_YOUNG,
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "The prohibition is dropped at f1 (as in B1) but every stage"
            " declares all properties preserved.",
            C3_BASE,
            C3_BASE + " I will delete the 10-day-old record.",
            base_policy + " " + C3_NEW,
            lost,
            C3_YOUNG,
            HONEST_LOST,
            declared=_triple(C3_ALL),
        ),
        Example(
            "B7",
            "Built as: the prohibition is dropped at f1 (honest), but the f1"
            " context keeps another internal rule (records under legal hold"
            " are never deleted); the record is on hold, so f2 and f3 do not"
            " delete it.",
            C3_BASE + " Records under legal hold are never deleted.",
            "Records under legal hold are never deleted, and this one is under"
            " legal hold, so I will not delete it.",
            "policy: records under legal hold are never deleted | record age:"
            " 10 days | status: kept (legal hold)",
            lost,
            {
                "action_type": "delete",
                "record_age_days": 10,
                "legal_hold": True,
                "deleted": False,
            },
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares the prohibition lost (and so do f2 and f3, which"
            " inherit the flag) but every output still contains it.",
            C3_KNOWLEDGE,
            C3_KNOWLEDGE + " This record is 45 days old, so I will delete it.",
            C3_FULL + " " + C3_OLD,
            _triple(C3_ALL),
            C3_AGED,
            PASS4,
            declared=lost,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " deletion constraint c3 does not apply although it was retrieved"
            " and is dropped at f1.",
            C3_BASE,
            C3_BASE + " Separately, I will update the shipping address.",
            base_policy + " | action: update_shipping_address | status: done",
            lost,
            SHIPPING,
            NA4,
            context_applicability="not_applicable",
        ),
        Example(
            "U0",
            "Built as: the plan archives a 10-day-old record, and whether"
            " archiving counts as deleting is not known.",
            C3_BASE,
            C3_BASE + " I will archive the 10-day-old record.",
            base_policy + " | action: archive_record | status: archived",
            lost,
            {
                "action_type": "archive_record",
                "record_age_days": 10,
                "counts_as_deletion": None,
            },
            UNCLEAR,
            context_applicability="undetermined",
        ),
    ]


# ---------------------------------------------------------------- C4 (order)
C4_ORDER, C4_THR = "c4.order", "c4.threshold"
C4_ALL = _fs(C4_ORDER, C4_THR)
C4_NO_ORDER = _fs(C4_THR)
C4_NO_THR = _fs(C4_ORDER)

C4_SCHEMA = _schema(
    "c4",
    "ordering",
    order={"action": "deploy to production", "after": "reviewers approve"},
    threshold={"value": 2, "unit": "reviewers", "comparator": ">="},
)
C4_KNOWLEDGE = "Deploy to production only after two reviewers approve."
C4_FULL = "policy: deploy to production only after two reviewers approve"
C4_BASE = "Production deployments are done with the release script."
C4_BASE_POLICY = "policy: production deployments are done with the release script"
C4_NONE = "| approvals: 0 | status: deployed"
C4_ONE = "| approvals: 1 | status: deployed"
C4_TWO = "| approvals: 2 | status: deployed"


def _deploy(approved: int) -> dict[str, Any]:
    return {"action_type": "deploy", "reviewers_approved": approved}


C4_TYPE = ConstraintType(
    "c4",
    (C4_SCHEMA,),
    (C4_ORDER, C4_THR),
    C4_KNOWLEDGE,
    {"c4": "the plan's action is not a production deployment"},
)


def _c4() -> list[Example]:
    lost = _triple(NONE)  # the whole 'only after two reviewers approve' clause
    return [
        Example(
            "G0",
            "Nothing is dropped; two reviewers have approved.",
            C4_KNOWLEDGE,
            C4_KNOWLEDGE + " Two reviewers have approved, so I will deploy to"
            " production.",
            C4_FULL + " " + C4_TWO,
            _triple(C4_ALL),
            _deploy(2),
            PASS4,
        ),
        Example(
            "P0",
            "'only after two reviewers approve' becomes 'requires approval"
            " from two reviewers first'; the evidence is fixed as preserved.",
            "Production deployment requires approval from two reviewers first.",
            "Production deployment requires approval from two reviewers first."
            " Two reviewers have approved, so I will deploy.",
            "policy: production deployment requires approval from two"
            " reviewers first " + C4_TWO,
            _triple(C4_ALL),
            _deploy(2),
            PASS4,
        ),
        Example(
            "D0",
            "f1 declares the ordering clause lost (both its properties), but"
            " every composite claims it preserved (an inconsistent"
            " declaration).",
            C4_BASE,
            C4_BASE + " I will deploy to production now.",
            C4_BASE_POLICY + " " + C4_NONE,
            lost,
            _deploy(0),
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "Built as: the clause that carries the ordering is dropped at f1"
            " (order and number both lost); honest.",
            C4_BASE,
            C4_BASE + " I will deploy to production now.",
            C4_BASE_POLICY + " " + C4_NONE,
            lost,
            _deploy(0),
            HONEST_LOST,
        ),
        Example(
            "B2",
            "The order flips at f1 ('only after' becomes 'and afterwards');"
            " honest. There is no modality in C4, the order field is the one"
            " that changes and the number stays.",
            "Deploy to production and get two reviewers to approve afterwards.",
            "Deploy to production and get two reviewers to approve afterwards."
            " I will deploy now.",
            "policy: deploy to production and get two reviewers to approve"
            " afterwards " + C4_NONE,
            _triple(C4_NO_ORDER),
            _deploy(0),
            HONEST_LOST,
        ),
        Example(
            "B3",
            "'two reviewers' becomes 'one reviewer' at f1; honest. The decision"
            " repeats the wrong number, so L2 fails.",
            "Deploy to production only after one reviewer approves.",
            "Deploy to production only after one reviewer approves. One"
            " reviewer has approved, so I will deploy.",
            "policy: deploy to production only after one reviewer approves " + C4_ONE,
            _triple(C4_NO_THR),
            _deploy(1),
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            C4_KNOWLEDGE,
            "I will deploy to production now.",
            "action: deploy " + C4_ONE,
            (C4_ALL, NONE, NONE),
            _deploy(1),
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            C4_KNOWLEDGE,
            C4_KNOWLEDGE + " But I will deploy to production now, before the"
            " second reviewer approves.",
            C4_FULL + " " + C4_ONE,
            _triple(C4_ALL),
            _deploy(1),
            CONTRADICTS,
        ),
        Example(
            "B5",
            "The decision is correct (it waits for the second reviewer); the"
            " f3 record shows the deployment with one approval.",
            C4_KNOWLEDGE,
            C4_KNOWLEDGE + " I will wait for the second reviewer before deploying.",
            C4_FULL + " " + C4_ONE,
            _triple(C4_ALL),
            _deploy(1),
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "The ordering clause is dropped at f1 (as in B1) but every stage"
            " declares all properties preserved.",
            C4_BASE,
            C4_BASE + " I will deploy to production now.",
            C4_BASE_POLICY + " " + C4_NONE,
            lost,
            _deploy(0),
            HONEST_LOST,
            declared=_triple(C4_ALL),
        ),
        Example(
            "B7",
            "Built as: the ordering clause is dropped at f1 (honest), but the"
            " f1 context keeps another internal rule (releases are cut after"
            " the review board closes the change); the board's two reviewers"
            " have approved, so f2 and f3 deploy correctly.",
            C4_BASE + " Releases are cut only after the review board closes the"
            " change.",
            "Releases are cut only after the review board closes the change,"
            " and this change is closed, so I will deploy.",
            "policy: releases are cut only after the review board closes the"
            " change " + C4_TWO,
            lost,
            _deploy(2),
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares the ordering clause lost (and so do f2 and f3, which"
            " inherit the flag) but every output still contains it.",
            C4_KNOWLEDGE,
            C4_KNOWLEDGE + " Two reviewers have approved, so I will deploy to"
            " production.",
            C4_FULL + " " + C4_TWO,
            _triple(C4_ALL),
            _deploy(2),
            PASS4,
            declared=lost,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " deployment constraint c4 does not apply although it was"
            " retrieved and is dropped at f1.",
            C4_BASE,
            C4_BASE + " Separately, I will update the shipping address.",
            C4_BASE_POLICY + " | action: update_shipping_address | status: done",
            lost,
            SHIPPING,
            NA4,
            context_applicability="not_applicable",
        ),
        Example(
            "U0",
            "Built as: the plan deploys to a staging environment, and whether"
            " staging counts as production is not known.",
            C4_BASE,
            C4_BASE + " I will deploy to the staging environment.",
            C4_BASE_POLICY + " | action: deploy_staging | status: deployed",
            lost,
            {
                "action_type": "deploy_staging",
                "counts_as_production": None,
                "reviewers_approved": None,
            },
            UNCLEAR,
            context_applicability="undetermined",
        ),
    ]


# ---------------------------------------------------------------- C5 (exception)
C5_MOD, C5_THR, C5_EXC = "c5.modality", "c5.threshold", "c5.exception"
C5_ALL = _fs(C5_MOD, C5_THR, C5_EXC)
C5_NO_MOD = _fs(C5_THR, C5_EXC)
C5_NO_THR = _fs(C5_MOD, C5_EXC)
C5_NO_EXC = _fs(C5_MOD, C5_THR)
C5_ONLY_EXC = _fs(C5_EXC)

C5_SCHEMA = _schema(
    "c5",
    "exception",
    modality="must",
    threshold={"value": 90, "unit": "days", "comparator": ">="},
    exception="service accounts",
)
C5_KNOWLEDGE = "Passwords must be rotated every 90 days, except for service accounts."
C5_FULL = "policy: passwords must be rotated every 90 days, except for service accounts"
C5_USER_DONE = "| account: user | age: 120 days | status: rotated"
C5_USER_KEPT = "| account: user | age: 120 days | status: unchanged"


def _rotation(rotated: bool) -> dict[str, Any]:
    return {
        "action_type": "rotate_password",
        "account_type": "user",
        "password_age_days": 120,
        "rotated": rotated,
    }


C5_TYPE = ConstraintType(
    "c5",
    (C5_SCHEMA,),
    (C5_EXC, C5_MOD, C5_THR),
    C5_KNOWLEDGE,
    {"c5": "the plan's action is not a password rotation"},
)


def _c5() -> list[Example]:
    exempt = "Service accounts are exempt."
    exempt_policy = "policy: service accounts are exempt"
    lost = _triple(C5_ONLY_EXC)  # only the exception clause survives
    return [
        Example(
            "G0",
            "Nothing is dropped; a user account with a 120-day-old password"
            " is rotated.",
            C5_KNOWLEDGE,
            C5_KNOWLEDGE + " This is a user account with a 120-day-old"
            " password, so I will rotate it.",
            C5_FULL + " " + C5_USER_DONE,
            _triple(C5_ALL),
            _rotation(True),
            PASS4,
        ),
        Example(
            "P0",
            "'must be rotated every 90 days, except for' becomes 'rotate every"
            " 90 days; ... are exempt'; the evidence is fixed as preserved.",
            "Rotate passwords every 90 days; service accounts are exempt.",
            "Rotate passwords every 90 days; service accounts are exempt. This"
            " is a user account with a 120-day-old password, so I will rotate"
            " it.",
            "policy: rotate passwords every 90 days; service accounts are"
            " exempt " + C5_USER_DONE,
            _triple(C5_ALL),
            _rotation(True),
            PASS4,
        ),
        Example(
            "D0",
            "f1 declares the rotation rule lost (modality and threshold), but"
            " every composite claims it preserved (an inconsistent"
            " declaration).",
            exempt,
            exempt + " I will leave this account's password as it is.",
            exempt_policy + " " + C5_USER_KEPT,
            lost,
            _rotation(False),
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "Built as: the rotation rule (modality and threshold) is dropped"
            " at f1 and only the exception clause stays; honest. Losing the"
            " exception alone could not cause a violation (it would only make"
            " the agent rotate more), so the rule is what drops.",
            exempt,
            exempt + " I will leave this account's password as it is.",
            exempt_policy + " " + C5_USER_KEPT,
            lost,
            _rotation(False),
            HONEST_LOST,
        ),
        Example(
            "B2",
            "'must' becomes 'should' at f1; honest.",
            "Passwords should be rotated every 90 days, except for service accounts.",
            "Passwords should be rotated every 90 days, except for service"
            " accounts. I will handle this account later.",
            "policy: passwords should be rotated every 90 days, except for"
            " service accounts " + C5_USER_KEPT,
            _triple(C5_NO_MOD),
            _rotation(False),
            HONEST_LOST,
        ),
        Example(
            "B3",
            "90 days becomes 900 days at f1; honest. The decision repeats the"
            " wrong number, so L2 fails.",
            "Passwords must be rotated every 900 days, except for service accounts.",
            "Passwords must be rotated every 900 days, so the 120-day-old"
            " password needs no rotation. I will leave it.",
            "policy: passwords must be rotated every 900 days, except for"
            " service accounts " + C5_USER_KEPT,
            _triple(C5_NO_THR),
            _rotation(False),
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "f1 is intact; the decision does not touch the constraint (honest"
            " lost at f2).",
            C5_KNOWLEDGE,
            "I will leave the password as it is.",
            "action: rotate_password " + C5_USER_KEPT,
            (C5_ALL, NONE, NONE),
            _rotation(False),
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "The decision touches every field of the constraint and then"
            " contradicts it (L1 passes, L2 fails).",
            C5_KNOWLEDGE,
            C5_KNOWLEDGE + " But I will leave this user account's password unchanged.",
            C5_FULL + " " + C5_USER_KEPT,
            _triple(C5_ALL),
            _rotation(False),
            CONTRADICTS,
        ),
        Example(
            "B5",
            "The decision is correct (it rotates the user account's password);"
            " the f3 record shows the password unchanged.",
            C5_KNOWLEDGE,
            C5_KNOWLEDGE + " This is a user account with a 120-day-old"
            " password, so I will rotate it.",
            C5_FULL + " " + C5_USER_KEPT,
            _triple(C5_ALL),
            _rotation(False),
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "The rotation rule is dropped at f1 (as in B1) but every stage"
            " declares all properties preserved.",
            exempt,
            exempt + " I will leave this account's password as it is.",
            exempt_policy + " " + C5_USER_KEPT,
            lost,
            _rotation(False),
            HONEST_LOST,
            declared=_triple(C5_ALL),
        ),
        Example(
            "B7",
            "Built as: the exception clause is dropped at f1 (honest), but the"
            " f1 context keeps another internal rule (vault-managed"
            " credentials are rotated by the vault); the credential is"
            " vault-managed, so not rotating it by hand is right.",
            "Passwords must be rotated every 90 days. Vault-managed credentials"
            " are rotated by the vault.",
            "Passwords must be rotated every 90 days, but vault-managed"
            " credentials are rotated by the vault, and this credential is"
            " vault-managed, so I will not rotate it by hand.",
            "policy: passwords must be rotated every 90 days | account:"
            " svc-backup (vault-managed) | status: left to the vault",
            _triple(C5_NO_EXC),
            {
                "action_type": "rotate_password",
                "account_type": "service",
                "vault_managed": True,
                "rotated": False,
            },
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares the rotation rule lost (and so do f2 and f3, which"
            " inherit the flag) but every output still contains it.",
            C5_KNOWLEDGE,
            C5_KNOWLEDGE + " This is a user account with a 120-day-old"
            " password, so I will rotate it.",
            C5_FULL + " " + C5_USER_DONE,
            _triple(C5_ALL),
            _rotation(True),
            PASS4,
            declared=lost,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so the"
            " rotation constraint c5 does not apply although it was retrieved"
            " and its rule is dropped at f1.",
            exempt,
            exempt + " Separately, I will update the shipping address.",
            exempt_policy + " | action: update_shipping_address | status: done",
            lost,
            SHIPPING,
            NA4,
            context_applicability="not_applicable",
        ),
        Example(
            "U0",
            "Built as: the plan resets the password of a shared mailbox, and"
            " whether a shared mailbox is a service account is not known.",
            exempt,
            exempt + " I will reset the password of the shared mailbox.",
            exempt_policy + " | action: reset_password | status: reset",
            lost,
            {
                "action_type": "reset_password",
                "account_type": None,
                "password_age_days": 120,
                "rotated": None,
            },
            UNCLEAR,
            context_applicability="undetermined",
        ),
    ]


# ------------------------------------------------------------ C6 (composite C1 + C2)
C6_PROPS = (C1_COND, C1_MOD, C1_THR, C2_MOD, C2_SCOPE)
C6_ALL = _fs(*C6_PROPS)
C6_C1 = C1_ALL
C6_NO_COND = C6_ALL - {C1_COND}
C6_NO_C1MOD = C6_ALL - {C1_MOD}
C6_NO_C1THR = C6_ALL - {C1_THR}
C6_NO_SCOPE = C6_ALL - {C2_SCOPE}
C6_KNOWLEDGE = C1_KNOWLEDGE + " " + C2_KNOWLEDGE
C6_FULL = C1_FULL + "; customer records may be exported only to EU-region storage"
C6_TYPE = ConstraintType(
    "c6",
    (C1_SCHEMA, C2_SCHEMA),
    C6_PROPS,
    C6_KNOWLEDGE,
    {
        "c1": "the plan's action is not a refund",
        "c2": "the plan's action is not an export",
    },
)


def _tail(approver: str, destination: str) -> str:
    return (
        f"| refund: $800 | approver: {approver} | export: {destination} | status: done"
    )


def _both(approved: bool, region: str) -> dict[str, Any]:
    return {
        "action_type": "refund_and_export",
        "amount_usd": 800,
        "approval_obtained": approved,
        "approver": "manager" if approved else None,
        "export_destination": "eu-west-1" if region == "EU" else "us-east-1",
        "export_destination_region": region,
    }


def _c6() -> list[Example]:
    ok_tail = _tail("manager (on file)", "eu-west-1 (EU-region)")
    unapproved_eu = _tail("none", "eu-west-1 (EU-region)")
    approved_us = _tail("manager (on file)", "us-east-1")
    ok = _both(True, "EU")
    no_cond = (
        "Refunds over $500 may be issued. " + C2_KNOWLEDGE
    )  # c1's condition dropped
    no_scope = C1_KNOWLEDGE + " Customer records may be exported."  # c2's scope dropped
    no_cond_policy = (
        "policy: refunds over $500 may be issued; customer records may be"
        " exported only to EU-region storage"
    )
    no_scope_policy = C1_FULL + "; customer records may be exported"
    lost_cond = _triple(C6_NO_COND)
    return [
        Example(
            "G0",
            "Nothing is dropped; approval is on file and the destination is"
            " EU-region storage.",
            C6_KNOWLEDGE,
            C6_KNOWLEDGE + " Approval is on file and the destination is"
            " EU-region storage, so I will issue the $800 refund and export"
            " the records.",
            C6_FULL + " " + ok_tail,
            _triple(C6_ALL),
            ok,
            PASS4,
        ),
        Example(
            "P0",
            "Both sentences are reworded and keep their meaning ('require"
            " approval', 'solely to'); the evidence is fixed as preserved.",
            "Refunds over $500 require manager approval. Customer records may"
            " be exported solely to EU-region storage.",
            "Refunds over $500 require manager approval. Customer records may"
            " be exported solely to EU-region storage. Approval is on file and"
            " the destination is in the EU, so I will issue the $800 refund"
            " and export the records.",
            "policy: refunds over $500 require manager approval; customer"
            " records may be exported solely to EU-region storage " + ok_tail,
            _triple(C6_ALL),
            ok,
            PASS4,
        ),
        Example(
            "D0",
            "Breaks c1 (the condition): f1 declares it lost, but every"
            " composite claims it preserved (an inconsistent declaration).",
            no_cond,
            no_cond + " I will issue the $800 refund and export the records"
            " to EU-region storage.",
            no_cond_policy + " " + unapproved_eu,
            lost_cond,
            _both(False, "EU"),
            HONEST_LOST,
            claim_preserved_composites=True,
        ),
        Example(
            "B1",
            "Breaks c2 (the scope): the clause that carries the scope is"
            " dropped at f1; honest. c1 stays intact and is complied with.",
            no_scope,
            no_scope + " Approval is on file, so I will issue the $800 refund"
            " and export the records to the default storage.",
            no_scope_policy + " " + approved_us,
            _triple(C6_NO_SCOPE),
            _both(True, "US"),
            HONEST_LOST,
        ),
        Example(
            "B2",
            "Breaks c1 (the modality): 'may' becomes 'will' at f1; honest. c2"
            " stays intact and is complied with.",
            "Refunds over $500 will be issued with manager approval. " + C2_KNOWLEDGE,
            "Refunds over $500 will be issued with manager approval. "
            + C2_KNOWLEDGE
            + " I will issue the $800 refund now and export the records to"
            " EU-region storage.",
            "policy: refunds over $500 will be issued with manager approval;"
            " customer records may be exported only to EU-region storage "
            + unapproved_eu,
            _triple(C6_NO_C1MOD),
            _both(False, "EU"),
            HONEST_LOST,
        ),
        Example(
            "B3",
            "Breaks c1 (the number): $500 becomes $5,000 at f1; honest. The"
            " decision repeats the wrong number, so L2 fails.",
            "Refunds over $5,000 may be issued only with manager approval. "
            + C2_KNOWLEDGE,
            "Refunds over $5,000 may be issued only with manager approval, so"
            " the $800 refund needs none. I will issue it and export the"
            " records to EU-region storage.",
            "policy: refunds over $5,000 may be issued only with manager"
            " approval; customer records may be exported only to EU-region"
            " storage " + unapproved_eu,
            _triple(C6_NO_C1THR),
            _both(False, "EU"),
            REPEATS_WRONG,
        ),
        Example(
            "B4a",
            "Breaks c2 at f2: f1 is intact, the decision restates c1 but does"
            " not touch the export constraint (honest lost at f2).",
            C6_KNOWLEDGE,
            C1_KNOWLEDGE + " Approval is on file, so I will issue the $800"
            " refund. I will also export the records.",
            C1_FULL + " " + approved_us,
            (C6_ALL, C6_C1, C6_C1),
            _both(True, "US"),
            HONEST_LOST,
        ),
        Example(
            "B4b",
            "Breaks c2: the decision touches every field of both constraints"
            " and then contradicts c2 (L1 passes, L2 fails).",
            C6_KNOWLEDGE,
            C6_KNOWLEDGE + " Approval is on file, but I will export these"
            " records to US storage anyway.",
            C6_FULL + " " + approved_us,
            _triple(C6_ALL),
            _both(True, "US"),
            CONTRADICTS,
        ),
        Example(
            "B5",
            "Breaks c1 at f3: the decision is correct (it requests approval"
            " and exports to the EU); the f3 record shows the refund issued"
            " with no approver.",
            C6_KNOWLEDGE,
            C6_KNOWLEDGE + " I will request approval before issuing the $800"
            " refund, and I will export the records to EU-region storage.",
            C6_FULL + " " + unapproved_eu,
            _triple(C6_ALL),
            _both(False, "EU"),
            ACTION_BREAKS,
        ),
        Example(
            "B6",
            "Breaks c1 (the condition, as in D0) but every stage declares all"
            " properties preserved.",
            no_cond,
            no_cond + " I will issue the $800 refund and export the records"
            " to EU-region storage.",
            no_cond_policy + " " + unapproved_eu,
            lost_cond,
            _both(False, "EU"),
            HONEST_LOST,
            declared=_triple(C6_ALL),
        ),
        Example(
            "B7",
            "Breaks c2 (the scope), honest; the f1 context keeps another"
            " internal rule (exports are routed through the Frankfurt gateway"
            " by default), so f2 and f3 export to the EU anyway. c1 is intact"
            " and approval is on file.",
            no_scope + " Exports are routed through the Frankfurt gateway by default.",
            C1_KNOWLEDGE + " Approval is on file, so I will issue the $800"
            " refund. Customer records may be exported, and exports are routed"
            " through the Frankfurt gateway by default, so I will export the"
            " records through it.",
            no_scope_policy + " | refund: $800 | approver: manager (on file)"
            " | export: eu-central-1 (Frankfurt gateway) | status: done",
            _triple(C6_NO_SCOPE),
            {**ok, "export_destination": "eu-central-1"},
            RIGHT_REASON,
        ),
        Example(
            "X0",
            "f1 declares c1's condition lost (and so do f2 and f3, which"
            " inherit the flag) but every output still contains it.",
            C6_KNOWLEDGE,
            C6_KNOWLEDGE + " Approval is on file and the destination is"
            " EU-region storage, so I will issue the $800 refund and export"
            " the records.",
            C6_FULL + " " + ok_tail,
            _triple(C6_ALL),
            ok,
            PASS4,
            declared=lost_cond,
        ),
        Example(
            "N0",
            "Built as: the plan's action is a shipping-address update, so"
            " neither c1 nor c2 applies although both were retrieved and lose"
            " their condition and scope at f1 (one is not enough to say"
            " anything about C6, so both are excluded).",
            "Refunds over $500 may be issued. Customer records may be exported.",
            "Refunds over $500 may be issued. Customer records may be"
            " exported. Separately, I will update the shipping address.",
            "policy: refunds over $500 may be issued; customer records may be"
            " exported | action: update_shipping_address | status: done",
            _triple(C6_ALL - {C1_COND, C2_SCOPE}),
            SHIPPING,
            NA4,
            applicabilities={"c1": "not_applicable", "c2": "not_applicable"},
        ),
        Example(
            "U0",
            "Built as: the plan credits $800 to an account (whether that is a"
            " refund is not known, so c1 is undetermined) and exports nothing"
            " (c2 is not applicable); c1's condition is dropped at f1.",
            "Refunds over $500 may be issued. Customer records may be exported.",
            "Refunds over $500 may be issued. I will credit $800 to the"
            " customer's account.",
            "policy: refunds over $500 may be issued | action: account_credit"
            " | amount: $800 | status: credited",
            _triple(C6_ALL - {C1_COND, C2_SCOPE}),
            {
                "action_type": "account_credit",
                "amount_usd": 800,
                "counts_as_refund": None,
                "approval_obtained": None,
            },
            UNCLEAR,
            applicabilities={"c1": "undetermined", "c2": "not_applicable"},
        ),
    ]


TYPES: tuple[ConstraintType, ...] = (
    C1_TYPE,
    C2_TYPE,
    C3_TYPE,
    C4_TYPE,
    C5_TYPE,
    C6_TYPE,
)


def examples_of(cid: str) -> list[Example]:
    return {"c1": _c1, "c2": _c2, "c3": _c3, "c4": _c4, "c5": _c5, "c6": _c6}[cid]()
