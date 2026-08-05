"""`POST /pullback` — thin controller over
`cle.topology.three_view_pullback.compute_common_invariant_subgraph`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import app

client = TestClient(app)


def _category(
    objects: list[str], morphisms: list[dict[str, str]]
) -> dict[str, object]:
    return {"objects": objects, "morphisms": morphisms, "composition": []}


def test_pullback_of_identical_categories_returns_the_shared_morphism() -> None:
    shared = {"name": "shared", "source": "A", "target": "B"}
    category = _category(["A", "B"], [shared])
    response = client.post(
        "/pullback",
        json={"subject": category, "observer": category, "knowledge": category},
    )
    assert response.status_code == 200
    assert response.json() == {
        "shared_morphisms": [{"name": "shared", "source": "A", "target": "B"}]
    }


def test_pullback_of_disjoint_categories_returns_no_shared_morphisms() -> None:
    subject = _category(["A", "B"], [{"name": "s_only", "source": "A", "target": "B"}])
    observer = _category(["A", "B"], [{"name": "o_only", "source": "A", "target": "B"}])
    knowledge = _category(["A"], [])
    response = client.post(
        "/pullback",
        json={"subject": subject, "observer": observer, "knowledge": knowledge},
    )
    assert response.status_code == 200
    assert response.json() == {"shared_morphisms": []}


def test_pullback_with_disagreeing_endpoints_is_a_422() -> None:
    subject = _category(["A", "B"], [{"name": "m", "source": "A", "target": "B"}])
    observer = _category(["A", "C"], [{"name": "m", "source": "A", "target": "C"}])
    knowledge = _category(["A"], [])
    response = client.post(
        "/pullback",
        json={"subject": subject, "observer": observer, "knowledge": knowledge},
    )
    assert response.status_code == 422
    assert "disagrees across views" in response.json()["detail"]


def test_pullback_with_a_dangling_morphism_is_a_422() -> None:
    malformed = _category(["A"], [{"name": "m", "source": "A", "target": "B"}])
    empty = _category(["A"], [])
    response = client.post(
        "/pullback",
        json={"subject": malformed, "observer": empty, "knowledge": empty},
    )
    assert response.status_code == 422
    assert "outside this category" in response.json()["detail"]
