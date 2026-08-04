"""The one outbound port CLE has: submitting a commit candidate to HEKB.

CLE never writes directly into HEKB — it produces `HEKBCommitCandidate`
values and hands them to whatever satisfies `CommitSink`. HEKB — and only
HEKB — decides whether to accept, reject, or hold a candidate; that decision
is out of scope for this repository.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cle.abi.outputs import HEKBCommitCandidate


@runtime_checkable
class CommitSink(Protocol):
    """CLE → HEKB: the sole outbound crossing, once per commit candidate."""

    def submit(self, candidate: HEKBCommitCandidate) -> None: ...


__all__ = ["CommitSink"]
