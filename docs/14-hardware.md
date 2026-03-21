# 14 — Hardware: Compatibilidad y Gestión de Recursos

## Resumen

YeyoOS se adapta a **cualquier hardware**: desde una GTX 1060 3GB hasta multi-GPU con aceleradores dedicados. Gracias a la arquitectura hexagonal y Ollama como capa de abstracción, el mismo código funciona en NVIDIA, AMD, Intel o CPU puro. **Cero cambios de código** al cambiar de hardware.

## Soporte de GPU

### Compatibilidad Actual

```
┌─────────────────────────────────────────────────────────┐
│                    OLLAMA ABSTRAE TODO                    │
│                                                          │
│  Tu código:  ollama.generate(model="qwen2.5-coder")    │
│              ↓ siempre igual, sin importar el hardware   │
├──────────────┬──────────────┬────────────────────────────┤
│   NVIDIA     │     AMD      │        Intel               │
│   CUDA       │    ROCm      │       oneAPI               │
│              │              │                            │
│  GTX 10xx    │  RX 6000     │   Arc A-Series            │
│  RTX 20xx    │  RX 7000     │   Arc B-Series            │
│  RTX 30xx    │  RX 7900     │   Flex Series             │
│  RTX 40xx    │  Radeon Pro  │   Data Center GPU Max     │
│  RTX 50xx    │              │                            │
└──────────────┴──────────────┴────────────────────────────┘
```

### Auto-Detección en Instalación

```
Instalación de YeyoOS:
  1. Detectar GPU → lspci | grep -i vga
  2. Identificar fabricante y modelo
  3. Instalar driver correcto automáticamente:
     - NVIDIA → CUDA toolkit + nvidia-driver
     - AMD    → ROCm + amdgpu driver
     - Intel  → oneAPI + i915/xe driver
     - Ninguna → modo CPU (más lento pero funcional)
  4. Instalar Ollama (detecta GPU automáticamente)
  5. Verificar con ollama run hello → ✓

El usuario NUNCA toca drivers ni configuraciones.
```

## NPU — Neural Processing Units (Futuro)

```
Los NPUs son procesadores dedicados para IA integrados en el CPU.
Ventaja: siempre disponibles, bajo consumo, no compiten con la GPU.

┌────────────────────────────────────────────────────────┐
│  Fabricante        Plataforma            TOPS          │
├────────────────────────────────────────────────────────┤
│  Intel             Meteor Lake           10-11 TOPS    │
│  Intel             Lunar Lake            48 TOPS       │
│  AMD               XDNA (Ryzen AI)      50 TOPS       │
│  Qualcomm          Hexagon (Snapdragon)  45 TOPS       │
│  Apple             Neural Engine (M1+)   15-38 TOPS    │
└────────────────────────────────────────────────────────┘

TOPS = Trillions of Operations Per Second
Para referencia: GTX 1060 ≈ 4.4 TFLOPS

Caso de uso en YeyoOS:
  - NPU maneja inferencia ligera (clasificación, embeddings)
  - GPU queda libre para tareas pesadas (generación, entrenamiento)
  - = Dos procesadores IA trabajando EN PARALELO
```

## Hardware IA Especializado

```
┌────────────────────────────────────────────────────────────────┐
│  Dispositivo      Precio     Rendimiento   Conexión    Nota   │
├────────────────────────────────────────────────────────────────┤
│  Google Coral USB  $60       4 TOPS        USB 3.0     Solo   │
│                                                        visión │
│                                                               │
│  Hailo-8 M.2      $100-200  26 TOPS       M.2/PCIe   Multi-  │
│                                                        tarea  │
│                                                               │
│  Tenstorrent       ~$300+    Variable      PCIe x16   RISC-V,│
│  (Wormhole)                                            futuro │
│                                                               │
│  Groq LPU          Cloud     500+ tok/s    API/Cloud  Ultra-  │
│                    only                                rápido │
└────────────────────────────────────────────────────────────────┘
```

### Tabla Comparativa Completa

