"""Structural ports to CLE's one neighbour with a write direction: HEKB.

CLE imports no HEKB code. `CommitSink` is a `typing.Protocol`, so HEKB (or a
test double) satisfies it by shape alone.
"""

from __future__ import annotations

from cle.ports.commit import CommitSink

__all__ = ["CommitSink"]
