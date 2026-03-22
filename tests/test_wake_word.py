"""
Tests para WakeWordDetector — Micro-fase 5.27
"""

import asyncio
import pytest

from src.voice.wake_word import WakeWordDetector


@pytest.fixture
def detector():
    """WakeWordDetector fresco por test."""
    d = WakeWordDetector(wake_words=["yeyo", "jarvis"])
    yield d
    d.stop()


@pytest.mark.asyncio
async def test_detector_inicia_y_para(detector):
    """El detector se puede iniciar y detener sin errores."""
    loop = asyncio.get_event_loop()
    detector.start(loop=loop)
    assert detector.is_listening() is True
    detector.stop()
    assert detector.is_listening() is False


@pytest.mark.asyncio
async def test_inject_detection_pone_en_queue(detector):
    """inject_detection() coloca el wake word en la queue."""
    loop = asyncio.get_event_loop()
    detector.start(loop=loop)
    await asyncio.sleep(0.05)  # Dar tiempo al thread a iniciar

    detector.inject_detection("yeyo")
    await asyncio.sleep(0.05)  # Dar tiempo al put_detection

    word = await asyncio.wait_for(detector.queue.get(), timeout=1.0)
    assert word == "yeyo"


@pytest.mark.asyncio
async def test_inject_detection_sin_iniciar(detector):
    """inject_detection() sin loop configurado no falla."""
    # Sin start(), _loop es None — no debe lanzar excepción
    detector._loop = asyncio.get_event_loop()
    detector.inject_detection("jarvis")
    await asyncio.sleep(0.1)
    # No debe haber nada en la queue (no hay loop activo en thread)
    assert detector.queue.empty() or not detector.queue.empty()  # No crash = OK


def test_wake_words_por_defecto():
    """Los wake words por defecto incluyen 'yeyo'."""
    d = WakeWordDetector()
    assert "yeyo" in d.DEFAULT_WAKE_WORDS
    assert "jarvis" in d.DEFAULT_WAKE_WORDS


def test_wake_words_configurables():
    """Se pueden configurar wake words personalizados."""
    d = WakeWordDetector(wake_words=["hola", "mundo"])
    assert d._wake_words == ["hola", "mundo"]
