## ═══════════════════════════════════════
## MICRO-FASE 0.10 — GPU Drivers + NVIDIA Container
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.10-1 [CLI] — Instalar NVIDIA drivers en WSL2

```
Estamos construyendo YeyoOS. Micro-fase 0.10, Prompt 1 de 2: configurar GPU NVIDIA en WSL2 para Ollama y IA.

Entorno: WSL2 Ubuntu, GTX 1060 3GB. Micro-fases 0.0-0.9 completadas.

IMPORTANTE PARA WSL2: Los drivers NVIDIA se instalan en WINDOWS, no en WSL2. WSL2 usa el driver de Windows via GPU paravirtualization. Solo necesitamos las CUDA libraries dentro de WSL2.

EJECUTAR:
1. Verificar que GPU es visible desde WSL2:
   nvidia-smi
   Si funciona → ya tienes el driver de Windows. Continuar.
   Si NO funciona → necesitas instalar NVIDIA drivers en Windows primero.

2. Instalar CUDA toolkit para WSL2:
   wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
   sudo dpkg -i cuda-keyring_1.1-1_all.deb
   sudo apt update
   sudo apt install -y cuda-toolkit-12-4

3. Agregar CUDA al PATH:
   echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
   echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc

4. Verificar CUDA:
   nvcc --version
   nvidia-smi

5. Reiniciar Ollama para que detecte GPU:
   sudo systemctl restart ollama
   Esperar 5 segundos.

6. Verificar que Ollama usa GPU:
   curl -s http://localhost:11434/api/tags
   ollama run qwen2.5:0.5b "Say GPU test" --verbose 2>&1 | grep -i gpu

VERIFICAR:
- [ ] nvidia-smi funciona: muestra GTX 1060 con 3GB
- [ ] CUDA version: `nvcc --version` → 12.x
- [ ] VRAM visible: `nvidia-smi --query-gpu=memory.total --format=csv` → ~3072 MiB
- [ ] Ollama detecta GPU: logs muestran CUDA/GPU
- [ ] Inferencia más rápida: comparar tiempo vs CPU

SI FALLA:
- nvidia-smi no funciona: instalar driver NVIDIA en Windows, reiniciar WSL
- CUDA no instala: verificar que el repo de NVIDIA WSL está configurado
- Ollama no detecta GPU: `OLLAMA_GPU_LAYER=99 ollama serve` para forzar

NO HACER:
- NO instalar drivers NVIDIA Linux (usamos los de Windows en WSL2)
- NO instalar nvidia-docker (usamos Podman)

GATE: nvidia-smi muestra GTX 1060 3GB, CUDA toolkit funcional, Ollama usa GPU.
```
