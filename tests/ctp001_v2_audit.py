"""A plain audit of the new fixtures' sentences (`Constraint Schema 仕様 v0.4`).

For every stage of every new fixture and every component the Carry Evidence says is
preserved (P), does the evidence for it actually appear in that stage's text? The
rules are string matching and the phrase tables of section 8 (comparator v2,
modality v2, ordering v2, exception v1), written out here and shared with nothing:
the Constraint Verifier is not consulted. A component is "attested" when the
evidence is found; the audit does not decide that a component is absent, only that
nothing in the text attests it.

A clause is a sentence, or a part of a sentence cut at `;` or `|` (section 7.1: the
evidence is read inside the clause that states the field).
"""

from __future__ import annotations

import re
from typing import Any

STAGE_TEXT = {"f1": "f1_context", "f2": "f2_decision", "f3": "f3_action"}
_WORDS = "zero one two three four five six seven eight nine ten"
NUMBER_WORDS = {w: str(i) for i, w in enumerate(_WORDS.split())}
# section 8.1
COMPARATORS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (">=", ("at least", "or more", "no less than", "minimum of")),
    ("<=", ("at most", "up to", "no more than", "maximum of", "not exceeding")),
    (">", ("over", "more than", "exceeding", "above", "greater than")),
    ("<", ("under", "less than", "below", "younger than", "fewer than")),
    ("==", ("exactly", "equal to")),
)
# section 8.2, the must_not row first so that "must not" is not read as "must"
MODALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "must_not",
        re.compile(
            r"\b(must not|may not|shall not|cannot|do not|never|is prohibited"
            r"|is not allowed)\b"
        ),
    ),
    ("may", re.compile(r"\b(may|can|is allowed to|is permitted to)\b")),
    (
        "must",
        re.compile(r"\b(must|shall|is required to|requires?|needs to|has to)\b"),
    ),
)
# section 8.2: an imperative sentence is a `must`. The verbs the fixtures' policies
# start with; a clause starting with one of them (after an optional `policy:`).
IMPERATIVE_VERBS = ("rotate", "deploy", "delete", "issue", "export")
# section 8.5, for `conditional_permission`: the other ways to say the same thing
CONDITIONAL_PERMISSION_EQUIVALENTS = re.compile(
    r"\b(only with|only if|only when|requires?|must have|needs|without|unless)\b"
)
# section 8.4
EXCEPTION_EXPRESSIONS = re.compile(
    r"\b(except for|except|excluding|other than|with the exception of|exempt"
    r"|excepted|does not apply to)\b"
)
# section 8.3: the expressions that put `action` after the other event
AFTER_EXPRESSIONS = re.compile(
    r"\b(only after|after|once|following|not before|subsequent to)\b"
)
# the audit's own cues for the quantity and the events (section 7.1: words are not
# enough alone, so these are only used inside a clause that also holds the value)
QUANTITY_CUES = {
    "refund amount": ("refund",),
    "record age": ("record",),
    "approving reviewers": ("reviewer", "approv"),
    "time since last rotation": ("rotat", "password"),
}
EVENT_CUES = {
    "deploy to production": ("deploy",),
    "reviewers approve": ("approv",),
}
# the clause of a modality is the one about the constraint's subject (c6 holds two
# constraints, and a `may` about refunds is not the modality of the export rule)
TOPIC_CUES = {
    "c1": ("refund",),
    "c2": ("export",),
    "c3": ("delet",),
    "c5": ("password", "rotat"),
}
UNIT_FORMS = {
    "USD": ("$", "usd"),
    "days": ("day",),
    "reviewers": ("reviewer",),
}


def clauses(text: str) -> list[str]:
    """Lower-cased clauses, thousands separators and number words normalised."""
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text.lower())
    text = re.sub(
        r"\b(" + "|".join(NUMBER_WORDS) + r")\b", lambda m: NUMBER_WORDS[m[1]], text
    )
    return [c.strip() for c in re.split(r"[.;|](?:\s|$)|[;|]", text) if c.strip()]


def _numbers(clause: str) -> set[str]:
    return set(re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])", clause))


def read_modality(clause: str) -> str | None:
    """Section 8.2 on one clause: the first row that matches (none: no modality)."""
    body = clause.removeprefix("policy:").strip()
    for modality, pattern in MODALS:
        if pattern.search(body):
            return modality
    if body.split(" ", 1)[0] in IMPERATIVE_VERBS:
        return "must"
    return None


