"""
YeyoOS — Logging System
Micro-fase 1.11 — Capa 1: Esqueleto

Logging estructurado con salida JSON.
Cada línea de log es un JSON parseable por Guardian.

Campos: timestamp, level, service, message, extra
Seguridad: passwords, tokens, API keys se redactan automáticamente.
"""

import json
import logging
import re
import sys
import os
from datetime import datetime, timezone
from typing import Any


SENSITIVE_PATTERNS = [
    re.compile(r'(password|passwd|pwd)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(token|api_key|apikey|secret|auth)\s*[=:]\s*\S+', re.IGNORECASE),
    re.compile(r'(Bearer\s+)\S+', re.IGNORECASE),
    re.compile(r'(postgresql://\w+:)\S+(@)', re.IGNORECASE),
]

REDACTED = "[REDACTED]"


def redact_sensitive(text: str) -> str:
    """Redacta datos sensibles de un texto."""
    result = text
    for pattern in SENSITIVE_PATTERNS:
        if pattern.groups:
            result = pattern.sub(
                lambda m: m.group(1) + REDACTED + (m.group(2) if len(m.groups()) > 1 else ""),
                result,
            )
        else:
            result = pattern.sub(REDACTED, result)
    return result


class JSONFormatter(logging.Formatter):
    """Formateador que produce JSON estructurado."""

    def __init__(self, service: str = "yeyo"):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "message": redact_sensitive(record.getMessage()),
            "logger": record.name,
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[1].__class__.__name__,
                "message": str(record.exc_info[1]),
            }

        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False)


class YeyoLogger:
    """Factory de loggers para YeyoOS."""

    _initialized: bool = False
    _log_dir: str = "/var/log/yeyo"
    _log_level: str = "INFO"

    @classmethod
    def configure(cls, log_dir: str | None = None, log_level: str = "INFO") -> None:
        cls._log_dir = log_dir or os.getenv("LOG_DIR", "/var/log/yeyo")
        cls._log_level = log_level
        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str, service: str | None = None) -> logging.Logger:
        """Crea y configura un logger con formato JSON."""
        logger = logging.getLogger(name)

        if logger.handlers:
            return logger

        level = getattr(logging, cls._log_level, logging.INFO)
        logger.setLevel(level)

        service_name = service or name.split(".")[-1]
        formatter = JSONFormatter(service=service_name)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

        try:
            os.makedirs(cls._log_dir, exist_ok=True)
            log_file = os.path.join(cls._log_dir, f"{service_name}.log")
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except PermissionError:
            pass

        logger.propagate = False
        return logger
