"""Tests para Logging System — Micro-fase 1.11"""

import json
import logging
import os
import pytest
from src.core.logger import YeyoLogger, JSONFormatter, redact_sensitive, REDACTED


@pytest.fixture
def tmp_log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return str(log_dir)


@pytest.fixture(autouse=True)
def clean_loggers():
    yield
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("yeyo.test"):
            logger = logging.getLogger(name)
            logger.handlers.clear()


class TestJSONFormatter:
    def test_output_is_valid_json(self):
        formatter = JSONFormatter(service="test")
        record = logging.LogRecord("yeyo.test", logging.INFO, "", 0, "Hello", None, None)
        output = formatter.format(record)
        assert isinstance(json.loads(output), dict)

    def test_has_required_fields(self):
        formatter = JSONFormatter(service="test")
        record = logging.LogRecord("yeyo.test", logging.INFO, "", 0, "test message", None, None)
        data = json.loads(formatter.format(record))
        assert "timestamp" in data
        assert "level" in data
        assert "service" in data
        assert "message" in data
        assert "logger" in data

    def test_level_is_correct(self):
        formatter = JSONFormatter(service="test")
        record = logging.LogRecord("yeyo.test", logging.WARNING, "", 0, "warning", None, None)
        data = json.loads(formatter.format(record))
        assert data["level"] == "WARNING"

    def test_service_is_set(self):
        formatter = JSONFormatter(service="gpu_scheduler")
        record = logging.LogRecord("yeyo.test", logging.INFO, "", 0, "test", None, None)
        data = json.loads(formatter.format(record))
        assert data["service"] == "gpu_scheduler"

    def test_timestamp_is_iso_format(self):
        formatter = JSONFormatter(service="test")
        record = logging.LogRecord("yeyo.test", logging.INFO, "", 0, "test", None, None)
        data = json.loads(formatter.format(record))
        assert "T" in data["timestamp"]


class TestRedactSensitive:
    def test_redact_password(self):
        result = redact_sensitive("password=my_secret_123")
        assert "my_secret_123" not in result
        assert REDACTED in result

    def test_redact_token(self):
        result = redact_sensitive("token=abc123xyz")
        assert "abc123xyz" not in result

    def test_redact_api_key(self):
        result = redact_sensitive("api_key=sk-123456")
        assert "sk-123456" not in result

    def test_redact_bearer_token(self):
        result = redact_sensitive("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9")
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_redact_database_url_password(self):
        result = redact_sensitive("postgresql://yeyo:super_secret@localhost:5432/yeyo_db")
        assert "super_secret" not in result

    def test_normal_text_unchanged(self):
        text = "Processing user request for chat"
        assert redact_sensitive(text) == text


class TestYeyoLogger:
    def test_get_logger_returns_logger(self, tmp_log_dir):
        YeyoLogger.configure(log_dir=tmp_log_dir)
        logger = YeyoLogger.get_logger("yeyo.test.basic")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_handlers(self, tmp_log_dir):
        YeyoLogger.configure(log_dir=tmp_log_dir)
        logger = YeyoLogger.get_logger("yeyo.test.handlers")
        assert len(logger.handlers) > 0

    def test_logger_outputs_json(self, tmp_log_dir, capsys):
        YeyoLogger.configure(log_dir=tmp_log_dir, log_level="DEBUG")
        logger = YeyoLogger.get_logger("yeyo.test.json_output")
        logger.info("test message")
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["message"] == "test message"

    def test_same_logger_returned(self, tmp_log_dir):
        YeyoLogger.configure(log_dir=tmp_log_dir)
        l1 = YeyoLogger.get_logger("yeyo.test.same")
        l2 = YeyoLogger.get_logger("yeyo.test.same")
        assert l1 is l2

    def test_log_levels_work(self, tmp_log_dir, capsys):
        YeyoLogger.configure(log_dir=tmp_log_dir, log_level="WARNING")
        logger = YeyoLogger.get_logger("yeyo.test.levels")
        logger.info("should not appear")
        logger.warning("should appear")
        captured = capsys.readouterr()
        assert "should not appear" not in captured.out
        assert "should appear" in captured.out

    def test_writes_to_file(self, tmp_log_dir):
        YeyoLogger.configure(log_dir=tmp_log_dir)
        logger = YeyoLogger.get_logger("yeyo.test.file_write", service="testservice")
        logger.info("file test message")
        log_file = os.path.join(tmp_log_dir, "testservice.log")
        assert os.path.exists(log_file)
        with open(log_file) as f:
            data = json.loads(f.readline())
            assert data["message"] == "file test message"

    def test_sensitive_data_redacted_in_output(self, tmp_log_dir, capsys):
        YeyoLogger.configure(log_dir=tmp_log_dir, log_level="DEBUG")
        logger = YeyoLogger.get_logger("yeyo.test.redact")
        logger.info("Connecting with password=secret123")
        captured = capsys.readouterr()
        assert "secret123" not in captured.out
        assert REDACTED in captured.out
