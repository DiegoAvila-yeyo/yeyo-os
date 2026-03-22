"""
Tests de integración de features avanzadas de grafos — Micro-fase 5.26

Escenarios:
1. Checkpoint + reanudación de grafo interrumpido
2. Cache hit evita re-ejecución en segundo run
3. Grafo generado por IA desde descripción simple
4. Validación de código peligroso bloqueado correctamente
5. Integración total: checkpoint + cache + generador
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

        resultado = await g.ejecutar({}, on_evento=cp.on_evento_checkpoint)
        assert resultado.exito is True

        await cp.guardar_estado(resultado.estado_final)

        assert flash._contador > 0

        estado_recuperado = await GrafoCheckpoint.reanudar("grafo_reanudable", flash)
        assert estado_recuperado is not None
        assert estado_recuperado.salida["datos_configurados"] is True
        assert estado_recuperado.contexto["usuarios"] == ["u1", "u2", "u3"]

    @pytest.mark.asyncio
    async def test_checkpoint_guarda_por_nodo_completado(self):
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

        checkpoints = await flash.buscar(query="", tipo=TIPO_CHECKPOINT)
        assert len(checkpoints) >= 3

    @pytest.mark.asyncio
    async def test_sin_checkpoint_reanudar_retorna_none(self):
        flash = FlashMemoryMock()
        resultado = await GrafoCheckpoint.reanudar("grafo_inexistente", flash)
        assert resultado is None


# ═══════════════════════════════════════════════════════════════════════════
# Escenario 2: Cache Hit en Segundo Run
# ═══════════════════════════════════════════════════════════════════════════

class TestCacheHitSegundoRun:

    @pytest.mark.asyncio
    async def test_segundo_run_usa_cache(self):
        contador_ejecuciones = {"n": 0}
        flash = FlashMemoryMock()

        @nodo(id="nodo_lento_cache")
        async def nodo_costoso_real(estado: EstadoGrafo) -> EstadoGrafo:
            contador_ejecuciones["n"] += 1
            estado.salida["resultado"] = f"calculado_{contador_ejecuciones['n']}"
            return estado

        nodo_con_cache = NodoCache(nodo_costoso_real, flash)

        entrada = {"texto": "consulta importante", "parametro": 42}

        estado_1 = EstadoGrafo(entrada=entrada)
        resultado_1 = await nodo_con_cache.ejecutar(estado_1)
        assert resultado_1.contexto["cache_hit"] is False
        assert resultado_1.salida["resultado"] == "calculado_1"
        assert contador_ejecuciones["n"] == 1

        estado_2 = EstadoGrafo(entrada=entrada)
        resultado_2 = await nodo_con_cache.ejecutar(estado_2)
        assert resultado_2.contexto["cache_hit"] is True
        assert resultado_2.salida["resultado"] == "calculado_1"
        assert contador_ejecuciones["n"] == 1

    @pytest.mark.asyncio
    async def test_diferente_input_no_usa_cache(self):
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

        e2 = EstadoGrafo(entrada={"q": "consulta_B"})
        await nc.ejecutar(e2)
        assert contador["n"] == 2

    @pytest.mark.asyncio
    async def test_cache_integrado_en_grafo(self):
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

        r1 = await g.ejecutar({"data": "test_cache_grafo"})
        assert r1.exito is True
        assert contador["n"] == 1

        r2 = await g.ejecutar({"data": "test_cache_grafo"})
        assert r2.exito is True
        assert contador["n"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Escenario 3: Grafo Generado por IA
# ═══════════════════════════════════════════════════════════════════════════

class TestGrafoGeneradoIA:

    @pytest.mark.asyncio
    async def test_grafo_generado_simple_ejecuta(self):
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

        resultado = await grafo.ejecutar({"a": 10, "b": 32})
        assert resultado.exito is True
        assert resultado.estado_final.salida["suma"] == 42

    @pytest.mark.asyncio
    async def test_grafo_generado_se_guarda_en_flash(self):
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

        guardados = await flash.buscar(query="", tipo="grafo_generado")
        assert len(guardados) >= 1

    @pytest.mark.asyncio
    async def test_listar_grafos_generados_por_usuario(self):
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
        v = GrafoValidador()
        result = v.validar("import os\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False
        assert len(result.errores) > 0

    def test_eval_bloqueado_con_ast(self):
        v = GrafoValidador()
        result = v.validar("x = eval('1+1')\ngrafo = YeyoGrafo('g', 'd')")
        assert result.is_valid is False

    def test_codigo_valido_con_nodo_funcion(self):
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
        codigo = "import os\nimport sys\nx = eval('1')\ngrafo = YeyoGrafo('g','d')"
        v = GrafoValidador()
        result = v.validar(codigo)
        assert result.is_valid is False
        assert len(result.errores) >= 3

    @pytest.mark.asyncio
    async def test_generador_rechaza_codigo_peligroso_via_validador(self):
        codigo_malo = "import os\nos.system('rm -rf /')\ngrafo = YeyoGrafo('hack', 'hack')"
        ollama = mock_ollama_genera(codigo_malo)
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError):
            await gen.generar("Grafo malicioso para tests")

    def test_nodo_fuera_de_catalogo_bloqueado(self):
        v = GrafoValidador(nodos_permitidos=["nodo_chat", "nodo_log"])
        codigo = (
            'n = catalogo.obtener("nodo_secreto_peligroso")\n'
            'grafo = YeyoGrafo("g", "d")'
        )
        result = v.validar(codigo)
        assert result.is_valid is False
        assert any("nodo_secreto_peligroso" in e for e in result.errores)

    def test_nodo_en_catalogo_aceptado(self):
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
        flash = FlashMemoryMock()

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

        r1 = await g.ejecutar({"input": "mismo_input"}, on_evento=cp.on_evento_checkpoint)
        assert r1.exito is True
        assert ejecutado["n"] == 1

        await cp.guardar_estado(r1.estado_final)

        r2 = await g.ejecutar({"input": "mismo_input"})
        assert r2.exito is True
        assert ejecutado["n"] == 1

        todos = await flash.buscar(query="")
        assert len(todos) >= 2

        estado_recuperado = await GrafoCheckpoint.reanudar("grafo_total", flash)
        assert estado_recuperado is not None