def read_comparator(clause: str, quantity: str) -> str | None:
    """Section 8.1 on one clause; None when no row applies."""
    for symbol, phrases in COMPARATORS:
        if any(re.search(rf"\b{re.escape(p)}\b", clause) for p in phrases):
            return symbol
    if quantity == "time since last rotation" and re.search(r"\bevery \d+", clause):
        return ">="  # every N, only when the quantity is an elapsed time
    if quantity == "approving reviewers" and re.search(r"\b\d+ reviewers?\b", clause):
        return ">="  # a bare count of a required number of reviewers
    return None


def _threshold(component: str, thr: dict[str, str], text: str) -> bool:
    """A clause that states a number with the unit is the threshold's clause; the
    value must be the schema's, so a changed number is not an attested `value` but
    still an attested `unit`, `quantity` and `comparator`."""
    value, unit, quantity = thr["value"], thr["unit"], thr["quantity"]
    for c in clauses(text):
        if not _numbers(c) or not any(f in c for f in UNIT_FORMS[unit]):
            continue
        if component == "value" and value in _numbers(c):
            return True
        if component == "unit":
            return True
        if component == "quantity" and any(cue in c for cue in QUANTITY_CUES[quantity]):
            return True
        if (
            component == "comparator"
            and read_comparator(c, quantity) == thr["comparator"]
        ):
            return True
    return False


def _modality(constraint_id: str, kind: str, modality: str, text: str) -> bool:
    for c in clauses(text):
        if not any(cue in c for cue in TOPIC_CUES[constraint_id]):
            continue
        read = read_modality(c)
        if read == modality:
            return True
        # section 8.5: only for conditional_permission, and only for `may`
        if (
            kind == "conditional_permission"
            and modality == "may"
            and CONDITIONAL_PERMISSION_EQUIVALENTS.search(c)
        ):
            return True
    return False


def _ordering(component: str, order: dict[str, str], text: str) -> bool:
    action = EVENT_CUES[order["action"]]
    after = EVENT_CUES[order["after"]]
    for c in clauses(text):
        a = min((c.find(x) for x in action if x in c), default=-1)
        b = min((c.find(x) for x in after if x in c), default=-1)
        if component == "action" and a >= 0:
            return True
        if component == "after" and b >= 0:
            return True
        if component == "after_edge" and a >= 0 and b >= 0:
            expr = AFTER_EXPRESSIONS.search(c)
            if expr and a < expr.start() < b:
                return True  # `action` ... after ... `after event`
            if a < b and re.search(r"\bfirst\b", c):
                return True  # `A first`: the event named last in front of `first`
            if b < a and expr and b < expr.start() < a:
                return False
    return False


def attested(
    template_id: str,
    component: str,
    constraint_id: str,
    kind: str,
    value: Any,
    text: str,
) -> bool:
    """Is the evidence of this component of this path in the text of the stage?"""
    if template_id == "T.condition":
        return any(value.lower() in c for c in clauses(text))
    if template_id == "T.scope":
        return any(value.lower() in c for c in clauses(text))
    if template_id == "T.modality":
        return _modality(constraint_id, kind, value, text)
    if template_id == "T.threshold":
        return _threshold(component, value, text)
    if template_id == "T.exception":
        for c in clauses(text):
            if value["exempt"] in c and (
                component == "exempt" or EXCEPTION_EXPRESSIONS.search(c)
            ):
                return True
        return False
    return _ordering(component, value, text)


def audit(doc: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """(stage, path label, component, expected status) for each P not attested."""
    kinds = {
        sc["constraint_id"]: sc["constraint_kind"]
        for sc in (
            doc["constraint_schema"]
            if isinstance(doc["constraint_schema"], list)
            else [doc["constraint_schema"]]
        )
    }
    missing = []
    for stage, key in STAGE_TEXT.items():
        for entry in doc["carry_evidence"][stage]:
            d = doc["path_definitions"][entry["property"]]
            for comp in entry["components"]:
                if comp["status"] != "P":
                    continue
                if not attested(
                    d["template_id"],
                    comp["name"],
                    d["constraint_id"],
                    kinds[d["constraint_id"]],
                    d["constraint_value"],
                    doc["texts"][key],
                ):
                    missing.append((stage, d["path_label"], comp["name"], "P"))
    return missing
