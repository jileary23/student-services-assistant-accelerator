from app.main import app
from fastapi.testclient import TestClient


def test_health_reports_mock_mode() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "mock"}


def test_public_config_exposes_institution_customization() -> None:
    with TestClient(app) as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    assert response.json()["institution_name"] == "Contoso University"
    assert "support_destination" in response.json()


def test_chat_returns_grounded_registration_answer() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "When does fall registration open?"},
        )

    payload = response.json()
    assert response.status_code == 200
    assert payload["citations"][0]["id"] == "registration"
    assert payload["escalation"]["required"] is False


def test_chat_rejects_empty_messages() -> None:
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422
