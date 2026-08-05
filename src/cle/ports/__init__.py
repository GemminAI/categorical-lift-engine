"""Structural ports to CLE's neighbours.

CLE imports no HEKB or NVS-Kernel code. `CommitSink` and
`ThreeViewRecoveryLike` are `typing.Protocol`s, so HEKB / NVS-Kernel (or a
test double) satisfy them by shape alone.
"""

from __future__ import annotations

from cle.ports.commit import CommitSink
from cle.ports.recovery import ThreeViewRecoveryLike

__all__ = ["CommitSink", "ThreeViewRecoveryLike"]
