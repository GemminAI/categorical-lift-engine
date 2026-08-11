"""5W1H extraction from a Prompt/Goal.

Deterministic and explainable: every field is either (a) taken verbatim
from an explicit caller-supplied override, or (b) derived by a disclosed,
simple rule from prompt/goal text, or (c) marked "unspecified" -- never
guessed.

Relocated verbatim from `cognitive-port-selector`'s `cps.grounding.five_w1h`
(2026-08-12 CLE-rebuild directive) -- same logic, moved rather than
duplicated, since CPS no longer owns Semantic Grounding.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

Source = Literal["explicit", "derived", "unspecified"]

_TIME_PATTERN = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{4}年\d{1,2}月\d{1,2}日|today|now|今|本日|現在)\b",
    re.IGNORECASE,
)
_LOCATION_PATTERN = re.compile(
    r"\b(at|in|de|於|にて|で)\s+([A-Za-z0-9_\-]+)", re.IGNORECASE
)


class FiveW1HField(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    source: Source


class FiveW1HOverrides(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    who: str | None = None
    what: str | None = None
    when: str | None = None
    where: str | None = None
    why: str | None = None
    how: str | None = None


class FiveW1H(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    who: FiveW1HField
    what: FiveW1HField
    when: FiveW1HField
    where: FiveW1HField
    why: FiveW1HField
    how: FiveW1HField


def _field(explicit: str | None, derived: str | None) -> FiveW1HField:
    if explicit is not None and explicit.strip():
        return FiveW1HField(value=explicit.strip(), source="explicit")
    if derived is not None and derived.strip():
        return FiveW1HField(value=derived.strip(), source="derived")
    return FiveW1HField(value="unspecified", source="unspecified")


def extract_five_w1h(
    prompt: str,
    goal: str,
    overrides: FiveW1HOverrides | None = None,
) -> FiveW1H:
    overrides = overrides or FiveW1HOverrides()

    when_match = _TIME_PATTERN.search(prompt) or _TIME_PATTERN.search(goal)
    derived_when = when_match.group(0) if when_match else None

    where_match = _LOCATION_PATTERN.search(prompt) or _LOCATION_PATTERN.search(goal)
    derived_where = where_match.group(2) if where_match else None

    # "what" derives from the Goal (the stated objective); "why" derives
    # from the Prompt's own text as the disclosed rationale, since no
    # separate rationale channel exists in the request. "how" derives
    # from the Prompt's leading clause up to the first sentence break.
    derived_what = goal.strip() if goal.strip() else None
    derived_why = prompt.strip() if prompt.strip() else None
    first_sentence = re.split(r"[。.!?\n]", prompt.strip(), maxsplit=1)[0].strip()
    derived_how = first_sentence if first_sentence else None

    return FiveW1H(
        who=_field(overrides.who, None),
        what=_field(overrides.what, derived_what),
        when=_field(overrides.when, derived_when),
        where=_field(overrides.where, derived_where),
        why=_field(overrides.why, derived_why),
        how=_field(overrides.how, derived_how),
    )


__all__ = ["FiveW1H", "FiveW1HField", "FiveW1HOverrides", "Source", "extract_five_w1h"]
