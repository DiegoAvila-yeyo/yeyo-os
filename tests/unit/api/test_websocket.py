"""Tests para WebSocket Server — Micro-fase 1.7"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.websocket import ConnectionManager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ws_manager():
    return ConnectionManager(max_connections=3)


class TestConnectionManager:
    def test_initial_no_connections(self, ws_manager):
        assert ws_manager.connection_count == 0

    def test_max_connections_set(self, ws_manager):
        assert ws_manager.max_connections == 3

    def test_default_max_connections(self):
        m = ConnectionManager()
        assert m.max_connections == 50

    def test_disconnect_removes_connection(self, ws_manager):
        mock_ws = MagicMock()
        ws_manager.active_connections.append(mock_ws)
        assert ws_manager.connection_count == 1
        ws_manager.disconnect(mock_ws)
        assert ws_manager.connection_count == 0

    def test_disconnect_nonexistent_is_safe(self, ws_manager):
        mock_ws = MagicMock()
        ws_manager.disconnect(mock_ws)
        assert ws_manager.connection_count == 0

    def test_get_status(self, ws_manager):
        status = ws_manager.get_status()
        assert status["active_connections"] == 0
        assert status["max_connections"] == 3

    @pytest.mark.asyncio
    async def test_send_message(self, ws_manager):
        mock_ws = AsyncMock()
        await ws_manager.send_message("hello", mock_ws)
        mock_ws.send_text.assert_called_once_with("hello")

    @pytest.mark.asyncio
    async def test_send_json(self, ws_manager):
        mock_ws = AsyncMock()
        await ws_manager.send_json({"key": "value"}, mock_ws)
        mock_ws.send_text.assert_called_once_with('{"key": "value"}')

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self, ws_manager):
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws_manager.active_connections = [ws1, ws2]
        await ws_manager.broadcast("hello all")
        ws1.send_text.assert_called_once_with("hello all")
        ws2.send_text.assert_called_once_with("hello all")

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self, ws_manager):
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("disconnected")
        ws_manager.active_connections = [ws_good, ws_bad]
        await ws_manager.broadcast("test")
        assert ws_bad not in ws_manager.active_connections
        assert ws_good in ws_manager.active_connections


class TestWebSocketEndpoint:
    def test_websocket_connect_and_echo(self, client):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("Hola YeyoOS")
            data = websocket.receive_json()
            assert data["type"] == "echo"
            assert data["content"] == "Hola YeyoOS"
            assert "timestamp" in data

    def test_websocket_multiple_messages(self, client):
        with client.websocket_connect("/ws") as websocket:
            for i in range(3):
                websocket.send_text(f"msg-{i}")
                data = websocket.receive_json()
                assert data["content"] == f"msg-{i}"
