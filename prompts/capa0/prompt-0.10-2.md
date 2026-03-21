## ═══════════════════════════════════════
## MICRO-FASE 0.10 — GPU Drivers + NVIDIA Container
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.10-2 [CLI] — Descargar modelo real y NVIDIA container toolkit

```
Estamos construyendo YeyoOS. Micro-fase 0.10, Prompt 2 de 2: descargar modelo de IA real y configurar GPU para containers.

PREREQUISITO: Prompt 0.10-1 completado (GPU visible + CUDA instalado).

EJECUTAR:
1. Descargar el modelo real que usaremos (qwen2.5:3b):
   ollama pull qwen2.5:3b
   (Esto tarda 2-5 minutos, ~2GB de descarga)

2. Verificar VRAM usage con el modelo real:
   En una terminal: watch -n 1 nvidia-smi
   En otra terminal: ollama run qwen2.5:3b "Explain what is AI in 2 sentences"
   → nvidia-smi debe mostrar VRAM usage ~1800MB durante inferencia

3. Instalar NVIDIA Container Toolkit para Podman:
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt update
   sudo apt install -y nvidia-container-toolkit
   sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

4. Verificar GPU en container:
   podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi

5. Actualizar .env con modelo real:
   Cambiar OLLAMA_MODEL en .env:
   OLLAMA_MODEL=qwen2.5:3b

6. Actualizar test de Ollama para usar modelo real:
   Editar tests/test_ollama.py y correr:
   pytest tests/test_ollama.py -v

VERIFICAR:
- [ ] Modelo 3b descargado: `ollama list` → qwen2.5:3b
- [ ] VRAM ~1800MB durante uso: nvidia-smi muestra uso
- [ ] VRAM vuelve a ~0 cuando idle: nvidia-smi post-inferencia
- [ ] GPU en container: `podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi` → muestra GPU
- [ ] Tests pasan con modelo real: `pytest tests/test_ollama.py -v` → 3 passed

SI FALLA:
- OOM con 3b: usar qwen2.5:1.5b como fallback
- NVIDIA container toolkit no instala: verificar repos, usar --no-install-recommends
- GPU no visible en container: revisar CDI config, regenerar yaml

GATE: qwen2.5:3b funciona con GPU, VRAM <2GB durante uso, GPU accesible desde containers Podman.
```
