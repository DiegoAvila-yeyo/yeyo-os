## ═══════════════════════════════════════
## MICRO-FASE 6.10 — Security Audit System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.10-1 [VSCODE] — Sistema de auditoría append-only con cadena SHA-256

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.10 de Capa 6 (Sistema Inmune): implementar el sistema de auditoría con log append-only y cadena de hashes SHA-256 para detección de tampering.

CONTEXTO:
- Micro-fases 6.0-6.9 completadas: Guardian completo + Dashboard
- Audit System: log append-only, NO UPDATE, NO DELETE
- Cada acción se registra: quién, qué, cuándo, dónde, resultado
- Cadena SHA-256: cada entrada incluye hash de la anterior (como blockchain simple)
- Exportable: JSON, CSV para compliance
- Buscable: por fecha, usuario, tipo de acción
- Tamper detection: si alguien modifica una entrada, la cadena se rompe

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/audit.py:

   Ruta: ~/yeyo-os/src/security/audit.py
   Contenido:

   """
   YeyoOS — Security Audit System
   Micro-fase 6.10 — Capa 6: Sistema Inmune

   Log append-only con cadena SHA-256.
   NO UPDATE, NO DELETE — cada entrada es inmutable.
   Cada entrada incluye hash de la anterior (tamper detection).
   """

   import csv
   import hashlib
   import io
   import json
   import logging
   from datetime import datetime, timezone
   from dataclasses import dataclass, field, asdict
   from pathlib import Path
   from typing import Optional
   from threading import Lock

   logger = logging.getLogger("yeyo.security.audit")

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   @dataclass
   class AuditEntry:
       """Entrada inmutable en el audit trail."""
       # Identificación
       sequence: int
       timestamp: str
       # Quién
       actor: str        # usuario, servicio, o daemon que realizó la acción
       actor_type: str   # "user", "service", "guardian", "system"
       # Qué
       action: str       # tipo de acción: "login", "file_access", "config_change", etc.
       description: str  # descripción legible
       # Dónde
       resource: str     # recurso afectado
       # Resultado
       result: str       # "success", "failure", "blocked"
       # Integridad
       previous_hash: str  # hash SHA-256 de la entrada anterior
       entry_hash: str     # hash SHA-256 de esta entrada
       # Metadata
       metadata: dict = field(default_factory=dict)

   @dataclass
   class AuditConfig:
       """Configuración del audit system."""
       log_file: str = "/var/log/yeyo/audit/audit.jsonl"
       max_entries_memory: int = 10000
       hash_algorithm: str = "sha256"

   # ═══════════════════════════════════
   # AUDIT TRAIL
   # ═══════════════════════════════════

   class AuditTrail:
       """
       Sistema de auditoría append-only con cadena SHA-256.

       REGLAS FUNDAMENTALES:
       1. NO UPDATE — las entradas nunca se modifican
       2. NO DELETE — las entradas nunca se borran
       3. Cada entrada incluye hash de la anterior
       4. Si la cadena se rompe, se detecta tampering
       """

       # Hash genesis (primera entrada)
       GENESIS_HASH = "0" * 64

       def __init__(self, config: Optional[AuditConfig] = None):
           self.config = config or AuditConfig()
           self._entries: list[AuditEntry] = []
           self._lock = Lock()
           self._sequence = 0
           self._last_hash = self.GENESIS_HASH
           self._load_existing()

       def _load_existing(self) -> None:
           """Carga entradas existentes del archivo de log."""
           path = Path(self.config.log_file)
           if not path.exists():
               return

           try:
               with open(path, "r") as f:
                   for line in f:
                       line = line.strip()
                       if not line:
                           continue
                       try:
                           data = json.loads(line)
                           entry = AuditEntry(**data)
                           self._entries.append(entry)
                           self._sequence = entry.sequence
                           self._last_hash = entry.entry_hash
                       except (json.JSONDecodeError, TypeError):
                           continue

               logger.info(f"Cargadas {len(self._entries)} entradas de audit trail")

           except OSError as e:
               logger.warning(f"Error cargando audit trail: {e}")

       # ═══════════════════════════════════
       # APPEND — Única operación de escritura
       # ═══════════════════════════════════

       def append(
           self,
           actor: str,
           actor_type: str,
           action: str,
           description: str,
           resource: str,
           result: str,
           metadata: Optional[dict] = None,
       ) -> AuditEntry:
           """
           Agrega una entrada al audit trail.
           ESTA ES LA ÚNICA FORMA DE ESCRIBIR.
           No existe update() ni delete().
           """
           with self._lock:
               self._sequence += 1

               timestamp = datetime.now(timezone.utc).isoformat()
               previous_hash = self._last_hash

               # Crear entrada sin hash propio (se calcula después)
               entry_data = {
                   "sequence": self._sequence,
                   "timestamp": timestamp,
                   "actor": actor,
                   "actor_type": actor_type,
                   "action": action,
                   "description": description,
                   "resource": resource,
                   "result": result,
                   "previous_hash": previous_hash,
                   "metadata": metadata or {},
               }

               # Calcular hash de esta entrada (incluye previous_hash)
               entry_hash = self._compute_hash(entry_data)
               entry_data["entry_hash"] = entry_hash

               entry = AuditEntry(**entry_data)

               # Almacenar en memoria
               self._entries.append(entry)
               self._last_hash = entry_hash

               # Mantener ventana en memoria
               if len(self._entries) > self.config.max_entries_memory:
                   self._entries = self._entries[-self.config.max_entries_memory:]

               # Persistir a archivo (append)
               self._persist_entry(entry)

               logger.debug(
                   f"Audit #{self._sequence}: [{action}] {actor} → {resource} = {result}"
               )

               return entry

       def _compute_hash(self, data: dict) -> str:
           """Calcula SHA-256 de una entrada."""
           # Serializar determinísticamente
           content = json.dumps(data, sort_keys=True, ensure_ascii=True)
           return hashlib.sha256(content.encode("utf-8")).hexdigest()

       def _persist_entry(self, entry: AuditEntry) -> None:
           """Persiste una entrada al archivo de log (append-only)."""
           try:
               path = Path(self.config.log_file)
               path.parent.mkdir(parents=True, exist_ok=True)

               with open(path, "a") as f:
                   f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

           except OSError as e:
               logger.error(f"Error persistiendo audit entry: {e}")

       # ═══════════════════════════════════
       # VERIFICAR INTEGRIDAD DE LA CADENA
       # ═══════════════════════════════════

       def verify_chain(self) -> tuple[bool, Optional[int]]:
           """
           Verifica la integridad de toda la cadena de hashes.
           Retorna (is_valid, first_broken_sequence).
           Si la cadena es válida: (True, None).
           Si está rota: (False, sequence_number_que_falla).
           """
           expected_prev_hash = self.GENESIS_HASH

           for entry in self._entries:
               # Verificar que previous_hash coincide
               if entry.previous_hash != expected_prev_hash:
                   logger.error(
                       f"Cadena rota en #{entry.sequence}: "
                       f"esperado prev_hash={expected_prev_hash[:16]}..., "
                       f"encontrado={entry.previous_hash[:16]}..."
                   )
                   return False, entry.sequence

               # Verificar hash propio
               entry_data = {
                   "sequence": entry.sequence,
                   "timestamp": entry.timestamp,
                   "actor": entry.actor,
                   "actor_type": entry.actor_type,
                   "action": entry.action,
                   "description": entry.description,
                   "resource": entry.resource,
                   "result": entry.result,
                   "previous_hash": entry.previous_hash,
                   "metadata": entry.metadata,
               }
               computed_hash = self._compute_hash(entry_data)

               if computed_hash != entry.entry_hash:
                   logger.error(
                       f"Hash inválido en #{entry.sequence}: "
                       f"esperado={computed_hash[:16]}..., "
                       f"encontrado={entry.entry_hash[:16]}..."
                   )
                   return False, entry.sequence

               expected_prev_hash = entry.entry_hash

           return True, None

       # ═══════════════════════════════════
       # BÚSQUEDA
       # ═══════════════════════════════════

       def search(
           self,
           actor: Optional[str] = None,
           action: Optional[str] = None,
           resource: Optional[str] = None,
           result: Optional[str] = None,
           from_date: Optional[str] = None,
           to_date: Optional[str] = None,
           limit: int = 100,
       ) -> list[AuditEntry]:
           """Busca entradas por criterios."""
           results = []

           for entry in reversed(self._entries):
               if actor and actor.lower() not in entry.actor.lower():
                   continue
               if action and action.lower() != entry.action.lower():
                   continue
               if resource and resource.lower() not in entry.resource.lower():
                   continue
               if result and result.lower() != entry.result.lower():
                   continue
               if from_date and entry.timestamp < from_date:
                   continue
               if to_date and entry.timestamp > to_date:
                   continue

               results.append(entry)

               if len(results) >= limit:
                   break

           return results

       # ═══════════════════════════════════
       # EXPORTAR
       # ═══════════════════════════════════

       def export_json(self, entries: Optional[list[AuditEntry]] = None) -> str:
           """Exporta entradas a JSON."""
           data = entries or self._entries
           return json.dumps(
               [asdict(e) for e in data],
               indent=2,
               ensure_ascii=False,
           )

       def export_csv(self, entries: Optional[list[AuditEntry]] = None) -> str:
           """Exporta entradas a CSV."""
           data = entries or self._entries
           if not data:
               return ""

           output = io.StringIO()
           fields = [
               "sequence", "timestamp", "actor", "actor_type",
               "action", "description", "resource", "result",
               "entry_hash",
           ]
           writer = csv.DictWriter(output, fieldnames=fields)
           writer.writeheader()

           for entry in data:
               row = {f: getattr(entry, f) for f in fields}
               writer.writerow(row)

           return output.getvalue()

       # ═══════════════════════════════════
       # CONSULTAS
       # ═══════════════════════════════════

       def get_entries(self, limit: int = 100) -> list[AuditEntry]:
           """Retorna las últimas N entradas."""
           return list(reversed(self._entries[-limit:]))

       def get_count(self) -> int:
           """Retorna el total de entradas."""
           return self._sequence

       def get_last_entry(self) -> Optional[AuditEntry]:
           """Retorna la última entrada."""
           return self._entries[-1] if self._entries else None

