"""`cle.api.app.create_app` — the production composition-root entrypoint.

`create_app` is the repair for the gap `docs/CLE_REPAIR_AUDIT.md` records:
there was no supported way, short of `app.dependency_overrides` (a test-only
FastAPI pattern), for a real deployment to hand `CLEEngine` a configured
`recovery_engine`/`hekb_store` before serving traffic. These tests exercise
`create_app` directly, standing in for that deployment.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import create_app

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


def test_create_app_with_no_arguments_matches_default_unconfigured_startup() -> None:
    """Priority F: default production startup must not silently succeed —
    calling `create_app()` with nothing configured is still a clean 503."""
    client = TestClient(create_app())
    response = client.post(
        "/recover",
        json={"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE},
    )
    assert response.status_code == 503
    assert "recovery_engine" in response.json()["detail"]


def test_create_app_with_a_recovery_engine_serves_a_valid_recover_response() -> None:
    client = TestClient(create_app(recovery_engine=_FakeRecoveryEngine()))
    response = client.post(
        "/recover",
        json={"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["converged"] is True
    assert body["recovered_state_id"].startswith("recovered:")
    assert body["reconstructed_closure"]["recovered_state"]
    assert isinstance(body["three_view_discrepancy"], float)


def test_create_app_recover_rejects_a_malformed_request() -> None:
    client = TestClient(create_app(recovery_engine=_FakeRecoveryEngine()))
    response = client.post("/recover", json={"subject": _SUBJECT})
    assert response.status_code == 422


def test_create_app_recover_is_deterministic_across_repeated_calls() -> None:
    client = TestClient(create_app(recovery_engine=_FakeRecoveryEngine()))
    payload = {"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE}
    responses = [client.post("/recover", json=payload).json() for _ in range(3)]
    assert responses[0] == responses[1] == responses[2]


def test_create_app_does_not_affect_the_default_module_level_app() -> None:
    """`create_app` must return an independent app, never mutate the shared
    default — the two entrypoints (dev/test vs. production composition)
    stay isolated from each other."""
    from cle.api.app import app as default_app

    configured_client = TestClient(create_app(recovery_engine=_FakeRecoveryEngine()))
    default_client = TestClient(default_app)

    payload = {"subject": _SUBJECT, "observer": _OBSERVER, "knowledge": _KNOWLEDGE}
    assert configured_client.post("/recover", json=payload).status_code == 200
    assert default_client.post("/recover", json=payload).status_code == 503
