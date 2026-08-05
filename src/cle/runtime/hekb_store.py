"""HEKB persistence binding — CLE v3 spec §5/§5.1.

`HEKBStore` implements the spec's literal `store()` method against an
in-memory backing store and `InMemorySCHEngine.put_l7_closure` /
`put_l6_morphism` — a real, testable reference implementation of the
storage boundary the spec defines, not a network client to a real HEKB/SCH
service: no `HEKBStore`, `SCHEngine`, or equivalent exists anywhere in this
repository or its sibling repos (confirmed by search), so there is nothing
to bind to instead. `SCHEngineLike` is the swap-point a real backend later
satisfies structurally, the same Protocol convention `cle.abi.inputs`
already established for MSR/HEKB.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from cle.runtime.models import LiftResult


@runtime_checkable
class SCHEngineLike(Protocol):
    def put_l7_closure(
        self, *, key: str, closure: dict[str, Any], ttl_seconds: int
    ) -> None: ...

    def put_l6_morphism(self, *, key: str, pushout: dict[str, Any]) -> None: ...


@dataclass(slots=True)
class _SCHEntry:
    value: dict[str, Any]
    expires_at: float


@dataclass(slots=True)
class InMemorySCHEngine:
    """A minimal, real (not simulated) SCH L6/L7 cache: TTL'd dict storage."""

    _l7_closures: dict[str, _SCHEntry] = field(default_factory=dict)
    _l6_morphisms: dict[str, dict[str, Any]] = field(default_factory=dict)

    def put_l7_closure(
        self, *, key: str, closure: dict[str, Any], ttl_seconds: int
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        expires_at = time.monotonic() + ttl_seconds
        self._l7_closures[key] = _SCHEntry(value=closure, expires_at=expires_at)

    def put_l6_morphism(self, *, key: str, pushout: dict[str, Any]) -> None:
        self._l6_morphisms[key] = pushout

    def get_l7_closure(self, key: str) -> dict[str, Any] | None:
        entry = self._l7_closures.get(key)
        if entry is None or entry.expires_at < time.monotonic():
            return None
        return entry.value

    def get_l6_morphism(self, key: str) -> dict[str, Any] | None:
        return self._l6_morphisms.get(key)


@dataclass(slots=True)
class HEKBStore:
    """L4/L6 morphism + invariant persistence, plus SCH L6/L7 caching."""

    sch_engine: SCHEngineLike
    _morphisms: dict[str, frozenset[tuple[str, str, str]]] = field(default_factory=dict)
    _invariants: dict[str, Any] = field(default_factory=dict)

    def _write_morphisms(
        self, concept_id: str, morphisms: frozenset[tuple[str, str, str]]
    ) -> None:
        self._morphisms[concept_id] = morphisms

    def _write_invariants(self, concept_id: str, invariants: Any) -> None:
        self._invariants[concept_id] = invariants

    def store(self, lift_result: LiftResult) -> bool:
        """Persist `lift_result` to L4/L6 storage and the SCH L6/L7 cache."""
        self._write_morphisms(lift_result.concept_id, lift_result.morphisms)
        self._write_invariants(lift_result.concept_id, lift_result.invariants)

        self.sch_engine.put_l7_closure(
            key=lift_result.normalized_hash,
            closure=lift_result.semantic_closure,
            ttl_seconds=3600,
        )
        self.sch_engine.put_l6_morphism(
            key=lift_result.concept_id, pushout=lift_result.pushout_colimit
        )
        return True

    def morphisms_for(self, concept_id: str) -> frozenset[tuple[str, str, str]] | None:
        return self._morphisms.get(concept_id)

    def invariants_for(self, concept_id: str) -> Any | None:
        return self._invariants.get(concept_id)


__all__ = ["HEKBStore", "InMemorySCHEngine", "SCHEngineLike"]
