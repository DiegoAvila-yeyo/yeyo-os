## ═══════════════════════════════════════
## MICRO-FASE 7.1 — LoRA Validation & Apply
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.1-1 [VSCODE] — Crear sistema de validación y aplicación de LoRA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.1 de Capa 7 (Evolución): validar el LoRA entrenado comparándolo con el modelo base, y aplicarlo a producción si pasa los benchmarks.

CONTEXTO:
- Micro-fase 7.0 completada: LoRA Training Pipeline creado
- El adapter LoRA ya está entrenado y guardado en models/lora_adapters/current_adapter
- Necesitamos validar ANTES de aplicar: comparar modelo base vs LoRA-enhanced
- Métricas: accuracy, calidad de respuesta, no incremento de alucinaciones
- Auto-rollback: si calidad baja >10%, revertir automáticamente
- Aplicar: merge adapter con modelo base en Ollama
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/training/validation.py:

   Ruta: ~/yeyo-os/src/training/validation.py
   Contenido:

   """
   YeyoOS — LoRA Validation & Apply
   Micro-fase 7.1 — Capa 7: Evolución

   Valida el adapter LoRA comparando con modelo base.
   Solo aplica si calidad mejora. Auto-rollback si degrada.
   """

   import asyncio
   import json
   import logging
   import subprocess
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.training.validation")


   class BenchmarkQuestion(BaseModel):
       """Pregunta de benchmark con respuesta esperada."""
       question: str
       expected_answer: str
       category: str = "general"
       weight: float = Field(default=1.0, ge=0.1, le=10.0)


   class ValidationMetrics(BaseModel):
       """Métricas de validación de un modelo."""
       accuracy: float = Field(ge=0.0, le=1.0)
       avg_response_quality: float = Field(ge=0.0, le=1.0)
       hallucination_rate: float = Field(ge=0.0, le=1.0)
       avg_latency_ms: float = Field(ge=0.0)
       total_questions: int = Field(ge=0)
       timestamp: str


   class ValidationResult(BaseModel):
       """Resultado de la comparación base vs LoRA."""
       base_metrics: ValidationMetrics
       lora_metrics: ValidationMetrics
       improvement_pct: float
       passed: bool
       reason: str
       auto_applied: bool = False


   class LoRAValidator:
       """Valida y aplica adapters LoRA a producción."""

       QUALITY_THRESHOLD = -10.0  # Máximo % de degradación permitido
       HALLUCINATION_THRESHOLD = 0.05  # Máximo incremento en tasa de alucinaciones

       def __init__(
           self,
           adapter_path: str = "models/lora_adapters/current_adapter",
           benchmark_path: str = "data/benchmarks/validation_questions.jsonl",
       ):
           self.adapter_path = Path(adapter_path)
           self.benchmark_path = Path(benchmark_path)
           self._benchmarks: list[BenchmarkQuestion] = []

       def load_benchmarks(self, path: Optional[str] = None) -> list[BenchmarkQuestion]:
           """Carga preguntas de benchmark desde JSONL."""
           file_path = Path(path) if path else self.benchmark_path
           if not file_path.exists():
               raise FileNotFoundError(f"Benchmark file no encontrado: {file_path}")

           benchmarks = []
           with open(file_path, 'r', encoding='utf-8') as f:
               for line in f:
                   line = line.strip()
                   if not line:
                       continue
                   data = json.loads(line)
                   benchmarks.append(BenchmarkQuestion(**data))

           self._benchmarks = benchmarks
           logger.info(f"Cargados {len(benchmarks)} benchmarks")
           return benchmarks

       async def evaluate_model(
           self,
           model_name: str,
           benchmarks: list[BenchmarkQuestion],
       ) -> ValidationMetrics:
           """Evalúa un modelo contra los benchmarks."""
           correct = 0
           quality_scores = []
           hallucinations = 0
           latencies = []

           for bq in benchmarks:
               start = datetime.now()
               try:
                   response = await self._query_ollama(model_name, bq.question)
                   latency = (datetime.now() - start).total_seconds() * 1000
                   latencies.append(latency)

                   # Evaluar respuesta
                   quality = self._evaluate_response_quality(
                       response, bq.expected_answer
                   )
                   quality_scores.append(quality * bq.weight)

                   if quality >= 0.5:
                       correct += 1

                   if self._detect_hallucination(response, bq.expected_answer):
                       hallucinations += 1

               except Exception as e:
                   logger.warning(f"Error evaluando pregunta: {e}")
                   quality_scores.append(0.0)
                   latencies.append(0.0)

           total = len(benchmarks)
           return ValidationMetrics(
               accuracy=correct / max(total, 1),
               avg_response_quality=sum(quality_scores) / max(len(quality_scores), 1),
               hallucination_rate=hallucinations / max(total, 1),
               avg_latency_ms=sum(latencies) / max(len(latencies), 1),
               total_questions=total,
               timestamp=datetime.now().isoformat(),
           )

       async def _query_ollama(self, model: str, prompt: str) -> str:
           """Consulta a Ollama con un prompt."""
           try:
               import httpx
               async with httpx.AsyncClient(timeout=60.0) as client:
                   resp = await client.post(
                       "http://localhost:11434/api/generate",
                       json={"model": model, "prompt": prompt, "stream": False},
                   )
                   resp.raise_for_status()
                   return resp.json().get("response", "")
           except Exception as e:
               logger.error(f"Error consultando Ollama ({model}): {e}")
               raise

       def _evaluate_response_quality(self, response: str, expected: str) -> float:
           """Evalúa calidad de respuesta vs esperada (0-1)."""
           if not response:
               return 0.0
           response_lower = response.lower().strip()
           expected_lower = expected.lower().strip()
           if expected_lower in response_lower:
               return 1.0
           expected_words = set(expected_lower.split())
           response_words = set(response_lower.split())
           if not expected_words:
               return 0.5
           overlap = len(expected_words & response_words) / len(expected_words)
           return round(overlap, 4)

       def _detect_hallucination(self, response: str, expected: str) -> bool:
           """Detecta si la respuesta contiene alucinaciones obvias."""
           if not response:
               return False
           expected_words = set(expected.lower().split())
           response_words = set(response.lower().split())
           if not expected_words:
               return False
           overlap = len(expected_words & response_words) / len(expected_words)
           return overlap < 0.2 and len(response) > len(expected) * 3

       async def validate(
           self,
           base_model: str = "qwen2.5:3b",
           lora_model: Optional[str] = None,
           benchmark_path: Optional[str] = None,
       ) -> ValidationResult:
           """Valida LoRA vs modelo base. Retorna resultado con decisión."""
           benchmarks = self.load_benchmarks(benchmark_path)
           if not benchmarks:
               raise ValueError("No hay benchmarks para validar")

           logger.info(f"Validando {len(benchmarks)} benchmarks...")

           # Evaluar modelo base
           logger.info(f"Evaluando modelo base: {base_model}")
           base_metrics = await self.evaluate_model(base_model, benchmarks)

           # Evaluar modelo LoRA
           lora_name = lora_model or f"{base_model}-lora"
           logger.info(f"Evaluando modelo LoRA: {lora_name}")
           lora_metrics = await self.evaluate_model(lora_name, benchmarks)

           # Comparar
           base_quality = base_metrics.avg_response_quality
           lora_quality = lora_metrics.avg_response_quality
           improvement = ((lora_quality - base_quality) / max(base_quality, 0.001)) * 100

           hallucination_increase = (
               lora_metrics.hallucination_rate - base_metrics.hallucination_rate
           )

           # Decidir
           passed = True
           reason = "LoRA aprobado"

           if improvement < self.QUALITY_THRESHOLD:
               passed = False
               reason = f"Calidad degradó {improvement:.1f}% (máximo permitido: {self.QUALITY_THRESHOLD}%)"

           if hallucination_increase > self.HALLUCINATION_THRESHOLD:
               passed = False
               reason = (f"Alucinaciones incrementaron {hallucination_increase:.2f} "
                         f"(máximo: {self.HALLUCINATION_THRESHOLD})")

           result = ValidationResult(
               base_metrics=base_metrics,
               lora_metrics=lora_metrics,
               improvement_pct=round(improvement, 2),
               passed=passed,
               reason=reason,
           )

           logger.info(f"Validación: passed={passed}, improvement={improvement:.1f}%, "
                       f"reason={reason}")

           return result

       async def apply_adapter(self, base_model: str = "qwen2.5:3b") -> bool:
           """Aplica el adapter LoRA al modelo en Ollama (crea Modelfile)."""
           if not self.adapter_path.exists():
               logger.error(f"Adapter no encontrado: {self.adapter_path}")
               return False

           modelfile_content = f"""FROM {base_model}
ADAPTER {self.adapter_path}
PARAMETER temperature 0.7
PARAMETER num_ctx 2048
"""
           modelfile_path = self.adapter_path / "Modelfile"
           modelfile_path.write_text(modelfile_content)

           try:
               result = subprocess.run(
                   ["ollama", "create", f"{base_model}-lora", "-f", str(modelfile_path)],
                   capture_output=True, text=True, timeout=300,
               )
               if result.returncode == 0:
                   logger.info(f"Adapter aplicado exitosamente como {base_model}-lora")
                   return True
               else:
                   logger.error(f"Error aplicando adapter: {result.stderr}")
                   return False
           except Exception as e:
               logger.error(f"Error ejecutando ollama create: {e}")
               return False

       async def validate_and_apply(
           self,
           base_model: str = "qwen2.5:3b",
           benchmark_path: Optional[str] = None,
       ) -> ValidationResult:
           """Flujo completo: validar y aplicar si pasa."""
           result = await self.validate(base_model, benchmark_path=benchmark_path)

           if result.passed:
               applied = await self.apply_adapter(base_model)
               result.auto_applied = applied
               if applied:
                   logger.info("LoRA validado y aplicado exitosamente")
               else:
                   logger.warning("LoRA validado pero falló al aplicar")
           else:
               logger.warning(f"LoRA NO aplicado: {result.reason}")

           return result

