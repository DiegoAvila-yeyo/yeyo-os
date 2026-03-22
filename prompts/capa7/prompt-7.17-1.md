## ═══════════════════════════════════════
## MICRO-FASE 7.17 — YeyoNet Core (Backend)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.17-1 [VSCODE] — Backend Python completo para YeyoNet: relay, sync, invitaciones y API

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.17 de Capa 7 (Evolución): implementar el backend de YeyoNet, el sistema de red privada distribuida que conecta múltiples instancias de YeyoOS. El Central es el maestro; los satélites sincronizan con él.

CONTEXTO:
- Micro-fases 7.0–7.16 completadas: LoRA pipeline, YEYO Store, ISO builder, wizard, multi-user, performance, observer, Node Studio — todos funcionando
- Stack: FastAPI (Python), Redis para colas y persistencia de códigos, PostgreSQL para estado de satélites
- Flash Memory: src/memory/flash_memory.py existe con métodos guardar(tipo, contenido, importancia) y buscar(query)
- LoRA: src/lora/trainer.py existe, los weights se guardan en ~/yeyo-os/models/lora/
- Guardian (Capa 6) está activo — todos los datos que entran/salen deben pasar por el pipeline de seguridad
- Hardware objetivo: GTX 1060 3GB — el relay y sync no deben consumir GPU
- Relay en Capa 7: WebSocket sobre Tailscale (IP estable, sin STUN/TURN por ahora)
- Arquitectura offline-first: satélites operan sin Central, encolan cambios, sincronizan al reconectar

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/yeyonet/__init__.py:

   Ruta: ~/yeyo-os/src/yeyonet/__init__.py
   Contenido:

   """
   YeyoNet — Cerebro Distribuido
   Micro-fase 7.17 — Capa 7: Evolución

   Red privada que conecta múltiples instancias de YeyoOS.
   El Central es el maestro. Los satélites son clientes.
   El aprendizaje fluye en ambas direcciones.
   """

   from .config import YeyoNetConfig, NodeType, VisibilityLevel
   from .auth import InviteCode, InviteManager
   from .relay import YeyoNetRelay
   from .sync import SyncManager
   from .satellite_manager import SatelliteManager, SatelliteStatus

   __all__ = [
       "YeyoNetConfig",
       "NodeType",
       "VisibilityLevel",
       "InviteCode",
       "InviteManager",
       "YeyoNetRelay",
       "SyncManager",
       "SatelliteManager",
       "SatelliteStatus",
   ]

2. Crear archivo src/yeyonet/config.py:

   Ruta: ~/yeyo-os/src/yeyonet/config.py
   Contenido:

   """
   YeyoNet — Configuración del nodo
   Micro-fase 7.17 — Capa 7: Evolución
   """

   from __future__ import annotations

   import os
   from dataclasses import dataclass, field
   from enum import IntEnum
   from typing import Literal


   class NodeType(str):
       CENTRAL = "central"
       SATELLITE = "satellite"


   class VisibilityLevel(IntEnum):
       """
       Niveles de visibilidad que el Central puede solicitar de un satélite.

       1 — Solo resultados: grafos creados, qué aprendió YEYO
       2 — Actividad: qué tareas corrió, cuándo, qué generó
       3 — Memoria completa: toda la Flash Memory del satélite
       4 — Control total: todo lo anterior + ejecutar tareas remotamente
       """
       RESULTS_ONLY = 1
       ACTIVITY = 2
       FULL_MEMORY = 3
       FULL_CONTROL = 4


   @dataclass
   class YeyoNetConfig:
       """Configuración completa del nodo YeyoNet (Central o Satélite)."""

       node_id: str
       node_type: Literal["central", "satellite"]
       central_url: str = ""
       auth_token: str = ""
       sync_interval_seconds: int = 60
       visibility_level: VisibilityLevel = VisibilityLevel.RESULTS_ONLY
       relay_url: str = ""
       heartbeat_interval_seconds: int = 30
       offline_queue_max_size: int = 10_000
       lora_weights_path: str = field(
           default_factory=lambda: os.path.expanduser("~/yeyo-os/models/lora/")
       )

       @classmethod
       def from_env(cls) -> "YeyoNetConfig":
           """Carga configuración desde variables de entorno."""
           return cls(
               node_id=os.environ.get("YEYONET_NODE_ID", ""),
               node_type=os.environ.get("YEYONET_NODE_TYPE", "satellite"),  # type: ignore[arg-type]
               central_url=os.environ.get("YEYONET_CENTRAL_URL", ""),
               auth_token=os.environ.get("YEYONET_AUTH_TOKEN", ""),
               sync_interval_seconds=int(os.environ.get("YEYONET_SYNC_INTERVAL", "60")),
               visibility_level=VisibilityLevel(
                   int(os.environ.get("YEYONET_VISIBILITY_LEVEL", "1"))
               ),
               relay_url=os.environ.get("YEYONET_RELAY_URL", ""),
               heartbeat_interval_seconds=int(
                   os.environ.get("YEYONET_HEARTBEAT_INTERVAL", "30")
               ),
           )

       def is_central(self) -> bool:
           return self.node_type == NodeType.CENTRAL

       def is_satellite(self) -> bool:
           return self.node_type == NodeType.SATELLITE

