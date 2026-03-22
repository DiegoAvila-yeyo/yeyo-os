## ═══════════════════════════════════════
## MICRO-FASE 4.21 — Grafos Estáticos Principales
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.21-1 [VSCODE] — Grafos predefinidos: chat contextual y búsqueda semántica

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.21 de Capa 4 (Sistema Nervioso): crear los grafos estáticos principales que usa YeyoOrquestador como tools predefinidas.

CONTEXTO:
- Micro-fases 4.14-4.20 completadas: orquestador completo + catálogo de nodos
- CatalogoNodos disponible en src/orquestador/catalogo.py
- Grafo 1: grafo_chat_contextual — mejora prompt → chat → extrae memorias → guarda
- Grafo 2: grafo_busqueda_semantica — embedding → buscar → rankear → responder
- Cada grafo es una función que retorna YeyoGrafo configurado (factory function)
- Los grafos usan los nodos del catálogo

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio:
   mkdir -p src/orquestador/grafos

2. Crear archivo src/orquestador/grafos/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/grafos/__init__.py
   Contenido:
   from .chat_contextual import crear_grafo_chat_contextual
   from .busqueda_semantica import crear_grafo_busqueda_semantica
   from .hacer_reel import crear_grafo_hacer_reel

3. Crear archivo src/orquestador/grafos/chat_contextual.py:

   Ruta: ~/yeyo-os/src/orquestador/grafos/chat_contextual.py
   Contenido:

   """
   YeyoOS — Grafo de Chat Contextual
   Micro-fase 4.21 — Capa 4: Sistema Nervioso

   Flujo: mejora prompt → chat con LLM → extrae memorias relevantes → guarda en Flash Memory
   """

   from typing import Optional, Any
   from ..estado import EstadoGrafo
   from ..nodo import nodo, NodoFuncion
   from ..grafo import YeyoGrafo
   from ..catalogo import CatalogoNodos


   def crear_grafo_chat_contextual(
       ollama_provider: Optional[Any] = None,
       flash_memory: Optional[Any] = None,
   ) -> YeyoGrafo:
       """
       Factory: crea y retorna el grafo de chat contextual configurado.

       Flujo de nodos:
       1. mejorar_prompt: enriquece el prompt con contexto del historial
       2. nodo_chat: envía el prompt mejorado a Ollama
       3. extraer_memorias: identifica datos importantes en la respuesta
       4. nodo_guardar_memoria: guarda las memorias extraídas

       Entrada esperada en estado.entrada:
         - "mensaje": str — mensaje del usuario
         - "historial": list (opcional) — mensajes previos
         - "usuario_id": str (opcional) — ID del usuario

       Salida en estado.salida:
         - "respuesta": str — respuesta final del LLM
         - "memorias_guardadas": int — cantidad de memorias nuevas guardadas
       """
       catalogo = CatalogoNodos(
           ollama_provider=ollama_provider,
           flash_memory=flash_memory,
       )

       @nodo(id="mejorar_prompt", timeout=10.0)
       async def mejorar_prompt(estado: EstadoGrafo) -> EstadoGrafo:
           """Enriquece el prompt con contexto del sistema."""
           mensaje_original = estado.entrada.get("mensaje", "")
           usuario_id = estado.entrada.get("usuario_id", "anonimo")
           historial = estado.entrada.get("historial", [])

           # El prompt mejorado incluye el sistema base de YeyoOS
           estado.contexto["mensaje_mejorado"] = mensaje_original
           estado.contexto["historial_procesado"] = historial
           estado.contexto["usuario_id"] = usuario_id

           # Preparar entrada para nodo_chat
           estado.entrada["mensaje"] = mensaje_original
           estado.entrada["sistema"] = (
               "Eres YeyoOS, un asistente AI nativo e inteligente. "
               "Responde de forma concisa y útil."
           )
           estado.entrada["historial"] = historial
           return estado

       @nodo(id="extraer_memorias", timeout=15.0)
       async def extraer_memorias(estado: EstadoGrafo) -> EstadoGrafo:
           """
           Identifica datos importantes en la respuesta del LLM
           y los prepara para guardar en Flash Memory.
           """
           respuesta = estado.salida.get("respuesta", "")
           mensaje_usuario = estado.entrada.get("mensaje", "")

           # Preparar dato para nodo_guardar_memoria
           estado.entrada["dato"] = f"Usuario: {mensaje_usuario}\nAsistente: {respuesta}"
           estado.entrada["tipo"] = "conversacion"
           estado.entrada["importancia"] = 0.6
           return estado

       @nodo(id="finalizar_chat", timeout=5.0)
       async def finalizar_chat(estado: EstadoGrafo) -> EstadoGrafo:
           """Finaliza el flujo y prepara la respuesta final."""
           memoria_id = estado.salida.get("memoria_id")
           estado.salida["memorias_guardadas"] = 1 if memoria_id else 0
           return estado

       nodo_chat = catalogo.obtener("nodo_chat")
       nodo_guardar = catalogo.obtener("nodo_guardar_memoria")

       grafo = (
           YeyoGrafo(
               "grafo_chat_contextual",
               "Conversación contextual con memoria: mejora prompt → chat → guarda memoria"
           )
           .agregar_nodo(mejorar_prompt)
           .agregar_nodo(nodo_chat)
           .agregar_nodo(extraer_memorias)
           .agregar_nodo(nodo_guardar)
           .agregar_nodo(finalizar_chat)
           .inicio("mejorar_prompt")
           .edge("mejorar_prompt", "nodo_chat")
           .edge("nodo_chat", "extraer_memorias")
           .edge("extraer_memorias", "nodo_guardar_memoria")
           .edge("nodo_guardar_memoria", "finalizar_chat")
           .fin("finalizar_chat")
       )

       return grafo

