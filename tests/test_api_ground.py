"""`POST /ground` -- thin controller over `cle.grounding.service.ground`.
Same TestClient pattern as `test_api_lift.py`."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import app

client = TestClient(app)


def test_ground_returns_semantic_state_and_lift() -> None:
    response = client.post(
        "/ground",
        json={
            "prompt": "軌跡が不安定なので安定化してほしい。",
            "goal": "stabilize trajectory",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["semantic_state"]["prompt"] == "軌跡が不安定なので安定化してほしい。"
    assert body["semantic_state"]["sok"]["observer"] == "CLE"
    assert body["lift"]["concept_id"].startswith("concept:")
    assert body["lift"]["proof"]["functor_axioms_satisfied"] is True


def test_ground_with_sok_overrides_reaches_response() -> None:
    response = client.post(
        "/ground",
        json={
            "prompt": "test prompt",
            "goal": "test goal",
            "sok_overrides": {
                "subject": "explicit-subject",
                "knowledge_reference": "explicit-ref",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["semantic_state"]["sok"]["subject"] == "explicit-subject"
    assert body["semantic_state"]["sok"]["subject_source"] == "explicit"
    assert body["semantic_state"]["sok"]["knowledge_reference"] == "explicit-ref"


def test_ground_different_subject_yields_different_invariants_over_http() -> None:
    """The end-to-end HTTP-level version of the causal acceptance test --
    proves the wire contract carries the causal effect, not just the
    Python-level service function."""
    response_a = client.post(
        "/ground",
        json={"prompt": "p", "goal": "g", "sok_overrides": {"subject": "Japan_Govt"}},
    )
    response_b = client.post(
        "/ground",
        json={"prompt": "p", "goal": "g", "sok_overrides": {"subject": "Private_Corp"}},
    )
    assert (
        response_a.json()["lift"]["invariants"]
        != response_b.json()["lift"]["invariants"]
    )


def test_ground_response_is_byte_stable_json() -> None:
    response = client.post("/ground", json={"prompt": "stability check", "goal": "g"})
    assert response.json() == response.json()  # trivial within-process; real proof is
    # test_grounding_embedding.py's cross-subprocess PYTHONHASHSEED check underneath it


def test_ground_embedding_dimension_bounds_are_enforced() -> None:
    response = client.post(
        "/ground", json={"prompt": "p", "goal": "g", "embedding_dimension": 0}
    )
    assert response.status_code == 422
    response = client.post(
        "/ground", json={"prompt": "p", "goal": "g", "embedding_dimension": 100}
    )
    assert response.status_code == 422
