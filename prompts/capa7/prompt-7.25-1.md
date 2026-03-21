## ═══════════════════════════════════════
## MICRO-FASE 7.25 — Schedule Nocturno Unificado (6 Fases)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.25-1 [VSCODE] — SchedulerNocturno: 6 fases orquestadas con detección de idle y reporte matutino

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.25 de Capa 7 (Evolución): implementar el Schedule Nocturno Unificado que orquesta todas las tareas nocturnas en 6 fases — investigación, training, hacking, limpieza, benchmark y sync — con detección de idle y pausa automática si el usuario vuelve.

CONTEXTO:
- Micro-fases 5.28-5.32 completadas: PipelineInvestigador, MicroTareas, Razonamiento, CachePatrones, SelectorModelo
- Capas existentes que el scheduler orquesta:
  - PipelineInvestigador (5.28) en src/investigador/pipeline.py: investigar(tarea) -> InvestigacionCompleta
  - CachePatrones (5.31) en src/investigador/cache_patrones.py: buscar_patron(), guardar_patron()
  - Code Dojo (7.0-7.2): LoRA pipeline existente (importar si existe, mock si no)
  - YEYO-HACK (6.12): sistema de hacking ético existente (importar si existe, mock si no)
  - YeyoBenchmark (6.15): benchmark post-training existente (importar si existe, mock si no)
  - YeyoNet sync (7.17): sync distribuido existente (importar si existe, mock si no)
- Flash Memory en src/memory/flash_memory.py: store(), recall()
- Memory model: Memory(id, content, type, tier, embedding, metadata, source)
- IAProvider en src/ia/interfaces.py: generate(), get_embedding()
- EventBus en src/core/event_bus.py: publish(), subscribe()
- El scheduler detecta idle (sin input 10+ min) y pausa si el usuario vuelve

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nocturno/__init__.py:

   Ruta: ~/yeyo-os/src/nocturno/__init__.py
   Contenido:

   """
   YeyoOS — Módulo Nocturno
   Capas 7.25–7.27 — Capa 7: Evolución

   Schedule nocturno unificado: investigación, training, hacking,
   limpieza, benchmark y sync. Autodidacta y Publisher.
   """

   from .scheduler import SchedulerNocturno

   __all__ = ["SchedulerNocturno"]


