## ═══════════════════════════════════════
## MICRO-FASE 7.0 — LoRA Training Pipeline
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.0-1 [VSCODE] — Crear pipeline de fine-tuning LoRA/QLoRA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.0 de Capa 7 (Evolución): crear el pipeline de fine-tuning LoRA usando QLoRA 4-bit para modelos Ollama, entrenando con datos de Flash Memory del usuario.

CONTEXTO:
- Capas 0-6 completadas: infraestructura, esqueleto, cerebro, cuerpo/UI, sistema nervioso, órganos, sistema inmune
- Capa 7 = EVOLUCIÓN de YeyoOS. El sistema aprende del usuario y mejora continuamente
- Hardware: GTX 1060 3GB VRAM, 16GB RAM — obligatorio QLoRA 4-bit quantization
- Training SOLO durante idle time, prioridad P3 (nunca interrumpe tareas del usuario)
- Schedule: nightly (cuando GPU está idle)
- Datos de entrenamiento: extraídos de Flash Memory (correcciones, preferencias, skills)
- Output: LoRA adapter file (.gguf adapter) compatible con Ollama
- Rollback: siempre mantener adapter anterior, restaurar si calidad degrada

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/training
   mkdir -p tests/unit/training

2. Crear archivo src/training/__init__.py:

   Ruta: ~/yeyo-os/src/training/__init__.py
   Contenido:
   from .lora_pipeline import LoRAPipeline, TrainingConfig, TrainingResult

