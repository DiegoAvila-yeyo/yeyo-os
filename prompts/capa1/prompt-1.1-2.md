## ═══════════════════════════════════════
## MICRO-FASE 1.1 — OllamaProvider Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.1-2 [VSCODE] — Tests del OllamaProvider

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.1, Prompt 2 de 2: tests completos para OllamaProvider.

CONTEXTO:
- Micro-fase 1.0 completada: IAProvider interface definida
- Prompt 1.1-1 completado: OllamaProvider implementado en src/ia/ollama_provider.py
- Ollama corriendo en http://localhost:11434 con modelo qwen2.5:3b
- Necesitamos tests unitarios (con mock) Y tests de integración (con Ollama real)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencias de test si no existen:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install pytest pytest-asyncio respx

2. Crear archivo tests/unit/ia/test_ollama_provider.py:

   Ruta: ~/yeyo-os/tests/unit/ia/test_ollama_provider.py
   Contenido:

   """
   Tests unitarios para OllamaProvider — Micro-fase 1.1
   Usan mocks para no depender de Ollama corriendo.
   """
   
   import pytest
   import httpx
   import respx
   from src.ia.ollama_provider import OllamaProvider
   from src.ia.interfaces import IAProvider, IAMessage, IAResponse
   
   
   @pytest.fixture
   def provider():
       return OllamaProvider(
           host="http://localhost:11434",
           model="qwen2.5:3b",
       )
   
   
   class TestOllamaProviderBasic:
       """Tests básicos sin red."""
   
       def test_is_ia_provider(self, provider):
           assert isinstance(provider, IAProvider)
   
       def test_default_host(self):
           p = OllamaProvider()
           assert "localhost" in p.host
           assert "11434" in p.host
   
       def test_default_model(self):
           p = OllamaProvider()
           assert p.model == "qwen2.5:3b"
   
       def test_custom_host_and_model(self):
           p = OllamaProvider(host="http://custom:9999", model="llama3:8b")
           assert p.host == "http://custom:9999"
           assert p.model == "llama3:8b"
   
       def test_get_model_name(self, provider):
           assert provider.get_model_name() == "qwen2.5:3b"
   
       def test_get_max_tokens(self, provider):
           assert provider.get_max_tokens() == 4000
   
   
   class TestOllamaProviderMocked:
       """Tests con HTTP mockeado."""
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_health_check_success(self, provider):
           respx.get("http://localhost:11434/api/tags").mock(
               return_value=httpx.Response(200, json={"models": []})
           )
           result = await provider.health_check()
           assert result is True
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_health_check_failure(self, provider):
           respx.get("http://localhost:11434/api/tags").mock(
               side_effect=httpx.ConnectError("Connection refused")
           )
           result = await provider.health_check()
           assert result is False
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_health_check_timeout(self, provider):
           respx.get("http://localhost:11434/api/tags").mock(
               side_effect=httpx.TimeoutException("Timeout")
           )
           result = await provider.health_check()
           assert result is False
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_generate_returns_ia_response(self, provider):
           respx.post("http://localhost:11434/api/generate").mock(
               return_value=httpx.Response(200, json={
                   "response": "Hola, soy YeyoOS",
                   "model": "qwen2.5:3b",
                   "eval_count": 10,
                   "prompt_eval_count": 5,
               })
           )
           result = await provider.generate("Saluda")
           assert isinstance(result, IAResponse)
           assert result.content == "Hola, soy YeyoOS"
           assert result.model == "qwen2.5:3b"
           assert result.tokens_used == 15
           assert result.latency_ms >= 0
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_generate_with_system_prompt(self, provider):
           respx.post("http://localhost:11434/api/generate").mock(
               return_value=httpx.Response(200, json={
                   "response": "OK",
                   "eval_count": 1,
                   "prompt_eval_count": 5,
               })
           )
           result = await provider.generate(
               prompt="Di OK",
               system="Eres un asistente conciso",
           )
           assert result.content == "OK"
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_chat_returns_ia_response(self, provider):
           respx.post("http://localhost:11434/api/chat").mock(
               return_value=httpx.Response(200, json={
                   "message": {"role": "assistant", "content": "¡Hola!"},
                   "model": "qwen2.5:3b",
                   "eval_count": 5,
                   "prompt_eval_count": 10,
               })
           )
           messages = [
               IAMessage(role="system", content="Eres YeyoOS"),
               IAMessage(role="user", content="Hola"),
           ]
           result = await provider.chat(messages)
           assert isinstance(result, IAResponse)
           assert result.content == "¡Hola!"
           assert result.tokens_used == 15
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_get_embedding_returns_vector(self, provider):
           fake_embedding = [0.1] * 768
           respx.post("http://localhost:11434/api/embed").mock(
               return_value=httpx.Response(200, json={
                   "embeddings": [fake_embedding]
               })
           )
           result = await provider.get_embedding("test text")
           assert isinstance(result, list)
           assert len(result) == 768
           assert all(isinstance(x, float) for x in result)
   
       @pytest.mark.asyncio
       @respx.mock
       async def test_generate_http_error_raises(self, provider):
           respx.post("http://localhost:11434/api/generate").mock(
               return_value=httpx.Response(500, text="Internal Server Error")
           )
           with pytest.raises(httpx.HTTPStatusError):
               await provider.generate("test")
   
       @pytest.mark.asyncio
       async def test_close_client(self, provider):
           await provider.close()
           # No debe lanzar excepción

