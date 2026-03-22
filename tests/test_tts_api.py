"""
Tests para TTS API endpoint — Micro-fase 3.18
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Cliente de test con pyttsx3 mockeado."""
    with patch("pyttsx3.init") as mock_init:
        mock_engine = MagicMock()
        mock_init.return_value = mock_engine

        from src.api.tts import router
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        yield TestClient(app), mock_engine


def test_tts_endpoint_existe(client):
    tc, _ = client
    response = tc.post("/api/tts/", json={"text": "Hola mundo"})
    assert response.status_code == 200


def test_tts_retorna_ok(client):
    tc, _ = client
    response = tc.post("/api/tts/", json={"text": "Hola mundo"})
    data = response.json()
    assert data["ok"] is True


def test_tts_texto_vacio_retorna_400(client):
    tc, _ = client
    response = tc.post("/api/tts/", json={"text": "   "})
    assert response.status_code == 400


def test_tts_acepta_rate_y_volume(client):
    tc, _ = client
    response = tc.post("/api/tts/", json={"text": "Test", "rate": 200, "volume": 0.5})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_tts_shader_uniforms():
    """Verifica que el archivo GLSL contiene los uniforms requeridos."""
    import os
    shader_path = os.path.join(os.path.dirname(__file__), "..", "src", "shaders", "grid_background.glsl")
    assert os.path.exists(shader_path), "grid_background.glsl no existe"
    with open(shader_path) as f:
        content = f.read()
    assert "u_time" in content, "Falta uniform u_time"
    assert "u_color" in content, "Falta uniform u_color"
    assert "u_saturation" in content, "Falta uniform u_saturation"
    assert "u_resolution" in content, "Falta uniform u_resolution"
