import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.routes.yeyonet as yeyonet_routes


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(yeyonet_routes.router)
    return TestClient(app)


def test_register_via_central_proxies_request(client, monkeypatch):
    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            captured["kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return httpx.Response(
                200,
                json={
                    "node_id": "sat-123",
                    "auth_token": "token-123",
                    "central_ws_url": "ws://192.168.1.10:8000/ws/yeyonet",
                    "permissions": ["chat", "memoria"],
                    "visibility_level": 3,
                },
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(yeyonet_routes.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/api/v1/yeyonet/register-via-central",
        json={
            "central_url": "http://192.168.1.10:8000/",
            "code": "YEYO-ABCD-EFGH-IJKL",
            "node_name": "Sat QA",
            "mode": "ligero",
        },
    )

    assert response.status_code == 200
    assert response.json()["central_ws_url"] == "ws://192.168.1.10:8000/ws/yeyonet"
    assert captured["url"] == "http://192.168.1.10:8000/api/v1/yeyonet/register"
    assert captured["json"] == {
        "code": "YEYO-ABCD-EFGH-IJKL",
        "node_name": "Sat QA",
        "mode": "ligero",
    }
    assert captured["kwargs"] == {"timeout": 20.0, "follow_redirects": True}


def test_register_via_central_surfaces_upstream_error(client, monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            return httpx.Response(
                400,
                json={"detail": "Código inválido, expirado o ya usado"},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(yeyonet_routes.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/api/v1/yeyonet/register-via-central",
        json={
            "central_url": "http://192.168.1.10:8000",
            "code": "YEYO-ABCD-EFGH-IJKL",
            "node_name": "Sat QA",
            "mode": "completo",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Código inválido, expirado o ya usado"


def test_register_via_central_handles_network_error(client, monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            raise httpx.ConnectError("boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(yeyonet_routes.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/api/v1/yeyonet/register-via-central",
        json={
            "central_url": "http://192.168.1.10:8000",
            "code": "YEYO-ABCD-EFGH-IJKL",
            "node_name": "Sat QA",
            "mode": "minimo",
        },
    )

    assert response.status_code == 502
    assert "No se pudo alcanzar la Central" in response.json()["detail"]
    assert "Detalle: no se pudo abrir conexión TCP: boom" in response.json()["detail"]


def test_register_via_central_handles_empty_network_error_message(client, monkeypatch):
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            raise httpx.ConnectError("", request=httpx.Request("POST", url))

    monkeypatch.setattr(yeyonet_routes.httpx, "AsyncClient", FakeAsyncClient)

    response = client.post(
        "/api/v1/yeyonet/register-via-central",
        json={
            "central_url": "http://192.168.1.10:8000",
            "code": "YEYO-ABCD-EFGH-IJKL",
            "node_name": "Sat QA",
            "mode": "minimo",
        },
    )

    assert response.status_code == 502
    assert "Detalle: no se pudo abrir conexión TCP" in response.json()["detail"]


def test_register_via_central_requires_http_scheme(client):
    response = client.post(
        "/api/v1/yeyonet/register-via-central",
        json={
            "central_url": "192.168.1.10:8000",
            "code": "YEYO-ABCD-EFGH-IJKL",
            "node_name": "Sat QA",
            "mode": "ligero",
        },
    )

    assert response.status_code == 400
    assert "http://" in response.json()["detail"]


def test_get_identity_includes_suggested_central_urls(client, monkeypatch):
    class FakeIdentity:
        async def get_node(self):
            class Node:
                id = "central-1"
                name = "Central QA"
                role = "central"
                status = "online"

            return Node()

    client.app.dependency_overrides[yeyonet_routes.get_node_identity] = lambda: FakeIdentity()
    monkeypatch.setattr(
        yeyonet_routes,
        "_suggest_central_urls",
        lambda: ["http://192.168.101.159:8000", "http://localhost:8000"],
    )

    response = client.get("/api/v1/yeyonet/identity")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "central-1"
    assert data["name"] == "Central QA"
    assert data["node_name"] == "Central QA"
    assert data["role"] == "central"
    assert data["suggested_central_urls"] == [
        "http://192.168.101.159:8000",
        "http://localhost:8000",
    ]
