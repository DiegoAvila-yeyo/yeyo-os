"""
YeyoOS — SelectorModelo
Micro-fase 5.32 — Capa 5: Órganos

Elige automáticamente el modelo correcto para cada tarea basándose en:
1. Complejidad estimada de la tarea
2. Modelos disponibles (Ollama local, YeyoNet remoto, API externa)
3. VRAM disponible en la máquina local
4. Historial de tiempos para tareas similares

Consultado por YeyoOrquestador (4.19) antes de ejecutar cada nodo.
Cada nodo puede overridear con modelo explícito.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from .modelos_selector import (
    MODELO_API_FALLBACK,
    MODELO_LOCAL_CODER,
    MODELO_LOCAL_SMALL,
    MODELO_YEYONET_DEFAULT,
    ModeloConfig,
)

logger = logging.getLogger(__name__)

KEYWORDS_ALTA_COMPLEJIDAD = {
    "distributed", "concurrent", "microservices", "machine learning",
    "neural network", "optimization", "security", "encryption",
    "compiler", "kernel", "parser", "real-time",
    "compilador", "distribuido", "concurrencia", "seguridad",
    "aprendizaje automático", "optimización",
}

KEYWORDS_MEDIA_COMPLEJIDAD = {
    "api", "database", "cache", "websocket", "middleware",
    "authentication", "migration", "pipeline", "docker",
    "base de datos", "autenticación", "migración",
}


class SelectorModeloError(Exception):
    """Error en selección de modelo."""
    pass


class SelectorModelo:
    """
    Selector automático de modelo por complejidad.

    Umbrales de selección:
    - complejidad < 0.3 → qwen2.5:3b (local, rápido)
    - complejidad 0.3-0.6 → qwen2.5-coder:7b (si hay VRAM)
    - complejidad 0.6-0.8 → delegar a YeyoNet (nodo con mejor GPU)
    - complejidad > 0.8 → API externa como fallback

    Fallback graceful: si el modelo elegido no está disponible,
    baja al siguiente nivel.
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        yeyonet_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
    ):
        self._ollama_host = ollama_host
        self._yeyonet_endpoint = yeyonet_endpoint
        self._api_key = api_key or os.getenv("YEYO_API_KEY")
        self._api_endpoint = api_endpoint or os.getenv("YEYO_API_ENDPOINT")
        self._modelos_cache: Optional[List[ModeloConfig]] = None
        self._historial_tiempos: Dict[str, List[float]] = {}

    async def elegir(self, tarea: str, modelo_override: Optional[str] = None) -> ModeloConfig:
        """
        Elige el modelo óptimo para la tarea dada.

        Args:
            tarea: Descripción de la tarea
            modelo_override: Modelo explícito (overridea la selección automática)

        Returns:
            ModeloConfig con el modelo elegido
        """
        # Override explícito
        if modelo_override:
            modelos = await self.modelos_disponibles()
            for m in modelos:
                if m.nombre == modelo_override and m.disponible:
                    logger.info(f"[selector_modelo] Override: {modelo_override}")
                    return m
            logger.warning(f"[selector_modelo] Override '{modelo_override}' no disponible, auto-seleccionando")

        complejidad = self.estimar_complejidad(tarea)
        logger.info(f"[selector_modelo] Complejidad estimada: {complejidad}")

        # Selección por complejidad con fallback
        if complejidad < 0.3:
            candidatos = [MODELO_LOCAL_SMALL, MODELO_LOCAL_CODER, MODELO_YEYONET_DEFAULT, MODELO_API_FALLBACK]
        elif complejidad < 0.6:
            candidatos = [MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL, MODELO_YEYONET_DEFAULT, MODELO_API_FALLBACK]
        elif complejidad < 0.8:
            candidatos = [MODELO_YEYONET_DEFAULT, MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL, MODELO_API_FALLBACK]
        else:
            candidatos = [MODELO_API_FALLBACK, MODELO_YEYONET_DEFAULT, MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL]

        # Intentar cada candidato en orden (fallback graceful)
        for candidato in candidatos:
            if await self._esta_disponible(candidato):
                logger.info(
                    f"[selector_modelo] Elegido: {candidato.nombre} "
                    f"(tipo={candidato.tipo}, complejidad={complejidad})"
                )
                return candidato

        # Último recurso: devolver el local pequeño aunque no responda
        logger.warning("[selector_modelo] Ningún modelo disponible, usando default")
        return MODELO_LOCAL_SMALL

    async def modelos_disponibles(self) -> List[ModeloConfig]:
        """
        Detecta qué modelos están disponibles:
        1. Modelos Ollama instalados localmente
        2. Nodos YeyoNet con GPU disponible
        3. APIs externas configuradas
        """
        if self._modelos_cache:
            return self._modelos_cache

        modelos: List[ModeloConfig] = []

        # 1. Modelos Ollama locales
        ollama_modelos = await self._detectar_ollama()
        modelos.extend(ollama_modelos)

        # 2. Nodos YeyoNet
        if self._yeyonet_endpoint:
            yeyonet = MODELO_YEYONET_DEFAULT
            yeyonet.endpoint = self._yeyonet_endpoint
            yeyonet.disponible = await self._check_yeyonet()
            modelos.append(yeyonet)

        # 3. API externa
        if self._api_key and self._api_endpoint:
            api = MODELO_API_FALLBACK
            api.endpoint = self._api_endpoint
            api.disponible = True
            modelos.append(api)

        self._modelos_cache = modelos
        logger.info(f"[selector_modelo] {len(modelos)} modelos detectados")
        return modelos

    def estimar_complejidad(self, tarea: str) -> float:
        """
        Estima complejidad 0.0-1.0 de una tarea.
        Factores: longitud, keywords técnicas, historial de tiempos.
        """
        tarea_lower = tarea.lower()

        # Factor 1: Longitud (0.0-0.3)
        longitud = len(tarea)
        if longitud > 1000:
            score_longitud = 0.3
        elif longitud > 500:
            score_longitud = 0.2
        elif longitud > 200:
            score_longitud = 0.1
        else:
            score_longitud = 0.05

        # Factor 2: Keywords (0.0-0.5)
        hits_alta = sum(1 for kw in KEYWORDS_ALTA_COMPLEJIDAD if kw in tarea_lower)
        hits_media = sum(1 for kw in KEYWORDS_MEDIA_COMPLEJIDAD if kw in tarea_lower)
        score_keywords = min((hits_alta * 0.15 + hits_media * 0.05), 0.5)

        # Factor 3: Historial de tiempos (0.0-0.2)
        score_historial = 0.0
        for key, tiempos in self._historial_tiempos.items():
            if any(word in tarea_lower for word in key.split()):
                avg_time = sum(tiempos) / len(tiempos)
                if avg_time > 10000:
                    score_historial = max(score_historial, 0.2)
                elif avg_time > 5000:
                    score_historial = max(score_historial, 0.1)

        return round(min(score_longitud + score_keywords + score_historial, 1.0), 3)

    def registrar_tiempo(self, tarea_key: str, tiempo_ms: float) -> None:
        """Registra el tiempo de ejecución para mejorar estimaciones futuras."""
        if tarea_key not in self._historial_tiempos:
            self._historial_tiempos[tarea_key] = []
        self._historial_tiempos[tarea_key].append(tiempo_ms)
        if len(self._historial_tiempos[tarea_key]) > 20:
            self._historial_tiempos[tarea_key] = self._historial_tiempos[tarea_key][-20:]

    async def invalidar_cache(self) -> None:
        """Fuerza re-detección de modelos en la próxima llamada."""
        self._modelos_cache = None

    async def _detectar_ollama(self) -> List[ModeloConfig]:
        """Detecta modelos instalados en Ollama local."""
        modelos: List[ModeloConfig] = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._ollama_host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for model in data.get("models", []):
                        nombre = model.get("name", "")
                        size_bytes = model.get("size", 0)
                        vram_mb = int(size_bytes / (1024 * 1024)) if size_bytes else 2048

                        config = ModeloConfig(
                            nombre=nombre,
                            tipo="local",
                            vram_requerida_mb=vram_mb,
                            velocidad_estimada=30.0 if "3b" in nombre else 15.0,
                            calidad_estimada=0.7 if "3b" in nombre else 0.85,
                            disponible=True,
                            endpoint=self._ollama_host,
                        )
                        modelos.append(config)

                    logger.info(f"[selector_modelo] Ollama: {len(modelos)} modelos detectados")
        except Exception as e:
            logger.warning(f"[selector_modelo] Ollama no accesible: {e}")

        # Si no detectó nada, agregar defaults
        if not modelos:
            modelos.append(MODELO_LOCAL_SMALL)

        return modelos

    async def _check_yeyonet(self) -> bool:
        """Verifica si YeyoNet tiene nodos disponibles."""
        if not self._yeyonet_endpoint:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._yeyonet_endpoint}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def _esta_disponible(self, modelo: ModeloConfig) -> bool:
        """Verifica si un modelo específico está disponible."""
        if modelo.tipo == "local":
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{self._ollama_host}/api/tags")
                    if resp.status_code == 200:
                        modelos = [m["name"] for m in resp.json().get("models", [])]
                        return modelo.nombre in modelos
            except Exception:
                return False
        elif modelo.tipo == "yeyonet":
            return await self._check_yeyonet()
        elif modelo.tipo == "api":
            return bool(self._api_key and self._api_endpoint)
        return False
