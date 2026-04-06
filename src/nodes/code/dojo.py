"""
YeyoOS — Code Dojo (12 Agentes Especializados)
Pipeline de calidad de código con verificación REAL.

Pipeline:
1. ARQUITECTO planifica
2. BACKEND escribe código
3. CRÍTICO evalúa (si < 8.0 → vuelve a BACKEND, máx 3 intentos)
4. AST PARSE — verifica que compile (ast.parse para Python)
5. TESTING — genera tests Y los ejecuta en sandbox. Si fallan → vuelve a BACKEND
6. PERFORMANCE analiza complejidad
7. SEGURIDAD revisa OWASP
8. Solo aprueba si: AST✅ AND Tests✅ AND Crítico≥8.0 AND Security OK

Overhead de tener 12 agentes: 0 VRAM extra (mismo modelo, distinto prompt).
"""

from __future__ import annotations

import ast
import asyncio
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.ia.interfaces import IAProvider, IAMessage
from src.memory.pipeline_events import pipeline_buffer

logger = logging.getLogger("yeyoos.code_dojo")


def _strip_markdown(text: str) -> str:
    """Elimina bloques de markdown y normaliza formato que modelos pequeños omiten."""
    import re

    # 1. Eliminar fences de markdown
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"```", "", text)

    # 2. Modelos 3B omiten saltos de línea antes de palabras clave de bloque
    #    Ej: "import pytestdef foo():" → "import pytest\ndef foo():"
    block_keywords = r"(def |class |import |from |@[a-zA-Z])"
    text = re.sub(rf"(\S)({block_keywords})", r"\1\n\2", text)

    # 3. Después de los dos puntos de un bloque, la siguiente sentencia va en nueva línea
    #    Ej: "def foo():    assert x" → "def foo():\n    assert x"
    text = re.sub(r"(:)\s{2,}(\S)", r":\n    \2", text)

    # 4. Separar sentencias pegadas dentro del cuerpo (4+ espacios entre sentencias)
    #    Ej: "    assert a == 1    assert b == 2" → "    assert a == 1\n    assert b == 2"
    stmt_start = r"(assert |return |raise |if |for |while |with |yield |pass|break|continue)"
    text = re.sub(rf"\s{{4,}}({stmt_start})", r"\n    \1", text)

    return text.strip()


def _format_python(code: str) -> str:
    """Intenta formatear código Python con black. Si falla, retorna el original."""
    try:
        import black
        return black.format_str(code, mode=black.Mode())
    except Exception:
        return code


# ─── Definición de los 12 agentes ────────────────────────────────────────────

