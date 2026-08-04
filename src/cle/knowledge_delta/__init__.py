"""Knowledge delta generation.

Owns describing a crystallized artifact as a `KnowledgeDelta` — the
audit/summary record `cle.commit_candidate` wraps into a
`HEKBCommitCandidate`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import KnowledgeDelta
from cle.crystallization import Artifact


@runtime_checkable
class KnowledgeDeltaGenerator(Protocol):
    """A crystallized artifact -> the `KnowledgeDelta` describing it."""

    def generate(self, artifact: Artifact) -> KnowledgeDelta: ...


__all__ = ["KnowledgeDeltaGenerator"]
