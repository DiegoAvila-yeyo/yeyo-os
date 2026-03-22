"""Tests para Node API Endpoints — Micro-fase 5.17"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes.nodes import router, _active_nodes
from src.nodes.base import NodeBase, PrivilegeLevel
from src.nodes.registry import NodeRegistry


class FakeNode(NodeBase):
    async def initialize(self): pass
    async def render_ui(self) -> dict:
        return {"component": "FakeNode", "props": {}}
    async def process(self, input_data: dict) -> dict:
        return {"echo": input_data}
    async def cleanup(self): pass

    def __init__(self):
        super().__init__(name="Fake", version="1.0")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    _active_nodes.clear()
    NodeRegistry.clear()
    NodeRegistry.register("fake", FakeNode)
    return TestClient(app)


class TestNodeAPIEndpoints:

    def test_list_node_types(self, client):
        response = client.get("/api/v1/nodes/")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert data["count"] >= 1

    def test_open_node(self, client):
        response = client.post("/api/v1/nodes/fake/open")
        assert response.status_code == 200
        data = response.json()
        assert "node_id" in data
        assert data["type"] == "fake"

    def test_open_unknown_type_404(self, client):
        response = client.post("/api/v1/nodes/nonexistent/open")
        assert response.status_code == 404

    def test_close_node(self, client):
        open_resp = client.post("/api/v1/nodes/fake/open")
        node_id = open_resp.json()["node_id"]
        close_resp = client.delete(f"/api/v1/nodes/{node_id}/close")
        assert close_resp.status_code == 200

    def test_close_nonexistent_404(self, client):
        response = client.delete("/api/v1/nodes/fake-id/close")
        assert response.status_code == 404

    def test_get_status(self, client):
        open_resp = client.post("/api/v1/nodes/fake/open")
        node_id = open_resp.json()["node_id"]
        status_resp = client.get(f"/api/v1/nodes/{node_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["name"] == "Fake"

    def test_process_data(self, client):
        open_resp = client.post("/api/v1/nodes/fake/open")
        node_id = open_resp.json()["node_id"]
        process_resp = client.post(
            f"/api/v1/nodes/{node_id}/process",
            json={"data": {"key": "value"}},
        )
        assert process_resp.status_code == 200

    def test_get_ui(self, client):
        open_resp = client.post("/api/v1/nodes/fake/open")
        node_id = open_resp.json()["node_id"]
        ui_resp = client.get(f"/api/v1/nodes/{node_id}/ui")
        assert ui_resp.status_code == 200
        assert ui_resp.json()["component"] == "FakeNode"

    def test_list_active_nodes(self, client):
        client.post("/api/v1/nodes/fake/open")
        response = client.get("/api/v1/nodes/active")
        assert response.status_code == 200
        assert response.json()["count"] == 1
