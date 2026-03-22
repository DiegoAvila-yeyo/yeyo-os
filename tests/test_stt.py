"""
Tests para SpeechToText — Micro-fase 5.27
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


def test_transcribe_sin_modelo_retorna_vacio():
    """Sin modelo disponible, transcribe() retorna string vacío."""
    with patch("src.voice.stt._WHISPER_AVAILABLE", False):
        from src.voice.stt import SpeechToText
        stt = SpeechToText()
        stt._model = None
        result = stt.transcribe(b"\x00" * 1024)
        assert result == ""


def test_transcribe_con_modelo_mock():
    """Con modelo mock, transcribe() retorna el texto de los segmentos."""
    with patch("src.voice.stt._WHISPER_AVAILABLE", True):
        from src.voice.stt import SpeechToText

        mock_segment = MagicMock()
        mock_segment.text = "  hola mundo  "
        mock_info = MagicMock()

        stt = SpeechToText.__new__(SpeechToText)
        stt._model_lock = __import__("threading").Lock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        stt._model = mock_model

        # Audio PCM 16-bit de 1 segundo (silencio)
        audio = np.zeros(16000, dtype=np.int16).tobytes()
        result = stt.transcribe(audio)
        assert result == "hola mundo"


def test_transcribe_multiples_segmentos():
    """Múltiples segmentos se unen con espacio."""
    with patch("src.voice.stt._WHISPER_AVAILABLE", True):
        from src.voice.stt import SpeechToText

        seg1 = MagicMock()
        seg1.text = "primera parte"
        seg2 = MagicMock()
        seg2.text = "segunda parte"

        stt = SpeechToText.__new__(SpeechToText)
        stt._model_lock = __import__("threading").Lock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([seg1, seg2], MagicMock())
        stt._model = mock_model

        audio = np.zeros(16000, dtype=np.int16).tobytes()
        result = stt.transcribe(audio)
        assert result == "primera parte segunda parte"


def test_transcribe_excepcion_retorna_vacio():
    """Si el modelo lanza excepción, transcribe() retorna vacío."""
    with patch("src.voice.stt._WHISPER_AVAILABLE", True):
        from src.voice.stt import SpeechToText

        stt = SpeechToText.__new__(SpeechToText)
        stt._model_lock = __import__("threading").Lock()
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("GPU OOM")
        stt._model = mock_model

        audio = np.zeros(16000, dtype=np.int16).tobytes()
        result = stt.transcribe(audio)
        assert result == ""