```
┌──────────────┬───────────┬──────────┬───────────┬──────────────┬─────────────┐
│ Hardware     │ Precio    │ TOPS/    │ Consumo   │ Caso de uso  │ Disponible  │
│              │           │ TFLOPS   │           │ principal    │             │
├──────────────┼───────────┼──────────┼───────────┼──────────────┼─────────────┤
│ CPU (i7)     │ Incluido  │ ~0.5     │ 65-125W   │ Fallback     │ HOY         │
│ GTX 1060 3GB│ $150-200  │ 4.4 TF   │ 120W      │ Todo-en-uno  │ HOY         │
│ RTX 3060 12G│ $250      │ 12.7 TF  │ 170W      │ Upgrade ideal│ HOY         │
│ RTX 4090    │ $1500+    │ 82.6 TF  │ 450W      │ Máximo local │ HOY         │
│ Google Coral │ $60       │ 4 TOPS   │ 2W        │ Visión edge  │ HOY         │
│ Hailo-8     │ $100-200  │ 26 TOPS  │ 2.5W      │ IA dedicada  │ HOY         │
│ NPU Intel   │ Incluido  │ 10-48    │ ~5W       │ IA integrada │ 2024+       │
│ NPU AMD     │ Incluido  │ 50 TOPS  │ ~5W       │ IA integrada │ 2024+       │
│ Tenstorrent  │ $300+     │ Variable │ 75-300W   │ Entrenamiento│ PRÓXIMO     │
│ Groq LPU    │ Cloud     │ 500+t/s  │ Cloud     │ Inferencia   │ CLOUD ONLY  │
└──────────────┴───────────┴──────────┴───────────┴──────────────┴─────────────┘
```

## Arquitectura Hexagonal: IAHardwareProvider

```
┌─────────────────────────────────────────┐
│           YeyoOS Core                    │
│                                          │
│   HardwareManager                        │
│     ├── get_best_for_task(task_type)    │
│     ├── detect_all_hardware()           │
│     └── get_status()                    │
│              │                           │
│              ▼                           │
│   IAHardwareProvider (interface)         │
│     ├── load_model(name, config)        │
│     ├── generate(prompt, params)        │
│     ├── get_capabilities()              │
│     ├── get_vram_available()            │
│     └── unload_model()                  │
│              │                           │
├──────────────┼───────────────────────────┤
│              ▼                           │
│   Implementaciones:                      │
│   ┌──────────┬──────────┬──────────┐    │
│   │NvidiaGPU │ AMDGPU   │  NPU     │    │
│   │Provider  │ Provider │ Provider │    │
│   ├──────────┼──────────┼──────────┤    │
│   │  Groq    │Tenstorrent│ Coral   │    │
│   │ Provider │ Provider │ Provider │    │
│   ├──────────┴──────────┴──────────┤    │
│   │       CPU Provider (fallback)  │    │
│   └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### Implementación HardwareManager

```python
import subprocess
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HardwareType(Enum):
    NVIDIA_GPU = "nvidia_gpu"
    AMD_GPU = "amd_gpu"
    INTEL_GPU = "intel_gpu"
    NPU = "npu"
    CORAL = "coral"
    HAILO = "hailo"
    TENSTORRENT = "tenstorrent"
    GROQ = "groq"
    CPU = "cpu"


class TaskType(Enum):
    LLM_INFERENCE = "llm_inference"
    IMAGE_GENERATION = "image_generation"
    EMBEDDING = "embedding"
    TRAINING = "training"
    VISION = "vision"
    SPEECH = "speech"
    COMPOSITOR = "compositor"


@dataclass
class HardwareCapabilities:
    hardware_type: HardwareType
    name: str
    vram_mb: int = 0
    tops: float = 0.0
    supports_training: bool = False
    supports_inference: bool = True
    power_watts: float = 0.0
    available: bool = True


class IAHardwareProvider(ABC):
    """Interfaz hexagonal para proveedores de hardware IA."""

    @abstractmethod
    def get_capabilities(self) -> HardwareCapabilities:
        pass

    @abstractmethod
    async def load_model(self, model_name: str, config: dict = None) -> bool:
        pass

    @abstractmethod
    async def generate(self, prompt: str, params: dict = None) -> str:
        pass

    @abstractmethod
    async def get_vram_available(self) -> int:
        pass

    @abstractmethod
    async def unload_model(self) -> bool:
        pass