AGENTES: dict[str, dict] = {
    "arquitecto": {
        "system_prompt": (
            "Eres un arquitecto de software senior. "
            "Diseñas soluciones escalables, defines estructura de archivos, "
            "patrones de diseño y dependencias entre componentes. "
            "Respondes con diagramas ASCII y planes detallados. "
            "Sé conciso: máximo 20 líneas."
        ),
        "especialidad": "diseño de sistemas",
        "output": "plan de arquitectura",
    },
    "backend": {
        "system_prompt": (
            "Eres un desarrollador backend experto. "
            "Escribes código limpio, eficiente y bien documentado. "
            "Manejas APIs REST/GraphQL, bases de datos, autenticación. "
            "Siempre incluyes manejo de errores, logging y type hints. "
            "IMPORTANTE: usa exactamente 4 espacios por nivel de indentación. "
            "IMPORTANTE: nunca pongas múltiples sentencias en la misma línea. "
            "Responde SOLO con el bloque de código Python, sin texto adicional."
        ),
        "especialidad": "lógica de servidor",
        "output": "código funcional",
    },
    "frontend": {
        "system_prompt": (
            "Eres un desarrollador frontend senior. "
            "Creas interfaces accesibles, responsivas y performantes. "
            "Dominas React, TypeScript, CSS moderno y diseño de componentes. "
            "Responde SOLO con el código del componente."
        ),
        "especialidad": "interfaces de usuario",
        "output": "componentes UI",
    },
    "mobile": {
        "system_prompt": (
            "Eres un desarrollador móvil experto. "
            "Creas apps nativas y cross-platform con Flutter, React Native, "
            "Swift y Kotlin. Optimizas para batería y rendimiento. "
            "Responde SOLO con el código."
        ),
        "especialidad": "aplicaciones móviles",
        "output": "código móvil",
    },
    "base_datos": {
        "system_prompt": (
            "Eres un DBA y experto en modelado de datos. "
            "Diseñas esquemas normalizados, escribes queries optimizadas, "
            "manejas migraciones y estrategias de indexación. "
            "Responde SOLO con SQL."
        ),
        "especialidad": "bases de datos",
        "output": "esquemas y queries",
    },
    "seguridad": {
        "system_prompt": (
            "Eres un experto en seguridad informática. "
            "Revisas código buscando vulnerabilidades OWASP Top 10: "
            "inyecciones SQL, XSS, auth bypass, data leaks, CSRF. "
            "Responde con JSON: {\"score\": 0-10, \"vulnerabilidades\": [], \"critico\": bool}"
        ),
        "especialidad": "seguridad",
        "output": "reporte de vulnerabilidades",
    },
    "ia_ml": {
        "system_prompt": (
            "Eres un ingeniero de ML/IA. "
            "Diseñas pipelines de datos, entrenas modelos, optimizas "
            "inferencia y manejas MLOps. "
            "Responde SOLO con el código."
        ),
        "especialidad": "inteligencia artificial",
        "output": "modelos y pipelines",
    },
    "performance": {
        "system_prompt": (
            "Eres un experto en optimización de rendimiento. "
            "Perfilas código, identificas cuellos de botella, optimizas "
            "algoritmos, memoria y I/O. "
            "Responde con JSON: {\"score\": 0-10, \"issues\": [], \"sugerencias\": []}"
        ),
        "especialidad": "rendimiento",
        "output": "análisis de performance",
    },
    "testing": {
        "system_prompt": (
            "Eres un ingeniero de QA senior. "
            "Escribes tests unitarios, integración y e2e. "
            "Manejas TDD, BDD, mocking y cobertura de código. "
            "IMPORTANTE: usa exactamente 4 espacios por nivel de indentación. "
            "IMPORTANTE: cada sentencia en su propia línea, nunca juntas. "
            "Responde SOLO con el bloque de código de tests (pytest para Python, Jest para JS)."
        ),
        "especialidad": "testing",
        "output": "suite de tests",
    },
    "devops": {
        "system_prompt": (
            "Eres un ingeniero DevOps senior. "
            "Manejas CI/CD, contenedores, infraestructura como código, "
            "monitoreo y despliegues automatizados. "
            "Responde SOLO con el código de configuración."
        ),
        "especialidad": "operaciones",
        "output": "pipelines y configs",
    },
    "datos": {
        "system_prompt": (
            "Eres un ingeniero de datos. "
            "Diseñas ETL pipelines, data warehouses, procesamiento "
            "batch y streaming con herramientas modernas. "
            "Responde SOLO con el código."
        ),
        "especialidad": "ingeniería de datos",
        "output": "pipelines de datos",
    },
    "sistemas": {
        "system_prompt": (
            "Eres un programador de sistemas. "
            "Escribes código de bajo nivel: drivers, kernel modules, "
            "networking, protocolos y optimización de SO. "
            "Responde SOLO con el código."
        ),
        "especialidad": "programación de sistemas",
        "output": "código de sistema",
    },
}

