"""
YeyoOS — Ensamblador
Micro-fase 5.28 — Capa 5: Órganos

Toma el candidato ganador + contexto del proyecto y usa el modelo IA
para adaptar el código (nombres, estructura, convenciones).
Cada adaptación es una micro-tarea con contexto limpio.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

from src.ia.interfaces import IAProvider, IAResponse

from .modelos import ResultadoBusqueda

logger = logging.getLogger(__name__)

PROMPT_ENSAMBLAR = """Eres un experto en adaptación de código. Tu tarea es tomar código encontrado en internet
y adaptarlo al proyecto YeyoOS.

REGLAS:
1. Mantener la lógica original intacta
2. Renombrar variables/funciones a convenciones del proyecto (snake_case Python, camelCase TypeScript)
3. Adaptar imports a la estructura del proyecto (src/ para backend, frontend/src/ para frontend)
4. Agregar type hints completos en Python
5. Agregar docstrings en español
6. Eliminar código innecesario o comentarios irrelevantes
7. NO inventar funcionalidad que no estaba en el original
8. Si hay dependencias externas, mencionarlas al final

CONTEXTO DEL PROYECTO:
{contexto_proyecto}

CÓDIGO ORIGINAL (fuente: {fuente}, URL: {url}):
```
{codigo_original}
```

TAREA:
{tarea}

Retorna SOLO el código adaptado, sin explicaciones adicionales."""

PROMPT_VERIFICAR_ADAPTACION = """Compara el código original con la adaptación.

ORIGINAL:
```
{codigo_original}
```

ADAPTACIÓN:
```
{codigo_adaptado}
```

¿La adaptación mantiene la misma lógica? ¿Hay errores?
Responde en formato:
CORRECTO: sí/no
ERRORES: lista de errores o "ninguno"
SCORE: 0.0-1.0"""


class EnsambladorError(Exception):
    """Error durante el ensamblaje."""
    pass


class Ensamblador:
    """
    Adapta código encontrado al contexto del proyecto YeyoOS.
    Usa el modelo IA para renombrar, reestructurar y adaptar.
    """

    def __init__(
        self,
        ia_provider: IAProvider,
        contexto_proyecto: Optional[str] = None,
    ):
        self._ia = ia_provider
        self._contexto = contexto_proyecto or self._contexto_default()

    @staticmethod
    def _contexto_default() -> str:
        return (
            "YeyoOS: OS AI-nativo. Backend FastAPI+Python en src/. "
            "Frontend Next.js+TypeScript en frontend/src/. "
            "PostgreSQL+pgvector+Redis. Modelo qwen2.5:3b via Ollama. "
            "Convenciones: snake_case Python, camelCase TypeScript, "
            "docstrings en español, type hints obligatorios, async/await."
        )

    async def ensamblar(
        self,
        candidato: ResultadoBusqueda,
        tarea: str,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Toma un candidato y lo adapta al proyecto.

        Returns:
            Dict con keys: codigo_adaptado, fuente, score_adaptacion, tokens_usados, duracion_ms
        """
        inicio = time.perf_counter()

        prompt = PROMPT_ENSAMBLAR.format(
            contexto_proyecto=self._contexto,
            fuente=candidato.fuente,
            url=candidato.url,
            codigo_original=candidato.codigo[:3000],
            tarea=tarea,
        )

        try:
            respuesta: IAResponse = await self._ia.generate(
                prompt=prompt,
                system="Eres un adaptador de código experto. Solo retorna código, sin markdown.",
                temperature=0.3,
            )

            codigo_adaptado = self._limpiar_codigo(respuesta.content)

            score = await self._verificar_adaptacion(
                candidato.codigo[:3000],
                codigo_adaptado,
            )

            duracion_ms = int((time.perf_counter() - inicio) * 1000)

            logger.info(
                f"[ensamblador] Adaptación completada: "
                f"score={score}, tokens={respuesta.tokens_used}, "
                f"duracion={duracion_ms}ms"
            )

            return {
                "codigo_adaptado": codigo_adaptado,
                "fuente": candidato.fuente,
                "url": candidato.url,
                "score_adaptacion": score,
                "tokens_usados": respuesta.tokens_used,
                "duracion_ms": duracion_ms,
            }

        except Exception as e:
            logger.error(f"[ensamblador] Error en ensamblaje: {e}")
            raise EnsambladorError(f"Fallo al ensamblar: {e}") from e

    async def _verificar_adaptacion(
        self,
        codigo_original: str,
        codigo_adaptado: str,
    ) -> float:
        """Verifica que la adaptación mantiene la lógica original."""
        try:
            prompt = PROMPT_VERIFICAR_ADAPTACION.format(
                codigo_original=codigo_original,
                codigo_adaptado=codigo_adaptado,
            )
            respuesta = await self._ia.generate(
                prompt=prompt,
                system="Evalúa la adaptación. Responde con SCORE: 0.0-1.0",
                temperature=0.1,
            )
            contenido = respuesta.content.lower()
            
            # Try to extract score using regex (more robust than split)
            # Matches: "score: 0.85", "score:0.85", "score = 0.85", etc.
            match = re.search(r'score\s*[:=]\s*([0-9]+\.?[0-9]*)', contenido)
            if match:
                try:
                    score_value = float(match.group(1))
                    return min(max(score_value, 0.0), 1.0)
                except ValueError:
                    pass
            
            # Fallback: check if response indicates correctness
            if "correcto: sí" in contenido or "correcto: si" in contenido:
                return 0.85
            
            return 0.5
        except Exception as e:
            logger.warning(f"[ensamblador] Error verificando adaptación: {e}")
            return 0.5

    @staticmethod
    def _limpiar_codigo(texto: str) -> str:
        """Elimina markdown code fences si el modelo las incluye."""
        lines = texto.strip().split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