4. Crear archivo src/orquestador/grafos/busqueda_semantica.py:

   Ruta: ~/yeyo-os/src/orquestador/grafos/busqueda_semantica.py
   Contenido:

   """
   YeyoOS — Grafo de Búsqueda Semántica
   Micro-fase 4.21 — Capa 4: Sistema Nervioso

   Flujo: embedding → buscar en Flash Memory → rankear → responder con contexto
   """

   from typing import Optional, Any
   from ..estado import EstadoGrafo
   from ..nodo import nodo
   from ..grafo import YeyoGrafo
   from ..catalogo import CatalogoNodos


   def crear_grafo_busqueda_semantica(
       ollama_provider: Optional[Any] = None,
       flash_memory: Optional[Any] = None,
   ) -> YeyoGrafo:
       """
       Factory: crea y retorna el grafo de búsqueda semántica configurado.

       Flujo de nodos:
       1. preparar_busqueda: normaliza la query de búsqueda
       2. nodo_embeddings: genera embedding de la query
       3. nodo_buscar_memoria: busca en Flash Memory por similitud
       4. rankear_resultados: ordena y filtra los resultados
       5. generar_respuesta: usa LLM para sintetizar los resultados

       Entrada esperada en estado.entrada:
         - "query": str — consulta del usuario
         - "limite": int (opcional) — máximo de resultados (default: 5)

       Salida en estado.salida:
         - "respuesta": str — respuesta sintetizada con los resultados
         - "resultados": list[dict] — resultados crudos de la búsqueda
         - "total_encontrados": int — cantidad de resultados
       """
       catalogo = CatalogoNodos(
           ollama_provider=ollama_provider,
           flash_memory=flash_memory,
       )

       @nodo(id="preparar_busqueda", timeout=5.0)
       async def preparar_busqueda(estado: EstadoGrafo) -> EstadoGrafo:
           """Normaliza la query y prepara los parámetros de búsqueda."""
           query = estado.entrada.get("query", "")
           limite = estado.entrada.get("limite", 5)

           estado.contexto["query_original"] = query
           # Para nodo_embeddings
           estado.entrada["texto"] = query
           # Para nodo_buscar_memoria
           estado.contexto["limite_busqueda"] = limite
           return estado

       @nodo(id="preparar_consulta_memoria", timeout=5.0)
       async def preparar_consulta_memoria(estado: EstadoGrafo) -> EstadoGrafo:
           """Transfiere parámetros del embedding a la búsqueda en memoria."""
           estado.entrada["query"] = estado.contexto.get("query_original", "")
           estado.entrada["limite"] = estado.contexto.get("limite_busqueda", 5)
           return estado

       @nodo(id="rankear_resultados", timeout=5.0)
       async def rankear_resultados(estado: EstadoGrafo) -> EstadoGrafo:
           """Ordena y filtra los resultados por score de relevancia."""
           resultados = estado.salida.get("resultados", [])

           # Filtrar resultados con score >= 0.5 y ordenar descendente
           resultados_filtrados = sorted(
               [r for r in resultados if r.get("score", 0) >= 0.5],
               key=lambda r: r.get("score", 0),
               reverse=True
           )

           estado.salida["resultados"] = resultados_filtrados
           estado.salida["total_encontrados"] = len(resultados_filtrados)

           # Preparar contexto para la respuesta final
           if resultados_filtrados:
               contexto_resultados = "\n".join([
                   f"- {r.get('contenido', '')}" for r in resultados_filtrados[:3]
               ])
               estado.entrada["mensaje"] = (
                   f"Basándote en estos resultados encontrados:\n{contexto_resultados}\n\n"
                   f"Responde a la pregunta: {estado.contexto.get('query_original', '')}"
               )
               estado.entrada["sistema"] = "Sintetiza la información encontrada de forma clara y concisa."
           else:
               estado.entrada["mensaje"] = (
                   f"No encontré información relevante sobre: "
                   f"{estado.contexto.get('query_original', '')}"
               )
               estado.entrada["sistema"] = "Indica amablemente que no se encontró información relevante."

           return estado

       nodo_embeddings = catalogo.obtener("nodo_embeddings")
       nodo_buscar = catalogo.obtener("nodo_buscar_memoria")
       nodo_chat = catalogo.obtener("nodo_chat")

       grafo = (
           YeyoGrafo(
               "grafo_busqueda_semantica",
               "Búsqueda semántica: embedding → buscar en memoria → rankear → responder"
           )
           .agregar_nodo(preparar_busqueda)
           .agregar_nodo(nodo_embeddings)
           .agregar_nodo(preparar_consulta_memoria)
           .agregar_nodo(nodo_buscar)
           .agregar_nodo(rankear_resultados)
           .agregar_nodo(nodo_chat)
           .inicio("preparar_busqueda")
           .edge("preparar_busqueda", "nodo_embeddings")
           .edge("nodo_embeddings", "preparar_consulta_memoria")
           .edge("preparar_consulta_memoria", "nodo_buscar_memoria")
           .edge("nodo_buscar_memoria", "rankear_resultados")
           .edge("rankear_resultados", "nodo_chat")
           .fin("nodo_chat")
       )

       return grafo

