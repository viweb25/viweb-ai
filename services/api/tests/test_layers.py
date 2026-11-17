from fastapi.testclient import TestClient
from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.bootstrap import app
from vi_api.container import get_function_templates
from vi_api.domain.catalogue.model import FunctionTemplate


class FakeRepository:
    def list_templates(self):
        return [
            FunctionTemplate(id="test", name="Example", stage="planned: test", config_schema={})
        ]


def test_controller_uses_injected_service_and_repository():
    app.dependency_overrides[get_function_templates] = lambda: GetFunctionTemplates(
        FakeRepository()
    )
    try:
        response = TestClient(app).get("/api/v1/function-templates")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "test"
    finally:
        app.dependency_overrides.clear()


def test_readiness_fails_closed_when_database_is_unavailable(monkeypatch):
    class UnavailableEngine:
        def connect(self):
            raise ConnectionError("private connection detail")

    monkeypatch.setattr("vi_api.container.engine", UnavailableEngine())
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"
    assert "private" not in response.text