class NvidiaGPUProvider(IAHardwareProvider):
    """Proveedor para GPUs NVIDIA via CUDA/Ollama."""

    def __init__(self):
        self.current_model = None
        self._detect()

    def _detect(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader"],
                capture_output=True, text=True
            )
            parts = result.stdout.strip().split(", ")
            self.gpu_name = parts[0]
            self.vram_total = int(parts[1].replace(" MiB", ""))
        except (FileNotFoundError, IndexError):
            self.gpu_name = "Unknown NVIDIA"
            self.vram_total = 0

    def get_capabilities(self) -> HardwareCapabilities:
        return HardwareCapabilities(
            hardware_type=HardwareType.NVIDIA_GPU,
            name=self.gpu_name,
            vram_mb=self.vram_total,
            supports_training=True,
            supports_inference=True,
            power_watts=120.0,
        )

    async def load_model(self, model_name: str, config: dict = None) -> bool:
        # Ollama maneja la carga del modelo en CUDA automáticamente
        self.current_model = model_name
        return True

    async def generate(self, prompt: str, params: dict = None) -> str:
        # Delegado a Ollama que usa CUDA internamente
        pass

    async def get_vram_available(self) -> int:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free",
             "--format=csv,noheader"],
            capture_output=True, text=True
        )
        return int(result.stdout.strip().replace(" MiB", ""))

    async def unload_model(self) -> bool:
        self.current_model = None
        return True


class CPUProvider(IAHardwareProvider):
    """Fallback: todo en CPU. Lento pero siempre funciona."""

    def get_capabilities(self) -> HardwareCapabilities:
        return HardwareCapabilities(
            hardware_type=HardwareType.CPU,
            name="CPU Fallback",
            vram_mb=0,
            supports_training=True,
            supports_inference=True,
        )

    async def load_model(self, model_name: str, config: dict = None) -> bool:
        return True

    async def generate(self, prompt: str, params: dict = None) -> str:
        pass

    async def get_vram_available(self) -> int:
        return 0  # CPU usa RAM, no VRAM

    async def unload_model(self) -> bool:
        return True


class HardwareManager:
    """Detecta y gestiona todo el hardware IA disponible."""

    def __init__(self):
        self.providers: list[IAHardwareProvider] = []
        self.detect_all_hardware()

    def detect_all_hardware(self):
        """Auto-detecta todo el hardware IA disponible."""
        self.providers = []

        # NVIDIA GPU
        if shutil.which("nvidia-smi"):
            self.providers.append(NvidiaGPUProvider())

        # AMD GPU
        if shutil.which("rocm-smi"):
            from yeyo.hardware.amd import AMDGPUProvider
            self.providers.append(AMDGPUProvider())

        # Intel GPU
        if shutil.which("xpu-smi"):
            from yeyo.hardware.intel import IntelGPUProvider
            self.providers.append(IntelGPUProvider())

        # Google Coral
        if self._detect_coral():
            from yeyo.hardware.coral import CoralProvider
            self.providers.append(CoralProvider())

        # Hailo
        if self._detect_hailo():
            from yeyo.hardware.hailo import HailoProvider
            self.providers.append(HailoProvider())

        # CPU siempre disponible como fallback
        self.providers.append(CPUProvider())

    def get_best_for_task(self, task_type: TaskType) -> IAHardwareProvider:
        """Selecciona el mejor hardware para cada tipo de tarea."""
        preferences = {
            TaskType.LLM_INFERENCE: [
                HardwareType.NVIDIA_GPU, HardwareType.AMD_GPU,
                HardwareType.INTEL_GPU, HardwareType.GROQ,
                HardwareType.NPU, HardwareType.CPU
            ],
            TaskType.IMAGE_GENERATION: [
                HardwareType.NVIDIA_GPU, HardwareType.AMD_GPU,
                HardwareType.INTEL_GPU, HardwareType.CPU
            ],
            TaskType.EMBEDDING: [
                HardwareType.NPU, HardwareType.HAILO,
                HardwareType.NVIDIA_GPU, HardwareType.CPU
            ],
            TaskType.TRAINING: [
                HardwareType.NVIDIA_GPU, HardwareType.AMD_GPU,
                HardwareType.TENSTORRENT, HardwareType.CPU
            ],
            TaskType.VISION: [
                HardwareType.CORAL, HardwareType.HAILO,
                HardwareType.NPU, HardwareType.NVIDIA_GPU,
                HardwareType.CPU
            ],
            TaskType.SPEECH: [
                HardwareType.NPU, HardwareType.NVIDIA_GPU,
                HardwareType.CPU
            ],
            TaskType.COMPOSITOR: [
                HardwareType.NVIDIA_GPU, HardwareType.AMD_GPU,
                HardwareType.CPU
            ],
        }

        preferred = preferences.get(task_type, [HardwareType.CPU])
        for hw_type in preferred:
            for provider in self.providers:
                caps = provider.get_capabilities()
                if caps.hardware_type == hw_type and caps.available:
                    return provider

        # Fallback a CPU
        return self.providers[-1]

    def get_status(self) -> dict:
        """Dashboard de estado de todo el hardware."""
        status = {"providers": [], "total_vram_mb": 0}
        for provider in self.providers:
            caps = provider.get_capabilities()
            status["providers"].append({
                "type": caps.hardware_type.value,
                "name": caps.name,
                "vram_mb": caps.vram_mb,
                "available": caps.available,
                "supports_training": caps.supports_training,
            })
            status["total_vram_mb"] += caps.vram_mb
        return status

    @staticmethod
    def _detect_coral() -> bool:
        try:
            result = subprocess.run(
                ["lsusb"], capture_output=True, text=True
            )
            return "Global Unichip" in result.stdout or "Google" in result.stdout
        except FileNotFoundError:
            return False

    @staticmethod
    def _detect_hailo() -> bool:
        try:
            result = subprocess.run(
                ["lspci"], capture_output=True, text=True
            )
            return "Hailo" in result.stdout
        except FileNotFoundError:
            return False
