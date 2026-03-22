"""
Tests para VoiceService — Micro-fase 5.27
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.voice.voice_service import VoiceService, MicState


@pytest.fixture
def service():
    """VoiceService fresco con mocks."""
    with patch("src.voice.voice_service.WakeWordDetector") as MockDetector, \
         patch("src.voice.voice_service.SpeechToText") as MockSTT, \
         patch("src.voice.voice_service.TextToSpeech") as MockTTS:

        mock_detector = MagicMock()
        mock_detector.queue = asyncio.Queue()
        mock_detector.start = MagicMock()
        mock_detector.stop = MagicMock()
        mock_detector.is_listening.return_value = True
        MockDetector.return_value = mock_detector

        mock_stt = MagicMock()
        mock_stt.record_until_silence.return_value = b"\x00" * 1024
        mock_stt.transcribe.return_value = "hola mundo"
        MockSTT.return_value = mock_stt

        mock_tts = MagicMock()
        mock_tts.speak = AsyncMock()
        mock_tts.say_system = AsyncMock()
        mock_tts.voice_enabled = True
        MockTTS.return_value = mock_tts

        svc = VoiceService()
        yield svc, mock_detector, mock_stt, mock_tts


@pytest.mark.asyncio
async def test_start_inicia_detector(service):
    """start() inicia el detector y cambia estado a LISTENING."""
    svc, mock_detector, _, _ = service
    await svc.start()
    assert svc.state == MicState.LISTENING
    mock_detector.start.assert_called_once()
    await svc.stop()


@pytest.mark.asyncio
async def test_stop_detiene_detector(service):
    """stop() detiene el detector y cambia estado a DISABLED."""
    svc, mock_detector, _, _ = service
    await svc.start()
    await svc.stop()
    assert svc.state == MicState.DISABLED
    mock_detector.stop.assert_called()


@pytest.mark.asyncio
async def test_comando_para_todo_activa_kill_switch(service):
    """Comando "para todo" activa el kill switch callback."""
    svc, _, _, _ = service
    kill_switch_called = []
    svc.set_kill_switch_callback(lambda: kill_switch_called.append(True))

    handled = svc._handle_quick_command("oye para todo por favor")
    assert handled is True
    assert len(kill_switch_called) == 1


@pytest.mark.asyncio
async def test_comando_silencio_deshabilita_mic(service):
    """Comando "silencio" deshabilita el micrófono."""
    svc, mock_detector, _, _ = service
    loop = asyncio.get_event_loop()
    svc._detector.start(loop=loop)

    handled = svc._handle_quick_command("silencio")
    assert handled is True
    assert svc.state == MicState.DISABLED


@pytest.mark.asyncio
async def test_comando_despierta_habilita_mic(service):
    """Comando "despierta" habilita el micrófono."""
    svc, mock_detector, _, _ = service
    svc._state = MicState.DISABLED
    handled = svc._handle_quick_command("despierta")
    assert handled is True
    assert svc.state == MicState.LISTENING


def test_texto_normal_no_es_comando(service):
    """Texto normal no activa ningún comando rápido."""
    svc, _, _, _ = service
    handled = svc._handle_quick_command("genera una imagen de un gato")
    assert handled is False


@pytest.mark.asyncio
async def test_state_callback_se_llama(service):
    """El callback de estado se llama al cambiar estado."""
    svc, _, _, _ = service
    states_received = []
    svc.set_state_callback(lambda s: states_received.append(s))
    await svc.start()
    assert MicState.LISTENING in states_received
    await svc.stop()


def test_comando_abre_imagen(service):
    """Comando "abre imagen" activa el callback de nodo."""
    svc, _, _, _ = service
    nodes_opened = []
    svc.set_open_node_callback(lambda n: nodes_opened.append(n))
    handled = svc._handle_quick_command("abre imagen")
    assert handled is True
    assert "image" in nodes_opened
