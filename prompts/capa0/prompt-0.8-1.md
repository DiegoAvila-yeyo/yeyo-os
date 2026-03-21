## ═══════════════════════════════════════
## MICRO-FASE 0.8 — Ollama
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.8-1 [CLI] — Instalar Ollama

```
Estamos construyendo YeyoOS. Micro-fase 0.8, Prompt 1 de 2: instalar Ollama para inferencia de IA local.

Entorno: WSL2 Ubuntu, GTX 1060 3GB VRAM. Micro-fases 0.0-0.7 completadas.

IMPORTANTE: Ollama necesita GPU drivers (que instalaremos en 0.10). Por ahora instalar y verificar que corre en CPU. La aceleración GPU vendrá después.

EJECUTAR:
1. Instalar Ollama:
   curl -fsSL https://ollama.ai/install.sh | sh

2. Verificar que el servicio está corriendo:
   systemctl status ollama
   Si no está corriendo:
   sudo systemctl enable --now ollama

3. Esperar 5 segundos y verificar el API:
   curl http://localhost:11434/api/tags

4. Descargar modelo ligero para verificación:
   ollama pull qwen2.5:0.5b
   (Este es el más pequeño, solo para test. El 3b lo usaremos después.)

5. Agregar a .env:
   # Ollama
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:0.5b

6. Actualizar .env.example:
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:0.5b

VERIFICAR:
- [ ] Ollama corriendo: `systemctl status ollama` → active
- [ ] API responde: `curl -s http://localhost:11434/api/tags | head` → JSON con models
- [ ] Modelo descargado: `ollama list` → qwen2.5:0.5b listado
- [ ] Puerto 11434: `ss -tlnp | grep 11434` → ollama

SI FALLA:
- Install script falla: descargar binario manualmente de github.com/ollama/ollama
- Puerto ocupado: verificar con ss y matar proceso
- Sin GPU: Ollama corre en CPU (más lento pero funcional)

NO HACER:
- No descargar modelos grandes aún (3b necesita GPU configurada)
- No configurar GPU aún (eso es 0.10)
- No exponer Ollama a red externa

GATE: Ollama corriendo en localhost:11434, modelo 0.5b descargado y listado.
```
