"""The CLE output ABI: the frozen knowledge artifacts CLE produces.

Six types, one direction — CLE always produces, never consumes, these:

=========================  ================================================
:class:`Concept`            A newly discovered, previously unknown concept
:class:`ConceptDelta`       An update to an existing HEKB concept
:class:`Category`           A grouping of concepts into a categorical structure
:class:`CategoryRelation`   A morphism between two categories
:class:`KnowledgeDelta`     A description of what changed, independent of commit
:class:`HEKBCommitCandidate`  The proposal CLE hands to HEKB — never a direct write
=========================  ================================================

All six are frozen and hold only plain Python scalars/tuples/dicts, matching
the convention `msr.abi` establishes for the neighbouring runtime: once
emitted, a value can never be retroactively changed, and it can be
serialized without touching numpy.

`Concept` is deliberately shaped to satisfy `msr.adapters.hekb.ConceptLike`
(`.id`, `.centroid`, optionally `.hessian`/`.invariants`) by structure, so a
`Concept` CLE commits into HEKB can, once round-tripped, become a field-prior
well for MSR again — without CLE importing `msr` or HEKB importing CLE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class Concept:
    """A newly crystallized concept: knowledge that did not exist before.

    Produced only from a novel stabilization (`StabilizedTrajectoryLike.is_novel`
    is `True`) — a trajectory that stabilized inside an already-known basin is
    reinforcement of existing knowledge, and belongs in a `ConceptDelta`
    instead, not a new `Concept`.
    """

    id: str
    frame_id: str
    centroid: Vector
    hessian: Matrix | None
    invariants: dict[str, float] = field(default_factory=dict)
    source_trajectory_id: str = ""
    provenance: tuple[str, ...] = ()

    @property
    def dimension(self) -> int:
        return len(self.centroid)


@dataclass(frozen=True, slots=True)
class ConceptDelta:
    """An update to a concept that already exists in HEKB.

    Produced when a stabilization lands inside a basin HEKB already
    recognizes (`StabilizedTrajectoryLike.basin_id` matches a known concept):
    the trajectory is evidence reinforcing or refining that concept, not a
    new one.
    """

    concept_id: str
    frame_id: str
    centroid_shift: Vector | None
    updated_invariants: dict[str, float] = field(default_factory=dict)
    reinforcement_count: int = 1
    source_trajectory_id: str = ""
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Category:
    """A categorical grouping of concepts: a structure over knowledge, not knowledge.

    `concept_ids` references `Concept.id`/`ConceptDelta.concept_id` values by
    id — `Category` does not embed the concepts it groups, so a category
    remains valid as the concepts it references evolve.
    """

    id: str
    label: str | None
    concept_ids: tuple[str, ...]
    structure_kind: str
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.concept_ids:
            raise ValueError("Category must reference at least one concept_id")


class MorphismType(StrEnum):
    """The categorical-theory construction a `ConceptMorphism` witnesses.

    Added for RFC-CLE001 Phase 1 (Functorial Lift Engine): mirrors
    `RFC-CLE002` §2.1's `MorphismType` enum value-for-value, so a future
    C-FFI/Arrow boundary (RFC-CLE002 §4) can serialize this field without
    translation. Phase 1 (`cle.morphism`) only ever produces `IDENTITY` and
    `INCLUSION`; the remaining three members are reserved for later phases
    (`HOMOTOPIC_EQUIVALENCE` — Phase 2 HPIA, `PULLBACK_CANONICAL` /
    `PUSHOUT_CANONICAL` — Phase 4 CET) and are not yet constructed anywhere.
    See `docs/RFC_ALIGNMENT.md`.
    """

    IDENTITY = "identity"
    INCLUSION = "inclusion"
    HOMOTOPIC_EQUIVALENCE = "homotopic_equivalence"
    PULLBACK_CANONICAL = "pullback_canonical"
    PUSHOUT_CANONICAL = "pushout_canonical"


@dataclass(frozen=True, slots=True)
class ConceptMorphism:
    """A morphism between two concepts, discovered during a single Functorial Lift.

    Added for RFC-CLE001 Phase 1: the existing output ABI had no type for a
    morphism *within* one lift's object structure — `CategoryRelation` is
    scoped to morphisms *between* two `Category` values instead (see its
    docstring). `ConceptMorphism` fills that gap additively; it does not
    replace or narrow `CategoryRelation`. See `docs/RFC_ALIGNMENT.md`.
    """

    morphism_id: str
    source_id: str
    target_id: str
    morphism_type: MorphismType
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CategoryRelation:
    """A morphism between two categories: functor, natural transformation, or inclusion.

    `relation_kind` names the categorical-theory construction that produced
    this relation (e.g. ``"functor"``, ``"natural_transformation"``,
    ``"inclusion"``) — the construction itself is owned by `cle.functor` /
    `cle.natural_transformation`; this is only the resulting frozen edge.
    """

    id: str
    source_category_id: str
    target_category_id: str
    relation_kind: str
    provenance: tuple[str, ...] = ()


class KnowledgeDeltaKind(StrEnum):
    """What kind of change a `KnowledgeDelta` describes."""

    CONCEPT_CREATED = "concept_created"
    CONCEPT_UPDATED = "concept_updated"
    CATEGORY_FORMED = "category_formed"
    CATEGORY_RELATED = "category_related"


@dataclass(frozen=True, slots=True)
class KnowledgeDelta:
    """A description of what changed in the knowledge graph, independent of commit.

    `KnowledgeDelta` is an audit/summary record — exactly one of `concept`,
    `concept_delta`, `category`, `category_relation` is populated, matching
    `kind`. It exists so "what changed" can be inspected, logged, or
    replayed without depending on whether HEKB ultimately accepted the
    corresponding `HEKBCommitCandidate`.
    """

    id: str
    kind: KnowledgeDeltaKind
    concept: Concept | None = None
    concept_delta: ConceptDelta | None = None
    category: Category | None = None
    category_relation: CategoryRelation | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        payload_by_kind: dict[KnowledgeDeltaKind, object | None] = {
            KnowledgeDeltaKind.CONCEPT_CREATED: self.concept,
            KnowledgeDeltaKind.CONCEPT_UPDATED: self.concept_delta,
            KnowledgeDeltaKind.CATEGORY_FORMED: self.category,
            KnowledgeDeltaKind.CATEGORY_RELATED: self.category_relation,
        }
        all_payloads = (
            self.concept,
            self.concept_delta,
            self.category,
            self.category_relation,
        )
        populated = [payload for payload in all_payloads if payload is not None]
        if len(populated) != 1:
            raise ValueError(
                "KnowledgeDelta must populate exactly one of "
                "concept/concept_delta/category/category_relation"
            )
        if payload_by_kind[self.kind] is None:
            raise ValueError(
                f"KnowledgeDelta.kind={self.kind!r} does not match its payload"
            )

    @property
    def payload(self) -> Concept | ConceptDelta | Category | CategoryRelation:
        """The single populated artifact, regardless of which field it lives in."""
        for candidate in (
            self.concept,
            self.concept_delta,
            self.category,
            self.category_relation,
        ):
            if candidate is not None:
                return candidate
        raise AssertionError("unreachable: __post_init__ guarantees one payload")


@dataclass(frozen=True, slots=True)
class HEKBCommitCandidate:
    """The proposal CLE hands to HEKB. CLE never writes directly into HEKB.

    A `HEKBCommitCandidate` is a request, not a fact: HEKB — and only HEKB —
    decides whether to accept it, per `RFC-HEKB00`'s Principle 3 (Provenance)
    and Principle 9 (Knowledge Promotion Shall Be Monotonic). `confidence` is
    CLE's own estimate and does not bind HEKB's acceptance decision.
    """

    id: str
    delta: KnowledgeDelta
    confidence: float
    source_trajectory_id: str
    created_at_ns: int
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0.0, 1.0]")


__all__ = [
    "Category",
    "CategoryRelation",
    "Concept",
    "ConceptDelta",
    "ConceptMorphism",
    "HEKBCommitCandidate",
    "KnowledgeDelta",
    "KnowledgeDeltaKind",
    "Matrix",
    "MorphismType",
    "Vector",
]
