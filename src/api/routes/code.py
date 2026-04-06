"""
YeyoOS — Code Node API
Endpoint directo para generación de código via Code Dojo.
No requiere pre-registro de nodo.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("yeyoos.api.code")

router = APIRouter(prefix="/api/v1/code", tags=["code"])

_ia_provider = None
_code_ia_provider = None
_memory_service = None


def set_ia_provider(ia):
    global _ia_provider
    _ia_provider = ia


def set_code_ia_provider(ia):
    global _code_ia_provider
    _code_ia_provider = ia


def set_memory_service(ms):
    global _memory_service
    _memory_service = ms


class CodeGenerateRequest(BaseModel):
    prompt: str
    language: str = "python"


@router.post("/generate")
async def generate_code(request: CodeGenerateRequest) -> dict:
    """Genera código usando el Code Dojo (pipeline de 12 agentes) con modelo especializado."""
    ia = _code_ia_provider or _ia_provider
    if not ia:
        raise HTTPException(status_code=503, detail="IA provider no inicializado")

    try:
        from src.nodes.code.dojo import CodeDojo
        dojo = CodeDojo(ia, memory_service=_memory_service)
        resultado = await dojo.ejecutar(
            pedido=request.prompt,
            lenguaje=request.language,
            incluir_arquitectura=False,
        )
        return {
            "codigo": resultado.codigo_final,
            "score": resultado.score_critico,
            "aprobado": resultado.exito,
            "resumen": resultado.resumen(),
            "lenguaje": resultado.lenguaje,
            "ast_valido": resultado.ast_valido,
            "tests_pasaron": resultado.tests_pasaron,
            "tests_output": resultado.tests_output[:500] if resultado.tests_output else "",
            "score_seguridad": resultado.score_seguridad,
            "score_performance": resultado.score_performance,
            "razon_falla": resultado.razon_falla,
        }
    except Exception as e:
        logger.error(f"Error generando código: {e}")
        raise HTTPException(status_code=500, detail=str(e))