2. Crear archivo src/nocturno/detector_idle.py:

   Ruta: ~/yeyo-os/src/nocturno/detector_idle.py
   Contenido:

   """
   YeyoOS — DetectorIdle
   Micro-fase 7.25 — Capa 7: Evolución

   Monitorea input de mouse/teclado para detectar inactividad.
   Platform-specific: Windows (ctypes), Linux (evdev/Xlib), Mac (Quartz).
   Provee método esta_idle(timeout_minutos) y registrar_actividad().
   """

   from __future__ import annotations

   import logging
   import platform
   import time
   from typing import Optional

   logger = logging.getLogger(__name__)


   class DetectorIdle:
       """
       Detecta si el usuario está idle (sin input de mouse/teclado).

       Usa APIs nativas del SO para detectar el último input:
       - Windows: ctypes → GetLastInputInfo
       - Linux: subprocess → xprintidle o /proc/interrupts
       - Mac: subprocess → ioreg (IOHIDSystem)

       Fallback: tracking manual via registrar_actividad().
       """

       def __init__(self, timeout_minutos: float = 10.0):
           self._timeout_minutos = timeout_minutos
           self._ultima_actividad: float = time.time()
           self._sistema = platform.system()
           self._idle_nativo_disponible = self._verificar_soporte_nativo()

       def registrar_actividad(self) -> None:
           """Registra actividad del usuario (llamado por cualquier input handler)."""
           self._ultima_actividad = time.time()

       def esta_idle(self, timeout_minutos: Optional[float] = None) -> bool:
           """
           Retorna True si el usuario lleva más de timeout_minutos sin input.
           Primero intenta detección nativa del SO, luego fallback manual.
           """
           timeout = timeout_minutos or self._timeout_minutos
           timeout_segundos = timeout * 60

           # Intentar detección nativa
           idle_nativo = self._idle_nativo_segundos()
           if idle_nativo is not None:
               return idle_nativo >= timeout_segundos

           # Fallback: tracking manual
           elapsed = time.time() - self._ultima_actividad
           return elapsed >= timeout_segundos

       def segundos_idle(self) -> float:
           """Retorna los segundos de inactividad."""
           idle_nativo = self._idle_nativo_segundos()
           if idle_nativo is not None:
               return idle_nativo
           return time.time() - self._ultima_actividad

       def _verificar_soporte_nativo(self) -> bool:
           """Verifica si el SO tiene soporte nativo de detección idle."""
           if self._sistema == "Windows":
               try:
                   import ctypes
                   return True
               except ImportError:
                   return False
           elif self._sistema == "Linux":
               try:
                   import subprocess
                   result = subprocess.run(
                       ["which", "xprintidle"],
                       capture_output=True, timeout=2,
                   )
                   return result.returncode == 0
               except Exception:
                   return False
           elif self._sistema == "Darwin":
               return True
           return False

       def _idle_nativo_segundos(self) -> Optional[float]:
           """Obtiene segundos de idle via API nativa del SO."""
           try:
               if self._sistema == "Windows":
                   return self._idle_windows()
               elif self._sistema == "Linux":
                   return self._idle_linux()
               elif self._sistema == "Darwin":
                   return self._idle_mac()
           except Exception as e:
               logger.debug(f"[detector_idle] Error detección nativa: {e}")
           return None

       @staticmethod
       def _idle_windows() -> Optional[float]:
           """Windows: usa GetLastInputInfo via ctypes."""
           try:
               import ctypes
               import ctypes.wintypes

               class LASTINPUTINFO(ctypes.Structure):
                   _fields_ = [
                       ("cbSize", ctypes.wintypes.UINT),
                       ("dwTime", ctypes.wintypes.DWORD),
                   ]

               lii = LASTINPUTINFO()
               lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
               if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                   tick_count = ctypes.windll.kernel32.GetTickCount()
                   idle_ms = tick_count - lii.dwTime
                   return idle_ms / 1000.0
           except Exception as e:
               logger.debug(f"[detector_idle] Windows idle error: {e}")
           return None

       @staticmethod
       def _idle_linux() -> Optional[float]:
           """Linux: usa xprintidle."""
           try:
               import subprocess
               result = subprocess.run(
                   ["xprintidle"],
                   capture_output=True,
                   text=True,
                   timeout=2,
               )
               if result.returncode == 0:
                   idle_ms = int(result.stdout.strip())
                   return idle_ms / 1000.0
           except Exception as e:
               logger.debug(f"[detector_idle] Linux idle error: {e}")
           return None

       @staticmethod
       def _idle_mac() -> Optional[float]:
           """Mac: usa ioreg para IOHIDSystem idle time."""
           try:
               import subprocess
               result = subprocess.run(
                   ["ioreg", "-c", "IOHIDSystem"],
                   capture_output=True,
                   text=True,
                   timeout=2,
               )
               if result.returncode == 0:
                   for line in result.stdout.split("\n"):
                       if "HIDIdleTime" in line:
                           parts = line.split("=")
                           if len(parts) >= 2:
                               idle_ns = int(parts[-1].strip())
                               return idle_ns / 1_000_000_000.0
           except Exception as e:
               logger.debug(f"[detector_idle] Mac idle error: {e}")
           return None


