## ═══════════════════════════════════════
## MICRO-FASE 7.26 — Autodidacta: Curriculum Dinámico Basado en Debilidades
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.26-1 [VSCODE] — YeyoAutodidacta: curriculum dinámico, ejercicios con PipelineInvestigador, NUNCA se rinde

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.26 de Capa 7 (Evolución): implementar YeyoAutodidacta que extiende Code Dojo con generación de curriculum personalizado basado en debilidades reales, ejecuta ejercicios usando PipelineInvestigador, y NUNCA se rinde.

CONTEXTO:
- Micro-fase 7.25 completada: SchedulerNocturno con 6 fases funcionando
- Autodidacta se ejecuta durante fase_investigacion del SchedulerNocturno (7.25)
- PipelineInvestigador (5.28) en src/investigador/pipeline.py:
  - investigar(tarea, lenguaje, max_resultados) -> InvestigacionCompleta
  - InvestigacionCompleta(tarea_id, pasos, resultado_final, confianza, tiempo_total_ms, exito)
- CachePatrones (5.31) en src/investigador/cache_patrones.py:
  - guardar_patron(tipo_problema, pasos, errores, patron_correcto, tiempo_ms, confianza)
  - buscar_patron(problema, threshold) -> PatronRazonamiento | None
- PatronRazonamiento en src/investigador/modelos_cache.py:
  - PatronRazonamiento(tipo_problema, errores_comunes, patron_correcto, pasos_razonamiento, confianza)
- EjecutorMicroTareas (5.29) en src/investigador/micro_tareas.py:
  - MicroTarea(prompt, input_keys, output_key, max_tokens)
  - ejecutar_cadena(tareas, datos_iniciales) -> ResultadoCadena
- IAProvider en src/ia/interfaces.py: generate(), get_embedding()
- Flash Memory en src/memory/flash_memory.py: store(), recall(), recall_by_type()
- YeyoBenchmark (6.15) existente: resultados con categorías y scores

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nocturno/modelos_autodidacta.py:

   Ruta: ~/yeyo-os/src/nocturno/modelos_autodidacta.py
   Contenido:

   """
   YeyoOS — Modelos del Autodidacta
   Micro-fase 7.26 — Capa 7: Evolución

   Dataclasses para el sistema de aprendizaje autónomo.
   """

   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from typing import Any, Dict, List, Optional


   @dataclass
   class Ejercicio:
       """Un ejercicio para que Yeyo practique."""
       id: str
       tema: str
       prompt: str
       prioridad: float = 0.5  # 0.0-1.0 (mayor = más urgente)
       razon: str = ""  # Por qué se generó este ejercicio
       criterios_exito: List[str] = field(default_factory=list)
       lenguaje: str = "python"
       categoria: str = ""  # Categoría del benchmark donde flaquea
       dificultad: float = 0.5  # 0.0-1.0


   @dataclass
   class ResultadoEjercicio:
       """Resultado de ejecutar un ejercicio."""
       ejercicio_id: str
       intentos: int = 0
       errores_cometidos: List[Dict[str, Any]] = field(default_factory=list)
       solucion_final: str = ""
       patron_aprendido: str = ""
       aplicable_a: List[str] = field(default_factory=list)
       tiempo_total_ms: int = 0
       exito: bool = False
       confianza: float = 0.0


   @dataclass
   class ResumenSesion:
       """Resumen de una sesión nocturna de autodidacta."""
       fecha: str = ""
       ejercicios_total: int = 0
       completados: int = 0
       patrones_nuevos: int = 0
       debilidades_restantes: List[str] = field(default_factory=list)
       tiempo_total_min: float = 0.0
       mejora_estimada: float = 0.0


