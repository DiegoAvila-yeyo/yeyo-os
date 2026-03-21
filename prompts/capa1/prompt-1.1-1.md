## ═══════════════════════════════════════
## MICRO-FASE 1.1 — OllamaProvider
## Tipo: VSCODE | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.1-1 [VSCODE] — Implementar OllamaProvider concreto

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.1, Prompt 1 de 2: implementar el proveedor concreto de Ollama que satisface la interfaz IAProvider.

CONTEXTO:
- Capa 0 completada: Ollama corriendo con modelo qwen2.5:3b
- Micro-fase 1.0 completada: IAProvider, IAMessage, IAResponse definidos en src/ia/interfaces.py
- Ollama API: http://localhost:11434
- Endpoints Ollama: POST /api/generate, POST /api/chat, POST /api/embed, GET /api/tags
- Hardware: GTX 1060 3GB VRAM — timeout generoso (120s) porque el modelo es lento

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencia si no existe:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install httpx

2. Crear archivo src/ia/ollama_provider.py:

   Ruta: ~/yeyo-os/src/ia/ollama_provider.py
   Contenido:

   """
   YeyoOS — OllamaProvider (Adaptador Hexagonal)
   Micro-fase 1.1 — Capa 1: Esqueleto
   
   Implementación concreta de IAProvider para Ollama.
   Traduce las llamadas abstractas a la API REST de Ollama.
   """
   
   import time
   import os
   import json
   from typing import AsyncIterator
   
   import httpx
   
   from .interfaces import IAProvider, IAMessage, IAResponse
   
   
   class OllamaProvider(IAProvider):
       """Adaptador concreto para Ollama local."""
   
       def __init__(
           self,
           host: str | None = None,
           model: str | None = None,
           embedding_model: str | None = None,
           timeout: float = 120.0,
       ):
           self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
           self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
           self.embedding_model = embedding_model or os.getenv(
               "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
           )
           self.timeout = timeout
           self.client = httpx.AsyncClient(timeout=self.timeout)
   
       async def generate(
           self,
           prompt: str,
           system: str = "",
           temperature: float = 0.7,
       ) -> IAResponse:
           """Genera respuesta usando /api/generate."""
           start = time.monotonic()
           payload = {
               "model": self.model,
               "prompt": prompt,
               "stream": False,
               "options": {"temperature": temperature},
           }
           if system:
               payload["system"] = system
   
           response = await self.client.post(
               f"{self.host}/api/generate",
               json=payload,
           )
           response.raise_for_status()
           data = response.json()
   
           latency = (time.monotonic() - start) * 1000
           tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
   
           return IAResponse(
               content=data.get("response", ""),
               model=self.model,
               tokens_used=tokens,
               latency_ms=round(latency, 2),
           )
   
       async def chat(
           self,
           messages: list[IAMessage],
           temperature: float = 0.7,
       ) -> IAResponse:
           """Genera respuesta usando /api/chat con historial."""
           start = time.monotonic()
           formatted_messages = [
               {"role": msg.role, "content": msg.content} for msg in messages
           ]
   
           response = await self.client.post(
               f"{self.host}/api/chat",
               json={
                   "model": self.model,
                   "messages": formatted_messages,
                   "stream": False,
                   "options": {"temperature": temperature},
               },
           )
           response.raise_for_status()
           data = response.json()
   
           latency = (time.monotonic() - start) * 1000
           tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
   
           return IAResponse(
               content=data.get("message", {}).get("content", ""),
               model=self.model,
               tokens_used=tokens,
               latency_ms=round(latency, 2),
           )
   
       async def chat_stream(
           self,
           messages: list[IAMessage],
           temperature: float = 0.7,
       ) -> AsyncIterator[str]:
           """Genera respuesta en streaming, yield de chunks."""
           formatted_messages = [
               {"role": msg.role, "content": msg.content} for msg in messages
           ]
   
           async with self.client.stream(
               "POST",
               f"{self.host}/api/chat",
               json={
                   "model": self.model,
                   "messages": formatted_messages,
                   "stream": True,
                   "options": {"temperature": temperature},
               },
           ) as response:
               response.raise_for_status()
               async for line in response.aiter_lines():
                   if line.strip():
                       data = json.loads(line)
                       content = data.get("message", {}).get("content", "")
                       if content:
                           yield content
   
       async def get_embedding(self, text: str) -> list[float]:
           """Genera embedding usando /api/embed."""
           response = await self.client.post(
               f"{self.host}/api/embed",
               json={
                   "model": self.embedding_model,
                   "input": text,
               },
           )
           response.raise_for_status()
           data = response.json()
           embeddings = data.get("embeddings", [[]])
           return embeddings[0] if embeddings else []
   
       async def health_check(self) -> bool:
           """Verifica que Ollama está corriendo consultando /api/tags."""
           try:
               response = await self.client.get(f"{self.host}/api/tags")
               return response.status_code == 200
           except (httpx.ConnectError, httpx.TimeoutException):
               return False
   
       def get_model_name(self) -> str:
           """Retorna el nombre del modelo configurado."""
           return self.model
   
       def get_max_tokens(self) -> int:
           """Retorna el budget máximo de tokens para YeyoOS."""
           return 4000
   
       async def close(self):
           """Cierra el cliente HTTP."""
           await self.client.aclose()

3. Actualizar src/ia/__init__.py:

   Ruta: ~/yeyo-os/src/ia/__init__.py
   Contenido:
   from .interfaces import IAProvider, IAMessage, IAResponse
   from .ollama_provider import OllamaProvider

VERIFICAR:
- [ ] Archivo src/ia/ollama_provider.py existe
- [ ] OllamaProvider hereda de IAProvider
- [ ] Todos los 7 métodos abstractos implementados
- [ ] Import funciona: `from src.ia.ollama_provider import OllamaProvider`
- [ ] No hay errores de sintaxis: `python -c "from src.ia.ollama_provider import OllamaProvider; print('OK')"`

SI FALLA:
- httpx no instalado: `pip install httpx`
- Import error en interfaces: verificar que micro-fase 1.0 está completada
- Syntaxis async iterator: requiere Python 3.11+

NO HACER:
- No ejecutar tests de integración con Ollama real todavía (eso es prompt 1.1-2)
- No agregar retry logic aún (eso viene en Capa 2)
- No cachear respuestas
- No agregar logging (eso es micro-fase 1.11)

GATE: OllamaProvider importable, satisface IAProvider completa, sin errores de sintaxis.
```