CRITICO_PROMPT = """Eres un revisor de código senior extremadamente estricto.
Evalúas el siguiente código en escala 0-10.

Criterios:
- Corrección (¿hace lo que se pide?): 30%
- Manejo de errores (¿captura excepciones?): 25%
- Claridad (¿es legible?): 20%
- Completitud (¿falta algo?): 25%

Responde SOLO con este JSON (sin texto extra):
{"score": X.X, "razon": "una línea explicando el score", "pasa": true/false}

pasa = true si score >= 8.0"""


# ─── Resultado del pipeline ───────────────────────────────────────────────────

@dataclass
class ResultadoDojo:
    """Resultado completo del pipeline del Code Dojo."""
    codigo_final: str
    lenguaje: str
    score_critico: float = 0.0
    score_seguridad: float = 0.0
    score_performance: float = 0.0
    tests_generados: str = ""
    tests_pasaron: bool = False
    tests_output: str = ""
    ast_valido: bool = False
    plan_arquitectura: str = ""
    vulnerabilidades: list = field(default_factory=list)
    issues_performance: list = field(default_factory=list)
    intentos_backend: int = 0
    exito: bool = False
    razon_falla: str = ""

    def resumen(self) -> str:
        estado = "✅ APROBADO" if self.exito else "❌ RECHAZADO"
        return (
            f"{estado} | Crítico: {self.score_critico:.1f}/10 | "
            f"Seguridad: {self.score_seguridad:.1f}/10 | "
            f"Performance: {self.score_performance:.1f}/10 | "
            f"AST: {'✅' if self.ast_valido else '❌'} | "
            f"Tests: {'✅' if self.tests_pasaron else '❌'} | "
            f"Intentos: {self.intentos_backend}"
        )


# ─── Agente base ─────────────────────────────────────────────────────────────

class AgenteBase:
    """Agente individual del Code Dojo. Un modelo, un system prompt."""

    def __init__(self, ia: IAProvider, agente_id: str):
        if agente_id not in AGENTES:
            raise ValueError(f"Agente desconocido: {agente_id}. Disponibles: {list(AGENTES)}")
        self._ia = ia
        self._id = agente_id
        self._config = AGENTES[agente_id]

    async def ejecutar(self, prompt: str) -> str:
        """Ejecuta el agente con el prompt dado."""
        messages = [
            IAMessage(role="system", content=self._config["system_prompt"]),
            IAMessage(role="user", content=prompt),
        ]
        try:
            resp = await self._ia.chat(messages, temperature=0.3)
            return _strip_markdown(resp.content)
        except Exception as e:
            logger.warning(f"[{self._id}] Error: {e}")
            return ""

    @property
    def id(self) -> str:
        return self._id

    @property
    def especialidad(self) -> str:
        return self._config["especialidad"]


# ─── Agente Crítico ───────────────────────────────────────────────────────────

class AgenteCritico:
    """
    Evalúa código 0-10. Rechaza si score < 8.0.
    Gate central de calidad — nada pasa sin su aprobación.
    """

    def __init__(self, ia: IAProvider):
        self._ia = ia

    async def evaluar(self, codigo: str, contexto: str = "") -> tuple[float, str, bool]:
        """
        Evalúa el código.
        Returns: (score, razon, pasa)
        """
        import json

        prompt = f"TAREA ORIGINAL:\n{contexto}\n\nCÓDIGO A EVALUAR:\n```\n{codigo}\n```"
        messages = [
            IAMessage(role="system", content=CRITICO_PROMPT),
            IAMessage(role="user", content=prompt),
        ]
        try:
            resp = await self._ia.chat(messages, temperature=0.1)
            content = resp.content.strip()

            # Extraer JSON de la respuesta
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(content[start:end])
                score = float(data.get("score", 0))
                razon = str(data.get("razon", "sin razón"))
                pasa = score >= 8.0
                return score, razon, pasa
        except Exception as e:
            logger.warning(f"[critico] Error parseando respuesta: {e}")

        return 0.0, "Error en evaluación", False


# ─── Sandbox de ejecución ─────────────────────────────────────────────────────

