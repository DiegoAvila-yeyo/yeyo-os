## ═══════════════════════════════════════
## MICRO-FASE 0.8 — Ollama
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.8-2 [CLI] — Verificar inferencia de Ollama

```
Estamos construyendo YeyoOS. Micro-fase 0.8, Prompt 2 de 2: verificar que Ollama puede hacer inferencia correctamente.

PREREQUISITO: Prompt 0.8-1 completado (Ollama instalado + modelo 0.5b).

EJECUTAR:
1. Test de inferencia básico:
   curl http://localhost:11434/api/generate -d '{
     "model": "qwen2.5:0.5b",
     "prompt": "Say hello in one word",
     "stream": false
   }'
   → Debe devolver JSON con "response" que contiene texto

2. Test de inferencia con streaming:
   curl http://localhost:11434/api/generate -d '{
     "model": "qwen2.5:0.5b",
     "prompt": "Count from 1 to 5",
     "stream": true
   }'
   → Debe devolver múltiples líneas JSON (streaming)

3. Test de chat API:
   curl http://localhost:11434/api/chat -d '{
     "model": "qwen2.5:0.5b",
     "messages": [{"role": "user", "content": "What is 2+2?"}],
     "stream": false
   }'
   → Debe responder con el resultado correcto

4. Crear script de test en Python:
   cd ~/yeyo-os
   source .venv/bin/activate
   
   Crear tests/test_ollama.py:
   import httpx
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   
   def test_ollama_api_reachable():
       r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
       assert r.status_code == 200
   
   def test_ollama_generate():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "prompt": "Say OK",
           "stream": False
       })
       assert r.status_code == 200
       assert "response" in r.json()
       assert len(r.json()["response"]) > 0
   
   def test_ollama_chat():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/chat", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "messages": [{"role": "user", "content": "Say hello"}],
           "stream": False
       })
       assert r.status_code == 200
       assert "message" in r.json()

5. Ejecutar tests:
   pytest tests/test_ollama.py -v

VERIFICAR:
- [ ] Generate (no stream) devuelve texto: response no vacío
- [ ] Generate (stream) devuelve múltiples chunks
- [ ] Chat API funciona: message con content
- [ ] 3 pytest tests pasan: `pytest tests/test_ollama.py -v` → 3 passed
- [ ] Latencia <30s en CPU: (0.5b es rápido incluso en CPU)

GATE: Ollama hace inferencia correctamente, 3 tests Python pasan, API generate + chat funcionan.
```
