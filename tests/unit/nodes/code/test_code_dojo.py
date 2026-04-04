"""
Tests del Code Dojo — 12 agentes especializados.
Todos usan mocks para no depender de Ollama corriendo.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.nodes.code.dojo import (
    AgenteBase,
    AgenteCritico,
    CodeDojo,
    ResultadoDojo,
    SandboxEjecucion,
    AGENTES,
)
from src.ia.interfaces import IAProvider, IAResponse


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_ia_mock(content: str = "resultado mock") -> AsyncMock:
    ia = AsyncMock(spec=IAProvider)
    ia.chat = AsyncMock(return_value=IAResponse(
        content=content,
        model="mock",
        tokens_used=10,
        latency_ms=50.0,
    ))
    return ia


# ─── Tests de definición de agentes ──────────────────────────────────────────

class TestDefinicionAgentes:
    def test_hay_12_agentes(self):
        assert len(AGENTES) == 12

    def test_todos_tienen_system_prompt(self):
        for nombre, config in AGENTES.items():
            assert "system_prompt" in config, f"{nombre} sin system_prompt"
            assert len(config["system_prompt"]) > 20, f"{nombre} system_prompt muy corto"

    def test_todos_tienen_especialidad(self):
        for nombre, config in AGENTES.items():
            assert "especialidad" in config, f"{nombre} sin especialidad"

    def test_agentes_esperados_presentes(self):
        esperados = {
            "arquitecto", "backend", "frontend", "mobile",
            "base_datos", "seguridad", "ia_ml", "performance",
            "testing", "devops", "datos", "sistemas"
        }
        assert set(AGENTES.keys()) == esperados


# ─── Tests de AgenteBase ─────────────────────────────────────────────────────

class TestAgenteBase:
    def test_agente_valido_crea_sin_error(self):
        ia = make_ia_mock()
        agente = AgenteBase(ia, "backend")
        assert agente.id == "backend"
        assert agente.especialidad == "lógica de servidor"

    def test_agente_invalido_lanza_error(self):
        ia = make_ia_mock()
        with pytest.raises(ValueError, match="Agente desconocido"):
            AgenteBase(ia, "inexistente")

    @pytest.mark.asyncio
    async def test_ejecutar_llama_ia_chat(self):
        ia = make_ia_mock("def hello(): return 'world'")
        agente = AgenteBase(ia, "backend")
        resultado = await agente.ejecutar("escribe una función hello world")
        assert "hello" in resultado
        ia.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_ejecutar_usa_system_prompt_del_agente(self):
        ia = make_ia_mock("código")
        agente = AgenteBase(ia, "seguridad")
        await agente.ejecutar("revisa este código")
        call_args = ia.chat.call_args[0][0]  # messages
        system_msg = call_args[0]
        assert system_msg.role == "system"
        assert "OWASP" in system_msg.content

    @pytest.mark.asyncio
    async def test_ejecutar_maneja_error_ia(self):
        ia = AsyncMock(spec=IAProvider)
        ia.chat = AsyncMock(side_effect=Exception("Ollama down"))
        agente = AgenteBase(ia, "backend")
        resultado = await agente.ejecutar("prueba")
        assert resultado == ""  # Falla silenciosamente, retorna string vacío


# ─── Tests de AgenteCritico ───────────────────────────────────────────────────

class TestAgenteCritico:
    @pytest.mark.asyncio
    async def test_score_alto_pasa(self):
        ia = make_ia_mock('{"score": 9.0, "razon": "excelente código", "pasa": true}')
        critico = AgenteCritico(ia)
        score, razon, pasa = await critico.evaluar("def foo(): return 42", "función simple")
        assert score == 9.0
        assert pasa is True
        assert "excelente" in razon

    @pytest.mark.asyncio
    async def test_score_bajo_no_pasa(self):
        ia = make_ia_mock('{"score": 5.5, "razon": "falta manejo de errores", "pasa": false}')
        critico = AgenteCritico(ia)
        score, razon, pasa = await critico.evaluar("def foo(): pass", "función")
        assert score == 5.5
        assert pasa is False
        assert "errores" in razon

    @pytest.mark.asyncio
    async def test_umbral_exacto_8_pasa(self):
        ia = make_ia_mock('{"score": 8.0, "razon": "cumple mínimo", "pasa": true}')
        critico = AgenteCritico(ia)
        score, razon, pasa = await critico.evaluar("código", "tarea")
        assert pasa is True

    @pytest.mark.asyncio
    async def test_respuesta_malformada_retorna_cero(self):
        ia = make_ia_mock("no soy json válido")
        critico = AgenteCritico(ia)
        score, razon, pasa = await critico.evaluar("código", "tarea")
        assert score == 0.0
        assert pasa is False

    @pytest.mark.asyncio
    async def test_json_con_texto_extra_funciona(self):
        # El crítico puede responder con texto antes/después del JSON
        ia = make_ia_mock('Aquí mi evaluación: {"score": 8.5, "razon": "buen código", "pasa": true} Fin.')
        critico = AgenteCritico(ia)
        score, _, pasa = await critico.evaluar("código", "tarea")
        assert score == 8.5
        assert pasa is True


# ─── Tests de SandboxEjecucion ────────────────────────────────────────────────

class TestSandboxEjecucion:
    def test_codigo_valido_pasa(self):
        tests = """
