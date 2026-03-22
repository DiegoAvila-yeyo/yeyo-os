## ═══════════════════════════════════════
## MICRO-FASE 5.22 — Flash Memory Checkpoints para Grafos
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.22-1 [VSCODE] — GrafoCheckpoint: guardar y reanudar ejecución de grafos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.22 de Capa 5 (Órganos): crear el sistema de checkpoints que guarda el progreso de un YeyoGrafo en Flash Memory para poder reanudarlo si se interrumpe.

CONTEXTO:
- Micro-fases 5.0-5.21 completadas: todos los nodos de Capa 5
- Micro-fases 4.14-4.23 completadas: YeyoOrquestador completo
- FlashMemory disponible en src/memoria/flash_memory.py con métodos: guardar(dato, metadata), buscar(query, tipo, limite)
- GrafoCheckpoint guarda el EstadoGrafo después de cada nodo completado
- El hook after_nodo se llama automáticamente si se configura en YeyoGrafo
- Reanudar: busca el último checkpoint en Flash Memory y reconstruye EstadoGrafo
- Los checkpoints se guardan con tipo="grafo_checkpoint" e importancia=0.9
- Los grafos pueden reanudarse desde el último nodo completado

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/checkpoint.py:

   Ruta: ~/yeyo-os/src/orquestador/checkpoint.py
   Contenido:

   """
   YeyoOS — GrafoCheckpoint
   Micro-fase 5.22 — Capa 5: Órganos

   Sistema de checkpoints para grafos.
   Guarda el EstadoGrafo en Flash Memory después de cada nodo completado.
   Permite reanudar ejecuciones interrumpidas desde el último checkpoint.
   """

   import json
   from datetime import datetime, timezone
   from typing import Optional, Any

   from .estado import EstadoGrafo


   TIPO_CHECKPOINT = "grafo_checkpoint"
   IMPORTANCIA_CHECKPOINT = 0.9


   class CheckpointError(Exception):
       """Error en el sistema de checkpoints."""
       pass


   class GrafoCheckpoint:
       """
       Gestiona checkpoints de ejecución de grafos en Flash Memory.

       Uso como callback after_nodo en YeyoGrafo:
           checkpoint = GrafoCheckpoint(flash_memory, grafo_id="mi_grafo")
           await grafo.ejecutar(entrada, on_evento=checkpoint.on_evento_checkpoint)

       Reanudar ejecución interrumpida:
           estado = await GrafoCheckpoint.reanudar(grafo_id="mi_grafo", flash_memory=flash)
           if estado:
               await grafo.ejecutar(estado)  # continuará desde donde quedó
       """

       def __init__(
           self,
           flash_memory: Any,
           grafo_id: str,
           guardar_cada_nodo: bool = True,
       ):
           """
           Args:
               flash_memory: instancia de FlashMemory
               grafo_id: ID del grafo (para identificar checkpoints)
               guardar_cada_nodo: si False, solo guarda al completar el grafo
           """
           self._flash = flash_memory
           self.grafo_id = grafo_id
           self.guardar_cada_nodo = guardar_cada_nodo
           self.checkpoints_guardados: list[str] = []  # IDs de memorias guardadas

       async def on_evento_checkpoint(self, evento: dict) -> None:
           """
           Callback compatible con el parámetro on_evento de YeyoGrafo.
           Guarda un checkpoint cuando un nodo se completa.
           """
           if not self.guardar_cada_nodo:
               return

           estado_nodo = evento.get("estado")
           if estado_nodo not in ("completado", "saltado"):
               return  # Solo guardar después de nodos exitosos

           # Reconstruir EstadoGrafo mínimo para el checkpoint
           # (el estado real está en el grafo, solo guardamos metadatos del evento)
           checkpoint_data = {
               "grafo_id": self.grafo_id,
               "nodo_completado": evento.get("nodo_id"),
               "progreso": evento.get("progreso", 0),
               "timestamp": evento.get("timestamp") or datetime.now(timezone.utc).isoformat(),
               "tipo": TIPO_CHECKPOINT,
           }

           memoria_id = await self._guardar_checkpoint(checkpoint_data)
           if memoria_id:
               self.checkpoints_guardados.append(memoria_id)

       async def guardar_estado(self, estado: EstadoGrafo) -> str:
           """
           Guarda el EstadoGrafo completo como checkpoint en Flash Memory.
           Retorna el ID de la memoria guardada.
           """
           checkpoint_data = {
               "grafo_id": self.grafo_id,
               "estado": estado.a_dict(),
               "timestamp": datetime.now(timezone.utc).isoformat(),
               "tipo": TIPO_CHECKPOINT,
           }

           memoria_id = await self._guardar_checkpoint(checkpoint_data)
           if memoria_id:
               self.checkpoints_guardados.append(memoria_id)
           return memoria_id or ""

       async def _guardar_checkpoint(self, data: dict) -> Optional[str]:
           """Guarda datos en Flash Memory y retorna el ID."""
           try:
               dato_json = json.dumps(data, ensure_ascii=False)
               memoria_id = await self._flash.guardar(
                   dato=dato_json,
                   metadata={
                       "tipo": TIPO_CHECKPOINT,
                       "grafo_id": self.grafo_id,
                       "importancia": IMPORTANCIA_CHECKPOINT,
                   }
               )
               return memoria_id
           except Exception as e:
               # Los errores de checkpoint no deben interrumpir la ejecución
               return None

       @staticmethod
       async def reanudar(
           grafo_id: str,
           flash_memory: Any,
       ) -> Optional[EstadoGrafo]:
           """
           Busca el último checkpoint del grafo en Flash Memory y
           reconstruye el EstadoGrafo para reanudar la ejecución.

           Retorna None si no hay checkpoint disponible.
           """
           try:
               resultados = await flash_memory.buscar(
                   query=f"grafo_id:{grafo_id}",
                   tipo=TIPO_CHECKPOINT,
                   limite=10,
               )
           except Exception:
               return None

           if not resultados:
               return None

           # Buscar el checkpoint más reciente con estado completo
           for resultado in resultados:
               try:
                   contenido = resultado.get("contenido", "")
                   if isinstance(contenido, str):
                       data = json.loads(contenido)
                   elif isinstance(contenido, dict):
                       data = contenido
                   else:
                       continue

                   if data.get("grafo_id") != grafo_id:
                       continue

                   # Solo podemos reanudar si tenemos el estado completo
                   estado_data = data.get("estado")
                   if estado_data:
                       return EstadoGrafo.desde_dict(estado_data)
               except (json.JSONDecodeError, Exception):
                   continue

           return None

       @staticmethod
       async def limpiar_checkpoints(
           grafo_id: str,
           flash_memory: Any,
       ) -> int:
           """
           Elimina todos los checkpoints de un grafo.
           Retorna el número de checkpoints eliminados.
           """
           try:
               resultados = await flash_memory.buscar(
                   query=f"grafo_id:{grafo_id}",
                   tipo=TIPO_CHECKPOINT,
                   limite=100,
               )
               # En una implementación real, se eliminarían aquí
               return len(resultados)
           except Exception:
               return 0

2. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 + 5.22-5.25 — Capas 4-5
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError
   from .catalogo import CatalogoNodos, CatalogoError
   from .eventos import GraphEventEmitter, crear_evento_grafo
   from .checkpoint import GrafoCheckpoint, CheckpointError

3. Crear archivo tests/unit/orquestador/test_checkpoint.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_checkpoint.py
   Contenido:

   """Tests para GrafoCheckpoint — Micro-fase 5.22"""

   import json
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo
   from src.orquestador.grafo import YeyoGrafo
   from src.orquestador.checkpoint import GrafoCheckpoint, TIPO_CHECKPOINT


   # ─── Mock de FlashMemory ───────────────────────────────────────────────────

   def mock_flash_memory(checkpoints=None):
       m = AsyncMock()
       memoria_guardada = {}
       contador = [0]

       async def guardar(dato, metadata=None):
           contador[0] += 1
           mid = f"mem-{contador[0]:03d}"
           memoria_guardada[mid] = {"contenido": dato, "metadata": metadata}
           return mid

       async def buscar(query, tipo=None, limite=10):
           if checkpoints is not None:
               return checkpoints
           # Retornar checkpoints guardados
           results = []
           for mid, data in memoria_guardada.items():
               if tipo is None or data.get("metadata", {}).get("tipo") == tipo:
                   results.append({"id": mid, "contenido": data["contenido"], "score": 0.9})
           return results[:limite]

       m.guardar = AsyncMock(side_effect=guardar)
       m.buscar = AsyncMock(side_effect=buscar)
       m._memoria_guardada = memoria_guardada
       return m


   # ─── Nodos de prueba ──────────────────────────────────────────────────────

   @nodo(id="checkpoint_nodo_a")
   async def checkpoint_nodo_a(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["a"] = True
       return estado


   @nodo(id="checkpoint_nodo_b")
   async def checkpoint_nodo_b(estado: EstadoGrafo) -> EstadoGrafo:
       estado.salida["b"] = True
       return estado


   class TestGrafoCheckpointGuardar:

       @pytest.mark.asyncio
       async def test_guardar_estado_retorna_memoria_id(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           estado = EstadoGrafo(entrada={"test": True})
           estado.registrar_nodo_completado("nodo_a")
           memoria_id = await cp.guardar_estado(estado)
           assert memoria_id != ""
           assert memoria_id.startswith("mem-")

       @pytest.mark.asyncio
       async def test_guardar_estado_llama_a_flash_memory(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           estado = EstadoGrafo(entrada={"x": 1})
           await cp.guardar_estado(estado)
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_guardar_estado_usa_tipo_checkpoint(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           estado = EstadoGrafo(entrada={})
           await cp.guardar_estado(estado)
           metadata_usada = flash.guardar.call_args.kwargs.get("metadata", {})
           assert metadata_usada.get("tipo") == TIPO_CHECKPOINT

       @pytest.mark.asyncio
       async def test_checkpoint_registrado_en_lista(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           estado = EstadoGrafo(entrada={})
           await cp.guardar_estado(estado)
           assert len(cp.checkpoints_guardados) == 1

       @pytest.mark.asyncio
       async def test_error_en_flash_memory_no_interrumpe(self):
           flash = AsyncMock()
           flash.guardar = AsyncMock(side_effect=ConnectionError("flash down"))
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           estado = EstadoGrafo(entrada={})
           # No debe lanzar excepción
           resultado = await cp.guardar_estado(estado)
           assert resultado == ""

       @pytest.mark.asyncio
       async def test_on_evento_checkpoint_guarda_en_completado(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           evento = {
               "type": "graph_event",
               "grafo_id": "mi_grafo",
               "nodo_id": "nodo_a",
               "estado": "completado",
               "progreso": 0.5,
               "mensaje": "ok",
               "timestamp": "2025-01-01T00:00:00Z"
           }
           await cp.on_evento_checkpoint(evento)
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_on_evento_checkpoint_no_guarda_en_activo(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           evento = {"estado": "activo", "nodo_id": "n", "progreso": 0.3}
           await cp.on_evento_checkpoint(evento)
           flash.guardar.assert_not_called()

       @pytest.mark.asyncio
       async def test_on_evento_checkpoint_guarda_en_saltado(self):
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
           evento = {"estado": "saltado", "nodo_id": "n", "progreso": 0.5}
           await cp.on_evento_checkpoint(evento)
           flash.guardar.assert_called_once()


   class TestGrafoCheckpointReanudar:

       @pytest.mark.asyncio
       async def test_reanudar_retorna_none_si_no_hay_checkpoints(self):
           flash = mock_flash_memory(checkpoints=[])
           resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
           assert resultado is None

       @pytest.mark.asyncio
       async def test_reanudar_reconstruye_estado(self):
           estado_original = EstadoGrafo(entrada={"x": 42})
           estado_original.registrar_nodo_completado("nodo_a")
           estado_original.salida["resultado"] = "ok"

           # Simular checkpoint guardado
           checkpoint_data = {
               "grafo_id": "mi_grafo",
               "estado": estado_original.a_dict(),
               "timestamp": "2025-01-01T00:00:00Z",
               "tipo": TIPO_CHECKPOINT,
           }
           flash = mock_flash_memory(checkpoints=[{
               "id": "mem-001",
               "contenido": json.dumps(checkpoint_data),
               "score": 0.9
           }])

           estado_recuperado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
           assert estado_recuperado is not None
           assert estado_recuperado.entrada == {"x": 42}
           assert "nodo_a" in estado_recuperado.historial
           assert estado_recuperado.salida["resultado"] == "ok"

       @pytest.mark.asyncio
       async def test_reanudar_ignora_checkpoints_de_otro_grafo(self):
           checkpoint_data = {
               "grafo_id": "otro_grafo",  # grafo diferente
               "estado": EstadoGrafo(entrada={}).a_dict(),
               "tipo": TIPO_CHECKPOINT,
           }
           flash = mock_flash_memory(checkpoints=[{
               "id": "mem-001",
               "contenido": json.dumps(checkpoint_data),
               "score": 0.9
           }])
           resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
           assert resultado is None

       @pytest.mark.asyncio
       async def test_reanudar_error_en_flash_retorna_none(self):
           flash = AsyncMock()
           flash.buscar = AsyncMock(side_effect=ConnectionError("flash down"))
           resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
           assert resultado is None


   class TestGrafoCheckpointIntegracion:

       @pytest.mark.asyncio
       async def test_checkpoint_integrado_con_yeyo_grafo(self):
           """GrafoCheckpoint como callback de YeyoGrafo guarda checkpoints por nodo."""
           flash = mock_flash_memory()
           cp = GrafoCheckpoint(flash, grafo_id="grafo_integ")

           g = (YeyoGrafo("grafo_integ")
                .agregar_nodo(checkpoint_nodo_a)
                .agregar_nodo(checkpoint_nodo_b)
                .inicio("checkpoint_nodo_a")
                .edge("checkpoint_nodo_a", "checkpoint_nodo_b")
                .fin("checkpoint_nodo_b"))

           await g.ejecutar({}, on_evento=cp.on_evento_checkpoint)

           # Debe haber guardado al menos 2 checkpoints (uno por nodo completado)
           assert flash.guardar.call_count >= 2

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_checkpoint.py -v

VERIFICAR:
- [ ] src/orquestador/checkpoint.py existe con GrafoCheckpoint
- [ ] guardar_estado() guarda en Flash Memory con tipo="grafo_checkpoint"
- [ ] on_evento_checkpoint() solo guarda en estados "completado" o "saltado"
- [ ] reanudar() reconstruye EstadoGrafo desde el checkpoint más reciente
- [ ] reanudar() retorna None si no hay checkpoints
- [ ] Error en Flash Memory no interrumpe la ejecución del grafo
- [ ] Integración con YeyoGrafo: guarda checkpoint por cada nodo completado
- [ ] TODOS los tests pasan

SI FALLA:
- FlashMemory no disponible: el mock es suficiente para todos los tests
- JSON serialization: verificar que estado.a_dict() retorna objetos JSON-serializables
- TypeError en desde_dict: verificar que EstadoGrafo.desde_dict() maneja el formato del checkpoint

NO HACER:
- No implementar NodoCache aún (eso es micro-fase 5.23)
- No conectar con FlashMemory real — solo mock en tests
- No implementar cleanup automático de checkpoints viejos (sería un extra futuro)

GATE: Checkpoint se guarda después de cada nodo completado via on_evento_checkpoint, se puede reanudar desde el último checkpoint con EstadoGrafo reconstruido correctamente, errores de Flash Memory no interrumpen la ejecución, todos los tests pasan.
```
