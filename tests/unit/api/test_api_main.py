"""Tests para API Base — Micro-fase 1.6"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data

    def test_health_status_is_healthy(self, client):
        response = client.get("/health")
        assert response.json()["status"] == "healthy"

    def test_health_version_is_correct(self, client):
        response = client.get("/health")
        assert response.json()["version"] == "0.1.0"

    def test_health_uptime_is_number(self, client):
        response = client.get("/health")
        uptime = response.json()["uptime_seconds"]
        assert isinstance(uptime, (int, float))
        assert uptime >= 0


class TestStatusEndpoint:
    def test_status_returns_200(self, client):
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_status_returns_json(self, client):
        response = client.get("/api/v1/status")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data

    def test_status_has_all_services(self, client):
        response = client.get("/api/v1/status")
        services = response.json()["services"]
        assert "api" in services
        assert "postgresql" in services
        assert "redis" in services
        assert "ollama" in services
        assert "gpu" in services

    def test_status_api_is_up(self, client):
        response = client.get("/api/v1/status")
        assert response.json()["services"]["api"] == "up"

    def test_status_unconfigured_services(self, client):
        """Sin lifespan, postgresql y ollama reportan not_configured."""
        response = client.get("/api/v1/status")
        services = response.json()["services"]
        assert services["postgresql"] == "not_configured"
        assert services["ollama"] == "not_configured"


class TestCORS:
    def test_cors_allows_localhost_3000(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_blocks_unknown_origin(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"

    def test_cors_allows_credentials(self, client):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-credentials") == "true"


class TestAppMetadata:
    def test_app_title(self):
        assert app.title == "YeyoOS API"

    def test_app_version(self):
        assert app.version == "0.1.0"

    def test_openapi_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_docs_available(self, client):
        response = client.get("/docs")
        assert response.status_code == 200


class TestNotFound:
    def test_unknown_route_returns_404(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_unknown_api_route_returns_404(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
