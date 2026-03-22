"""
YeyoOS — Módulo Investigador
Capas 5.28–5.32 — Capa 5: Órganos

Pipeline de investigación autónoma: buscar, evaluar, ensamblar, verificar, almacenar.
Incluye micro-tareas, razonamiento extendido, caché de patrones y selector de modelo.
"""

from .modelos import ResultadoBusqueda, InvestigacionCompleta, PasoInvestigacion
from .modelos_selector import ModeloConfig
from .pipeline import PipelineInvestigador
from .selector_modelo import SelectorModelo

__all__ = [
    "ResultadoBusqueda",
    "InvestigacionCompleta",
    "PasoInvestigacion",
    "PipelineInvestigador",
    "ModeloConfig",
    "SelectorModelo",
]