3. Crear archivo src/yeyonet/auth.py:

   Ruta: ~/yeyo-os/src/yeyonet/auth.py
   Contenido:

   """
   YeyoNet — Gestión de códigos de invitación
   Micro-fase 7.17 — Capa 7: Evolución

   Genera códigos YEYO-XXXX-XXXX-XXXX de un solo uso.
   Persiste en Redis con TTL según expiración configurada.
   """

   from __future__ import annotations

   import json
   import logging
   import secrets
   import string
   from dataclasses import asdict, dataclass
   from datetime import datetime, timedelta, timezone
   from typing import List, Optional

   import redis

   logger = logging.getLogger(__name__)

   _ALPHABET = string.ascii_uppercase + string.digits
   _CODE_SEGMENT_LENGTH = 4
   _CODE_SEGMENTS = 3
   _REDIS_KEY_PREFIX = "yeyonet:invite:"


   def _generate_segment() -> str:
       return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_SEGMENT_LENGTH))


   def generate_invite_code() -> str:
       """Genera un código con formato YEYO-XXXX-XXXX-XXXX."""
       segments = "-".join(_generate_segment() for _ in range(_CODE_SEGMENTS))
       return f"YEYO-{segments}"


   @dataclass
   class InviteCode:
       """Representa una invitación generada por el Central."""

       code: str
       satellite_name: str
       permissions: List[str]
       expires_at: datetime
       used: bool = False
       created_at: datetime = None  # type: ignore[assignment]

       def __post_init__(self) -> None:
           if self.created_at is None:
               self.created_at = datetime.now(timezone.utc)

       def is_expired(self) -> bool:
           now = datetime.now(timezone.utc)
           expires = self.expires_at
           if expires.tzinfo is None:
               expires = expires.replace(tzinfo=timezone.utc)
           return now > expires

       def is_valid(self) -> bool:
           return not self.used and not self.is_expired()

       def to_dict(self) -> dict:
           return {
               "code": self.code,
               "satellite_name": self.satellite_name,
               "permissions": self.permissions,
               "expires_at": self.expires_at.isoformat(),
               "used": self.used,
               "created_at": self.created_at.isoformat(),
           }

       @classmethod
       def from_dict(cls, data: dict) -> "InviteCode":
           return cls(
               code=data["code"],
               satellite_name=data["satellite_name"],
               permissions=data["permissions"],
               expires_at=datetime.fromisoformat(data["expires_at"]),
               used=data.get("used", False),
               created_at=datetime.fromisoformat(data["created_at"]),
           )


   class InviteManager:
       """
       Gestiona invitaciones YeyoNet en Redis.

       - Genera códigos únicos YEYO-XXXX-XXXX-XXXX
       - Persiste con TTL calculado desde expires_at
       - Valida y marca como usado (single-use)
       """

       def __init__(self, redis_client: redis.Redis) -> None:
           self._redis = redis_client

       def _key(self, code: str) -> str:
           return f"{_REDIS_KEY_PREFIX}{code}"

       def create(
           self,
           satellite_name: str,
           permissions: List[str],
           expires_in_days: int = 7,
       ) -> InviteCode:
           """Genera y persiste un código de invitación de un solo uso."""
           code = generate_invite_code()
           expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
           invite = InviteCode(
               code=code,
               satellite_name=satellite_name,
               permissions=permissions,
               expires_at=expires_at,
           )
           ttl_seconds = int(timedelta(days=expires_in_days).total_seconds())
           self._redis.setex(
               self._key(code),
               ttl_seconds,
               json.dumps(invite.to_dict()),
           )
           logger.info(f"Invitación creada: {code} para '{satellite_name}' (expira en {expires_in_days}d)")
           return invite

       def get(self, code: str) -> Optional[InviteCode]:
           """Recupera una invitación por código. Retorna None si no existe o expiró."""
           raw = self._redis.get(self._key(code))
           if raw is None:
               return None
           try:
               return InviteCode.from_dict(json.loads(raw))
           except (json.JSONDecodeError, KeyError) as e:
               logger.error(f"Error al deserializar invitación {code}: {e}")
               return None

       def validate(self, code: str) -> Optional[InviteCode]:
           """Valida que el código existe, no ha sido usado, y no expiró."""
           invite = self.get(code)
           if invite is None:
               logger.warning(f"Código no encontrado: {code}")
               return None
           if not invite.is_valid():
               logger.warning(f"Código inválido (usado={invite.used}, expirado={invite.is_expired()}): {code}")
               return None
           return invite

       def mark_used(self, code: str) -> bool:
           """Marca el código como usado. Retorna True si el update fue exitoso."""
           invite = self.get(code)
           if invite is None:
               return False
           invite.used = True
           # Mantener TTL restante
           ttl = self._redis.ttl(self._key(code))
           if ttl > 0:
               self._redis.setex(self._key(code), ttl, json.dumps(invite.to_dict()))
           else:
               self._redis.set(self._key(code), json.dumps(invite.to_dict()))
           logger.info(f"Código marcado como usado: {code}")
           return True

       def revoke(self, code: str) -> bool:
           """Elimina un código de Redis (revocación manual)."""
           deleted = self._redis.delete(self._key(code))
           if deleted:
               logger.info(f"Código revocado: {code}")
           return bool(deleted)

