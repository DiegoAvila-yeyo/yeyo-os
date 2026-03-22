"""
YeyoOS — NodoCache
Micro-fase 5.23 — Capa 5: Órganos

Wrapper que añade cache a cualquier Nodo.
Antes de ejecutar, busca en Flash Memory si ya existe un resultado reciente.
Cache hit → usa resultado guardado (nodo "saltado")
Cache miss → ejecuta normalmente y guarda resultado
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from .estado import EstadoGrafo
from .nodo import Nodo, NodoError


TIPO_CACHE = "resultado_nodo"
TTL_CACHE_HORAS = 24


class CacheError(Exception):
    """Error en el sistema de cache."""
    pass


class NodoCache(Nodo):
    """
    Wrapper que añade cache a cualquier Nodo del catálogo.
    """

    def __init__(
        self,
        nodo: Nodo,
        flash_memory: Any,
        ttl_horas: float = TTL_CACHE_HORAS,
        campos_entrada: Optional[list[str]] = None,
    ):
        super().__init__(
            id=nodo.id,
            timeout=nodo.timeout,
            max_intentos=nodo.max_intentos,
        )
        self._nodo_original = nodo
        self._flash = flash_memory
        self.ttl_horas = ttl_horas
        self.campos_entrada = campos_entrada
        self.cache_hits = 0
        self.cache_misses = 0

    async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
        hash_entrada = self._hash_entrada(estado.entrada)
        resultado_cacheado = await self._buscar_cache(hash_entrada)

        if resultado_cacheado is not None:
            self.cache_hits += 1
            return self._aplicar_cache(estado, resultado_cacheado, hash_entrada)

        self.cache_misses += 1
        estado = await self._nodo_original.ejecutar(estado)

        await self._guardar_cache(hash_entrada, estado)

        estado.contexto["cache_hit"] = False
        estado.contexto["cache_hash"] = hash_entrada
        return estado

    def _hash_entrada(self, entrada: dict) -> str:
        if self.campos_entrada:
            entrada_filtrada = {k: entrada.get(k) for k in self.campos_entrada if k in entrada}
        else:
            entrada_filtrada = entrada

        try:
            entrada_json = json.dumps(entrada_filtrada, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            entrada_json = str(entrada_filtrada)

        return hashlib.sha256(entrada_json.encode()).hexdigest()[:16]

    async def _buscar_cache(self, hash_entrada: str) -> Optional[dict]:
        try:
            resultados = await self._flash.buscar(
                query=f"nodo_id:{self.id} hash:{hash_entrada}",
                tipo=TIPO_CACHE,
                limite=5,
            )
        except Exception:
            return None

        if not resultados:
            return None

        ahora = datetime.now(timezone.utc)
        ttl = timedelta(hours=self.ttl_horas)

        for resultado in resultados:
            try:
                contenido = resultado.get("contenido", "")
                if isinstance(contenido, str):
                    data = json.loads(contenido)
                elif isinstance(contenido, dict):
                    data = contenido
                else:
                    continue

                if data.get("nodo_id") != self.id:
                    continue
                if data.get("hash_entrada") != hash_entrada:
                    continue

                guardado_en = data.get("guardado_en")
                if guardado_en:
                    t_guardado = datetime.fromisoformat(guardado_en)
                    if ahora - t_guardado > ttl:
                        continue

                return data.get("salida")
            except (json.JSONDecodeError, ValueError, Exception):
                continue

        return None

    async def _guardar_cache(self, hash_entrada: str, estado: EstadoGrafo) -> None:
        cache_data = {
            "nodo_id": self.id,
            "hash_entrada": hash_entrada,
            "salida": estado.salida,
            "guardado_en": datetime.now(timezone.utc).isoformat(),
            "tipo": TIPO_CACHE,
        }

        try:
            await self._flash.guardar(
                dato=json.dumps(cache_data, ensure_ascii=False),
                metadata={
                    "tipo": TIPO_CACHE,
                    "nodo_id": self.id,
                    "hash": hash_entrada,
                }
            )
        except Exception:
            pass

    def _aplicar_cache(
        self,
        estado: EstadoGrafo,
        salida_cacheada: dict,
        hash_entrada: str
    ) -> EstadoGrafo:
        estado.salida.update(salida_cacheada)
        estado.contexto["cache_hit"] = True
        estado.contexto["cache_hash"] = hash_entrada
        estado.contexto["cache_nodo_id"] = self.id
        return estado

    @property
    def tasa_hit(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
