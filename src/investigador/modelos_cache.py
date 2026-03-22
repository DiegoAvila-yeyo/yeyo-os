"""
YeyoOS — Modelos de Caché de Patrones
Micro-fase 5.31 — Capa 5: Órganos

Dataclasses para patrones de razonamiento reutilizables
y pre-computaciones anticipatorias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PatronRazonamiento:
    """
    Un patrón de razonamiento reutilizable.
    Almacena no solo el resultado sino el CAMINO para llegar a él.
    """
    id: Optional[int] = None
    tipo_problema: str = ""
    errores_comunes: List[Dict[str, Any]] = field(default_factory=list)
    patron_correcto: str = ""
    pasos_razonamiento: List[Dict[str, Any]] = field(default_factory=list)
    tiempo_original_ms: int = 0
    confianza: float = 0.0
    veces_reutilizado: int = 0
    aplicable_a: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None


@dataclass
class PreComputado:
    """
    Una solución pre-computada por el Anticipador.
    Preparada en background para que esté lista cuando el usuario la necesite.
    """
    tarea_anticipada: str
    solucion: str
    confianza: float = 0.0
    razon: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    usada: bool = False
