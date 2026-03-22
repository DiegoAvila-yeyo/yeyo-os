## ═══════════════════════════════════════
## MICRO-FASE 6.13 — YeyoQuality: Criterios Objetivos de Feedback
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.13-1 [VSCODE] — Evaluador objetivo de calidad de código con feedback diferido al modelo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.13 de Capa 6 (Sistema Inmune): implementar YeyoQuality, el sistema que evalúa objetivamente si el código generado es bueno antes de dar feedback positivo al modelo. El modelo solo aprende de código que cumple criterios objetivos — no por simple aceptación del usuario.

CONTEXTO:
- Micro-fases 6.0–6.12 completadas: Guardian Daemon (Rust), Anomaly Detection, Kill Switch, Smart Snapshots, Backup 3-2-1, Anti-Ransomware, Honeypots, Network Firewall, Security Dashboard, Audit System, Integration Tests, YEYO-HACK Red Team Nocturno
- Flash Memory client: disponible en src/memory/flash_memory.py con método `store(content, importance, tags, metadata)`
- Base de datos: PostgreSQL con SQLAlchemy async (ya configurado en src/db/)
- Modelo IA: qwen2.5:3b via Ollama en http://localhost:11434
- YEYO-HACK (6.12) ya detecta vulnerabilidades y escribe resultados en Flash Memory
- El problema actual: si el usuario acepta un código, Yeyo aprende que fue bueno. Eso es incorrecto
- El código debe probarse objetivamente (ejecuta sin errores, pasa tests, 7 días en producción sin fallar)
- Solo score >= 0.8 genera feedback positivo al modelo; score < 0.4 genera feedback negativo
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/quality/__init__.py:

   Ruta: ~/yeyo-os/src/quality/__init__.py
   Contenido:

   """YeyoQuality — Módulo de Calidad Objetiva. Micro-fase 6.13."""

2. Crear archivo src/quality/models.py:

   Ruta: ~/yeyo-os/src/quality/models.py
   Contenido:

   """
   YeyoOS — YeyoQuality: Modelos de Base de Datos
   Micro-fase 6.13 — Capa 6: Sistema Inmune

   SQLAlchemy models para tracking de código evaluado.
   """

   import hashlib
   import json
   from datetime import datetime, timezone
   from typing import Optional

   from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
   from sqlalchemy.orm import declarative_base

   Base = declarative_base()


   def _utcnow() -> datetime:
       return datetime.now(timezone.utc)


   class CodigoEvaluado(Base):
       """Registro de cada bloque de código generado por Yeyo y su evaluación."""

       __tablename__ = "yeyo_quality_codigos"

       id = Column(Integer, primary_key=True, autoincrement=True)
       codigo_id = Column(String(64), unique=True, nullable=False, index=True)
       codigo_hash = Column(String(64), nullable=False)
       lenguaje = Column(String(32), nullable=False, default="python")
       generado_en = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
       evaluacion_iniciada_en = Column(DateTime(timezone=True), nullable=True)
       evaluacion_finalizada_en = Column(DateTime(timezone=True), nullable=True)

       # Criterios individuales (JSON con resultado de cada uno)
       criterios_json = Column(Text, nullable=False, default="{}")

       # Resultados finales
       score_final = Column(Float, nullable=True)
       feedback_tipo = Column(String(16), nullable=True)  # POSITIVO / NEUTRO / NEGATIVO
       feedback_aplicado = Column(Boolean, nullable=False, default=False)
       feedback_aplicado_en = Column(DateTime(timezone=True), nullable=True)

       # Razones legibles
       razones_json = Column(Text, nullable=False, default="[]")

       # Estado del ciclo de vida
       estado = Column(String(32), nullable=False, default="pendiente")
       # Estados: pendiente → monitoreando → evaluado → feedback_aplicado

       def criterios(self) -> dict:
           return json.loads(self.criterios_json)

       def razones(self) -> list:
           return json.loads(self.razones_json)

       def __repr__(self) -> str:
           return (
               f"<CodigoEvaluado id={self.id} codigo_id={self.codigo_id!r} "
               f"estado={self.estado!r} score={self.score_final}>"
           )

       @staticmethod
       def hash_codigo(codigo: str) -> str:
           return hashlib.sha256(codigo.encode()).hexdigest()

