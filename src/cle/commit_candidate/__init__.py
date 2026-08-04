"""Commit-candidate building.

Owns turning a `KnowledgeDelta` into the `HEKBCommitCandidate` CLE hands to
whatever satisfies `cle.ports.CommitSink` — CLE's only outbound artifact,
and the only thing that ever crosses toward HEKB.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from cle.abi.outputs import (
    Category,
    CategoryRelation,
    Concept,
    ConceptDelta,
    HEKBCommitCandidate,
    KnowledgeDelta,
)
from cle.identity import deterministic_id


@runtime_checkable
class CommitCandidateBuilder(Protocol):
    """A `KnowledgeDelta` -> the `HEKBCommitCandidate` proposed to HEKB."""

    def build(
        self, delta: KnowledgeDelta, *, source_trajectory_id: str
    ) -> HEKBCommitCandidate: ...


def _saturating_confidence(evidence: float, half_life: float) -> float:
    """Monotonically increasing in `evidence`, bounded to `[0, 1)`.

    `evidence / (evidence + half_life)` — `half_life` is the amount of
    evidence at which confidence reaches exactly 0.5, a single named
    tuning knob rather than a magic constant. Strictly increasing for
    `evidence >= 0`, `half_life > 0` (derivative `half_life / (evidence +
    half_life) ** 2 > 0`), so more observable evidence always yields
    strictly higher confidence — never lower, never equal.
    """
    return evidence / (evidence + half_life)


@dataclass(frozen=True, slots=True)
class ObservationalCommitCandidateBuilder:
    """RFC-CLE003 Phase 3, Step 2 (confidence) + Step 4 (CommitCandidate).

    Confidence is estimated *only* from observable evidence already
    carried by the delta's payload — never a topological signal (Betti
    numbers have no ABI home yet, deliberately deferred, see
    `docs/RFC_ALIGNMENT.md`) and never anything HEKB-side:

    - `Concept` (newly discovered): evidence = `invariants["dwell_steps"]`
      — how long the trajectory dwelled before crystallizing into this
      concept.
    - `ConceptDelta` (reinforcement): evidence = `reinforcement_count` —
      how many times this concept has been reinforced.
    - `Category`: evidence = `len(concept_ids)` — how many concepts
      support this grouping.
    - `CategoryRelation`: confidence is exactly `1.0`, not evidence-scaled
      — a `CategoryRelation` only exists because a `FunctorConstructor`
      already *proved* the structure-preserving mapping holds (e.g.
      `CanonicalInclusionFunctorConstructor` raises `FunctorialityViolation`
      rather than construct one that doesn't), so its existence is a
      validated fact, not a confidence estimate over a volume of evidence.

    `created_at_ns` comes from an injectable `clock_ns` callable (default:
    `time.time_ns`) rather than a direct call, so the deterministic parts of
    this builder's output (`id`, `delta`, `confidence`, `provenance`) can be
    tested for "same input -> same output" independently of wall-clock
    time, which by definition varies from call to call and cannot be made
    deterministic without lying about when the candidate was built.

    `confidence_half_life` must be strictly positive — `_saturating_confidence`
    divides by it, and at `0.0` confidence stops depending on evidence at all
    (a positive evidence value always saturates to `1.0`) while `evidence=0.0`
    raises `ZeroDivisionError`; a negative value can push the result outside
    `HEKBCommitCandidate`'s own `[0, 1]` bound. Validated here, at
    construction, so a misconfigured builder fails immediately rather than
    on some later, unrelated `build()` call.
    """

    confidence_half_life: float = 5.0
    clock_ns: Callable[[], int] = field(default=time.time_ns)

    def __post_init__(self) -> None:
        if self.confidence_half_life <= 0:
            raise ValueError("confidence_half_life must be greater than zero")

    def build(
        self, delta: KnowledgeDelta, *, source_trajectory_id: str
    ) -> HEKBCommitCandidate:
        return HEKBCommitCandidate(
            id=deterministic_id("commit_candidate", delta.id, source_trajectory_id),
            delta=delta,
            confidence=self._confidence_for(delta),
            source_trajectory_id=source_trajectory_id,
            created_at_ns=self.clock_ns(),
            provenance=delta.provenance,
        )

    def _confidence_for(self, delta: KnowledgeDelta) -> float:
        payload = delta.payload
        if isinstance(payload, Concept):
            evidence = payload.invariants.get("dwell_steps", 0.0)
        elif isinstance(payload, ConceptDelta):
            evidence = float(payload.reinforcement_count)
        elif isinstance(payload, Category):
            evidence = float(len(payload.concept_ids))
        else:
            assert isinstance(payload, CategoryRelation)
            return 1.0
        return _saturating_confidence(max(0.0, evidence), self.confidence_half_life)


__all__ = ["CommitCandidateBuilder", "ObservationalCommitCandidateBuilder"]
