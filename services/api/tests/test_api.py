from fastapi.testclient import TestClient
from vi_api.bootstrap import app

client = TestClient(app)


def test_liveness_and_catalogue():
    assert client.get("/health/live").json() == {"status": "ok", "service": "api"}
    response = client.get("/api/v1/function-templates")
    assert response.status_code == 200
    assert len(response.json()) == 8
    assert all(item["stage"].startswith("planned:") for item in response.json())


def test_unknown_route_uses_error_envelope():
    response = client.get("/api/v1/projects")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_404"