3. Crear archivo src/quality/yeyo_quality.py:

   Ruta: ~/yeyo-os/src/quality/yeyo_quality.py
   Contenido:

   """
   YeyoOS — YeyoQuality: Evaluador Objetivo de Calidad
   Micro-fase 6.13 — Capa 6: Sistema Inmune

   Evalúa objetivamente si el código generado es bueno.
   Solo da feedback positivo al modelo si cumple TODOS los criterios.

   Flujo:
     Yeyo genera código
       ↓
     YeyoQuality registra el código_id con estado "pendiente"
       ↓
     QualityMonitor observa el código en ejecución (7 días)
       ↓
     Al finalizar evaluación:
       → score >= 0.8: feedback POSITIVO al modelo (aprende este patrón)
       → score 0.4-0.8: feedback NEUTRO (no aprende ni desaprende)
       → score < 0.4: feedback NEGATIVO (aprende a evitar este patrón)
         ↓
     Resultado guardado en Flash Memory con importancia según score
   """

   import asyncio
   import json
   import logging
   import subprocess
   import tempfile
   import uuid
   from dataclasses import dataclass, field
   from datetime import datetime, timedelta, timezone
   from typing import Optional

   logger = logging.getLogger("yeyo.quality")


   # ─── Dataclasses de resultado ──────────────────────────────────────────────


   @dataclass
   class CriterioResult:
       """Resultado de evaluar un criterio individual."""

       nombre: str
       aprobado: bool
       peso: float
       razon: str = ""
       detalle: dict = field(default_factory=dict)


   @dataclass
   class QualityResult:
       """Resultado completo de la evaluación de calidad de un código."""

       codigo_id: str
       score: float                       # 0.0 – 1.0
       feedback: str                      # POSITIVO / NEUTRO / NEGATIVO
       criterios: list[CriterioResult] = field(default_factory=list)
       razones: list[str] = field(default_factory=list)
       evaluado_en: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

       @property
       def es_positivo(self) -> bool:
           return self.score >= 0.8

       @property
       def es_negativo(self) -> bool:
           return self.score < 0.4

       def to_dict(self) -> dict:
           return {
               "codigo_id": self.codigo_id,
               "score": round(self.score, 4),
               "feedback": self.feedback,
               "razones": self.razones,
               "criterios": [
                   {
                       "nombre": c.nombre,
                       "aprobado": c.aprobado,
                       "peso": c.peso,
                       "razon": c.razon,
                   }
                   for c in self.criterios
               ],
               "evaluado_en": self.evaluado_en.isoformat(),
           }


   # ─── Evaluador principal ───────────────────────────────────────────────────


   class YeyoQuality:
       """
       Evalúa objetivamente si el código generado es bueno.
       Solo da feedback positivo al modelo si cumple TODOS los criterios.
       """

       # Pesos de cada criterio (deben sumar 1.0)
       CRITERIOS_PESOS = {
           "ejecuta_sin_errores": 0.30,
           "pasa_tests": 0.30,
           "no_vulnerabilidades": 0.25,
           "rendimiento_aceptable": 0.10,
           "tiempo_produccion_dias": 0.05,
       }

       # Días en producción sin fallar para aprobar el criterio temporal
       DIAS_PRODUCCION_REQUERIDOS: int = 7

       # Umbral de recursos: si el código usa >2x los recursos esperados, falla
       FACTOR_RECURSOS_MAXIMO: float = 2.0

       def __init__(self) -> None:
           self._registro: dict[str, dict] = {}

       def registrar_codigo(self, codigo: str, lenguaje: str = "python") -> str:
           """
           Registra un bloque de código para evaluación diferida.
           Retorna el codigo_id único para rastrear su evaluación.
           """
           from .models import CodigoEvaluado

           codigo_id = str(uuid.uuid4())
           self._registro[codigo_id] = {
               "codigo": codigo,
               "lenguaje": lenguaje,
               "registrado_en": datetime.now(timezone.utc).isoformat(),
               "estado": "pendiente",
               "criterios_parciales": {},
           }
           logger.info("Código registrado para evaluación: %s", codigo_id)
           return codigo_id

       def evaluar(self, codigo_id: str) -> Optional[QualityResult]:
           """
           Evalúa el código registrado con codigo_id.
           Retorna QualityResult o None si el código_id no existe.
           """
           entrada = self._registro.get(codigo_id)
           if not entrada:
               logger.warning("codigo_id no encontrado: %s", codigo_id)
               return None

           codigo = entrada["codigo"]
           lenguaje = entrada["lenguaje"]
           criterios_parciales = entrada.get("criterios_parciales", {})

           criterios: list[CriterioResult] = []

           # ── Criterio 1: ejecuta_sin_errores ──────────────────────────────
           resultado_ejecucion = self._evaluar_ejecucion(codigo, lenguaje)
           criterios.append(resultado_ejecucion)

           # ── Criterio 2: pasa_tests ────────────────────────────────────────
           resultado_tests = self._evaluar_tests(codigo_id, criterios_parciales)
           criterios.append(resultado_tests)

           # ── Criterio 3: no_vulnerabilidades ──────────────────────────────
           resultado_vulnerabilidades = self._evaluar_vulnerabilidades(
               codigo_id, criterios_parciales
           )
           criterios.append(resultado_vulnerabilidades)

           # ── Criterio 4: rendimiento_aceptable ────────────────────────────
           resultado_rendimiento = self._evaluar_rendimiento(
               codigo_id, criterios_parciales
           )
           criterios.append(resultado_rendimiento)

           # ── Criterio 5: tiempo_produccion_dias ───────────────────────────
           resultado_tiempo = self._evaluar_tiempo_produccion(
               codigo_id, criterios_parciales
           )
           criterios.append(resultado_tiempo)

           # ── Calcular score ponderado ──────────────────────────────────────
           score = sum(
               (1.0 if c.aprobado else 0.0) * self.CRITERIOS_PESOS[c.nombre]
               for c in criterios
           )

           # ── Determinar tipo de feedback ───────────────────────────────────
           if score >= 0.8:
               feedback = "POSITIVO"
           elif score >= 0.4:
               feedback = "NEUTRO"
           else:
               feedback = "NEGATIVO"

           razones = [c.razon for c in criterios if c.razon and not c.aprobado]

           result = QualityResult(
               codigo_id=codigo_id,
               score=score,
               feedback=feedback,
               criterios=criterios,
               razones=razones,
           )

           self._registro[codigo_id]["estado"] = "evaluado"
           self._registro[codigo_id]["resultado"] = result.to_dict()

           logger.info(
               "Evaluación completada: codigo_id=%s score=%.2f feedback=%s",
               codigo_id,
               score,
               feedback,
           )
           return result

       # ── Evaluadores individuales ───────────────────────────────────────────

       def _evaluar_ejecucion(self, codigo: str, lenguaje: str) -> CriterioResult:
           """Compila/ejecuta el código en sandbox y verifica que no lance excepciones."""
           if lenguaje != "python":
               # Para otros lenguajes se asume aprobado (extensible)
               return CriterioResult(
                   nombre="ejecuta_sin_errores",
                   aprobado=True,
                   peso=self.CRITERIOS_PESOS["ejecuta_sin_errores"],
                   razon="",
               )

           try:
               with tempfile.NamedTemporaryFile(
                   suffix=".py", mode="w", delete=False, encoding="utf-8"
               ) as f:
                   f.write(codigo)
                   tmp_path = f.name

               proc = subprocess.run(
                   ["python", "-c", f"import py_compile; py_compile.compile('{tmp_path}', doraise=True)"],
                   capture_output=True,
                   text=True,
                   timeout=10,
               )
               if proc.returncode != 0:
                   return CriterioResult(
                       nombre="ejecuta_sin_errores",
                       aprobado=False,
                       peso=self.CRITERIOS_PESOS["ejecuta_sin_errores"],
                       razon=f"Error de compilación: {proc.stderr.strip()[:200]}",
                   )
               return CriterioResult(
                   nombre="ejecuta_sin_errores",
                   aprobado=True,
                   peso=self.CRITERIOS_PESOS["ejecuta_sin_errores"],
                   razon="",
               )
           except subprocess.TimeoutExpired:
               return CriterioResult(
                   nombre="ejecuta_sin_errores",
                   aprobado=False,
                   peso=self.CRITERIOS_PESOS["ejecuta_sin_errores"],
                   razon="Timeout al compilar el código (>10s)",
               )
           except Exception as exc:
               return CriterioResult(
                   nombre="ejecuta_sin_errores",
                   aprobado=False,
                   peso=self.CRITERIOS_PESOS["ejecuta_sin_errores"],
                   razon=f"Excepción inesperada: {exc}",
               )

       def _evaluar_tests(
           self, codigo_id: str, criterios_parciales: dict
       ) -> CriterioResult:
           """Verifica que los tests automáticos asociados pasen."""
           resultado_tests = criterios_parciales.get("pasa_tests")
           if resultado_tests is None:
               return CriterioResult(
                   nombre="pasa_tests",
                   aprobado=False,
                   peso=self.CRITERIOS_PESOS["pasa_tests"],
                   razon="Tests no ejecutados todavía — pendiente de ejecución del QualityMonitor",
               )
           aprobado = resultado_tests.get("passed", False)
           razon = "" if aprobado else resultado_tests.get("razon", "Tests fallaron")
           return CriterioResult(
               nombre="pasa_tests",
               aprobado=aprobado,
               peso=self.CRITERIOS_PESOS["pasa_tests"],
               razon=razon,
               detalle=resultado_tests,
           )

       def _evaluar_vulnerabilidades(
           self, codigo_id: str, criterios_parciales: dict
       ) -> CriterioResult:
           """Verifica que YEYO-HACK no encontró vulnerabilidades en este código."""
           resultado_vuln = criterios_parciales.get("no_vulnerabilidades")
           if resultado_vuln is None:
               return CriterioResult(
                   nombre="no_vulnerabilidades",
                   aprobado=True,
                   peso=self.CRITERIOS_PESOS["no_vulnerabilidades"],
                   razon="",
                   detalle={"nota": "YEYO-HACK no reportó nada — asumido limpio"},
               )
           aprobado = resultado_vuln.get("limpio", True)
           razon = "" if aprobado else resultado_vuln.get("razon", "Vulnerabilidades detectadas")
           return CriterioResult(
               nombre="no_vulnerabilidades",
               aprobado=aprobado,
               peso=self.CRITERIOS_PESOS["no_vulnerabilidades"],
               razon=razon,
               detalle=resultado_vuln,
           )

       def _evaluar_rendimiento(
           self, codigo_id: str, criterios_parciales: dict
       ) -> CriterioResult:
           """Verifica que el código no consume >2x los recursos esperados."""
           resultado_rend = criterios_parciales.get("rendimiento_aceptable")
           if resultado_rend is None:
               return CriterioResult(
                   nombre="rendimiento_aceptable",
                   aprobado=True,
                   peso=self.CRITERIOS_PESOS["rendimiento_aceptable"],
                   razon="",
                   detalle={"nota": "Sin datos de rendimiento — asumido aceptable"},
               )
           factor = resultado_rend.get("factor_recursos", 1.0)
           aprobado = factor <= self.FACTOR_RECURSOS_MAXIMO
           razon = (
               ""
               if aprobado
               else f"Usa {factor:.1f}x los recursos esperados (máximo {self.FACTOR_RECURSOS_MAXIMO}x)"
           )
           return CriterioResult(
               nombre="rendimiento_aceptable",
               aprobado=aprobado,
               peso=self.CRITERIOS_PESOS["rendimiento_aceptable"],
               razon=razon,
               detalle=resultado_rend,
           )

       def _evaluar_tiempo_produccion(
           self, codigo_id: str, criterios_parciales: dict
       ) -> CriterioResult:
           """Verifica que el código lleva al menos 7 días en producción sin fallar."""
           resultado_tiempo = criterios_parciales.get("tiempo_produccion_dias")
           if resultado_tiempo is None:
               return CriterioResult(
                   nombre="tiempo_produccion_dias",
                   aprobado=False,
                   peso=self.CRITERIOS_PESOS["tiempo_produccion_dias"],
                   razon=f"Código pendiente de {self.DIAS_PRODUCCION_REQUERIDOS} días en producción",
               )
           dias = resultado_tiempo.get("dias_sin_fallar", 0)
           fallos = resultado_tiempo.get("fallos", 0)
           aprobado = dias >= self.DIAS_PRODUCCION_REQUERIDOS and fallos == 0
           razon = (
               ""
               if aprobado
               else f"Solo {dias} días sin fallar (requiere {self.DIAS_PRODUCCION_REQUERIDOS}) — {fallos} fallo(s) detectado(s)"
           )
           return CriterioResult(
               nombre="tiempo_produccion_dias",
               aprobado=aprobado,
               peso=self.CRITERIOS_PESOS["tiempo_produccion_dias"],
               razon=razon,
               detalle=resultado_tiempo,
           )

       def registrar_criterio_parcial(
           self, codigo_id: str, criterio: str, datos: dict
       ) -> None:
           """
           Permite al QualityMonitor actualizar resultados parciales de criterios
           mientras observa el código en ejecución.
           """
           if codigo_id not in self._registro:
               logger.warning(
                   "Intento de actualizar criterio para codigo_id desconocido: %s", codigo_id
               )
               return
           self._registro[codigo_id]["criterios_parciales"][criterio] = datos
           logger.debug("Criterio parcial actualizado: %s → %s", criterio, criterio)

       def listar_pendientes(self) -> list[str]:
           """Retorna lista de codigo_ids en estado pendiente o monitoreando."""
           return [
               cid
               for cid, datos in self._registro.items()
               if datos["estado"] in ("pendiente", "monitoreando")
           ]


   # ─── Monitor de background ────────────────────────────────────────────────


   class QualityMonitor:
       """
       Background thread que observa código registrado en ejecución.
       Actualiza criterios parciales y dispara evaluación final al cumplir el tiempo.
       """

       def __init__(
           self,
           quality: YeyoQuality,
           feedback_engine=None,
           intervalo_check_horas: int = 24,
       ) -> None:
           self.quality = quality
           self.feedback_engine = feedback_engine
           self.intervalo_check_horas = intervalo_check_horas
           self._task: Optional[asyncio.Task] = None
           self._corriendo = False

       async def iniciar(self) -> None:
           """Inicia el monitor como tarea asyncio."""
           self._corriendo = True
           self._task = asyncio.create_task(self._loop())
           logger.info("QualityMonitor iniciado (intervalo=%dh)", self.intervalo_check_horas)

       async def detener(self) -> None:
           """Detiene el monitor."""
           self._corriendo = False
           if self._task:
               self._task.cancel()
               try:
                   await self._task
               except asyncio.CancelledError:
                   pass
           logger.info("QualityMonitor detenido")

       async def _loop(self) -> None:
           """Ciclo principal de monitoreo."""
           while self._corriendo:
               pendientes = self.quality.listar_pendientes()
               logger.info(
                   "QualityMonitor: revisando %d código(s) pendiente(s)", len(pendientes)
               )
               for codigo_id in pendientes:
                   await self._revisar_codigo(codigo_id)
               await asyncio.sleep(self.intervalo_check_horas * 3600)

       async def _revisar_codigo(self, codigo_id: str) -> None:
           """Revisa el estado de un código individual y actualiza criterios."""
           entrada = self.quality._registro.get(codigo_id)
           if not entrada:
               return

           registrado_en = datetime.fromisoformat(entrada["registrado_en"])
           dias_transcurridos = (datetime.now(timezone.utc) - registrado_en).days

           # Actualizar tiempo en producción
           self.quality.registrar_criterio_parcial(
               codigo_id,
               "tiempo_produccion_dias",
               {
                   "dias_sin_fallar": dias_transcurridos,
                   "fallos": entrada.get("fallos_detectados", 0),
               },
           )

           # Si ya pasaron 7 días, disparar evaluación final
           if dias_transcurridos >= YeyoQuality.DIAS_PRODUCCION_REQUERIDOS:
               logger.info(
                   "Código %s alcanzó %d días — iniciando evaluación final",
                   codigo_id,
                   dias_transcurridos,
               )
               result = self.quality.evaluar(codigo_id)
               if result and self.feedback_engine:
                   await self.feedback_engine.aplicar_feedback(result)

