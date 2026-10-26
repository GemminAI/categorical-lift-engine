"""R0a: the CLE v0.3 section 2 data model and the section 4 result type.

Plain frozen dataclasses. Nothing here touches `cle.abi`, `FiniteCategory` or
`Functor`. Every type has ``to_dict`` (canonical-JSON-safe: ints and strings
only, no floats) and ``from_dict``; ``compute_id`` / ``compute_hash`` give the
content-addressed IDs of section 2.1 (sha256 of the canonical JSON, with the
type's own ID field left out).

Sets (``preserved``, ``lost``) and collections whose order the recorder does
not control (states, morphisms, compositions, branches) are sorted in
``to_dict`` so the same content always hashes to the same ID.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal, get_args

from cle.errors import CLEError
from cle.representation.canonical import sha256_hex

RefKind = Literal["hext", "checker_output", "theorem_name", "history"]
SealStatus = Literal["SEAL_OK", "SEAL_FAIL"]
Validity = Literal["UNCHECKED", "CHECKED_BY_TOOL", "CHECKED_BY_HUMAN", "REFUTED"]
Role = Literal["generator", "identity", "composite", "inverse_claim"]
Source = Literal["model", "human", "verifier", "unknown"]
Verification = Literal["UNVERIFIED", "VERIFIED", "REFUTED"]
Claim = Literal["invertible", "not_invertible", "unknown"]
Basis = Literal["declared", "recomputed"]
Status = Literal["PASS", "FAIL", "UNVERIFIABLE"]
RuleId = Literal["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
LocationKind = Literal["state", "morphism", "composition", "field"]


class RepresentationError(CLEError, ValueError):
    """An ill-formed representation record or `CheckResult`."""


def _require(value: object, allowed: tuple[Any, ...], what: str) -> None:
    if value not in allowed:
        raise RepresentationError(f"{what}: {value!r} is not one of {allowed}")


def _opt_ref(data: Mapping[str, Any] | None) -> Ref | None:
    return None if data is None else Ref.from_dict(data)


@dataclass(frozen=True, slots=True)
class Ref:
    """A typed reference (section 2.2).

    ``value`` is the state_hash (hext), the output_sha256 (checker_output), a
    name (theorem_name) or the history_hash (history). ``name``/``version``
    carry checker_name/checker_version, or the history_id for kind "history".
    ``seal_status`` and ``validity`` are read, never computed (C4-3).
    """

    kind: RefKind
    value: str
    seal_status: SealStatus | None = None
    validity: Validity | None = None
    name: str | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        _require(self.kind, get_args(RefKind), "Ref.kind")
        if self.seal_status is not None:
            _require(self.seal_status, get_args(SealStatus), "Ref.seal_status")
        if self.validity is not None:
            _require(self.validity, get_args(Validity), "Ref.validity")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "seal_status": self.seal_status,
            "validity": self.validity,
            "name": self.name,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Ref:
        return cls(
            kind=data["kind"],
            value=data["value"],
            seal_status=data.get("seal_status"),
            validity=data.get("validity"),
            name=data.get("name"),
            version=data.get("version"),
        )


@dataclass(frozen=True, slots=True)
class Span:
    session_id: str
    p_start: int
    p_end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "p_start": self.p_start,
            "p_end": self.p_end,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Span:
        return cls(data["session_id"], data["p_start"], data["p_end"])


@dataclass(frozen=True, slots=True)
class RepresentationState:
    state_id: str
    history_id: str
    kind: str
    description: str = ""
    span: Span | None = None
    source: Source = "unknown"
    verification: Verification = "UNVERIFIED"

    def __post_init__(self) -> None:
        _require(self.source, get_args(Source), "RepresentationState.source")
        _require(
            self.verification,
            get_args(Verification),
            "RepresentationState.verification",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "history_id": self.history_id,
            "kind": self.kind,
            "description": self.description,
            "span": None if self.span is None else self.span.to_dict(),
            "source": self.source,
            "verification": self.verification,
        }

    def compute_id(self) -> str:
        content = self.to_dict()
        del content["state_id"]
        return sha256_hex(content)

    def with_id(self) -> RepresentationState:
        return replace(self, state_id=self.compute_id())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepresentationState:
        span = data.get("span")
        return cls(
            state_id=data["state_id"],
            history_id=data["history_id"],
            kind=data["kind"],
            description=data.get("description", ""),
            span=None if span is None else Span.from_dict(span),
            source=data.get("source", "unknown"),
            verification=data.get("verification", "UNVERIFIED"),
        )


@dataclass(frozen=True, slots=True)
class Invertibility:
    claim: Claim = "unknown"
    inverse_morphism_id: str | None = None

    def __post_init__(self) -> None:
        _require(self.claim, get_args(Claim), "Invertibility.claim")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "inverse_morphism_id": self.inverse_morphism_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Invertibility:
        return cls(data.get("claim", "unknown"), data.get("inverse_morphism_id"))


@dataclass(frozen=True, slots=True)
class RepresentationMorphism:
    """A morphism (section 2.3).

    ``rule_text`` is for human readers and is never used by a check.
    ``carry`` maps a property name at the source to one at the target;
    ``None`` means "not recorded" (R3 -> CARRY_MISSING).
    """

    morphism_id: str
    source_state_id: str
    target_state_id: str
    role: Role = "generator"
    rule_ref: Ref | None = None
    rule_text: str = ""
    preserved: tuple[str, ...] = ()
    lost: tuple[str, ...] = ()
    carry: Mapping[str, str] | None = None
    evidence: tuple[Ref, ...] = ()
    invertibility: Invertibility = field(default_factory=Invertibility)
    source: Source = "unknown"
    verification: Verification = "UNVERIFIED"

    def __post_init__(self) -> None:
        _require(self.role, get_args(Role), "RepresentationMorphism.role")
        _require(self.source, get_args(Source), "RepresentationMorphism.source")
        _require(
            self.verification,
            get_args(Verification),
            "RepresentationMorphism.verification",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "morphism_id": self.morphism_id,
            "source_state_id": self.source_state_id,
            "target_state_id": self.target_state_id,
            "role": self.role,
            "rule_ref": None if self.rule_ref is None else self.rule_ref.to_dict(),
            "rule_text": self.rule_text,
            "preserved": sorted(self.preserved),
            "lost": sorted(self.lost),
            "carry": None if self.carry is None else dict(self.carry),
            "evidence": [ref.to_dict() for ref in self.evidence],
            "invertibility": self.invertibility.to_dict(),
            "source": self.source,
            "verification": self.verification,
        }

    def compute_id(self) -> str:
        content = self.to_dict()
        del content["morphism_id"]
        return sha256_hex(content)

    def with_id(self) -> RepresentationMorphism:
        return replace(self, morphism_id=self.compute_id())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepresentationMorphism:
        carry = data.get("carry")
        return cls(
            morphism_id=data["morphism_id"],
            source_state_id=data["source_state_id"],
            target_state_id=data["target_state_id"],
            role=data.get("role", "generator"),
            rule_ref=_opt_ref(data.get("rule_ref")),
            rule_text=data.get("rule_text", ""),
            preserved=tuple(data.get("preserved", ())),
            lost=tuple(data.get("lost", ())),
            carry=None if carry is None else dict(carry),
            evidence=tuple(Ref.from_dict(r) for r in data.get("evidence", ())),
            invertibility=Invertibility.from_dict(data.get("invertibility", {})),
            source=data.get("source", "unknown"),
            verification=data.get("verification", "UNVERIFIED"),
        )


@dataclass(frozen=True, slots=True)
class Composition:
    """``result`` = ``second`` after ``first`` (f: A->B, g: B->C, h: A->C)."""

    first: str
    second: str
    result: str
    basis: Basis = "declared"
    evidence: tuple[Ref, ...] = ()
    source: Source = "unknown"

    def __post_init__(self) -> None:
        _require(self.basis, get_args(Basis), "Composition.basis")
        _require(self.source, get_args(Source), "Composition.source")

    def to_dict(self) -> dict[str, Any]:
        return {
            "first": self.first,
            "second": self.second,
            "result": self.result,
            "basis": self.basis,
            "evidence": [ref.to_dict() for ref in self.evidence],
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Composition:
        return cls(
            first=data["first"],
            second=data["second"],
            result=data["result"],
            basis=data.get("basis", "declared"),
            evidence=tuple(Ref.from_dict(r) for r in data.get("evidence", ())),
            source=data.get("source", "unknown"),
        )


@dataclass(frozen=True, slots=True)
class PropertyVocabulary:
    vocabulary_id: str
    version: str
    task_ref: str
    properties: tuple[str, ...]
    information: tuple[str, ...]
    ref: Ref

    def to_dict(self) -> dict[str, Any]:
        return {
            "vocabulary_id": self.vocabulary_id,
            "version": self.version,
            "task_ref": self.task_ref,
            "properties": sorted(self.properties),
            "information": sorted(self.information),
            "ref": self.ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PropertyVocabulary:
        return cls(
            vocabulary_id=data["vocabulary_id"],
            version=data["version"],
            task_ref=data["task_ref"],
            properties=tuple(data["properties"]),
            information=tuple(data["information"]),
            ref=Ref.from_dict(data["ref"]),
        )


@dataclass(frozen=True, slots=True)
class AbandonedBranch:
    """A branch that was not taken (v0.4 D-25).

    Shape: ``{branch_id, state_ids[], morphism_ids[]}``. The ids let R6 see a
    branch shrink, which an id-only form could not.
    """

    branch_id: str
    state_ids: tuple[str, ...] = ()
    morphism_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "state_ids": sorted(self.state_ids),
            "morphism_ids": sorted(self.morphism_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AbandonedBranch:
        return cls(
            data["branch_id"],
            tuple(data.get("state_ids", ())),
            tuple(data.get("morphism_ids", ())),
        )


@dataclass(frozen=True, slots=True)
class RepresentationHistory:
    history_id: str
    task_ref: str
    vocabulary_ref: Ref
    states: tuple[RepresentationState, ...] = ()
    morphisms: tuple[RepresentationMorphism, ...] = ()
    compositions: tuple[Composition, ...] = ()
    abandoned_branches: tuple[AbandonedBranch, ...] = ()
    prev_history_hash: str | None = None
    history_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "task_ref": self.task_ref,
            "vocabulary_ref": self.vocabulary_ref.to_dict(),
            "states": [
                s.to_dict() for s in sorted(self.states, key=lambda s: s.state_id)
            ],
            "morphisms": [
                m.to_dict() for m in sorted(self.morphisms, key=lambda m: m.morphism_id)
            ],
            "compositions": [
                c.to_dict()
                for c in sorted(
                    self.compositions, key=lambda c: (c.first, c.second, c.result)
                )
            ],
            "abandoned_branches": [
                b.to_dict()
                for b in sorted(self.abandoned_branches, key=lambda b: b.branch_id)
            ],
            "prev_history_hash": self.prev_history_hash,
            "history_hash": self.history_hash,
        }

    def compute_hash(self) -> str:
        """sha256 of the canonical JSON with ``history_hash`` itself left out."""
        content = self.to_dict()
        del content["history_hash"]
        return sha256_hex(content)

    def seal(self) -> RepresentationHistory:
        return replace(self, history_hash=self.compute_hash())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RepresentationHistory:
        return cls(
            history_id=data["history_id"],
            task_ref=data["task_ref"],
            vocabulary_ref=Ref.from_dict(data["vocabulary_ref"]),
            states=tuple(RepresentationState.from_dict(s) for s in data["states"]),
            morphisms=tuple(
                RepresentationMorphism.from_dict(m) for m in data["morphisms"]
            ),
            compositions=tuple(
                Composition.from_dict(c) for c in data.get("compositions", ())
            ),
            abandoned_branches=tuple(
                AbandonedBranch.from_dict(b) for b in data.get("abandoned_branches", ())
            ),
            prev_history_hash=data.get("prev_history_hash"),
            history_hash=data.get("history_hash", ""),
        )


@dataclass(frozen=True, slots=True)
class Location:
    kind: LocationKind
    id: str
    field: str | None = None

    def __post_init__(self) -> None:
        _require(self.kind, get_args(LocationKind), "Location.kind")

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "id": self.id, "field": self.field}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Location:
        return cls(data["kind"], data["id"], data.get("field"))


@dataclass(frozen=True, slots=True)
class CheckerInfo:
    name: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True, slots=True)
class CheckWarning:
    """A finding that does not change a rule's status (v0.4 D-14)."""

    reason_code: str
    location: Location

    def to_dict(self) -> dict[str, Any]:
        return {"reason_code": self.reason_code, "location": self.location.to_dict()}


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One check outcome (section 4).

    FAIL and UNVERIFIABLE must carry a reason code and at least one location;
    constructing one without raises `RepresentationError`. PASS carries
    neither.
    """

    rule: RuleId
    status: Status
    reason_code: str | None
    locations: tuple[Location, ...]
    inputs_sha256: str
    checker: CheckerInfo
    warnings: tuple[CheckWarning, ...] = ()

    def __post_init__(self) -> None:
        _require(self.rule, get_args(RuleId), "CheckResult.rule")
        _require(self.status, get_args(Status), "CheckResult.status")
        if self.status == "PASS":
            if self.reason_code is not None:
                raise RepresentationError("a PASS result must not carry a reason_code")
        elif not self.reason_code or not self.locations:
            raise RepresentationError(
                f"{self.status} requires a reason_code and at least one location"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "status": self.status,
            "reason_code": self.reason_code,
            "locations": [loc.to_dict() for loc in self.locations],
            "inputs_sha256": self.inputs_sha256,
            "checker": self.checker.to_dict(),
            "warnings": [w.to_dict() for w in self.warnings],
        }


def aggregate(results: Sequence[CheckResult]) -> Status:
    """Section 4: any FAIL -> FAIL; else any UNVERIFIABLE -> UNVERIFIABLE; else PASS.

    UNVERIFIABLE is never counted as PASS. Only the rules present in
    ``results`` are considered.
    """
    statuses = {r.status for r in results}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNVERIFIABLE" in statuses:
        return "UNVERIFIABLE"
    return "PASS"


__all__ = [
    "AbandonedBranch",
    "CheckResult",
    "CheckWarning",
    "CheckerInfo",
    "Composition",
    "Invertibility",
    "Location",
    "PropertyVocabulary",
    "Ref",
    "RepresentationError",
    "RepresentationHistory",
    "RepresentationMorphism",
    "RepresentationState",
    "Span",
    "aggregate",
]