4. Crear archivo src/yeyonet/relay.py:

   Ruta: ~/yeyo-os/src/yeyonet/relay.py
   Contenido:

   """
   YeyoNet — Relay WebSocket
   Micro-fase 7.17 — Capa 7: Evolución

   Cliente WebSocket que mantiene conexión persistente con el Central.
   Reconexión automática con exponential backoff.
   Ping/pong heartbeat para detectar caídas.
   """

   from __future__ import annotations

   import asyncio
   import json
   import logging
   from typing import Any, Callable, Coroutine, Dict, Optional

   import websockets
   from websockets.exceptions import ConnectionClosed, WebSocketException

   logger = logging.getLogger(__name__)

   _BACKOFF_BASE = 1.0
   _BACKOFF_MULTIPLIER = 2.0
   _BACKOFF_MAX = 60.0


   MessageHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


   class YeyoNetRelay:
       """
       Cliente WebSocket con reconexión automática para comunicación con el Central.

       Usa exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s (máximo).
       Ping/pong cada heartbeat_interval_seconds para detectar caídas silenciosas.
       """

       def __init__(
           self,
           relay_url: str,
           auth_token: str,
           node_id: str,
           heartbeat_interval: int = 30,
           on_message: Optional[MessageHandler] = None,
           on_connected: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
           on_disconnected: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
       ) -> None:
           self._relay_url = relay_url
           self._auth_token = auth_token
           self._node_id = node_id
           self._heartbeat_interval = heartbeat_interval
           self._on_message = on_message
           self._on_connected = on_connected
           self._on_disconnected = on_disconnected
           self._ws: Optional[websockets.WebSocketClientProtocol] = None
           self._running = False
           self._backoff = _BACKOFF_BASE

       async def send(self, message: Dict[str, Any]) -> None:
           """Envía un mensaje JSON al relay. No-op si no hay conexión."""
           if self._ws is None:
               logger.warning("YeyoNetRelay: intento de envío sin conexión activa")
               return
           try:
               await self._ws.send(json.dumps(message))
           except (ConnectionClosed, WebSocketException) as e:
               logger.error(f"YeyoNetRelay: error al enviar mensaje: {e}")

       async def start(self) -> None:
           """Inicia el loop de conexión persistente. Llamar con asyncio.create_task()."""
           self._running = True
           while self._running:
               try:
                   await self._connect_and_run()
                   self._backoff = _BACKOFF_BASE
               except Exception as e:
                   logger.error(f"YeyoNetRelay: conexión perdida ({e}), reintentando en {self._backoff:.0f}s")
                   await asyncio.sleep(self._backoff)
                   self._backoff = min(self._backoff * _BACKOFF_MULTIPLIER, _BACKOFF_MAX)

       async def stop(self) -> None:
           """Detiene el relay limpiamente."""
           self._running = False
           if self._ws is not None:
               await self._ws.close()

       async def _connect_and_run(self) -> None:
           headers = {
               "Authorization": f"Bearer {self._auth_token}",
               "X-YeyoNet-Node-ID": self._node_id,
           }
           async with websockets.connect(self._relay_url, extra_headers=headers) as ws:
               self._ws = ws
               logger.info(f"YeyoNetRelay: conectado a {self._relay_url}")
               if self._on_connected:
                   await self._on_connected()

               try:
                   await asyncio.gather(
                       self._receive_loop(ws),
                       self._heartbeat_loop(ws),
                   )
               finally:
                   self._ws = None
                   if self._on_disconnected:
                       await self._on_disconnected()

       async def _receive_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
           async for raw in ws:
               try:
                   message = json.loads(raw)
               except json.JSONDecodeError as e:
                   logger.error(f"YeyoNetRelay: mensaje inválido recibido: {e}")
                   continue
               if self._on_message:
                   try:
                       await self._on_message(message)
                   except Exception as e:
                       logger.error(f"YeyoNetRelay: error en handler de mensaje: {e}")

       async def _heartbeat_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
           while True:
               await asyncio.sleep(self._heartbeat_interval)
               try:
                   pong = await ws.ping()
                   await asyncio.wait_for(pong, timeout=10.0)
               except (asyncio.TimeoutError, ConnectionClosed) as e:
                   logger.warning(f"YeyoNetRelay: heartbeat fallido: {e}")
                   raise

5. Crear archivo src/yeyonet/sync.py:

   Ruta: ~/yeyo-os/src/yeyonet/sync.py
   Contenido:

   """
   YeyoNet — Sincronización de Flash Memory y LoRA weights
   Micro-fase 7.17 — Capa 7: Evolución

   SyncManager gestiona:
   - Flash Memory entries: satélite → Central
   - LoRA weights: Central → satélite
   - Grafos de IA: bidireccional
   - Cola offline: guarda cambios cuando Central no está disponible,
     los procesa al reconectar en orden FIFO.
   """

   from __future__ import annotations

   import json
   import logging
   import os
   import shutil
   from dataclasses import dataclass
   from datetime import datetime, timezone
   from typing import Any, Dict, List, Optional

   import redis

   logger = logging.getLogger(__name__)

   _OFFLINE_QUEUE_KEY = "yeyonet:offline_queue"
   _LAST_SYNC_KEY = "yeyonet:last_sync_ts"
   _LORA_VERSION_KEY = "yeyonet:lora_version"


   @dataclass
   class SyncEntry:
       """Un item en la cola offline."""
       entry_type: str
       payload: Dict[str, Any]
       timestamp: str
       node_id: str

       def to_dict(self) -> Dict[str, Any]:
           return {
               "entry_type": self.entry_type,
               "payload": self.payload,
               "timestamp": self.timestamp,
               "node_id": self.node_id,
           }

       @classmethod
       def from_dict(cls, data: Dict[str, Any]) -> "SyncEntry":
           return cls(
               entry_type=data["entry_type"],
               payload=data["payload"],
               timestamp=data["timestamp"],
               node_id=data["node_id"],
           )


   class SyncManager:
       """
       Gestiona la sincronización bidireccional entre satélite y Central.

       Flujo offline:
       1. Cambio ocurre mientras Central está offline
       2. Se guarda en Redis list (LPUSH) con timestamp
       3. Al reconectar, _process_offline_queue() vacía la cola FIFO (RPOP)
       4. Conflictos resueltos por timestamp: el más reciente gana
       """

       def __init__(
           self,
           redis_client: redis.Redis,
           node_id: str,
           lora_weights_path: str,
           max_queue_size: int = 10_000,
       ) -> None:
           self._redis = redis_client
           self._node_id = node_id
           self._lora_weights_path = lora_weights_path
           self._max_queue_size = max_queue_size

       # ── Offline Queue ──────────────────────────────────────────────────────

       def enqueue_offline(self, entry_type: str, payload: Dict[str, Any]) -> None:
           """Guarda un cambio en la cola offline (LIFO push, FIFO pop)."""
           queue_size = self._redis.llen(_OFFLINE_QUEUE_KEY)
           if queue_size >= self._max_queue_size:
               logger.warning(f"SyncManager: cola offline llena ({queue_size} items), descartando más viejo")
               self._redis.rpop(_OFFLINE_QUEUE_KEY)
           entry = SyncEntry(
               entry_type=entry_type,
               payload=payload,
               timestamp=datetime.now(timezone.utc).isoformat(),
               node_id=self._node_id,
           )
           self._redis.lpush(_OFFLINE_QUEUE_KEY, json.dumps(entry.to_dict()))
           logger.debug(f"SyncManager: encolado offline: {entry_type}")

       def get_offline_queue(self) -> List[SyncEntry]:
           """Retorna todos los items en cola (sin eliminar), del más viejo al más nuevo."""
           raw_items = self._redis.lrange(_OFFLINE_QUEUE_KEY, 0, -1)
           entries = []
           for raw in reversed(raw_items):
               try:
                   entries.append(SyncEntry.from_dict(json.loads(raw)))
               except (json.JSONDecodeError, KeyError) as e:
                   logger.error(f"SyncManager: entrada offline corrupta: {e}")
           return entries

       def clear_offline_queue(self) -> int:
           """Vacía la cola offline. Retorna la cantidad de items eliminados."""
           size = self._redis.llen(_OFFLINE_QUEUE_KEY)
           self._redis.delete(_OFFLINE_QUEUE_KEY)
           logger.info(f"SyncManager: cola offline vaciada ({size} items)")
           return int(size)

       # ── Flash Memory Sync ──────────────────────────────────────────────────

       def get_pending_flash_entries(
           self,
           flash_memory_entries: List[Dict[str, Any]],
       ) -> List[Dict[str, Any]]:
           """
           Filtra las Flash Memory entries que no han sido sincronizadas.
           Compara por timestamp contra el último sync guardado en Redis.
           """
           last_sync_raw = self._redis.get(_LAST_SYNC_KEY)
           if last_sync_raw is None:
               return flash_memory_entries

           last_sync_ts = datetime.fromisoformat(last_sync_raw.decode())
           pending = []
           for entry in flash_memory_entries:
               entry_ts_raw = entry.get("timestamp") or entry.get("created_at", "")
               try:
                   entry_ts = datetime.fromisoformat(entry_ts_raw)
                   if entry_ts.tzinfo is None:
                       entry_ts = entry_ts.replace(tzinfo=timezone.utc)
                   if last_sync_ts.tzinfo is None:
                       last_sync_ts = last_sync_ts.replace(tzinfo=timezone.utc)
                   if entry_ts > last_sync_ts:
                       pending.append(entry)
               except (ValueError, TypeError):
                   pending.append(entry)
           return pending

       def mark_flash_synced(self) -> None:
           """Registra el timestamp del último sync exitoso."""
           self._redis.set(_LAST_SYNC_KEY, datetime.now(timezone.utc).isoformat())

       def resolve_conflict(
           self,
           local: Dict[str, Any],
           remote: Dict[str, Any],
       ) -> Dict[str, Any]:
           """
           Resuelve conflictos entre entrada local y remota.
           Estrategia: timestamp más reciente gana.
           """
           def parse_ts(entry: Dict[str, Any]) -> datetime:
               raw = entry.get("timestamp") or entry.get("created_at", "1970-01-01T00:00:00")
               try:
                   ts = datetime.fromisoformat(raw)
                   return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
               except (ValueError, TypeError):
                   return datetime(1970, 1, 1, tzinfo=timezone.utc)

           return local if parse_ts(local) >= parse_ts(remote) else remote

       # ── LoRA Weights Sync ──────────────────────────────────────────────────

       def get_local_lora_version(self) -> Optional[str]:
           """Retorna la versión del LoRA local guardada en Redis."""
           raw = self._redis.get(_LORA_VERSION_KEY)
           return raw.decode() if raw else None

       def apply_lora_weights(self, weights_path: str, version: str) -> bool:
           """
           Aplica nuevos LoRA weights recibidos del Central.
           Hace backup del anterior antes de reemplazar.
           Retorna True si el update fue exitoso.
           """
           if not os.path.exists(weights_path):
               logger.error(f"SyncManager: archivo de weights no encontrado: {weights_path}")
               return False

           backup_path = f"{self._lora_weights_path}/backup_before_{version}"
           try:
               if os.path.exists(self._lora_weights_path):
                   os.makedirs(backup_path, exist_ok=True)
                   for f in os.listdir(self._lora_weights_path):
                       if not f.startswith("backup_"):
                           shutil.copy2(
                               os.path.join(self._lora_weights_path, f),
                               os.path.join(backup_path, f),
                           )
               shutil.copy2(weights_path, self._lora_weights_path)
               self._redis.set(_LORA_VERSION_KEY, version)
               logger.info(f"SyncManager: LoRA weights actualizados a versión {version}")
               return True
           except (OSError, shutil.Error) as e:
               logger.error(f"SyncManager: error aplicando LoRA weights: {e}")
               return False

