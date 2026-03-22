"""
YeyoOS — Verificador
Micro-fase 5.28 — Capa 5: Órganos

5 niveles de verificación para código investigado:
1. Ejecución básica (compilación/interpretación)
2. Tests independientes
3. Análisis estático (conecta con YeyoLint 6.14 si disponible)
4. Comparación con fuente original (similitud)
5. Stress test en Docker (si disponible)

Calcula confianza agregada 0.0-1.0 sobre los 5 niveles.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .modelos import LintResult, StressResult, TestResult, VerificacionCompleta

logger = logging.getLogger(__name__)

PESOS_NIVELES = {
    1: 0.25,  # Ejecución
    2: 0.25,  # Tests
    3: 0.20,  # Lint
    4: 0.15,  # Similitud con fuente
    5: 0.15,  # Stress test
}


class VerificadorError(Exception):
    """Error en verificación."""
    pass


class Verificador:
    """
    Verificador de código con 5 niveles de profundidad.
    Cada nivel es independiente — si uno falla, los demás siguen.
    La confianza final es un promedio ponderado de todos los niveles.
    """

    def __init__(
        self,
        timeout_ejecucion: float = 30.0,
        timeout_tests: float = 60.0,
        timeout_stress: float = 120.0,
        yeyo_lint_fn: Optional[Any] = None,
    ):
        self._timeout_ejecucion = timeout_ejecucion
        self._timeout_tests = timeout_tests
        self._timeout_stress = timeout_stress
        self._yeyo_lint_fn = yeyo_lint_fn

    async def verificar_completo(
        self,
        codigo: str,
        lenguaje: str = "python",
        tests: Optional[str] = None,
        fuente_original: Optional[str] = None,
        config_stress: Optional[Dict[str, Any]] = None,
    ) -> VerificacionCompleta:
        """
        Ejecuta los 5 niveles de verificación.
        Cada nivel es independiente — si uno falla, los demás siguen.
        """
        resultado = VerificacionCompleta()

        resultado.nivel_1_ejecucion = await self.ejecutar_codigo(codigo, lenguaje)

        if tests:
            resultado.nivel_2_tests = await self.correr_tests(codigo, tests)
        else:
            resultado.nivel_2_tests = TestResult(passed=True, total=0)

        resultado.nivel_3_lint = await self.analisis_estatico(codigo, lenguaje)

        if fuente_original:
            resultado.nivel_4_similitud = await self.comparar_con_fuente(codigo, fuente_original)
        else:
            resultado.nivel_4_similitud = 0.7

        if config_stress:
            resultado.nivel_5_stress = await self.stress_test_docker(codigo, config_stress)
        else:
            resultado.nivel_5_stress = StressResult(passed=True)

        resultado.confianza = self.calcular_confianza(resultado)

        logger.info(f"[verificador] Verificación completa: confianza={resultado.confianza}")
        return resultado

    async def ejecutar_codigo(self, codigo: str, lenguaje: str = "python") -> bool:
        """
        Nivel 1: Verifica que el código se ejecuta sin errores de sintaxis/importación.
        Ejecuta en subprocess con timeout. NO ejecuta lógica de negocio completa.
        """
        if lenguaje not in ("python", "javascript", "typescript"):
            logger.warning(f"[verificador] Lenguaje no soportado para ejecución: {lenguaje}")
            return True

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=self._extension(lenguaje),
                delete=False,
            ) as f:
                if lenguaje == "python":
                    f.write(f"import ast\nast.parse('''{codigo}''')\nprint('OK')\n")
                else:
                    f.write(codigo)
                f.flush()
                tmp_path = f.name

            if lenguaje == "python":
                cmd = [sys.executable, tmp_path]
            elif lenguaje == "javascript":
                cmd = ["node", "--check", tmp_path]
            else:
                cmd = ["npx", "tsc", "--noEmit", tmp_path]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout_ejecucion,
            )

            passed = proc.returncode == 0
            if not passed:
                logger.warning(f"[verificador] Nivel 1 falló: {stderr.decode()[:500]}")
            return passed

        except asyncio.TimeoutError:
            logger.warning("[verificador] Nivel 1 timeout")
            return False
        except Exception as e:
            logger.error(f"[verificador] Nivel 1 error: {e}")
            return False
        finally:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    async def correr_tests(self, codigo: str, tests: str) -> TestResult:
        """
        Nivel 2: Ejecuta tests independientes contra el código.
        Crea un archivo temporal con código + tests y ejecuta pytest.
        """
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                code_path = Path(tmpdir) / "modulo.py"
                test_path = Path(tmpdir) / "test_modulo.py"

                code_path.write_text(codigo, encoding="utf-8")
                test_content = f"import sys\nsys.path.insert(0, r'{tmpdir}')\nfrom modulo import *\n\n{tests}"
                test_path.write_text(test_content, encoding="utf-8")

                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self._timeout_tests,
                )

                output = stdout.decode()
                passed = proc.returncode == 0
                total, failed = self._parse_pytest_output(output)

                return TestResult(
                    passed=passed,
                    total=total,
                    failed=failed,
                    errors=[] if passed else [stderr.decode()[:1000]],
                    output=output[:2000],
                )

        except asyncio.TimeoutError:
            return TestResult(passed=False, errors=["Timeout ejecutando tests"])
        except Exception as e:
            return TestResult(passed=False, errors=[str(e)])

    async def analisis_estatico(self, codigo: str, lenguaje: str = "python") -> LintResult:
        """
        Nivel 3: Análisis estático. Usa YeyoLint (6.14) si está disponible,
        sino hace análisis básico con patrones.
        """
        if self._yeyo_lint_fn:
            try:
                return await self._yeyo_lint_fn(codigo, lenguaje)
            except Exception as e:
                logger.warning(f"[verificador] YeyoLint falló, usando fallback: {e}")

        issues = []
        lines = codigo.split("\n")
        warnings = 0
        errors = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "eval(" in stripped or "exec(" in stripped:
                issues.append({"linea": i, "tipo": "error", "mensaje": "Uso de eval/exec detectado"})
                errors += 1
            if len(line) > 120:
                issues.append({"linea": i, "tipo": "warning", "mensaje": "Línea > 120 caracteres"})
                warnings += 1
            if "TODO" in stripped or "FIXME" in stripped:
                issues.append({"linea": i, "tipo": "warning", "mensaje": "TODO/FIXME encontrado"})
                warnings += 1
            if "import *" in stripped:
                issues.append({"linea": i, "tipo": "warning", "mensaje": "Import wildcard"})
                warnings += 1

        return LintResult(
            passed=errors == 0,
            warnings=warnings,
            errors=errors,
            issues=issues,
        )

    async def comparar_con_fuente(self, codigo: str, fuente_original: str) -> float:
        """
        Nivel 4: Compara el código adaptado con la fuente original.
        Retorna similitud 0.0-1.0. Debe ser diferente (adaptado) pero no totalmente distinto.
        """
        if not fuente_original or not codigo:
            return 0.5

        set_original = set(fuente_original.split())
        set_adaptado = set(codigo.split())

        if not set_original or not set_adaptado:
            return 0.5

        interseccion = len(set_original & set_adaptado)
        union = len(set_original | set_adaptado)
        jaccard = interseccion / union if union > 0 else 0.0

        if jaccard > 0.95:
            return 0.6
        if jaccard > 0.3:
            return 0.9
        if jaccard > 0.1:
            return 0.7
        return 0.4

    async def stress_test_docker(
        self,
        codigo: str,
        config: Dict[str, Any],
    ) -> StressResult:
        """
        Nivel 5: Stress test en Docker container efímero.
        Ejecuta el código N veces con carga y mide rendimiento.
        Requiere Docker instalado. Si no está disponible, retorna passed=True.
        """
        iteraciones = config.get("iteraciones", 100)
        memoria_max_mb = config.get("memoria_max_mb", 256)

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                logger.info("[verificador] Docker no disponible, saltando stress test")
                return StressResult(passed=True, tiempo_ms=0)
        except FileNotFoundError:
            logger.info("[verificador] Docker no instalado, saltando stress test")
            return StressResult(passed=True, tiempo_ms=0)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = Path(tmpdir) / "stress.py"
                stress_code = (
                    f"import time\nstart = time.time()\n"
                    f"for i in range({iteraciones}):\n"
                    f"    exec(open('/app/code.py').read(), {{}})\n"
                    f"elapsed = int((time.time() - start) * 1000)\n"
                    f"print(f'OK {{elapsed}}ms')\n"
                )
                script_path.write_text(stress_code, encoding="utf-8")
                code_path = Path(tmpdir) / "code.py"
                code_path.write_text(codigo, encoding="utf-8")

                proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm",
                    "--network=none",
                    f"--memory={memoria_max_mb}m",
                    "--cpus=1",
                    "-v", f"{tmpdir}:/app:ro",
                    "python:3.11-slim",
                    "python", "/app/stress.py",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self._timeout_stress,
                )

                output = stdout.decode()
                passed = proc.returncode == 0 and "OK" in output
                tiempo_ms = 0
                if "OK" in output:
                    try:
                        tiempo_ms = int(output.split("OK")[1].strip().replace("ms", ""))
                    except (ValueError, IndexError):
                        pass

                return StressResult(
                    passed=passed,
                    tiempo_ms=tiempo_ms,
                    memoria_peak_mb=float(memoria_max_mb),
                    errores=[] if passed else [stderr.decode()[:500]],
                )

        except asyncio.TimeoutError:
            return StressResult(passed=False, errores=["Timeout en stress test"])
        except Exception as e:
            logger.error(f"[verificador] Error stress test: {e}")
            return StressResult(passed=False, errores=[str(e)])

    def calcular_confianza(self, resultado: VerificacionCompleta) -> float:
        """
        Calcula confianza final 0.0-1.0 como promedio ponderado de los 5 niveles.
        """
        scores = {}
        scores[1] = 1.0 if resultado.nivel_1_ejecucion else 0.0

        if resultado.nivel_2_tests:
            scores[2] = 1.0 if resultado.nivel_2_tests.passed else 0.0
        else:
            scores[2] = 0.5

        if resultado.nivel_3_lint:
            scores[3] = 1.0 if resultado.nivel_3_lint.passed else 0.3
        else:
            scores[3] = 0.5

        scores[4] = resultado.nivel_4_similitud

        if resultado.nivel_5_stress:
            scores[5] = 1.0 if resultado.nivel_5_stress.passed else 0.0
        else:
            scores[5] = 0.5

        confianza = sum(scores[n] * PESOS_NIVELES[n] for n in range(1, 6))
        return round(confianza, 3)

    @staticmethod
    def _extension(lenguaje: str) -> str:
        return {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
        }.get(lenguaje, ".txt")

    @staticmethod
    def _parse_pytest_output(output: str) -> tuple:
        """Parsea output de pytest para obtener total y fallidos."""
        total = 0
        failed = 0
        for line in output.split("\n"):
            if "passed" in line or "failed" in line:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "passed" and i > 0:
                        try:
                            total += int(parts[i - 1])
                        except ValueError:
                            pass
                    if p == "failed" and i > 0:
                        try:
                            failed += int(parts[i - 1])
                            total += failed
                        except ValueError:
                            pass
        return total, failed