3. Crear archivo tests/integration/ia/__init__.py:

   Ruta: ~/yeyo-os/tests/integration/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/integration/ia/__init__.py
   Contenido: (archivo vacío)

4. Crear archivo tests/integration/ia/test_ollama_integration.py:

   Ruta: ~/yeyo-os/tests/integration/ia/test_ollama_integration.py
   Contenido:

   """
   Tests de integración para OllamaProvider — Micro-fase 1.1
   Requieren Ollama corriendo con modelo qwen2.5:3b.
   Ejecutar con: pytest tests/integration/ -v -m integration
   """
   
   import pytest
   from src.ia.ollama_provider import OllamaProvider
   from src.ia.interfaces import IAMessage, IAResponse
   
   
   pytestmark = pytest.mark.integration
   
   
   @pytest.fixture
   async def provider():
       p = OllamaProvider()
       yield p
       await p.close()
   
   
   @pytest.mark.asyncio
   async def test_ollama_health_check(provider):
       result = await provider.health_check()
       assert result is True, "Ollama no está corriendo"
   
   
   @pytest.mark.asyncio
   async def test_ollama_generate(provider):
       result = await provider.generate("Responde solo con la palabra OK")
       assert isinstance(result, IAResponse)
       assert len(result.content) > 0
       assert result.tokens_used > 0
       assert result.latency_ms > 0
   
   
   @pytest.mark.asyncio
   async def test_ollama_chat(provider):
       messages = [
           IAMessage(role="system", content="Responde siempre en una sola palabra"),
           IAMessage(role="user", content="Di hola"),
       ]
       result = await provider.chat(messages)
       assert isinstance(result, IAResponse)
       assert len(result.content) > 0
   
   
   @pytest.mark.asyncio
   async def test_ollama_chat_stream(provider):
       messages = [
           IAMessage(role="user", content="Cuenta del 1 al 5"),
       ]
       chunks = []
       async for chunk in provider.chat_stream(messages):
           chunks.append(chunk)
       assert len(chunks) > 0
       full_response = "".join(chunks)
       assert len(full_response) > 0
   
   
   @pytest.mark.asyncio
   async def test_ollama_embedding(provider):
       result = await provider.get_embedding("YeyoOS es un sistema operativo AI-nativo")
       assert isinstance(result, list)
       assert len(result) > 0
       assert all(isinstance(x, float) for x in result)

5. Crear archivo pytest.ini (o actualizar si existe):

   Ruta: ~/yeyo-os/pytest.ini
   Contenido:
   [pytest]
   asyncio_mode = auto
   markers =
       integration: tests que requieren servicios externos (Ollama, PostgreSQL, etc)

6. Ejecutar tests unitarios:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/ia/ -v

7. Ejecutar tests de integración (solo si Ollama está corriendo):
   python -m pytest tests/integration/ia/ -v -m integration

VERIFICAR:
- [ ] Tests unitarios: TODOS pasan (0 failed)
- [ ] health_check mockeado funciona (success y failure)
- [ ] generate retorna IAResponse correctamente
- [ ] chat retorna IAResponse con contenido
- [ ] embedding retorna lista de floats
- [ ] Error HTTP se propaga correctamente
- [ ] Tests de integración pasan (si Ollama disponible)

SI FALLA:
- respx no instalado: `pip install respx`
- pytest-asyncio no instalado: `pip install pytest-asyncio`
- Import error: verificar __init__.py en todos los directorios
- Tests integración fallan: verificar que Ollama está corriendo con `curl http://localhost:11434/api/tags`
- Modelo no encontrado: `ollama pull qwen2.5:3b`

NO HACER:
- No mockear tests de integración (esos usan Ollama real)
- No hardcodear URLs en tests (usar el fixture provider)
- No agregar tests de rendimiento todavía
- No tests de concurrencia aún

GATE: Todos los tests unitarios pasan + tests de integración pasan con Ollama corriendo.
```
