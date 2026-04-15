"""
YeyoOS — Code Node API
Endpoint conversacional para generación de código via Code Dojo.
El flujo es: usuario escribe → planificador analiza → si falta info pregunta → si tiene todo genera.
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ia.interfaces import IAMessage

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


PLANNER_PROMPT = """Eres un planificador de código. Analiza el pedido del usuario y decide:

¿Tienes suficiente información para generar código de calidad?

Considera:
- ¿Queda claro QUÉ debe hacer el código?
- ¿Se puede inferir el lenguaje de programación? (si no se dice, pregunta)
- ¿Hay ambigüedad en los requisitos que podría llevar a código incorrecto?
- ¿Se necesita algún framework o biblioteca específica?

Si el pedido es CLARO y puedes generar código con confianza, responde SOLO con este JSON:
{"ready": true, "language": "LENGUAJE_DETECTADO", "task": "DESCRIPCIÓN_CLARA_DE_LA_TAREA"}

Si FALTA información o hay ambigüedad, responde SOLO con este JSON:
{"ready": false, "questions": "Tus preguntas al usuario escritas de forma natural y amigable"}

Ejemplos:
- "genera fibonacci" → {"ready": false, "questions": "¡Claro! Antes de generar, ¿en qué lenguaje lo necesitas? Y ¿quieres que retorne el n-ésimo número o toda la secuencia hasta n?"}
- "haz una función en Python que sume dos números" → {"ready": true, "language": "python", "task": "función que suma dos números"}
- "crea una API" → {"ready": false, "questions": "¡Me encanta! Para hacer una buena API necesito saber: ¿qué tipo de datos va a manejar? ¿En qué lenguaje/framework (FastAPI, Express, Gin...)? ¿Qué endpoints necesitas?"}
- "haz un merge sort en rust" → {"ready": true, "language": "rust", "task": "implementar algoritmo merge sort"}

Responde SOLO con el JSON, sin texto extra."""


class CodeChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)


class CodeGenerateRequest(BaseModel):
    prompt: str
    language: str = "python"


@router.post("/chat")
async def code_chat(request: CodeChatRequest) -> dict:
    """
    Endpoint conversacional inteligente para el nodo de código.
    Analiza el pedido y decide: preguntar o generar.
    """
    ia = _code_ia_provider or _ia_provider
    if not ia:
        raise HTTPException(status_code=503, detail="IA provider no inicializado")

    try:
        # Step 1: Planner analyzes the request
        planner_messages = [
            IAMessage(role="system", content=PLANNER_PROMPT),
        ]
        # Include conversation history for context
        for msg in request.history[-6:]:
            planner_messages.append(IAMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))
        planner_messages.append(IAMessage(role="user", content=request.message))

        planner_resp = await ia.chat(planner_messages, temperature=0.1)
        content = planner_resp.content.strip()

        # Parse planner response
        plan = _parse_json(content)

        if not plan or not plan.get("ready", False):
            # Planner needs more info — return questions
            questions = plan.get("questions", content) if plan else content
            return {
                "type": "question",
                "message": questions,
            }

        # Step 2: Planner says ready — generate code via Dojo
        language = plan.get("language", "python").lower()
        task = plan.get("task", request.message)

        from src.nodes.code.dojo import CodeDojo
        dojo = CodeDojo(ia, memory_service=_memory_service)
        resultado = await dojo.ejecutar(
            pedido=task,
            lenguaje=language,
            incluir_arquitectura=False,
        )

        return {
            "type": "code",
            "codigo": resultado.codigo_final,
            "score": resultado.score_critico,
            "aprobado": resultado.exito,
            "resumen": resultado.resumen(),
            "lenguaje": resultado.lenguaje,
            "ast_valido": resultado.ast_valido,
            "tests_pasaron": resultado.tests_pasaron,
            "tests_output": resultado.tests_output[:500] if resultado.tests_output else "",
            "func_verificado": resultado.func_verificado,
            "func_output": resultado.func_output[:500] if resultado.func_output else "",
            "score_seguridad": resultado.score_seguridad,
            "score_performance": resultado.score_performance,
            "razon_falla": resultado.razon_falla,
        }

    except Exception as e:
        logger.error(f"Error en code chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_code(request: CodeGenerateRequest) -> dict:
    """Genera código directamente (sin planificador). Para uso programático."""
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
            "type": "code",
            "codigo": resultado.codigo_final,
            "score": resultado.score_critico,
            "aprobado": resultado.exito,
            "resumen": resultado.resumen(),
            "lenguaje": resultado.lenguaje,
            "ast_valido": resultado.ast_valido,
            "tests_pasaron": resultado.tests_pasaron,
            "tests_output": resultado.tests_output[:500] if resultado.tests_output else "",
            "func_verificado": resultado.func_verificado,
            "func_output": resultado.func_output[:500] if resultado.func_output else "",
            "score_seguridad": resultado.score_seguridad,
            "score_performance": resultado.score_performance,
            "razon_falla": resultado.razon_falla,
        }
    except Exception as e:
        logger.error(f"Error generando código: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_json(text: str) -> dict | None:
    """Extrae JSON de una respuesta del LLM."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None
