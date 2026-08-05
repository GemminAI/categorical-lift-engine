"""Outbound port CLE v3's `CLEEngine.recover()` uses to reach NVS-Kernel physics.

CLE has no dependency on `nvs_kernel` — the same convention `cle.abi.inputs`
already establishes for MSR/HEKB: a Protocol shape, not a shared class, so
`nvs_kernel.nvs_kernel_physics.recovery.ThreeViewTrajectoryRecovery`
satisfies this Protocol structurally without CLE importing `nvs_kernel`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


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


__all__ = ["ThreeViewRecoveryLike"]
