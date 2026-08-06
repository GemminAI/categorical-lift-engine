"""`POST /lift` — thin controller over `cle.runtime.engine.CLEEngine.lift`."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import app

client = TestClient(app)

_TRIANGLE = {
    "states": [
        {"theta": [0.0, 0.0]},
        {"theta": [1.0, 0.0]},
        {"theta": [0.5, 0.9]},
    ]
}
_EDGE = {"states": [{"theta": [0.0, 0.0]}, {"theta": [1.0, 0.0]}]}


def test_lift_without_views_returns_a_valid_result() -> None:
    response = client.post("/lift", json={"concept": _TRIANGLE})
    assert response.status_code == 200
    body = response.json()
    assert body["invariants"] == {
        "betti_0": 1,
        "betti_1": 0,
        "betti_2": 0,
        "euler_characteristic": 1,
    }
    assert body["proof"]["is_valid"] is True
    assert body["pullback_limit"] == {"morphisms": []}


def test_lift_with_three_views_uses_pullback_and_pushout() -> None:
    response = client.post(
        "/lift",
        json={
            "concept": _TRIANGLE,
            "subject_context": _EDGE,
            "observer_context": _EDGE,
            "human_knowledge_context": _EDGE,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pullback_limit"]["morphisms"]
    assert body["pushout_colimit"]["objects"] == ["v0", "v1"]


def test_lift_is_deterministic_for_the_same_concept() -> None:
    first = client.post("/lift", json={"concept": _TRIANGLE}).json()
    second = client.post("/lift", json={"concept": _TRIANGLE}).json()
    assert first["concept_id"] == second["concept_id"]
    assert first["normalized_hash"] == second["normalized_hash"]


def test_lift_with_mismatched_dimensions_is_a_422() -> None:
    bad_concept = {
        "states": [{"theta": [0.0, 0.0]}, {"theta": [1.0, 2.0, 3.0]}],
    }
    response = client.post("/lift", json={"concept": bad_concept})
    assert response.status_code == 422
    assert "dimension" in response.json()["detail"]