6. Crear archivo src/yeyonet/satellite_manager.py:

   Ruta: ~/yeyo-os/src/yeyonet/satellite_manager.py
   Contenido:

   """
   YeyoNet — Gestión de satélites (lado Central)
   Micro-fase 7.17 — Capa 7: Evolución

   SatelliteManager mantiene el registro de satélites conectados,
   sus estados y los datos que se exponen según el visibility_level.
   """

   from __future__ import annotations

   import json
   import logging
   from dataclasses import dataclass, field
   from datetime import datetime, timedelta, timezone
   from enum import Enum
   from typing import Any, Dict, List, Optional

   import redis

   logger = logging.getLogger(__name__)

   _SATELLITES_KEY = "yeyonet:satellites"
   _ONLINE_THRESHOLD_MINUTES = 5
   _IDLE_THRESHOLD_MINUTES = 60


   class SatelliteStatus(str, Enum):
       ONLINE = "online"
       IDLE = "idle"
       OFFLINE = "offline"


   @dataclass
   class Satellite:
       """Representa un satélite registrado en el Central."""
       satellite_id: str
       name: str
       permissions: List[str]
       visibility_level: int
       last_seen: Optional[datetime] = None
       connected_at: Optional[datetime] = None
       node_mode: int = 1

       def get_status(self) -> SatelliteStatus:
           if self.last_seen is None:
               return SatelliteStatus.OFFLINE
           now = datetime.now(timezone.utc)
           last = self.last_seen
           if last.tzinfo is None:
               last = last.replace(tzinfo=timezone.utc)
           delta = now - last
           if delta < timedelta(minutes=_ONLINE_THRESHOLD_MINUTES):
               return SatelliteStatus.ONLINE
           if delta < timedelta(minutes=_IDLE_THRESHOLD_MINUTES):
               return SatelliteStatus.IDLE
           return SatelliteStatus.OFFLINE

       def to_dict(self) -> Dict[str, Any]:
           return {
               "satellite_id": self.satellite_id,
               "name": self.name,
               "permissions": self.permissions,
               "visibility_level": self.visibility_level,
               "last_seen": self.last_seen.isoformat() if self.last_seen else None,
               "connected_at": self.connected_at.isoformat() if self.connected_at else None,
               "node_mode": self.node_mode,
               "status": self.get_status().value,
           }

       @classmethod
       def from_dict(cls, data: Dict[str, Any]) -> "Satellite":
           return cls(
               satellite_id=data["satellite_id"],
               name=data["name"],
               permissions=data.get("permissions", []),
               visibility_level=data.get("visibility_level", 1),
               last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
               connected_at=datetime.fromisoformat(data["connected_at"]) if data.get("connected_at") else None,
               node_mode=data.get("node_mode", 1),
           )


   class SatelliteManager:
       """
       Gestiona el registro de satélites conectados al Central.

       Persiste en Redis hash: yeyonet:satellites -> {satellite_id: JSON}
       """

       def __init__(self, redis_client: redis.Redis) -> None:
           self._redis = redis_client

       def register(self, satellite: Satellite) -> None:
           """Registra o actualiza un satélite."""
           self._redis.hset(_SATELLITES_KEY, satellite.satellite_id, json.dumps(satellite.to_dict()))
           logger.info(f"SatelliteManager: satélite registrado: {satellite.name} ({satellite.satellite_id})")

       def get(self, satellite_id: str) -> Optional[Satellite]:
           """Recupera un satélite por ID."""
           raw = self._redis.hget(_SATELLITES_KEY, satellite_id)
           if raw is None:
               return None
           try:
               return Satellite.from_dict(json.loads(raw))
           except (json.JSONDecodeError, KeyError) as e:
               logger.error(f"SatelliteManager: error al deserializar satélite {satellite_id}: {e}")
               return None

       def list_all(self) -> List[Satellite]:
           """Lista todos los satélites registrados."""
           raw_map = self._redis.hgetall(_SATELLITES_KEY)
           satellites = []
           for raw in raw_map.values():
               try:
                   satellites.append(Satellite.from_dict(json.loads(raw)))
               except (json.JSONDecodeError, KeyError) as e:
                   logger.error(f"SatelliteManager: satélite corrupto en Redis: {e}")
           return sorted(satellites, key=lambda s: s.name)

       def update_last_seen(self, satellite_id: str) -> bool:
           """Actualiza el último ping del satélite. Retorna True si existe."""
           satellite = self.get(satellite_id)
           if satellite is None:
               return False
           satellite.last_seen = datetime.now(timezone.utc)
           self.register(satellite)
           return True

       def disconnect(self, satellite_id: str) -> bool:
           """Elimina un satélite del registro. Retorna True si existía."""
           deleted = self._redis.hdel(_SATELLITES_KEY, satellite_id)
           if deleted:
               logger.info(f"SatelliteManager: satélite desconectado: {satellite_id}")
           return bool(deleted)

       def apply_visibility_filter(
           self,
           satellite: Satellite,
           data: Dict[str, Any],
       ) -> Dict[str, Any]:
           """
           Filtra los datos del satélite según su visibility_level.

           Nivel 1: solo grafos y aprendizaje
           Nivel 2: + actividad (tareas, timestamps)
           Nivel 3: + Flash Memory completa
           Nivel 4: todo (+ control remoto habilitado)
           """
           level = satellite.visibility_level
           filtered: Dict[str, Any] = {}

           if level >= 1:
               filtered["graphs"] = data.get("graphs", [])
               filtered["learned_skills"] = data.get("learned_skills", [])

           if level >= 2:
               filtered["activity_log"] = data.get("activity_log", [])
               filtered["task_history"] = data.get("task_history", [])

           if level >= 3:
               filtered["flash_memory"] = data.get("flash_memory", [])

           if level >= 4:
               filtered["remote_control_enabled"] = True

           return filtered

