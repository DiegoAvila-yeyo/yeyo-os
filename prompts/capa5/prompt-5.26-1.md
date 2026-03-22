## ═══════════════════════════════════════
## MICRO-FASE 5.26 — Integration Test Grafos Avanzados
## Tipo: MIXTA | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.26-1 [VSCODE] — Test de integración de las 4 features avanzadas de grafos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.26 de Capa 5 (Órganos): crear el test de integración que verifica que las 4 features avanzadas de grafos (checkpoint, cache, generador, validador) funcionan correctamente de forma integrada.

CONTEXTO:
- Micro-fases 5.22-5.25 completadas: GrafoCheckpoint, NodoCache, GeneradorGrafos, GrafoValidador
- Tests unitarios de cada feature ya existen
- Este test verifica que todas las piezas encajan correctamente de forma integrada
- Los 4 escenarios: checkpoint+reanudación, cache hit en segundo run, grafo generado por IA, validación de código peligroso bloqueado

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo tests/integration/test_grafos_avanzados.py:

   Ruta: ~/yeyo-os/tests/integration/test_grafos_avanzados.py
   Contenido:

   """
   Tests de integración de features avanzadas de grafos — Micro-fase 5.26

   Escenarios:
   1. Checkpoint + reanudación de grafo interrumpido
   2. Cache hit evita re-ejecución en segundo run
   3. Grafo generado por IA desde descripción simple
   4. Validación de código peligroso bloqueado correctamente
   """

   import json
   import pytest
   from datetime import datetime, timezone
   from unittest.mock import AsyncMock, MagicMock

   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo, NodoFuncion
   from src.orquestador.grafo import YeyoGrafo
   from src.orquestador.checkpoint import GrafoCheckpoint, TIPO_CHECKPOINT
   from src.orquestador.cache import NodoCache, TIPO_CACHE
   from src.orquestador.generador import GeneradorGrafos, GeneradorGrafosError
   from src.orquestador.validador import GrafoValidador


   # ═══════════════════════════════════════════════════════════════════════════
   # Fixtures compartidos
   # ═══════════════════════════════════════════════════════════════════════════

   class FlashMemoryMock:
       """Mock de FlashMemory con persistencia en memoria para tests de integración."""

       def __init__(self):
           self._datos: dict = {}
           self._contador = 0

       async def guardar(self, dato: str, metadata: dict = None) -> str:
           self._contador += 1
           mid = f"mem-integ-{self._contador:04d}"
           self._datos[mid] = {
               "contenido": dato,
               "metadata": metadata or {},
               "guardado_en": datetime.now(timezone.utc).isoformat(),
           }
           return mid

       async def buscar(self, query: str, tipo: str = None, limite: int = 10) -> list:
           resultados = []
           for mid, data in self._datos.items():
               if tipo and data["metadata"].get("tipo") != tipo:
                   continue
               resultados.append({
                   "id": mid,
                   "contenido": data["contenido"],
                   "score": 0.9,
               })
           return resultados[:limite]

       def limpiar(self):
           self._datos.clear()
           self._contador = 0


   def mock_ollama_genera(codigo: str):
       m = AsyncMock()
       resp = MagicMock()
       resp.content = f"```python\n{codigo}\n```"
       resp.tool_calls = None
       m.chat = AsyncMock(return_value=resp)
       m.embeddings = AsyncMock(return_value=[0.1, 0.2])
       return m


   # ═══════════════════════════════════════════════════════════════════════════
   # Escenario 1: Checkpoint + Reanudación
   # ═══════════════════════════════════════════════════════════════════════════

   class TestCheckpointReanudacion:

       @pytest.mark.asyncio
       async def test_reanudacion_desde_checkpoint(self):
           """
           Simula un grafo interrumpido y su reanudación:
           1. Ejecutar grafo y guardar checkpoint manual del estado intermedio
           2. Simular interrupción (no ejecutar los nodos restantes)
           3. Reanudar desde el checkpoint
           4. Verificar que el estado se reconstruye correctamente
           """
           flash = FlashMemoryMock()
           cp = GrafoCheckpoint(flash, grafo_id="grafo_reanudable")

           @nodo(id="setup_datos")
           async def setup_datos(estado: EstadoGrafo) -> EstadoGrafo:
               estado.salida["datos_configurados"] = True
               estado.contexto["usuarios"] = ["u1", "u2", "u3"]
               return estado

           g = (YeyoGrafo("grafo_reanudable")
                .agregar_nodo(setup_datos)
                .inicio("setup_datos")
                .fin("setup_datos"))

           # Ejecutar grafo normal
           resultado = await g.ejecutar({}, on_evento=cp.on_evento_checkpoint)
           assert resultado.exito is True

           # Guardar estado completo para reanudación
           await cp.guardar_estado(resultado.estado_final)

           # Verificar que se guardaron checkpoints en Flash Memory
           assert flash._contador > 0

           # Reconstruir estado desde Flash Memory
           estado_recuperado = await GrafoCheckpoint.reanudar("grafo_reanudable", flash)
           assert estado_recuperado is not None
           assert estado_recuperado.salida["datos_configurados"] is True
           assert estado_recuperado.contexto["usuarios"] == ["u1", "u2", "u3"]

       @pytest.mark.asyncio
       async def test_checkpoint_guarda_por_nodo_completado(self):
           """Verifica que cada nodo completado genera un checkpoint."""
           flash = FlashMemoryMock()
           cp = GrafoCheckpoint(flash, grafo_id="grafo_multi_nodo")

           @nodo(id="nodo_1")
           async def n1(e: EstadoGrafo) -> EstadoGrafo:
               e.salida["n1"] = True
               return e

           @nodo(id="nodo_2")
           async def n2(e: EstadoGrafo) -> EstadoGrafo:
               e.salida["n2"] = True
               return e

           @nodo(id="nodo_3")
           async def n3(e: EstadoGrafo) -> EstadoGrafo:
               e.salida["n3"] = True
               return e

           g = (YeyoGrafo("grafo_multi_nodo")
                .agregar_nodo(n1)
                .agregar_nodo(n2)
                .agregar_nodo(n3)
                .inicio("nodo_1")
                .edge("nodo_1", "nodo_2")
                .edge("nodo_2", "nodo_3")
                .fin("nodo_3"))

           await g.ejecutar({}, on_evento=cp.on_evento_checkpoint)

           # Debe haber al menos 3 checkpoints (uno por nodo completado)
           checkpoints = await flash.buscar(query="", tipo=TIPO_CHECKPOINT)
           assert len(checkpoints) >= 3

       @pytest.mark.asyncio
       async def test_sin_checkpoint_reanudar_retorna_none(self):
           """Sin checkpoints previos, reanudar retorna None."""
           flash = FlashMemoryMock()
           resultado = await GrafoCheckpoint.reanudar("grafo_inexistente", flash)
           assert resultado is None


   # ═══════════════════════════════════════════════════════════════════════════
   # Escenario 2: Cache Hit en Segundo Run
   # ═══════════════════════════════════════════════════════════════════════════

   class TestCacheHitSegundoRun:

       @pytest.mark.asyncio
       async def test_segundo_run_usa_cache(self):
           """
           El segundo run con el mismo input debe usar el cache sin re-ejecutar el nodo.
           """
           contador_ejecuciones = {"n": 0}
           flash = FlashMemoryMock()

           @nodo(id="nodo_lento_cache")
           async def nodo_costoso_real(estado: EstadoGrafo) -> EstadoGrafo:
               contador_ejecuciones["n"] += 1
               estado.salida["resultado"] = f"calculado_{contador_ejecuciones['n']}"
               return estado

           nodo_con_cache = NodoCache(nodo_costoso_real, flash)

           entrada = {"texto": "consulta importante", "parametro": 42}

           # Primer run — cache miss
           estado_1 = EstadoGrafo(entrada=entrada)
           resultado_1 = await nodo_con_cache.ejecutar(estado_1)
           assert resultado_1.contexto["cache_hit"] is False
           assert resultado_1.salida["resultado"] == "calculado_1"
           assert contador_ejecuciones["n"] == 1

           # Segundo run — mismo input → cache hit
           estado_2 = EstadoGrafo(entrada=entrada)
           resultado_2 = await nodo_con_cache.ejecutar(estado_2)
           assert resultado_2.contexto["cache_hit"] is True
           # Resultado del cache = el mismo que la primera ejecución
           assert resultado_2.salida["resultado"] == "calculado_1"
           # El nodo NO se re-ejecutó
           assert contador_ejecuciones["n"] == 1

       @pytest.mark.asyncio
       async def test_diferente_input_no_usa_cache(self):
           """Input diferente → no usa cache → ejecuta el nodo."""
           contador = {"n": 0}
           flash = FlashMemoryMock()

           @nodo(id="nodo_cache_diferente")
           async def nodo_real(estado: EstadoGrafo) -> EstadoGrafo:
               contador["n"] += 1
               estado.salida["r"] = contador["n"]
               return estado

           nc = NodoCache(nodo_real, flash)

           e1 = EstadoGrafo(entrada={"q": "consulta_A"})
           await nc.ejecutar(e1)
           assert contador["n"] == 1

           e2 = EstadoGrafo(entrada={"q": "consulta_B"})  # diferente
           await nc.ejecutar(e2)
           assert contador["n"] == 2  # re-ejecutó

       @pytest.mark.asyncio
       async def test_cache_integrado_en_grafo(self):
           """NodoCache puede usarse dentro de un YeyoGrafo normalmente."""
           flash = FlashMemoryMock()
           contador = {"n": 0}

           @nodo(id="nodo_base_integ")
           async def nodo_base(estado: EstadoGrafo) -> EstadoGrafo:
               contador["n"] += 1
               estado.salida["procesado"] = True
               return estado

           nodo_cacheado = NodoCache(nodo_base, flash)

           g = (YeyoGrafo("grafo_con_cache")
                .agregar_nodo(nodo_cacheado)
                .inicio("nodo_base_integ")
                .fin("nodo_base_integ"))

           # Primer run
           r1 = await g.ejecutar({"data": "test_cache_grafo"})
           assert r1.exito is True
           assert contador["n"] == 1

           # Segundo run — mismo input
           r2 = await g.ejecutar({"data": "test_cache_grafo"})
           assert r2.exito is True
           # El nodo no se re-ejecutó gracias al cache
           assert contador["n"] == 1


   # ═══════════════════════════════════════════════════════════════════════════
   # Escenario 3: Grafo Generado por IA
   # ═══════════════════════════════════════════════════════════════════════════

   class TestGrafoGeneradoIA:

       @pytest.mark.asyncio
       async def test_grafo_generado_simple_ejecuta(self):
           """
           Genera un grafo simple desde descripción de texto y lo ejecuta.
           """
           codigo_grafo = '''
async def fn_suma(estado):
    a = estado.entrada.get("a", 0)
    b = estado.entrada.get("b", 0)
    estado.salida["suma"] = a + b
    return estado

nodo_suma = NodoFuncion(id="calcular_suma", fn=fn_suma, timeout=10.0)
grafo = (
    YeyoGrafo("grafo_suma_ia", "Suma dos números")
    .agregar_nodo(nodo_suma)
    .inicio("calcular_suma")
    .fin("calcular_suma")
)
'''
           ollama = mock_ollama_genera(codigo_grafo)
           flash = FlashMemoryMock()
           gen = GeneradorGrafos(ollama, flash_memory=flash)

           grafo = await gen.generar(
               descripcion="Un grafo que suma dos números a y b",
               usuario_id="test_user",
           )

           assert isinstance(grafo, YeyoGrafo)
           assert grafo.id == "grafo_suma_ia"

           # Ejecutar el grafo generado
           resultado = await grafo.ejecutar({"a": 10, "b": 32})
           assert resultado.exito is True
           assert resultado.estado_final.salida["suma"] == 42

       @pytest.mark.asyncio
       async def test_grafo_generado_se_guarda_en_flash(self):
           """El grafo generado se persiste en Flash Memory."""
           codigo_grafo = '''
async def fn_hello(estado):
    estado.salida["msg"] = "hola"
    return estado

nodo_h = NodoFuncion(id="hello", fn=fn_hello, timeout=5.0)
grafo = YeyoGrafo("grafo_hello", "Dice hola").agregar_nodo(nodo_h).inicio("hello").fin("hello")
'''
           ollama = mock_ollama_genera(codigo_grafo)
           flash = FlashMemoryMock()
           gen = GeneradorGrafos(ollama, flash_memory=flash)

           await gen.generar("Un grafo que dice hola", usuario_id="user_a")

           # Verificar que se guardó en Flash Memory
           guardados = await flash.buscar(query="", tipo="grafo_generado")
           assert len(guardados) >= 1

       @pytest.mark.asyncio
       async def test_listar_grafos_generados_por_usuario(self):
           """listar_generados retorna los grafos del usuario correcto."""
           codigo_grafo = '''
nodo_t = NodoFuncion(id="n", fn=lambda e: e, timeout=5.0)
grafo = YeyoGrafo("g_lista", "test").agregar_nodo(nodo_t).inicio("n").fin("n")
'''
           ollama = mock_ollama_genera(codigo_grafo)
           flash = FlashMemoryMock()
           gen = GeneradorGrafos(ollama, flash_memory=flash)

           await gen.generar("Primer grafo", usuario_id="usuario_lista")
           await gen.generar("Segundo grafo", usuario_id="usuario_lista")

           lista = await gen.listar_generados("usuario_lista")
           assert isinstance(lista, list)


   # ═══════════════════════════════════════════════════════════════════════════
   # Escenario 4: Validación de Código Peligroso Bloqueado
   # ═══════════════════════════════════════════════════════════════════════════

   class TestValidacionCodigoPeligroso:

       def test_import_os_bloqueado_con_ast(self):
           """GrafoValidador con AST bloquea import os correctamente."""
           v = GrafoValidador()
           result = v.validar("import os\ngrafo = YeyoGrafo('x', 'y')")
           assert result.is_valid is False
           assert len(result.errores) > 0

       def test_eval_bloqueado_con_ast(self):
           """eval() bloqueado por análisis AST."""
           v = GrafoValidador()
           result = v.validar("x = eval('1+1')\ngrafo = YeyoGrafo('g', 'd')")
           assert result.is_valid is False

       def test_codigo_valido_con_nodo_funcion(self):
           """Código válido que usa NodoFuncion pasa la validación."""
           codigo = """
async def fn(estado):
    estado.salida["ok"] = True
    return estado

n = NodoFuncion(id="nodo", fn=fn, timeout=30.0)
grafo = YeyoGrafo("g", "d").agregar_nodo(n).inicio("nodo").fin("nodo")
"""
           v = GrafoValidador()
           result = v.validar(codigo)
           assert result.is_valid is True

       def test_multiples_errores_en_un_codigo(self):
           """Código con múltiples problemas reporta todos los errores."""
           codigo = "import os\nimport sys\nx = eval('1')\ngrafo = YeyoGrafo('g','d')"
           v = GrafoValidador()
           result = v.validar(codigo)
           assert result.is_valid is False
           assert len(result.errores) >= 3  # os + sys + eval

       @pytest.mark.asyncio
       async def test_generador_rechaza_codigo_peligroso_via_validador(self):
           """
           GeneradorGrafos rechaza código peligroso usando GrafoValidador con AST.
           """
           codigo_malo = "import os\nos.system('rm -rf /')\ngrafo = YeyoGrafo('hack', 'hack')"
           ollama = mock_ollama_genera(codigo_malo)
           gen = GeneradorGrafos(ollama)
           with pytest.raises(GeneradorGrafosError):
               await gen.generar("Grafo malicioso para tests")

       def test_nodo_fuera_de_catalogo_bloqueado(self):
           """Nodo que no está en el catálogo es rechazado."""
           v = GrafoValidador(nodos_permitidos=["nodo_chat", "nodo_log"])
           codigo = (
               'n = catalogo.obtener("nodo_secreto_peligroso")\n'
               'grafo = YeyoGrafo("g", "d")'
           )
           result = v.validar(codigo)
           assert result.is_valid is False
           assert any("nodo_secreto_peligroso" in e for e in result.errores)

       def test_nodo_en_catalogo_aceptado(self):
           """Nodo que está en el catálogo es aceptado."""
           v = GrafoValidador(nodos_permitidos=["nodo_chat", "nodo_log"])
           codigo = (
               'n = catalogo.obtener("nodo_chat")\n'
               'grafo = YeyoGrafo("g", "d")'
           )
           result = v.validar(codigo)
           assert result.is_valid is True


   # ═══════════════════════════════════════════════════════════════════════════
   # Escenario 5: Integración total — checkpoint + cache + generador
   # ═══════════════════════════════════════════════════════════════════════════

   class TestIntegracionTotal:

       @pytest.mark.asyncio
       async def test_flujo_completo_con_todas_las_features(self):
           """
           Flujo completo que usa checkpoint, cache y validación en un mismo test.
           """
           flash = FlashMemoryMock()

           # 1. Crear grafo con nodo cacheado
           ejecutado = {"n": 0}

           @nodo(id="nodo_central")
           async def nodo_central(estado: EstadoGrafo) -> EstadoGrafo:
               ejecutado["n"] += 1
               estado.salida["procesado"] = ejecutado["n"]
               return estado

           nodo_con_cache = NodoCache(nodo_central, flash)
           cp = GrafoCheckpoint(flash, grafo_id="grafo_total")

           g = (YeyoGrafo("grafo_total")
                .agregar_nodo(nodo_con_cache)
                .inicio("nodo_central")
                .fin("nodo_central"))

           # 2. Primer run: cache miss + checkpoint
           r1 = await g.ejecutar({"input": "mismo_input"}, on_evento=cp.on_evento_checkpoint)
           assert r1.exito is True
           assert ejecutado["n"] == 1

           # Guardar estado completo
           await cp.guardar_estado(r1.estado_final)

           # 3. Segundo run: mismo input → cache hit
           r2 = await g.ejecutar({"input": "mismo_input"})
           assert r2.exito is True
           assert ejecutado["n"] == 1  # no re-ejecutó gracias al cache

           # 4. Verificar que Flash Memory tiene datos (checkpoint + cache)
           todos = await flash.buscar(query="")
           assert len(todos) >= 2  # al menos checkpoint + resultado_nodo

           # 5. Reanudar desde checkpoint
           estado_recuperado = await GrafoCheckpoint.reanudar("grafo_total", flash)
           assert estado_recuperado is not None

2. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/integration/test_grafos_avanzados.py -v

VERIFICAR:
- [ ] Escenario 1: checkpoint guarda y reanuda EstadoGrafo correctamente
- [ ] Escenario 2: segundo run con mismo input usa cache (nodo no re-ejecuta)
- [ ] Escenario 3: grafo generado por IA es ejecutable
- [ ] Escenario 4: código peligroso bloqueado por GrafoValidador + GeneradorGrafos
- [ ] Escenario 5: integración total (cache + checkpoint) funciona
- [ ] TODOS los tests pasan (sin infraestructura real, solo mocks)

SI FALLA:
- FlashMemoryMock no persiste entre llamadas: verificar que usa la misma instancia en todos los tests del escenario
- NodoCache no encuentra el cache del primer run: verificar que el hash se genera de la misma forma en ambos runs
- GeneradorGrafos rechaza código válido: verificar que _validar_codigo_completo solo rechaza código peligroso
- Sub-test de integración falla: ejecutar el test específico con pytest -k "TestIntegracionTotal" para aislar

NO HACER:
- No conectar con infraestructura real (Postgres, Ollama) en este test
- No agregar tests de Capa 4 aquí (ya están en test_capa4_orquestador_integration.py)
- No implementar cleanup automático de Flash Memory en tests

GATE: Las 4 features avanzadas (checkpoint + reanudación, cache hit, grafo generado por IA, validación de código peligroso) funcionan correctamente de forma integrada con FlashMemoryMock. Todos los tests pasan.
```
