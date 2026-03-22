"""
YeyoOS — BuscadorExterno
Micro-fase 5.28 — Capa 5: Órganos

Busca soluciones en fuentes externas: GitHub, StackOverflow, documentación.
Cada método retorna List[ResultadoBusqueda] con score normalizado 0.0-1.0.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from .modelos import ResultadoBusqueda

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
SO_API = "https://api.stackexchange.com/2.3"
DEFAULT_TIMEOUT = 15.0


class BuscadorExternoError(Exception):
    """Error en búsqueda externa."""
    pass


class BuscadorExterno:
    """
    Busca código y soluciones en fuentes externas.

    Requiere conexión a internet. Cada método captura errores de red
    y retorna lista vacía en vez de explotar (graceful degradation).
    """

    def __init__(
        self,
        github_token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._github_token = github_token
        self._timeout = timeout
        headers = {"Accept": "application/json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers=headers,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def buscar_github(
        self,
        query: str,
        min_stars: int = 50,
        lenguaje: Optional[str] = None,
        max_resultados: int = 10,
    ) -> List[ResultadoBusqueda]:
        """
        Busca repositorios y código en GitHub.
        Filtra por estrellas mínimas para garantizar calidad.
        Retorna List[ResultadoBusqueda] ordenados por score descendente.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            q = f"{query} stars:>={min_stars}"
            if lenguaje:
                q += f" language:{lenguaje}"

            resp = await self._client.get(
                f"{GITHUB_API}/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": max_resultados},
            )
            if resp.status_code == 403:
                logger.warning("[buscador_externo] GitHub API rate limit alcanzado")
                return resultados
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", [])[:max_resultados]:
                stars = item.get("stargazers_count", 0)
                max_stars = max(stars, 1)
                score_stars = min(stars / 10000.0, 1.0)
                updated = item.get("updated_at", "")
                score_fresh = 0.8 if "2024" in updated or "2025" in updated else 0.4
                score = round((score_stars * 0.6 + score_fresh * 0.4), 3)

                resultados.append(ResultadoBusqueda(
                    fuente="github",
                    url=item.get("html_url", ""),
                    codigo=item.get("description", "") or "",
                    score=score,
                    metadata={
                        "estrellas": stars,
                        "lenguaje": item.get("language", ""),
                        "nombre": item.get("full_name", ""),
                        "actualizado": updated,
                        "licencia": (item.get("license") or {}).get("spdx_id", "unknown"),
                        "topics": item.get("topics", []),
                    },
                ))

            resultados.sort(key=lambda r: r.score, reverse=True)
            logger.info(f"[buscador_externo] GitHub: {len(resultados)} resultados para '{query}'")

        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error GitHub API: {e}")
        except Exception as e:
            logger.error(f"[buscador_externo] Error inesperado GitHub: {e}")

        return resultados

    async def buscar_stackoverflow(
        self,
        query: str,
        min_votes: int = 10,
        max_resultados: int = 10,
    ) -> List[ResultadoBusqueda]:
        """
        Busca preguntas con respuestas aceptadas en StackOverflow.
        Filtra por votos mínimos. Retorna respuestas, no preguntas.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            resp = await self._client.get(
                f"{SO_API}/search/advanced",
                params={
                    "order": "desc",
                    "sort": "votes",
                    "q": query,
                    "accepted": "True",
                    "site": "stackoverflow",
                    "filter": "withbody",
                    "pagesize": max_resultados,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                votos = item.get("score", 0)
                if votos < min_votes:
                    continue

                score_votos = min(votos / 500.0, 1.0)
                tiene_respuesta = 1.0 if item.get("is_answered") else 0.3
                score = round((score_votos * 0.5 + tiene_respuesta * 0.5), 3)

                body = item.get("body", "")
                if len(body) > 3000:
                    body = body[:3000] + "... [truncado]"

                resultados.append(ResultadoBusqueda(
                    fuente="stackoverflow",
                    url=item.get("link", ""),
                    codigo=body,
                    score=score,
                    metadata={
                        "votos": votos,
                        "titulo": item.get("title", ""),
                        "tags": item.get("tags", []),
                        "respondida": item.get("is_answered", False),
                        "respuestas": item.get("answer_count", 0),
                        "vistas": item.get("view_count", 0),
                    },
                ))

            resultados.sort(key=lambda r: r.score, reverse=True)
            logger.info(f"[buscador_externo] StackOverflow: {len(resultados)} resultados para '{query}'")

        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error SO API: {e}")
        except Exception as e:
            logger.error(f"[buscador_externo] Error inesperado SO: {e}")

        return resultados

    async def buscar_documentacion(
        self,
        libreria: str,
        tema: str,
        max_resultados: int = 5,
    ) -> List[ResultadoBusqueda]:
        """
        Busca en documentación oficial usando GitHub code search.
        Busca en repos oficiales de la librería.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            q = f"{tema} repo:{libreria}/{libreria} path:docs OR path:README"
            resp = await self._client.get(
                f"{GITHUB_API}/search/code",
                params={"q": q, "per_page": max_resultados},
            )
            if resp.status_code == 403:
                logger.warning("[buscador_externo] GitHub code search rate limit")
                return resultados
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", [])[:max_resultados]:
                resultados.append(ResultadoBusqueda(
                    fuente="docs",
                    url=item.get("html_url", ""),
                    codigo=item.get("name", ""),
                    score=0.7,
                    metadata={
                        "archivo": item.get("path", ""),
                        "repo": item.get("repository", {}).get("full_name", ""),
                    },
                ))

            logger.info(f"[buscador_externo] Docs: {len(resultados)} resultados para '{libreria}/{tema}'")

        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error docs search: {e}")
        except Exception as e:
            logger.error(f"[buscador_externo] Error inesperado docs: {e}")

        return resultados
