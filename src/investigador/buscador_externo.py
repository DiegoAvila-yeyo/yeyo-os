"""
YeyoOS — BuscadorExterno
Micro-fase 5.28 — Capa 5: Órganos

Busca soluciones en fuentes externas: GitHub, StackOverflow, documentación.
Cada método retorna List[ResultadoBusqueda] con score normalizado 0.0-1.0.
"""

from __future__ import annotations

import asyncio
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
DEFAULT_TIMEOUT = 30.0  # Timeout per request
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # exponential backoff: 1s, 2s, 4s


class BuscadorExternoError(Exception):
    """Error en búsqueda externa."""
    pass


class RateLimitError(BuscadorExternoError):
    """GitHub/SO API rate limited (HTTP 403)."""
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
        self._max_retries = MAX_RETRIES
        self._retry_delay = RETRY_DELAY
        self._closed = False
        headers = {"Accept": "application/json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers=headers,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the httpx client connection."""
        if not self._closed:
            await self._client.aclose()
            self._closed = True

    def __del__(self):
        """Cleanup: close client if not already closed."""
        if not self._closed and hasattr(self, '_client'):
            try:
                # Can't use await in __del__, so we need sync close
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule cleanup for later
                        asyncio.create_task(self.close())
                    else:
                        loop.run_until_complete(self.close())
                except RuntimeError:
                    pass
            except Exception:
                pass

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: ensure cleanup."""
        await self.close()
        return False

    async def _retryable_request(
        self,
        method: str,
        url: str,
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Execute HTTP request with exponential backoff retry.
        
        Args:
            method: HTTP method (GET, POST, etc)
            url: Target URL
            max_retries: Number of retries (default: MAX_RETRIES)
            **kwargs: Additional arguments for httpx request
        
        Returns:
            httpx.Response if successful
            
        Raises:
            RateLimitError: If HTTP 403 (rate limited)
            httpx.HTTPError: If all retries exhausted
        """
        if max_retries is None:
            max_retries = self._max_retries
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                resp = await self._client.request(method, url, **kwargs)
                
                # Rate limit (HTTP 403) - no retry, fail immediately
                if resp.status_code == 403:
                    logger.warning(f"[buscador_externo] Rate limit (403) for {url}")
                    raise RateLimitError(f"Rate limited: {url}")
                
                # Server error (5xx) - retry
                if 500 <= resp.status_code < 600:
                    if attempt < max_retries - 1:
                        wait_time = self._retry_delay * (2 ** attempt)
                        logger.warning(
                            f"[buscador_externo] Server error {resp.status_code}, "
                            f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        resp.raise_for_status()
                
                resp.raise_for_status()
                return resp
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        f"[buscador_externo] Network error ({type(e).__name__}), "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[buscador_externo] Timeout after {max_retries} retries: {url}")
                    raise
            
            except httpx.HTTPError as e:
                # HTTPError with status_code attribute (e.g., HTTPStatusError)
                status_code = getattr(e, 'response', {}).status_code if hasattr(e, 'response') else None
                if attempt < max_retries - 1 and status_code and status_code >= 500:
                    wait_time = self._retry_delay * (2 ** attempt)
                    logger.warning(f"[buscador_externo] HTTP error {status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        if last_error:
            raise last_error

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
        Implementa retry automático en caso de network issues.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            q = f"{query} stars:>={min_stars}"
            if lenguaje:
                q += f" language:{lenguaje}"

            resp = await self._retryable_request(
                "GET",
                f"{GITHUB_API}/search/repositories",
                params={"q": q, "sort": "stars", "order": "desc", "per_page": max_resultados},
            )
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

        except RateLimitError as e:
            logger.warning(f"[buscador_externo] GitHub rate limited: {e}")
        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error GitHub API (after retries): {e}")
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
        Implementa retry automático en caso de network issues.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            resp = await self._retryable_request(
                "GET",
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

        except RateLimitError as e:
            logger.warning(f"[buscador_externo] StackOverflow rate limited: {e}")
        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error SO API (after retries): {e}")
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
        Implementa retry automático en caso de network issues.
        """
        resultados: List[ResultadoBusqueda] = []
        try:
            q = f"{tema} repo:{libreria}/{libreria} path:docs OR path:README"
            resp = await self._retryable_request(
                "GET",
                f"{GITHUB_API}/search/code",
                params={"q": q, "per_page": max_resultados},
            )
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

        except RateLimitError as e:
            logger.warning(f"[buscador_externo] Docs search rate limited: {e}")
        except httpx.HTTPError as e:
            logger.error(f"[buscador_externo] Error docs search (after retries): {e}")
        except Exception as e:
            logger.error(f"[buscador_externo] Error inesperado docs: {e}")

        return resultados
