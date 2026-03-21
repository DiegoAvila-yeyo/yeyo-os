## ═══════════════════════════════════════
## MICRO-FASE 2.15 — Chat API Endpoints
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.15-1 [VSCODE] — Implementar endpoints FastAPI para chat

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.15 de Capa 2 (Cerebro): implementar los endpoints de la API REST para chat con FastAPI, incluyendo streaming via SSE.

CONTEXTO:
- Capa 1 completada: FastAPI base configurada en src/api/
- Micro-fases 2.5-2.14 completadas: ChatService, ContextualChatService, ConversationManager, FeedbackService funcionando
- Endpoints necesarios: chat, streaming, conversaciones CRUD, feedback
- Streaming via Server-Sent Events (SSE) para respuestas en tiempo real
- Token budget: 4000 total
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p src/api/routes

2. Crear archivo src/api/routes/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/api/routes/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/api/routes/chat.py:

   Ruta: ~/yeyo-os/src/api/routes/chat.py
   Contenido:

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

   import logging
   import uuid
   from typing import Optional

   from fastapi import APIRouter, HTTPException, Depends
   from fastapi.responses import StreamingResponse
   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyoos.api.chat")

   router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


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
       """
       try:
           conv_id = request.conversation_id
           if not conv_id:
               conv_id = await conv_manager.create_conversation()

           history = await conv_manager.get_history(conv_id, limit=10)
           history_dicts = [
               {"role": m.role, "content": m.content} for m in history
           ]

           await conv_manager.add_message(conv_id, "user", request.message)

           async def event_generator():
               full_response = []
               async for chunk in chat_service.send_message_stream(
                   user_input=request.message,
                   conversation_history=history_dicts,
                   conversation_id=conv_id,
               ):
                   full_response.append(chunk)
                   yield f"data: {chunk}\n\n"

               # Guardar respuesta completa
               complete = "".join(full_response)
               await conv_manager.add_message(conv_id, "assistant", complete)
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
           logger.error(f"Error en streaming: {e}")
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

4. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/api/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/unit/api/test_chat_routes.py
   Contenido:

   """
   Tests para Chat API Endpoints — Micro-fase 2.15
   Tests unitarios con TestClient de FastAPI.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from fastapi import FastAPI
   from fastapi.testclient import TestClient
   from src.api.routes.chat import router, get_chat_service, get_conversation_manager, get_feedback_service
   from src.ia.interfaces import IAMessage


   @pytest.fixture
   def mock_chat_service():
       service = AsyncMock()
       service.send_message.return_value = "Respuesta de YeyoOS"
       return service


   @pytest.fixture
   def mock_conv_manager():
       cm = AsyncMock()
       cm.create_conversation.return_value = "conv-123"
       cm.get_history.return_value = []
       cm.list_conversations.return_value = [
           {"id": "conv-1", "title": "Test", "message_count": 0}
       ]
       cm.get_conversation.return_value = {
           "id": "conv-1",
           "title": "Test",
           "message_count": 0,
       }
       return cm


   @pytest.fixture
   def mock_feedback_service():
       fs = AsyncMock()
       fs.rate_response.return_value = {
           "id": "fb-1",
           "message_id": "msg-1",
           "rating": 5,
           "comment": "",
       }
       return fs


   @pytest.fixture
   def client(mock_chat_service, mock_conv_manager, mock_feedback_service):
       app = FastAPI()
       app.include_router(router)

       app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
       app.dependency_overrides[get_conversation_manager] = lambda: mock_conv_manager
       app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service

       return TestClient(app)


   class TestChatEndpoint:
       """Tests del endpoint POST /api/v1/chat."""

       def test_send_message(self, client):
           response = client.post(
               "/api/v1/chat",
               json={"message": "Hola YeyoOS"},
           )
           assert response.status_code == 200
           data = response.json()
           assert "response" in data
           assert "conversation_id" in data
           assert "message_id" in data

       def test_send_empty_message_rejected(self, client):
           response = client.post(
               "/api/v1/chat",
               json={"message": ""},
           )
           assert response.status_code == 422  # Validation error

       def test_send_with_conversation_id(self, client):
           response = client.post(
               "/api/v1/chat",
               json={"message": "Test", "conversation_id": "conv-123"},
           )
           assert response.status_code == 200


   class TestConversationEndpoints:
       """Tests de endpoints de conversaciones."""

       def test_list_conversations(self, client):
           response = client.get("/api/v1/chat/conversations")
           assert response.status_code == 200
           assert isinstance(response.json(), list)

       def test_create_conversation(self, client):
           response = client.post(
               "/api/v1/chat/conversations",
               json={"title": "Mi conversación"},
           )
           assert response.status_code == 200
           assert "id" in response.json()

       def test_get_conversation(self, client):
           response = client.get("/api/v1/chat/conversations/conv-1")
           assert response.status_code == 200

       def test_get_conversation_not_found(self, client, mock_conv_manager):
           mock_conv_manager.get_conversation.return_value = None
           response = client.get(
               "/api/v1/chat/conversations/nonexistent"
           )
           assert response.status_code == 404


   class TestFeedbackEndpoints:
       """Tests de endpoints de feedback."""

       def test_submit_feedback(self, client):
           response = client.post(
               "/api/v1/chat/msg-1/feedback",
               json={"rating": 5, "comment": "Excelente"},
           )
           assert response.status_code == 200

       def test_feedback_invalid_rating(self, client):
           response = client.post(
               "/api/v1/chat/msg-1/feedback",
               json={"rating": 0},
           )
           assert response.status_code == 422

       def test_feedback_rating_6_rejected(self, client):
           response = client.post(
               "/api/v1/chat/msg-1/feedback",
               json={"rating": 6},
           )
           assert response.status_code == 422

       def test_submit_correction(self, client, mock_feedback_service):
           mock_feedback_service.report_incorrect.return_value = {
               "feedback_id": "fb-1",
               "correction": "Es Diego",
               "memory_created": "mem-1",
           }
           response = client.post(
               "/api/v1/chat/msg-1/correction",
               json={"correction": "Es Diego, no Juan"},
           )
           assert response.status_code == 200


   class TestAllEndpointsExist:
       """Verificar que todos los endpoints existen."""

       def test_chat_post_exists(self, client):
           response = client.post("/api/v1/chat", json={"message": "test"})
           assert response.status_code != 404

       def test_stream_post_exists(self, client):
           response = client.post(
               "/api/v1/chat/stream",
               json={"message": "test"},
           )
           assert response.status_code != 404

       def test_conversations_get_exists(self, client):
           response = client.get("/api/v1/chat/conversations")
           assert response.status_code != 404

       def test_conversations_post_exists(self, client):
           response = client.post(
               "/api/v1/chat/conversations",
               json={"title": "test"},
           )
           assert response.status_code != 404

       def test_feedback_post_exists(self, client):
           response = client.post(
               "/api/v1/chat/msg-1/feedback",
               json={"rating": 3},
           )
           assert response.status_code != 404

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install httpx  # Required by TestClient
   python -m pytest tests/unit/api/test_chat_routes.py -v

