## ═══════════════════════════════════════
## MICRO-FASE 4.20 — Catálogo de Nodos Base
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.20-1 [VSCODE] — CatalogoNodos con 5 nodos base registrados

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.20 de Capa 4 (Sistema Nervioso): crear el CatalogoNodos con los 5 nodos base que pueden usarse para construir grafos (tanto manuales como generados por IA).

CONTEXTO:
- Micro-fases 4.14-4.19 completadas: EstadoGrafo, Nodo, Edge, YeyoGrafo, NodoParalelo, YeyoOrquestador
- OllamaProvider en src/ia/ollama_provider.py con métodos: chat(), embeddings()
- FlashMemory en src/memoria/flash_memory.py con métodos: guardar(), buscar()
- Los 5 nodos base: nodo_chat, nodo_embeddings, nodo_guardar_memoria, nodo_buscar_memoria, nodo_log
- Cada nodo base espera campos específicos en estado.entrada y escribe en estado.salida
- El catálogo permite registrar nodos adicionales y es la base del GeneradorGrafos (5.24)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/catalogo.py:

   Ruta: ~/yeyo-os/src/orquestador/catalogo.py
   Contenido:

   """
   YeyoOS — CatalogoNodos
   Micro-fase 4.20 — Capa 4: Sistema Nervioso

   Registro de nodos base disponibles para construir grafos.
   La IA solo puede usar nodos del catálogo registrado.
   """

   from typing import Optional, Any
   from .estado import EstadoGrafo
   from .nodo import Nodo, NodoFuncion, nodo


   class CatalogoError(Exception):
       """Error en el CatalogoNodos."""
       pass


   class CatalogoNodos:
       """
       Registro central de nodos disponibles para construir grafos.

       Los nodos base incluidos por defecto cubren las operaciones más comunes:
       - nodo_chat: conversación con LLM via OllamaProvider
       - nodo_embeddings: genera embeddings de texto
       - nodo_guardar_memoria: guarda datos en Flash Memory
       - nodo_buscar_memoria: busca en Flash Memory
       - nodo_log: registra un mensaje en los logs del sistema

       Se pueden registrar nodos adicionales con registrar().
       """

       def __init__(
           self,
           ollama_provider: Optional[Any] = None,
           flash_memory: Optional[Any] = None,
       ):
           self._ollama = ollama_provider
           self._flash_memory = flash_memory
           self._nodos: dict[str, Nodo] = {}
           self._registrar_nodos_base()

       def _registrar_nodos_base(self) -> None:
           """Registra los 5 nodos base en el catálogo."""
           self.registrar(self._crear_nodo_chat())
           self.registrar(self._crear_nodo_embeddings())
           self.registrar(self._crear_nodo_guardar_memoria())
           self.registrar(self._crear_nodo_buscar_memoria())
           self.registrar(self._crear_nodo_log())

       # ─── Registro ─────────────────────────────────────────────────────────────

       def registrar(self, nodo: Nodo) -> "CatalogoNodos":
           """Registra un nodo en el catálogo."""
           self._nodos[nodo.id] = nodo
           return self

       def obtener(self, nodo_id: str) -> Nodo:
           """Obtiene un nodo por ID. Lanza CatalogoError si no existe."""
           if nodo_id not in self._nodos:
               raise CatalogoError(
                   f"Nodo '{nodo_id}' no encontrado en el catálogo. "
                   f"Disponibles: {list(self._nodos.keys())}"
               )
           return self._nodos[nodo_id]

       def listar(self) -> list[str]:
           """Lista los IDs de todos los nodos registrados."""
           return list(self._nodos.keys())

       def existe(self, nodo_id: str) -> bool:
           """Retorna True si el nodo existe en el catálogo."""
           return nodo_id in self._nodos

       def describir(self) -> dict[str, str]:
           """Retorna dict {nodo_id: descripcion} para todos los nodos."""
           return {
               nodo_id: getattr(n, "descripcion", n.id)
               for nodo_id, n in self._nodos.items()
           }

       # ─── Nodos base ───────────────────────────────────────────────────────────

       def _crear_nodo_chat(self) -> Nodo:
           """
           nodo_chat: Conversación con LLM via OllamaProvider.

           Entrada esperada en estado.entrada:
             - "mensaje": str — el mensaje del usuario
             - "sistema": str (opcional) — prompt del sistema
             - "historial": list (opcional) — historial de mensajes previos

           Escribe en estado.salida:
             - "respuesta": str — la respuesta del LLM
           """
           ollama = self._ollama

           async def fn(estado: EstadoGrafo) -> EstadoGrafo:
               mensaje = estado.entrada.get("mensaje", "")
               sistema = estado.entrada.get("sistema", "")
               historial = estado.entrada.get("historial", [])

               messages = []
               if sistema:
                   messages.append({"role": "system", "content": sistema})
               messages.extend(historial)
               messages.append({"role": "user", "content": mensaje})

               if ollama is None:
                   estado.salida["respuesta"] = f"[mock] Respuesta a: {mensaje}"
                   return estado

               respuesta = await ollama.chat(messages=messages)
               if hasattr(respuesta, "content"):
                   estado.salida["respuesta"] = respuesta.content
               elif isinstance(respuesta, dict):
                   estado.salida["respuesta"] = respuesta.get("content", str(respuesta))
               else:
                   estado.salida["respuesta"] = str(respuesta)
               return estado

           n = NodoFuncion(id="nodo_chat", fn=fn, timeout=60.0, nombre_display="Chat LLM")
           n.descripcion = "Conversación con LLM via OllamaProvider"
           return n

       def _crear_nodo_embeddings(self) -> Nodo:
           """
           nodo_embeddings: Genera embeddings de texto.

           Entrada esperada en estado.entrada:
             - "texto": str — el texto a embeder

           Escribe en estado.salida:
             - "embedding": list[float] — vector de embeddings
             - "embedding_dim": int — dimensión del vector
           """
           ollama = self._ollama

           async def fn(estado: EstadoGrafo) -> EstadoGrafo:
               texto = estado.entrada.get("texto", "")

               if ollama is None:
                   # Mock: embedding de dimensión 4 para tests
                   estado.salida["embedding"] = [0.1, 0.2, 0.3, 0.4]
                   estado.salida["embedding_dim"] = 4
                   return estado

               embedding = await ollama.embeddings(texto)
               estado.salida["embedding"] = embedding
               estado.salida["embedding_dim"] = len(embedding)
               return estado

           n = NodoFuncion(id="nodo_embeddings", fn=fn, timeout=30.0, nombre_display="Embeddings")
           n.descripcion = "Genera embeddings de texto via OllamaProvider"
           return n

       def _crear_nodo_guardar_memoria(self) -> Nodo:
           """
           nodo_guardar_memoria: Guarda datos en Flash Memory.

           Entrada esperada en estado.entrada:
             - "dato": str — el dato a guardar
             - "tipo": str (opcional) — tipo de memoria (default: "general")
             - "importancia": float (opcional) — importancia 0.0-1.0 (default: 0.5)

           Escribe en estado.salida:
             - "memoria_id": str — ID de la memoria guardada
           También registra en estado.memoria_ids
           """
           flash_memory = self._flash_memory

           async def fn(estado: EstadoGrafo) -> EstadoGrafo:
               dato = estado.entrada.get("dato", "")
               tipo = estado.entrada.get("tipo", "general")
               importancia = estado.entrada.get("importancia", 0.5)

               if flash_memory is None:
                   memoria_id = f"mock-mem-{hash(dato) % 10000:04d}"
                   estado.salida["memoria_id"] = memoria_id
                   estado.registrar_memoria(memoria_id)
                   return estado

               memoria_id = await flash_memory.guardar(
                   dato=dato,
                   metadata={"tipo": tipo, "importancia": importancia}
               )
               estado.salida["memoria_id"] = memoria_id
               estado.registrar_memoria(memoria_id)
               return estado

           n = NodoFuncion(id="nodo_guardar_memoria", fn=fn, timeout=15.0, nombre_display="Guardar Memoria")
           n.descripcion = "Guarda datos en Flash Memory"
           return n

       def _crear_nodo_buscar_memoria(self) -> Nodo:
           """
           nodo_buscar_memoria: Busca en Flash Memory.

           Entrada esperada en estado.entrada:
             - "query": str — consulta de búsqueda
             - "tipo": str (opcional) — filtrar por tipo
             - "limite": int (opcional) — máximo de resultados (default: 5)

           Escribe en estado.salida:
             - "resultados": list[dict] — resultados de la búsqueda
             - "total_encontrados": int — cantidad de resultados
           """
           flash_memory = self._flash_memory

           async def fn(estado: EstadoGrafo) -> EstadoGrafo:
               query = estado.entrada.get("query", "")
               tipo = estado.entrada.get("tipo")
               limite = estado.entrada.get("limite", 5)

               if flash_memory is None:
                   estado.salida["resultados"] = [
                       {"id": "mock-1", "contenido": f"Resultado mock para: {query}", "score": 0.9}
                   ]
                   estado.salida["total_encontrados"] = 1
                   return estado

               resultados = await flash_memory.buscar(
                   query=query,
                   tipo=tipo,
                   limite=limite
               )
               estado.salida["resultados"] = resultados
               estado.salida["total_encontrados"] = len(resultados)
               return estado

           n = NodoFuncion(id="nodo_buscar_memoria", fn=fn, timeout=15.0, nombre_display="Buscar Memoria")
           n.descripcion = "Busca en Flash Memory por relevancia semántica"
           return n

       def _crear_nodo_log(self) -> Nodo:
           """
           nodo_log: Registra un mensaje en los logs.

           Entrada esperada en estado.entrada:
             - "mensaje_log": str — el mensaje a registrar
             - "nivel": str (opcional) — "debug"|"info"|"warning"|"error" (default: "info")

           Escribe en estado.salida:
             - "log_registrado": bool — True si se registró
           """
           import logging
           logger = logging.getLogger("yeyo.orquestador.nodo_log")

           async def fn(estado: EstadoGrafo) -> EstadoGrafo:
               mensaje = estado.entrada.get("mensaje_log", "")
               nivel = estado.entrada.get("nivel", "info").lower()

               log_fn = getattr(logger, nivel, logger.info)
               log_fn(f"[nodo_log] {mensaje}")

               estado.salida["log_registrado"] = True
               return estado

           n = NodoFuncion(id="nodo_log", fn=fn, timeout=5.0, nombre_display="Log")
           n.descripcion = "Registra un mensaje en los logs del sistema"
           return n

   # ── Hub Nodes (Capa 5) ──────────────────────────────────────────────────
   # Los nodos del Hub se registrarán aquí en Capa 5:
   # catalogo.registrar("hub.imagen.generar", ...)
   # catalogo.registrar("hub.video.componer", ...)
   # catalogo.registrar("hub.codigo.ejecutar", ...)
   # Esto permite grafos que coordinan múltiples nodos del Hub (GrafoMultiNodo)

2. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 — Capa 4: Sistema Nervioso
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError
   from .catalogo import CatalogoNodos, CatalogoError

3. Crear archivo tests/unit/orquestador/test_catalogo.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_catalogo.py
   Contenido:

   """Tests para CatalogoNodos — Micro-fase 4.20"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.catalogo import CatalogoNodos, CatalogoError


   # ─── Mocks ─────────────────────────────────────────────────────────────────

   def mock_ollama():
       m = AsyncMock()
       respuesta = MagicMock()
       respuesta.content = "Respuesta de prueba"
       m.chat = AsyncMock(return_value=respuesta)
       m.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
       return m


   def mock_flash_memory():
       m = AsyncMock()
       m.guardar = AsyncMock(return_value="mem-test-123")
       m.buscar = AsyncMock(return_value=[
           {"id": "mem-1", "contenido": "resultado test", "score": 0.9}
       ])
       return m


   class TestCatalogoNodosBase:

       def test_catalogo_tiene_5_nodos_base(self):
           catalogo = CatalogoNodos()
           assert len(catalogo.listar()) == 5

       def test_nodos_base_correctos(self):
           catalogo = CatalogoNodos()
           nodos = catalogo.listar()
           assert "nodo_chat" in nodos
           assert "nodo_embeddings" in nodos
           assert "nodo_guardar_memoria" in nodos
           assert "nodo_buscar_memoria" in nodos
           assert "nodo_log" in nodos

       def test_obtener_nodo_existente(self):
           catalogo = CatalogoNodos()
           nodo = catalogo.obtener("nodo_chat")
           assert nodo.id == "nodo_chat"

       def test_obtener_nodo_inexistente_falla(self):
           catalogo = CatalogoNodos()
           with pytest.raises(CatalogoError, match="no encontrado"):
               catalogo.obtener("nodo_inexistente")

       def test_existe_nodo(self):
           catalogo = CatalogoNodos()
           assert catalogo.existe("nodo_chat") is True
           assert catalogo.existe("nodo_magico") is False

       def test_describir_retorna_dict(self):
           catalogo = CatalogoNodos()
           descripciones = catalogo.describir()
           assert isinstance(descripciones, dict)
           assert len(descripciones) == 5

       def test_registrar_nodo_adicional(self):
           from src.orquestador.nodo import NodoInline
           catalogo = CatalogoNodos()
           nodo_extra = NodoInline(id="nodo_extra", fn=lambda e: e)
           catalogo.registrar(nodo_extra)
           assert catalogo.existe("nodo_extra")
           assert len(catalogo.listar()) == 6


   class TestNodoChat:

       @pytest.mark.asyncio
       async def test_nodo_chat_sin_ollama_usa_mock(self):
           catalogo = CatalogoNodos(ollama_provider=None)
           nodo = catalogo.obtener("nodo_chat")
           estado = EstadoGrafo(entrada={"mensaje": "Hola"})
           resultado = await nodo.ejecutar(estado)
           assert "respuesta" in resultado.salida
           assert "Hola" in resultado.salida["respuesta"]

       @pytest.mark.asyncio
       async def test_nodo_chat_con_ollama_mock(self):
           ollama = mock_ollama()
           catalogo = CatalogoNodos(ollama_provider=ollama)
           nodo = catalogo.obtener("nodo_chat")
           estado = EstadoGrafo(entrada={"mensaje": "Hola"})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["respuesta"] == "Respuesta de prueba"
           ollama.chat.assert_called_once()

       @pytest.mark.asyncio
       async def test_nodo_chat_pasa_sistema_y_historial(self):
           ollama = mock_ollama()
           catalogo = CatalogoNodos(ollama_provider=ollama)
           nodo = catalogo.obtener("nodo_chat")
           estado = EstadoGrafo(entrada={
               "mensaje": "Hola",
               "sistema": "Eres un asistente de YeyoOS",
               "historial": [{"role": "user", "content": "Mensaje anterior"}]
           })
           await nodo.ejecutar(estado)
           messages_usados = ollama.chat.call_args.kwargs.get("messages", [])
           assert messages_usados[0]["role"] == "system"
           assert "YeyoOS" in messages_usados[0]["content"]


   class TestNodoEmbeddings:

       @pytest.mark.asyncio
       async def test_nodo_embeddings_sin_ollama_usa_mock(self):
           catalogo = CatalogoNodos(ollama_provider=None)
           nodo = catalogo.obtener("nodo_embeddings")
           estado = EstadoGrafo(entrada={"texto": "hola mundo"})
           resultado = await nodo.ejecutar(estado)
           assert "embedding" in resultado.salida
           assert isinstance(resultado.salida["embedding"], list)
           assert "embedding_dim" in resultado.salida

       @pytest.mark.asyncio
       async def test_nodo_embeddings_con_ollama(self):
           ollama = mock_ollama()
           catalogo = CatalogoNodos(ollama_provider=ollama)
           nodo = catalogo.obtener("nodo_embeddings")
           estado = EstadoGrafo(entrada={"texto": "texto de prueba"})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["embedding_dim"] == 5
           assert resultado.salida["embedding"] == [0.1, 0.2, 0.3, 0.4, 0.5]


   class TestNodoGuardarMemoria:

       @pytest.mark.asyncio
       async def test_nodo_guardar_sin_flash_memory_usa_mock(self):
           catalogo = CatalogoNodos(flash_memory=None)
           nodo = catalogo.obtener("nodo_guardar_memoria")
           estado = EstadoGrafo(entrada={"dato": "algo importante", "tipo": "nota"})
           resultado = await nodo.ejecutar(estado)
           assert "memoria_id" in resultado.salida
           assert len(resultado.memoria_ids) == 1

       @pytest.mark.asyncio
       async def test_nodo_guardar_con_flash_memory(self):
           flash = mock_flash_memory()
           catalogo = CatalogoNodos(flash_memory=flash)
           nodo = catalogo.obtener("nodo_guardar_memoria")
           estado = EstadoGrafo(entrada={"dato": "dato importante", "importancia": 0.9})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["memoria_id"] == "mem-test-123"
           assert "mem-test-123" in resultado.memoria_ids
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_nodo_guardar_registra_en_estado(self):
           catalogo = CatalogoNodos(flash_memory=None)
           nodo = catalogo.obtener("nodo_guardar_memoria")
           estado = EstadoGrafo(entrada={"dato": "test"})
           resultado = await nodo.ejecutar(estado)
           assert len(resultado.memoria_ids) == 1


   class TestNodoBuscarMemoria:

       @pytest.mark.asyncio
       async def test_nodo_buscar_sin_flash_memory_usa_mock(self):
           catalogo = CatalogoNodos(flash_memory=None)
           nodo = catalogo.obtener("nodo_buscar_memoria")
           estado = EstadoGrafo(entrada={"query": "buscar algo"})
           resultado = await nodo.ejecutar(estado)
           assert "resultados" in resultado.salida
           assert "total_encontrados" in resultado.salida
           assert resultado.salida["total_encontrados"] >= 0

       @pytest.mark.asyncio
       async def test_nodo_buscar_con_flash_memory(self):
           flash = mock_flash_memory()
           catalogo = CatalogoNodos(flash_memory=flash)
           nodo = catalogo.obtener("nodo_buscar_memoria")
           estado = EstadoGrafo(entrada={"query": "algo importante", "limite": 3})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["total_encontrados"] == 1
           flash.buscar.assert_called_once()


   class TestNodoLog:

       @pytest.mark.asyncio
       async def test_nodo_log_registra_correctamente(self):
           catalogo = CatalogoNodos()
           nodo = catalogo.obtener("nodo_log")
           estado = EstadoGrafo(entrada={"mensaje_log": "Prueba de log", "nivel": "info"})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["log_registrado"] is True

       @pytest.mark.asyncio
       async def test_nodo_log_con_mensaje_vacio(self):
           catalogo = CatalogoNodos()
           nodo = catalogo.obtener("nodo_log")
           estado = EstadoGrafo(entrada={})
           resultado = await nodo.ejecutar(estado)
           assert resultado.salida["log_registrado"] is True

   class TestCatalogoHubNodes:
       """Verifica que el catálogo acepta registrar nodos con prefijo hub.*"""

       def test_registrar_nodo_hub_imagen(self):
           catalogo = CatalogoNodos()
           from src.orquestador.nodo import NodoFuncion
           async def fn(e): return e
           nodo_hub = NodoFuncion(id="hub.imagen.generar", fn=fn, timeout=10.0,
                                  nombre_display="Hub Imagen Generar")
           catalogo.registrar("hub.imagen.generar", nodo_hub)
           assert catalogo.obtener("hub.imagen.generar") is nodo_hub

       def test_registrar_multiples_nodos_hub(self):
           catalogo = CatalogoNodos()
           from src.orquestador.nodo import NodoFuncion
           async def fn(e): return e
           for nombre in ["hub.imagen.generar", "hub.video.componer", "hub.codigo.ejecutar"]:
               n = NodoFuncion(id=nombre, fn=fn, timeout=10.0, nombre_display=nombre)
               catalogo.registrar(nombre, n)
           for nombre in ["hub.imagen.generar", "hub.video.componer", "hub.codigo.ejecutar"]:
               assert catalogo.obtener(nombre) is not None

       def test_nodos_hub_no_reemplazan_nodos_base(self):
           catalogo = CatalogoNodos()
           from src.orquestador.nodo import NodoFuncion
           async def fn(e): return e
           nodo_hub = NodoFuncion(id="hub.imagen.generar", fn=fn, timeout=10.0,
                                  nombre_display="Hub Imagen")
           catalogo.registrar("hub.imagen.generar", nodo_hub)
           for nombre_base in ["nodo_chat", "nodo_embeddings", "nodo_guardar_memoria",
                               "nodo_buscar_memoria", "nodo_log"]:
               assert catalogo.obtener(nombre_base) is not None

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_catalogo.py -v

VERIFICAR:
- [ ] src/orquestador/catalogo.py existe con CatalogoNodos
- [ ] Catálogo tiene exactamente 5 nodos base por defecto
- [ ] nodo_chat usa OllamaProvider si está disponible, mock si no
- [ ] nodo_embeddings retorna vector de embeddings
- [ ] nodo_guardar_memoria registra en estado.memoria_ids
- [ ] nodo_buscar_memoria retorna lista de resultados
- [ ] nodo_log registra sin fallar y retorna log_registrado=True
- [ ] Se pueden registrar nodos adicionales
- [ ] TODOS los tests pasan

SI FALLA:
- OllamaProvider no existe aún: usar None en CatalogoNodos(ollama_provider=None) — usa mocks automáticamente
- FlashMemory no existe aún: usar None en CatalogoNodos(flash_memory=None)
- Import error: verificar que catalogo.py importa de .nodo correctamente

NO HACER:
- No conectar con OllamaProvider real — usar el mock de los tests
- No conectar con FlashMemory real — usar el mock
- No crear GeneradorGrafos aún (eso es micro-fase 5.24)

GATE: Catálogo tiene 5 nodos base, cada uno ejecuta su función correctamente con mocks de OllamaProvider y FlashMemory, se pueden registrar nodos adicionales, todos los tests pasan.
```