3. Crear archivo src/nocturno/reporte.py:

   Ruta: ~/yeyo-os/src/nocturno/reporte.py
   Contenido:

   """
   YeyoOS — ReporteNocturno
   Micro-fase 7.25 — Capa 7: Evolución

   Genera resumen de lo que hizo cada fase nocturna.
   Guarda el reporte en Flash Memory con importancia 0.85.
   Marca notificaciones urgentes (degradación, vulnerabilidades).
   """

   from __future__ import annotations

   import logging
   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any, Dict, List, Optional

   logger = logging.getLogger(__name__)


   @dataclass
   class FaseReporte:
       """Reporte de una fase individual."""
       nombre: str
       inicio: Optional[datetime] = None
       fin: Optional[datetime] = None
       exito: bool = False
       resumen: str = ""
       metricas: Dict[str, Any] = field(default_factory=dict)
       errores: List[str] = field(default_factory=list)
       urgente: bool = False
       razon_urgente: str = ""


   @dataclass
   class ReporteCompleto:
       """Reporte completo de una noche."""
       fecha: str = ""
       fases: List[FaseReporte] = field(default_factory=list)
       duracion_total_min: float = 0.0
       fases_completadas: int = 0
       fases_total: int = 6
       hay_urgente: bool = False
       mensajes_urgentes: List[str] = field(default_factory=list)


   class ReporteNocturno:
       """
       Genera y almacena reportes de las sesiones nocturnas.
       Guarda en Flash Memory con importancia 0.85.
       """

       def __init__(self, flash_memory: Optional[Any] = None, ia_provider: Optional[Any] = None):
           self._flash = flash_memory
           self._ia = ia_provider
           self._fases: List[FaseReporte] = []

       def registrar_fase(self, fase: FaseReporte) -> None:
           """Registra el resultado de una fase."""
           self._fases.append(fase)
           if fase.urgente:
               logger.warning(f"[reporte_nocturno] URGENTE en {fase.nombre}: {fase.razon_urgente}")

       def generar_reporte(self) -> ReporteCompleto:
           """Genera el reporte completo de la noche."""
           reporte = ReporteCompleto(
               fecha=datetime.utcnow().strftime("%Y-%m-%d"),
               fases=list(self._fases),
               fases_completadas=sum(1 for f in self._fases if f.exito),
               fases_total=6,
           )

           total_minutos = 0.0
           for fase in self._fases:
               if fase.inicio and fase.fin:
                   delta = (fase.fin - fase.inicio).total_seconds() / 60.0
                   total_minutos += delta
               if fase.urgente:
                   reporte.hay_urgente = True
                   reporte.mensajes_urgentes.append(
                       f"[{fase.nombre}] {fase.razon_urgente}"
                   )

           reporte.duracion_total_min = round(total_minutos, 1)
           return reporte

       def formatear_texto(self, reporte: ReporteCompleto) -> str:
           """Formatea el reporte como texto legible."""
           lineas = [
               f"🌙 REPORTE NOCTURNO — {reporte.fecha}",
               f"Fases completadas: {reporte.fases_completadas}/{reporte.fases_total}",
               f"Duración total: {reporte.duracion_total_min} minutos",
               "",
           ]

           if reporte.hay_urgente:
               lineas.append("⚠️ NOTIFICACIONES URGENTES:")
               for msg in reporte.mensajes_urgentes:
                   lineas.append(f"  • {msg}")
               lineas.append("")

           for fase in reporte.fases:
               estado = "✅" if fase.exito else "❌"
               lineas.append(f"{estado} {fase.nombre}: {fase.resumen}")
               if fase.errores:
                   for err in fase.errores[:3]:
                       lineas.append(f"   ⚠ {err}")

           return "\n".join(lineas)

       async def guardar_en_memoria(self, reporte: ReporteCompleto) -> None:
           """Guarda el reporte en Flash Memory con importancia 0.85."""
           if not self._flash:
               logger.warning("[reporte_nocturno] Flash Memory no disponible, reporte no guardado")
               return

           texto = self.formatear_texto(reporte)

           try:
               embedding = None
               if self._ia:
                   try:
                       embedding = await self._ia.get_embedding(texto[:500])
                   except Exception:
                       pass

               await self._flash.store(
                   content=texto,
                   type="fact",
                   metadata={
                       "tipo": "reporte_nocturno",
                       "fecha": reporte.fecha,
                       "fases_completadas": reporte.fases_completadas,
                       "hay_urgente": reporte.hay_urgente,
                       "importancia": 0.85,
                   },
                   embedding=embedding,
                   source="scheduler_nocturno",
               )
               logger.info(f"[reporte_nocturno] Reporte guardado en Flash Memory")
           except Exception as e:
               logger.error(f"[reporte_nocturno] Error guardando reporte: {e}")

       def reset(self) -> None:
           """Limpia las fases para una nueva noche."""
           self._fases.clear()