3. Crear archivo src/training/lora_pipeline.py:

   Ruta: ~/yeyo-os/src/training/lora_pipeline.py
   Contenido:

   """
   YeyoOS — LoRA Training Pipeline (QLoRA 4-bit)
   Micro-fase 7.0 — Capa 7: Evolución

   Fine-tune modelos Ollama con datos del usuario usando QLoRA.
   CRÍTICO: Solo ejecutar en prioridad P3 (idle time).
   Hardware: GTX 1060 3GB VRAM → obligatorio 4-bit quantization.
   """

   import asyncio
   import json
   import logging
   import os
   import shutil
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.training.lora")


   class TrainingConfig(BaseModel):
       """Configuración del pipeline de entrenamiento LoRA."""
       base_model: str = Field(default="qwen2.5:3b", description="Modelo base de Ollama")
       lora_rank: int = Field(default=8, ge=4, le=64, description="Rango LoRA (8 óptimo para 3GB)")
       lora_alpha: int = Field(default=16, ge=8, le=128, description="Alpha LoRA")
       lora_dropout: float = Field(default=0.05, ge=0.0, le=0.5)
       learning_rate: float = Field(default=2e-4, gt=0.0, le=1e-2)
       num_epochs: int = Field(default=3, ge=1, le=10)
       batch_size: int = Field(default=1, ge=1, le=4, description="Batch size 1 para 3GB VRAM")
       max_seq_length: int = Field(default=512, ge=128, le=2048)
       quantization_bits: int = Field(default=4, description="QLoRA 4-bit obligatorio")
       gradient_accumulation_steps: int = Field(default=8, ge=1, le=32)
       warmup_ratio: float = Field(default=0.1, ge=0.0, le=0.5)
       output_dir: str = Field(default="models/lora_adapters")
       min_training_samples: int = Field(default=100, ge=50)
       validation_split: float = Field(default=0.1, ge=0.05, le=0.3)
       max_gpu_memory_mb: int = Field(default=2800, description="Límite VRAM para training")


   class TrainingResult(BaseModel):
       """Resultado de una sesión de entrenamiento."""
       adapter_path: str
       base_model: str
       num_samples: int
       num_epochs: int
       final_loss: float
       validation_loss: float
       training_time_seconds: float
       timestamp: str
       quality_score: float = Field(ge=0.0, le=1.0)
       rollback_path: Optional[str] = None


   class LoRAPipeline:
       """Pipeline de fine-tuning LoRA/QLoRA para YeyoOS."""

       def __init__(self, config: Optional[TrainingConfig] = None):
           self.config = config or TrainingConfig()
           self.output_dir = Path(self.config.output_dir)
           self.output_dir.mkdir(parents=True, exist_ok=True)
           self._backup_dir = self.output_dir / "backups"
           self._backup_dir.mkdir(parents=True, exist_ok=True)
           self._is_training = False
           self._current_adapter_path: Optional[Path] = None
           logger.info(f"LoRA Pipeline inicializado: modelo={self.config.base_model}, "
                       f"rank={self.config.lora_rank}, bits={self.config.quantization_bits}")

       async def check_gpu_available(self) -> bool:
           """Verifica que GPU está disponible y tiene suficiente VRAM libre."""
           try:
               import subprocess
               result = subprocess.run(
                   ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                   capture_output=True, text=True, timeout=10
               )
               if result.returncode != 0:
                   logger.warning("nvidia-smi falló, GPU no disponible")
                   return False
               free_mb = int(result.stdout.strip().split('\n')[0])
               available = free_mb >= self.config.max_gpu_memory_mb
               logger.info(f"GPU VRAM libre: {free_mb}MB, requerido: {self.config.max_gpu_memory_mb}MB, "
                           f"disponible: {available}")
               return available
           except Exception as e:
               logger.error(f"Error verificando GPU: {e}")
               return False

       async def check_scheduler_priority(self) -> bool:
           """Verifica que el scheduler permite training (solo P3 idle)."""
           try:
               from src.core.gpu_scheduler import GPUScheduler
               scheduler = GPUScheduler.get_instance()
               current_priority = scheduler.get_current_priority()
               is_idle = current_priority is None or current_priority >= 3
               logger.info(f"GPU Scheduler prioridad actual: {current_priority}, idle={is_idle}")
               return is_idle
           except ImportError:
               logger.warning("GPU Scheduler no disponible, asumiendo idle")
               return True

       def _backup_current_adapter(self) -> Optional[str]:
           """Respalda el adapter actual antes de entrenar uno nuevo."""
           current = self.output_dir / "current_adapter"
           if current.exists():
               timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
               backup_path = self._backup_dir / f"adapter_backup_{timestamp}"
               shutil.copytree(str(current), str(backup_path))
               logger.info(f"Adapter actual respaldado en: {backup_path}")
               return str(backup_path)
           return None

       async def prepare_training_data(self, data_path: str) -> dict:
           """Prepara y valida datos de entrenamiento desde JSONL."""
           samples = []
           data_file = Path(data_path)
           if not data_file.exists():
               raise FileNotFoundError(f"Archivo de datos no encontrado: {data_path}")

           with open(data_file, 'r', encoding='utf-8') as f:
               for line_num, line in enumerate(f, 1):
                   line = line.strip()
                   if not line:
                       continue
                   try:
                       sample = json.loads(line)
                       if not all(k in sample for k in ('instruction', 'output')):
                           logger.warning(f"Línea {line_num}: falta instruction/output, saltando")
                           continue
                       samples.append(sample)
                   except json.JSONDecodeError:
                       logger.warning(f"Línea {line_num}: JSON inválido, saltando")

           total = len(samples)
           if total < self.config.min_training_samples:
               raise ValueError(
                   f"Insuficientes muestras: {total} < {self.config.min_training_samples} mínimo"
               )

           split_idx = int(total * (1 - self.config.validation_split))
           train_samples = samples[:split_idx]
           val_samples = samples[split_idx:]

           logger.info(f"Datos preparados: {len(train_samples)} train, {len(val_samples)} validation")
           return {
               "train": train_samples,
               "validation": val_samples,
               "total": total,
           }

       async def train(self, data_path: str) -> TrainingResult:
           """
           Ejecuta el pipeline completo de entrenamiento LoRA.
           SOLO ejecutar cuando GPU está idle (P3).
           """
           if self._is_training:
               raise RuntimeError("Ya hay un entrenamiento en curso")

           self._is_training = True
           start_time = datetime.now()

           try:
               # 1. Verificar GPU disponible
               if not await self.check_gpu_available():
                   raise RuntimeError("GPU no disponible o VRAM insuficiente")

               # 2. Verificar prioridad P3 (idle)
               if not await self.check_scheduler_priority():
                   raise RuntimeError("GPU no está idle (se requiere P3)")

               # 3. Preparar datos
               data = await self.prepare_training_data(data_path)

               # 4. Respaldar adapter actual
               rollback_path = self._backup_current_adapter()

               # 5. Configurar QLoRA
               logger.info("Configurando QLoRA 4-bit...")
               from transformers import (
                   AutoModelForCausalLM,
                   AutoTokenizer,
                   TrainingArguments,
                   Trainer,
                   BitsAndBytesConfig,
               )
               from peft import LoraConfig, get_peft_model, TaskType
               from datasets import Dataset
               import torch

               bnb_config = BitsAndBytesConfig(
                   load_in_4bit=True,
                   bnb_4bit_quant_type="nf4",
                   bnb_4bit_compute_dtype=torch.float16,
                   bnb_4bit_use_double_quant=True,
               )

               # 6. Cargar modelo base con quantización 4-bit
               logger.info(f"Cargando modelo base: {self.config.base_model}")
               model = AutoModelForCausalLM.from_pretrained(
                   self.config.base_model,
                   quantization_config=bnb_config,
                   device_map="auto",
                   torch_dtype=torch.float16,
               )

               tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
               if tokenizer.pad_token is None:
                   tokenizer.pad_token = tokenizer.eos_token

               # 7. Configurar LoRA
               lora_config = LoraConfig(
                   task_type=TaskType.CAUSAL_LM,
                   r=self.config.lora_rank,
                   lora_alpha=self.config.lora_alpha,
                   lora_dropout=self.config.lora_dropout,
                   target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
               )

               model = get_peft_model(model, lora_config)
               trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
               total_params = sum(p.numel() for p in model.parameters())
               logger.info(f"Parámetros entrenables: {trainable_params:,} / {total_params:,} "
                           f"({100 * trainable_params / total_params:.2f}%)")

               # 8. Preparar datasets
               def format_sample(sample):
                   instruction = sample.get("instruction", "")
                   input_text = sample.get("input", "")
                   output = sample.get("output", "")
                   if input_text:
                       text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
                   else:
                       text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
                   return tokenizer(
                       text,
                       truncation=True,
                       max_length=self.config.max_seq_length,
                       padding="max_length",
                   )

               train_dataset = Dataset.from_list(data["train"]).map(format_sample)
               val_dataset = Dataset.from_list(data["validation"]).map(format_sample)

               # 9. Configurar entrenamiento
               adapter_output = str(self.output_dir / "current_adapter")
               training_args = TrainingArguments(
                   output_dir=adapter_output,
                   num_train_epochs=self.config.num_epochs,
                   per_device_train_batch_size=self.config.batch_size,
                   gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                   learning_rate=self.config.learning_rate,
                   warmup_ratio=self.config.warmup_ratio,
                   logging_steps=10,
                   save_strategy="epoch",
                   evaluation_strategy="epoch",
                   fp16=True,
                   optim="paged_adamw_8bit",
                   report_to="none",
                   max_grad_norm=0.3,
               )

               # 10. Entrenar
               logger.info("Iniciando entrenamiento LoRA...")
               trainer = Trainer(
                   model=model,
                   args=training_args,
                   train_dataset=train_dataset,
                   eval_dataset=val_dataset,
               )

               train_result = trainer.train()
               final_loss = train_result.training_loss

               # 11. Evaluar
               eval_result = trainer.evaluate()
               validation_loss = eval_result["eval_loss"]

               # 12. Guardar adapter
               model.save_pretrained(adapter_output)
               tokenizer.save_pretrained(adapter_output)

               elapsed = (datetime.now() - start_time).total_seconds()

               # 13. Calcular quality score
               quality_score = self._calculate_quality_score(final_loss, validation_loss)

               result = TrainingResult(
                   adapter_path=adapter_output,
                   base_model=self.config.base_model,
                   num_samples=data["total"],
                   num_epochs=self.config.num_epochs,
                   final_loss=final_loss,
                   validation_loss=validation_loss,
                   training_time_seconds=elapsed,
                   timestamp=datetime.now().isoformat(),
                   quality_score=quality_score,
                   rollback_path=rollback_path,
               )

               # 14. Guardar metadata
               metadata_path = Path(adapter_output) / "training_metadata.json"
               with open(metadata_path, 'w') as f:
                   json.dump(result.model_dump(), f, indent=2)

               logger.info(f"Entrenamiento completado: loss={final_loss:.4f}, "
                           f"val_loss={validation_loss:.4f}, quality={quality_score:.2f}, "
                           f"tiempo={elapsed:.0f}s")

               return result

           finally:
               self._is_training = False

       def _calculate_quality_score(self, train_loss: float, val_loss: float) -> float:
           """Calcula score de calidad 0-1 basado en loss y overfitting."""
           loss_score = max(0.0, 1.0 - (val_loss / 5.0))
           overfit_ratio = val_loss / max(train_loss, 0.001)
           overfit_penalty = max(0.0, (overfit_ratio - 1.5) * 0.3)
           score = max(0.0, min(1.0, loss_score - overfit_penalty))
           return round(score, 4)

       async def rollback(self, rollback_path: str) -> bool:
           """Restaura un adapter anterior desde backup."""
           backup = Path(rollback_path)
           if not backup.exists():
               logger.error(f"Backup no encontrado: {rollback_path}")
               return False

           current = self.output_dir / "current_adapter"
           if current.exists():
               shutil.rmtree(str(current))

           shutil.copytree(str(backup), str(current))
           logger.info(f"Rollback completado desde: {rollback_path}")
           return True

       def get_current_adapter_path(self) -> Optional[str]:
           """Retorna path del adapter actual si existe."""
           current = self.output_dir / "current_adapter"
           if current.exists():
               return str(current)
           return None

       @property
       def is_training(self) -> bool:
           return self._is_training

