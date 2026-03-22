## ═══════════════════════════════════════
## MICRO-FASE 6.14 — YeyoLint: Análisis Estático Pre-Entrega
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.14-1 [VSCODE] — Análisis estático multi-lenguaje con regeneración automática antes de entregar código al usuario

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.14 de Capa 6 (Sistema Inmune): implementar YeyoLint, el sistema que intercepta TODA generación de código antes de entregarlo al usuario. Si el código tiene vulnerabilidades críticas, Yeyo regenera internamente (máximo 3 intentos) sin que el usuario lo vea. Malas prácticas que "funcionan" como SQL sin índices o ausencia de manejo de errores ya no pasan desapercibidas.

CONTEXTO:
- Micro-fases 6.0–6.13 completadas: incluye YeyoQuality (6.13) en src/quality/
- Stack backend: FastAPI + Python en src/
- Stack frontend: Next.js + TypeScript en frontend/src/
- Modelo IA: qwen2.5:3b via Ollama en http://localhost:11434
- ESLint ya existe en el frontend (package.json lo tiene configurado)
- YeyoLint intercepta generación de código ANTES de que llegue al usuario
- Si falla en 3 intentos: entrega código con advertencia visible al usuario
- Herramientas a instalar: bandit, pylint, mypy, semgrep (pip install)
- sqlfluff para SQL (pip install sqlfluff)
- Reglas críticas incluyen: no_passwords_en_codigo, no_sql_injection, no_eval_con_input_usuario
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencias necesarias:

   Ejecutar en terminal dentro de ~/yeyo-os:

   pip install bandit pylint mypy semgrep sqlfluff