7. Crear archivo src/api/yeyonet_api.py:

   Ruta: ~/yeyo-os/src/api/yeyonet_api.py
   Contenido:

   """
   YeyoNet — API endpoints FastAPI
   Micro-fase 7.17 — Capa 7: Evolución

   Endpoints:
   POST /api/yeyonet/invite           — Central genera código de invitación
   GET  /api/yeyonet/satellites       — Central lista sus satélites
   DELETE /api/yeyonet/satellites/{id} — Central desconecta un satélite
   POST /api/yeyonet/connect          — Satélite usa código para conectar
   GET  /api/yeyonet/status           — Estado del nodo actual
   """

   from __future__ import annotations

   import logging
   import os
   import uuid
   from datetime import datetime, timezone
   from typing import List, Optional

   import redis
   from fastapi import APIRouter, Depends, HTTPException, status
   from pydantic import BaseModel, Field

   from src.yeyonet.auth import InviteCode, InviteManager
   from src.yeyonet.config import VisibilityLevel, YeyoNetConfig
   from src.yeyonet.satellite_manager import Satellite, SatelliteManager

   logger = logging.getLogger(__name__)

   router = APIRouter(prefix="/api/yeyonet", tags=["yeyonet"])


   # ── Dependencias ────────────────────────────────────────────────────────────

   def get_redis() -> redis.Redis:
       return redis.Redis(
           host=os.environ.get("REDIS_HOST", "localhost"),
           port=int(os.environ.get("REDIS_PORT", "6379")),
           decode_responses=True,
       )


   def get_invite_manager(r: redis.Redis = Depends(get_redis)) -> InviteManager:
       return InviteManager(r)


   def get_satellite_manager(r: redis.Redis = Depends(get_redis)) -> SatelliteManager:
       return SatelliteManager(r)


   def get_config() -> YeyoNetConfig:
       return YeyoNetConfig.from_env()


   # ── Schemas ─────────────────────────────────────────────────────────────────

   class CreateInviteRequest(BaseModel):
       satellite_name: str = Field(..., min_length=1, max_length=100)
       permissions: List[str] = Field(default=["chat"])
       expires_in_days: int = Field(default=7, ge=1, le=30)
       visibility_level: int = Field(default=1, ge=1, le=4)


   class InviteResponse(BaseModel):
       code: str
       satellite_name: str
       permissions: List[str]
       expires_at: str
       created_at: str


   class SatelliteResponse(BaseModel):
       satellite_id: str
       name: str
       permissions: List[str]
       visibility_level: int
       status: str
       last_seen: Optional[str]
       connected_at: Optional[str]
       node_mode: int


   class ConnectRequest(BaseModel):
       code: str = Field(..., min_length=18, max_length=22)
       node_id: Optional[str] = None
       node_mode: int = Field(default=1, ge=1, le=3)


   class ConnectResponse(BaseModel):
       ok: bool
       satellite_id: str
       satellite_name: str
       permissions: List[str]
       visibility_level: int
       central_url: str


   class StatusResponse(BaseModel):
       node_id: str
       node_type: str
       is_connected: bool
       satellites_count: int
       pending_sync_count: int


   # ── Endpoints ────────────────────────────────────────────────────────────────

   @router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
   async def create_invite(
       req: CreateInviteRequest,
       invite_mgr: InviteManager = Depends(get_invite_manager),
       config: YeyoNetConfig = Depends(get_config),
   ) -> InviteResponse:
       """Central genera un código de invitación de un solo uso para un nuevo satélite."""
       if not config.is_central():
           raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail="Solo el Central puede generar invitaciones",
           )
       invite = invite_mgr.create(
           satellite_name=req.satellite_name,
           permissions=req.permissions,
           expires_in_days=req.expires_in_days,
       )
       return InviteResponse(
           code=invite.code,
           satellite_name=invite.satellite_name,
           permissions=invite.permissions,
           expires_at=invite.expires_at.isoformat(),
           created_at=invite.created_at.isoformat(),
       )


   @router.get("/satellites", response_model=List[SatelliteResponse])
   async def list_satellites(
       satellite_mgr: SatelliteManager = Depends(get_satellite_manager),
       config: YeyoNetConfig = Depends(get_config),
   ) -> List[SatelliteResponse]:
       """Central lista todos sus satélites con estado actual."""
       if not config.is_central():
           raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail="Solo el Central puede listar satélites",
           )
       satellites = satellite_mgr.list_all()
       return [
           SatelliteResponse(
               satellite_id=s.satellite_id,
               name=s.name,
               permissions=s.permissions,
               visibility_level=s.visibility_level,
               status=s.get_status().value,
               last_seen=s.last_seen.isoformat() if s.last_seen else None,
               connected_at=s.connected_at.isoformat() if s.connected_at else None,
               node_mode=s.node_mode,
           )
           for s in satellites
       ]


   @router.delete("/satellites/{satellite_id}", status_code=status.HTTP_204_NO_CONTENT)
   async def disconnect_satellite(
       satellite_id: str,
       satellite_mgr: SatelliteManager = Depends(get_satellite_manager),
       config: YeyoNetConfig = Depends(get_config),
   ) -> None:
       """Central desconecta y elimina un satélite del registro."""
       if not config.is_central():
           raise HTTPException(
               status_code=status.HTTP_403_FORBIDDEN,
               detail="Solo el Central puede desconectar satélites",
           )
       removed = satellite_mgr.disconnect(satellite_id)
       if not removed:
           raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail=f"Satélite no encontrado: {satellite_id}",
           )


   @router.post("/connect", response_model=ConnectResponse)
   async def connect_satellite(
       req: ConnectRequest,
       invite_mgr: InviteManager = Depends(get_invite_manager),
       satellite_mgr: SatelliteManager = Depends(get_satellite_manager),
       config: YeyoNetConfig = Depends(get_config),
   ) -> ConnectResponse:
       """
       Satélite usa un código de invitación para conectarse al Central.
       Valida el código, registra el satélite, marca el código como usado.
       """
       invite = invite_mgr.validate(req.code)
       if invite is None:
           raise HTTPException(
               status_code=status.HTTP_400_BAD_REQUEST,
               detail="Código inválido, expirado o ya utilizado",
           )

       satellite_id = req.node_id or str(uuid.uuid4())
       satellite = Satellite(
           satellite_id=satellite_id,
           name=invite.satellite_name,
           permissions=invite.permissions,
           visibility_level=1,
           last_seen=datetime.now(timezone.utc),
           connected_at=datetime.now(timezone.utc),
           node_mode=req.node_mode,
       )
       satellite_mgr.register(satellite)
       invite_mgr.mark_used(req.code)

       logger.info(f"Satélite conectado: {invite.satellite_name} (id={satellite_id})")

       return ConnectResponse(
           ok=True,
           satellite_id=satellite_id,
           satellite_name=invite.satellite_name,
           permissions=invite.permissions,
           visibility_level=1,
           central_url=config.central_url,
       )


   @router.get("/status", response_model=StatusResponse)
   async def get_status(
       satellite_mgr: SatelliteManager = Depends(get_satellite_manager),
       config: YeyoNetConfig = Depends(get_config),
       r: redis.Redis = Depends(get_redis),
   ) -> StatusResponse:
       """Retorna el estado actual del nodo (Central o Satélite)."""
       satellites = satellite_mgr.list_all() if config.is_central() else []
       pending = r.llen("yeyonet:offline_queue")
       return StatusResponse(
           node_id=config.node_id,
           node_type=config.node_type,
           is_connected=True,
           satellites_count=len(satellites),
           pending_sync_count=int(pending),
       )