2. Actualizar src/training/__init__.py:

   Ruta: ~/yeyo-os/src/training/__init__.py
   Contenido:
   from .lora_pipeline import LoRAPipeline, TrainingConfig, TrainingResult
   from .validation import LoRAValidator, ValidationResult, ValidationMetrics

3. Crear archivo tests/unit/training/test_validation.py:

   Ruta: ~/yeyo-os/tests/unit/training/test_validation.py
   Contenido:

   """Tests para LoRA Validation & Apply — Micro-fase 7.1"""

   import json
   import os
   import tempfile
   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from pathlib import Path
   from src.training.validation import (
       LoRAValidator, BenchmarkQuestion, ValidationMetrics,
       ValidationResult,
   )


   class TestBenchmarkQuestion:
       """Tests para BenchmarkQuestion."""

       def test_valid_question(self):
           q = BenchmarkQuestion(
               question="¿Capital de Francia?",
               expected_answer="París",
           )
           assert q.question == "¿Capital de Francia?"
           assert q.weight == 1.0

       def test_custom_weight(self):
           q = BenchmarkQuestion(
               question="test", expected_answer="test",
               category="math", weight=2.5,
           )
           assert q.weight == 2.5


   class TestLoRAValidator:
       """Tests para LoRAValidator."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.validator = LoRAValidator(
               adapter_path=os.path.join(self.tmp_dir, "adapter"),
               benchmark_path=os.path.join(self.tmp_dir, "benchmarks.jsonl"),
           )

       def test_load_benchmarks(self):
           bm_path = os.path.join(self.tmp_dir, "benchmarks.jsonl")
           with open(bm_path, 'w') as f:
               json.dump({"question": "¿2+2?", "expected_answer": "4"}, f)
               f.write('\n')
               json.dump({"question": "¿Color del cielo?", "expected_answer": "azul"}, f)
               f.write('\n')
           result = self.validator.load_benchmarks(bm_path)
           assert len(result) == 2

       def test_load_benchmarks_file_not_found(self):
           with pytest.raises(FileNotFoundError):
               self.validator.load_benchmarks("/nonexistent.jsonl")

       def test_evaluate_response_quality_exact(self):
           score = self.validator._evaluate_response_quality("París", "París")
           assert score == 1.0

       def test_evaluate_response_quality_contains(self):
           score = self.validator._evaluate_response_quality(
               "La capital de Francia es París", "París"
           )
           assert score == 1.0

       def test_evaluate_response_quality_empty(self):
           score = self.validator._evaluate_response_quality("", "París")
           assert score == 0.0

       def test_detect_hallucination_no(self):
           is_hallucination = self.validator._detect_hallucination(
               "París es la capital", "París capital"
           )
           assert is_hallucination is False

       def test_detect_hallucination_yes(self):
           is_hallucination = self.validator._detect_hallucination(
               "Tokio es una ciudad enorme con muchos edificios y templos y tecnología avanzada "
               "y trenes bala y sushi y anime y manga",
               "París",
           )
           assert is_hallucination is True

       def test_quality_threshold(self):
           assert LoRAValidator.QUALITY_THRESHOLD == -10.0

       def test_hallucination_threshold(self):
           assert LoRAValidator.HALLUCINATION_THRESHOLD == 0.05


   class TestValidationMetrics:
       """Tests para ValidationMetrics."""

       def test_valid_metrics(self):
           m = ValidationMetrics(
               accuracy=0.85,
               avg_response_quality=0.9,
               hallucination_rate=0.02,
               avg_latency_ms=150.0,
               total_questions=20,
               timestamp="2025-01-01T00:00:00",
           )
           assert m.accuracy == 0.85
           assert m.hallucination_rate == 0.02


   class TestValidationResult:
       """Tests para ValidationResult."""

       def test_passed_result(self):
           metrics = ValidationMetrics(
               accuracy=0.8, avg_response_quality=0.85,
               hallucination_rate=0.01, avg_latency_ms=100.0,
               total_questions=10, timestamp="2025-01-01",
           )
           result = ValidationResult(
               base_metrics=metrics, lora_metrics=metrics,
               improvement_pct=5.0, passed=True,
               reason="LoRA aprobado",
           )
           assert result.passed is True
           assert result.auto_applied is False

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/training/test_validation.py -v

VERIFICAR:
- [ ] Archivo src/training/validation.py existe con LoRAValidator
- [ ] Benchmarks se cargan desde JSONL
- [ ] Calidad de respuesta se evalúa correctamente
- [ ] Alucinaciones se detectan
- [ ] Threshold de calidad: -10% máximo degradación
- [ ] Threshold de alucinaciones: +5% máximo incremento
- [ ] apply_adapter crea Modelfile y ejecuta ollama create
- [ ] validate_and_apply auto-aplica solo si pasa
- [ ] TODOS los tests pasan

SI FALLA:
- httpx no instalado: pip install httpx
- pytest-asyncio no instalado: pip install pytest-asyncio

NO HACER:
- No ejecutar queries reales a Ollama en tests unitarios
- No aplicar adapter sin validar primero

GATE: LoRAValidator compara base vs LoRA, aplica solo si mejora, auto-rollback si degrada, todos los tests pasan.
```