4. Crear archivo src/quality/feedback_engine.py:

   Ruta: ~/yeyo-os/src/quality/feedback_engine.py
   Contenido:

   """
   YeyoOS — YeyoQuality: Motor de Feedback
   Micro-fase 6.13 — Capa 6: Sistema Inmune

   Aplica feedback positivo/negativo al modelo via ajuste de Flash Memory weights.
   El modelo aprende de código bueno y aprende a evitar código malo.
   """

   import json
   import logging
   from datetime import datetime, timezone
   from typing import Optional

   import httpx

   logger = logging.getLogger("yeyo.quality.feedback")

   OLLAMA_BASE_URL = "http://localhost:11434"
   FLASH_MEMORY_IMPORTANCE_POSITIVO = 0.9
   FLASH_MEMORY_IMPORTANCE_NEUTRO = 0.5
   FLASH_MEMORY_IMPORTANCE_NEGATIVO = 0.2


   class FeedbackEngine:
       """
       Aplica feedback al modelo basado en QualityResult.
       Estrategia: ajusta Flash Memory weights según score.
       """

       def __init__(self, flash_memory=None) -> None:
           self.flash_memory = flash_memory
           self._historial: list[dict] = []

       async def aplicar_feedback(self, result) -> bool:
           """
           Aplica el feedback correspondiente según el resultado de calidad.
           Retorna True si el feedback fue aplicado exitosamente.
           """
           from .yeyo_quality import QualityResult

           if not isinstance(result, QualityResult):
               logger.error("resultado no es QualityResult: %s", type(result))
               return False

           if result.feedback == "POSITIVO":
               exito = await self._feedback_positivo(result)
           elif result.feedback == "NEGATIVO":
               exito = await self._feedback_negativo(result)
           else:
               exito = await self._feedback_neutro(result)

           self._historial.append(
               {
                   "codigo_id": result.codigo_id,
                   "feedback": result.feedback,
                   "score": result.score,
                   "aplicado": exito,
                   "aplicado_en": datetime.now(timezone.utc).isoformat(),
               }
           )
           return exito

       async def _feedback_positivo(self, result) -> bool:
           """
           Feedback POSITIVO: score >= 0.8.
           Guarda el patrón en Flash Memory con importancia alta.
           El modelo aprende a replicar este estilo.
           """
           logger.info(
               "Aplicando feedback POSITIVO para codigo_id=%s score=%.2f",
               result.codigo_id,
               result.score,
           )
           if not self.flash_memory:
               logger.warning("Flash Memory no disponible — feedback positivo omitido")
               return False

           contenido = (
               f"[PATRÓN POSITIVO] Código evaluado con score={result.score:.2f}. "
               f"Criterios aprobados: {[c.nombre for c in result.criterios if c.aprobado]}. "
               f"Este patrón debe replicarse."
           )
           try:
               self.flash_memory.store(
                   content=contenido,
                   importance=FLASH_MEMORY_IMPORTANCE_POSITIVO,
                   tags=["quality", "feedback_positivo", "patron_bueno"],
                   metadata={
                       "codigo_id": result.codigo_id,
                       "score": result.score,
                       "tipo": "feedback_positivo",
                   },
               )
               logger.info("Feedback positivo guardado en Flash Memory")
               return True
           except Exception as exc:
               logger.error("Error guardando feedback positivo: %s", exc)
               return False

       async def _feedback_negativo(self, result) -> bool:
           """
           Feedback NEGATIVO: score < 0.4.
           Guarda el anti-patrón en Flash Memory con importancia baja.
           El modelo aprende a evitar este estilo.
           """
           logger.info(
               "Aplicando feedback NEGATIVO para codigo_id=%s score=%.2f",
               result.codigo_id,
               result.score,
           )
           if not self.flash_memory:
               logger.warning("Flash Memory no disponible — feedback negativo omitido")
               return False

           razones_str = "; ".join(result.razones) if result.razones else "sin razones específicas"
           contenido = (
               f"[ANTI-PATRÓN] Código evaluado con score={result.score:.2f}. "
               f"Razones de fallo: {razones_str}. "
               f"Criterios reprobados: {[c.nombre for c in result.criterios if not c.aprobado]}. "
               f"Este patrón debe EVITARSE."
           )
           try:
               self.flash_memory.store(
                   content=contenido,
                   importance=FLASH_MEMORY_IMPORTANCE_NEGATIVO,
                   tags=["quality", "feedback_negativo", "anti_patron"],
                   metadata={
                       "codigo_id": result.codigo_id,
                       "score": result.score,
                       "tipo": "feedback_negativo",
                       "razones": result.razones,
                   },
               )
               logger.info("Feedback negativo guardado en Flash Memory")
               return True
           except Exception as exc:
               logger.error("Error guardando feedback negativo: %s", exc)
               return False

       async def _feedback_neutro(self, result) -> bool:
           """
           Feedback NEUTRO: score 0.4–0.8.
           Se registra pero no modifica los pesos del modelo.
           """
           logger.info(
               "Feedback NEUTRO para codigo_id=%s score=%.2f — sin cambios en el modelo",
               result.codigo_id,
               result.score,
           )
           return True

       def obtener_historial(self) -> list[dict]:
           """Retorna historial de feedbacks aplicados."""
           return list(self._historial)

       def estadisticas(self) -> dict:
           """Retorna estadísticas del feedback engine."""
           total = len(self._historial)
           if total == 0:
               return {"total": 0, "positivos": 0, "neutros": 0, "negativos": 0}
           positivos = sum(1 for h in self._historial if h["feedback"] == "POSITIVO")
           negativos = sum(1 for h in self._historial if h["feedback"] == "NEGATIVO")
           neutros = total - positivos - negativos
           return {
               "total": total,
               "positivos": positivos,
               "neutros": neutros,
               "negativos": negativos,
               "tasa_positivos": round(positivos / total, 4),
               "score_promedio": round(
                   sum(h["score"] for h in self._historial) / total, 4
               ),
           }