4. Crear archivo src/orquestador/grafos/hacer_reel.py:

   Ruta: ~/yeyo-os/src/orquestador/grafos/hacer_reel.py
   Contenido:

   """
   YeyoOS — GrafoMultiNodo: Hacer Reel
   Micro-fase 4.21 — Capa 4: Sistema Nervioso

   Flujo: generar guión → imágenes paralelas (3 ó 5) → componer video → guardar
   Demuestra coordinación entre múltiples Hub Nodes (GrafoMultiNodo).
   """

   from typing import Optional, Any
   from ..estado import EstadoGrafo
   from ..nodo import nodo, NodoFuncion
   from ..grafo import YeyoGrafo
   from ..paralelo import NodoParalelo
   from ..edge import FIN_GRAFO
   from ..catalogo import CatalogoNodos


   def _crear_mock_imagen(idx: int):
       """Nodo imagen mock para usar cuando hub.imagen.generar no está disponible."""
       async def fn(estado: EstadoGrafo) -> EstadoGrafo:
           imagenes = estado.salida.get("imagenes", [])
           imagenes.append(f"imagen_mock_{idx}.png")
           estado.salida["imagenes"] = imagenes
           return estado
       n = NodoFuncion(id=f"mock_imagen_{idx}", fn=fn, timeout=10.0,
                       nombre_display=f"Mock Imagen {idx}")
       n.descripcion = f"Genera imagen mock #{idx} (hub.imagen.generar no disponible)"
       return n


   def crear_grafo_hacer_reel(
       ollama_provider: Optional[Any] = None,
       hub_imagen: Optional[Any] = None,
       hub_video: Optional[Any] = None,
       flash_memory: Optional[Any] = None,
   ) -> YeyoGrafo:
       """
       Factory: crea y retorna el GrafoMultiNodo para hacer un reel.

       Flujo de nodos:
       1. generar_guion: llama a nodo_chat para crear guión con escenas
       2a. generar_imagenes_x5: NodoParalelo con 5 instancias (si guión > 5 escenas)
       2b. generar_imagenes_x3: NodoParalelo con 3 instancias (si guión ≤ 5 escenas)
       3. componer_video: llama a hub.video.componer con las imágenes generadas
       4. guardar: llama a nodo_guardar_memoria para persistir el resultado

       Entrada esperada en estado.entrada:
         - "tema": str — tema o descripción del reel
         - "usuario_id": str (opcional) — ID del usuario

       Salida en estado.salida:
         - "guion": str — guión generado
         - "imagenes": list[str] — rutas de imágenes generadas
         - "video_path": str — ruta del video compuesto
       """
       catalogo = CatalogoNodos(
           ollama_provider=ollama_provider,
           flash_memory=flash_memory,
       )

       if hub_imagen is not None:
           catalogo.registrar("hub.imagen.generar", hub_imagen)
       if hub_video is not None:
           catalogo.registrar("hub.video.componer", hub_video)

       @nodo(id="generar_guion")
       async def generar_guion(estado: EstadoGrafo) -> EstadoGrafo:
           tema = estado.entrada.get("tema", "reel genérico")
           if ollama_provider is None:
               estado.salida["guion"] = "ESCENA 1: Intro\nESCENA 2: Desarrollo\nESCENA 3: Cierre"
               estado.salida["num_escenas"] = 3
               return estado
           respuesta = await ollama_provider.chat(
               f"Crea un guión corto para un reel sobre: {tema}. Numera cada escena como ESCENA N:"
           )
           guion = respuesta.content
           estado.salida["guion"] = guion
           estado.salida["num_escenas"] = guion.count("ESCENA")
           return estado

       def _rama_imagenes(estado: EstadoGrafo) -> str:
           return "muchas" if estado.salida.get("num_escenas", 0) > 5 else "pocas"

       nodo_imagen = catalogo.obtener("hub.imagen.generar") if hub_imagen else None
       imagenes_x5 = NodoParalelo(
           id="generar_imagenes_x5",
           nodos=[nodo_imagen or _crear_mock_imagen(i) for i in range(5)],
       )
       imagenes_x3 = NodoParalelo(
           id="generar_imagenes_x3",
           nodos=[nodo_imagen or _crear_mock_imagen(i) for i in range(3)],
       )

       @nodo(id="componer_video")
       async def componer_video(estado: EstadoGrafo) -> EstadoGrafo:
           imagenes = estado.salida.get("imagenes", [])
           if hub_video is not None:
               resultado = await hub_video.ejecutar(estado)
               estado.salida["video_path"] = resultado.salida.get("video_path", "reel.mp4")
           else:
               estado.salida["video_path"] = f"reel_{len(imagenes)}_frames_mock.mp4"
           return estado

       nodo_guardar = catalogo.obtener("nodo_guardar_memoria")

       grafo = (
           YeyoGrafo("grafo_hacer_reel")
           .descripcion("GrafoMultiNodo: guión → imágenes paralelas → video → guardado")
           .agregar_nodo(generar_guion)
           .agregar_nodo(imagenes_x5)
           .agregar_nodo(imagenes_x3)
           .agregar_nodo(componer_video)
           .agregar_nodo(nodo_guardar)
           .inicio("generar_guion")
           .edge_condicional("generar_guion", _rama_imagenes, {
               "muchas": "generar_imagenes_x5",
               "pocas":  "generar_imagenes_x3",
           })
           .edge("generar_imagenes_x5", "componer_video")
           .edge("generar_imagenes_x3", "componer_video")
           .edge("componer_video", "nodo_guardar_memoria")
           .fin("nodo_guardar_memoria")
       )
       return grafo

