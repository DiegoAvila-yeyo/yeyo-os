"""
YeyoOS — Modelos para SelectorModelo
Micro-fase 5.32 — Capa 5: Órganos

Dataclasses para configuración de modelos y selección.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModeloConfig:
    """Configuración de un modelo disponible."""
    nombre: str  # Nombre del modelo (e.g., "qwen2.5:3b")
    tipo: str  # "local" | "yeyonet" | "api"
    vram_requerida_mb: int = 0  # VRAM necesaria en MB
    velocidad_estimada: float = 1.0  # tokens/segundo estimados
    calidad_estimada: float = 0.7  # 0.0-1.0 calidad esperada
    disponible: bool = True
    endpoint: Optional[str] = None  # URL si es remoto/API
    max_tokens: int = 4096
    costo_por_token: float = 0.0  # Solo para APIs externas


# Modelos predefinidos
MODELO_LOCAL_SMALL = ModeloConfig(
    nombre="qwen2.5:3b",
    tipo="local",
    vram_requerida_mb=2048,
    velocidad_estimada=30.0,
    calidad_estimada=0.7,
    max_tokens=4096,
)

MODELO_LOCAL_CODER = ModeloConfig(
    nombre="qwen2.5-coder:7b",
    tipo="local",
    vram_requerida_mb=5120,
    velocidad_estimada=15.0,
    calidad_estimada=0.85,
    max_tokens=8192,
)

MODELO_YEYONET_DEFAULT = ModeloConfig(
    nombre="yeyonet:best",
    tipo="yeyonet",
    vram_requerida_mb=0,
    velocidad_estimada=20.0,
    calidad_estimada=0.9,
    max_tokens=8192,
)

MODELO_API_FALLBACK = ModeloConfig(
    nombre="api:fallback",
    tipo="api",
    vram_requerida_mb=0,
    velocidad_estimada=50.0,
    calidad_estimada=0.95,
    max_tokens=16384,
    costo_por_token=0.00001,
)