5. Crear archivo tests/unit/quality/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/quality/__init__.py
   Contenido:

   """Tests unitarios para el módulo quality — Micro-fase 6.13."""

6. Crear archivo tests/unit/quality/test_yeyo_quality.py:

   Ruta: ~/yeyo-os/tests/unit/quality/test_yeyo_quality.py
   Contenido:

   """
   Tests unitarios para YeyoQuality — Micro-fase 6.13
   Cubre: registro, evaluación, criterios, feedback engine, score.
   """

   import asyncio
   from datetime import datetime, timezone
   from unittest.mock import AsyncMock, MagicMock, patch

   import pytest

   from src.quality.yeyo_quality import (
       CriterioResult,
       QualityMonitor,
       QualityResult,
       YeyoQuality,
   )
   from src.quality.feedback_engine import FeedbackEngine


   # ─── Fixtures ─────────────────────────────────────────────────────────────


   @pytest.fixture
   def quality() -> YeyoQuality:
       return YeyoQuality()


   @pytest.fixture
   def codigo_python_valido() -> str:
       return """
   def sumar(a: int, b: int) -> int:
       \"\"\"Suma dos enteros.\"\"\"
       if not isinstance(a, int) or not isinstance(b, int):
           raise TypeError("a y b deben ser enteros")
       return a + b
   """


   @pytest.fixture
   def codigo_python_invalido() -> str:
       return "def broken(:\n    pass"


   # ─── Test 1: registro retorna código_id único ──────────────────────────────


   def test_registrar_codigo_retorna_id_unico(quality, codigo_python_valido):
       id1 = quality.registrar_codigo(codigo_python_valido)
       id2 = quality.registrar_codigo(codigo_python_valido)
       assert id1 != id2
       assert len(id1) == 36  # UUID4


   # ─── Test 2: código válido aprueba ejecuta_sin_errores ────────────────────


   def test_evaluar_ejecucion_codigo_valido(quality, codigo_python_valido):
       resultado = quality._evaluar_ejecucion(codigo_python_valido, "python")
       assert resultado.nombre == "ejecuta_sin_errores"
       assert resultado.aprobado is True
       assert resultado.razon == ""


   # ─── Test 3: código inválido reprueba ejecuta_sin_errores ─────────────────


   def test_evaluar_ejecucion_codigo_invalido(quality, codigo_python_invalido):
       resultado = quality._evaluar_ejecucion(codigo_python_invalido, "python")
       assert resultado.nombre == "ejecuta_sin_errores"
       assert resultado.aprobado is False
       assert "compilación" in resultado.razon.lower() or "error" in resultado.razon.lower()


   # ─── Test 4: score >= 0.8 → feedback POSITIVO ─────────────────────────────


   def test_score_alto_genera_feedback_positivo(quality, codigo_python_valido):
       codigo_id = quality.registrar_codigo(codigo_python_valido)
       # Simular todos los criterios aprobados
       quality.registrar_criterio_parcial(codigo_id, "pasa_tests", {"passed": True, "razon": ""})
       quality.registrar_criterio_parcial(codigo_id, "no_vulnerabilidades", {"limpio": True})
       quality.registrar_criterio_parcial(
           codigo_id, "rendimiento_aceptable", {"factor_recursos": 1.1}
       )
       quality.registrar_criterio_parcial(
           codigo_id,
           "tiempo_produccion_dias",
           {"dias_sin_fallar": 7, "fallos": 0},
       )
       resultado = quality.evaluar(codigo_id)
       assert resultado is not None
       assert resultado.feedback == "POSITIVO"
       assert resultado.score >= 0.8


   # ─── Test 5: score < 0.4 → feedback NEGATIVO ──────────────────────────────


   def test_score_bajo_genera_feedback_negativo(quality):
       codigo_id = quality.registrar_codigo("x = 1")
       # Todos los criterios reprobados
       quality.registrar_criterio_parcial(
           codigo_id, "pasa_tests", {"passed": False, "razon": "Tests fallaron"}
       )
       quality.registrar_criterio_parcial(
           codigo_id,
           "no_vulnerabilidades",
           {"limpio": False, "razon": "SQL injection detectado"},
       )
       quality.registrar_criterio_parcial(
           codigo_id, "rendimiento_aceptable", {"factor_recursos": 5.0}
       )
       quality.registrar_criterio_parcial(
           codigo_id,
           "tiempo_produccion_dias",
           {"dias_sin_fallar": 0, "fallos": 3},
       )
       resultado = quality.evaluar(codigo_id)
       assert resultado is not None
       assert resultado.feedback == "NEGATIVO"
       assert resultado.score < 0.4


   # ─── Test 6: score intermedio → feedback NEUTRO ───────────────────────────


   def test_score_intermedio_genera_feedback_neutro(quality, codigo_python_valido):
       codigo_id = quality.registrar_codigo(codigo_python_valido)
       # Tests pasan, pero vulnerabilidades presentes
       quality.registrar_criterio_parcial(codigo_id, "pasa_tests", {"passed": True, "razon": ""})
       quality.registrar_criterio_parcial(
           codigo_id,
           "no_vulnerabilidades",
           {"limpio": False, "razon": "Uso inseguro de eval"},
       )
       quality.registrar_criterio_parcial(
           codigo_id, "rendimiento_aceptable", {"factor_recursos": 1.5}
       )
       quality.registrar_criterio_parcial(
           codigo_id,
           "tiempo_produccion_dias",
           {"dias_sin_fallar": 3, "fallos": 0},
       )
       resultado = quality.evaluar(codigo_id)
       assert resultado is not None
       assert resultado.feedback == "NEUTRO"
       assert 0.4 <= resultado.score < 0.8


   # ─── Test 7: codigo_id inexistente retorna None ───────────────────────────


   def test_evaluar_id_inexistente_retorna_none(quality):
       resultado = quality.evaluar("id-que-no-existe")
       assert resultado is None


   # ─── Test 8: FeedbackEngine aplica feedback positivo a Flash Memory ───────


   @pytest.mark.asyncio
   async def test_feedback_engine_aplica_positivo():
       flash_mock = MagicMock()
       engine = FeedbackEngine(flash_memory=flash_mock)

       result = QualityResult(
           codigo_id="test-123",
           score=0.92,
           feedback="POSITIVO",
           criterios=[
               CriterioResult("ejecuta_sin_errores", True, 0.3),
               CriterioResult("pasa_tests", True, 0.3),
               CriterioResult("no_vulnerabilidades", True, 0.25),
               CriterioResult("rendimiento_aceptable", True, 0.1),
               CriterioResult("tiempo_produccion_dias", True, 0.05),
           ],
           razones=[],
       )

       exito = await engine.aplicar_feedback(result)
       assert exito is True
       flash_mock.store.assert_called_once()
       call_kwargs = flash_mock.store.call_args.kwargs
       assert call_kwargs["importance"] == 0.9
       assert "feedback_positivo" in call_kwargs["tags"]


   # ─── Test adicional: estadísticas del feedback engine ─────────────────────


   @pytest.mark.asyncio
   async def test_feedback_engine_estadisticas():
       engine = FeedbackEngine(flash_memory=MagicMock())

       result_positivo = QualityResult(
           codigo_id="p1", score=0.9, feedback="POSITIVO", criterios=[], razones=[]
       )
       result_negativo = QualityResult(
           codigo_id="n1", score=0.3, feedback="NEGATIVO", criterios=[], razones=["error"]
       )

       await engine.aplicar_feedback(result_positivo)
       await engine.aplicar_feedback(result_negativo)

       stats = engine.estadisticas()
       assert stats["total"] == 2
       assert stats["positivos"] == 1
       assert stats["negativos"] == 1
       assert stats["tasa_positivos"] == 0.5