8. Crear archivo tests/test_yeyonet.py:

   Ruta: ~/yeyo-os/tests/test_yeyonet.py
   Contenido:

   """
   Tests para YeyoNet Core — Micro-fase 7.17

   Cubre: InviteManager, SatelliteManager, SyncManager y endpoints API.
   Usa fakeredis para no requerir Redis real en CI.
   """

   import json
   import os
   import uuid
   from datetime import datetime, timedelta, timezone
   from unittest.mock import MagicMock, patch

   import fakeredis
   import pytest
   from fastapi import FastAPI
   from fastapi.testclient import TestClient

   from src.yeyonet.auth import InviteManager, generate_invite_code
   from src.yeyonet.config import VisibilityLevel, YeyoNetConfig
   from src.yeyonet.satellite_manager import Satellite, SatelliteManager, SatelliteStatus
   from src.yeyonet.sync import SyncManager


   # ── Fixtures ─────────────────────────────────────────────────────────────────

   @pytest.fixture
   def fake_redis():
       return fakeredis.FakeRedis(decode_responses=True)


   @pytest.fixture
   def invite_manager(fake_redis):
       return InviteManager(fake_redis)


   @pytest.fixture
   def satellite_manager(fake_redis):
       return SatelliteManager(fake_redis)


   @pytest.fixture
   def sync_manager(fake_redis, tmp_path):
       return SyncManager(
           redis_client=fake_redis,
           node_id="test-node-01",
           lora_weights_path=str(tmp_path / "lora"),
           max_queue_size=100,
       )


   @pytest.fixture
   def api_client(fake_redis):
       """Cliente FastAPI con Redis mockeado para tests de endpoints."""
       from src.api.yeyonet_api import router, get_redis, get_config

       app = FastAPI()
       app.include_router(router)

       central_config = YeyoNetConfig(
           node_id="central-01",
           node_type="central",
           central_url="ws://localhost:8765",
       )

       app.dependency_overrides[get_redis] = lambda: fake_redis
       app.dependency_overrides[get_config] = lambda: central_config

       return TestClient(app)


   # ── Tests: generate_invite_code ───────────────────────────────────────────────

   def test_invite_code_formato():
       code = generate_invite_code()
       assert code.startswith("YEYO-")
       parts = code.split("-")
       assert len(parts) == 4
       assert all(len(p) == 4 for p in parts[1:])


   def test_invite_code_unicidad():
       codes = {generate_invite_code() for _ in range(100)}
       assert len(codes) == 100


   # ── Tests: InviteManager ──────────────────────────────────────────────────────

   def test_invite_manager_crea_y_recupera(invite_manager):
       invite = invite_manager.create("Laptop Viaje", ["chat", "grafos"], expires_in_days=7)
       recovered = invite_manager.get(invite.code)
       assert recovered is not None
       assert recovered.satellite_name == "Laptop Viaje"
       assert recovered.permissions == ["chat", "grafos"]
       assert not recovered.used


   def test_invite_manager_valida_codigo_valido(invite_manager):
       invite = invite_manager.create("Test Sat", ["chat"])
       result = invite_manager.validate(invite.code)
       assert result is not None
       assert result.code == invite.code


   def test_invite_manager_valida_codigo_inexistente(invite_manager):
       assert invite_manager.validate("YEYO-FAKE-CODE-XXXX") is None


   def test_invite_manager_marca_usado(invite_manager):
       invite = invite_manager.create("Sat", ["chat"])
       invite_manager.mark_used(invite.code)
       recovered = invite_manager.get(invite.code)
       assert recovered.used is True


   def test_invite_manager_no_valida_usado(invite_manager):
       invite = invite_manager.create("Sat", ["chat"])
       invite_manager.mark_used(invite.code)
       assert invite_manager.validate(invite.code) is None


   def test_invite_manager_revoca(invite_manager):
       invite = invite_manager.create("Sat", ["chat"])
       invite_manager.revoke(invite.code)
       assert invite_manager.get(invite.code) is None


   def test_invite_expirado_invalido(invite_manager):
       invite = invite_manager.create("Sat", ["chat"], expires_in_days=7)
       invite._redis = invite_manager._redis
       # Simular expiración manual
       invite_obj = invite_manager.get(invite.code)
       invite_obj.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
       import json
       invite_manager._redis.set(
           f"yeyonet:invite:{invite.code}",
           json.dumps(invite_obj.to_dict()),
       )
       assert invite_manager.validate(invite.code) is None


   # ── Tests: SatelliteManager ───────────────────────────────────────────────────

   def test_satellite_manager_registra_y_lista(satellite_manager):
       sat = Satellite(
           satellite_id="sat-001",
           name="Laptop Test",
           permissions=["chat"],
           visibility_level=1,
           last_seen=datetime.now(timezone.utc),
       )
       satellite_manager.register(sat)
       satellites = satellite_manager.list_all()
       assert len(satellites) == 1
       assert satellites[0].satellite_id == "sat-001"


   def test_satellite_manager_estado_online(satellite_manager):
       sat = Satellite(
           satellite_id="sat-002",
           name="Sat Online",
           permissions=[],
           visibility_level=1,
           last_seen=datetime.now(timezone.utc),
       )
       satellite_manager.register(sat)
       recovered = satellite_manager.get("sat-002")
       assert recovered.get_status() == SatelliteStatus.ONLINE


   def test_satellite_manager_estado_offline(satellite_manager):
       sat = Satellite(
           satellite_id="sat-003",
           name="Sat Offline",
           permissions=[],
           visibility_level=1,
           last_seen=datetime.now(timezone.utc) - timedelta(hours=2),
       )
       satellite_manager.register(sat)
       recovered = satellite_manager.get("sat-003")
       assert recovered.get_status() == SatelliteStatus.OFFLINE


   def test_satellite_manager_desconecta(satellite_manager):
       sat = Satellite(
           satellite_id="sat-004",
           name="Sat Delete",
           permissions=[],
           visibility_level=1,
       )
       satellite_manager.register(sat)
       satellite_manager.disconnect("sat-004")
       assert satellite_manager.get("sat-004") is None


   def test_satellite_manager_visibility_filter_nivel1(satellite_manager):
       sat = Satellite("id", "name", [], 1)
       data = {
           "graphs": [{"id": "g1"}],
           "learned_skills": ["skill1"],
           "activity_log": ["task"],
           "flash_memory": [{"content": "secret"}],
       }
       filtered = satellite_manager.apply_visibility_filter(sat, data)
       assert "graphs" in filtered
       assert "activity_log" not in filtered
       assert "flash_memory" not in filtered


   def test_satellite_manager_visibility_filter_nivel4(satellite_manager):
       sat = Satellite("id", "name", [], 4)
       data = {
           "graphs": [],
           "activity_log": [],
           "flash_memory": [{"content": "data"}],
       }
       filtered = satellite_manager.apply_visibility_filter(sat, data)
       assert "flash_memory" in filtered
       assert filtered.get("remote_control_enabled") is True


   # ── Tests: SyncManager ────────────────────────────────────────────────────────

   def test_sync_manager_enqueue_offline(sync_manager):
       sync_manager.enqueue_offline("flash_memory", {"content": "test", "timestamp": "2024-01-01T00:00:00"})
       queue = sync_manager.get_offline_queue()
       assert len(queue) == 1
       assert queue[0].entry_type == "flash_memory"


   def test_sync_manager_clear_offline_queue(sync_manager):
       sync_manager.enqueue_offline("flash_memory", {"content": "a"})
       sync_manager.enqueue_offline("flash_memory", {"content": "b"})
       count = sync_manager.clear_offline_queue()
       assert count == 2
       assert len(sync_manager.get_offline_queue()) == 0


   def test_sync_manager_pending_flash_entries(sync_manager):
       entries = [
           {"content": "old", "timestamp": "2020-01-01T00:00:00"},
           {"content": "new", "timestamp": "2030-01-01T00:00:00"},
       ]
       sync_manager.mark_flash_synced()
       pending = sync_manager.get_pending_flash_entries(entries)
       assert len(pending) == 1
       assert pending[0]["content"] == "new"


   def test_sync_manager_resolve_conflict_reciente_gana(sync_manager):
       local = {"content": "local", "timestamp": "2024-06-01T12:00:00+00:00"}
       remote = {"content": "remote", "timestamp": "2024-06-01T10:00:00+00:00"}
       winner = sync_manager.resolve_conflict(local, remote)
       assert winner["content"] == "local"


   def test_sync_manager_offline_queue_max_size(sync_manager):
       sync_manager._max_queue_size = 3
       for i in range(5):
           sync_manager.enqueue_offline("test", {"i": i})
       queue = sync_manager.get_offline_queue()
       assert len(queue) <= 3


   # ── Tests: API endpoints ──────────────────────────────────────────────────────

   def test_api_create_invite(api_client):
       response = api_client.post("/api/yeyonet/invite", json={
           "satellite_name": "Laptop Viaje",
           "permissions": ["chat", "grafos"],
           "expires_in_days": 7,
       })
       assert response.status_code == 201
       data = response.json()
       assert data["code"].startswith("YEYO-")
       assert data["satellite_name"] == "Laptop Viaje"


   def test_api_list_satellites_vacio(api_client):
       response = api_client.get("/api/yeyonet/satellites")
       assert response.status_code == 200
       assert response.json() == []


   def test_api_connect_satellite(api_client):
       # Primero crear invitación
       invite_resp = api_client.post("/api/yeyonet/invite", json={
           "satellite_name": "PC Test",
           "permissions": ["chat"],
           "expires_in_days": 7,
       })
       code = invite_resp.json()["code"]

       # Conectar satélite con el código
       connect_resp = api_client.post("/api/yeyonet/connect", json={
           "code": code,
           "node_mode": 2,
       })
       assert connect_resp.status_code == 200
       data = connect_resp.json()
       assert data["ok"] is True
       assert data["satellite_name"] == "PC Test"


   def test_api_connect_codigo_invalido(api_client):
       response = api_client.post("/api/yeyonet/connect", json={
           "code": "YEYO-FAKE-FAKE-FAKE",
       })
       assert response.status_code == 400


   def test_api_connect_codigo_ya_usado(api_client):
       invite_resp = api_client.post("/api/yeyonet/invite", json={
           "satellite_name": "Sat",
           "permissions": ["chat"],
       })
       code = invite_resp.json()["code"]

       api_client.post("/api/yeyonet/connect", json={"code": code})
       # Segundo intento debe fallar
       response = api_client.post("/api/yeyonet/connect", json={"code": code})
       assert response.status_code == 400


   def test_api_list_satellites_despues_de_conectar(api_client):
       invite_resp = api_client.post("/api/yeyonet/invite", json={
           "satellite_name": "Sat Visible",
           "permissions": ["chat"],
       })
       code = invite_resp.json()["code"]
       api_client.post("/api/yeyonet/connect", json={"code": code})

       list_resp = api_client.get("/api/yeyonet/satellites")
       assert list_resp.status_code == 200
       satellites = list_resp.json()
       assert len(satellites) == 1
       assert satellites[0]["name"] == "Sat Visible"


   def test_api_disconnect_satellite(api_client):
       invite_resp = api_client.post("/api/yeyonet/invite", json={
           "satellite_name": "Sat Para Borrar",
           "permissions": ["chat"],
       })
       code = invite_resp.json()["code"]
       connect_resp = api_client.post("/api/yeyonet/connect", json={"code": code})
       sat_id = connect_resp.json()["satellite_id"]

       delete_resp = api_client.delete(f"/api/yeyonet/satellites/{sat_id}")
       assert delete_resp.status_code == 204


   def test_api_status(api_client):
       response = api_client.get("/api/yeyonet/status")
       assert response.status_code == 200
       data = response.json()
       assert data["node_type"] == "central"
       assert "satellites_count" in data
       assert "pending_sync_count" in data