```

## GPU Scheduler: Cola de Prioridades

```
La GPU es UN recurso compartido. El scheduler decide quién la usa:

PRIORIDAD P0 — Compositor (SIEMPRE)
  → Renderizado de la interfaz del usuario
  → Nunca se interrumpe
  → Usa ~200-500 MB de VRAM reservados

PRIORIDAD P1 — Solicitud activa del usuario
  → "Hazme una función que..." → respuesta inmediata
  → Interrumpe P2 y P3
  → Tiempo máximo de espera: 0 segundos

PRIORIDAD P2 — Tareas en segundo plano
  → Indexación de código, pre-cálculo de embeddings
  → Se pausa cuando llega P1
  → Reanuda automáticamente cuando P1 termina

PRIORIDAD P3 — Idle / Nocturno
  → Entrenamiento del Dojo, LoRA training
  → Solo cuando no hay P1 ni P2
  → Se ejecuta principalmente de noche (2 AM - 10 AM)
```

### Implementación GpuScheduler

```python
import asyncio
import heapq
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Coroutine


class Priority(IntEnum):
    P0_COMPOSITOR = 0
    P1_USER_ACTIVE = 1
    P2_BACKGROUND = 2
    P3_IDLE_NIGHTLY = 3


@dataclass(order=True)
class GpuJob:
    priority: Priority
    submitted_at: float = field(compare=True)
    name: str = field(compare=False)
    coroutine_fn: Callable[[], Coroutine] = field(compare=False, repr=False)
    vram_required_mb: int = field(compare=False, default=0)
    cancellable: bool = field(compare=False, default=True)
    task: Any = field(compare=False, default=None, repr=False)


class GpuScheduler:
    """Scheduler de GPU con cola de prioridades para YeyoOS."""

    def __init__(self, total_vram_mb: int = 3072):
        self.total_vram_mb = total_vram_mb
        self.reserved_compositor_mb = 300
        self.available_vram_mb = total_vram_mb - self.reserved_compositor_mb
        self.queue: list[GpuJob] = []
        self.current_job: GpuJob | None = None
        self.running = False
        self._lock = asyncio.Lock()

    async def submit(self, name: str, priority: Priority,
                     coroutine_fn: Callable, vram_mb: int = 0,
                     cancellable: bool = True) -> GpuJob:
        """Envía un trabajo a la cola de la GPU."""
        job = GpuJob(
            priority=priority,
            submitted_at=time.time(),
            name=name,
            coroutine_fn=coroutine_fn,
            vram_required_mb=vram_mb,
            cancellable=cancellable,
        )

        async with self._lock:
            heapq.heappush(self.queue, job)

            # Si el nuevo job es más prioritario que el actual, preemptar
            if (self.current_job and
                    job.priority < self.current_job.priority and
                    self.current_job.cancellable):
                await self._preempt_current(reason=f"Preempted by {name}")

        if not self.running:
            asyncio.create_task(self._process_queue())

        return job

    async def _process_queue(self):
        """Procesa trabajos de la cola por prioridad."""
        self.running = True
        while self.queue:
            async with self._lock:
                if not self.queue:
                    break
                job = heapq.heappop(self.queue)
                self.current_job = job

            try:
                print(f"[GPU] Ejecutando: {job.name} (P{job.priority})")
                job.task = asyncio.create_task(job.coroutine_fn())
                await job.task
                print(f"[GPU] Completado: {job.name}")
            except asyncio.CancelledError:
                print(f"[GPU] Cancelado: {job.name}")
                # Re-encolar si fue preempted y es reanudable
                async with self._lock:
                    heapq.heappush(self.queue, job)
            except Exception as e:
                print(f"[GPU] Error en {job.name}: {e}")
            finally:
                async with self._lock:
                    self.current_job = None

        self.running = False

    async def _preempt_current(self, reason: str):
        """Interrumpe el trabajo actual para dar paso a uno más prioritario."""
        if self.current_job and self.current_job.task:
            print(f"[GPU] Preempting: {self.current_job.name} — {reason}")
            self.current_job.task.cancel()

    def get_queue_status(self) -> dict:
        """Estado actual del scheduler para el dashboard."""
        return {
            "total_vram_mb": self.total_vram_mb,
            "reserved_compositor_mb": self.reserved_compositor_mb,
            "available_vram_mb": self.available_vram_mb,
            "current_job": self.current_job.name if self.current_job else None,
            "current_priority": (f"P{self.current_job.priority}"
                                 if self.current_job else None),
            "queue_length": len(self.queue),
            "queued_jobs": [
                {"name": j.name, "priority": f"P{j.priority}",
                 "vram_mb": j.vram_required_mb}
                for j in sorted(self.queue)
            ],
        }
