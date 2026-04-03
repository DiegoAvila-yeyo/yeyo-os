"""
YeyoOS — Modelos del Investigador
Micro-fase 5.28 — Capa 5: Órganos

Dataclasses compartidas por todo el módulo investigador.
Usadas por: pipeline.py, buscador_externo.py, evaluador.py, ensamblador.py,
verificador.py, micro_tareas.py, cache_patrones.py, razonamiento.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ResultadoBusqueda:
    """Un resultado individual de búsqueda (interna o externa)."""
    fuente: str  # "flash_memory", "redis", "pgvector", "github", "stackoverflow", "docs"
    url: str  # URL o ID del recurso
    codigo: str  # Código o contenido encontrado
    score: float  # 0.0-1.0 — calidad estimada
    metadata: Dict[str, Any] = field(default_factory=dict)
    # metadata puede incluir: estrellas, votos, fecha, lenguaje, licencia, etc.


@dataclass
class PasoInvestigacion:
    """Un paso individual dentro de una investigación."""
    numero: int
    tipo: str  # "busqueda_interna", "busqueda_externa", "evaluacion", "ensamblaje", "verificacion", "almacenamiento"
    input_resumen: str  # Resumen del input (truncado para no llenar contexto)
    output_resumen: str  # Resumen del output
    tokens: int = 0
    duracion_ms: int = 0
    confianza: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InvestigacionCompleta:
    """Resultado completo de una investigación."""
    tarea_id: str
    pasos: List[PasoInvestigacion] = field(default_factory=list)
    resultado_final: str = ""
    confianza: float = 0.0  # 0.0-1.0
    tiempo_total_ms: int = 0
    tokens_total: int = 0
    fuentes_usadas: List[str] = field(default_factory=list)
    exito: bool = False
    fallos: Dict[str, Any] = field(default_factory=dict)  # Track failure reasons


@dataclass
class TestResult:
    """Resultado de ejecución de tests."""
    passed: bool
    total: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    output: str = ""


@dataclass
class LintResult:
    """Resultado de análisis estático."""
    passed: bool
    warnings: int = 0
    errors: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StressResult:
    """Resultado de stress test en Docker."""
    passed: bool
    tiempo_ms: int = 0
    memoria_peak_mb: float = 0.0
    errores: List[str] = field(default_factory=list)


@dataclass
class VerificacionCompleta:
    """Resultado agregado de los 5 niveles de verificación."""
    nivel_1_ejecucion: bool = False
    nivel_2_tests: Optional[TestResult] = None
    nivel_3_lint: Optional[LintResult] = None
    nivel_4_similitud: float = 0.0
    nivel_5_stress: Optional[StressResult] = None
    confianza: float = 0.0  # Calculada sobre los 5 niveles
    detalles: Dict[str, Any] = field(default_factory=dict)
