"""Data classes of the EXP-RAG-CTP001 fixture builder (constraint types C1-C6).

`ctp001_types.py` holds the data (the six types and their 14 examples each),
`ctp001_builder.py` turns an `Example` of a `ConstraintType` into the fixture
document. Nothing here knows a particular type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConstraintType:
    """One constraint type: its schema(s), vocabulary and the knowledge text."""

    cid: str  # "c1" ... "c6"; also the prefix of the type's properties
    schemas: tuple[dict[str, Any], ...]  # one Constraint Schema; C6 holds two
    props: tuple[str, ...]  # `<constraint_id>.<field>` of every non-null field
    knowledge: str
    exclusion_reasons: dict[str, str]  # why a constraint is left out of O (N0)

    def __post_init__(self) -> None:
        # the vocabulary stores its properties sorted; keep one order everywhere
        if tuple(sorted(self.props)) != self.props:
            raise ValueError(f"{self.cid}: props must be listed in sorted order")

    @property
    def label(self) -> str:
        return self.cid.upper()

    @property
    def constraint_ids(self) -> tuple[str, ...]:
        return tuple(s["constraint_id"] for s in self.schemas)


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
    # per constraint, when a type holds more than one (C6); otherwise the
    # single `context_applicability` applies to the type's one constraint
    applicabilities: dict[str, str] | None = None
    declared: tuple[frozenset[str], frozenset[str], frozenset[str]] | None = None
    claim_preserved_composites: bool = False
