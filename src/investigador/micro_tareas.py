"""
YeyoOS — EjecutorMicroTareas
Micro-fase 5.29 — Capa 5: Órganos

Ejecuta cadenas de razonamiento largas sin llenar el contexto del modelo.
Cada micro-tarea tiene contexto limpio (<max_tokens).
La DB sirve de pegamento: cada paso lee inputs de DB y guarda outputs en DB.

Usado por: PipelineInvestigador (5.28), Razonamiento (5.30), Autodidacta (7.26).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.ia.interfaces import IAProvider, IAResponse

from .modelos import PasoInvestigacion
from .tarea_db import TareaDB

logger = logging.getLogger(__name__)

MAX_TOKENS_DEFAULT = 2000
MAX_REINTENTOS = 2


@dataclass
class MicroTarea:
    """
    Una micro-tarea individual en una cadena de razonamiento.

    - prompt: template con placeholders {key} que se resuelven desde DB
    - input_keys: keys a leer de DB (outputs de pasos anteriores)
    - output_key: key donde guardar el resultado en DB
    - max_tokens: límite de tokens para esta tarea (contexto limpio)
    - system: system prompt opcional para esta tarea específica
    """
    prompt: str
    input_keys: List[str] = field(default_factory=list)
    output_key: str = ""
    max_tokens: int = MAX_TOKENS_DEFAULT
    system: str = "Eres un asistente experto. Responde de forma concisa y precisa."
    temperature: float = 0.3


@dataclass
class ResultadoCadena:
    """Resultado completo de ejecutar una cadena de micro-tareas."""
    tarea_id: str
    pasos: List[PasoInvestigacion] = field(default_factory=list)
    exito: bool = False
    resultado_final: str = ""
    tokens_total: int = 0
    duracion_total_ms: int = 0
    errores: List[str] = field(default_factory=list)


class EjecutorMicroTareasError(Exception):
    """Error en ejecución de micro-tareas."""
    pass


class EjecutorMicroTareas:
    """
    Ejecuta cadenas de micro-tareas con contexto limpio por paso.

    Patrón:
    1. Para cada MicroTarea en la cadena:
       a. Lee inputs de DB (por input_keys)
       b. Formatea el prompt con los inputs
       c. Llama al modelo con contexto limpio
       d. Guarda output en DB (por output_key)
       e. Limpia contexto completamente
    2. El resultado final es el output del último paso.

    La DB es el pegamento — no hay estado compartido en memoria entre pasos.
    """

    def __init__(
        self,
        ia_provider: IAProvider,
        tarea_db: TareaDB,
        max_tokens_global: int = MAX_TOKENS_DEFAULT,
    ):
        self._ia = ia_provider
        self._db = tarea_db
        self._max_tokens_global = max_tokens_global

    async def ejecutar_cadena(
        self,
        tareas: List[MicroTarea],
        tarea_id: Optional[str] = None,
        datos_iniciales: Optional[Dict[str, str]] = None,
    ) -> ResultadoCadena:
        """
        Ejecuta una cadena de micro-tareas secuencialmente.

        Args:
            tareas: Lista ordenada de micro-tareas a ejecutar
            tarea_id: ID único para esta cadena (auto-generado si no se provee)
            datos_iniciales: Dict de key->value para inyectar antes del primer paso

        Returns:
            ResultadoCadena con todos los pasos, resultado final y métricas.
        """
        tarea_id = tarea_id or f"chain_{uuid.uuid4().hex[:12]}"
        resultado = ResultadoCadena(tarea_id=tarea_id)
        inicio_total = time.perf_counter()

        # Inyectar datos iniciales en DB
        if datos_iniciales:
            for key, value in datos_iniciales.items():
                await self._db.guardar_dato(tarea_id, key, value)

        ultimo_output = ""

        for i, tarea in enumerate(tareas):
            paso_numero = i + 1
            inicio_paso = time.perf_counter()

            try:
                # 1. Leer inputs de DB
                inputs = await self._leer_inputs(tarea_id, tarea.input_keys)

                # 2. Formatear prompt con inputs
                prompt_formateado = self._formatear_prompt(tarea.prompt, inputs)

                # 3. Truncar si excede max_tokens
                if len(prompt_formateado) > tarea.max_tokens * 4:
                    prompt_formateado = prompt_formateado[:tarea.max_tokens * 4]
                    logger.warning(
                        f"[micro_tareas] Paso {paso_numero}: prompt truncado a {tarea.max_tokens * 4} chars"
                    )

                # 4. Llamar al modelo (contexto limpio)
                respuesta = await self._ejecutar_con_reintentos(
                    prompt=prompt_formateado,
                    system=tarea.system,
                    temperature=tarea.temperature,
                    max_reintentos=MAX_REINTENTOS,
                )

                output = respuesta.content.strip()
                tokens_usados = respuesta.tokens_used

                # 5. Guardar output en DB
                if tarea.output_key:
                    await self._db.guardar_dato(tarea_id, tarea.output_key, output)

                # 6. Registrar paso en DB
                duracion_ms = int((time.perf_counter() - inicio_paso) * 1000)
                paso = PasoInvestigacion(
                    numero=paso_numero,
                    tipo="micro_tarea",
                    input_resumen=prompt_formateado[:200],
                    output_resumen=output[:200],
                    tokens=tokens_usados,
                    duracion_ms=duracion_ms,
                )
                resultado.pasos.append(paso)
                resultado.tokens_total += tokens_usados

                await self._db.guardar_paso(
                    tarea_id=tarea_id,
                    paso=paso_numero,
                    tipo="micro_tarea",
                    input_resumen=prompt_formateado[:500],
                    output_resumen=output[:500],
                    tokens=tokens_usados,
                    duracion=duracion_ms,
                )

                ultimo_output = output
                logger.info(
                    f"[micro_tareas] Paso {paso_numero}/{len(tareas)} completado: "
                    f"tokens={tokens_usados}, duracion={duracion_ms}ms"
                )

            except Exception as e:
                logger.error(f"[micro_tareas] Error en paso {paso_numero}: {e}")
                resultado.errores.append(f"Paso {paso_numero}: {str(e)}")
                duracion_ms = int((time.perf_counter() - inicio_paso) * 1000)
                resultado.pasos.append(PasoInvestigacion(
                    numero=paso_numero,
                    tipo="micro_tarea_error",
                    input_resumen=f"Error: {str(e)[:200]}",
                    output_resumen="",
                    duracion_ms=duracion_ms,
                ))
                break

        resultado.resultado_final = ultimo_output
        resultado.duracion_total_ms = int((time.perf_counter() - inicio_total) * 1000)
        resultado.exito = len(resultado.errores) == 0

        logger.info(
            f"[micro_tareas] Cadena {tarea_id} completada: "
            f"{len(resultado.pasos)} pasos, exito={resultado.exito}, "
            f"tokens_total={resultado.tokens_total}"
        )
        return resultado

    async def _leer_inputs(
        self,
        tarea_id: str,
        input_keys: List[str],
    ) -> Dict[str, str]:
        """Lee los valores de input_keys desde la DB."""
        inputs: Dict[str, str] = {}
        for key in input_keys:
            valor = await self._db.leer_dato(tarea_id, key)
            if valor is not None:
                inputs[key] = valor
            else:
                logger.warning(f"[micro_tareas] Key '{key}' no encontrada en DB para {tarea_id}")
                inputs[key] = ""
        return inputs

    @staticmethod
    def _formatear_prompt(template: str, inputs: Dict[str, str]) -> str:
        """Formatea el template reemplazando {key} con valores de inputs."""
        resultado = template
        for key, value in inputs.items():
            resultado = resultado.replace(f"{{{key}}}", value)
        return resultado

    async def _ejecutar_con_reintentos(
        self,
        prompt: str,
        system: str,
        temperature: float,
        max_reintentos: int,
    ) -> IAResponse:
        """Ejecuta prompt contra el modelo con reintentos en caso de error."""
        ultimo_error = None
        for intento in range(max_reintentos + 1):
            try:
                respuesta = await self._ia.generate(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                )
                if respuesta.content.strip():
                    return respuesta
                logger.warning(f"[micro_tareas] Respuesta vacía, intento {intento + 1}")
            except Exception as e:
                ultimo_error = e
                logger.warning(f"[micro_tareas] Error intento {intento + 1}: {e}")
        raise EjecutorMicroTareasError(
            f"Fallaron {max_reintentos + 1} intentos: {ultimo_error}"
        )