5. Crear archivo tests/unit/orquestador/test_grafos_estaticos.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_grafos_estaticos.py
   Contenido:

   """Tests de integración mock para grafos estáticos — Micro-fase 4.21"""

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.grafos import (
       crear_grafo_chat_contextual,
       crear_grafo_busqueda_semantica,
   )


   def mock_ollama(respuesta_texto="Respuesta de prueba"):
       m = AsyncMock()
       resp = MagicMock()
       resp.content = respuesta_texto
       m.chat = AsyncMock(return_value=resp)
       m.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
       return m


   def mock_flash_memory(resultados=None):
       m = AsyncMock()
       m.guardar = AsyncMock(return_value="mem-test-001")
       m.buscar = AsyncMock(return_value=resultados or [
           {"id": "m1", "contenido": "información relevante", "score": 0.9}
       ])
       return m


   class TestGrafoChatContextual:

       def test_crear_grafo_chat_contextual(self):
           grafo = crear_grafo_chat_contextual()
           assert grafo.id == "grafo_chat_contextual"
           assert grafo._nodo_inicio == "mejorar_prompt"

       def test_grafo_tiene_descripcion(self):
           grafo = crear_grafo_chat_contextual()
           assert grafo.descripcion != ""

       @pytest.mark.asyncio
       async def test_ejecuta_con_mocks_sin_providers(self):
           grafo = crear_grafo_chat_contextual()
           resultado = await grafo.ejecutar({"mensaje": "Hola, ¿cómo estás?"})
           assert resultado.exito is True
           assert "respuesta" in resultado.estado_final.salida

       @pytest.mark.asyncio
       async def test_ejecuta_con_ollama_mock(self):
           ollama = mock_ollama("Estoy bien, gracias por preguntar")
           flash = mock_flash_memory()
           grafo = crear_grafo_chat_contextual(ollama_provider=ollama, flash_memory=flash)
           resultado = await grafo.ejecutar({"mensaje": "¿Cómo estás?", "usuario_id": "u1"})
           assert resultado.exito is True
           assert resultado.estado_final.salida["respuesta"] == "Estoy bien, gracias por preguntar"

       @pytest.mark.asyncio
       async def test_guarda_memoria_de_la_conversacion(self):
           ollama = mock_ollama()
           flash = mock_flash_memory()
           grafo = crear_grafo_chat_contextual(ollama_provider=ollama, flash_memory=flash)
           resultado = await grafo.ejecutar({"mensaje": "recuerda que me gustan los gatos"})
           assert resultado.exito is True
           flash.guardar.assert_called_once()

       @pytest.mark.asyncio
       async def test_historial_en_contexto_funciona(self):
           ollama = mock_ollama()
           grafo = crear_grafo_chat_contextual(ollama_provider=ollama)
           historial = [
               {"role": "user", "content": "Hola"},
               {"role": "assistant", "content": "¡Hola!"},
           ]
           resultado = await grafo.ejecutar({"mensaje": "¿Recuerdas lo anterior?", "historial": historial})
           assert resultado.exito is True


   class TestGrafoBusquedaSemantica:

       def test_crear_grafo_busqueda_semantica(self):
           grafo = crear_grafo_busqueda_semantica()
           assert grafo.id == "grafo_busqueda_semantica"
           assert grafo._nodo_inicio == "preparar_busqueda"

       def test_grafo_tiene_descripcion(self):
           grafo = crear_grafo_busqueda_semantica()
           assert grafo.descripcion != ""

       @pytest.mark.asyncio
       async def test_ejecuta_con_mocks_sin_providers(self):
           grafo = crear_grafo_busqueda_semantica()
           resultado = await grafo.ejecutar({"query": "información sobre gatos"})
           assert resultado.exito is True

       @pytest.mark.asyncio
       async def test_ejecuta_con_resultados_de_flash_memory(self):
           ollama = mock_ollama("Los gatos son animales independientes")
           flash = mock_flash_memory([
               {"id": "m1", "contenido": "Los gatos son mascotas populares", "score": 0.95},
               {"id": "m2", "contenido": "Los gatos duermen mucho", "score": 0.85},
           ])
           grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
           resultado = await grafo.ejecutar({"query": "gatos"})
           assert resultado.exito is True
           assert "respuesta" in resultado.estado_final.salida

       @pytest.mark.asyncio
       async def test_genera_embeddings_de_la_query(self):
           ollama = mock_ollama()
           flash = mock_flash_memory()
           grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
           await grafo.ejecutar({"query": "buscar algo importante"})
           ollama.embeddings.assert_called_once_with("buscar algo importante")

       @pytest.mark.asyncio
       async def test_resultados_bajos_filtrados(self):
           ollama = mock_ollama("No encontré información relevante")
           flash = mock_flash_memory([
               {"id": "m1", "contenido": "resultado poco relevante", "score": 0.2}
           ])
           grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
           resultado = await grafo.ejecutar({"query": "busqueda sin resultados"})
           assert resultado.exito is True
           assert resultado.estado_final.salida.get("total_encontrados", 0) == 0

   class TestGrafoHacerReel:

       def test_crear_grafo_hacer_reel(self):
           from src.orquestador.grafos import crear_grafo_hacer_reel
           grafo = crear_grafo_hacer_reel()
           assert grafo.id == "grafo_hacer_reel"
           assert grafo._nodo_inicio == "generar_guion"

       def test_grafo_tiene_descripcion(self):
           from src.orquestador.grafos import crear_grafo_hacer_reel
           grafo = crear_grafo_hacer_reel()
           assert "GrafoMultiNodo" in grafo.descripcion

       @pytest.mark.asyncio
       async def test_ejecuta_con_mocks_sin_providers(self):
           from src.orquestador.grafos import crear_grafo_hacer_reel
           grafo = crear_grafo_hacer_reel()
           resultado = await grafo.ejecutar({"tema": "viaje a la luna"})
           assert resultado.exito is True
           assert "guion" in resultado.estado_final.salida

       @pytest.mark.asyncio
       async def test_rama_pocas_imagenes_con_3_escenas(self):
           from src.orquestador.grafos import crear_grafo_hacer_reel
           grafo = crear_grafo_hacer_reel()
           resultado = await grafo.ejecutar({"tema": "test"})
           # Sin ollama → 3 escenas → rama "pocas" → generar_imagenes_x3
           assert resultado.exito is True
           assert "video_path" in resultado.estado_final.salida

       @pytest.mark.asyncio
       async def test_rama_muchas_imagenes_con_ollama(self):
           from src.orquestador.grafos import crear_grafo_hacer_reel
           ollama = mock_ollama(
               "ESCENA 1: A\nESCENA 2: B\nESCENA 3: C\nESCENA 4: D\nESCENA 5: E\nESCENA 6: F"
           )
           grafo = crear_grafo_hacer_reel(ollama_provider=ollama)
           resultado = await grafo.ejecutar({"tema": "épica odisea"})
           assert resultado.exito is True
           assert "video_path" in resultado.estado_final.salida

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_grafos_estaticos.py -v

