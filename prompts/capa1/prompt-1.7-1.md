## ═══════════════════════════════════════
## MICRO-FASE 1.7 — WebSocket Server
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.7-1 [VSCODE] — Servidor WebSocket para comunicación en tiempo real

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.7: crear el servidor WebSocket para comunicación en tiempo real entre backend y frontend.

CONTEXTO:
- Micro-fases 1.0-1.6 completadas: interfaces, config, factory, API FastAPI listos
- WebSocket para: streaming de chat, actualizaciones de UI, eventos del sistema
- ConnectionManager maneja conexiones activas
- Límite: 50 conexiones simultáneas (config.websocket_max_connections)
- Se integra con la app FastAPI existente en src/api/main.py

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencia (websockets ya viene con FastAPI):
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install websockets

2. Crear archivo src/api/websocket.py:

   Ruta: ~/yeyo-os/src/api/websocket.py
   Contenido:

   """
   YeyoOS — WebSocket Server
   Micro-fase 1.7 — Capa 1: Esqueleto
   
   Gestión de conexiones WebSocket para comunicación
   en tiempo real con el frontend.
   Límite: 50 conexiones simultáneas.
   """
   
   import json
   import time
   from typing import Any
   
   from fastapi import WebSocket, WebSocketDisconnect
   
   
   class ConnectionManager:
       """Gestor de conexiones WebSocket."""
   
       def __init__(self, max_connections: int = 50):
           self.max_connections = max_connections
           self.active_connections: list[WebSocket] = []
   
       @property
       def connection_count(self) -> int:
           """Número de conexiones activas."""
           return len(self.active_connections)
   
       async def connect(self, websocket: WebSocket) -> bool:
           """
           Acepta una nueva conexión WebSocket.
           Retorna False si se alcanzó el límite de conexiones.
           """
           if self.connection_count >= self.max_connections:
               await websocket.close(code=1013, reason="Max connections reached")
               return False
           await websocket.accept()
           self.active_connections.append(websocket)
           return True
   
       def disconnect(self, websocket: WebSocket) -> None:
           """Elimina una conexión de la lista de activas."""
           if websocket in self.active_connections:
               self.active_connections.remove(websocket)
   
       async def send_message(self, message: str, websocket: WebSocket) -> None:
           """Envía mensaje de texto a un cliente específico."""
           await websocket.send_text(message)
   
       async def send_json(self, data: dict[str, Any], websocket: WebSocket) -> None:
           """Envía mensaje JSON a un cliente específico."""
           await websocket.send_text(json.dumps(data))
   
       async def broadcast(self, message: str) -> None:
           """Envía mensaje a TODAS las conexiones activas."""
           disconnected = []
           for connection in self.active_connections:
               try:
                   await connection.send_text(message)
               except Exception:
                   disconnected.append(connection)
           for conn in disconnected:
               self.disconnect(conn)
   
       async def broadcast_json(self, data: dict[str, Any]) -> None:
           """Envía JSON a TODAS las conexiones activas."""
           await self.broadcast(json.dumps(data))
   
       def get_status(self) -> dict:
           """Retorna estado del WebSocket server."""
           return {
               "active_connections": self.connection_count,
               "max_connections": self.max_connections,
           }
   
   
   # Instancia global del manager
   manager = ConnectionManager()

3. Actualizar src/api/main.py para incluir WebSocket endpoint. Agregar al final del archivo:

   Abrir ~/yeyo-os/src/api/main.py y agregar después de los endpoints existentes:

   from fastapi import WebSocket, WebSocketDisconnect
   from src.api.websocket import manager
   
   
   @app.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket):
       """Endpoint WebSocket principal."""
       connected = await manager.connect(websocket)
       if not connected:
           return
       try:
           while True:
               data = await websocket.receive_text()
               # Echo por ahora, en Capa 2 se conectará con Orquestador
               await manager.send_json(
                   {"type": "echo", "content": data, "timestamp": time.time()},
                   websocket,
               )
       except WebSocketDisconnect:
           manager.disconnect(websocket)

4. Crear tests:
   mkdir -p tests/unit/api