2. Crear archivo tests/unit/security/test_audit.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_audit.py
   Contenido:

   """Tests para Security Audit System — Micro-fase 6.10"""

   import pytest
   import json
   from pathlib import Path
   from src.security.audit import AuditTrail, AuditConfig, AuditEntry


   @pytest.fixture
   def tmp_config(tmp_path):
       return AuditConfig(
           log_file=str(tmp_path / "audit.jsonl"),
           max_entries_memory=100,
       )


   @pytest.fixture
   def trail(tmp_config):
       return AuditTrail(config=tmp_config)


   class TestAppendOnly:
       def test_append_creates_entry(self, trail):
           entry = trail.append(
               actor="admin",
               actor_type="user",
               action="login",
               description="Admin logged in",
               resource="/auth",
               result="success",
           )
           assert entry.sequence == 1
           assert entry.actor == "admin"
           assert entry.action == "login"

       def test_no_update_method(self, trail):
           assert not hasattr(trail, 'update')

       def test_no_delete_method(self, trail):
           assert not hasattr(trail, 'delete')

       def test_no_remove_method(self, trail):
           assert not hasattr(trail, 'remove')

       def test_sequence_increments(self, trail):
           e1 = trail.append("a", "user", "login", "d", "/r", "success")
           e2 = trail.append("b", "user", "logout", "d", "/r", "success")
           assert e1.sequence == 1
           assert e2.sequence == 2

       def test_entry_persisted_to_file(self, trail, tmp_config):
           trail.append("admin", "user", "test", "d", "/r", "success")
           path = Path(tmp_config.log_file)
           assert path.exists()
           content = path.read_text()
           assert "admin" in content


   class TestHashChain:
       def test_first_entry_has_genesis_hash(self, trail):
           entry = trail.append("a", "user", "login", "d", "/r", "success")
           assert entry.previous_hash == AuditTrail.GENESIS_HASH

       def test_second_entry_links_to_first(self, trail):
           e1 = trail.append("a", "user", "login", "d", "/r", "success")
           e2 = trail.append("b", "user", "logout", "d", "/r", "success")
           assert e2.previous_hash == e1.entry_hash

       def test_chain_valid(self, trail):
           for i in range(10):
               trail.append(f"user_{i}", "user", "action", f"desc {i}", "/r", "success")
           is_valid, broken_at = trail.verify_chain()
           assert is_valid is True
           assert broken_at is None

       def test_tampered_entry_detected(self, trail):
           trail.append("a", "user", "login", "d", "/r", "success")
           trail.append("b", "user", "action", "d", "/r", "success")
           trail.append("c", "user", "logout", "d", "/r", "success")

           # Tamper: modificar una entrada
           trail._entries[1].description = "TAMPERED"

           is_valid, broken_at = trail.verify_chain()
           assert is_valid is False
           assert broken_at == 2  # La entrada 2 falla porque el hash de 1 cambió

       def test_entry_hash_is_sha256(self, trail):
           entry = trail.append("a", "user", "login", "d", "/r", "success")
           assert len(entry.entry_hash) == 64  # SHA-256 hex = 64 chars
           assert all(c in '0123456789abcdef' for c in entry.entry_hash)


   class TestSearch:
       def test_search_by_actor(self, trail):
           trail.append("admin", "user", "login", "d", "/auth", "success")
           trail.append("guest", "user", "login", "d", "/auth", "failure")
           results = trail.search(actor="admin")
           assert len(results) == 1
           assert results[0].actor == "admin"

       def test_search_by_action(self, trail):
           trail.append("a", "user", "login", "d", "/r", "success")
           trail.append("a", "user", "logout", "d", "/r", "success")
           trail.append("a", "user", "login", "d", "/r", "success")
           results = trail.search(action="login")
           assert len(results) == 2

       def test_search_by_result(self, trail):
           trail.append("a", "user", "login", "d", "/r", "success")
           trail.append("b", "user", "login", "d", "/r", "failure")
           results = trail.search(result="failure")
           assert len(results) == 1

       def test_search_with_limit(self, trail):
           for i in range(20):
               trail.append("user", "user", "action", f"d{i}", "/r", "success")
           results = trail.search(limit=5)
           assert len(results) == 5


   class TestExport:
       def test_export_json(self, trail):
           trail.append("admin", "user", "login", "Admin login", "/auth", "success")
           exported = trail.export_json()
           data = json.loads(exported)
           assert len(data) == 1
           assert data[0]["actor"] == "admin"

       def test_export_csv(self, trail):
           trail.append("admin", "user", "login", "Admin login", "/auth", "success")
           exported = trail.export_csv()
           assert "admin" in exported
           assert "login" in exported
           assert "sequence" in exported  # Header

       def test_export_empty(self, trail):
           json_out = trail.export_json()
           assert json_out == "[]"

           csv_out = trail.export_csv()
           assert csv_out == ""


   class TestConsistency:
       def test_reload_preserves_chain(self, tmp_config):
           # Crear trail y agregar entradas
           trail1 = AuditTrail(config=tmp_config)
           trail1.append("a", "user", "login", "d", "/r", "success")
           trail1.append("b", "user", "action", "d", "/r", "success")

           # Recargar desde archivo
           trail2 = AuditTrail(config=tmp_config)
           is_valid, _ = trail2.verify_chain()
           assert is_valid is True
           assert trail2.get_count() == 2

       def test_count_accurate(self, trail):
           assert trail.get_count() == 0
           trail.append("a", "user", "login", "d", "/r", "success")
           assert trail.get_count() == 1

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_audit.py -v

VERIFICAR:
- [ ] Archivo src/security/audit.py existe con AuditTrail
- [ ] Append-only: NO existe update(), delete(), remove()
- [ ] Cadena SHA-256 válida para entradas normales
- [ ] Tampering detectado: modificar entrada rompe la cadena
- [ ] Búsqueda por actor, action, result, fecha funciona
- [ ] Exportar JSON y CSV funciona
- [ ] Persistencia: recargar desde archivo preserva cadena
- [ ] Hash SHA-256 correcto (64 chars hex)
- [ ] TODOS los tests pasan

SI FALLA:
- Hash mismatch: verificar serialización determinística (sort_keys=True)
- File lock: verificar que threading.Lock funciona
- Import error: verificar __init__.py

NO HACER:
- No crear métodos update() o delete() — NUNCA
- No permitir modificar entradas existentes
- No truncar el log de auditoría
- No usar hash débil (SIEMPRE SHA-256)

GATE: AuditTrail es append-only sin update/delete, cadena SHA-256 válida, tampering detectado, búsqueda y exportación funcionan, persistencia preserva cadena, todos los tests pasan.
```