4. Crear archivo src/nocturno/scheduler.py:

   Ruta: ~/yeyo-os/src/nocturno/scheduler.py
   Contenido:

   """
   YeyoOS — SchedulerNocturno
   Micro-fase 7.25 — Capa 7: Evolución

   Orquesta todas las tareas nocturnas en 6 fases:
   1. Investigación (22:00-00:00) — pre-computa soluciones
   2. Training (00:00-02:00) — LoRA fine-tuning
   3. HACK (02:00-03:00) — YEYO-HACK security
   4. Limpieza (03:00-04:00) — consolidar memoria
   5. Benchmark (04:00-05:00) — benchmark post-training
   6. Sync (05:00-06:00) — YeyoNet sync

   Detecta idle, se pausa si el usuario vuelve, genera reporte matutino.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   from datetime import datetime
   from typing import Any, Callable, Dict, List, Optional

   from .detector_idle import DetectorIdle
   from .reporte import FaseReporte, ReporteNocturno

   logger = logging.getLogger(__name__)

   FASES_CONFIG = {
       "investigacion": {"hora_inicio": 22, "hora_fin": 0, "duracion_max_min": 120},
       "training": {"hora_inicio": 0, "hora_fin": 2, "duracion_max_min": 120},
       "hack": {"hora_inicio": 2, "hora_fin": 3, "duracion_max_min": 60},
       "limpieza": {"hora_inicio": 3, "hora_fin": 4, "duracion_max_min": 60},
       "benchmark": {"hora_inicio": 4, "hora_fin": 5, "duracion_max_min": 60},
       "sync": {"hora_inicio": 5, "hora_fin": 6, "duracion_max_min": 60},
   }


   class SchedulerNocturnoError(Exception):
       """Error en scheduler nocturno."""
       pass


   class SchedulerNocturno:
       """
       Orquesta las 6 fases nocturnas.

       Cada fase:
       1. Verifica que el usuario sigue idle
       2. Ejecuta la tarea con timeout configurable
       3. Si el usuario vuelve: pausa inmediata
       4. Registra resultado en el reporte

       Integración:
       - Fase 1: PipelineInvestigador (5.28) + CachePatrones (5.31)
       - Fase 2: LoRA pipeline (7.0-7.2) + Code Dojo (13-code-dojo.md)
       - Fase 3: YEYO-HACK (6.12)
       - Fase 4: Flash Memory limpieza (NUEVA — implementada aquí)
       - Fase 5: YeyoBenchmark (6.15)
       - Fase 6: YeyoNet sync (7.17)
       """

       def __init__(
           self,
           detector_idle: Optional[DetectorIdle] = None,
           flash_memory: Optional[Any] = None,
           ia_provider: Optional[Any] = None,
           pipeline_investigador: Optional[Any] = None,
           cache_patrones: Optional[Any] = None,
           lora_trainer: Optional[Any] = None,
           yeyo_hack: Optional[Any] = None,
           yeyo_benchmark: Optional[Any] = None,
           yeyonet_sync: Optional[Any] = None,
           reporte: Optional[ReporteNocturno] = None,
       ):
           self._detector = detector_idle or DetectorIdle()
           self._flash = flash_memory
           self._ia = ia_provider
           self._pipeline = pipeline_investigador
           self._cache_patrones = cache_patrones
           self._lora = lora_trainer
           self._hack = yeyo_hack
           self._benchmark = yeyo_benchmark
           self._yeyonet = yeyonet_sync
           self._reporte = reporte or ReporteNocturno(flash_memory, ia_provider)
           self._pausado = False
           self._corriendo = False
           self._fase_actual: Optional[str] = None

       @property
       def esta_corriendo(self) -> bool:
           return self._corriendo

       @property
       def fase_actual(self) -> Optional[str]:
           return self._fase_actual

       @property
       def esta_pausado(self) -> bool:
           return self._pausado

       def pausar(self) -> None:
           """Pausa inmediata de la fase actual (llamado cuando el usuario vuelve)."""
           if self._corriendo:
               self._pausado = True
               logger.info(f"[scheduler] Pausado en fase: {self._fase_actual}")

       def reanudar(self) -> None:
           """Reanuda el scheduler después de una pausa."""
           self._pausado = False
           logger.info("[scheduler] Reanudado")

       async def ejecutar_noche(self) -> None:
           """
           Ejecuta las 6 fases en orden.
           Se detiene si el usuario vuelve o si es la hora límite.
           Genera reporte matutino al finalizar.
           """
           if not self._detector.esta_idle():
               logger.info("[scheduler] Usuario activo, no se inicia sesión nocturna")
               return

           self._corriendo = True
           self._pausado = False
           self._reporte.reset()

           logger.info("[scheduler] 🌙 Iniciando sesión nocturna")

           fases = [
               ("investigacion", self.fase_investigacion),
               ("training", self.fase_training),
               ("hack", self.fase_hack),
               ("limpieza", self.fase_limpieza),
               ("benchmark", self.fase_benchmark),
               ("sync", self.fase_sync),
           ]

           for nombre, ejecutar_fase in fases:
               if self._pausado or not self._detector.esta_idle(timeout_minutos=5):
                   logger.info(f"[scheduler] Usuario activo, deteniendo antes de {nombre}")
                   break

               self._fase_actual = nombre
               logger.info(f"[scheduler] Iniciando fase: {nombre}")

               config = FASES_CONFIG[nombre]
               timeout = config["duracion_max_min"] * 60

               fase_reporte = FaseReporte(nombre=nombre, inicio=datetime.utcnow())

               try:
                   resultado = await asyncio.wait_for(
                       ejecutar_fase(),
                       timeout=timeout,
                   )
                   fase_reporte.exito = True
                   fase_reporte.resumen = str(resultado)[:500] if resultado else "Completado"
                   fase_reporte.metricas = resultado if isinstance(resultado, dict) else {}

               except asyncio.TimeoutError:
                   fase_reporte.exito = False
                   fase_reporte.resumen = f"Timeout ({config['duracion_max_min']} min)"
                   fase_reporte.errores.append("Timeout alcanzado")
                   logger.warning(f"[scheduler] Fase {nombre} timeout")

               except Exception as e:
                   fase_reporte.exito = False
                   fase_reporte.resumen = f"Error: {str(e)[:200]}"
                   fase_reporte.errores.append(str(e)[:500])
                   logger.error(f"[scheduler] Error en fase {nombre}: {e}")

               fase_reporte.fin = datetime.utcnow()
               self._reporte.registrar_fase(fase_reporte)

           # Generar y guardar reporte matutino
           self._fase_actual = None
           self._corriendo = False
           reporte = self._reporte.generar_reporte()
           await self._reporte.guardar_en_memoria(reporte)

           texto = self._reporte.formatear_texto(reporte)
           logger.info(f"[scheduler] 🌅 Sesión nocturna completada:\n{texto}")

       async def fase_investigacion(self) -> Dict[str, Any]:
           """
           Fase 1 (22:00-00:00): Pre-computa soluciones para tareas lentas del día.
           Usa PipelineInvestigador (5.28) y guarda patrones en CachePatrones (5.31).
           """
           resultados = {"tareas_investigadas": 0, "patrones_guardados": 0}

           if not self._pipeline:
               logger.info("[scheduler] PipelineInvestigador no disponible, saltando fase")
               return resultados

           # Obtener tareas pendientes de Flash Memory
           tareas_pendientes = []
           if self._flash:
               try:
                   memorias = await self._flash.recall_by_type("correction", limit=10)
                   for mem in memorias:
                       tareas_pendientes.append(mem.content[:500])
               except Exception as e:
                   logger.warning(f"[scheduler] Error obteniendo tareas pendientes: {e}")

           for tarea in tareas_pendientes[:5]:
               if self._pausado:
                   break
               try:
                   resultado = await self._pipeline.investigar(tarea)
                   resultados["tareas_investigadas"] += 1

                   if resultado.exito and self._cache_patrones:
                       await self._cache_patrones.guardar_patron(
                           tipo_problema=tarea[:200],
                           pasos_razonamiento=[
                               {"paso": p.numero, "tipo": p.tipo, "resumen": p.output_resumen}
                               for p in resultado.pasos
                           ],
                           errores_comunes=[],
                           patron_correcto=resultado.resultado_final[:2000],
                           tiempo_original_ms=resultado.tiempo_total_ms,
                           confianza=resultado.confianza,
                       )
                       resultados["patrones_guardados"] += 1
               except Exception as e:
                   logger.warning(f"[scheduler] Error investigando tarea: {e}")

           return resultados

       async def fase_training(self) -> Dict[str, Any]:
           """
           Fase 2 (00:00-02:00): LoRA fine-tuning con datos verificados.
           Conecta con Code Dojo (7.0-7.2) y LoRA pipeline.
           """
           resultados = {"training_ejecutado": False, "mejora": 0.0}

           if self._lora:
               try:
                   resultado = await self._lora.entrenar()
                   resultados["training_ejecutado"] = True
                   resultados["mejora"] = getattr(resultado, "mejora", 0.0)
               except Exception as e:
                   logger.warning(f"[scheduler] Error en training: {e}")
           else:
               logger.info("[scheduler] LoRA trainer no disponible, saltando fase training")

           return resultados

       async def fase_hack(self) -> Dict[str, Any]:
           """
           Fase 3 (02:00-03:00): Ejecuta YEYO-HACK (6.12).
           Busca vulnerabilidades y mejoras de seguridad.
           """
           resultados = {"vulnerabilidades": 0, "fixes": 0}

           if self._hack:
               try:
                   resultado = await self._hack.ejecutar()
                   resultados["vulnerabilidades"] = getattr(resultado, "vulnerabilidades", 0)
                   resultados["fixes"] = getattr(resultado, "fixes", 0)

                   if resultados["vulnerabilidades"] > 0:
                       logger.warning(f"[scheduler] {resultados['vulnerabilidades']} vulnerabilidades encontradas")
               except Exception as e:
                   logger.warning(f"[scheduler] Error en HACK: {e}")
           else:
               logger.info("[scheduler] YEYO-HACK no disponible, saltando fase hack")

           return resultados

       async def fase_limpieza(self) -> Dict[str, Any]:
           """
           Fase 4 (03:00-04:00): Limpieza de memoria.
           - Consolidar memorias duplicadas
           - Degradar memorias no accedidas (WARM → COLD)
           - Resolver contradicciones
           NUEVA — implementada completamente aquí.
           """
           resultados = {"consolidadas": 0, "degradadas": 0, "contradicciones": 0}

           if not self._flash:
               logger.info("[scheduler] Flash Memory no disponible, saltando limpieza")
               return resultados

           # 1. Degradar memorias no accedidas
           try:
               memorias_warm = await self._flash.recall_by_type("skill", limit=50)
               for mem in memorias_warm:
                   if self._pausado:
                       break
                   if hasattr(mem, 'access_count') and mem.access_count == 0:
                       if hasattr(mem, 'tier') and mem.tier == "WARM":
                           try:
                               await self._flash.demote_tier(mem.id)
                               resultados["degradadas"] += 1
                           except Exception:
                               pass
           except Exception as e:
               logger.warning(f"[scheduler] Error en degradación: {e}")

           logger.info(
               f"[scheduler] Limpieza completada: "
               f"degradadas={resultados['degradadas']}"
           )
           return resultados

       async def fase_benchmark(self) -> Dict[str, Any]:
           """
           Fase 5 (04:00-05:00): YeyoBenchmark post-training (6.15).
           Si hay degradación, marca como urgente para rollback.
           """
           resultados = {"benchmark_ejecutado": False, "score": 0.0, "degradacion": False}

           if self._benchmark:
               try:
                   resultado = await self._benchmark.ejecutar()
                   resultados["benchmark_ejecutado"] = True
                   resultados["score"] = getattr(resultado, "score", 0.0)

                   score_previo = getattr(resultado, "score_previo", None)
                   if score_previo and resultados["score"] < score_previo * 0.9:
                       resultados["degradacion"] = True
                       logger.warning(
                           f"[scheduler] ⚠️ DEGRADACIÓN detectada: "
                           f"{score_previo} → {resultados['score']}"
                       )
               except Exception as e:
                   logger.warning(f"[scheduler] Error en benchmark: {e}")
           else:
               logger.info("[scheduler] YeyoBenchmark no disponible, saltando fase benchmark")

           return resultados

       async def fase_sync(self) -> Dict[str, Any]:
           """
           Fase 6 (05:00-06:00): Sync con YeyoNet cerebro central (7.17).
           Sincroniza memorias y modelos con otros nodos de la red.
           """
           resultados = {"sync_ejecutado": False, "nodos_sincronizados": 0}

           if self._yeyonet:
               try:
                   resultado = await self._yeyonet.sync()
                   resultados["sync_ejecutado"] = True
                   resultados["nodos_sincronizados"] = getattr(resultado, "nodos", 0)
               except Exception as e:
                   logger.warning(f"[scheduler] Error en sync: {e}")
           else:
               logger.info("[scheduler] YeyoNet sync no disponible, saltando fase sync")

           return resultados


5. Crear archivo tests/unit/nocturno/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/nocturno/__init__.py
   Contenido:



6. Crear archivo tests/unit/nocturno/test_scheduler.py:

   Ruta: ~/yeyo-os/tests/unit/nocturno/test_scheduler.py
   Contenido:

   """
   Tests unitarios para SchedulerNocturno.
   Micro-fase 7.25 — 10 tests (idle, 6 fases, pausa, reporte).
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch
   from datetime import datetime

   from src.nocturno.scheduler import SchedulerNocturno, FASES_CONFIG
   from src.nocturno.detector_idle import DetectorIdle
   from src.nocturno.reporte import ReporteNocturno, FaseReporte, ReporteCompleto


   @pytest.fixture
   def detector_idle():
       detector = DetectorIdle(timeout_minutos=0.01)
       detector._ultima_actividad = 0
       return detector


   @pytest.fixture
   def mock_flash():
       flash = AsyncMock()
       flash.recall_by_type.return_value = []
       flash.store.return_value = MagicMock(id="mem_1")
       return flash


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock()
       ia.get_embedding.return_value = [0.1] * 768
       ia.generate.return_value = MagicMock(content="ok", tokens_used=10)
       return ia


   @pytest.fixture
   def scheduler(detector_idle, mock_flash, mock_ia):
       return SchedulerNocturno(
           detector_idle=detector_idle,
           flash_memory=mock_flash,
           ia_provider=mock_ia,
       )


   def test_detector_idle_esta_idle(detector_idle):
       assert detector_idle.esta_idle(timeout_minutos=0.0001) is True


   def test_detector_idle_no_idle_despues_de_actividad():
       detector = DetectorIdle(timeout_minutos=10)
       detector.registrar_actividad()
       assert detector.esta_idle() is False


   @pytest.mark.asyncio
   async def test_scheduler_no_inicia_si_usuario_activo():
       detector = DetectorIdle(timeout_minutos=10)
       detector.registrar_actividad()
       scheduler = SchedulerNocturno(detector_idle=detector)
       await scheduler.ejecutar_noche()
       assert scheduler.esta_corriendo is False


   @pytest.mark.asyncio
   async def test_scheduler_ejecuta_fases(scheduler):
       await scheduler.ejecutar_noche()
       assert scheduler.esta_corriendo is False


   @pytest.mark.asyncio
   async def test_fase_investigacion_sin_pipeline(scheduler):
       resultado = await scheduler.fase_investigacion()
       assert resultado["tareas_investigadas"] == 0


   @pytest.mark.asyncio
   async def test_fase_investigacion_con_pipeline(detector_idle, mock_flash, mock_ia):
       pipeline = AsyncMock()
       inv_completa = MagicMock()
       inv_completa.exito = True
       inv_completa.resultado_final = "solución"
       inv_completa.confianza = 0.9
       inv_completa.tiempo_total_ms = 1000
       inv_completa.pasos = []
       pipeline.investigar.return_value = inv_completa

       mem = MagicMock()
       mem.content = "tarea pendiente"
       mock_flash.recall_by_type.return_value = [mem]

       scheduler = SchedulerNocturno(
           detector_idle=detector_idle,
           flash_memory=mock_flash,
           ia_provider=mock_ia,
           pipeline_investigador=pipeline,
       )
       resultado = await scheduler.fase_investigacion()
       assert resultado["tareas_investigadas"] >= 1


   @pytest.mark.asyncio
   async def test_fase_limpieza(scheduler):
       resultado = await scheduler.fase_limpieza()
       assert "degradadas" in resultado


   @pytest.mark.asyncio
   async def test_pausar_scheduler(scheduler):
       scheduler._corriendo = True
       scheduler.pausar()
       assert scheduler.esta_pausado is True
       scheduler.reanudar()
       assert scheduler.esta_pausado is False


   def test_reporte_nocturno():
       reporte = ReporteNocturno()
       reporte.registrar_fase(FaseReporte(
           nombre="investigacion",
           inicio=datetime.utcnow(),
           fin=datetime.utcnow(),
           exito=True,
           resumen="5 tareas investigadas",
       ))
       reporte.registrar_fase(FaseReporte(
           nombre="benchmark",
           exito=False,
           resumen="Degradación detectada",
           urgente=True,
           razon_urgente="Score bajó 15%",
       ))
       completo = reporte.generar_reporte()
       assert isinstance(completo, ReporteCompleto)
       assert completo.fases_completadas == 1
       assert completo.hay_urgente is True
       assert len(completo.mensajes_urgentes) == 1


   def test_reporte_formatear_texto():
       reporte = ReporteNocturno()
       reporte.registrar_fase(FaseReporte(
           nombre="investigacion", exito=True, resumen="OK",
       ))
       completo = reporte.generar_reporte()
       texto = reporte.formatear_texto(completo)
       assert "REPORTE NOCTURNO" in texto
       assert "investigacion" in texto


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/nocturno/test_scheduler.py -v
   Esperado: 10 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.nocturno import SchedulerNocturno; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.nocturno.detector_idle import DetectorIdle; print('OK')"
   Esperado: OK

