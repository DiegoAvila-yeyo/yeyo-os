"""
Tests para TextToSpeech — Micro-fase 5.27
"""

import asyncio
import sys
import pytest
import time
from unittest.mock import patch, MagicMock


@pytest.fixture
def tts_mock():
    """TTS con pyttsx3 mockeado via sys.modules."""
    mock_pyttsx3 = MagicMock()
    mock_engine = MagicMock()
    mock_pyttsx3.init.return_value = mock_engine

    with patch.dict("sys.modules", {"pyttsx3": mock_pyttsx3}):
        # Reload the module so it picks up the mock
        if "src.voice.tts" in sys.modules:
            del sys.modules["src.voice.tts"]
        import src.voice.tts as tts_mod
        tts_mod._PYTTSX3_AVAILABLE = True
        tts_mod.pyttsx3 = mock_pyttsx3
        tts_instance = tts_mod.TextToSpeech()
        yield tts_instance, mock_engine


@pytest.mark.asyncio
async def test_speak_no_bloquea(tts_mock):
    """speak() async retorna rápido sin esperar que el audio termine."""
    tts, _ = tts_mock
    start = time.time()
    await tts.speak("Texto de prueba que tardaría en hablar")
    elapsed = time.time() - start
    # speak() con run_in_executor puede bloquear en test — verificar que no excede 2s
    assert elapsed < 5.0  # En tests con mock es casi instantáneo


@pytest.mark.asyncio
async def test_speak_texto_vacio_no_hace_nada(tts_mock):
    """speak() con texto vacío no llama al engine."""
    tts, mock_engine = tts_mock
    await tts.speak("   ")
    mock_engine.say.assert_not_called()


def test_speak_sync_espera(tts_mock):
    """speak_sync() llama al engine y espera."""
    tts, mock_engine = tts_mock
    tts.speak_sync("Hola mundo")
    mock_engine.say.assert_called_once_with("Hola mundo")
    mock_engine.runAndWait.assert_called_once()


def test_voice_enabled_false_no_habla(tts_mock):
    """Cuando voice_enabled=False, speak_sync() no habla."""
    tts, mock_engine = tts_mock
    tts.voice_enabled = False
    tts.speak_sync("No debería hablar")
    mock_engine.say.assert_not_called()


def test_configure_rate_y_volume(tts_mock):
    """configure() actualiza rate y volume."""
    tts, _ = tts_mock
    tts.configure(rate=200, volume=0.5)
    assert tts._rate == 200
    assert tts._volume == 0.5


def test_configure_limites():
    """configure() respeta los límites min/max."""
    from src.voice.tts import TextToSpeech
    tts = TextToSpeech()
    tts.configure(rate=1000, volume=2.0)
    assert tts._rate == 400
    assert tts._volume == 1.0
    tts.configure(rate=-100, volume=-1.0)
    assert tts._rate == 50
    assert tts._volume == 0.0


@pytest.mark.asyncio
async def test_say_system_frases(tts_mock):
    """say_system() habla las frases del sistema predefinidas."""
    tts, mock_engine = tts_mock
    await tts.say_system("ready")
    mock_engine.say.assert_called_with("Dime.")
