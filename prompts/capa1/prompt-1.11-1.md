## ═══════════════════════════════════════
## MICRO-FASE 1.11 — Logging System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 1.11-1 [VSCODE] — Sistema de logging estructurado en JSON

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.11: crear el sistema de logging estructurado con salida JSON para monitoreo del Guardian.

CONTEXTO:
- Micro-fases 1.0-1.10 completadas: interfaces, config, factory, API, WebSocket, GPU Scheduler, Event Bus, Errors listos
- Logging JSON: cada línea es un JSON válido parseable por Guardian
- Campos obligatorios: timestamp, level, service, message
- Salida: stdout + archivo en /var/log/yeyo/ (o directorio configurable)
- SEGURIDAD: datos sensibles (passwords, tokens, API keys) se redactan automáticamente
- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/logger.py:

   Ruta: ~/yeyo-os/src/core/logger.py
   Contenido:

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
   
   
   # Patrones de datos sensibles a redactar
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
           """Configura el sistema de logging globalmente."""
           cls._log_dir = log_dir or os.getenv("LOG_DIR", "/var/log/yeyo")
           cls._log_level = log_level
           cls._initialized = True
   
       @classmethod
       def get_logger(cls, name: str, service: str | None = None) -> logging.Logger:
           """
           Crea y configura un logger con formato JSON.
           
           Args:
               name: Nombre del logger (ej: "yeyo.gpu", "yeyo.ia")
               service: Nombre del servicio para el campo JSON
           """
           logger = logging.getLogger(name)
   
           if logger.handlers:
               return logger
   
           level = getattr(logging, cls._log_level, logging.INFO)
           logger.setLevel(level)
   
           service_name = service or name.split(".")[-1]
           formatter = JSONFormatter(service=service_name)
   
           # Handler stdout
           stdout_handler = logging.StreamHandler(sys.stdout)
           stdout_handler.setFormatter(formatter)
           logger.addHandler(stdout_handler)
   
           # Handler archivo (si el directorio existe o se puede crear)
           try:
               os.makedirs(cls._log_dir, exist_ok=True)
               log_file = os.path.join(cls._log_dir, f"{service_name}.log")
               file_handler = logging.FileHandler(log_file)
               file_handler.setFormatter(formatter)
               logger.addHandler(file_handler)
           except PermissionError:
               # En desarrollo puede no tener permisos para /var/log/yeyo
               pass
   
           logger.propagate = False
           return logger

