## ═══════════════════════════════════════
## MICRO-FASE 7.2 — Training Data Extractor
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.2-1 [VSCODE] — Crear extractor de datos de entrenamiento desde Flash Memory

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.2 de Capa 7 (Evolución): extraer y preparar datos de entrenamiento desde Flash Memory para alimentar el pipeline LoRA.

CONTEXTO:
- Micro-fases 7.0-7.1 completadas: LoRA Pipeline y Validation creados
- Flash Memory contiene: correcciones del usuario (mayor valor), preferencias, skills aprendidos
- Formato de salida: JSONL (instruction/input/output) para entrenamiento
- Privacidad: NUNCA incluir datos personales crudos
- Deduplicación: eliminar near-duplicates
- Mínimo: 100 muestras antes de permitir entrenamiento
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/training/data_extractor.py:

   Ruta: ~/yeyo-os/src/training/data_extractor.py
   Contenido:

   """
   YeyoOS — Training Data Extractor
   Micro-fase 7.2 — Capa 7: Evolución

   Extrae datos de Flash Memory y los prepara como JSONL
   para entrenamiento LoRA. Prioriza correcciones del usuario.
   CRÍTICO: Nunca incluir datos personales crudos.
   """

   import hashlib
   import json
   import logging
   import re
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.training.extractor")


   # Patrones de datos personales a filtrar
   PERSONAL_DATA_PATTERNS = [
       r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # emails
       r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # teléfonos
       r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # tarjetas
       r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IPs
       r'\b[A-Z]{2}\d{6,10}\b',  # documentos de identidad
   ]


   class TrainingSample(BaseModel):
       """Muestra de entrenamiento en formato instruction/input/output."""
       instruction: str
       input: str = ""
       output: str
       source: str = Field(description="corrections|preferences|skills")
       quality_weight: float = Field(default=1.0, ge=0.1, le=5.0)
       hash: str = ""


   class ExtractionStats(BaseModel):
       """Estadísticas de extracción."""
       total_extracted: int = 0
       corrections: int = 0
       preferences: int = 0
       skills: int = 0
       duplicates_removed: int = 0
       privacy_filtered: int = 0
       final_count: int = 0
       timestamp: str = ""


   class TrainingDataExtractor:
       """Extrae datos de Flash Memory para entrenamiento LoRA."""

       SIMILARITY_THRESHOLD = 0.85
       MIN_SAMPLES = 100

       def __init__(self, output_dir: str = "data/training"):
           self.output_dir = Path(output_dir)
           self.output_dir.mkdir(parents=True, exist_ok=True)
           self._personal_patterns = [
               re.compile(p, re.IGNORECASE) for p in PERSONAL_DATA_PATTERNS
           ]

       def _compute_hash(self, text: str) -> str:
           """Computa hash de contenido para deduplicación."""
           normalized = text.lower().strip()
           return hashlib.sha256(normalized.encode()).hexdigest()[:16]

       def _contains_personal_data(self, text: str) -> bool:
           """Verifica si el texto contiene datos personales."""
           for pattern in self._personal_patterns:
               if pattern.search(text):
                   return True
           return False

       def _sanitize_text(self, text: str) -> str:
           """Elimina datos personales del texto."""
           sanitized = text
           for pattern in self._personal_patterns:
               sanitized = pattern.sub("[REDACTED]", sanitized)
           return sanitized

       async def extract_corrections(self, db_connection) -> list[TrainingSample]:
           """
           Extrae correcciones del usuario desde Flash Memory.
           Las correcciones son el dato de mayor valor para training.
           """
           samples = []
           query = """
               SELECT original_response, corrected_response, context, created_at
               FROM flash_memory.corrections
               WHERE used_for_training = false
               ORDER BY created_at DESC
               LIMIT 5000
           """
           try:
               rows = await db_connection.fetch(query)
               for row in rows:
                   original = row["original_response"]
                   corrected = row["corrected_response"]
                   context = row.get("context", "")

                   # Filtrar datos personales
                   if self._contains_personal_data(corrected):
                       corrected = self._sanitize_text(corrected)
                   if self._contains_personal_data(original):
                       original = self._sanitize_text(original)

                   sample = TrainingSample(
                       instruction=f"Responde a la siguiente consulta de forma precisa y útil.",
                       input=context if context else original,
                       output=corrected,
                       source="corrections",
                       quality_weight=3.0,  # Correcciones = mayor peso
                       hash=self._compute_hash(f"{original}{corrected}"),
                   )
                   samples.append(sample)

               logger.info(f"Extraídas {len(samples)} correcciones")
           except Exception as e:
               logger.error(f"Error extrayendo correcciones: {e}")

           return samples

       async def extract_preferences(self, db_connection) -> list[TrainingSample]:
           """Extrae preferencias del usuario desde Flash Memory."""
           samples = []
           query = """
               SELECT preference_key, preference_value, context
               FROM flash_memory.preferences
               WHERE used_for_training = false
               ORDER BY updated_at DESC
               LIMIT 2000
           """
           try:
               rows = await db_connection.fetch(query)
               for row in rows:
                   key = row["preference_key"]
                   value = row["preference_value"]
                   context = row.get("context", "")

                   if self._contains_personal_data(value):
                       continue  # Skip preferences con datos personales

                   sample = TrainingSample(
                       instruction=f"El usuario prefiere lo siguiente sobre {key}.",
                       input=context,
                       output=value,
                       source="preferences",
                       quality_weight=1.5,
                       hash=self._compute_hash(f"{key}{value}"),
                   )
                   samples.append(sample)

               logger.info(f"Extraídas {len(samples)} preferencias")
           except Exception as e:
               logger.error(f"Error extrayendo preferencias: {e}")

           return samples

       async def extract_skills(self, db_connection) -> list[TrainingSample]:
           """Extrae skills aprendidos desde Flash Memory."""
           samples = []
           query = """
               SELECT skill_name, skill_description, example_input, example_output
               FROM flash_memory.skills
               WHERE used_for_training = false
               ORDER BY confidence DESC
               LIMIT 2000
           """
           try:
               rows = await db_connection.fetch(query)
               for row in rows:
                   name = row["skill_name"]
                   desc = row["skill_description"]
                   ex_input = row.get("example_input", "")
                   ex_output = row.get("example_output", "")

                   if self._contains_personal_data(ex_output):
                       ex_output = self._sanitize_text(ex_output)

                   sample = TrainingSample(
                       instruction=f"{desc}",
                       input=ex_input,
                       output=ex_output if ex_output else f"Skill aplicado: {name}",
                       source="skills",
                       quality_weight=2.0,
                       hash=self._compute_hash(f"{name}{ex_input}{ex_output}"),
                   )
                   samples.append(sample)

               logger.info(f"Extraídos {len(samples)} skills")
           except Exception as e:
               logger.error(f"Error extrayendo skills: {e}")

           return samples

       def deduplicate(self, samples: list[TrainingSample]) -> list[TrainingSample]:
           """Elimina duplicados basado en hash de contenido."""
           seen_hashes = set()
           unique = []
           duplicates = 0

           for sample in samples:
               if sample.hash not in seen_hashes:
                   seen_hashes.add(sample.hash)
                   unique.append(sample)
               else:
                   duplicates += 1

           logger.info(f"Deduplicación: {len(samples)} → {len(unique)} "
                       f"({duplicates} duplicados eliminados)")
           return unique

       def export_jsonl(self, samples: list[TrainingSample], filename: str = None) -> str:
           """Exporta muestras a archivo JSONL para entrenamiento."""
           if filename is None:
               timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
               filename = f"training_data_{timestamp}.jsonl"

           output_path = self.output_dir / filename
           with open(output_path, 'w', encoding='utf-8') as f:
               for sample in samples:
                   record = {
                       "instruction": sample.instruction,
                       "input": sample.input,
                       "output": sample.output,
                   }
                   f.write(json.dumps(record, ensure_ascii=False) + '\n')

           logger.info(f"Exportadas {len(samples)} muestras a {output_path}")
           return str(output_path)

       async def extract_all(self, db_connection) -> tuple[str, ExtractionStats]:
           """
           Extrae todos los datos de Flash Memory, deduplica, y exporta JSONL.
           Retorna (path_al_jsonl, estadísticas).
           """
           # 1. Extraer de cada fuente
           corrections = await self.extract_corrections(db_connection)
           preferences = await self.extract_preferences(db_connection)
           skills = await self.extract_skills(db_connection)

           all_samples = corrections + preferences + skills
           privacy_count = 0  # Ya filtrado en extracción

           # 2. Deduplicar
           original_count = len(all_samples)
           unique_samples = self.deduplicate(all_samples)
           duplicates = original_count - len(unique_samples)

           # 3. Ordenar por peso de calidad (correcciones primero)
           unique_samples.sort(key=lambda s: s.quality_weight, reverse=True)

           # 4. Verificar mínimo
           if len(unique_samples) < self.MIN_SAMPLES:
               raise ValueError(
                   f"Muestras insuficientes: {len(unique_samples)} < {self.MIN_SAMPLES}. "
                   f"Se necesitan más correcciones/preferencias/skills."
               )

           # 5. Exportar
           output_path = self.export_jsonl(unique_samples)

           stats = ExtractionStats(
               total_extracted=original_count,
               corrections=len(corrections),
               preferences=len(preferences),
               skills=len(skills),
               duplicates_removed=duplicates,
               privacy_filtered=privacy_count,
               final_count=len(unique_samples),
               timestamp=datetime.now().isoformat(),
           )

           logger.info(f"Extracción completa: {stats.final_count} muestras "
                       f"(correcciones={stats.corrections}, preferencias={stats.preferences}, "
                       f"skills={stats.skills})")

           return output_path, stats

