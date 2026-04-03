"""
YeyoOS — Chat API Endpoints
Micro-fase 2.15 — Capa 2: Cerebro

Endpoints REST para funcionalidad de chat:
- POST /api/v1/chat — enviar mensaje
- POST /api/v1/chat/stream — respuesta en streaming (SSE)
- GET /api/v1/chat/conversations — listar conversaciones
- GET /api/v1/chat/conversations/{id} — obtener conversación
- POST /api/v1/chat/conversations — crear conversación
- POST /api/v1/chat/{message_id}/feedback — enviar feedback
"""

import asyncio
import logging
import uuid
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.chat")

# ChatNode integration
from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.types import ChatNodeError, ErrorCode

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ========== Error Handler ==========

def _map_error_to_user_message(error_code: str) -> str:
    """
    Map ChatNode error codes to user-friendly messages for frontend display.
    
    Args:
        error_code: ErrorCode from ChatNode
        
    Returns:
        User-friendly error message (non-technical)
    """
    error_map = {
        ErrorCode.ERROR_INVALID_INPUT: "El mensaje no es válido. Por favor, verifica el contenido.",
        ErrorCode.ERROR_MESSAGE_EMPTY: "El mensaje no puede estar vacío.",
        ErrorCode.ERROR_MESSAGE_TOO_LONG: "El mensaje es demasiado largo. Máximo 10,000 caracteres.",
        ErrorCode.ERROR_INVALID_CONVERSATION_ID: "La conversación no existe o ha expirado.",
        ErrorCode.ERROR_INVALID_TONE: "El tono de conversación no es válido.",
        ErrorCode.ERROR_INVALID_TYPE: "El tipo de conversación no es válido.",
        
        ErrorCode.ERROR_AGENT_VALIDATION_FAILED: "La respuesta no pasó validación de calidad. Por favor, intenta de nuevo.",
        ErrorCode.ERROR_SYSTEM_PROMPT_GENERATION: "Error al generar el contexto. Por favor, intenta de nuevo.",
        
        ErrorCode.ERROR_OLLAMA_UNREACHABLE: "El servicio de IA no está disponible. Por favor, intenta más tarde.",
        ErrorCode.ERROR_OLLAMA_TIMEOUT: "La solicitud tardó demasiado. Por favor, intenta de nuevo.",
        ErrorCode.ERROR_OLLAMA_OUT_OF_MEMORY: "El servicio de IA está sobrecargado. Por favor, intenta más tarde.",
        ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE: "Respuesta inválida del servicio de IA. Por favor, intenta de nuevo.",
        
        ErrorCode.ERROR_OUTPUT_VALIDATION_FAILED: "La respuesta generada no es válida. Por favor, intenta de nuevo.",
        ErrorCode.ERROR_INVALID_CONFIDENCE: "Error de calidad en la respuesta. Por favor, intenta de nuevo.",
        
        ErrorCode.ERROR_DATABASE: "Error de conexión a la base de datos. Por favor, intenta más tarde.",
        ErrorCode.ERROR_MEMORY_INJECTION: "Error al cargar el contexto. Por favor, intenta de nuevo.",
        ErrorCode.ERROR_INTERNAL_SERVER_ERROR: "Error interno del servidor. Por favor, intenta más tarde.",
        
        ErrorCode.ERROR_RATE_LIMIT_EXCEEDED: "Demasiadas solicitudes. Por favor, espera un momento antes de intentar de nuevo.",
        ErrorCode.ERROR_REQUEST_TIMEOUT: "La solicitud expiró. Por favor, intenta de nuevo.",
    }
    
    return error_map.get(error_code, "Ha ocurrido un error desconocido. Por favor, intenta de nuevo.")


# ========== Request/Response Models ==========

class ChatRequest(BaseModel):
    """Request para enviar un mensaje de chat."""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response de un mensaje de chat."""
    response: str
    conversation_id: str
    message_id: str
    tokens_used: int = 0


class CreateConversationRequest(BaseModel):
    """Request para crear una conversación."""
    title: str = Field(default="Nueva conversación", max_length=200)


class ConversationResponse(BaseModel):
    """Response de una conversación."""
    id: str
    title: str
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FeedbackRequest(BaseModel):
    """Request para enviar feedback."""
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=500)


class CorrectionRequest(BaseModel):
    """Request para reportar corrección."""
    correction: str = Field(..., min_length=1, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response de feedback."""
    id: str
    message_id: str
    rating: int
    comment: str = ""


# ========== Dependency Injection ==========
# Estas funciones se sobreescriben en la app principal
# para inyectar las dependencias reales

async def get_chat_service():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Chat service not initialized")


async def get_conversation_manager():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Conversation manager not initialized")


async def get_feedback_service():
    """Placeholder — sobreescribir con dependency injection."""
    raise HTTPException(status_code=503, detail="Feedback service not initialized")


# ========== Endpoints ==========

