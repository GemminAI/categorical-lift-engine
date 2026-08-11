"""Outbound port CLE v3's `CLEEngine.recover()` uses to reach NVS-Kernel physics.

CLE has no dependency on `nvs_kernel` — the same convention `cle.abi.inputs`
already establishes for MSR/HEKB: a Protocol shape, not a shared class, so
`nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery`
satisfies this Protocol structurally without CLE importing `nvs_kernel`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class ThreeViewRecoveryLike(Protocol):
    """Structurally identical to
    `nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery`.
    """

    def recover_state(
        self,
        current_x: Any,
        x_subject: Any,
        x_observer: Any,
        x_human: Any,
        *,
        steps: int = 20,
        lr: float = 0.05,
    ) -> Any: ...

    def compute_recovery_gradient(
        self, current_x: Any, x_subject: Any, x_observer: Any, x_human: Any
    ) -> Any: ...


def _as_ndarray(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value
    return np.asarray(value, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class NumpyCoercingRecovery:
    """`ThreeViewRecoveryLike` adapter: coerces every vector argument to a
    `numpy.ndarray` before delegating to `inner`.

    `ThreeViewRecoveryLike` types every vector `Any` on purpose — CLE holds
    no opinion on vector representation (`cle.runtime.engine._coordinates_of`
    produces plain `tuple[float, ...]`). A concrete implementation is free to
    assume `numpy.ndarray` specifically, and at least one confirmed real one
    does: every `nvs_kernel.manifold.Manifold` implementation calls `.shape`
    on both arguments of `distance`/`log_map`, so hand it a plain tuple and
    it fails with `AttributeError: 'tuple' object has no attribute 'shape'`
    — not a domain error, an implementation detail leaking through the port.
    Wrap any `ThreeViewRecoveryLike` in this first, and CLE can keep handing
    it whatever vector shape it already has.
    """

    inner: ThreeViewRecoveryLike

    def recover_state(
        self,
        current_x: Any,
        x_subject: Any,
        x_observer: Any,
        x_human: Any,
        *,
        steps: int = 20,
        lr: float = 0.05,
    ) -> Any:
        return self.inner.recover_state(
            _as_ndarray(current_x),
            _as_ndarray(x_subject),
            _as_ndarray(x_observer),
            _as_ndarray(x_human),
            steps=steps,
            lr=lr,
        )

    def compute_recovery_gradient(
        self, current_x: Any, x_subject: Any, x_observer: Any, x_human: Any
    ) -> Any:
        return self.inner.compute_recovery_gradient(
            _as_ndarray(current_x),
            _as_ndarray(x_subject),
            _as_ndarray(x_observer),
            _as_ndarray(x_human),
        )


__all__ = ["NumpyCoercingRecovery", "ThreeViewRecoveryLike"]