VERIFICAR:
- [ ] Archivo src/api/routes/chat.py existe
- [ ] POST /api/v1/chat — enviar mensaje funciona
- [ ] POST /api/v1/chat/stream — streaming SSE funciona
- [ ] GET /api/v1/chat/conversations — lista conversaciones
- [ ] GET /api/v1/chat/conversations/{id} — obtiene conversación
- [ ] POST /api/v1/chat/conversations — crea conversación
- [ ] POST /api/v1/chat/{msg_id}/feedback — envía feedback
- [ ] POST /api/v1/chat/{msg_id}/correction — reporta corrección
- [ ] Mensajes vacíos rechazados (422)
- [ ] Ratings inválidos rechazados (422)
- [ ] TODOS los tests pasan

SI FALLA:
- FastAPI no instalado: `pip install fastapi`
- httpx no instalado: `pip install httpx` (para TestClient)
- Import error: verificar que micro-fases 2.5-2.14 están completadas
- Dependency injection: verificar overrides en tests

NO HACER:
- No implementar autenticación todavía (eso viene en capas superiores)
- No agregar rate limiting todavía
- No exponer endpoints internos de debug en producción
- No permitir mensajes mayores a 2000 caracteres

GATE: Todos los endpoints existen y funcionan, validación de inputs, streaming SSE, CRUD de conversaciones, feedback con correcciones, todos los tests pasan.
```