```

## Estrategias para Hardware Limitado (GTX 1060 3GB)

> **La 1060 es como un chef trabajando solo: puede preparar CUALQUIER plato, pero uno a la vez. La calidad es IDÉNTICA.**

### 1. Time-Slicing (Un trabajo a la vez)

```
Cola de trabajos → [Job A] [Job B] [Job C]
                      ↓
GPU:  ████ Job A ████ → ████ Job B ████ → ████ Job C ████
      completado         completado         completado

No hay paralelismo de GPU, pero el scheduler asegura
que lo más importante se ejecute primero (P0 > P1 > P2 > P3).
```

### 2. Model Swapping (Carga/descarga de modelos)

```
Solo UN modelo en VRAM a la vez:

Estado inicial: [Qwen2.5-Coder-3B cargado, 2.5GB VRAM]

Llega tarea de imagen:
  1. Descargar Qwen2.5-Coder-3B de VRAM (~1-2 seg)
  2. Cargar Stable Diffusion Turbo en VRAM (~2-3 seg)
  3. Generar imagen
  4. Descargar SD Turbo
  5. Recargar Qwen2.5-Coder-3B

Overhead de swap: ~2-5 segundos (aceptable para el usuario)
```

### 3. Chunked Processing (Procesamiento por trozos)

```
Generación de imagen 1024x1024 no cabe en 3GB de una vez:

SOLUCIÓN: Tile-based generation (generación por tiles)

  ┌──────┬──────┐
  │Tile 1│Tile 2│   Cada tile: 512x512
  │~700MB│~700MB│   VRAM por tile: ~700MB
  ├──────┼──────┤   Total: 4 tiles secuenciales
  │Tile 3│Tile 4│   Resultado: imagen 1024x1024 completa
  │~700MB│~700MB│
  └──────┴──────┘

  Tiempo: ~4x más lento que GPU grande, pero FUNCIONA.
```

### 4. CPU Offloading (División GPU/RAM)

```
Modelo demasiado grande para 3GB VRAM:

  Modelo total: 5GB
  ┌─────────────────────────────────────┐
  │  Capas 1-18 (60%)  → GPU (3GB VRAM)│  ← Rápido
  │  Capas 19-30 (40%) → CPU (RAM)     │  ← Más lento
  └─────────────────────────────────────┘

  Resultado: ~40% más lento que 100% GPU
  Pero: permite usar modelos más grandes de lo que
        la VRAM permite normalmente.
```

### 5. Adaptive Quality (Calidad adaptativa)

```
Preview rápido → resultado final:

Solicitud: "Genera una imagen de un castillo"

  Paso 1 (instantáneo): Preview 512x512, 10 steps
    → 3 segundos, baja calidad pero el usuario VE algo
    → "¿Es esto lo que querías?"

  Paso 2 (si aprueba): Full 1024x1024, 30 steps
    → 25 segundos, calidad máxima
    → Resultado final

  Beneficio: El usuario no espera 25 seg para descubrir
             que no era lo que quería.
```

## Smart Snapshots / Backups

```
La IA decide cuándo hacer backup basándose en contexto:

Triggers automáticos:
  - Antes de actualización del sistema
  - Después de instalar software nuevo
  - Cuando detecta cambios masivos en archivos
  - Antes de entrenamiento LoRA (por si falla)
  - Cada 24 horas si no se ha hecho uno