VERIFICAR:
- [ ] Directorio src/orquestador/grafos/ existe con __init__.py
- [ ] crear_grafo_chat_contextual() retorna YeyoGrafo con ID correcto
- [ ] crear_grafo_busqueda_semantica() retorna YeyoGrafo con ID correcto
- [ ] crear_grafo_hacer_reel() retorna YeyoGrafo con ID "grafo_hacer_reel"
- [ ] grafo_chat_contextual ejecuta con providers mock y sin providers (usa defaults del catálogo)
- [ ] grafo_chat_contextual guarda memoria de la conversación
- [ ] grafo_busqueda_semantica genera embedding de la query
- [ ] grafo_busqueda_semantica filtra resultados con score < 0.5
- [ ] grafo_hacer_reel toma rama "pocas" (3 imágenes) cuando guión tiene ≤ 5 escenas
- [ ] grafo_hacer_reel toma rama "muchas" (5 imágenes) cuando guión tiene > 5 escenas
- [ ] grafo_hacer_reel produce "video_path" en estado final
- [ ] TODOS los tests pasan

SI FALLA:
- Nodo ID duplicado: verificar que nodo_chat del catálogo y los nodos inline tienen IDs únicos
- Flujo roto: verificar que los edge() usan los IDs exactos de los nodos agregados
- CatalogoNodos no encontrado: verificar que el import de catalogo.py funciona

NO HACER:
- No crear grafos para todas las funcionalidades (solo chat y búsqueda en esta micro-fase)
- No conectar con Ollama/FlashMemory reales — solo mocks en tests
- No implementar grafos dinámicos generados por IA (eso es micro-fase 5.24)

GATE: Los 2 grafos estáticos se construyen sin errores y ejecutan correctamente con datos mock de OllamaProvider y FlashMemory.
```
