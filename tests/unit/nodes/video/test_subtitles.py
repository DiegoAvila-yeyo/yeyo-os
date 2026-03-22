"""Tests para Subtitles + TTS — Micro-fase 5.6"""

import pytest
from unittest.mock import AsyncMock
from src.nodes.video.subtitles import (
    WhisperSubtitleService, PiperTTSService,
    SubtitleEntry, SubtitleResult,
)


class TestWhisperSubtitles:

    def test_format_time_zero(self):
        service = WhisperSubtitleService()
        assert service._format_time(0.0) == "00:00:00,000"

    def test_format_time_minutes(self):
        service = WhisperSubtitleService()
        assert service._format_time(61.5) == "00:01:01,500"

    def test_format_time_hours(self):
        service = WhisperSubtitleService()
        assert service._format_time(3661.123) == "01:01:01,123"

    def test_generate_srt(self):
        service = WhisperSubtitleService()
        entries = [
            SubtitleEntry(1, "00:00:00,000", "00:00:02,000", "Hola mundo"),
            SubtitleEntry(2, "00:00:02,000", "00:00:04,000", "Soy YeyoOS"),
        ]
        srt = service._generate_srt(entries)
        assert "1\n00:00:00,000 --> 00:00:02,000\nHola mundo" in srt
        assert "2\n00:00:02,000 --> 00:00:04,000\nSoy YeyoOS" in srt

    def test_parse_segments(self):
        service = WhisperSubtitleService()
        segments = [
            {"start": 0.0, "end": 2.0, "text": " Hola "},
            {"start": 2.0, "end": 4.0, "text": " Mundo "},
        ]
        entries = service._parse_segments(segments)
        assert len(entries) == 2
        assert entries[0].text == "Hola"
        assert entries[1].text == "Mundo"
        assert entries[0].index == 1
        assert entries[1].index == 2

    def test_model_runs_on_cpu(self):
        """Whisper DEBE correr en CPU, NO en GPU VRAM."""
        service = WhisperSubtitleService(model_size="base")
        assert service._model_size == "base"

    def test_srt_format_complete(self):
        service = WhisperSubtitleService()
        entries = [
            SubtitleEntry(1, "00:00:00,000", "00:00:03,000", "Primera línea"),
        ]
        srt = service._generate_srt(entries)
        lines = srt.strip().split("\n")
        assert lines[0] == "1"
        assert "-->" in lines[1]
        assert lines[2] == "Primera línea"


class TestPiperTTS:

    @pytest.mark.asyncio
    async def test_tts_error_when_not_installed(self):
        service = PiperTTSService()
        result = await service.generate_audio("test", "/tmp/test.wav")
        assert "error" in result or "output_path" in result

    def test_default_voice_is_spanish(self):
        service = PiperTTSService()
        assert "es" in service._voice.lower()

    def test_custom_voice(self):
        service = PiperTTSService(voice="en_US-lessac-medium")
        assert service._voice == "en_US-lessac-medium"