2. Crear archivo src/quality/lint_rules.py:

   Ruta: ~/yeyo-os/src/quality/lint_rules.py
   Contenido:

   """
   YeyoOS — YeyoLint: Reglas Críticas
   Micro-fase 6.14 — Capa 6: Sistema Inmune

   Constantes de reglas con severidad: CRÍTICO / ADVERTENCIA / INFO.
   Las reglas CRÍTICAS bloquean la entrega y disparan regeneración.
   """

   from dataclasses import dataclass
   from enum import Enum
   from typing import Pattern
   import re


   class Severidad(str, Enum):
       CRITICO = "CRÍTICO"
       ADVERTENCIA = "ADVERTENCIA"
       INFO = "INFO"


   @dataclass(frozen=True)
   class ReglaLint:
       """Define una regla de análisis estático."""

       id: str
       descripcion: str
       severidad: Severidad
       patron: str                 # regex que detecta la violación
       lenguajes: tuple[str, ...]  # ("python",) o ("python", "javascript") o ("*",)
       sugerencia: str             # qué hacer en lugar de esto


   # ── Reglas críticas (bloquean entrega + regeneración) ─────────────────────

   REGLAS_CRITICAS: list[ReglaLint] = [
       ReglaLint(
           id="no_passwords_en_codigo",
           descripcion="Credenciales o contraseñas hardcodeadas en el código",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(password|passwd|pwd|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{4,}["\']',
           lenguajes=("*",),
           sugerencia="Usar variables de entorno: os.environ.get('MY_SECRET') o python-dotenv",
       ),
       ReglaLint(
           id="no_api_keys_hardcoded",
           descripcion="API keys o tokens hardcodeados",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{30,}|AIza[a-zA-Z0-9]{30,})',
           lenguajes=("*",),
           sugerencia="Nunca incluir API keys en el código fuente — usar .env y gitignore",
       ),
       ReglaLint(
           id="no_sql_injection_posible",
           descripcion="Construcción de queries SQL con concatenación de strings (riesgo de SQL injection)",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(execute|cursor\.execute|db\.query)\s*\(\s*[f"\'].*\{.*\}|["\'\s]\s*\+\s*(user|input|request|param)',
           lenguajes=("python", "javascript", "typescript"),
           sugerencia="Usar parámetros preparados: cursor.execute('SELECT * FROM t WHERE id = %s', (user_id,))",
       ),
       ReglaLint(
           id="no_eval_con_input_usuario",
           descripcion="Uso de eval() o exec() con input del usuario",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(eval|exec)\s*\(\s*(request|input|user|param|body|data)',
           lenguajes=("python", "javascript", "typescript"),
           sugerencia="Nunca pasar input del usuario a eval/exec — es ejecución remota de código",
       ),
       ReglaLint(
           id="no_credenciales_en_logs",
           descripcion="Credenciales o datos sensibles siendo logueados",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(logger\.|logging\.|print\(|console\.log\().*?(password|token|secret|api_key)',
           lenguajes=("*",),
           sugerencia="Nunca loguear credenciales — usar logger.info('Auth attempt for user: %s', username)",
       ),
       ReglaLint(
           id="no_path_traversal",
           descripcion="Construcción insegura de rutas de archivo con input del usuario",
           severidad=Severidad.CRITICO,
           patron=r'(?i)(open|os\.path\.join|pathlib\.Path)\s*\(.*?(request|user|input|param)',
           lenguajes=("python",),
           sugerencia="Usar pathlib con restricción al directorio permitido: base_dir / Path(user_input).name",
       ),
   ]

   # ── Reglas de advertencia (reportadas pero no bloquean) ───────────────────

   REGLAS_ADVERTENCIA: list[ReglaLint] = [
       ReglaLint(
           id="manejo_de_errores_presente",
           descripcion="Función sin ningún manejo de errores (try/except o raise)",
           severidad=Severidad.ADVERTENCIA,
           patron=r'^def\s+\w+[^:]*:\n(?!.*(?:try|raise|except))',
           lenguajes=("python",),
           sugerencia="Agregar try/except o documentar que los errores se propagan intencionalmente",
       ),
       ReglaLint(
           id="no_bare_except",
           descripcion="Uso de 'except:' sin especificar la excepción",
           severidad=Severidad.ADVERTENCIA,
           patron=r'^\s*except\s*:\s*$',
           lenguajes=("python",),
           sugerencia="Especificar excepción: except ValueError as e: — nunca capturar todo ciegamente",
       ),
       ReglaLint(
           id="no_print_en_produccion",
           descripcion="Uso de print() en lugar de logging",
           severidad=Severidad.ADVERTENCIA,
           patron=r'^\s*print\s*\(',
           lenguajes=("python",),
           sugerencia="Usar logger = logging.getLogger(__name__) y logger.info/debug/error",
       ),
       ReglaLint(
           id="no_sql_sin_indices",
           descripcion="Query SQL con WHERE sin índice obvio (columnas id/created_at preferidas)",
           severidad=Severidad.ADVERTENCIA,
           patron=r'(?i)WHERE\s+(?!id\s|created_at\s|updated_at\s)\w+\s*=',
           lenguajes=("sql",),
           sugerencia="Agregar índice: CREATE INDEX idx_tabla_columna ON tabla(columna)",
       ),
   ]

   # ── Reglas informativas ───────────────────────────────────────────────────

   REGLAS_INFO: list[ReglaLint] = [
       ReglaLint(
           id="docstring_presente",
           descripcion="Función pública sin docstring",
           severidad=Severidad.INFO,
           patron=r'^def\s+[a-z][^_][^:]*:\n\s*(?!\"\"\"|\'\'\')',
           lenguajes=("python",),
           sugerencia="Agregar docstring: def mi_funcion(): \"\"\"Descripción de qué hace.\"\"\"",
       ),
       ReglaLint(
           id="type_hints_presentes",
           descripcion="Función sin type hints",
           severidad=Severidad.INFO,
           patron=r'^def\s+\w+\([^)]*\)\s*:',
           lenguajes=("python",),
           sugerencia="Agregar type hints: def mi_funcion(nombre: str) -> int:",
       ),
   ]

   # ── Índice consolidado ────────────────────────────────────────────────────

   TODAS_LAS_REGLAS: list[ReglaLint] = REGLAS_CRITICAS + REGLAS_ADVERTENCIA + REGLAS_INFO

   IDS_CRITICOS: set[str] = {r.id for r in REGLAS_CRITICAS}

3. Crear archivo src/quality/yeyo_lint.py:

   Ruta: ~/yeyo-os/src/quality/yeyo_lint.py
   Contenido:

   """
   YeyoOS — YeyoLint: Análisis Estático Pre-Entrega
   Micro-fase 6.14 — Capa 6: Sistema Inmune

   Intercepta TODA generación de código antes de entregarlo al usuario.
   Si falla, Yeyo regenera internamente (máximo 3 intentos) sin que el usuario lo vea.
   Si los 3 intentos fallan: entrega con advertencia visible.
   """

   import logging
   import re
   import subprocess
   import tempfile
   import os
   from dataclasses import dataclass, field
   from typing import Optional

   from .lint_rules import (
       TODAS_LAS_REGLAS,
       IDS_CRITICOS,
       ReglaLint,
       Severidad,
   )

   logger = logging.getLogger("yeyo.quality.lint")

   ADVERTENCIA_USUARIO = (
       "\n\n⚠️ **Este código tiene observaciones de calidad.**\n"
       "YeyoLint detectó problemas que no pudo resolver automáticamente.\n"
       "Revisa el código antes de usarlo en producción."
   )


   # ─── Dataclasses de resultado ──────────────────────────────────────────────


   @dataclass
   class ViolacionLint:
       """Una violación detectada durante el análisis."""

       regla_id: str
       descripcion: str
       severidad: str
       linea: Optional[int]
       fragmento: str
       sugerencia: str


   @dataclass
   class LintResult:
       """Resultado completo del análisis estático."""

       passed: bool
       errores: list[ViolacionLint] = field(default_factory=list)
       warnings: list[ViolacionLint] = field(default_factory=list)
       infos: list[ViolacionLint] = field(default_factory=list)
       score: float = 1.0
       herramientas_usadas: list[str] = field(default_factory=list)

       @property
       def tiene_criticos(self) -> bool:
           return len(self.errores) > 0

       def resumen(self) -> str:
           return (
               f"passed={self.passed} "
               f"errores={len(self.errores)} "
               f"warnings={len(self.warnings)} "
               f"score={self.score:.2f}"
           )


   # ─── Analizador principal ──────────────────────────────────────────────────


   class YeyoLint:
       """
       Análisis estático multi-lenguaje antes de entregar código.
       Yeyo nunca entrega código que no pase YeyoLint.
       """

       ANALIZADORES = {
           "python": ["bandit", "pylint", "mypy"],
           "typescript": ["eslint", "tsc"],
           "javascript": ["eslint"],
           "sql": ["sqlfluff"],
           "*": ["semgrep"],
       }

       MAX_INTENTOS = 3

       def __init__(self) -> None:
           self._herramientas_disponibles: dict[str, bool] = {}
           self._detectar_herramientas()

       def _detectar_herramientas(self) -> None:
           """Detecta qué herramientas de análisis están disponibles."""
           herramientas = ["bandit", "pylint", "mypy", "semgrep", "sqlfluff", "eslint"]
           for herramienta in herramientas:
               try:
                   resultado = subprocess.run(
                       [herramienta, "--version"],
                       capture_output=True,
                       timeout=5,
                   )
                   self._herramientas_disponibles[herramienta] = resultado.returncode == 0
               except (FileNotFoundError, subprocess.TimeoutExpired):
                   self._herramientas_disponibles[herramienta] = False
           disponibles = [h for h, ok in self._herramientas_disponibles.items() if ok]
           logger.info("Herramientas disponibles: %s", disponibles)

       def analizar(self, codigo: str, lenguaje: str) -> LintResult:
           """
           Analiza el código con reglas internas + herramientas externas.
           LintResult: passed: bool, errores: list, warnings: list, score: float
           """
           lenguaje = lenguaje.lower().strip()
           errores: list[ViolacionLint] = []
           warnings: list[ViolacionLint] = []
           infos: list[ViolacionLint] = []
           herramientas_usadas: list[str] = ["reglas_internas"]

           # ── Paso 1: Reglas internas (regex rápido) ────────────────────────
           violaciones_internas = self._analizar_reglas_internas(codigo, lenguaje)
           for v in violaciones_internas:
               if v.severidad == Severidad.CRITICO:
                   errores.append(v)
               elif v.severidad == Severidad.ADVERTENCIA:
                   warnings.append(v)
               else:
                   infos.append(v)

           # ── Paso 2: Herramientas externas para Python ─────────────────────
           if lenguaje == "python":
               resultado_bandit = self._analizar_bandit(codigo)
               errores.extend(resultado_bandit["errores"])
               warnings.extend(resultado_bandit["warnings"])
               if resultado_bandit["usado"]:
                   herramientas_usadas.append("bandit")

               resultado_semgrep = self._analizar_semgrep(codigo, lenguaje)
               errores.extend(resultado_semgrep["errores"])
               warnings.extend(resultado_semgrep["warnings"])
               if resultado_semgrep["usado"]:
                   herramientas_usadas.append("semgrep")

           elif lenguaje == "sql":
               resultado_sqlfluff = self._analizar_sqlfluff(codigo)
               warnings.extend(resultado_sqlfluff["warnings"])
               if resultado_sqlfluff["usado"]:
                   herramientas_usadas.append("sqlfluff")

           # ── Calcular score ────────────────────────────────────────────────
           total_penalizacion = len(errores) * 0.3 + len(warnings) * 0.05
           score = max(0.0, 1.0 - total_penalizacion)

           passed = len(errores) == 0

           if passed:
               logger.info("YeyoLint PASSED — lenguaje=%s warnings=%d", lenguaje, len(warnings))
           else:
               logger.warning(
                   "YeyoLint FAILED — lenguaje=%s errores=%d", lenguaje, len(errores)
               )

           return LintResult(
               passed=passed,
               errores=errores,
               warnings=warnings,
               infos=infos,
               score=score,
               herramientas_usadas=herramientas_usadas,
           )

       def _analizar_reglas_internas(
           self, codigo: str, lenguaje: str
       ) -> list[ViolacionLint]:
           """Aplica reglas regex internas al código."""
           violaciones: list[ViolacionLint] = []
           lineas = codigo.split("\n")

           for regla in TODAS_LAS_REGLAS:
               if lenguaje not in regla.lenguajes and "*" not in regla.lenguajes:
                   continue

               try:
                   patron_compilado = re.compile(regla.patron, re.MULTILINE | re.IGNORECASE)
               except re.error:
                   logger.debug("Patrón inválido para regla %s: %s", regla.id, regla.patron)
                   continue

               for num_linea, linea in enumerate(lineas, start=1):
                   if patron_compilado.search(linea):
                       violaciones.append(
                           ViolacionLint(
                               regla_id=regla.id,
                               descripcion=regla.descripcion,
                               severidad=regla.severidad,
                               linea=num_linea,
                               fragmento=linea.strip()[:120],
                               sugerencia=regla.sugerencia,
                           )
                       )
                       break  # Una violación por regla es suficiente para bloquear

           return violaciones

       def _analizar_bandit(self, codigo: str) -> dict:
           """Ejecuta bandit para análisis de seguridad Python."""
           if not self._herramientas_disponibles.get("bandit"):
               return {"errores": [], "warnings": [], "usado": False}

           try:
               with tempfile.NamedTemporaryFile(
                   suffix=".py", mode="w", delete=False, encoding="utf-8"
               ) as f:
                   f.write(codigo)
                   tmp = f.name

               proc = subprocess.run(
                   ["bandit", "-r", tmp, "-f", "json", "-q"],
                   capture_output=True,
                   text=True,
                   timeout=30,
               )
               os.unlink(tmp)

               import json as json_mod
               datos = json_mod.loads(proc.stdout) if proc.stdout.strip() else {}
               resultados = datos.get("results", [])

               errores = []
               warnings = []

               for r in resultados:
                   severidad_bandit = r.get("issue_severity", "LOW").upper()
                   violacion = ViolacionLint(
                       regla_id=f"bandit_{r.get('test_id', 'unknown')}",
                       descripcion=r.get("issue_text", ""),
                       severidad=Severidad.CRITICO if severidad_bandit == "HIGH" else Severidad.ADVERTENCIA,
                       linea=r.get("line_number"),
                       fragmento=r.get("code", "").strip()[:120],
                       sugerencia=r.get("more_info", ""),
                   )
                   if severidad_bandit == "HIGH":
                       errores.append(violacion)
                   else:
                       warnings.append(violacion)

               return {"errores": errores, "warnings": warnings, "usado": True}

           except Exception as exc:
               logger.debug("Error ejecutando bandit: %s", exc)
               return {"errores": [], "warnings": [], "usado": False}

       def _analizar_semgrep(self, codigo: str, lenguaje: str) -> dict:
           """Ejecuta semgrep para análisis universal de patrones de seguridad."""
           if not self._herramientas_disponibles.get("semgrep"):
               return {"errores": [], "warnings": [], "usado": False}

           try:
               with tempfile.NamedTemporaryFile(
                   suffix=f".{lenguaje}", mode="w", delete=False, encoding="utf-8"
               ) as f:
                   f.write(codigo)
                   tmp = f.name

               proc = subprocess.run(
                   ["semgrep", "--config=auto", tmp, "--json", "--quiet"],
                   capture_output=True,
                   text=True,
                   timeout=60,
               )
               os.unlink(tmp)

               import json as json_mod
               datos = json_mod.loads(proc.stdout) if proc.stdout.strip() else {}
               resultados = datos.get("results", [])

               errores = []
               warnings = []
               for r in resultados:
                   severidad_sg = r.get("extra", {}).get("severity", "WARNING").upper()
                   violacion = ViolacionLint(
                       regla_id=f"semgrep_{r.get('check_id', 'unknown')}",
                       descripcion=r.get("extra", {}).get("message", ""),
                       severidad=Severidad.CRITICO if severidad_sg == "ERROR" else Severidad.ADVERTENCIA,
                       linea=r.get("start", {}).get("line"),
                       fragmento=r.get("extra", {}).get("lines", "").strip()[:120],
                       sugerencia="Ver: " + r.get("extra", {}).get("metadata", {}).get("references", [""])[0],
                   )
                   if severidad_sg == "ERROR":
                       errores.append(violacion)
                   else:
                       warnings.append(violacion)

               return {"errores": errores, "warnings": warnings, "usado": True}

           except Exception as exc:
               logger.debug("Error ejecutando semgrep: %s", exc)
               return {"errores": [], "warnings": [], "usado": False}

       def _analizar_sqlfluff(self, codigo: str) -> dict:
           """Ejecuta sqlfluff para análisis de queries SQL."""
           if not self._herramientas_disponibles.get("sqlfluff"):
               return {"warnings": [], "usado": False}

           try:
               with tempfile.NamedTemporaryFile(
                   suffix=".sql", mode="w", delete=False, encoding="utf-8"
               ) as f:
                   f.write(codigo)
                   tmp = f.name

               proc = subprocess.run(
                   ["sqlfluff", "lint", tmp, "--format", "json", "--dialect", "ansi"],
                   capture_output=True,
                   text=True,
                   timeout=30,
               )
               os.unlink(tmp)

               import json as json_mod
               datos = json_mod.loads(proc.stdout) if proc.stdout.strip() else []
               warnings = []

               for archivo in datos:
                   for violacion in archivo.get("violations", []):
                       warnings.append(
                           ViolacionLint(
                               regla_id=f"sqlfluff_{violacion.get('code', 'unknown')}",
                               descripcion=violacion.get("description", ""),
                               severidad=Severidad.ADVERTENCIA,
                               linea=violacion.get("line_no"),
                               fragmento="",
                               sugerencia="Ver documentación SQLFluff para corrección",
                           )
                       )

               return {"warnings": warnings, "usado": True}

           except Exception as exc:
               logger.debug("Error ejecutando sqlfluff: %s", exc)
               return {"warnings": [], "usado": False}

       def analizar_con_regeneracion(
           self,
           prompt_original: str,
           lenguaje: str,
           generador,
       ) -> tuple[str, LintResult]:
           """
           Ejecuta el flujo de análisis con regeneración automática.
           Retorna (codigo_final, lint_result).

           Si los 3 intentos fallan: entrega el último código con advertencia visible.
           """
           ultimo_codigo = ""
           ultimo_resultado = None

           for intento in range(self.MAX_INTENTOS):
               prompt = prompt_original
               if intento > 0 and ultimo_resultado:
                   errores_str = "\n".join(
                       f"- Línea {e.linea}: {e.descripcion} → {e.sugerencia}"
                       for e in ultimo_resultado.errores
                   )
                   prompt = (
                       f"{prompt_original}\n\n"
                       f"ERRORES DEL INTENTO ANTERIOR (intento {intento}):\n"
                       f"{errores_str}\n"
                       f"Corrige TODOS estos problemas de seguridad antes de responder."
                   )

               ultimo_codigo = generador(prompt)
               ultimo_resultado = self.analizar(ultimo_codigo, lenguaje)

               if ultimo_resultado.passed:
                   logger.info("YeyoLint passed en intento %d", intento + 1)
                   return ultimo_codigo, ultimo_resultado

               logger.warning(
                   "YeyoLint failed intento %d/%d — errores=%d",
                   intento + 1,
                   self.MAX_INTENTOS,
                   len(ultimo_resultado.errores),
               )

           # Todos los intentos fallaron — entregar con advertencia
           logger.error(
               "YeyoLint: %d intentos fallidos para lenguaje=%s — entregando con advertencia",
               self.MAX_INTENTOS,
               lenguaje,
           )
           codigo_con_advertencia = ultimo_codigo + ADVERTENCIA_USUARIO
           return codigo_con_advertencia, ultimo_resultado

5. Crear archivo src/api/routes/lint.py:

   Ruta: ~/yeyo-os/src/api/routes/lint.py
   Contenido:

   """
   YeyoOS — API: Endpoint de YeyoLint
   Micro-fase 6.14 — Capa 6: Sistema Inmune

   POST /api/lint/ — recibe código y retorna análisis estático completo.
   """

   import logging
   from typing import Literal, Optional

   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel, Field

   from src.quality.yeyo_lint import YeyoLint, LintResult

   logger = logging.getLogger("yeyo.api.lint")
   router = APIRouter(prefix="/api/lint", tags=["lint"])

   _yeyo_lint = YeyoLint()


   # ─── Modelos de request/response ──────────────────────────────────────────


   class LintRequest(BaseModel):
       codigo: str = Field(..., description="Código fuente a analizar", min_length=1)
       lenguaje: Literal["python", "typescript", "javascript", "sql"] = Field(
           default="python", description="Lenguaje del código"
       )


   class ViolacionResponse(BaseModel):
       regla_id: str
       descripcion: str
       severidad: str
       linea: Optional[int]
       fragmento: str
       sugerencia: str


   class LintResponse(BaseModel):
       passed: bool
       score: float
       errores: list[ViolacionResponse]
       warnings: list[ViolacionResponse]
       infos: list[ViolacionResponse]
       herramientas_usadas: list[str]
       resumen: str


   # ─── Endpoints ─────────────────────────────────────────────────────────────


   @router.post("/", response_model=LintResponse, summary="Analizar código con YeyoLint")
   async def analizar_codigo(request: LintRequest) -> LintResponse:
       """
       Analiza código fuente con YeyoLint.

       Retorna errores críticos (que bloquearían entrega al usuario),
       warnings (malas prácticas), e infos (sugerencias de estilo).
       """
       if not request.codigo.strip():
           raise HTTPException(status_code=422, detail="El código no puede estar vacío")

       resultado: LintResult = _yeyo_lint.analizar(request.codigo, request.lenguaje)

       def _to_response(violacion) -> ViolacionResponse:
           return ViolacionResponse(
               regla_id=violacion.regla_id,
               descripcion=violacion.descripcion,
               severidad=str(violacion.severidad),
               linea=violacion.linea,
               fragmento=violacion.fragmento,
               sugerencia=violacion.sugerencia,
           )

       return LintResponse(
           passed=resultado.passed,
           score=round(resultado.score, 4),
           errores=[_to_response(e) for e in resultado.errores],
           warnings=[_to_response(w) for w in resultado.warnings],
           infos=[_to_response(i) for i in resultado.infos],
           herramientas_usadas=resultado.herramientas_usadas,
           resumen=resultado.resumen(),
       )


   @router.get(
       "/herramientas",
       summary="Estado de herramientas de análisis disponibles",
   )
   async def estado_herramientas() -> dict:
       """Retorna qué herramientas de análisis estático están instaladas."""
       return {
           "disponibles": {
               h: ok for h, ok in _yeyo_lint._herramientas_disponibles.items()
           }
       }

6. Crear archivo tests/unit/quality/test_yeyo_lint.py:

   Ruta: ~/yeyo-os/tests/unit/quality/test_yeyo_lint.py
   Contenido:

   """
   Tests unitarios para YeyoLint — Micro-fase 6.14
   Incluye casos de código malicioso que DEBE rechazar.
   """

   import pytest
   from unittest.mock import MagicMock, patch

   from src.quality.yeyo_lint import YeyoLint, LintResult, ViolacionLint
   from src.quality.lint_rules import Severidad, IDS_CRITICOS


   # ─── Fixtures ─────────────────────────────────────────────────────────────


   @pytest.fixture
   def lint() -> YeyoLint:
       return YeyoLint()


   # ─── Test 1: código limpio pasa ────────────────────────────────────────────


   def test_codigo_limpio_pasa(lint):
       codigo = """
   import os
   import logging

   logger = logging.getLogger(__name__)

   def obtener_usuario(user_id: int) -> dict:
       \"\"\"Obtiene usuario por ID de forma segura.\"\"\"
       try:
           return {"id": user_id, "nombre": "Juan"}
       except Exception as exc:
           logger.error("Error obteniendo usuario: %s", exc)
           raise
   """
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is True
       assert len(resultado.errores) == 0


   # ─── Test 2: password hardcodeado → error crítico ─────────────────────────


   def test_password_hardcodeado_es_critico(lint):
       codigo = 'password = "super_secreto_123"\ndb_url = f"postgresql://user:{password}@localhost/db"'
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_passwords_en_codigo" in ids_errores


   # ─── Test 3: SQL injection → error crítico ────────────────────────────────


   def test_sql_injection_es_critico(lint):
       codigo = """
   def buscar_usuario(username):
       query = "SELECT * FROM users WHERE name = '" + username + "'"
       cursor.execute(query)
   """
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_sql_injection_posible" in ids_errores


   # ─── Test 4: eval con input del usuario → error crítico ───────────────────


   def test_eval_con_input_es_critico(lint):
       codigo = """
   def ejecutar(request_data):
       resultado = eval(request_data)
       return resultado
   """
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_eval_con_input_usuario" in ids_errores


   # ─── Test 5: API key hardcodeada → error crítico ──────────────────────────


   def test_api_key_hardcodeada_es_critico(lint):
       codigo = 'API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456789"\nclient.authenticate(API_KEY)'
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_api_keys_hardcoded" in ids_errores


   # ─── Test 6: credenciales en logs → error crítico ─────────────────────────


   def test_credenciales_en_logs_es_critico(lint):
       codigo = """
   import logging
   logger = logging.getLogger(__name__)

   def login(username, password):
       logger.info("Login attempt: user=%s password=%s", username, password)
   """
       resultado = lint.analizar(codigo, "python")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_credenciales_en_logs" in ids_errores


   # ─── Test 7: score se calcula correctamente ───────────────────────────────


   def test_score_disminuye_con_errores(lint):
       codigo_limpio = "x: int = 1\ny: int = x + 2\n"
       codigo_malo = 'password = "1234"\nsecret = "token_abc"\napi_key = "sk-' + 'a' * 30 + '"'
       resultado_limpio = lint.analizar(codigo_limpio, "python")
       resultado_malo = lint.analizar(codigo_malo, "python")
       assert resultado_limpio.score > resultado_malo.score


   # ─── Test 8: analizar_con_regeneracion llama al generador múltiples veces ─


   def test_regeneracion_reintenta_maximo_3_veces(lint):
       generador_mock = MagicMock(return_value='password = "hack"\n')
       codigo_final, resultado = lint.analizar_con_regeneracion(
           "Escribe algo", "python", generador_mock
       )
       assert generador_mock.call_count == 3
       assert "⚠️" in codigo_final


   # ─── Test 9: regeneración exitosa en segundo intento ─────────────────────


   def test_regeneracion_exitosa_en_segundo_intento(lint):
       llamadas = []

       def generador_mock(prompt):
           llamadas.append(prompt)
           if len(llamadas) == 1:
               return 'password = "malo"\n'
           return "x: int = 1\n"

       codigo_final, resultado = lint.analizar_con_regeneracion(
           "Escribe algo", "python", generador_mock
       )
       assert len(llamadas) == 2
       assert resultado.passed is True
       assert "⚠️" not in codigo_final


   # ─── Test 10: código TypeScript analiza con reglas universales ────────────


   def test_typescript_analiza_reglas_universales(lint):
       codigo = 'const apiKey = "sk-' + 'b' * 30 + '";\nconsole.log(apiKey);'
       resultado = lint.analizar(codigo, "typescript")
       assert resultado.passed is False
       ids_errores = {e.regla_id for e in resultado.errores}
       assert "no_api_keys_hardcoded" in ids_errores

VERIFICAR:
- [ ] `src/quality/lint_rules.py` contiene `REGLAS_CRITICAS`, `REGLAS_ADVERTENCIA`, `REGLAS_INFO` y `TODAS_LAS_REGLAS`
- [ ] `src/quality/yeyo_lint.py` contiene `YeyoLint`, `LintResult`, `ViolacionLint`
- [ ] `src/api/routes/lint.py` contiene endpoint `POST /api/lint/`
- [ ] `tests/unit/quality/test_yeyo_lint.py` contiene 10 tests
- [ ] Ejecutar `pip install bandit pylint mypy semgrep sqlfluff` → sin errores
- [ ] Ejecutar `cd ~/yeyo-os && python -m pytest tests/unit/quality/test_yeyo_lint.py -v` → los 10 tests pasan
- [ ] Test con password hardcodeado: `lint.analizar('password = "secreto"', 'python').passed == False`
- [ ] Test código limpio: `lint.analizar('x = 1 + 2', 'python').passed == True`
- [ ] Ejecutar `curl -X POST http://localhost:8000/api/lint/ -H "Content-Type: application/json" -d '{"codigo":"x=1","lenguaje":"python"}'` → respuesta JSON con `passed: true`
- [ ] Regeneración automática se activa sin que el usuario lo vea

SI FALLA:
- `bandit: command not found`: `pip install bandit` en el entorno virtual activo (verificar con `which python`)
- `semgrep timeout`: reducir timeout en `_analizar_semgrep` de 60 a 30 segundos si el hardware es lento
- `ImportError: src.quality.lint_rules`: verificar que `src/quality/__init__.py` existe (creado en 6.13)
- Tests de regeneración fallan: verificar que el fixture `lint` crea una instancia fresca por test con `@pytest.fixture`
- `endpoint 404`: agregar `from src.api.routes.lint import router as lint_router` y `app.include_router(lint_router)` en `src/main.py`
- `sqlfluff dialect error`: el dialect `ansi` es el más compatible — si falla intentar `--dialect postgres`

NO HACER:
- No entregar código con `no_passwords_en_codigo` o `no_api_keys_hardcoded` al usuario bajo ninguna circunstancia
- No hacer que el usuario vea los intentos de regeneración — el proceso es interno y transparente
- No aumentar `MAX_INTENTOS` por encima de 3 — si el modelo no puede corregir en 3 intentos, la advertencia es apropiada
- No omitir la verificación de herramientas disponibles al inicio — si bandit no está instalado, YeyoLint debe funcionar igual con las reglas internas
- No mezclar análisis síncrono con await — `analizar()` es síncrono por diseño para no bloquear el event loop de FastAPI innecesariamente

GATE: Todo código generado pasa por YeyoLint antes de ser entregado, código con vulnerabilidades críticas se regenera automáticamente hasta 3 veces, los 10 tests unitarios pasan, y el usuario nunca recibe código con passwords hardcodeados o SQL injection — si los 3 intentos fallan, recibe advertencia visible.
```