def test_suma():
    assert 1 + 1 == 2

def test_string():
    assert "hola".upper() == "HOLA"
"""
        exito, output = SandboxEjecucion.ejecutar_python(tests)
        assert exito is True
        assert "passed" in output.lower() or "2 passed" in output

    def test_test_que_falla_retorna_false(self):
        tests = """
def test_falla_intencionalmente():
    assert 1 == 2, "esto siempre falla"
"""
        exito, output = SandboxEjecucion.ejecutar_python(tests)
        assert exito is False

    def test_sintaxis_invalida_retorna_false(self):
        tests = "def test_roto( esto no es código válido !!!"
        exito, output = SandboxEjecucion.ejecutar_python(tests)
        assert exito is False

    def test_codigo_fuente_se_importa(self):
        fuente = """
def sumar(a, b):
    return a + b
"""
        tests = """
from source import sumar

def test_sumar():
    assert sumar(2, 3) == 5
"""
        exito, output = SandboxEjecucion.ejecutar_python(tests, fuente)
        assert exito is True


# ─── Tests del pipeline CodeDojo ─────────────────────────────────────────────

class TestCodeDojoPipeline:
    def _make_dojo_con_respuestas(
        self,
        codigo_backend: str = "def foo(): return 42",
        score_critico: float = 9.0,
        tests: str = "def test_foo(): assert foo() == 42",
        score_perf: float = 9.0,
        score_seg: float = 9.0,
    ) -> CodeDojo:
        """Crea un CodeDojo con respuestas controladas."""
        respuestas = [
            # arquitecto
            "Plan: función simple de una línea",
            # backend
            codigo_backend,
            # critico
            f'{{"score": {score_critico}, "razon": "ok", "pasa": {str(score_critico >= 8.0).lower()}}}',
            # testing
            tests,
            # performance
            f'{{"score": {score_perf}, "issues": []}}',
            # seguridad
            f'{{"score": {score_seg}, "vulnerabilidades": [], "critico": false}}',
        ]

        call_count = 0

        async def chat_mock(messages, temperature=0.7):
            nonlocal call_count
            idx = min(call_count, len(respuestas) - 1)
            call_count += 1
            return IAResponse(
                content=respuestas[idx],
                model="mock",
                tokens_used=10,
                latency_ms=50.0,
            )

        ia = AsyncMock(spec=IAProvider)
        ia.chat = chat_mock
        return CodeDojo(ia)

    @pytest.mark.asyncio
    async def test_pipeline_exitoso_retorna_codigo(self):
        dojo = self._make_dojo_con_respuestas(
            codigo_backend="def foo(): return 42",
            score_critico=9.0,
        )
        resultado = await dojo.ejecutar("escribe una función foo que retorne 42")
        assert resultado.exito is True
        assert "foo" in resultado.codigo_final
        assert resultado.score_critico == 9.0

    @pytest.mark.asyncio
    async def test_critico_bajo_reintenta(self):
        """Si el Crítico rechaza, el Backend reintenta."""
        intentos = []
        call_count = 0

        respuestas = [
            "Plan arquitectura",           # arquitecto
            "código malo",                  # backend intento 1
            '{"score": 4.0, "razon": "falta error handling", "pasa": false}',  # critico rechaza
            "código mejorado con try/except",  # backend intento 2
            '{"score": 9.0, "razon": "perfecto", "pasa": true}',  # critico aprueba
            "def test_ok(): pass",          # testing
            '{"score": 9.0, "issues": []}', # performance
            '{"score": 9.0, "vulnerabilidades": [], "critico": false}',  # seguridad
        ]

        async def chat_mock(messages, temperature=0.7):
            nonlocal call_count
            idx = min(call_count, len(respuestas) - 1)
            call_count += 1
            return IAResponse(content=respuestas[idx], model="mock", tokens_used=5, latency_ms=10.0)

        ia = AsyncMock(spec=IAProvider)
        ia.chat = chat_mock
        dojo = CodeDojo(ia)

        resultado = await dojo.ejecutar("escribe código con manejo de errores")
        assert resultado.exito is True
        assert resultado.intentos_backend == 2

    @pytest.mark.asyncio
    async def test_3_rechazos_consecutivos_falla(self):
        """Después de 3 rechazos del Crítico, el pipeline falla."""
        call_count = 0
        respuestas = [
            "Plan",                                                              # arquitecto
            "código malo 1",                                                    # backend 1
            '{"score": 3.0, "razon": "muy mal", "pasa": false}',              # critico 1
            "código malo 2",                                                    # backend 2
            '{"score": 4.0, "razon": "sigue mal", "pasa": false}',            # critico 2
            "código malo 3",                                                    # backend 3
            '{"score": 5.0, "razon": "todavía mal", "pasa": false}',          # critico 3
        ]

        async def chat_mock(messages, temperature=0.7):
            nonlocal call_count
            idx = min(call_count, len(respuestas) - 1)
            call_count += 1
            return IAResponse(content=respuestas[idx], model="mock", tokens_used=5, latency_ms=10.0)

        ia = AsyncMock(spec=IAProvider)
        ia.chat = chat_mock
        dojo = CodeDojo(ia)

        resultado = await dojo.ejecutar("tarea imposible")
        assert resultado.exito is False
        assert resultado.intentos_backend == 3
        assert "Crítico" in resultado.razon_falla

    @pytest.mark.asyncio
    async def test_vulnerabilidad_critica_bloquea(self):
        """Si hay vulnerabilidad crítica de seguridad, el pipeline falla."""
        call_count = 0
        respuestas = [
            "Plan",
            "código con sql injection",
            '{"score": 9.0, "razon": "ok", "pasa": true}',
            "tests",
            '{"score": 9.0, "issues": []}',
            '{"score": 2.0, "vulnerabilidades": ["SQL injection detectada"], "critico": true}',
        ]

        async def chat_mock(messages, temperature=0.7):
            nonlocal call_count
            idx = min(call_count, len(respuestas) - 1)
            call_count += 1
            return IAResponse(content=respuestas[idx], model="mock", tokens_used=5, latency_ms=10.0)

        ia = AsyncMock(spec=IAProvider)
        ia.chat = chat_mock
        dojo = CodeDojo(ia)

        resultado = await dojo.ejecutar("query a la base de datos")
        assert resultado.exito is False
        assert "crítica" in resultado.razon_falla.lower() or "SQL" in resultado.razon_falla

    @pytest.mark.asyncio
    async def test_resumen_formato_correcto(self):
        dojo = self._make_dojo_con_respuestas()
        resultado = await dojo.ejecutar("tarea simple")
        resumen = resultado.resumen()
        assert "✅ APROBADO" in resumen or "❌ RECHAZADO" in resumen
        assert "Crítico:" in resumen
        assert "/10" in resumen


# ─── Tests de ResultadoDojo ───────────────────────────────────────────────────

class TestResultadoDojo:
    def test_resumen_aprobado(self):
        r = ResultadoDojo(
            codigo_final="código",
            lenguaje="python",
            score_critico=9.0,
            score_seguridad=10.0,
            score_performance=8.5,
            tests_pasaron=True,
            intentos_backend=1,
            exito=True,
        )
        assert "✅ APROBADO" in r.resumen()
        assert "9.0/10" in r.resumen()

    def test_resumen_rechazado(self):
        r = ResultadoDojo(
            codigo_final="",
            lenguaje="python",
            exito=False,
            razon_falla="No pasó el Crítico",
        )
        assert "❌ RECHAZADO" in r.resumen()
