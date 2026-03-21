## ═══════════════════════════════════════
## MICRO-FASE 1.9 — Event Bus
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.9-1 [VSCODE] — Event Bus para comunicación interna

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.9: crear el Event Bus interno para comunicación pub/sub entre servicios.

CONTEXTO:
- Micro-fases 1.0-1.8 completadas: interfaces, config, factory, API, WebSocket, GPU Scheduler listos
- Event Bus: patrón pub/sub para desacoplar servicios
- Singleton: una sola instancia global
- Eventos predefinidos: gpu.task.started, gpu.task.completed, memory.stored, memory.recalled, chat.message, system.error, node.opened, node.closed
- Los suscriptores son funciones async (callbacks)
- Si un suscriptor falla, NO debe afectar a los demás

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/event_bus.py:

   Ruta: ~/yeyo-os/src/core/event_bus.py
   Contenido:

   """
   YeyoOS — Event Bus
   Micro-fase 1.9 — Capa 1: Esqueleto
   
   Bus de eventos interno para comunicación pub/sub entre servicios.
   Patrón Singleton: una sola instancia compartida.
   
   Eventos del sistema:
     gpu.task.started    - Tarea GPU iniciada
     gpu.task.completed  - Tarea GPU completada
     memory.stored       - Memoria almacenada
     memory.recalled     - Memoria recuperada
     chat.message        - Mensaje de chat procesado
     system.error        - Error del sistema
     node.opened         - Nodo del hub abierto
     node.closed         - Nodo del hub cerrado
   """
   
   import asyncio
   import logging
   from typing import Callable, Any, Awaitable
   
   
   # Tipos de eventos válidos del sistema
   SYSTEM_EVENTS = {
       "gpu.task.started",
       "gpu.task.completed",
       "gpu.task.preempted",
       "memory.stored",
       "memory.recalled",
       "memory.promoted",
       "memory.demoted",
       "chat.message",
       "chat.stream.start",
       "chat.stream.end",
       "system.error",
       "system.startup",
       "system.shutdown",
       "node.opened",
       "node.closed",
   }
   
   # Tipo para callbacks de suscriptores
   EventCallback = Callable[[Any], Awaitable[None]]
   
   logger = logging.getLogger("yeyo.event_bus")
   
   
   class EventBus:
       """
       Bus de eventos con patrón Singleton.
       Suscriptores reciben eventos de forma asíncrona.
       Si un suscriptor falla, los demás siguen recibiendo.
       """
   
       _instance: "EventBus | None" = None
   
       def __init__(self):
           self._subscribers: dict[str, list[EventCallback]] = {}
   
       @classmethod
       def instance(cls) -> "EventBus":
           """Obtiene la instancia singleton del Event Bus."""
           if cls._instance is None:
               cls._instance = EventBus()
           return cls._instance
   
       @classmethod
       def reset_instance(cls) -> None:
           """Resetea la instancia singleton (útil para tests)."""
           cls._instance = None
   
       def subscribe(self, event_type: str, callback: EventCallback) -> None:
           """
           Suscribe un callback a un tipo de evento.
           El callback debe ser una función async.
           """
           if event_type not in self._subscribers:
               self._subscribers[event_type] = []
           if callback not in self._subscribers[event_type]:
               self._subscribers[event_type].append(callback)
   
       def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
           """Elimina un callback de un tipo de evento."""
           if event_type in self._subscribers:
               try:
                   self._subscribers[event_type].remove(callback)
               except ValueError:
                   pass
   
       async def publish(self, event_type: str, data: Any = None) -> None:
           """
           Publica un evento a todos los suscriptores.
           Si un suscriptor falla, loguea el error y continúa.
           """
           if event_type not in self._subscribers:
               return
   
           for callback in self._subscribers[event_type]:
               try:
                   await callback(data)
               except Exception as e:
                   logger.error(
                       f"Error en suscriptor de '{event_type}': {e}",
                       exc_info=True,
                   )
   
       def get_subscriber_count(self, event_type: str) -> int:
           """Retorna el número de suscriptores para un tipo de evento."""
           return len(self._subscribers.get(event_type, []))
   
       def get_all_event_types(self) -> list[str]:
           """Retorna todos los tipos de eventos con suscriptores."""
           return list(self._subscribers.keys())
   
       def clear(self) -> None:
           """Elimina todos los suscriptores (útil para tests)."""
           self._subscribers.clear()

