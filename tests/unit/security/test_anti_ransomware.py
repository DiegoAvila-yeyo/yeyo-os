"""Tests para Anti-Ransomware — Micro-fase 6.6"""

import pytest
import os
from pathlib import Path
from src.security.anti_ransomware import (
    RansomwareDetector,
    AntiRansomwareConfig,
    calculate_entropy,
    calculate_file_entropy,
    RANSOMWARE_EXTENSIONS,
)


@pytest.fixture
def detector():
    config = AntiRansomwareConfig(
        file_threshold=5,
        time_window_secs=5.0,
        watch_dirs=["/tmp"],
        ignore_dirs=["/proc"],
    )
    return RansomwareDetector(config=config)


class TestEntropy:
    def test_empty_data_zero_entropy(self):
        assert calculate_entropy(b"") == 0.0

    def test_uniform_data_low_entropy(self):
        data = b"\x00" * 1000
        assert calculate_entropy(data) == 0.0

    def test_random_data_high_entropy(self):
        data = bytes(range(256)) * 10
        entropy = calculate_entropy(data)
        assert entropy > 7.0

    def test_text_data_medium_entropy(self):
        data = b"Hello World! This is a normal text file with some content." * 20
        entropy = calculate_entropy(data)
        assert 3.0 < entropy < 6.0

    def test_file_entropy(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello World " * 100)
        entropy = calculate_file_entropy(str(f))
        assert 0.0 < entropy < 5.0


class TestRansomwareDetection:
    def test_known_extension_detected(self, detector, tmp_path):
        f = tmp_path / "document.encrypted"
        f.write_text("fake encrypted content")
        alert = detector.on_file_event(str(f), "created")
        assert alert is not None
        assert alert.alert_type == "known_extension"
        assert alert.severity == "critical"

    def test_normal_extension_not_flagged(self, detector, tmp_path):
        f = tmp_path / "document.txt"
        f.write_text("normal text content")
        alert = detector.on_file_event(str(f), "modified")
        assert alert is None

    def test_mass_modification_detected(self, detector, tmp_path):
        alert = None
        for i in range(20):
            f = tmp_path / f"file_{i}.dat"
            f.write_bytes(bytes(range(256)) * 16)
            result = detector.on_file_event(str(f), "modified")
            if result is not None:
                alert = result
        assert alert is not None

    def test_normal_file_ops_not_flagged(self, detector, tmp_path):
        for i in range(3):
            f = tmp_path / f"normal_{i}.txt"
            f.write_text(f"Normal content {i}")
            alert = detector.on_file_event(str(f), "modified")
            assert alert is None

    def test_ignored_directory(self, detector):
        alert = detector.on_file_event("/proc/something", "modified")
        assert alert is None

    def test_paused_detection(self, detector, tmp_path):
        detector.pause()
        f = tmp_path / "file.encrypted"
        f.write_text("should not be detected")
        alert = detector.on_file_event(str(f), "created")
        assert alert is None
        assert detector.is_paused()

    def test_resume_detection(self, detector, tmp_path):
        detector.pause()
        detector.resume()
        assert not detector.is_paused()
        f = tmp_path / "file.locked"
        f.write_text("should be detected")
        alert = detector.on_file_event(str(f), "created")
        assert alert is not None


class TestEntropyAnalysis:
    def test_encrypted_file_high_entropy(self, tmp_path):
        f = tmp_path / "encrypted.bin"
        f.write_bytes(os.urandom(4096))
        entropy = calculate_file_entropy(str(f))
        assert entropy > 7.5

    def test_text_file_low_entropy(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("The quick brown fox jumps over the lazy dog. " * 100)
        entropy = calculate_file_entropy(str(f))
        assert entropy < 5.0