2. Crear archivo tests/unit/core/test_logger.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_logger.py
   Contenido:

   """Tests para Logging System — Micro-fase 1.11"""
   
   import json
   import logging
   import pytest
   from src.core.logger import (
       YeyoLogger,
       JSONFormatter,
       redact_sensitive,
       REDACTED,
   )
   
   
   @pytest.fixture
   def tmp_log_dir(tmp_path):
       """Directorio temporal para logs."""
       log_dir = tmp_path / "logs"
       log_dir.mkdir()
       return str(log_dir)
   
   
   @pytest.fixture(autouse=True)
   def clean_loggers():
       """Limpia loggers entre tests."""
       yield
       # Eliminar handlers de loggers creados en tests
       for name in list(logging.Logger.manager.loggerDict.keys()):
           if name.startswith("yeyo.test"):
               logger = logging.getLogger(name)
               logger.handlers.clear()
   
   
   class TestJSONFormatter:
       """Tests para el formateador JSON."""
   
       def test_output_is_valid_json(self):
           formatter = JSONFormatter(service="test")
           record = logging.LogRecord(
               name="yeyo.test",
               level=logging.INFO,
               pathname="",
               lineno=0,
               msg="Hello",
               args=None,
               exc_info=None,
           )
           output = formatter.format(record)
           data = json.loads(output)
           assert isinstance(data, dict)
   
       def test_has_required_fields(self):
           formatter = JSONFormatter(service="test")
           record = logging.LogRecord(
               name="yeyo.test",
               level=logging.INFO,
               pathname="",
               lineno=0,
               msg="test message",
               args=None,
               exc_info=None,
           )
           output = formatter.format(record)
           data = json.loads(output)
           assert "timestamp" in data
           assert "level" in data
           assert "service" in data
           assert "message" in data
           assert "logger" in data
   
       def test_level_is_correct(self):
           formatter = JSONFormatter(service="test")
           record = logging.LogRecord(
               name="yeyo.test",
               level=logging.WARNING,
               pathname="",
               lineno=0,
               msg="warning",
               args=None,
               exc_info=None,
           )
           output = formatter.format(record)
           data = json.loads(output)
           assert data["level"] == "WARNING"
   
       def test_service_is_set(self):
           formatter = JSONFormatter(service="gpu_scheduler")
           record = logging.LogRecord(
               name="yeyo.test",
               level=logging.INFO,
               pathname="",
               lineno=0,
               msg="test",
               args=None,
               exc_info=None,
           )
           output = formatter.format(record)
           data = json.loads(output)
           assert data["service"] == "gpu_scheduler"
   
       def test_timestamp_is_iso_format(self):
           formatter = JSONFormatter(service="test")
           record = logging.LogRecord(
               name="yeyo.test",
               level=logging.INFO,
               pathname="",
               lineno=0,
               msg="test",
               args=None,
               exc_info=None,
           )
           output = formatter.format(record)
           data = json.loads(output)
           # ISO format contiene 'T' y termina con timezone info
           assert "T" in data["timestamp"]
   
   
   class TestRedactSensitive:
       """Tests para redacción de datos sensibles."""
   
       def test_redact_password(self):
           text = "password=my_secret_123"
           result = redact_sensitive(text)
           assert "my_secret_123" not in result
           assert REDACTED in result
   
       def test_redact_token(self):
           text = "token=abc123xyz"
           result = redact_sensitive(text)
           assert "abc123xyz" not in result
   
       def test_redact_api_key(self):
           text = "api_key=sk-123456"
           result = redact_sensitive(text)
           assert "sk-123456" not in result
   
       def test_redact_bearer_token(self):
           text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
           result = redact_sensitive(text)
           assert "eyJhbGciOiJIUzI1NiJ9" not in result
   
       def test_redact_database_url_password(self):
           text = "postgresql://yeyo:super_secret@localhost:5432/yeyo_db"
           result = redact_sensitive(text)
           assert "super_secret" not in result
   
       def test_normal_text_unchanged(self):
           text = "Processing user request for chat"
           result = redact_sensitive(text)
           assert result == text
   
   
   class TestYeyoLogger:
       """Tests para el factory de loggers."""
   
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

3. Agregar import os al principio de test_logger.py (ya está implícito via tmp_path pero lo necesitamos para os.path.join):

   Asegúrate de que el archivo test_logger.py tenga al inicio:
   import json
   import logging
   import os
   import pytest

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_logger.py -v

VERIFICAR:
- [ ] Archivo src/core/logger.py existe con YeyoLogger, JSONFormatter, redact_sensitive
- [ ] TODOS los tests pasan (0 failed)
- [ ] Output es JSON válido parseable
- [ ] Campos obligatorios: timestamp, level, service, message
- [ ] Passwords se redactan en logs
- [ ] Tokens se redactan en logs
- [ ] API keys se redactan en logs
- [ ] Bearer tokens se redactan en logs
- [ ] Database URLs con password se redactan
- [ ] Niveles de log funcionan (DEBUG, INFO, WARNING, ERROR)
- [ ] Escribe a archivo cuando tiene permisos

SI FALLA:
- PermissionError en /var/log/yeyo: el test usa tmp_path, no debería fallar
- JSON parse error: verificar que formatter retorna JSON válido
- Logger duplicate handlers: verificar el guard `if logger.handlers`
- capsys no captura: verificar que stdout_handler usa sys.stdout

NO HACER:
- No implementar log rotation (eso es configuración de producción)
- No agregar remote logging (ELK, etc.)
- No loguear datos sensibles sin redactar
- No crear loggers globales al importar el módulo

GATE: Logging JSON funcional, datos sensibles redactados, escribe a stdout y archivo, niveles de log funcionan, todos los tests pasan.
```
