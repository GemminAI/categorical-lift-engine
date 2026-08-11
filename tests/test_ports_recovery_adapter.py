"""`cle.ports.recovery.NumpyCoercingRecovery` — the CLE x NVS-Kernel adapter.

`docs/CLE_NVS_RECOVERY_INTEGRATION_AUDIT.md` records the concrete
incompatibility this fixes: `cle.runtime.engine._coordinates_of` produces
plain `tuple[float, ...]` vectors, but `nvs_kernel`'s `Manifold`
implementations call `.shape` on every vector argument to
`distance`/`log_map` — a bare tuple has no `.shape` and raises
`AttributeError`, confirmed against the real `nvs_kernel` package (not
reproduced here, since these tests must stay hermetic and not depend on a
sibling repository being present). `_ShapeRequiringRecovery` below is a
minimal, in-repo stand-in for that exact failure mode.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from cle.ports.recovery import NumpyCoercingRecovery, ThreeViewRecoveryLike

Vector = tuple[float, ...]


class _ShapeRequiringRecovery:
    """Mimics every `nvs_kernel.manifold.Manifold` implementation: every
    vector argument must be a `numpy.ndarray` (accesses `.shape`,
    `.dtype`-free arithmetic) or it raises `AttributeError`, not a domain
    error."""

    def recover_state(
        self,
        current_x: np.ndarray,
        x_subject: np.ndarray,
        x_observer: np.ndarray,
        x_human: np.ndarray,
        *,
        steps: int = 20,
        lr: float = 0.05,
    ) -> np.ndarray:
        for vector in (current_x, x_subject, x_observer, x_human):
            _ = vector.shape  # raises AttributeError on a plain tuple
        weight = 1.0 / 3.0
        return weight * x_subject + weight * x_observer + weight * x_human

    def compute_recovery_gradient(
        self,
        current_x: np.ndarray,
        x_subject: np.ndarray,
        x_observer: np.ndarray,
        x_human: np.ndarray,
    ) -> np.ndarray:
        for vector in (current_x, x_subject, x_observer, x_human):
            _ = vector.shape
        return np.zeros_like(current_x)


def test_numpy_coercing_recovery_satisfies_the_protocol() -> None:
    adapter = NumpyCoercingRecovery(_ShapeRequiringRecovery())
    assert isinstance(adapter, ThreeViewRecoveryLike)


def test_plain_tuples_crash_the_unwrapped_shape_requiring_engine() -> None:
    """Reproduces the exact incompatibility the adapter exists to fix."""
    engine = _ShapeRequiringRecovery()
    plain_tuple: Any = (1.0, 0.0)
    with pytest.raises(AttributeError, match="shape"):
        engine.recover_state(plain_tuple, plain_tuple, plain_tuple, plain_tuple)


def test_numpy_coercing_recovery_lets_cle_shaped_tuples_through() -> None:
    adapter = NumpyCoercingRecovery(_ShapeRequiringRecovery())
    result = adapter.recover_state((1.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, 0.0))
    assert np.allclose(result, (1.0 / 3.0, 1.0 / 3.0))


def test_numpy_coercing_recovery_gradient_also_coerces() -> None:
    adapter = NumpyCoercingRecovery(_ShapeRequiringRecovery())
    gradient = adapter.compute_recovery_gradient(
        (1.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, 0.0)
    )
    assert np.allclose(gradient, (0.0, 0.0))


def test_numpy_coercing_recovery_passes_through_arrays_unchanged() -> None:
    adapter = NumpyCoercingRecovery(_ShapeRequiringRecovery())
    array = np.array([1.0, 0.0])
    result = adapter.recover_state(array, array, array, array)
    assert np.allclose(result, array)


def test_numpy_coercing_recovery_forwards_steps_and_lr() -> None:
    calls: list[tuple[int, float]] = []

    class _RecordingEngine:
        def recover_state(
            self,
            current_x: np.ndarray,
            x_subject: np.ndarray,
            x_observer: np.ndarray,
            x_human: np.ndarray,
            *,
            steps: int = 20,
            lr: float = 0.05,
        ) -> np.ndarray:
            calls.append((steps, lr))
            return current_x

        def compute_recovery_gradient(
            self,
            current_x: np.ndarray,
            x_subject: np.ndarray,
            x_observer: np.ndarray,
            x_human: np.ndarray,
        ) -> np.ndarray:
            return current_x

    adapter = NumpyCoercingRecovery(_RecordingEngine())
    adapter.recover_state((0.0,), (0.0,), (0.0,), (0.0,), steps=7, lr=0.2)
    assert calls == [(7, 0.2)]