Triggers inteligentes:
  - "Voy a refactorizar todo el proyecto"
    → IA: snapshot antes de empezar
  - "Instala esto que encontré en un foro random"
    → IA: snapshot + sandbox de instalación
  - 3 AM, nada pasando
    → IA: buen momento para backup incremental
```

## Dashboard de Recursos

```
┌─────────────────────────────────────────────────────────┐
│  YEYO RESOURCE MANAGER                        [2:34 PM] │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  GPU: NVIDIA GTX 1060 3GB                               │
│  ┌──────────────────────────────────┐                   │
│  │████████████████████░░░░░░░░░░░░░│ 2.1/3.0 GB (70%)  │
│  └──────────────────────────────────┘                   │
│  Modelo: qwen2.5-coder-3B (2.1 GB)                     │
│  Modo: Inferencia activa                                 │
│                                                          │
│  RAM: 16 GB                                              │
│  ┌──────────────────────────────────┐                   │
│  │████████████░░░░░░░░░░░░░░░░░░░░░│ 6.2/16 GB (39%)   │
│  └──────────────────────────────────┘                   │
│  Sistema: 2.1 GB | Apps: 1.8 GB | Cache IA: 2.3 GB     │
│                                                          │
│  COLA DE TRABAJOS:                                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │ P0 │ Compositor          │ SIEMPRE │ 300 MB VRAM  │ │
│  │ P1 │ Chat: código Python │ ACTIVO  │ 2.1 GB VRAM  │ │
│  │ P2 │ Indexar proyecto    │ ESPERA  │ 500 MB VRAM  │ │
│  │ P3 │ Dojo challenge #847 │ ESPERA  │ 2.1 GB VRAM  │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  MODO ACTUAL: ⚡ Respuesta al usuario (P1 activo)       │
│  Siguiente: Indexar proyecto (cuando P1 termine)        │
└─────────────────────────────────────────────────────────┘
```

## Rutas de Upgrade

```
NIVEL 1 — $250: El salto más importante
┌─────────────────────────────────────────────┐
│  RTX 3060 12GB                               │
│  → 4x más VRAM (3GB → 12GB)                │
│  → Modelos de 7B-13B SIN offloading         │
│  → Generación de imágenes 1024px directo    │
│  → Training LoRA de modelos más grandes     │
│  → El mejor costo/beneficio posible         │
└─────────────────────────────────────────────┘

NIVEL 2 — $500: IA paralela
┌─────────────────────────────────────────────┐
│  RTX 3060 12GB + CPU con NPU + Google Coral │
│  → GPU: LLM + generación de imágenes       │
│  → NPU: embeddings + clasificación 24/7    │
│  → Coral: detección de objetos en cámara    │
│  → 3 procesadores IA en paralelo           │
└─────────────────────────────────────────────┘

NIVEL 3 — $1,500: Estación de trabajo IA
┌─────────────────────────────────────────────┐
│  RTX 4090 24GB + Tenstorrent PCIe           │
│  → Modelos de 70B cuantizados              │
│  → Entrenamiento de modelos completos      │
│  → Múltiples modelos simultáneos           │
│  → Tenstorrent: entrenamiento dedicado     │
└─────────────────────────────────────────────┘

NIVEL 4 — $5,000+: La bestia multi-GPU
┌─────────────────────────────────────────────┐
│  2x RTX 4090 + Tenstorrent + Hailo + NPU   │
│  → Modelos de 70B+ sin cuantizar           │
│  → Todo en paralelo: nada espera           │
│  → Entrenamiento de modelos desde cero     │
│  → Nivel de datacenter personal            │
└─────────────────────────────────────────────┘
```

## Filosofía de Hardware en YeyoOS

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║  "La 1060 es como un chef trabajando solo:                ║
║   puede preparar CUALQUIER plato,                         ║
║   pero uno a la vez.                                      ║
║   La calidad es IDÉNTICA."                                ║
║                                                           ║
║  Con más hardware, el chef tiene ayudantes:               ║
║   - NPU: el sous-chef que prepara ingredientes           ║
║   - Coral: el que vigila la puerta                        ║
║   - Más VRAM: cocina más grande = platos más grandes     ║
║   - Multi-GPU: varios chefs = varios platos a la vez     ║
║                                                           ║
║  Pero la RECETA (tu modelo, tu LoRA, tu RAG)             ║
║  es exactamente la misma. Solo cambia la velocidad.       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```