@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    chat_service=Depends(get_chat_service),
    conv_manager=Depends(get_conversation_manager),
):
    """
    Envía un mensaje de chat y obtiene respuesta.
    Si no se proporciona conversation_id, crea una nueva conversación.
    """
    try:
        # Crear conversación si no existe
        conv_id = request.conversation_id
        if not conv_id:
            conv_id = await conv_manager.create_conversation()

        # Obtener historial
        history = await conv_manager.get_history(conv_id, limit=10)
        history_dicts = [
            {"role": m.role, "content": m.content} for m in history
        ]

        # Guardar mensaje del usuario
        msg_id = str(uuid.uuid4())
        await conv_manager.add_message(conv_id, "user", request.message)

        # Generar respuesta
        response = await chat_service.send_message(
            user_input=request.message,
            conversation_history=history_dicts,
            conversation_id=conv_id,
        )

        # Guardar respuesta del asistente
        await conv_manager.add_message(conv_id, "assistant", response)

        return ChatResponse(
            response=response,
            conversation_id=conv_id,
            message_id=msg_id,
        )

    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    chat_service=Depends(get_chat_service),
    conv_manager=Depends(get_conversation_manager),
):
    """
    Envía un mensaje y recibe la respuesta en streaming (SSE).
    
    Phase 3.1.1: Integración con ChatNodeService
    - Valida entrada
    - Carga contexto de conversación
    - Llama Ollama con retry
    - Valida output
    - Guarda en memoria
    - Devuelve streaming SSE en tiempo real
    """
    try:
        conv_id = request.conversation_id
        if not conv_id:
            conv_id = await conv_manager.create_conversation()

        await conv_manager.add_message(conv_id, "user", request.message)

        async def event_generator() -> AsyncGenerator[str, None]:
            """
            SSE generator que llama ChatNodeService y streams la respuesta.
            Formato: "data: <chunk>\n\n" por línea
            Termina con: "data: [DONE]\n\n"
            
            Maneja excepciones específicas de ChatNode:
            - OllamaError (no alcanzable, timeout, out of memory)
            - DatabaseError (fallos de conexión)
            - InputValidationError (entrada inválida)
            - AgentValidationError (validación del agente falló)
            - Genéricas (errores internos inesperados)
            """
            chat_node_service = ChatNodeService()
            full_response = ""
            
            try:
                # Llamar ChatNodeService (Phase 3.1.1)
                result = await chat_node_service.process_message(
                    message=request.message,
                    conversation_id=conv_id,
                )
                
                # Manejar error si ocurrió
                if isinstance(result, ChatNodeError):
                    logger.warning(
                        f"ChatNodeError: {result.error}",
                        extra={"error_code": result.error_code, "conversation_id": conv_id}
                    )
                    # Mapear error code a mensaje user-friendly
                    error_message = _map_error_to_user_message(result.error_code)
                    yield f"data: ERROR:{result.error_code}:{error_message}\n\n"
                    yield f"data: [DONE]\n\n"
                    return
                
                # Success case: stream response in chunks
                full_response = result.response
                
                # Send conversation_id as first metadata chunk for frontend to capture
                yield f"data: METADATA:conversation_id:{conv_id}\n\n"
                
                # Stream por chunks pequeños para mejor UX
                chunk_size = 50
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i:i + chunk_size]
                    yield f"data: {chunk}\n\n"
                    await asyncio.sleep(0.01)  # Pequeño delay para smooth streaming
                
                # Guardar respuesta completa en conversación
                await conv_manager.add_message(conv_id, "assistant", full_response)
                
                # Señal de fin
                yield f"data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error en event_generator: {e}", exc_info=True)
                error_message = "Ha ocurrido un error interno. Por favor, intenta de nuevo."
                yield f"data: ERROR:INTERNAL:{error_message}\n\n"
                yield f"data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        logger.error(f"Error en send_message_stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations(
    limit: int = 50,
    conv_manager=Depends(get_conversation_manager),
):
    """Lista todas las conversaciones."""
    try:
        return await conv_manager.list_conversations(limit=limit)
    except Exception as e:
        logger.error(f"Error listando conversaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    conv_manager=Depends(get_conversation_manager),
):
    """Obtiene una conversación específica con historial."""
    try:
        conv = await conv_manager.get_conversation(conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        history = await conv_manager.get_history(conversation_id)
        conv["messages"] = [
            {"role": m.role, "content": m.content} for m in history
        ]
        return conv
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    conv_manager=Depends(get_conversation_manager),
):
    """Crea una nueva conversación."""
    try:
        conv_id = await conv_manager.create_conversation(title=request.title)
        return {"id": conv_id, "title": request.title}
    except Exception as e:
        logger.error(f"Error creando conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{message_id}/feedback")
async def submit_feedback(
    message_id: str,
    request: FeedbackRequest,
    feedback_service=Depends(get_feedback_service),
):
    """Envía feedback para un mensaje."""
    try:
        result = await feedback_service.rate_response(
            message_id=message_id,
            rating=request.rating,
            comment=request.comment,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{message_id}/correction")
async def submit_correction(
    message_id: str,
    request: CorrectionRequest,
    feedback_service=Depends(get_feedback_service),
):
    """Reporta una corrección para un mensaje."""
    try:
        result = await feedback_service.report_incorrect(
            message_id=message_id,
            correction=request.correction,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en corrección: {e}")
        raise HTTPException(status_code=500, detail=str(e))