2. Crear archivo tests/unit/core/test_event_bus.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_event_bus.py
   Contenido:

   """Tests para Event Bus — Micro-fase 1.9"""
   
   import pytest
   from src.core.event_bus import EventBus, SYSTEM_EVENTS
   
   
   @pytest.fixture
   def bus():
       """Crea un Event Bus limpio para cada test."""
       EventBus.reset_instance()
       b = EventBus()
       yield b
       b.clear()
   
   
   class TestEventBusSingleton:
       """Tests para patrón singleton."""
   
       def test_singleton_returns_same_instance(self):
           EventBus.reset_instance()
           b1 = EventBus.instance()
           b2 = EventBus.instance()
           assert b1 is b2
   
       def test_reset_creates_new_instance(self):
           EventBus.reset_instance()
           b1 = EventBus.instance()
           EventBus.reset_instance()
           b2 = EventBus.instance()
           assert b1 is not b2
   
   
   class TestEventBusSubscribe:
       """Tests para suscripción."""
   
       def test_subscribe_adds_callback(self, bus):
           async def handler(data):
               pass
           bus.subscribe("test.event", handler)
           assert bus.get_subscriber_count("test.event") == 1
   
       def test_subscribe_multiple_callbacks(self, bus):
           async def handler1(data):
               pass
           async def handler2(data):
               pass
           bus.subscribe("test.event", handler1)
           bus.subscribe("test.event", handler2)
           assert bus.get_subscriber_count("test.event") == 2
   
       def test_subscribe_same_callback_once(self, bus):
           async def handler(data):
               pass
           bus.subscribe("test.event", handler)
           bus.subscribe("test.event", handler)
           assert bus.get_subscriber_count("test.event") == 1
   
       def test_unsubscribe_removes_callback(self, bus):
           async def handler(data):
               pass
           bus.subscribe("test.event", handler)
           bus.unsubscribe("test.event", handler)
           assert bus.get_subscriber_count("test.event") == 0
   
       def test_unsubscribe_nonexistent_is_safe(self, bus):
           async def handler(data):
               pass
           bus.unsubscribe("nonexistent.event", handler)
   
       def test_get_subscriber_count_no_event(self, bus):
           assert bus.get_subscriber_count("nonexistent") == 0
   
   
   class TestEventBusPublish:
       """Tests para publicación de eventos."""
   
       @pytest.mark.asyncio
       async def test_publish_calls_subscriber(self, bus):
           received = []
           async def handler(data):
               received.append(data)
           bus.subscribe("test.event", handler)
           await bus.publish("test.event", {"key": "value"})
           assert len(received) == 1
           assert received[0] == {"key": "value"}
   
       @pytest.mark.asyncio
       async def test_publish_calls_all_subscribers(self, bus):
           results = []
           async def handler1(data):
               results.append("h1")
           async def handler2(data):
               results.append("h2")
           bus.subscribe("test.event", handler1)
           bus.subscribe("test.event", handler2)
           await bus.publish("test.event", None)
           assert "h1" in results
           assert "h2" in results
   
       @pytest.mark.asyncio
       async def test_publish_no_subscribers_is_safe(self, bus):
           await bus.publish("nonexistent.event", {"data": 1})
   
       @pytest.mark.asyncio
       async def test_publish_with_none_data(self, bus):
           received = []
           async def handler(data):
               received.append(data)
           bus.subscribe("test.event", handler)
           await bus.publish("test.event")
           assert received[0] is None
   
       @pytest.mark.asyncio
       async def test_subscriber_error_doesnt_affect_others(self, bus):
           results = []
           async def bad_handler(data):
               raise RuntimeError("Error intencional")
           async def good_handler(data):
               results.append("ok")
           bus.subscribe("test.event", bad_handler)
           bus.subscribe("test.event", good_handler)
           await bus.publish("test.event", None)
           assert "ok" in results
   
       @pytest.mark.asyncio
       async def test_publish_only_to_matching_event(self, bus):
           results = []
           async def handler_a(data):
               results.append("a")
           async def handler_b(data):
               results.append("b")
           bus.subscribe("event.a", handler_a)
           bus.subscribe("event.b", handler_b)
           await bus.publish("event.a", None)
           assert results == ["a"]
   
   
   class TestEventBusUtility:
       """Tests para métodos utilitarios."""
   
       def test_clear_removes_all(self, bus):
           async def handler(data):
               pass
           bus.subscribe("event.a", handler)
           bus.subscribe("event.b", handler)
           bus.clear()
           assert bus.get_subscriber_count("event.a") == 0
           assert bus.get_subscriber_count("event.b") == 0
   
       def test_get_all_event_types(self, bus):
           async def handler(data):
               pass
           bus.subscribe("event.a", handler)
           bus.subscribe("event.b", handler)
           types = bus.get_all_event_types()
           assert "event.a" in types
           assert "event.b" in types
   
   
   class TestSystemEvents:
       """Tests para eventos del sistema predefinidos."""
   
       def test_system_events_are_strings(self):
           for event in SYSTEM_EVENTS:
               assert isinstance(event, str)
   
       def test_gpu_events_exist(self):
           assert "gpu.task.started" in SYSTEM_EVENTS
           assert "gpu.task.completed" in SYSTEM_EVENTS
   
       def test_memory_events_exist(self):
           assert "memory.stored" in SYSTEM_EVENTS
           assert "memory.recalled" in SYSTEM_EVENTS
   
       def test_chat_events_exist(self):
           assert "chat.message" in SYSTEM_EVENTS
   
       def test_system_events_exist(self):
           assert "system.error" in SYSTEM_EVENTS
   
       def test_node_events_exist(self):
           assert "node.opened" in SYSTEM_EVENTS
           assert "node.closed" in SYSTEM_EVENTS

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_event_bus.py -v

VERIFICAR:
- [ ] Archivo src/core/event_bus.py existe con EventBus y SYSTEM_EVENTS
- [ ] TODOS los tests pasan (0 failed)
- [ ] Singleton funciona correctamente
- [ ] Subscribe y unsubscribe funcionan
- [ ] Publish llama a todos los suscriptores
- [ ] Error en un suscriptor NO afecta a los demás
- [ ] Eventos del sistema definidos correctamente
- [ ] clear() limpia todo

SI FALLA:
- Import error: verificar __init__.py en src/core/
- AsyncMock error: requiere Python 3.8+
- Logging error: verificar que logger está configurado

NO HACER:
- No persistir eventos en BD (eso es futuro)
- No implementar event replay/history
- No agregar filtros de eventos complejos
- No hacer eventos distribuidos (Redis pub/sub viene después)

GATE: EventBus singleton funcional, pub/sub correcto, errores aislados entre suscriptores, SYSTEM_EVENTS definidos, todos los tests pasan.
```
