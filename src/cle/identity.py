"""Deterministic, content-addressed identifiers.

RFC-CLE001 §7 and RFC-CLE005 §3.2 both require that lifting the same input
twice produce byte-identical object and morphism ids (`test_property_lift_determinism`).
Every id minted anywhere in CLE derives only from the semantic content being
identified — never from wall-clock time or a random UUID — so replay and
idempotency hold by construction, not by convention.
"""

from __future__ import annotations

import hashlib


def deterministic_id(prefix: str, *parts: object) -> str:
    """A stable id for `parts`, prefixed for readability (e.g. ``"concept:..."``).

    Two calls with equal `prefix` and equal `parts` (by `repr`) always return
    the same string, in any process, on any run.
    """
    canonical = "|".join(repr(part) for part in parts)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest[:24]}"


__all__ = ["deterministic_id"]