2. Crear archivo src/nocturno/autodidacta.py:

   Ruta: ~/yeyo-os/src/nocturno/autodidacta.py
   Contenido:

   """
   YeyoOS — YeyoAutodidacta
   Micro-fase 7.26 — Capa 7: Evolución

   Sistema de aprendizaje autónomo que:
   1. Genera curriculum basado en debilidades reales (benchmark + tareas lentas)
   2. Ejecuta ejercicios usando PipelineInvestigador
   3. NUNCA se rinde — si falla 3 veces, descompone en sub-ejercicios
   4. Guarda patrones aprendidos en CachePatrones

   Se ejecuta durante fase_investigacion del SchedulerNocturno (7.25).
   """

   from __future__ import annotations

   import logging
   import time
   import uuid
   from datetime import datetime
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider
   from src.investigador.cache_patrones import CachePatrones
   from src.investigador.modelos import InvestigacionCompleta
   from src.investigador.pipeline import PipelineInvestigador

   from .modelos_autodidacta import Ejercicio, ResultadoEjercicio, ResumenSesion

   logger = logging.getLogger(__name__)

   MAX_INTENTOS = 3
   MAX_SUB_EJERCICIOS = 3
   EJERCICIOS_POR_NOCHE = 20
   TIMEOUT_SESION_MIN = 120  # 2 horas default

   PROMPT_GENERAR_EJERCICIO = """Genera un ejercicio de programación sobre el tema: {tema}

   Nivel de dificultad: {dificultad}
   Razón: {razon}

   El ejercicio debe:
   1. Ser concreto y resoluble
   2. Incluir criterios de éxito claros
   3. Ser relevante para un desarrollador full-stack

   Formato:
   ENUNCIADO: [descripción del ejercicio]
   CRITERIOS:
   - [criterio 1]
   - [criterio 2]
   - [criterio 3]"""

   PROMPT_DESCOMPONER = """El siguiente ejercicio falló {intentos} veces:

   Ejercicio: {prompt}
   Errores: {errores}

   Descompón en {n} sub-ejercicios más simples que juntos resuelvan el original.

   Formato:
   SUB-EJERCICIO 1: [descripción]
   SUB-EJERCICIO 2: [descripción]
   SUB-EJERCICIO 3: [descripción]"""


   class YeyoAutodidactaError(Exception):
       """Error en autodidacta."""
       pass


   class YeyoAutodidacta:
       """
       Sistema de aprendizaje autónomo que genera y ejecuta curriculum personalizado.

       Workflow:
       1. generar_curriculum() → analiza debilidades y genera 20 ejercicios
       2. ejecutar_ejercicio() → usa PipelineInvestigador, NUNCA se rinde
       3. ejecutar_sesion_nocturna() → ejecuta ejercicios en orden de prioridad

       Integración:
       - Se ejecuta durante fase_investigacion del SchedulerNocturno (7.25)
       - Usa PipelineInvestigador (5.28) para resolver ejercicios
       - Guarda patrones en CachePatrones (5.31)
       - Obtiene debilidades de YeyoBenchmark (6.15)
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           pipeline: PipelineInvestigador,
           cache_patrones: CachePatrones,
           flash_memory: Optional[Any] = None,
           benchmark_resultados: Optional[Dict[str, float]] = None,
           timeout_sesion_min: float = TIMEOUT_SESION_MIN,
       ):
           self._ia = ia_provider
           self._pipeline = pipeline
           self._cache = cache_patrones
           self._flash = flash_memory
           self._benchmark = benchmark_resultados or {}
           self._timeout_sesion = timeout_sesion_min

       async def generar_curriculum(self) -> List[Ejercicio]:
           """
           Genera curriculum personalizado basado en debilidades reales.

           Fuentes de debilidades:
           1. Categorías del benchmark < 70%
           2. Tareas del día que tardaron > 10 min
           3. Tecnologías no exploradas
           4. Tendencias tecnológicas (semanal)

           Retorna hasta 20 ejercicios priorizados.
           """
           ejercicios: List[Ejercicio] = []

           # 1. Debilidades del benchmark
           ejercicios.extend(await self._ejercicios_desde_benchmark())

           # 2. Tareas lentas del día
           ejercicios.extend(await self._ejercicios_desde_tareas_lentas())

           # 3. Tecnologías no exploradas
           ejercicios.extend(await self._ejercicios_tecnologias_nuevas())

           # 4. Tendencias (IA genera ejercicios sobre tendencias)
           ejercicios.extend(await self._ejercicios_tendencias())

           # Ordenar por prioridad descendente y limitar
           ejercicios.sort(key=lambda e: e.prioridad, reverse=True)
           ejercicios = ejercicios[:EJERCICIOS_POR_NOCHE]

           logger.info(f"[autodidacta] Curriculum generado: {len(ejercicios)} ejercicios")
           return ejercicios

       async def ejecutar_ejercicio(self, ejercicio: Ejercicio) -> ResultadoEjercicio:
           """
           Ejecuta un ejercicio usando PipelineInvestigador.
           Si falla 3 veces, descompone en sub-ejercicios.
           NUNCA se rinde — busca hasta encontrar solución.
           """
           inicio = time.perf_counter()
           resultado = ResultadoEjercicio(ejercicio_id=ejercicio.id)

           for intento in range(1, MAX_INTENTOS + 1):
               resultado.intentos = intento

               try:
                   investigacion = await self._pipeline.investigar(
                       tarea=ejercicio.prompt,
                       lenguaje=ejercicio.lenguaje,
                   )

                   if investigacion.exito and investigacion.confianza >= 0.6:
                       resultado.solucion_final = investigacion.resultado_final
                       resultado.confianza = investigacion.confianza
                       resultado.exito = True
                       resultado.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)

                       # Guardar patrón aprendido
                       await self._guardar_patron(ejercicio, resultado, investigacion)

                       logger.info(
                           f"[autodidacta] Ejercicio {ejercicio.id} resuelto en intento {intento} "
                           f"(confianza={resultado.confianza})"
                       )
                       return resultado

                   resultado.errores_cometidos.append({
                       "intento": intento,
                       "confianza": investigacion.confianza,
                       "razon": "Confianza insuficiente",
                   })

               except Exception as e:
                   resultado.errores_cometidos.append({
                       "intento": intento,
                       "error": str(e),
                   })
                   logger.warning(f"[autodidacta] Intento {intento} falló: {e}")

           # NUNCA se rinde — descomponer en sub-ejercicios
           logger.info(f"[autodidacta] Descomponiendo ejercicio {ejercicio.id} en sub-ejercicios")
           sub_resultado = await self._resolver_por_descomposicion(ejercicio, resultado)

           sub_resultado.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
           return sub_resultado

       async def ejecutar_sesion_nocturna(self) -> ResumenSesion:
           """
           Ejecuta una sesión de aprendizaje nocturna.
           Genera curriculum, ejecuta ejercicios en orden de prioridad.
           Para cuando se acaba el tiempo asignado.
           """
           inicio = time.perf_counter()
           timeout_ms = self._timeout_sesion * 60 * 1000

           curriculum = await self.generar_curriculum()

           resumen = ResumenSesion(
               fecha=datetime.utcnow().strftime("%Y-%m-%d"),
               ejercicios_total=len(curriculum),
           )

           for ejercicio in curriculum:
               elapsed_ms = (time.perf_counter() - inicio) * 1000
               if elapsed_ms >= timeout_ms:
                   logger.info("[autodidacta] Tiempo agotado, terminando sesión")
                   break

               try:
                   resultado = await self.ejecutar_ejercicio(ejercicio)

                   if resultado.exito:
                       resumen.completados += 1
                       if resultado.patron_aprendido:
                           resumen.patrones_nuevos += 1
                   else:
                       resumen.debilidades_restantes.append(ejercicio.tema)

               except Exception as e:
                   logger.error(f"[autodidacta] Error en ejercicio {ejercicio.id}: {e}")
                   resumen.debilidades_restantes.append(ejercicio.tema)

           resumen.tiempo_total_min = round((time.perf_counter() - inicio) / 60, 1)
           resumen.mejora_estimada = round(
               resumen.completados / max(resumen.ejercicios_total, 1), 2
           )

           logger.info(
               f"[autodidacta] Sesión completada: "
               f"{resumen.completados}/{resumen.ejercicios_total} ejercicios, "
               f"{resumen.patrones_nuevos} patrones nuevos, "
               f"{resumen.tiempo_total_min} min"
           )
           return resumen

       async def _ejercicios_desde_benchmark(self) -> List[Ejercicio]:
           """Genera ejercicios para categorías del benchmark < 70%."""
           ejercicios: List[Ejercicio] = []

           for categoria, score in self._benchmark.items():
               if score < 0.7:
                   dificultad = max(0.3, 1.0 - score)
                   ejercicios.append(Ejercicio(
                       id=f"bench_{uuid.uuid4().hex[:8]}",
                       tema=categoria,
                       prompt=f"Practica {categoria}: crea un ejemplo funcional con tests",
                       prioridad=1.0 - score,
                       razon=f"Benchmark score: {score:.0%} (< 70%)",
                       criterios_exito=[
                           f"Código funcional de {categoria}",
                           "Tests unitarios incluidos",
                           "Documentación clara",
                       ],
                       categoria=categoria,
                       dificultad=dificultad,
                   ))

           return ejercicios

       async def _ejercicios_desde_tareas_lentas(self) -> List[Ejercicio]:
           """Genera ejercicios basados en tareas del día que tardaron mucho."""
           ejercicios: List[Ejercicio] = []

           if self._flash:
               try:
                   memorias = await self._flash.recall_by_type("correction", limit=10)
                   for mem in memorias:
                       ejercicios.append(Ejercicio(
                           id=f"slow_{uuid.uuid4().hex[:8]}",
                           tema=mem.content[:100],
                           prompt=f"Practica resolver rápidamente: {mem.content[:300]}",
                           prioridad=0.7,
                           razon="Tarea que tardó demasiado",
                           criterios_exito=["Resolución más rápida", "Patrón claro"],
                       ))
               except Exception as e:
                   logger.debug(f"[autodidacta] Error obteniendo tareas lentas: {e}")

           return ejercicios[:5]

       async def _ejercicios_tecnologias_nuevas(self) -> List[Ejercicio]:
           """Genera ejercicios sobre tecnologías no exploradas."""
           tecnologias_objetivo = [
               "WebAssembly", "Rust para backend", "GraphQL avanzado",
               "Kubernetes operators", "Terraform IaC",
           ]

           ejercicios: List[Ejercicio] = []
           for tech in tecnologias_objetivo[:3]:
               patron = await self._cache.buscar_patron(tech, threshold=0.9)
               if not patron:
                   ejercicios.append(Ejercicio(
                       id=f"new_{uuid.uuid4().hex[:8]}",
                       tema=tech,
                       prompt=f"Explora {tech}: crea un proyecto mínimo funcional",
                       prioridad=0.4,
                       razon="Tecnología no explorada",
                       criterios_exito=[f"Proyecto funcional con {tech}", "README básico"],
                       dificultad=0.6,
                   ))

           return ejercicios

       async def _ejercicios_tendencias(self) -> List[Ejercicio]:
           """Genera ejercicios sobre tendencias tecnológicas."""
           try:
               respuesta = await self._ia.generate(
                   prompt=(
                       "Lista 3 tendencias tecnológicas relevantes para un desarrollador full-stack "
                       "en 2025. Para cada una, sugiere un ejercicio práctico.\n"
                       "Formato: TENDENCIA: [nombre] | EJERCICIO: [descripción]"
                   ),
                   system="Sé conciso. Solo tendencias relevantes y prácticas.",
                   temperature=0.5,
               )

               ejercicios: List[Ejercicio] = []
               for line in respuesta.content.split("\n"):
                   if "TENDENCIA:" in line and "EJERCICIO:" in line:
                       parts = line.split("|")
                       if len(parts) >= 2:
                           tema = parts[0].replace("TENDENCIA:", "").strip()
                           prompt = parts[1].replace("EJERCICIO:", "").strip()
                           ejercicios.append(Ejercicio(
                               id=f"trend_{uuid.uuid4().hex[:8]}",
                               tema=tema,
                               prompt=prompt,
                               prioridad=0.3,
                               razon="Tendencia tecnológica",
                               criterios_exito=["Ejercicio completado", "Patrón documentado"],
                               dificultad=0.5,
                           ))

               return ejercicios[:3]

           except Exception as e:
               logger.debug(f"[autodidacta] Error generando tendencias: {e}")
               return []

       async def _resolver_por_descomposicion(
           self,
           ejercicio: Ejercicio,
           resultado_previo: ResultadoEjercicio,
       ) -> ResultadoEjercicio:
           """
           Descompone un ejercicio fallido en sub-ejercicios más simples.
           Resuelve cada sub-ejercicio y combina los resultados.
           NUNCA se rinde.
           """
           try:
               errores_texto = "\n".join(
                   str(e) for e in resultado_previo.errores_cometidos[:3]
               )

               respuesta = await self._ia.generate(
                   prompt=PROMPT_DESCOMPONER.format(
                       intentos=resultado_previo.intentos,
                       prompt=ejercicio.prompt,
                       errores=errores_texto,
                       n=MAX_SUB_EJERCICIOS,
                   ),
                   system="Descompón en sub-ejercicios concretos y resoluble.",
                   temperature=0.3,
               )

               sub_ejercicios = self._parsear_sub_ejercicios(respuesta.content, ejercicio)

               soluciones_parciales = []
               for sub in sub_ejercicios:
                   sub_investigacion = await self._pipeline.investigar(
                       tarea=sub.prompt,
                       lenguaje=ejercicio.lenguaje,
                   )
                   if sub_investigacion.exito:
                       soluciones_parciales.append(sub_investigacion.resultado_final)

               if soluciones_parciales:
                   solucion_combinada = "\n\n".join(soluciones_parciales)
                   resultado_previo.solucion_final = solucion_combinada
                   resultado_previo.exito = True
                   resultado_previo.confianza = 0.6
                   resultado_previo.patron_aprendido = (
                       f"Descomposición: {ejercicio.tema} → {len(sub_ejercicios)} partes"
                   )

                   # Guardar patrón de descomposición
                   await self._cache.guardar_patron(
                       tipo_problema=ejercicio.tema,
                       pasos_razonamiento=[
                           {"tipo": "descomposicion", "sub": s.tema} for s in sub_ejercicios
                       ],
                       errores_comunes=resultado_previo.errores_cometidos,
                       patron_correcto=solucion_combinada[:2000],
                       tiempo_original_ms=resultado_previo.tiempo_total_ms,
                       confianza=0.6,
                       aplicable_a=[ejercicio.tema],
                   )

           except Exception as e:
               logger.error(f"[autodidacta] Error en descomposición: {e}")

           return resultado_previo

       async def _guardar_patron(
           self,
           ejercicio: Ejercicio,
           resultado: ResultadoEjercicio,
           investigacion: InvestigacionCompleta,
       ) -> None:
           """Guarda el patrón aprendido en CachePatrones."""
           try:
               patron_texto = f"Solución para: {ejercicio.tema}"
               resultado.patron_aprendido = patron_texto
               resultado.aplicable_a = [ejercicio.tema, ejercicio.categoria]

               await self._cache.guardar_patron(
                   tipo_problema=ejercicio.tema,
                   pasos_razonamiento=[
                       {"paso": p.numero, "tipo": p.tipo, "resumen": p.output_resumen}
                       for p in investigacion.pasos
                   ],
                   errores_comunes=resultado.errores_cometidos,
                   patron_correcto=resultado.solucion_final[:2000],
                   tiempo_original_ms=resultado.tiempo_total_ms,
                   confianza=resultado.confianza,
                   aplicable_a=resultado.aplicable_a,
               )
           except Exception as e:
               logger.debug(f"[autodidacta] Error guardando patrón: {e}")

       @staticmethod
       def _parsear_sub_ejercicios(texto: str, padre: Ejercicio) -> List[Ejercicio]:
           """Parsea sub-ejercicios del output del modelo."""
           ejercicios: List[Ejercicio] = []
           for line in texto.split("\n"):
               line = line.strip()
               if line.startswith("SUB-EJERCICIO") and ":" in line:
                   prompt = line.split(":", 1)[1].strip()
                   if prompt:
                       ejercicios.append(Ejercicio(
                           id=f"sub_{uuid.uuid4().hex[:8]}",
                           tema=f"Sub: {padre.tema}",
                           prompt=prompt,
                           prioridad=padre.prioridad,
                           razon=f"Descomposición de {padre.id}",
                           lenguaje=padre.lenguaje,
                           dificultad=padre.dificultad * 0.6,
                       ))
           return ejercicios[:MAX_SUB_EJERCICIOS]


3. Crear archivo tests/unit/nocturno/test_autodidacta.py:

   Ruta: ~/yeyo-os/tests/unit/nocturno/test_autodidacta.py
   Contenido:

   """
   Tests unitarios para YeyoAutodidacta.
   Micro-fase 7.26 — 8 tests.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock

   from src.nocturno.autodidacta import YeyoAutodidacta
   from src.nocturno.modelos_autodidacta import (
       Ejercicio,
       ResultadoEjercicio,
       ResumenSesion,
   )
   from src.investigador.cache_patrones import CachePatrones
   from src.investigador.modelos import InvestigacionCompleta


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock()
       ia.generate.return_value = MagicMock(
           content="TENDENCIA: AI Agents | EJERCICIO: Crear un agente simple",
           tokens_used=50,
           latency_ms=100,
       )
       ia.get_embedding.return_value = [0.1] * 768
       return ia


   @pytest.fixture
   def mock_pipeline():
       pipeline = AsyncMock()
       inv = MagicMock(spec=InvestigacionCompleta)
       inv.exito = True
       inv.resultado_final = "solución del ejercicio"
       inv.confianza = 0.85
       inv.tiempo_total_ms = 3000
       inv.pasos = []
       pipeline.investigar.return_value = inv
       return pipeline


   @pytest.fixture
   def cache(mock_ia):
       return CachePatrones(pool=None, ia_provider=mock_ia)


   @pytest.fixture
   def autodidacta(mock_ia, mock_pipeline, cache):
       return YeyoAutodidacta(
           ia_provider=mock_ia,
           pipeline=mock_pipeline,
           cache_patrones=cache,
           benchmark_resultados={
               "async_python": 0.5,
               "testing": 0.65,
               "docker": 0.85,
               "typescript": 0.4,
           },
           timeout_sesion_min=0.1,
       )


   @pytest.mark.asyncio
   async def test_generar_curriculum(autodidacta):
       curriculum = await autodidacta.generar_curriculum()
       assert isinstance(curriculum, list)
       assert len(curriculum) > 0
       for ej in curriculum:
           assert isinstance(ej, Ejercicio)
           assert ej.id != ""
           assert ej.prompt != ""


   @pytest.mark.asyncio
   async def test_curriculum_prioriza_debilidades(autodidacta):
       curriculum = await autodidacta.generar_curriculum()
       if len(curriculum) >= 2:
           assert curriculum[0].prioridad >= curriculum[-1].prioridad


   @pytest.mark.asyncio
   async def test_ejecutar_ejercicio_exitoso(autodidacta):
       ejercicio = Ejercicio(
           id="test_1",
           tema="async Python",
           prompt="Crea un ejemplo de asyncio con aiohttp",
       )
       resultado = await autodidacta.ejecutar_ejercicio(ejercicio)
       assert isinstance(resultado, ResultadoEjercicio)
       assert resultado.exito is True
       assert resultado.solucion_final != ""


   @pytest.mark.asyncio
   async def test_ejecutar_ejercicio_falla_y_descompone(mock_ia, cache):
       pipeline_falla = AsyncMock()
       inv_falla = MagicMock(spec=InvestigacionCompleta)
       inv_falla.exito = False
       inv_falla.confianza = 0.2
       inv_falla.resultado_final = ""
       inv_falla.pasos = []
       pipeline_falla.investigar.return_value = inv_falla

       mock_ia.generate.return_value = MagicMock(
           content="SUB-EJERCICIO 1: parte simple\nSUB-EJERCICIO 2: otra parte",
           tokens_used=30,
           latency_ms=50,
       )

       autodidacta = YeyoAutodidacta(
           ia_provider=mock_ia,
           pipeline=pipeline_falla,
           cache_patrones=cache,
       )

       ejercicio = Ejercicio(id="hard_1", tema="distributed systems", prompt="Algo muy difícil")
       resultado = await autodidacta.ejecutar_ejercicio(ejercicio)
       assert isinstance(resultado, ResultadoEjercicio)
       assert resultado.intentos == 3


   @pytest.mark.asyncio
   async def test_ejecutar_sesion_nocturna(autodidacta):
       resumen = await autodidacta.ejecutar_sesion_nocturna()
       assert isinstance(resumen, ResumenSesion)
       assert resumen.ejercicios_total > 0
       assert resumen.tiempo_total_min >= 0


   @pytest.mark.asyncio
   async def test_ejercicios_desde_benchmark(autodidacta):
       ejercicios = await autodidacta._ejercicios_desde_benchmark()
       temas_debiles = [e.tema for e in ejercicios]
       assert "async_python" in temas_debiles or "typescript" in temas_debiles


   @pytest.mark.asyncio
   async def test_patron_guardado_despues_de_exito(autodidacta, cache):
       ejercicio = Ejercicio(
           id="patron_1",
           tema="caching Redis",
           prompt="Implementar cache con Redis",
       )
       resultado = await autodidacta.ejecutar_ejercicio(ejercicio)
       if resultado.exito:
           assert len(cache._cache_local) >= 1


   @pytest.mark.asyncio
   async def test_nunca_se_rinde(mock_ia, cache):
       """Verifica que el autodidacta NUNCA se rinde — siempre intenta descomponer."""
       pipeline_falla = AsyncMock()
       inv_falla = MagicMock(spec=InvestigacionCompleta)
       inv_falla.exito = False
       inv_falla.confianza = 0.1
       inv_falla.resultado_final = ""
       inv_falla.pasos = []
       pipeline_falla.investigar.return_value = inv_falla

       mock_ia.generate.return_value = MagicMock(
           content="SUB-EJERCICIO 1: simplificar\nSUB-EJERCICIO 2: reducir",
           tokens_used=20,
           latency_ms=30,
       )

       autodidacta = YeyoAutodidacta(
           ia_provider=mock_ia,
           pipeline=pipeline_falla,
           cache_patrones=cache,
       )

       ejercicio = Ejercicio(id="impossible", tema="quantum computing", prompt="Algo imposible")
       resultado = await autodidacta.ejecutar_ejercicio(ejercicio)
       assert resultado.intentos == 3


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/nocturno/test_autodidacta.py -v
   Esperado: 8 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.nocturno.autodidacta import YeyoAutodidacta; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.nocturno.modelos_autodidacta import Ejercicio, ResultadoEjercicio, ResumenSesion; print('OK')"
   Esperado: OK

SI FALLA:
- Si falla import de src.investigador.pipeline: verificar que PipelineInvestigador existe (5.28)
- Si falla import de src.investigador.cache_patrones: verificar que CachePatrones existe (5.31)
- Si falla import de src.investigador.modelos: verificar que InvestigacionCompleta existe (5.28)
- Si timeout en tests: reducir timeout_sesion_min en fixtures

NO HACER:
- NO modificar src/investigador/ (creado en 5.28-5.32)
- NO modificar src/nocturno/scheduler.py (creado en 7.25)
- NO hacer llamadas reales a APIs en tests
- NO rendirse en ningún ejercicio — siempre descomponer

GATE:
✅ YeyoAutodidacta genera curriculum basado en debilidades reales del benchmark
✅ Considera tareas lentas, tecnologías no exploradas, y tendencias
✅ Ejecuta ejercicios usando PipelineInvestigador (5.28)
✅ NUNCA se rinde — si falla 3 veces, descompone en sub-ejercicios
✅ Guarda patrones aprendidos en CachePatrones (5.31)
✅ ejecutar_sesion_nocturna() respeta timeout y genera ResumenSesion
✅ 8 tests pasan
✅ Ejercicio, ResultadoEjercicio, ResumenSesion exportados correctamente
```