2. Actualizar src/training/__init__.py:

   Ruta: ~/yeyo-os/src/training/__init__.py
   Contenido:
   from .lora_pipeline import LoRAPipeline, TrainingConfig, TrainingResult
   from .validation import LoRAValidator, ValidationResult, ValidationMetrics
   from .data_extractor import TrainingDataExtractor, ExtractionStats

3. Crear archivo tests/unit/training/test_data_extractor.py:

   Ruta: ~/yeyo-os/tests/unit/training/test_data_extractor.py
   Contenido:

   """Tests para Training Data Extractor — Micro-fase 7.2"""

   import json
   import os
   import tempfile
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from pathlib import Path
   from src.training.data_extractor import (
       TrainingDataExtractor, TrainingSample, ExtractionStats,
   )


   class TestTrainingDataExtractor:
       """Tests para TrainingDataExtractor."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.extractor = TrainingDataExtractor(output_dir=self.tmp_dir)

       def test_creates_output_dir(self):
           assert Path(self.tmp_dir).exists()

       def test_compute_hash_deterministic(self):
           h1 = self.extractor._compute_hash("hello world")
           h2 = self.extractor._compute_hash("hello world")
           assert h1 == h2

       def test_compute_hash_case_insensitive(self):
           h1 = self.extractor._compute_hash("Hello World")
           h2 = self.extractor._compute_hash("hello world")
           assert h1 == h2

       def test_contains_personal_data_email(self):
           assert self.extractor._contains_personal_data("mi email es user@example.com")

       def test_contains_personal_data_phone(self):
           assert self.extractor._contains_personal_data("llama al 555-123-4567")

       def test_contains_personal_data_credit_card(self):
           assert self.extractor._contains_personal_data("tarjeta 4111 1111 1111 1111")

       def test_contains_personal_data_ip(self):
           assert self.extractor._contains_personal_data("IP: 192.168.1.100")

       def test_no_personal_data(self):
           assert not self.extractor._contains_personal_data("Hola, ¿cómo estás?")

       def test_sanitize_text_redacts_email(self):
           result = self.extractor._sanitize_text("envía a user@test.com por favor")
           assert "[REDACTED]" in result
           assert "user@test.com" not in result

       def test_deduplicate_removes_duplicates(self):
           samples = [
               TrainingSample(instruction="a", output="b", source="corrections",
                              hash="abc123"),
               TrainingSample(instruction="c", output="d", source="corrections",
                              hash="def456"),
               TrainingSample(instruction="a", output="b", source="corrections",
                              hash="abc123"),
           ]
           result = self.extractor.deduplicate(samples)
           assert len(result) == 2

       def test_deduplicate_preserves_unique(self):
           samples = [
               TrainingSample(instruction="a", output="b", source="corrections",
                              hash="abc"),
               TrainingSample(instruction="c", output="d", source="preferences",
                              hash="def"),
           ]
           result = self.extractor.deduplicate(samples)
           assert len(result) == 2

       def test_export_jsonl_creates_file(self):
           samples = [
               TrainingSample(instruction="test", output="resp", source="corrections",
                              hash="abc"),
           ]
           path = self.extractor.export_jsonl(samples, "test.jsonl")
           assert Path(path).exists()
           with open(path) as f:
               data = json.loads(f.readline())
               assert data["instruction"] == "test"
               assert data["output"] == "resp"

       def test_export_jsonl_correct_format(self):
           samples = [
               TrainingSample(instruction="i1", input="in1", output="o1",
                              source="corrections", hash="a"),
               TrainingSample(instruction="i2", input="in2", output="o2",
                              source="skills", hash="b"),
           ]
           path = self.extractor.export_jsonl(samples, "format.jsonl")
           with open(path) as f:
               lines = f.readlines()
           assert len(lines) == 2
           for line in lines:
               data = json.loads(line)
               assert "instruction" in data
               assert "input" in data
               assert "output" in data

       @pytest.mark.asyncio
       async def test_extract_corrections(self):
           mock_db = AsyncMock()
           mock_db.fetch.return_value = [
               {"original_response": "resp1", "corrected_response": "corrected1",
                "context": "ctx1", "created_at": "2025-01-01"},
               {"original_response": "resp2", "corrected_response": "corrected2",
                "context": "ctx2", "created_at": "2025-01-02"},
           ]
           result = await self.extractor.extract_corrections(mock_db)
           assert len(result) == 2
           assert all(s.source == "corrections" for s in result)
           assert all(s.quality_weight == 3.0 for s in result)

       @pytest.mark.asyncio
       async def test_extract_all_rejects_insufficient(self):
           mock_db = AsyncMock()
           mock_db.fetch.return_value = [
               {"original_response": "r", "corrected_response": "c",
                "context": "", "created_at": "2025-01-01"},
           ]
           with pytest.raises(ValueError, match="Muestras insuficientes"):
               await self.extractor.extract_all(mock_db)

       def test_min_samples_is_100(self):
           assert TrainingDataExtractor.MIN_SAMPLES == 100

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/training/test_data_extractor.py -v

VERIFICAR:
- [ ] Archivo src/training/data_extractor.py existe con TrainingDataExtractor
- [ ] Extrae de 3 fuentes: correcciones (peso 3.0), preferencias (1.5), skills (2.0)
- [ ] Formato JSONL con instruction/input/output
- [ ] Detecta y redacta datos personales (email, teléfono, tarjeta, IP)
- [ ] Deduplicación por hash funciona
- [ ] Rechaza <100 muestras
- [ ] Export crea archivo JSONL válido
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- pytest-asyncio: pip install pytest-asyncio

NO HACER:
- No incluir datos personales crudos en training data
- No permitir entrenamiento con <100 muestras
- No modificar Flash Memory directamente

GATE: Extractor prepara datos de Flash Memory en JSONL, filtra privacidad, deduplica, valida mínimo 100 muestras, todos los tests pasan.
```