5. Crear archivo tests/unit/api/test_websocket.py:

   Ruta: ~/yeyo-os/tests/unit/api/test_websocket.py
   Contenido:

   """Tests para WebSocket Server — Micro-fase 1.7"""
   
   import pytest
   import json
   from unittest.mock import AsyncMock, MagicMock
   from fastapi.testclient import TestClient
   from src.api.main import app
   from src.api.websocket import ConnectionManager
   
   
   @pytest.fixture
   def client():
       return TestClient(app)
   
   
   @pytest.fixture
   def ws_manager():
       return ConnectionManager(max_connections=3)
   
   
   class TestConnectionManager:
       """Tests para ConnectionManager."""
   
       def test_initial_no_connections(self, ws_manager):
           assert ws_manager.connection_count == 0
   
       def test_max_connections_set(self, ws_manager):
           assert ws_manager.max_connections == 3
   
       def test_default_max_connections(self):
           m = ConnectionManager()
           assert m.max_connections == 50
   
       def test_disconnect_removes_connection(self, ws_manager):
           mock_ws = MagicMock()
           ws_manager.active_connections.append(mock_ws)
           assert ws_manager.connection_count == 1
           ws_manager.disconnect(mock_ws)
           assert ws_manager.connection_count == 0
   
       def test_disconnect_nonexistent_is_safe(self, ws_manager):
           mock_ws = MagicMock()
           ws_manager.disconnect(mock_ws)  # No debe lanzar excepción
           assert ws_manager.connection_count == 0
   
       def test_get_status(self, ws_manager):
           status = ws_manager.get_status()
           assert status["active_connections"] == 0
           assert status["max_connections"] == 3
   
       @pytest.mark.asyncio
       async def test_send_message(self, ws_manager):
           mock_ws = AsyncMock()
           await ws_manager.send_message("hello", mock_ws)
           mock_ws.send_text.assert_called_once_with("hello")
   
       @pytest.mark.asyncio
       async def test_send_json(self, ws_manager):
           mock_ws = AsyncMock()
           await ws_manager.send_json({"key": "value"}, mock_ws)
           mock_ws.send_text.assert_called_once_with('{"key": "value"}')
   
       @pytest.mark.asyncio
       async def test_broadcast_sends_to_all(self, ws_manager):
           ws1 = AsyncMock()
           ws2 = AsyncMock()
           ws_manager.active_connections = [ws1, ws2]
           await ws_manager.broadcast("hello all")
           ws1.send_text.assert_called_once_with("hello all")
           ws2.send_text.assert_called_once_with("hello all")
   
       @pytest.mark.asyncio
       async def test_broadcast_removes_disconnected(self, ws_manager):
           ws_good = AsyncMock()
           ws_bad = AsyncMock()
           ws_bad.send_text.side_effect = Exception("disconnected")
           ws_manager.active_connections = [ws_good, ws_bad]
           await ws_manager.broadcast("test")
           assert ws_bad not in ws_manager.active_connections
           assert ws_good in ws_manager.active_connections
   
   
   class TestWebSocketEndpoint:
       """Tests para el endpoint /ws."""
   
       def test_websocket_connect_and_echo(self, client):
           with client.websocket_connect("/ws") as websocket:
               websocket.send_text("Hola YeyoOS")
               data = websocket.receive_json()
               assert data["type"] == "echo"
               assert data["content"] == "Hola YeyoOS"
               assert "timestamp" in data
   
       def test_websocket_multiple_messages(self, client):
           with client.websocket_connect("/ws") as websocket:
               for i in range(3):
                   websocket.send_text(f"msg-{i}")
                   data = websocket.receive_json()
                   assert data["content"] == f"msg-{i}"

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/api/test_websocket.py -v

VERIFICAR:
- [ ] Archivo src/api/websocket.py existe con ConnectionManager
- [ ] TODOS los tests pasan (0 failed)
- [ ] Connect/disconnect funciona
- [ ] Send message a cliente individual funciona
- [ ] Broadcast a todos funciona
- [ ] Desconexiones se manejan gracefully
- [ ] Límite de conexiones configurable (default 50)
- [ ] WebSocket endpoint /ws responde y hace echo

SI FALLA:
- websockets no instalado: `pip install websockets`
- Import error: verificar que src/api/websocket.py tiene ConnectionManager
- WebSocket test error: asegurar que el endpoint está registrado en main.py
- AsyncMock error: requiere Python 3.8+ (ya tenemos 3.11)

NO HACER:
- No implementar lógica de chat real (eso es Capa 2/3)
- No agregar autenticación WebSocket todavía
- No hacer broadcasting de eventos reales aún
- No agregar rooms/channels por ahora

GATE: ConnectionManager funcional, WebSocket endpoint /ws responde con echo, broadcast funciona, límite de 50 conexiones, todos los tests pasan.
```