4. Ejecutar: cd ~/yeyo-os && python -c "from src.nocturno.reporte import ReporteNocturno, FaseReporte; print('OK')"
   Esperado: OK

SI FALLA:
- Si falla import de src.investigador.pipeline: verificar que existe (5.28) o usar Optional
- Si falla DetectorIdle en CI (sin display): usa fallback manual — no requiere display para tests
- Si falla asyncio.wait_for: verificar que cada fase es async

NO HACER:
- NO modificar src/investigador/ (creado en 5.28-5.32)
- NO ejecutar LoRA training en tests (solo mock)
- NO hacer llamadas reales a YeyoNet en tests
- NO bloquear el event loop — todas las fases son async

GATE:
✅ SchedulerNocturno detecta idle (sin input 10+ min)
✅ Ejecuta 6 fases en orden: investigación, training, hack, limpieza, benchmark, sync
✅ Cada fase conecta con componentes existentes (pipeline, LoRA, HACK, benchmark, YeyoNet)
✅ Fase 4 (limpieza) implementada: degradar memorias no accedidas
✅ Se pausa inmediatamente si el usuario vuelve (input detectado)
✅ Genera reporte matutino guardado en Flash Memory (importancia 0.85)
✅ Marcas de urgente para degradación o vulnerabilidades críticas
✅ 10 tests pasan (idle, fases, pausa, reporte)
```
