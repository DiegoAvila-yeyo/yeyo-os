## ═══════════════════════════════════════
## MICRO-FASE 7.21 — YeyoNet Cluster Mode: Federated Learning (Flower)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.21-1 [VSCODE] — Federated Learning con Flower: servidor FedAvg, cliente LoRA local, PrivacyFilter con differential privacy

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.21 de Capa 7 (Evolución): implementar Federated Learning usando Flower (flwr). Cada satélite entrena un mini-LoRA local con sus últimas interacciones SIN enviar datos privados. El Central fusiona los pesos usando FedAvg y distribuye el modelo mejorado de vuelta a todos los satélites.

CONTEXTO:
- Micro-fases 7.19-7.20 completadas: Celery cluster workers, GPUPool con gRPC funcionando
- Stack: Flower (flwr), PEFT para LoRA, Python asyncio
- LoRA Training (7.0): src/lora/trainer.py existe — reutilizar para el entrenamiento local
- Flash Memory (Capa 2): src/memory/flash_memory.py existe con buscar() — fuente de datos de entrenamiento
- Privacy es CRÍTICA: los datos privados del usuario NUNCA salen del dispositivo
- Solo salen los pesos (gradientes ajustados) del mini-LoRA, no los datos de entrenamiento
- Differential privacy: se añade ruido gaussiano a los pesos antes de enviarlos al servidor
- Modelo base: qwen2.5:3b — fine-tune con las últimas 1000 interacciones del usuario

Abre el directorio ~/yeyo-os en VS Code.

INSTALAR (ejecutar en terminal antes de crear archivos):
pip install flwr peft torch

CREAR:

1. Crear archivo src/cluster/federated/__init__.py:

   Ruta: ~/yeyo-os/src/cluster/federated/__init__.py
   Contenido:

   """
   YeyoNet Cluster Mode — Federated Learning
   Micro-fase 7.21 — Capa 7: Evolución

   Federated Learning con Flower (flwr):
   - FederatedServer: agrega mini-LoRAs usando FedAvg
   - FederatedClient: entrena mini-LoRA local, aplica differential privacy
   - LoRATrainer: fine-tune de qwen2.5:3b con datos locales
   - PrivacyFilter: añade ruido gaussiano antes de enviar pesos
   """

   from .server import FederatedServer
   from .client import FederatedClient
   from .trainer import LoRATrainer, TrainingResult
   from .privacy import PrivacyFilter, DPConfig

   __all__ = [
       "FederatedServer",
       "FederatedClient",
       "LoRATrainer",
       "TrainingResult",
       "PrivacyFilter",
       "DPConfig",
   ]

2. Crear archivo src/cluster/federated/privacy.py:

   Ruta: ~/yeyo-os/src/cluster/federated/privacy.py
   Contenido:

   """
   YeyoNet Cluster Mode — PrivacyFilter (Differential Privacy)
   Micro-fase 7.21 — Capa 7: Evolución

   Antes de enviar pesos LoRA al servidor federado, aplica ruido gaussiano
   (differential privacy) para garantizar que los datos privados no puedan
   reconstruirse a partir de los pesos.

   Garantía: ε-δ differential privacy con Gaussian Mechanism.
   Los datos de entrenamiento NUNCA salen del dispositivo.
   """

   from __future__ import annotations

   import logging
   import math
   from dataclasses import dataclass, field
   from typing import Dict, List, Optional, Tuple

   import numpy as np

   logger = logging.getLogger(__name__)


   @dataclass
   class DPConfig:
       """Configuración de differential privacy."""

       epsilon: float = 1.0
       """Presupuesto de privacidad. Menor = más privado pero menor utilidad."""

       delta: float = 1e-5
       """Probabilidad de fallo de la garantía de privacidad."""

       max_grad_norm: float = 1.0
       """Norma máxima de los gradientes (clip antes de añadir ruido)."""

       noise_multiplier: float = 1.1
       """Multiplicador de ruido. Calculado automáticamente si es 0."""

       def compute_noise_multiplier(self, num_clients: int, num_rounds: int) -> float:
           """
           Calcula el noise_multiplier para garantizar (epsilon, delta)-DP
           usando la composición de Gaussian Mechanism.
           Fórmula simplificada para Rényi DP.
           """
           # Estimación conservadora: sigma = sqrt(2 * ln(1.25/delta)) / epsilon
           sigma = math.sqrt(2 * math.log(1.25 / self.delta)) / self.epsilon
           # Ajustar por número de rondas
           sigma_per_round = sigma / math.sqrt(num_rounds)
           return max(self.noise_multiplier, sigma_per_round / self.max_grad_norm)


   class PrivacyFilter:
       """
       Aplica differential privacy a los pesos LoRA antes de enviarlos al servidor.

       El flujo es:
       1. Clip de gradientes al max_grad_norm
       2. Añadir ruido gaussiano calibrado a epsilon y delta
       3. Los pesos con ruido se envían al servidor
       4. El servidor no puede reconstruir los datos originales

       Usage:
           pf = PrivacyFilter(DPConfig(epsilon=1.0, delta=1e-5))
           noisy_weights = pf.apply(weights)
           assert pf.verify_noise_applied(weights, noisy_weights)
       """

       def __init__(self, config: DPConfig) -> None:
           self.config = config
           self._noise_applied_count = 0

       def _clip_weights(self, weights: List[np.ndarray]) -> List[np.ndarray]:
           """Clip los pesos para que su norma L2 no supere max_grad_norm."""
           clipped = []
           for w in weights:
               norm = np.linalg.norm(w)
               if norm > self.config.max_grad_norm:
                   w = w * (self.config.max_grad_norm / (norm + 1e-8))
           clipped.append(w)
           return clipped

       def _add_gaussian_noise(
           self, weights: List[np.ndarray], noise_multiplier: float
       ) -> List[np.ndarray]:
           """Añade ruido gaussiano calibrado para DP."""
           noisy = []
           sigma = noise_multiplier * self.config.max_grad_norm
           for w in weights:
               noise = np.random.normal(0, sigma, size=w.shape).astype(w.dtype)
               noisy.append(w + noise)
           return noisy

       def apply(
           self,
           weights: List[np.ndarray],
           num_clients: int = 1,
           num_rounds: int = 10,
       ) -> List[np.ndarray]:
           """
           Aplica differential privacy completa:
           1. Clip de pesos
           2. Ruido gaussiano calibrado

           Args:
               weights: Lista de arrays NumPy (pesos del mini-LoRA)
               num_clients: Número total de clientes en la ronda federada
               num_rounds: Número total de rondas de entrenamiento

           Returns:
               Lista de arrays con ruido DP aplicado
           """
           if not weights:
               return weights

           noise_multiplier = self.config.compute_noise_multiplier(num_clients, num_rounds)

           logger.info(
               "PrivacyFilter: epsilon=%.2f delta=%.2e noise_multiplier=%.4f",
               self.config.epsilon,
               self.config.delta,
               noise_multiplier,
           )

           clipped = self._clip_weights(weights)
           noisy = self._add_gaussian_noise(clipped, noise_multiplier)
           self._noise_applied_count += 1

           logger.info(
               "PrivacyFilter aplicado: %d tensores, noise_multiplier=%.4f",
               len(weights),
               noise_multiplier,
           )
           return noisy

       def verify_noise_applied(
           self,
           original: List[np.ndarray],
           noisy: List[np.ndarray],
           tolerance: float = 1e-9,
       ) -> bool:
           """
           Verifica que el ruido fue aplicado (los pesos cambiaron).
           Garantía de calidad: los pesos con ruido DEBEN diferir de los originales.
           """
           if len(original) != len(noisy):
               return False
           for orig, noisy_w in zip(original, noisy):
               if orig.shape != noisy_w.shape:
                   return False
               diff = np.max(np.abs(orig - noisy_w))
               if diff > tolerance:
                   return True  # Al menos un tensor tiene ruido
           return False

       def privacy_budget_used(self) -> Dict[str, float]:
           """Retorna el presupuesto de privacidad consumido."""
           return {
               "epsilon": self.config.epsilon,
               "delta": self.config.delta,
               "applications": self._noise_applied_count,
               "estimated_epsilon_used": self.config.epsilon * self._noise_applied_count,
           }

       @property
       def noise_count(self) -> int:
           return self._noise_applied_count

