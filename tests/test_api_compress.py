"""`POST /compress` — thin controller over `cle.compression.measure_compression`."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import app

client = TestClient(app)


def test_compress_reports_ratio_and_target() -> None:
    response = client.post(
        "/compress",
        json={"raw_context": "x" * 1000, "lifted_morphism_set": "y" * 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ratio"] >= 10.0
    assert body["meets_target"] is True


def test_compress_below_target_reports_meets_target_false() -> None:
    response = client.post(
        "/compress",
        json={"raw_context": "x" * 20, "lifted_morphism_set": "y" * 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ratio"] < 10.0
    assert body["meets_target"] is False
