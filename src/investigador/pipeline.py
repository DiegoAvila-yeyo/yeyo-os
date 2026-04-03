"""
YeyoOS — PipelineInvestigador
Micro-fase 5.28 — Capa 5: Órganos

Corazón del paradigma de investigación autónoma.
6 fases: buscar_interno → buscar_externo → evaluar_candidatos →
ensamblar_solucion → verificar → almacenar.

Cuando Yeyo no tiene la respuesta en memoria, investiga en internet.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from src.ia.interfaces import IAProvider
from src.memory.flash_memory import FlashMemory
from src.memory.cache import MemoryCache

from .buscador_externo import BuscadorExterno
from .ensamblador import Ensamblador
from .evaluador import EvaluadorCandidatos
from .modelos import (
    InvestigacionCompleta,
    PasoInvestigacion,
    ResultadoBusqueda,
)
from .verificador import Verificador

logger = logging.getLogger(__name__)

CONFIANZA_MINIMA_INTERNA = 0.7
CONFIANZA_MINIMA_ACEPTAR = 0.6


class PipelineInvestigadorError(Exception):
    """Error en el pipeline de investigación."""
    pass


class PipelineInvestigador:
    """
    Pipeline de investigación autónoma de 6 fases.

    Uso:
        pipeline = PipelineInvestigador(ia, flash_memory, cache, buscador, ...)
        resultado = await pipeline.investigar("Cómo implementar rate limiting en FastAPI")

    Integración con YeyoOrquestador (4.19):
        Un nodo de tipo "investigar" en un grafo delega al pipeline.
        Si un nodo normal falla, escala automáticamente aquí.
    """

    def __init__(
        self,
        ia_provider: IAProvider,
        flash_memory: FlashMemory,
        memory_cache: Optional[MemoryCache] = None,
        buscador_externo: Optional[BuscadorExterno] = None,
        evaluador: Optional[EvaluadorCandidatos] = None,
        ensamblador: Optional[Ensamblador] = None,
        verificador: Optional[Verificador] = None,
        cache_patrones: Optional[Any] = None,
    ):
        self._ia = ia_provider
        self._flash = flash_memory
        self._cache = memory_cache
        self._buscador = buscador_externo or BuscadorExterno()
        self._evaluador = evaluador or EvaluadorCandidatos()
        self._ensamblador = ensamblador or Ensamblador(ia_provider)
        self._verificador = verificador or Verificador()
        self._cache_patrones = cache_patrones

    async def investigar(
        self,
        tarea: str,
        lenguaje: str = "python",
        max_resultados_externos: int = 10,
    ) -> InvestigacionCompleta:
        """
        Ejecuta las 6 fases de investigación.
        Retorna InvestigacionCompleta con resultado, confianza y pasos.
        """
        tarea_id = f"inv_{uuid.uuid4().hex[:12]}"
        investigacion = InvestigacionCompleta(tarea_id=tarea_id)
        inicio = time.perf_counter()

        try:
            # Fase 0: Consultar caché de patrones (5.31) si disponible
            if self._cache_patrones:
                patron = await self._consultar_cache_patrones(tarea, investigacion)
                if patron and patron.get("confianza", 0) >= CONFIANZA_MINIMA_INTERNA:
                    investigacion.resultado_final = patron.get("solucion", "")
                    investigacion.confianza = patron["confianza"]
                    investigacion.exito = True
                    investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                    investigacion.fuentes_usadas.append("cache_patrones")
                    logger.info(f"[pipeline] {tarea_id} resuelto por caché de patrones")
                    return investigacion

            # Fase 1: Búsqueda interna (Redis → pgvector → Flash Memory)
            internos = await self.buscar_interno(tarea, investigacion)
            if internos and internos[0].score >= CONFIANZA_MINIMA_INTERNA:
                mejor = internos[0]
                investigacion.resultado_final = mejor.codigo
                investigacion.confianza = mejor.score
                investigacion.exito = True
                investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                investigacion.fuentes_usadas.append(mejor.fuente)
                logger.info(f"[pipeline] {tarea_id} resuelto por búsqueda interna")
                return investigacion

            # Fase 2: Búsqueda externa (GitHub, StackOverflow, docs)
            externos = await self.buscar_externo(tarea, lenguaje, max_resultados_externos, investigacion)

            todos = (internos or []) + (externos or [])
            if not todos:
                # Track WHY no results
                fallo_interno = internos is None or len(internos) == 0
                fallo_externo = externos is None or len(externos) == 0
                
                investigacion.resultado_final = ""
                investigacion.confianza = 0.0
                investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                investigacion.exito = False
                
                # Log structured failure info
                razon = []
                if fallo_interno:
                    razon.append("búsqueda_interna_sin_resultados")
                if fallo_externo:
                    razon.append("búsqueda_externa_sin_resultados")
                
                investigacion.fallos = {
                    "interno_fallido": fallo_interno,
                    "externo_fallido": fallo_externo,
                    "razones": razon,
                }
                
                logger.warning(
                    f"[pipeline] {tarea_id} sin resultados: {', '.join(razon) if razon else 'desconocido'}"
                )
                return investigacion

            # Fase 3: Evaluar candidatos
            evaluados = await self.evaluar_candidatos(todos, investigacion)
            if not evaluados or len(evaluados) == 0:
                investigacion.resultado_final = ""
                investigacion.confianza = 0.0
                investigacion.exito = False
                investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
                logger.warning(f"[pipeline] {tarea_id} evaluación retornó cero candidatos")
                return investigacion

            mejor_candidato = evaluados[0].resultado

            # Fase 4: Ensamblar solución
            ensamblado = await self.ensamblar_solucion(mejor_candidato, tarea, investigacion)

            # Fase 5: Verificar
            confianza = await self.verificar(
                ensamblado.get("codigo_adaptado", ""),
                lenguaje,
                mejor_candidato.codigo,
                investigacion,
            )

            # Fase 6: Almacenar en memoria
            if confianza >= CONFIANZA_MINIMA_ACEPTAR:
                await self.almacenar(
                    tarea_id,
                    tarea,
                    ensamblado.get("codigo_adaptado", ""),
                    confianza,
                    investigacion,
                )
                investigacion.resultado_final = ensamblado.get("codigo_adaptado", "")
                investigacion.confianza = confianza
                investigacion.exito = True
            else:
                investigacion.resultado_final = ensamblado.get("codigo_adaptado", "")
                investigacion.confianza = confianza
                investigacion.exito = False

        except Exception as e:
            logger.error(f"[pipeline] {tarea_id} error: {e}")
            investigacion.exito = False

        investigacion.tiempo_total_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.tokens_total = sum(p.tokens for p in investigacion.pasos)
        return investigacion

    async def buscar_interno(
        self,
        tarea: str,
        investigacion: InvestigacionCompleta,
    ) -> List[ResultadoBusqueda]:
        """Fase 1: Busca en Redis → pgvector → Flash Memory."""
        inicio = time.perf_counter()
        resultados: List[ResultadoBusqueda] = []

        try:
            # 1a. Redis cache
            if self._cache:
                try:
                    cached = await self._cache.get(f"inv:{tarea[:100]}")
                    if cached:
                        resultados.append(ResultadoBusqueda(
                            fuente="redis",
                            url=f"cache:inv:{tarea[:50]}",
                            codigo=cached.content if hasattr(cached, 'content') else str(cached),
                            score=0.9,
                            metadata={"origen": "redis_cache"},
                        ))
                except Exception as e:
                    logger.debug(f"[pipeline] Redis miss: {e}")

            # 1b. pgvector semantic search via Flash Memory
            try:
                embedding = await self._ia.get_embedding(tarea)
                memorias = await self._flash.search_semantic(
                    embedding=embedding,
                    threshold=0.7,
                    limit=5,
                )
                for mem in memorias:
                    resultados.append(ResultadoBusqueda(
                        fuente="pgvector",
                        url=f"memory:{mem.id}",
                        codigo=mem.content,
                        score=0.8,
                        metadata={"tipo": mem.type, "tier": mem.tier},
                    ))
            except Exception as e:
                logger.debug(f"[pipeline] pgvector search error: {e}")

            # 1c. Flash Memory recall por texto
            try:
                memorias = await self._flash.recall(query=tarea, limit=5)
                for mem in memorias:
                    if not any(r.url == f"memory:{mem.id}" for r in resultados):
                        resultados.append(ResultadoBusqueda(
                            fuente="flash_memory",
                            url=f"memory:{mem.id}",
                            codigo=mem.content,
                            score=0.7,
                            metadata={"tipo": mem.type, "tier": mem.tier},
                        ))
            except Exception as e:
                logger.debug(f"[pipeline] Flash Memory recall error: {e}")

        except Exception as e:
            logger.error(f"[pipeline] Error búsqueda interna: {e}")

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="busqueda_interna",
            input_resumen=tarea[:200],
            output_resumen=f"{len(resultados)} resultados internos",
            duracion_ms=duracion_ms,
        ))
        return resultados

    async def buscar_externo(
        self,
        tarea: str,
        lenguaje: str,
        max_resultados: int,
        investigacion: InvestigacionCompleta,
    ) -> List[ResultadoBusqueda]:
        """Fase 2: Busca en GitHub, StackOverflow, documentación."""
        inicio = time.perf_counter()
        resultados: List[ResultadoBusqueda] = []

        try:
            github_res = await self._buscador.buscar_github(
                query=tarea,
                min_stars=50,
                lenguaje=lenguaje,
                max_resultados=max_resultados,
            )
            resultados.extend(github_res)
            investigacion.fuentes_usadas.append("github")
        except Exception as e:
            logger.warning(f"[pipeline] GitHub search failed: {e}")

        try:
            so_res = await self._buscador.buscar_stackoverflow(
                query=tarea,
                min_votes=10,
                max_resultados=max_resultados,
            )
            resultados.extend(so_res)
            investigacion.fuentes_usadas.append("stackoverflow")
        except Exception as e:
            logger.warning(f"[pipeline] StackOverflow search failed: {e}")

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="busqueda_externa",
            input_resumen=tarea[:200],
            output_resumen=f"{len(resultados)} resultados externos (GitHub + SO)",
            duracion_ms=duracion_ms,
        ))
        return resultados

    async def evaluar_candidatos(
        self,
        candidatos: List[ResultadoBusqueda],
        investigacion: InvestigacionCompleta,
    ) -> list:
        """Fase 3: Evalúa candidatos con criterios de calidad."""
        inicio = time.perf_counter()
        evaluados = self._evaluador.evaluar(candidatos)

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        top_score = evaluados[0].score_final if evaluados else 0
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="evaluacion",
            input_resumen=f"{len(candidatos)} candidatos",
            output_resumen=f"Top score: {top_score}",
            duracion_ms=duracion_ms,
        ))
        return evaluados

    async def ensamblar_solucion(
        self,
        candidato: ResultadoBusqueda,
        tarea: str,
        investigacion: InvestigacionCompleta,
    ) -> Dict[str, Any]:
        """Fase 4: Ensambla la solución adaptándola al proyecto."""
        inicio = time.perf_counter()
        resultado = await self._ensamblador.ensamblar(candidato, tarea)

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="ensamblaje",
            input_resumen=f"Candidato de {candidato.fuente}",
            output_resumen=f"Adaptado, score={resultado.get('score_adaptacion', 0)}",
            tokens=resultado.get("tokens_usados", 0),
            duracion_ms=duracion_ms,
        ))
        return resultado

    async def verificar(
        self,
        codigo: str,
        lenguaje: str,
        fuente_original: str,
        investigacion: InvestigacionCompleta,
    ) -> float:
        """Fase 5: Verifica con 5 niveles."""
        inicio = time.perf_counter()
        resultado = await self._verificador.verificar_completo(
            codigo=codigo,
            lenguaje=lenguaje,
            fuente_original=fuente_original,
        )

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="verificacion",
            input_resumen=f"Código {lenguaje} ({len(codigo)} chars)",
            output_resumen=f"Confianza: {resultado.confianza}",
            confianza=resultado.confianza,
            duracion_ms=duracion_ms,
        ))
        return resultado.confianza

    async def almacenar(
        self,
        tarea_id: str,
        tarea: str,
        codigo: str,
        confianza: float,
        investigacion: InvestigacionCompleta,
    ) -> None:
        """Fase 6: Almacena en Flash Memory + pgvector + Redis."""
        inicio = time.perf_counter()

        try:
            embedding = await self._ia.get_embedding(f"{tarea}\n{codigo[:500]}")
            await self._flash.store(
                content=f"[Investigación {tarea_id}]\nTarea: {tarea}\n\n{codigo}",
                type="skill",
                metadata={
                    "tarea_id": tarea_id,
                    "confianza": confianza,
                    "fuentes": investigacion.fuentes_usadas,
                    "pasos": len(investigacion.pasos),
                },
                embedding=embedding,
                source="investigador",
            )

            if self._cache:
                try:
                    from src.memory.models import Memory
                    mem = Memory(
                        id=tarea_id,
                        content=codigo[:5000],
                        type="skill",
                        tier="WARM",
                        embedding=None,
                        checksum="",
                        access_count=0,
                        metadata={"confianza": confianza},
                        source="investigador",
                    )
                    await self._cache.set(mem, ttl=86400)
                except Exception as e:
                    logger.debug(f"[pipeline] Redis cache set error: {e}")

        except Exception as e:
            logger.error(f"[pipeline] Error almacenando: {e}")

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        investigacion.pasos.append(PasoInvestigacion(
            numero=len(investigacion.pasos) + 1,
            tipo="almacenamiento",
            input_resumen=f"Resultado {tarea_id}",
            output_resumen=f"Almacenado con confianza {confianza}",
            duracion_ms=duracion_ms,
        ))

    async def _consultar_cache_patrones(
        self,
        tarea: str,
        investigacion: InvestigacionCompleta,
    ) -> Optional[Dict[str, Any]]:
        """Consulta CachePatrones (5.31) para reutilizar razonamientos previos."""
        try:
            patron = await self._cache_patrones.buscar_patron(tarea, threshold=0.85)
            if patron:
                return {
                    "solucion": patron.patron_correcto,
                    "confianza": patron.confianza,
                }
        except Exception as e:
            logger.debug(f"[pipeline] CachePatrones no disponible: {e}")
        return None