4. Crear archivo tests/unit/training/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/training/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/training/test_lora_pipeline.py:

   Ruta: ~/yeyo-os/tests/unit/training/test_lora_pipeline.py
   Contenido:

   """Tests para LoRA Training Pipeline — Micro-fase 7.0"""

   import json
   import os
   import tempfile
   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from pathlib import Path
   from src.training.lora_pipeline import LoRAPipeline, TrainingConfig, TrainingResult


   class TestTrainingConfig:
       """Tests para TrainingConfig."""

       def test_default_config(self):
           config = TrainingConfig()
           assert config.base_model == "qwen2.5:3b"
           assert config.lora_rank == 8
           assert config.quantization_bits == 4
           assert config.batch_size == 1
           assert config.min_training_samples == 100

       def test_4bit_quantization_default(self):
           config = TrainingConfig()
           assert config.quantization_bits == 4

       def test_vram_limit_default(self):
           config = TrainingConfig()
           assert config.max_gpu_memory_mb == 2800

       def test_custom_config(self):
           config = TrainingConfig(lora_rank=16, num_epochs=5)
           assert config.lora_rank == 16
           assert config.num_epochs == 5

       def test_invalid_rank_rejected(self):
           from pydantic import ValidationError
           with pytest.raises(ValidationError):
               TrainingConfig(lora_rank=2)

       def test_invalid_epochs_rejected(self):
           from pydantic import ValidationError
           with pytest.raises(ValidationError):
               TrainingConfig(num_epochs=0)


   class TestLoRAPipeline:
       """Tests para LoRAPipeline."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.config = TrainingConfig(output_dir=self.tmp_dir)
           self.pipeline = LoRAPipeline(self.config)

       def test_pipeline_creates_output_dir(self):
           assert Path(self.tmp_dir).exists()

       def test_pipeline_creates_backup_dir(self):
           assert (Path(self.tmp_dir) / "backups").exists()

       def test_is_training_initially_false(self):
           assert self.pipeline.is_training is False

       def test_no_current_adapter_initially(self):
           assert self.pipeline.get_current_adapter_path() is None

       @pytest.mark.asyncio
       async def test_prepare_data_rejects_insufficient_samples(self):
           data_file = os.path.join(self.tmp_dir, "small_data.jsonl")
           with open(data_file, 'w') as f:
               for i in range(10):
                   json.dump({"instruction": f"test {i}", "output": f"resp {i}"}, f)
                   f.write('\n')
           with pytest.raises(ValueError, match="Insuficientes muestras"):
               await self.pipeline.prepare_training_data(data_file)

       @pytest.mark.asyncio
       async def test_prepare_data_accepts_sufficient_samples(self):
           data_file = os.path.join(self.tmp_dir, "good_data.jsonl")
           with open(data_file, 'w') as f:
               for i in range(150):
                   json.dump({"instruction": f"test {i}", "output": f"resp {i}"}, f)
                   f.write('\n')
           result = await self.pipeline.prepare_training_data(data_file)
           assert result["total"] == 150
           assert len(result["train"]) > 0
           assert len(result["validation"]) > 0

       @pytest.mark.asyncio
       async def test_prepare_data_file_not_found(self):
           with pytest.raises(FileNotFoundError):
               await self.pipeline.prepare_training_data("/nonexistent/path.jsonl")

       @pytest.mark.asyncio
       async def test_prepare_data_skips_invalid_json(self):
           data_file = os.path.join(self.tmp_dir, "mixed_data.jsonl")
           with open(data_file, 'w') as f:
               for i in range(110):
                   json.dump({"instruction": f"test {i}", "output": f"resp {i}"}, f)
                   f.write('\n')
               f.write("INVALID JSON LINE\n")
           result = await self.pipeline.prepare_training_data(data_file)
           assert result["total"] == 110

       def test_backup_current_adapter_no_adapter(self):
           result = self.pipeline._backup_current_adapter()
           assert result is None

       def test_backup_current_adapter_with_adapter(self):
           adapter_dir = Path(self.tmp_dir) / "current_adapter"
           adapter_dir.mkdir()
           (adapter_dir / "adapter_config.json").write_text("{}")
           result = self.pipeline._backup_current_adapter()
           assert result is not None
           assert Path(result).exists()

       @pytest.mark.asyncio
       async def test_rollback_restores_backup(self):
           backup_dir = Path(self.tmp_dir) / "backups" / "test_backup"
           backup_dir.mkdir(parents=True)
           (backup_dir / "adapter_config.json").write_text('{"test": true}')
           success = await self.pipeline.rollback(str(backup_dir))
           assert success is True
           current = Path(self.tmp_dir) / "current_adapter"
           assert current.exists()
           assert (current / "adapter_config.json").read_text() == '{"test": true}'

       @pytest.mark.asyncio
       async def test_rollback_fails_on_missing_backup(self):
           success = await self.pipeline.rollback("/nonexistent/backup")
           assert success is False

       def test_quality_score_good_loss(self):
           score = self.pipeline._calculate_quality_score(0.5, 0.6)
           assert 0.0 <= score <= 1.0
           assert score > 0.5

       def test_quality_score_overfit_penalized(self):
           normal_score = self.pipeline._calculate_quality_score(0.5, 0.6)
           overfit_score = self.pipeline._calculate_quality_score(0.1, 3.0)
           assert overfit_score < normal_score

       @pytest.mark.asyncio
       async def test_check_scheduler_priority_fallback(self):
           is_idle = await self.pipeline.check_scheduler_priority()
           assert is_idle is True


   class TestTrainingResult:
       """Tests para TrainingResult."""

       def test_valid_result(self):
           result = TrainingResult(
               adapter_path="/tmp/adapter",
               base_model="qwen2.5:3b",
               num_samples=150,
               num_epochs=3,
               final_loss=0.5,
               validation_loss=0.6,
               training_time_seconds=3600.0,
               timestamp="2025-01-01T00:00:00",
               quality_score=0.88,
           )
           assert result.adapter_path == "/tmp/adapter"
           assert result.quality_score == 0.88

       def test_quality_score_bounds(self):
           from pydantic import ValidationError
           with pytest.raises(ValidationError):
               TrainingResult(
                   adapter_path="/tmp/a", base_model="test",
                   num_samples=100, num_epochs=1,
                   final_loss=0.5, validation_loss=0.6,
                   training_time_seconds=10.0,
                   timestamp="2025-01-01", quality_score=1.5,
               )

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/training/test_lora_pipeline.py -v

VERIFICAR:
- [ ] Archivo src/training/lora_pipeline.py existe con LoRAPipeline, TrainingConfig, TrainingResult
- [ ] QLoRA usa 4-bit quantization (BitsAndBytesConfig con load_in_4bit=True)
- [ ] Pipeline verifica prioridad P3 antes de entrenar
- [ ] Pipeline respalda adapter anterior antes de entrenar
- [ ] Rollback restaura adapter desde backup
- [ ] Mínimo 100 muestras para entrenar
- [ ] Validation split funciona
- [ ] Quality score calcula correctamente
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar que existen todos los __init__.py
- transformers/peft no instalado: pip install transformers peft bitsandbytes datasets
- pytest-asyncio no instalado: pip install pytest-asyncio

NO HACER:
- No ejecutar training real en tests (mock de GPU)
- No usar más de 3GB VRAM
- No entrenar sin verificar prioridad P3

GATE: LoRAPipeline configurado con QLoRA 4-bit, valida datos, respeta P3, rollback funciona, todos los tests pasan.
```
