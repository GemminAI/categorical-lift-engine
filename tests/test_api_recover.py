"""`POST /recover` — thin controller over `CLEEngine.recover`.

`CLEEngine.recover` needs a `recovery_engine`
(`cle.ports.recovery.ThreeViewRecoveryLike`) injected before it can do
anything — that Protocol's implementation is owned by whatever composes CLE
with NVS-Kernel, not by this API. The default `get_engine()` dependency has
none configured, so `/recover` is expected to report a clean 503 until a
caller overrides it — exactly as `docs/ARCHITECTURE.md`'s "fail loudly, not
fabricate" convention requires.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cle.api.app import app
from cle.api.router import get_engine
from cle.runtime.engine import CLEEngine

client = TestClient(app)

Vector = tuple[float, ...]

_SUBJECT = {"states": [{"theta": [1.0, 0.0]}]}
_OBSERVER = {"states": [{"theta": [0.0, 1.0]}]}
_KNOWLEDGE = {"states": [{"theta": [0.0, 0.0]}]}


class _FakeRecoveryEngine:
    """Structurally identical to nvs_kernel's ThreeViewTrajectoryRecovery."""

    def recover_state(
        self,
        current_x: Vector,
        x_subject: Vector,
        x_observer: Vector,
        x_human: Vector,
        *,
        steps: int = 20,
        lr: float = 0.05,
    ) -> Vector:
        weight = 1.0 / 3.0
        return tuple(
            weight * s + weight * o + weight * h
            for s, o, h in zip(x_subject, x_observer, x_human, strict=True)
        )

    def compute_recovery_gradient(
        self, current_x: Vector, x_subject: Vector, x_observer: Vector, x_human: Vector
    ) -> Vector:
        return tuple(0.0 for _ in current_x)


@pytest.fixture
def configured_recovery_engine() -> Iterator[None]:
    app.dependency_overrides[get_engine] = lambda: CLEEngine(
        recovery_engine=_FakeRecoveryEngine()
    )
    yield
    app.dependency_overrides.pop(get_engine, None)


def test_recover_without_a_configured_engine_is_a_503() -> None:
    response = client.post(
        "/recover",
        json={"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE},
    )
    assert response.status_code == 503
    assert "recovery_engine" in response.json()["detail"]


def test_recover_with_a_configured_engine_returns_a_recovered_context(
    configured_recovery_engine: None,
) -> None:
    response = client.post(
        "/recover",
        json={"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["converged"] is True
    assert body["recovered_state_id"].startswith("recovered:")
    assert body["reconstructed_closure"]["recovered_state"]
