from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_dependencies_without_secrets() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ok",
        "database": "not_configured",
        "scheduler": "not_started",
        "embedding": "not_configured",
        "model": "not_configured",
        "feishu": "not_configured",
    }
    serialized = response.text.lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized


def test_frontend_development_origin_can_call_api() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/ask",
        headers={
            "Origin": "http://localhost:5177",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5177"
