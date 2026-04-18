import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.routes.yeyonet as yeyonet_routes
import src.yeyonet.satellite_config as satellite_config


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


def test_connect_rebuilds_runtime_when_only_websocket_client_exists(client, monkeypatch):
    holder = {
        "client": type("ExistingClient", (), {"connected": True})(),
        "worker": None,
        "resource_monitor": None,
    }
    stop_calls: list[dict] = []
    start_calls: list[dict] = []

    async def fake_stop(runtime_holder):
        stop_calls.append(dict(runtime_holder))
        runtime_holder["client"] = None
        runtime_holder["worker"] = None
        runtime_holder["resource_monitor"] = None

    async def fake_start(runtime_holder, config):
        start_calls.append(config)
        runtime_holder["client"] = type("StartedClient", (), {"connected": False})()
        runtime_holder["worker"] = object()
        runtime_holder["resource_monitor"] = object()

    monkeypatch.setattr(satellite_config, "load_config", lambda: {
        "node_id": "sat-123",
        "auth_token": "token-123",
        "central_ws_url": "ws://127.0.0.1:8000/ws/yeyonet",
        "central_name": "Central QA",
    })
    monkeypatch.setattr(yeyonet_routes, "_stop_satellite_runtime", fake_stop)
    monkeypatch.setattr(yeyonet_routes, "_start_satellite_runtime", fake_start)
    client.app.dependency_overrides[yeyonet_routes.get_yeyonet_client] = lambda: holder

    response = client.post("/api/v1/yeyonet/connect")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "connecting",
        "connected": False,
        "central_ws_url": "ws://127.0.0.1:8000/ws/yeyonet",
        "node_id": "sat-123",
        "central_name": "Central QA",
    }
    assert len(stop_calls) == 1
    assert start_calls == [{
        "node_id": "sat-123",
        "auth_token": "token-123",
        "central_ws_url": "ws://127.0.0.1:8000/ws/yeyonet",
        "central_name": "Central QA",
    }]
    assert holder["worker"] is not None
    assert holder["resource_monitor"] is not None


def test_connect_keeps_existing_runtime_when_config_matches(client, monkeypatch):
    holder = {
        "client": type(
            "ExistingClient",
            (),
            {
                "connected": True,
                "_node_id": "sat-123",
                "_auth_token": "token-123",
                "_url": "ws://127.0.0.1:8000/ws/yeyonet",
            },
        )(),
        "worker": object(),
        "resource_monitor": object(),
    }
    start_calls: list[dict] = []
    stop_calls: list[dict] = []

    async def fake_start(runtime_holder, config):
        start_calls.append(config)

    async def fake_stop(runtime_holder):
        stop_calls.append(dict(runtime_holder))

    monkeypatch.setattr(satellite_config, "load_config", lambda: {
        "node_id": "sat-123",
        "auth_token": "token-123",
        "central_ws_url": "ws://127.0.0.1:8000/ws/yeyonet",
        "central_name": "Central QA",
    })
    monkeypatch.setattr(yeyonet_routes, "_start_satellite_runtime", fake_start)
    monkeypatch.setattr(yeyonet_routes, "_stop_satellite_runtime", fake_stop)
    client.app.dependency_overrides[yeyonet_routes.get_yeyonet_client] = lambda: holder

    response = client.post("/api/v1/yeyonet/connect")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "already_connected",
        "connected": True,
        "central_ws_url": "ws://127.0.0.1:8000/ws/yeyonet",
        "node_id": "sat-123",
        "central_name": "Central QA",
    }
    assert start_calls == []
    assert stop_calls == []


def test_disconnect_stops_full_satellite_runtime(client, monkeypatch):
    holder = {
        "client": object(),
        "worker": object(),
        "resource_monitor": object(),
    }
    stop_calls: list[dict] = []
    clear_calls: list[bool] = []

    async def fake_stop(runtime_holder):
        stop_calls.append(dict(runtime_holder))
        runtime_holder["client"] = None
        runtime_holder["worker"] = None
        runtime_holder["resource_monitor"] = None

    monkeypatch.setattr(yeyonet_routes, "_stop_satellite_runtime", fake_stop)
    monkeypatch.setattr(satellite_config, "clear_config", lambda: clear_calls.append(True))
    client.app.dependency_overrides[yeyonet_routes.get_yeyonet_client] = lambda: holder

    response = client.post("/api/v1/yeyonet/disconnect")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "disconnected", "connected": False}
    assert len(stop_calls) == 1
    assert clear_calls == [True]
    assert holder == {"client": None, "worker": None, "resource_monitor": None}
