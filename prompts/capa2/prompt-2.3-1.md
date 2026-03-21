## ═══════════════════════════════════════
## MICRO-FASE 2.3 — Embedding Pipeline
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.3-1 [VSCODE] — Implementar servicio de embeddings con sentence-transformers

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.3 de Capa 2 (Cerebro): implementar el servicio de generación de embeddings con sentence-transformers para búsqueda semántica en Flash Memory.

CONTEXTO:
- Capa 0 y 1 completadas
- Micro-fase 2.0-2.1: Flash Memory schema y CRUD funcionando
- pgvector espera embeddings de 384 dimensiones (all-MiniLM-L6-v2)
- IMPORTANTE: Embeddings corren en CPU, NO en GPU
- La GPU (GTX 1060 3GB) es exclusiva para Ollama y generación de imágenes
- sentence-transformers genera vectores densos para similitud semántica
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencias:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install sentence-transformers numpy

2. Crear archivo src/ia/embeddings.py:

   Ruta: ~/yeyo-os/src/ia/embeddings.py
   Contenido:

   """
   YeyoOS — EmbeddingService (Pipeline de Embeddings en CPU)
   Micro-fase 2.3 — Capa 2: Cerebro

   Genera embeddings vectoriales con sentence-transformers.
   IMPORTANTE: Corre en CPU. La GPU es exclusiva para Ollama/SD.
   Modelo: all-MiniLM-L6-v2 → 384 dimensiones.
   """

   import logging
   import os
   from typing import Optional

   import numpy as np
   from sentence_transformers import SentenceTransformer

   logger = logging.getLogger("yeyoos.embeddings")

   # Forzar CPU para sentence-transformers
   os.environ["CUDA_VISIBLE_DEVICES"] = ""


   class EmbeddingService:
       """
       Servicio de generación de embeddings para búsqueda semántica.
       Usa sentence-transformers en CPU (GPU reservada para Ollama).
       """

       def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
           self.model_name = model_name
           self.model: Optional[SentenceTransformer] = None
           self.dimension: int = 384  # Dimensión del modelo all-MiniLM-L6-v2
           self._loaded = False

       def _ensure_loaded(self):
           """Carga el modelo lazy (solo cuando se necesita por primera vez)."""
           if not self._loaded:
               logger.info(f"Cargando modelo de embeddings: {self.model_name} (CPU)")
               self.model = SentenceTransformer(
                   self.model_name,
                   device="cpu",
               )
               self._loaded = True
               logger.info(f"Modelo cargado: {self.model_name} ({self.dimension}d)")

       def generate(self, text: str) -> list[float]:
           """
           Genera embedding para un texto.
           Retorna vector de 384 dimensiones.
           """
           if not text or not text.strip():
               return [0.0] * self.dimension

           self._ensure_loaded()
           embedding = self.model.encode(
               text,
               convert_to_numpy=True,
               normalize_embeddings=True,
               show_progress_bar=False,
           )
           return embedding.tolist()

       def generate_batch(self, texts: list[str]) -> list[list[float]]:
           """
           Genera embeddings para múltiples textos en batch.
           Más eficiente que llamar generate() individualmente.
           """
           if not texts:
               return []

           # Filtrar textos vacíos, mantener índices
           valid_texts = []
           valid_indices = []
           for i, text in enumerate(texts):
               if text and text.strip():
                   valid_texts.append(text)
                   valid_indices.append(i)

           if not valid_texts:
               return [[0.0] * self.dimension for _ in texts]

           self._ensure_loaded()
           embeddings = self.model.encode(
               valid_texts,
               convert_to_numpy=True,
               normalize_embeddings=True,
               show_progress_bar=False,
               batch_size=32,
           )

           # Reconstruir resultado con zeros para textos vacíos
           result = [[0.0] * self.dimension for _ in texts]
           for idx, emb in zip(valid_indices, embeddings):
               result[idx] = emb.tolist()

           return result

       def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
           """
           Calcula similitud coseno entre dos embeddings.
           Retorna valor entre -1.0 y 1.0 (normalizado: 0.0 a 1.0).
           """
           vec1 = np.array(embedding1)
           vec2 = np.array(embedding2)

           # Evitar división por cero
           norm1 = np.linalg.norm(vec1)
           norm2 = np.linalg.norm(vec2)
           if norm1 == 0 or norm2 == 0:
               return 0.0

           cosine = np.dot(vec1, vec2) / (norm1 * norm2)
           return float(cosine)

       def get_dimension(self) -> int:
           """Retorna la dimensión del embedding."""
           return self.dimension

       def get_model_name(self) -> str:
           """Retorna el nombre del modelo de embeddings."""
           return self.model_name

       def is_loaded(self) -> bool:
           """Verifica si el modelo está cargado en memoria."""
           return self._loaded

3. Actualizar src/ia/__init__.py para incluir embeddings:

   Ruta: ~/yeyo-os/src/ia/__init__.py
   Agregar al final:
   from .embeddings import EmbeddingService

4. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/ia/test_embeddings.py
   Contenido:

   """
   Tests para EmbeddingService — Micro-fase 2.3
   El modelo se descarga automáticamente la primera vez.
   """

   import pytest
   import numpy as np
   from src.ia.embeddings import EmbeddingService


   @pytest.fixture(scope="module")
   def embedding_service():
       """Fixture con scope=module para no recargar modelo en cada test."""
       return EmbeddingService()


   class TestEmbeddingServiceBasic:
       """Tests básicos sin cargar modelo."""

       def test_default_model_name(self):
           service = EmbeddingService()
           assert service.get_model_name() == "all-MiniLM-L6-v2"

       def test_dimension_is_384(self):
           service = EmbeddingService()
           assert service.get_dimension() == 384

       def test_not_loaded_initially(self):
           service = EmbeddingService()
           assert service.is_loaded() is False

       def test_custom_model_name(self):
           service = EmbeddingService(model_name="custom-model")
           assert service.get_model_name() == "custom-model"


   class TestEmbeddingServiceGenerate:
       """Tests que requieren cargar el modelo."""

       def test_generate_returns_list(self, embedding_service):
           result = embedding_service.generate("Hola mundo")
           assert isinstance(result, list)

       def test_generate_correct_dimension(self, embedding_service):
           result = embedding_service.generate("Test de dimensión")
           assert len(result) == 384

       def test_generate_all_floats(self, embedding_service):
           result = embedding_service.generate("Test de tipos")
           assert all(isinstance(x, float) for x in result)

       def test_generate_empty_text_returns_zeros(self, embedding_service):
           result = embedding_service.generate("")
           assert len(result) == 384
           assert all(x == 0.0 for x in result)

       def test_generate_whitespace_returns_zeros(self, embedding_service):
           result = embedding_service.generate("   ")
           assert all(x == 0.0 for x in result)

       def test_model_loaded_after_generate(self, embedding_service):
           embedding_service.generate("trigger load")
           assert embedding_service.is_loaded() is True

       def test_generate_normalized(self, embedding_service):
           """Embeddings normalizados deben tener norma ~1.0."""
           result = embedding_service.generate("Test normalización")
           norm = np.linalg.norm(result)
           assert abs(norm - 1.0) < 0.01


   class TestEmbeddingServiceBatch:
       """Tests de generación en batch."""

       def test_batch_returns_list_of_lists(self, embedding_service):
           results = embedding_service.generate_batch(["Hola", "Mundo"])
           assert isinstance(results, list)
           assert len(results) == 2
           assert all(isinstance(r, list) for r in results)

       def test_batch_correct_dimensions(self, embedding_service):
           results = embedding_service.generate_batch(["Uno", "Dos", "Tres"])
           assert all(len(r) == 384 for r in results)

       def test_batch_empty_list(self, embedding_service):
           results = embedding_service.generate_batch([])
           assert results == []

       def test_batch_handles_empty_strings(self, embedding_service):
           results = embedding_service.generate_batch(["Hola", "", "Mundo"])
           assert len(results) == 3
           assert len(results[0]) == 384
           assert all(x == 0.0 for x in results[1])  # vacío = zeros
           assert len(results[2]) == 384


   class TestEmbeddingSimilarity:
       """Tests de similitud coseno."""

       def test_identical_texts_high_similarity(self, embedding_service):
           emb1 = embedding_service.generate("Python es genial")
           emb2 = embedding_service.generate("Python es genial")
           sim = embedding_service.similarity(emb1, emb2)
           assert sim > 0.99  # Idénticos ≈ 1.0

       def test_similar_texts_high_similarity(self, embedding_service):
           emb1 = embedding_service.generate("Me gusta programar en Python")
           emb2 = embedding_service.generate("Disfruto codear con Python")
           sim = embedding_service.similarity(emb1, emb2)
           assert sim > 0.5  # Similares > 0.5

       def test_different_texts_low_similarity(self, embedding_service):
           emb1 = embedding_service.generate("Programación en Python")
           emb2 = embedding_service.generate("Receta de torta de chocolate")
           sim = embedding_service.similarity(emb1, emb2)
           assert sim < 0.5  # Diferentes < 0.5

       def test_similarity_range(self, embedding_service):
           emb1 = embedding_service.generate("Test rango")
           emb2 = embedding_service.generate("Otro texto")
           sim = embedding_service.similarity(emb1, emb2)
           assert -1.0 <= sim <= 1.0

       def test_similarity_zero_vectors(self, embedding_service):
           zeros = [0.0] * 384
           emb = embedding_service.generate("Algo")
           sim = embedding_service.similarity(zeros, emb)
           assert sim == 0.0

       def test_runs_on_cpu(self, embedding_service):
           """Verificar que el modelo corre en CPU, no GPU."""
           import os
           assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""

5. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/ia/test_embeddings.py -v

VERIFICAR:
- [ ] Archivo src/ia/embeddings.py existe
- [ ] EmbeddingService genera embeddings de 384 dimensiones
- [ ] generate() retorna list[float] normalizado
- [ ] generate_batch() procesa múltiples textos eficientemente
- [ ] similarity() calcula cosine similarity correctamente
- [ ] Textos similares tienen alta similitud (>0.5)
- [ ] Textos diferentes tienen baja similitud (<0.5)
- [ ] Textos vacíos retornan vector de zeros
- [ ] Modelo corre en CPU (CUDA_VISIBLE_DEVICES="")
- [ ] TODOS los tests pasan

SI FALLA:
- sentence-transformers no instalado: `pip install sentence-transformers`
- numpy no instalado: `pip install numpy`
- Error descargando modelo: verificar conexión a internet (primera vez descarga ~90MB)
- CUDA error: verificar que CUDA_VISIBLE_DEVICES="" está seteado
- Memoria insuficiente: all-MiniLM-L6-v2 usa ~100MB RAM

NO HACER:
- No usar GPU para embeddings (GPU es para Ollama)
- No cambiar la dimensión del modelo (384 es fijo para all-MiniLM-L6-v2)
- No usar embeddings de Ollama para búsqueda semántica (sentence-transformers es más preciso para esto)
- No generar embeddings sincrónicamente en el request handler (usar background task)

GATE: EmbeddingService genera vectores de 384d en CPU, similitud funciona correctamente, batch processing funciona, todos los tests pasan.
```