VERIFICAR:
- [ ] src/yeyonet/__init__.py exporta todos los símbolos necesarios
- [ ] src/yeyonet/config.py tiene YeyoNetConfig con from_env() funcionando
- [ ] src/yeyonet/auth.py genera códigos YEYO-XXXX-XXXX-XXXX únicos y valida single-use
- [ ] src/yeyonet/relay.py reconecta con exponential backoff y hace heartbeat ping/pong
- [ ] src/yeyonet/sync.py encola offline y procesa al reconectar por timestamp
- [ ] src/yeyonet/satellite_manager.py aplica visibility filter según nivel 1-4
- [ ] src/api/yeyonet_api.py tiene 5 endpoints: invite, satellites (GET/DELETE), connect, status
- [ ] Tests pasan: pytest tests/test_yeyonet.py (requiere fakeredis: pip install fakeredis)

SI FALLA:
- fakeredis no instalado: pip install fakeredis
- websockets no instalado: pip install websockets
- Import errors en tests: verificar que src/yeyonet/__init__.py está completo
- Redis connection errors en CI: todos los tests usan fakeredis, no Redis real
- YeyoNetConfig.from_env() falla: variables de entorno opcionales, usa defaults

NO HACER:
- No implementar WebRTC P2P (eso es futuro — Capa 7 usa Tailscale + WebSocket)
- No compartir archivos del OS, pantalla, contraseñas fuera de YeyoOS
- No hacer sync síncrono bloqueante — todo async o en cola
- No persistir auth_token en logs (solo en Redis/env)
- No implementar relay server (eso es infraestructura Tailscale) — solo el cliente

GATE: Central genera código YEYO-XXXX-XXXX-XXXX, satélite lo usa para conectar vía POST /connect, sync de Flash Memory entries pendientes funciona con resolución de conflictos por timestamp, offline queue acumula cambios y los retorna ordenados. Todos los tests pasan (≥22 tests).
```
