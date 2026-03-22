"""Tests para Package API Endpoints — Micro-fase 4.11"""

import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.packages import router, _installed_packages, _package_permissions


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    _installed_packages.clear()
    _package_permissions.clear()
    return TestClient(app)


@pytest.fixture
def client_with_package(client):
    _installed_packages["test-pkg"] = {
        "name": "test-pkg",
        "version": "1.0.0",
        "author": "Test",
        "description": "Test package",
        "type": "node",
        "privilege_level": "L2",
        "status": "installed",
    }
    return client


class TestListPackages:
    """Tests para GET /api/v1/packages"""

    def test_list_empty(self, client):
        response = client.get("/api/v1/packages/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_packages(self, client_with_package):
        response = client_with_package.get("/api/v1/packages/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-pkg"


class TestGetPackage:
    """Tests para GET /api/v1/packages/{name}"""

    def test_get_existing_package(self, client_with_package):
        response = client_with_package.get("/api/v1/packages/test-pkg")
        assert response.status_code == 200
        assert response.json()["name"] == "test-pkg"

    def test_get_nonexistent_returns_404(self, client):
        response = client.get("/api/v1/packages/nonexistent")
        assert response.status_code == 404


class TestUninstallPackage:
    """Tests para DELETE /api/v1/packages/{name}"""

    def test_uninstall_existing(self, client_with_package):
        response = client_with_package.delete("/api/v1/packages/test-pkg")
        assert response.status_code == 200
        assert response.json()["success"] is True

        response = client_with_package.get("/api/v1/packages/test-pkg")
        assert response.status_code == 404

    def test_uninstall_nonexistent_returns_404(self, client):
        response = client.delete("/api/v1/packages/nonexistent")
        assert response.status_code == 404


class TestPermissions:
    """Tests para POST/GET /api/v1/packages/{name}/permissions"""

    def test_grant_permission(self, client_with_package):
        response = client_with_package.post(
            "/api/v1/packages/test-pkg/permissions",
            json={"action": "grant", "permission": "memory.read"},
        )
        assert response.status_code == 200
        assert response.json()["granted"] is True

    def test_revoke_permission(self, client_with_package):
        client_with_package.post(
            "/api/v1/packages/test-pkg/permissions",
            json={"action": "grant", "permission": "memory.read"},
        )
        response = client_with_package.post(
            "/api/v1/packages/test-pkg/permissions",
            json={"action": "revoke", "permission": "memory.read"},
        )
        assert response.status_code == 200
        assert response.json()["granted"] is False

    def test_get_permissions(self, client_with_package):
        client_with_package.post(
            "/api/v1/packages/test-pkg/permissions",
            json={"action": "grant", "permission": "memory.read"},
        )
        response = client_with_package.get(
            "/api/v1/packages/test-pkg/permissions"
        )
        assert response.status_code == 200
        perms = response.json()["permissions"]
        assert len(perms) == 1

    def test_permissions_nonexistent_package(self, client):
        response = client.post(
            "/api/v1/packages/nonexistent/permissions",
            json={"action": "grant", "permission": "memory.read"},
        )
        assert response.status_code == 404

    def test_invalid_action_rejected(self, client_with_package):
        response = client_with_package.post(
            "/api/v1/packages/test-pkg/permissions",
            json={"action": "invalid", "permission": "memory.read"},
        )
        assert response.status_code == 422


class TestCheckUpdates:
    """Tests para GET /api/v1/packages/updates/check"""

    def test_check_updates(self, client):
        response = client.get("/api/v1/packages/updates/check")
        assert response.status_code == 200
        assert "updates" in response.json()


class TestInstallPackage:
    """Tests para POST /api/v1/packages/install"""

    def test_install_invalid_format_rejected(self, client):
        file_content = b"not a real package"
        response = client.post(
            "/api/v1/packages/install",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert response.status_code == 400

    def test_install_ypkg_file(self, client):
        file_content = b"fake ypkg content"
        response = client.post(
            "/api/v1/packages/install",
            files={"file": ("test-pkg-1.0.0.ypkg", io.BytesIO(file_content), "application/gzip")},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