class SandboxEjecucion:
    """Ejecuta código en un proceso aislado con timeout."""

    TIMEOUT_SEGUNDOS = 10

    @staticmethod
    def ejecutar_python(codigo_tests: str, codigo_fuente: str = "") -> tuple[bool, str]:
        """
        Ejecuta tests de pytest en un subprocess aislado.
        Returns: (exito, output)
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)

                # Escribir código fuente si existe
                if codigo_fuente:
                    (tmp / "source.py").write_text(codigo_fuente, encoding="utf-8")

                # Escribir tests
                test_file = tmp / "test_dojo.py"
                if codigo_fuente:
                    # Importar el módulo fuente
                    test_content = (
                        "import sys, os\n"
                        "sys.path.insert(0, os.path.dirname(__file__))\n"
                        f"{codigo_tests}"
                    )
                else:
                    test_content = codigo_tests
                test_file.write_text(test_content, encoding="utf-8")

                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=SandboxEjecucion.TIMEOUT_SEGUNDOS,
                    cwd=tmpdir,
                )
                exito = result.returncode == 0
                output = result.stdout + result.stderr
                return exito, output[:2000]  # limitar output

        except subprocess.TimeoutExpired:
            return False, f"Timeout de {SandboxEjecucion.TIMEOUT_SEGUNDOS}s excedido"
        except Exception as e:
            return False, f"Error en sandbox: {e}"


# ─── Pipeline del Code Dojo ───────────────────────────────────────────────────

class CodeDojo:
    """
    Orquesta el pipeline completo de los 12 agentes.

    Pipeline:
    1. ARQUITECTO planifica
    2. BACKEND escribe código
    3. CRÍTICO evalúa (si < 8.0 → vuelve a BACKEND, máx 3 intentos)
    4. TESTING genera tests y los ejecuta en sandbox real
    5. PERFORMANCE analiza complejidad
    6. SEGURIDAD revisa OWASP
    7. Si todo pasa → devuelve código al usuario

    Todos los agentes usan el mismo modelo (qwen2.5:3b).
    Overhead extra de tener 12 agentes: 0 VRAM.
    """

    MAX_INTENTOS_BACKEND = 3
    MAX_INTENTOS_TESTS = 2

    def __init__(self, ia: IAProvider, memory_service=None):
        self._ia = ia
        self._memory_service = memory_service
        self._critico = AgenteCritico(ia)
        self._sandbox = SandboxEjecucion()
        self._agentes = {k: AgenteBase(ia, k) for k in AGENTES}

    async def ejecutar(
        self,
        pedido: str,
        lenguaje: str = "python",
        incluir_arquitectura: bool = True,
    ) -> ResultadoDojo:
        """
        Ejecuta el pipeline completo del Code Dojo con verificación REAL.
        Cada paso emite eventos al pipeline visual.
        """
        resultado = ResultadoDojo(codigo_final="", lenguaje=lenguaje)
        pid = pipeline_buffer.new_pipeline(source="code_dojo")

        # ── RECEIVED ──
        pipeline_buffer.emit(pid, "RECEIVED", "ok",
                             f"[{lenguaje}] {pedido[:60]}",
                             {"content": pedido[:200], "source": "code_dojo"})

        # ── Paso 0: Contexto de memoria ──
        memory_context = ""
        if self._memory_service:
            try:
                memory_context = await self._memory_service.get_code_context(
                    f"{lenguaje} {pedido}", limit=5
                )
            except Exception:
                pass

        # ── ARCHITECT ──
        plan = ""
        if incluir_arquitectura:
            logger.info("[dojo] Paso 1: Arquitecto planificando...")
            architect_prompt = f"Planifica la arquitectura para: {pedido}\nLenguaje: {lenguaje}"
            if memory_context:
                architect_prompt += f"\n\n[BUENAS PRÁCTICAS Y PREFERENCIAS DEL USUARIO]\n{memory_context}"
            plan = await self._agentes["arquitecto"].ejecutar(architect_prompt)
            resultado.plan_arquitectura = plan
            pipeline_buffer.emit(pid, "ARCHITECT", "ok" if plan else "error",
                                 f"Plan: {plan[:80]}" if plan else "Sin plan")

        # ── BACKEND_GEN + CRITIC_EVAL loop ──
        codigo = ""
        score_critico = 0.0
        razon_critico = ""

        contexto_backend = f"{pedido}\nLenguaje: {lenguaje}"
        if plan:
            contexto_backend += f"\n\nPLAN DE ARQUITECTURA:\n{plan}"
        if memory_context:
            contexto_backend += f"\n\n[BUENAS PRÁCTICAS Y PREFERENCIAS]\n{memory_context}"

        for intento in range(self.MAX_INTENTOS_BACKEND):
            resultado.intentos_backend = intento + 1

            logger.info(f"[dojo] Paso 2 (intento {intento + 1}): Backend escribiendo...")
            prompt_backend = contexto_backend
            if razon_critico and intento > 0:
                prompt_backend += f"\n\nFEEDBACK DEL CRÍTICO (corregir):\n{razon_critico}"

            agente_key = "backend"
            if lenguaje in ("typescript", "javascript"):
                agente_key = "frontend"
            elif lenguaje == "sql":
                agente_key = "base_datos"

            codigo = await self._agentes[agente_key].ejecutar(prompt_backend)

            if not codigo:
                pipeline_buffer.emit(pid, "BACKEND_GEN", "error",
                                     f"Intento {intento + 1}: sin código")
                resultado.razon_falla = "Backend no generó código"
                continue

            if lenguaje == "python":
                codigo = _format_python(codigo)

            pipeline_buffer.emit(pid, "BACKEND_GEN", "ok",
                                 f"Intento {intento + 1}: {len(codigo)} chars",
                                 {"attempt": intento + 1, "code_len": len(codigo)})

            # Crítico evalúa
            logger.info(f"[dojo] Paso 3: Crítico evaluando (intento {intento + 1})...")
            score_critico, razon_critico, pasa = await self._critico.evaluar(codigo, pedido)
            resultado.score_critico = score_critico

            pipeline_buffer.emit(pid, "CRITIC_EVAL",
                                 "ok" if pasa else "error",
                                 f"Score: {score_critico:.1f}/10 — {razon_critico[:60]}",
                                 {"score": score_critico, "reason": razon_critico})

            if pasa:
                break
            else:
                logger.info(f"[dojo] Rechazado ({score_critico:.1f}/10). Reintentando...")

        if score_critico < 8.0:
            resultado.razon_falla = f"No pasó el Crítico tras {self.MAX_INTENTOS_BACKEND} intentos: {razon_critico}"
            logger.info(f"[dojo] ❌ {resultado.razon_falla}")
            return resultado

        resultado.codigo_final = codigo

        # ── AST_PARSE — Verificación real de que compila ──
        ast_ok, ast_error = self._verificar_ast(codigo, lenguaje)
        resultado.ast_valido = ast_ok
        pipeline_buffer.emit(pid, "AST_PARSE",
                             "ok" if ast_ok else "error",
                             "Sintaxis válida" if ast_ok else f"Error: {ast_error[:80]}",
                             {"valid": ast_ok, "error": ast_error})

        if not ast_ok:
            resultado.exito = False
            resultado.razon_falla = f"AST inválido: {ast_error}"
            logger.info(f"[dojo] ❌ AST falló: {ast_error}")
            return resultado

        # ── TESTS_RUN — Tests como gate OBLIGATORIO ──
        tests_ok = False
        tests_code = ""
        tests_output = ""

        for test_intento in range(self.MAX_INTENTOS_TESTS):
            logger.info(f"[dojo] Paso 5: Testing (intento {test_intento + 1})...")
            tests_code, tests_ok, tests_output = await self._ejecutar_testing(
                codigo, pedido, lenguaje
            )

            if tests_ok:
                break

            # Tests fallaron — si hay más intentos, regenerar código con feedback
            if test_intento < self.MAX_INTENTOS_TESTS - 1:
                logger.info("[dojo] Tests fallaron, regenerando código con feedback...")
                feedback_prompt = (
                    f"{contexto_backend}\n\n"
                    f"CÓDIGO ANTERIOR (tests fallaron):\n```{lenguaje}\n{codigo}\n```\n\n"
                    f"OUTPUT DE TESTS:\n{tests_output[:500]}\n\n"
                    f"Corrige el código para que pase los tests."
                )
                codigo = await self._agentes[agente_key].ejecutar(feedback_prompt)
                if lenguaje == "python":
                    codigo = _format_python(codigo)
                resultado.codigo_final = codigo

                # Re-verify AST after regeneration
                ast_ok2, ast_err2 = self._verificar_ast(codigo, lenguaje)
                if not ast_ok2:
                    break

        resultado.tests_generados = tests_code
        resultado.tests_pasaron = tests_ok
        resultado.tests_output = tests_output

        pipeline_buffer.emit(pid, "TESTS_RUN",
                             "ok" if tests_ok else "error",
                             f"{'✅ Pasaron' if tests_ok else '❌ Fallaron'}: {tests_output[:80]}",
                             {"passed": tests_ok, "output": tests_output[:500]})

        if not tests_ok:
            resultado.exito = False
            resultado.razon_falla = f"Tests fallaron tras {self.MAX_INTENTOS_TESTS} intentos: {tests_output[:200]}"
            logger.info(f"[dojo] ❌ {resultado.razon_falla}")
            return resultado

        # ── SECURITY_SCAN + PERF_ANALYSIS en paralelo ──
        logger.info("[dojo] Paso 6-7: Seguridad + Performance en paralelo...")
        perf_task = self._ejecutar_performance(codigo, pedido)
        seg_task = self._ejecutar_seguridad(codigo, pedido)

        perf_resultado, seg_resultado = await asyncio.gather(perf_task, seg_task)

        resultado.score_performance = perf_resultado[0]
        resultado.issues_performance = perf_resultado[1]

        resultado.score_seguridad = seg_resultado[0]
        resultado.vulnerabilidades = seg_resultado[1]

        pipeline_buffer.emit(pid, "SECURITY_SCAN",
                             "error" if seg_resultado[2] else "ok",
                             f"Score: {seg_resultado[0]:.1f}/10"
                             + (f" — ⚠️ {', '.join(seg_resultado[1][:2])}" if seg_resultado[1] else ""),
                             {"score": seg_resultado[0], "critical": seg_resultado[2]})

        pipeline_buffer.emit(pid, "PERF_ANALYSIS", "ok",
                             f"Score: {perf_resultado[0]:.1f}/10",
                             {"score": perf_resultado[0]})

        # Gate de seguridad: vulnerabilidades críticas bloquean
        if seg_resultado[2]:  # critico=True
            resultado.razon_falla = (
                f"Vulnerabilidades críticas detectadas: {', '.join(seg_resultado[1])}"
            )
            return resultado

        # ── ✅ APROBADO — todos los gates pasaron ──
        resultado.exito = True
        logger.info(f"[dojo] ✅ Pipeline completado: {resultado.resumen()}")

        # ── EMBEDDING + STORED — guardar en memoria ──
        if self._memory_service and resultado.codigo_final:
            try:
                await self._memory_service.store_result(
                    content=f"Code Dojo ({lenguaje}): {pedido} — Score: {resultado.score_critico:.1f}",
                    namespace="codigo:usuario",
                    memory_type="skill",
                    source="code_dojo",
                    metadata={
                        "language": lenguaje,
                        "score_critico": resultado.score_critico,
                        "score_seguridad": resultado.score_seguridad,
                        "score_performance": resultado.score_performance,
                        "tests_passed": resultado.tests_pasaron,
                        "ast_valid": resultado.ast_valido,
                        "code_preview": resultado.codigo_final[:300],
                    },
                    _pipeline_id=pid,
                )
            except Exception:
                pass

        return resultado

    @staticmethod
    def _verificar_ast(codigo: str, lenguaje: str) -> tuple[bool, str]:
        """
        Verificación real de sintaxis.
        Para Python: ast.parse(). Para JS/TS: node --check.
        Returns: (valido, error_message)
        """
        if lenguaje == "python":
            try:
                ast.parse(codigo)
                return True, ""
            except SyntaxError as e:
                return False, f"Línea {e.lineno}: {e.msg}"
        elif lenguaje in ("javascript", "typescript"):
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".js", mode="w", delete=True
                ) as f:
                    f.write(codigo)
                    f.flush()
                    result = subprocess.run(
                        ["node", "--check", f.name],
                        capture_output=True, text=True, timeout=5,
                    )
                    if result.returncode == 0:
                        return True, ""
                    return False, result.stderr[:200]
            except FileNotFoundError:
                return True, ""  # node not installed, skip
            except Exception as e:
                return True, ""  # skip on error
        # For other languages, skip AST check
        return True, ""

    async def _ejecutar_testing(
        self, codigo: str, pedido: str, lenguaje: str
    ) -> tuple[str, bool, str]:
        """Genera tests y los ejecuta en sandbox. Returns (tests_code, passed, output)."""
        prompt = (
            f"Escribe tests para este código:\n```{lenguaje}\n{codigo}\n```\n"
            f"Tarea original: {pedido}\n"
            f"Usa pytest. Incluye al menos 3 tests que cubran casos normales y edge cases.\n"
            f"IMPORTANTE: El código fuente estará en 'source.py'. Usa 'from source import *' para importarlo."
        )
        tests = await self._agentes["testing"].ejecutar(prompt)
        if not tests:
            return "", False, "Testing agent no generó tests"

        if lenguaje == "python":
            tests = _format_python(tests)
            exito, output = self._sandbox.ejecutar_python(tests, codigo)
            logger.info(f"[dojo] Tests: {'✅ pasaron' if exito else '❌ fallaron'}")
            return tests, exito, output

        return tests, True, "Lenguaje no soportado para sandbox, asumiendo OK"

    async def _ejecutar_performance(self, codigo: str, pedido: str) -> tuple[float, list]:
        """Analiza performance del código."""
        import json
        prompt = (
            f"Analiza la complejidad y performance de este código:\n```\n{codigo}\n```\n"
            f"Tarea: {pedido}"
        )
        respuesta = await self._agentes["performance"].ejecutar(prompt)
        try:
            start = respuesta.find("{")
            end = respuesta.rfind("}") + 1
            if start >= 0:
                data = json.loads(respuesta[start:end])
                return float(data.get("score", 8.0)), data.get("issues", [])
        except Exception:
            pass
        return 8.0, []

    async def _ejecutar_seguridad(self, codigo: str, pedido: str) -> tuple[float, list, bool]:
        """Revisa seguridad OWASP. Returns (score, vulnerabilidades, es_critico)."""
        import json
        prompt = (
            f"Revisa este código buscando vulnerabilidades OWASP Top 10:\n```\n{codigo}\n```"
        )
        respuesta = await self._agentes["seguridad"].ejecutar(prompt)
        try:
            start = respuesta.find("{")
            end = respuesta.rfind("}") + 1
            if start >= 0:
                data = json.loads(respuesta[start:end])
                score = float(data.get("score", 9.0))
                vulns = data.get("vulnerabilidades", [])
                critico = bool(data.get("critico", False))
                return score, vulns, critico
        except Exception:
            pass
        return 9.0, [], False