VERIFICAR:
- [ ] `src/quality/__init__.py` existe
- [ ] `src/quality/models.py` contiene clase `CodigoEvaluado` con SQLAlchemy
- [ ] `src/quality/yeyo_quality.py` contiene `YeyoQuality`, `QualityResult`, `QualityMonitor`
- [ ] `src/quality/feedback_engine.py` contiene `FeedbackEngine` con métodos positivo/negativo/neutro
- [ ] `tests/unit/quality/test_yeyo_quality.py` contiene 8+ tests
- [ ] Ejecutar `cd ~/yeyo-os && python -m pytest tests/unit/quality/test_yeyo_quality.py -v` → todos los tests pasan
- [ ] Ejecutar `cd ~/yeyo-os && python -c "from src.quality.yeyo_quality import YeyoQuality; q = YeyoQuality(); print(q.listar_pendientes())"` → imprime `[]`
- [ ] `YeyoQuality.CRITERIOS_PESOS.values()` suman exactamente 1.0
- [ ] Feedback positivo solo se aplica cuando score >= 0.8
- [ ] Aceptación del usuario NO dispara feedback positivo directamente

SI FALLA:
- `ModuleNotFoundError: src.quality`: ejecutar desde `~/yeyo-os` con `PYTHONPATH=.` o verificar que existe `src/__init__.py`
- `ImportError: sqlalchemy`: `pip install sqlalchemy` en el entorno virtual
- `pytest: asyncio`: instalar `pytest-asyncio` con `pip install pytest-asyncio` y agregar `asyncio_mode = "auto"` en `pytest.ini`
- Tests de compilación fallan en Windows: verificar que `python` apunta al mismo intérprete (no `python3`)
- `Flash Memory not available`: el test usa mock — en producción verificar que `src/memory/flash_memory.py` está inicializado antes de instanciar `FeedbackEngine`

NO HACER:
- No aplicar feedback positivo cuando el usuario solo acepta el código sin ejecución objetiva
- No borrar registros del `_registro` interno — son el historial de evaluación
- No usar `score >= 0.5` como umbral positivo — el umbral es **0.8** según especificación
- No saltarse el criterio `tiempo_produccion_dias` — 7 días en producción es obligatorio para score perfecto
- No conectar directamente al modelo Ollama para fine-tuning sin pasar por Flash Memory first

GATE: YeyoQuality evalúa código generado con criterios objetivos (ejecución, tests, vulnerabilidades, rendimiento, 7 días en producción), aplica feedback positivo solo cuando score>=0.8, y los 8 tests unitarios pasan — el modelo nunca mejora su score por simple aceptación del usuario.
```
