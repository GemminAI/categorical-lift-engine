"""`GET /health`."""

from __future__ import annotations

from fastapi.testclient import TestClient

from cle.api.app import app
from cle.version import __version__

client = TestClient(app)


def test_health_reports_ok_status_service_and_version() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "cle",
        "version": __version__,
    }