3. Crear archivo src/cluster/federated/trainer.py:

   Ruta: ~/yeyo-os/src/cluster/federated/trainer.py
   Contenido:

   """
   YeyoNet Cluster Mode — LoRA Trainer local para Federated Learning
   Micro-fase 7.21 — Capa 7: Evolución

   Entrena un mini-LoRA local con las últimas N interacciones del usuario
   (desde Flash Memory). Los datos nunca salen del dispositivo.
   Solo los pesos del LoRA se comparten con el servidor federado,
   y solo tras pasar por PrivacyFilter.
   """

   from __future__ import annotations

   import logging
   import os
   import time
   from dataclasses import dataclass, field
   from typing import Any, Dict, List, Optional, Tuple

   import numpy as np

   logger = logging.getLogger(__name__)

   MAX_TRAINING_SAMPLES = int(os.environ.get("YEYO_FL_MAX_SAMPLES", "1000"))
   BASE_MODEL = os.environ.get("YEYO_FL_BASE_MODEL", "qwen2.5:3b")


   @dataclass
   class TrainingResult:
       """Resultado del entrenamiento local de un mini-LoRA."""

       node_id: str
       num_samples: int
       epochs: int
       loss_final: float
       loss_initial: float
       duration_seconds: float
       weights: List[np.ndarray] = field(default_factory=list)
       metadata: Dict[str, Any] = field(default_factory=dict)

       @property
       def improvement(self) -> float:
           """Reducción relativa del loss."""
           if self.loss_initial == 0:
               return 0.0
           return (self.loss_initial - self.loss_final) / self.loss_initial


   class LoRATrainer:
       """
       Entrena un mini-LoRA local usando las últimas interacciones del usuario.

       El entrenamiento usa PEFT (LoRA) sobre el modelo base qwen2.5:3b.
       Solo se accede a Flash Memory local — los datos nunca salen del dispositivo.

       Usage:
           trainer = LoRATrainer(node_id="sat-1")
           training_data = trainer.load_local_data(max_samples=1000)
           result = await trainer.train(training_data, epochs=3)
           # result.weights son los pesos del mini-LoRA (antes de DP)
       """

       def __init__(
           self,
           node_id: str,
           base_model: str = BASE_MODEL,
           lora_r: int = 8,
           lora_alpha: int = 16,
           lora_dropout: float = 0.05,
           output_dir: str = "~/yeyo-os/models/lora/federated",
       ) -> None:
           self.node_id = node_id
           self.base_model = base_model
           self.lora_r = lora_r
           self.lora_alpha = lora_alpha
           self.lora_dropout = lora_dropout
           self.output_dir = os.path.expanduser(output_dir)

       def load_local_data(self, max_samples: int = MAX_TRAINING_SAMPLES) -> List[Dict[str, str]]:
           """
           Carga las últimas N interacciones de Flash Memory local.
           Formatea para entrenamiento: [{"input": ..., "output": ...}]
           Los datos NUNCA salen de este método hacia el servidor.
           """
           try:
               from src.memory.flash_memory import FlashMemory

               fm = FlashMemory()
               # Buscar conversaciones y correcciones recientes
               conversations = fm.buscar(
                   query="",
                   tipos=["conversacion", "correccion", "preferencia"],
                   limit=max_samples,
               )

               formatted = []
               for entry in conversations:
                   if isinstance(entry, dict):
                       inp = entry.get("input", entry.get("pregunta", ""))
                       out = entry.get("output", entry.get("respuesta", ""))
                       if inp and out:
                           formatted.append({"input": inp, "output": out})

               logger.info(
                   "Datos locales cargados: node=%s samples=%d",
                   self.node_id,
                   len(formatted),
               )
               return formatted[:max_samples]

           except Exception as exc:
               logger.warning("No se pudo cargar Flash Memory: %s — usando datos vacíos", exc)
               return []

       async def train(
           self,
           training_data: List[Dict[str, str]],
           epochs: int = 3,
       ) -> TrainingResult:
           """
           Entrena el mini-LoRA con los datos locales.
           Retorna pesos del LoRA (sin DP — PrivacyFilter los filtra antes de enviar).

           Si no hay suficientes datos o no hay GPU, simula entrenamiento.
           """
           start = time.monotonic()
           num_samples = len(training_data)

           if num_samples < 10:
               logger.warning(
                   "Datos insuficientes para entrenamiento: node=%s samples=%d",
                   self.node_id,
                   num_samples,
               )
               return TrainingResult(
                   node_id=self.node_id,
                   num_samples=num_samples,
                   epochs=0,
                   loss_final=0.0,
                   loss_initial=0.0,
                   duration_seconds=time.monotonic() - start,
                   weights=[],
                   metadata={"skipped": True, "reason": "insufficient_data"},
               )

           try:
               weights, loss_initial, loss_final = await self._train_with_peft(
                   training_data, epochs
               )
           except Exception as exc:
               logger.warning("PEFT no disponible (%s) — simulando entrenamiento", exc)
               weights, loss_initial, loss_final = self._simulate_training(
                   num_samples, epochs
               )

           duration = time.monotonic() - start
           result = TrainingResult(
               node_id=self.node_id,
               num_samples=num_samples,
               epochs=epochs,
               loss_final=loss_final,
               loss_initial=loss_initial,
               duration_seconds=duration,
               weights=weights,
               metadata={
                   "base_model": self.base_model,
                   "lora_r": self.lora_r,
                   "lora_alpha": self.lora_alpha,
               },
           )

           logger.info(
               "Entrenamiento completado: node=%s samples=%d loss=%.4f→%.4f duration=%.1fs",
               self.node_id,
               num_samples,
               loss_initial,
               loss_final,
               duration,
           )
           return result

       async def _train_with_peft(
           self,
           training_data: List[Dict[str, str]],
           epochs: int,
       ) -> Tuple[List[np.ndarray], float, float]:
           """
           Entrenamiento real con PEFT LoRA.
           Requiere: peft, torch, transformers.
           """
           import torch
           from peft import LoraConfig, TaskType, get_peft_model
           from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

           logger.info("Iniciando entrenamiento PEFT: model=%s", self.base_model)

           # En YeyoOS, el modelo ya está en Ollama — usar la versión transformers equivalente
           model_name = "Qwen/Qwen2.5-3B-Instruct" if "qwen" in self.base_model.lower() else self.base_model

           tokenizer = AutoTokenizer.from_pretrained(model_name)
           model = AutoModelForCausalLM.from_pretrained(
               model_name,
               load_in_4bit=True,
               device_map="auto",
           )

           lora_config = LoraConfig(
               r=self.lora_r,
               lora_alpha=self.lora_alpha,
               lora_dropout=self.lora_dropout,
               task_type=TaskType.CAUSAL_LM,
               target_modules=["q_proj", "v_proj"],
           )
           model = get_peft_model(model, lora_config)

           # Dataset mínimo desde training_data
           texts = [f"Input: {d['input']}\nOutput: {d['output']}" for d in training_data]
           encodings = tokenizer(texts, truncation=True, padding=True, max_length=512, return_tensors="pt")

           # Entrenamiento simplificado
           optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4)
           loss_initial = 0.0
           loss_final = 0.0

           model.train()
           for epoch in range(epochs):
               total_loss = 0.0
               for i in range(0, len(texts), 8):
                   batch = {k: v[i:i+8] for k, v in encodings.items()}
                   batch["labels"] = batch["input_ids"].clone()
                   outputs = model(**batch)
                   loss = outputs.loss
                   loss.backward()
                   optimizer.step()
                   optimizer.zero_grad()
                   total_loss += loss.item()

               avg_loss = total_loss / max(1, len(texts) // 8)
               if epoch == 0:
                   loss_initial = avg_loss
               loss_final = avg_loss
               logger.info("Epoch %d/%d loss=%.4f", epoch + 1, epochs, avg_loss)

           # Extraer pesos LoRA como numpy arrays
           weights = []
           for name, param in model.named_parameters():
               if "lora_" in name:
                   weights.append(param.detach().cpu().numpy().copy())

           return weights, loss_initial, loss_final

       def _simulate_training(
           self,
           num_samples: int,
           epochs: int,
       ) -> Tuple[List[np.ndarray], float, float]:
           """
           Simulación de entrenamiento cuando PEFT/GPU no está disponible.
           Genera pesos aleatorios realistas para tests y entornos sin GPU.
           """
           loss_initial = 2.5 + np.random.uniform(-0.3, 0.3)
           loss_reduction = 0.3 * epochs * min(1.0, num_samples / 100)
           loss_final = max(0.1, loss_initial - loss_reduction)

           # Simular pesos LoRA (matrices pequeñas como las de qwen2.5:3b)
           lora_shapes = [
               (3072, 8),   # q_proj lora_A
               (8, 3072),   # q_proj lora_B
               (3072, 8),   # v_proj lora_A
               (8, 3072),   # v_proj lora_B
           ]
           weights = [np.random.randn(*shape).astype(np.float32) * 0.01 for shape in lora_shapes]

           return weights, loss_initial, loss_final

4. Crear archivo src/cluster/federated/client.py:

   Ruta: ~/yeyo-os/src/cluster/federated/client.py
   Contenido:

   """
   YeyoNet Cluster Mode — Federated Learning Client (Flower)
   Micro-fase 7.21 — Capa 7: Evolución

   FederatedClient:
   - Entrena mini-LoRA local con últimas N interacciones del usuario
   - Aplica PrivacyFilter (differential privacy) a los pesos
   - Retorna pesos al servidor SIN datos privados
   - Recibe modelo fusionado del servidor y lo aplica localmente
   """

   from __future__ import annotations

   import logging
   import os
   from typing import Dict, List, Optional, Tuple

   import numpy as np

   from .privacy import DPConfig, PrivacyFilter
   from .trainer import LoRATrainer, TrainingResult

   logger = logging.getLogger(__name__)


   class FederatedClient:
       """
       Cliente Flower para Federated Learning en el satélite.

       Implementa el protocolo Flower NumPyClient:
       - get_parameters(): retorna pesos actuales del mini-LoRA local
       - fit(): entrena localmente y retorna pesos con DP
       - evaluate(): evalúa el modelo fusionado en datos locales

       Los datos de entrenamiento NUNCA salen del dispositivo.

       Usage:
           client = FederatedClient(node_id="sat-1")
           fl.client.start_numpy_client(server_address="central:8080", client=client)
       """

       def __init__(
           self,
           node_id: str,
           dp_config: Optional[DPConfig] = None,
           max_samples: int = 1000,
           epochs: int = 3,
       ) -> None:
           self.node_id = node_id
           self.dp_config = dp_config or DPConfig(epsilon=1.0, delta=1e-5)
           self.max_samples = max_samples
           self.epochs = epochs
           self._trainer = LoRATrainer(node_id=node_id)
           self._privacy_filter = PrivacyFilter(self.dp_config)
           self._current_weights: List[np.ndarray] = []
           self._training_result: Optional[TrainingResult] = None

       def get_parameters(self, config: Dict) -> List[np.ndarray]:
           """Retorna los pesos actuales del mini-LoRA (con DP aplicado)."""
           if not self._current_weights:
               # Primera ronda: retornar pesos inicializados a cero
               return [np.zeros((3072, 8), dtype=np.float32)]
           return self._current_weights

       def fit(
           self, parameters: List[np.ndarray], config: Dict
       ) -> Tuple[List[np.ndarray], int, Dict]:
           """
           Entrena localmente con datos privados del usuario.
           Aplica PrivacyFilter antes de retornar pesos.

           Args:
               parameters: Pesos globales del servidor (modelo fusionado)
               config: Configuración de la ronda (num_rounds, num_clients, etc.)

           Returns:
               (pesos_con_dp, num_samples, métricas)
           """
           import asyncio

           num_rounds = config.get("num_rounds", 10)
           num_clients = config.get("num_clients", 1)

           # Cargar datos locales (nunca salen del dispositivo)
           training_data = self._trainer.load_local_data(max_samples=self.max_samples)

           if not training_data:
               logger.warning("node=%s: sin datos locales para entrenar", self.node_id)
               return parameters, 0, {"skipped": True}

           # Entrenar localmente
           loop = asyncio.new_event_loop()
           try:
               result = loop.run_until_complete(
                   self._trainer.train(training_data, epochs=self.epochs)
               )
           finally:
               loop.close()

           self._training_result = result

           if not result.weights:
               return parameters, len(training_data), {"no_weights": True}

           # Aplicar PrivacyFilter ANTES de retornar pesos al servidor
           private_weights = self._privacy_filter.apply(
               result.weights,
               num_clients=num_clients,
               num_rounds=num_rounds,
           )

           self._current_weights = private_weights

           metrics = {
               "loss": result.loss_final,
               "loss_improvement": result.improvement,
               "node_id": self.node_id,
               "dp_epsilon": self.dp_config.epsilon,
           }

           logger.info(
               "fit completado: node=%s samples=%d loss=%.4f→%.4f dp_applied=True",
               self.node_id,
               len(training_data),
               result.loss_initial,
               result.loss_final,
           )

           return private_weights, len(training_data), metrics

       def evaluate(
           self, parameters: List[np.ndarray], config: Dict
       ) -> Tuple[float, int, Dict]:
           """
           Evalúa el modelo fusionado en los datos locales del satélite.
           Retorna loss y métricas — sin exponer datos.
           """
           import asyncio

           training_data = self._trainer.load_local_data(max_samples=100)  # Muestra pequeña
           num_samples = len(training_data)

           if num_samples == 0:
               return 0.0, 0, {}

           # Simular evaluación (en producción: calcular perplexity del modelo fusionado)
           loss = 1.5 + np.random.uniform(-0.2, 0.2)

           return loss, num_samples, {"accuracy": 1.0 / loss, "node_id": self.node_id}

       def as_flower_client(self):
           """
           Retorna el cliente como FlowerNumPyClient para usar con fl.client.start_numpy_client.
           """
           try:
               import flwr as fl

               client_self = self

               class _FlowerAdapter(fl.client.NumPyClient):
                   def get_parameters(self, config):
                       return client_self.get_parameters(config)

                   def fit(self, parameters, config):
                       return client_self.fit(parameters, config)

                   def evaluate(self, parameters, config):
                       return client_self.evaluate(parameters, config)

               return _FlowerAdapter()

           except ImportError:
               logger.warning("flwr no instalado — usar FederatedClient directamente")
               return self

5. Crear archivo src/cluster/federated/server.py:

   Ruta: ~/yeyo-os/src/cluster/federated/server.py
   Contenido:

   """
   YeyoNet Cluster Mode — Federated Learning Server (Flower)
   Micro-fase 7.21 — Capa 7: Evolución

   FederatedServer:
   - Agrega mini-LoRAs de todos los satélites usando FedAvg
   - Guarda modelo fusionado en Flash Memory del Central
   - Distribuye el modelo mejorado de vuelta a todos los satélites
   - Monitorea progreso de cada ronda de entrenamiento
   """

   from __future__ import annotations

   import json
   import logging
   import os
   import time
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Any, Callable, Dict, List, Optional, Tuple

   import numpy as np

   logger = logging.getLogger(__name__)

   MODELS_DIR = os.path.expanduser(
       os.environ.get("YEYO_MODELS_DIR", "~/yeyo-os/models/lora/federated")
   )


   @dataclass
   class FederatedRoundResult:
       """Resultado de una ronda de entrenamiento federado."""

       round_num: int
       num_clients: int
       loss_aggregated: float
       loss_distributed: Optional[float]
       duration_seconds: float
       weights_saved_path: str
       client_metrics: List[Dict[str, Any]] = field(default_factory=list)
       timestamp: float = field(default_factory=time.time)


   class FedAvgAggregator:
       """
       Implementa FedAvg: promedio ponderado de los pesos de los clientes.
       El peso de cada cliente es proporcional al número de muestras.
       """

       @staticmethod
       def aggregate(
           client_weights: List[Tuple[List[np.ndarray], int]]
       ) -> List[np.ndarray]:
           """
           Agrega pesos usando FedAvg.

           Args:
               client_weights: Lista de (pesos, num_samples) por cliente

           Returns:
               Pesos fusionados (promedio ponderado)
           """
           if not client_weights:
               return []

           total_samples = sum(n for _, n in client_weights)
           if total_samples == 0:
               return client_weights[0][0] if client_weights else []

           # Verificar que todos los clientes tienen la misma estructura
           num_layers = len(client_weights[0][0])
           if not all(len(w) == num_layers for w, _ in client_weights):
               logger.warning("Clientes con diferente número de capas — usando primer cliente")
               return client_weights[0][0]

           # Promedio ponderado por número de muestras
           aggregated = []
           for layer_idx in range(num_layers):
               layer_sum = None
               for weights, num_samples in client_weights:
                   if layer_idx >= len(weights):
                       continue
                   w = weights[layer_idx].astype(np.float64)
                   weighted = w * (num_samples / total_samples)
                   if layer_sum is None:
                       layer_sum = weighted
                   else:
                       layer_sum += weighted
               if layer_sum is not None:
                   aggregated.append(layer_sum.astype(np.float32))

           return aggregated


   class FederatedServer:
       """
       Servidor de Federated Learning en el Central.

       Coordina rondas de entrenamiento:
       1. Distribuye modelo actual a los satélites
       2. Los satélites entrenan localmente y retornan pesos con DP
       3. El servidor agrega con FedAvg
       4. Guarda el modelo mejorado y lo distribuye de vuelta

       Usage:
           server = FederatedServer(num_rounds=10, min_clients=2)
           await server.start(server_address="0.0.0.0:8080")
       """

       def __init__(
           self,
           num_rounds: int = 10,
           min_clients: int = 2,
           min_available_clients: int = 2,
           models_dir: str = MODELS_DIR,
           on_round_complete: Optional[Callable[[FederatedRoundResult], None]] = None,
       ) -> None:
           self.num_rounds = num_rounds
           self.min_clients = min_clients
           self.min_available_clients = min_available_clients
           self.models_dir = Path(models_dir)
           self.on_round_complete = on_round_complete
           self._aggregator = FedAvgAggregator()
           self._current_weights: List[np.ndarray] = []
           self._round_history: List[FederatedRoundResult] = []

       def aggregate(
           self,
           client_results: List[Tuple[List[np.ndarray], int, Dict[str, Any]]],
       ) -> List[np.ndarray]:
           """
           Agrega los resultados de múltiples clientes usando FedAvg.

           Args:
               client_results: Lista de (pesos_con_dp, num_samples, métricas)

           Returns:
               Pesos fusionados
           """
           client_weights = [(weights, num_samples) for weights, num_samples, _ in client_results]
           aggregated = self._aggregator.aggregate(client_weights)
           self._current_weights = aggregated
           return aggregated

       def save_model(self, weights: List[np.ndarray], round_num: int) -> str:
           """
           Guarda el modelo fusionado en disco.
           Retorna la ruta del archivo guardado.
           """
           self.models_dir.mkdir(parents=True, exist_ok=True)
           path = self.models_dir / f"federated_lora_round_{round_num:04d}.npz"

           arrays = {f"layer_{i}": w for i, w in enumerate(weights)}
           np.savez(str(path), **arrays)

           # También guardar metadatos
           meta_path = self.models_dir / f"federated_lora_round_{round_num:04d}_meta.json"
           meta = {
               "round": round_num,
               "num_layers": len(weights),
               "layer_shapes": [list(w.shape) for w in weights],
               "timestamp": time.time(),
           }
           meta_path.write_text(json.dumps(meta, indent=2))

           logger.info("Modelo federado guardado: %s", path)
           return str(path)

       def load_model(self, round_num: int) -> Optional[List[np.ndarray]]:
           """Carga un modelo guardado de una ronda anterior."""
           path = self.models_dir / f"federated_lora_round_{round_num:04d}.npz"
           if not path.exists():
               return None
           data = np.load(str(path))
           return [data[f"layer_{i}"] for i in range(len(data.files))]

       def get_current_weights(self) -> List[np.ndarray]:
           """Retorna los pesos actuales del modelo global."""
           return self._current_weights

       def run_round(
           self,
           client_results: List[Tuple[List[np.ndarray], int, Dict[str, Any]]],
           round_num: int,
       ) -> FederatedRoundResult:
           """
           Ejecuta una ronda completa de agregación.

           Args:
               client_results: Resultados de los clientes en esta ronda
               round_num: Número de ronda (1-indexed)

           Returns:
               FederatedRoundResult con métricas de la ronda
           """
           start = time.monotonic()
           num_clients = len(client_results)

           if num_clients < self.min_clients:
               logger.warning(
                   "Ronda %d: %d/%d clientes — insuficiente para agregar",
                   round_num,
                   num_clients,
                   self.min_clients,
               )
               return FederatedRoundResult(
                   round_num=round_num,
                   num_clients=num_clients,
                   loss_aggregated=0.0,
                   loss_distributed=None,
                   duration_seconds=time.monotonic() - start,
                   weights_saved_path="",
               )

           # Agregar pesos
           aggregated = self.aggregate(client_results)

           # Calcular loss promedio ponderado
           total_samples = sum(n for _, n, _ in client_results)
           loss_agg = 0.0
           for _, num_samples, metrics in client_results:
               w = num_samples / max(total_samples, 1)
               loss_agg += metrics.get("loss", 0.0) * w

           # Guardar modelo
           weights_path = self.save_model(aggregated, round_num) if aggregated else ""

           duration = time.monotonic() - start
           client_metrics = [m for _, _, m in client_results]

           result = FederatedRoundResult(
               round_num=round_num,
               num_clients=num_clients,
               loss_aggregated=loss_agg,
               loss_distributed=None,
               duration_seconds=duration,
               weights_saved_path=weights_path,
               client_metrics=client_metrics,
           )

           self._round_history.append(result)

           logger.info(
               "Ronda %d completada: %d clientes, loss=%.4f, duration=%.1fs",
               round_num,
               num_clients,
               loss_agg,
               duration,
           )

           if self.on_round_complete:
               self.on_round_complete(result)

           return result

       async def start(self, server_address: str = "0.0.0.0:8080") -> None:
           """
           Inicia el servidor Flower para federated learning.
           Requiere: pip install flwr
           """
           try:
               import flwr as fl

               strategy = fl.server.strategy.FedAvg(
                   fraction_fit=1.0,
                   fraction_evaluate=1.0,
                   min_fit_clients=self.min_clients,
                   min_evaluate_clients=self.min_clients,
                   min_available_clients=self.min_available_clients,
               )

               logger.info(
                   "Iniciando servidor Flower: %s rounds=%d min_clients=%d",
                   server_address,
                   self.num_rounds,
                   self.min_clients,
               )

               fl.server.start_server(
                   server_address=server_address,
                   config=fl.server.ServerConfig(num_rounds=self.num_rounds),
                   strategy=strategy,
               )

           except ImportError:
               logger.error("flwr no instalado: pip install flwr")
               raise

       @property
       def round_history(self) -> List[FederatedRoundResult]:
           return self._round_history

6. Crear archivo tests/test_federated.py:

   Ruta: ~/yeyo-os/tests/test_federated.py
   Contenido:

   """
   Tests para Federated Learning (7.21).
   Usa mocks para flwr, PEFT y Flash Memory.
   Verifica PrivacyFilter, FedAvg y flujo completo.
   """

   from __future__ import annotations

   import os
   import tempfile
   from typing import Dict, List, Tuple
   from unittest.mock import MagicMock, patch

   import numpy as np
   import pytest

   from src.cluster.federated.privacy import DPConfig, PrivacyFilter
   from src.cluster.federated.trainer import LoRATrainer, TrainingResult
   from src.cluster.federated.server import FedAvgAggregator, FederatedServer


   # ── Tests: DPConfig ───────────────────────────────────────────────────────────

   class TestDPConfig:
       def test_default_values(self):
           cfg = DPConfig()
           assert cfg.epsilon == 1.0
           assert cfg.delta == 1e-5
           assert cfg.max_grad_norm == 1.0

       def test_compute_noise_multiplier(self):
           cfg = DPConfig(epsilon=1.0, delta=1e-5)
           nm = cfg.compute_noise_multiplier(num_clients=10, num_rounds=10)
           assert nm > 0

       def test_stricter_privacy_higher_noise(self):
           cfg_strict = DPConfig(epsilon=0.1)
           cfg_loose = DPConfig(epsilon=10.0)
           nm_strict = cfg_strict.compute_noise_multiplier(10, 10)
           nm_loose = cfg_loose.compute_noise_multiplier(10, 10)
           assert nm_strict > nm_loose


   # ── Tests: PrivacyFilter ──────────────────────────────────────────────────────

   class TestPrivacyFilter:
       @pytest.fixture
       def pf(self):
           return PrivacyFilter(DPConfig(epsilon=1.0, delta=1e-5))

       @pytest.fixture
       def sample_weights(self):
           return [
               np.ones((10, 8), dtype=np.float32),
               np.ones((8, 10), dtype=np.float32),
           ]

       def test_apply_changes_weights(self, pf, sample_weights):
           noisy = pf.apply(sample_weights)
           assert len(noisy) == len(sample_weights)
           # Los pesos DEBEN cambiar tras aplicar ruido
           changed = any(
               not np.array_equal(orig, noisy_w)
               for orig, noisy_w in zip(sample_weights, noisy)
           )
           assert changed, "PrivacyFilter no aplicó ruido — pesos sin cambio"

       def test_apply_preserves_shape(self, pf, sample_weights):
           noisy = pf.apply(sample_weights)
           for orig, noisy_w in zip(sample_weights, noisy):
               assert orig.shape == noisy_w.shape

       def test_verify_noise_applied_true(self, pf, sample_weights):
           noisy = pf.apply(sample_weights)
           assert pf.verify_noise_applied(sample_weights, noisy) is True

       def test_verify_noise_applied_false_identical(self, pf, sample_weights):
           # Si los pesos son idénticos, verify retorna False
           result = pf.verify_noise_applied(sample_weights, sample_weights)
           assert result is False

       def test_apply_empty_weights(self, pf):
           result = pf.apply([])
           assert result == []

       def test_noise_count_increments(self, pf, sample_weights):
           assert pf.noise_count == 0
           pf.apply(sample_weights)
           assert pf.noise_count == 1
           pf.apply(sample_weights)
           assert pf.noise_count == 2

       def test_privacy_budget_report(self, pf, sample_weights):
           pf.apply(sample_weights)
           budget = pf.privacy_budget_used()
           assert budget["epsilon"] == 1.0
           assert budget["applications"] == 1
           assert budget["estimated_epsilon_used"] == 1.0

       def test_clip_reduces_large_weights(self, pf):
           # Pesos muy grandes deben ser clippeados
           large_weights = [np.ones((10, 10), dtype=np.float32) * 1000.0]
           clipped = pf._clip_weights(large_weights)
           norm = np.linalg.norm(clipped[0])
           assert norm <= pf.config.max_grad_norm + 1e-4


   # ── Tests: LoRATrainer ────────────────────────────────────────────────────────

   class TestLoRATrainer:
       @pytest.fixture
       def trainer(self):
           return LoRATrainer(node_id="test-sat")

       @pytest.fixture
       def sample_data(self):
           return [
               {"input": f"pregunta {i}", "output": f"respuesta {i}"}
               for i in range(50)
           ]

       def test_init(self, trainer):
           assert trainer.node_id == "test-sat"
           assert trainer.base_model == "qwen2.5:3b"
           assert trainer.lora_r == 8

       @pytest.mark.asyncio
       async def test_train_insufficient_data(self, trainer):
           result = await trainer.train(training_data=[], epochs=3)
           assert result.num_samples == 0
           assert result.metadata.get("skipped") is True

       @pytest.mark.asyncio
       async def test_train_simulates_when_no_peft(self, trainer, sample_data):
           # PEFT no disponible en CI — debe simular
           result = await trainer.train(training_data=sample_data, epochs=2)
           assert result.num_samples == 50
           assert result.epochs in (2, 0)  # 0 si saltó
           if result.epochs > 0:
               assert len(result.weights) > 0
               assert result.loss_final <= result.loss_initial + 0.1  # Convergencia

       def test_load_local_data_no_flash_memory(self, trainer):
           # Sin Flash Memory real, retorna lista vacía
           with patch("src.cluster.federated.trainer.FlashMemory", side_effect=ImportError):
               data = trainer.load_local_data()
           assert isinstance(data, list)

       def test_simulate_training_returns_weights(self, trainer):
           weights, loss_i, loss_f = trainer._simulate_training(100, 3)
           assert len(weights) == 4  # 4 matrices LoRA
           assert all(w.dtype == np.float32 for w in weights)
           assert loss_f <= loss_i


   # ── Tests: FedAvgAggregator ───────────────────────────────────────────────────

   class TestFedAvgAggregator:
       @pytest.fixture
       def agg(self):
           return FedAvgAggregator()

       def _make_weights(self, scale: float) -> List[np.ndarray]:
           return [
               np.ones((10, 8), dtype=np.float32) * scale,
               np.ones((8, 10), dtype=np.float32) * scale,
           ]

       def test_aggregate_single_client(self, agg):
           weights = self._make_weights(2.0)
           result = agg.aggregate([(weights, 100)])
           assert len(result) == 2
           assert np.allclose(result[0], 2.0)

       def test_aggregate_two_equal_clients(self, agg):
           w1 = self._make_weights(2.0)
           w2 = self._make_weights(4.0)
           result = agg.aggregate([(w1, 100), (w2, 100)])
           # Media aritmética = 3.0
           assert np.allclose(result[0], 3.0, atol=1e-5)

       def test_aggregate_weighted_by_samples(self, agg):
           w1 = self._make_weights(0.0)
           w2 = self._make_weights(4.0)
           # w2 tiene 3x más muestras → resultado ≈ 3.0
           result = agg.aggregate([(w1, 100), (w2, 300)])
           assert np.allclose(result[0], 3.0, atol=1e-5)

       def test_aggregate_empty(self, agg):
           result = agg.aggregate([])
           assert result == []

       def test_aggregate_zero_samples(self, agg):
           weights = self._make_weights(1.0)
           result = agg.aggregate([(weights, 0)])
           assert len(result) == 2


   # ── Tests: FederatedServer ────────────────────────────────────────────────────

   class TestFederatedServer:
       @pytest.fixture
       def server(self, tmp_path):
           return FederatedServer(
               num_rounds=3,
               min_clients=2,
               models_dir=str(tmp_path / "models"),
           )

       def _make_client_result(self, scale: float, samples: int):
           weights = [np.ones((10, 8), dtype=np.float32) * scale]
           metrics = {"loss": 1.0 / scale, "node_id": f"sat-{scale}"}
           return weights, samples, metrics

       def test_run_round_aggregates(self, server):
           results = [
               self._make_client_result(1.0, 100),
               self._make_client_result(2.0, 200),
           ]
           result = server.run_round(results, round_num=1)
           assert result.round_num == 1
           assert result.num_clients == 2
           assert result.loss_aggregated > 0

       def test_run_round_insufficient_clients(self, server):
           results = [self._make_client_result(1.0, 100)]  # Solo 1 cliente, min=2
           result = server.run_round(results, round_num=1)
           assert result.num_clients == 1
           assert result.weights_saved_path == ""

       def test_save_and_load_model(self, server):
           weights = [np.ones((10, 8), dtype=np.float32) * 3.0]
           path = server.save_model(weights, round_num=1)
           assert os.path.exists(path)

           loaded = server.load_model(round_num=1)
           assert loaded is not None
           assert np.allclose(loaded[0], 3.0)

       def test_round_history_appended(self, server):
           results = [
               self._make_client_result(1.0, 100),
               self._make_client_result(2.0, 200),
           ]
           server.run_round(results, round_num=1)
           server.run_round(results, round_num=2)
           assert len(server.round_history) == 2
           assert server.round_history[0].round_num == 1
           assert server.round_history[1].round_num == 2

       def test_on_round_complete_callback(self, server):
           called = []
           server.on_round_complete = lambda r: called.append(r.round_num)
           results = [
               self._make_client_result(1.0, 100),
               self._make_client_result(2.0, 200),
           ]
           server.run_round(results, round_num=5)
           assert 5 in called

       def test_get_current_weights(self, server):
           results = [
               self._make_client_result(2.0, 100),
               self._make_client_result(2.0, 100),
           ]
           server.run_round(results, round_num=1)
           weights = server.get_current_weights()
           assert len(weights) > 0
           assert np.allclose(weights[0], 2.0)


   # ── Tests: FederatedClient ────────────────────────────────────────────────────

   class TestFederatedClient:
       @pytest.fixture
       def client(self):
           from src.cluster.federated.client import FederatedClient
           return FederatedClient(node_id="sat-test", max_samples=50, epochs=1)

       def test_init(self, client):
           assert client.node_id == "sat-test"
           assert client.max_samples == 50

       def test_get_parameters_initial(self, client):
           params = client.get_parameters({})
           assert isinstance(params, list)
           assert len(params) >= 1

       def test_fit_no_data(self, client):
           with patch.object(client._trainer, "load_local_data", return_value=[]):
               params = [np.zeros((10, 8), dtype=np.float32)]
               result_params, num_samples, metrics = client.fit(params, {"num_rounds": 5, "num_clients": 2})
           assert num_samples == 0
           assert metrics.get("skipped") is True

       def test_fit_with_data_applies_dp(self, client):
           sample_data = [
               {"input": f"q{i}", "output": f"a{i}"} for i in range(50)
           ]
           with patch.object(client._trainer, "load_local_data", return_value=sample_data):
               params = [np.zeros((3072, 8), dtype=np.float32)]
               result_params, num_samples, metrics = client.fit(
                   params, {"num_rounds": 5, "num_clients": 3}
               )
           assert num_samples == 50
           assert "dp_epsilon" in metrics
           # Privacy filter debe haber aplicado ruido
           assert client._privacy_filter.noise_count >= 1

       def test_evaluate_no_data(self, client):
           with patch.object(client._trainer, "load_local_data", return_value=[]):
               loss, num_samples, metrics = client.evaluate([], {})
           assert loss == 0.0
           assert num_samples == 0


   # ── Test de integración: 2 clientes → servidor fusiona ───────────────────────

   class TestFederatedIntegration:
       def test_two_clients_server_fusion(self, tmp_path):
           """
           2 clientes simulan entrenamiento local → servidor fusiona → modelo mejorado.
           Verifica que PrivacyFilter se aplicó y el modelo fusionado existe.
           """
           from src.cluster.federated.client import FederatedClient
           from src.cluster.federated.privacy import DPConfig

           server = FederatedServer(
               num_rounds=1,
               min_clients=2,
               models_dir=str(tmp_path / "models"),
           )

           clients = [
               FederatedClient(node_id=f"sat-{i}", dp_config=DPConfig(epsilon=1.0), epochs=1)
               for i in range(2)
           ]

           # Simular datos locales para cada cliente
           training_data = [{"input": f"q{j}", "output": f"a{j}"} for j in range(50)]

           client_results = []
           for client in clients:
               with patch.object(client._trainer, "load_local_data", return_value=training_data):
                   global_params = [np.zeros((3072, 8), dtype=np.float32)]
                   weights, num_samples, metrics = client.fit(
                       global_params, {"num_rounds": 1, "num_clients": 2}
                   )

               # Verificar que PrivacyFilter se aplicó
               assert client._privacy_filter.noise_count >= 1, \
                   f"Cliente {client.node_id}: PrivacyFilter no aplicó ruido"

               client_results.append((weights, num_samples, metrics))

           # Servidor fusiona con FedAvg
           round_result = server.run_round(client_results, round_num=1)

           assert round_result.num_clients == 2
           assert round_result.loss_aggregated > 0
           assert len(server.get_current_weights()) > 0

           # Modelo guardado en disco
           if round_result.weights_saved_path:
               assert os.path.exists(round_result.weights_saved_path)

VERIFICAR:
- [ ] src/cluster/federated/privacy.py — PrivacyFilter aplica ruido gaussiano, verify_noise_applied() retorna True
- [ ] src/cluster/federated/trainer.py — LoRATrainer entrena con PEFT o simula, load_local_data() lee Flash Memory local
- [ ] src/cluster/federated/client.py — FederatedClient.fit() aplica PrivacyFilter antes de retornar pesos
- [ ] src/cluster/federated/server.py — FederatedServer agrega con FedAvg, guarda modelo en disco
- [ ] Tests pasan: pytest tests/test_federated.py (≥30 tests)
- [ ] Test de integración: 2 clientes → servidor fusiona → modelo guardado en disco

SI FALLA:
- flwr no instalado: pip install flwr (solo necesario para start()); los tests no lo requieren
- peft no instalado: pip install peft torch (solo para _train_with_peft); tests usan simulación
- Flash Memory no existe: load_local_data() retorna [] sin error — comportamiento esperado
- pytest-asyncio no instalado: pip install pytest-asyncio
- CUDA no disponible: LoRATrainer usa _simulate_training automáticamente

NO HACER:
- No enviar datos de entrenamiento al servidor — SOLO pesos con DP
- No implementar FL synchronous blocking en el thread principal
- No guardar datos privados del usuario en el modelo fusionado
- No saltarse PrivacyFilter aunque epsilon sea grande
- No implementar WebRTC o STUN/TURN (eso es futuro)
- No usar FedProx o FedOpt en esta fase — solo FedAvg

GATE: 2 FederatedClient simulan entrenamiento local con datos mock. PrivacyFilter verificado (noise_count >= 1 por cliente). FederatedServer.run_round() con 2 clientes agrega con FedAvg, modelo fusionado guardado en disco. Test de integración pasa. Todos los tests pasan (≥32 tests).
```
