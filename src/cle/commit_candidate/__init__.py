"""Commit-candidate building.

Owns turning a `KnowledgeDelta` into the `HEKBCommitCandidate` CLE hands to
whatever satisfies `cle.ports.CommitSink` — CLE's only outbound artifact,
and the only thing that ever crosses toward HEKB.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import HEKBCommitCandidate, KnowledgeDelta


@runtime_checkable
class CommitCandidateBuilder(Protocol):
    """A `KnowledgeDelta` -> the `HEKBCommitCandidate` proposed to HEKB."""

    def build(
        self, delta: KnowledgeDelta, *, source_trajectory_id: str
    ) -> HEKBCommitCandidate: ...


__all__ = ["CommitCandidateBuilder"]
