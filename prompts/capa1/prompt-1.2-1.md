## ═══════════════════════════════════════
## MICRO-FASE 1.2 — MemoriaProvider Interface
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 1.2-1 [VSCODE] — Crear interfaz abstracta MemoriaProvider

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.2: crear la interfaz abstracta para Flash Memory, el sistema de memoria persistente.

CONTEXTO:
- Capa 0 completada: PostgreSQL 16 + pgvector funcionando
- Micro-fases 1.0-1.1 completadas: IAProvider + OllamaProvider listos
- Flash Memory es la MEMORIA del OS: NUNCA se borra, solo se mueve entre tiers
- Tiers: HOT (acceso frecuente) → WARM (acceso medio) → COLD (archivo)
- Cada memoria tiene checksum SHA-256 para integridad
- Búsqueda semántica via pgvector embeddings
- REGLA FUNDAMENTAL: La memoria NUNCA se elimina. No existe método delete.

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/memory
   mkdir -p tests/unit/memory

2. Crear archivo src/memory/__init__.py:

   Ruta: ~/yeyo-os/src/memory/__init__.py
   Contenido:
   from .interfaces import MemoriaProvider, Memory, MemoryTier, MemoryType

3. Crear archivo src/memory/interfaces.py:

   Ruta: ~/yeyo-os/src/memory/interfaces.py
   Contenido:

   """
   YeyoOS — MemoriaProvider Interface (Puerto Hexagonal)
   Micro-fase 1.2 — Capa 1: Esqueleto
   
   Interfaz abstracta para Flash Memory.
   La memoria en YeyoOS es PERMANENTE — nunca se elimina,
   solo se mueve entre tiers (HOT/WARM/COLD).
   Cada memoria tiene checksum SHA-256 para garantizar integridad.
   """
   
   from abc import ABC, abstractmethod
   from datetime import datetime
   from enum import Enum
   from typing import Optional
   
   from pydantic import BaseModel, Field
   
   
   class MemoryTier(str, Enum):
       """Tier de acceso de la memoria."""
       HOT = "HOT"      # Acceso frecuente, en cache Redis
       WARM = "WARM"     # Acceso medio, solo en PostgreSQL
       COLD = "COLD"     # Archivo, comprimido, acceso raro
   
   
   class MemoryType(str, Enum):
       """Tipo semántico de la memoria."""
       CONVERSATION = "conversation"  # Fragmentos de conversación
       PREFERENCE = "preference"      # Preferencias del usuario
       FACT = "fact"                   # Hechos aprendidos
       CORRECTION = "correction"      # Correcciones del usuario
       SKILL = "skill"                # Habilidades aprendidas
   
   
   class Memory(BaseModel):
       """Modelo de una memoria persistente en Flash Memory."""
       id: str = Field(..., min_length=1)
       content: str = Field(..., min_length=1)
       type: MemoryType
       tier: MemoryTier = MemoryTier.WARM
       embedding: Optional[list[float]] = None
       checksum: str = Field(..., min_length=64, max_length=64)  # SHA-256
       created_at: datetime
       accessed_at: datetime
       access_count: int = Field(default=0, ge=0)
       metadata: dict = Field(default_factory=dict)
   
   
   class MemoriaProvider(ABC):
       """
       Puerto hexagonal para Flash Memory.
       
       IMPORTANTE: No existe método delete().
       La memoria en YeyoOS es PERMANENTE por diseño.
       Solo se mueve entre tiers para gestionar rendimiento.
       """
   
       @abstractmethod
       async def store(
           self,
           content: str,
           type: MemoryType,
           metadata: dict | None = None,
       ) -> Memory:
           """
           Almacena nueva memoria. Genera checksum SHA-256 automáticamente.
           Nuevas memorias entran como WARM por defecto.
           """
           ...
   
       @abstractmethod
       async def recall(self, query: str, limit: int = 5) -> list[Memory]:
           """
           Busca memorias relevantes por query (combinación de texto y semántica).
           Actualiza accessed_at y access_count de las memorias encontradas.
           """
           ...
   
       @abstractmethod
       async def recall_by_type(
           self, type: MemoryType, limit: int = 10
       ) -> list[Memory]:
           """Busca memorias por tipo, ordenadas por acceso más reciente."""
           ...
   
       @abstractmethod
       async def get_by_id(self, id: str) -> Memory | None:
           """Obtiene una memoria específica por su ID."""
           ...
   
       @abstractmethod
       async def search_semantic(
           self,
           query: str,
           threshold: float = 0.7,
           limit: int = 5,
       ) -> list[Memory]:
           """
           Búsqueda puramente semántica via embeddings pgvector.
           threshold: similitud mínima (0.0 a 1.0).
           """
           ...
   
       @abstractmethod
       async def promote_tier(self, id: str) -> Memory:
           """
           Promueve una memoria: COLD → WARM → HOT.
           Si ya es HOT, no hace nada.
           """
           ...
   
       @abstractmethod
       async def demote_tier(self, id: str) -> Memory:
           """
           Degrada una memoria: HOT → WARM → COLD.
           Si ya es COLD, no hace nada.
           """
           ...
   
       @abstractmethod
       async def get_stats(self) -> dict:
           """
           Retorna estadísticas de Flash Memory:
           - Conteo por tier (HOT/WARM/COLD)
           - Conteo por tipo
           - Total de memorias
           """
           ...
   
       @abstractmethod
       async def health_check(self) -> bool:
           """Verifica conexión a PostgreSQL + pgvector."""
           ...

4. Crear archivo tests/unit/memory/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/memory/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/memory/test_memory_interfaces.py:

   Ruta: ~/yeyo-os/tests/unit/memory/test_memory_interfaces.py
   Contenido:

   """Tests para MemoriaProvider Interface — Micro-fase 1.2"""
   
   import pytest
   from datetime import datetime
   from pydantic import ValidationError
   from src.memory.interfaces import (
       MemoriaProvider,
       Memory,
       MemoryTier,
       MemoryType,
   )
   
   
   class TestMemoryTier:
       """Tests para el enum MemoryTier."""
   
       def test_hot_value(self):
           assert MemoryTier.HOT == "HOT"
   
       def test_warm_value(self):
           assert MemoryTier.WARM == "WARM"
   
       def test_cold_value(self):
           assert MemoryTier.COLD == "COLD"
   
       def test_only_three_tiers(self):
           assert len(MemoryTier) == 3
   
   
   class TestMemoryType:
       """Tests para el enum MemoryType."""
   
       def test_conversation(self):
           assert MemoryType.CONVERSATION == "conversation"
   
       def test_preference(self):
           assert MemoryType.PREFERENCE == "preference"
   
       def test_fact(self):
           assert MemoryType.FACT == "fact"
   
       def test_correction(self):
           assert MemoryType.CORRECTION == "correction"
   
       def test_skill(self):
           assert MemoryType.SKILL == "skill"
   
       def test_only_five_types(self):
           assert len(MemoryType) == 5
   
   
   class TestMemory:
       """Tests para el modelo Memory."""
   
       @pytest.fixture
       def valid_memory(self):
           return Memory(
               id="mem-001",
               content="El usuario prefiere respuestas concisas",
               type=MemoryType.PREFERENCE,
               tier=MemoryTier.HOT,
               checksum="a" * 64,
               created_at=datetime.now(),
               accessed_at=datetime.now(),
               access_count=5,
               metadata={"source": "chat"},
           )
   
       def test_valid_memory_creates(self, valid_memory):
           assert valid_memory.id == "mem-001"
           assert valid_memory.type == MemoryType.PREFERENCE
           assert valid_memory.tier == MemoryTier.HOT
   
       def test_default_tier_is_warm(self):
           mem = Memory(
               id="mem-002",
               content="test",
               type=MemoryType.FACT,
               checksum="b" * 64,
               created_at=datetime.now(),
               accessed_at=datetime.now(),
           )
           assert mem.tier == MemoryTier.WARM
   
       def test_default_access_count_is_zero(self):
           mem = Memory(
               id="mem-003",
               content="test",
               type=MemoryType.FACT,
               checksum="c" * 64,
               created_at=datetime.now(),
               accessed_at=datetime.now(),
           )
           assert mem.access_count == 0
   
       def test_default_metadata_is_empty_dict(self):
           mem = Memory(
               id="mem-004",
               content="test",
               type=MemoryType.FACT,
               checksum="d" * 64,
               created_at=datetime.now(),
               accessed_at=datetime.now(),
           )
           assert mem.metadata == {}
   
       def test_embedding_optional(self):
           mem = Memory(
               id="mem-005",
               content="test",
               type=MemoryType.FACT,
               checksum="e" * 64,
               created_at=datetime.now(),
               accessed_at=datetime.now(),
           )
           assert mem.embedding is None
   
       def test_checksum_required(self):
           with pytest.raises(ValidationError):
               Memory(
                   id="mem-006",
                   content="test",
                   type=MemoryType.FACT,
                   created_at=datetime.now(),
                   accessed_at=datetime.now(),
               )
   
       def test_checksum_must_be_64_chars(self):
           with pytest.raises(ValidationError):
               Memory(
                   id="mem-007",
                   content="test",
                   type=MemoryType.FACT,
                   checksum="short",
                   created_at=datetime.now(),
                   accessed_at=datetime.now(),
               )
   
       def test_empty_content_rejected(self):
           with pytest.raises(ValidationError):
               Memory(
                   id="mem-008",
                   content="",
                   type=MemoryType.FACT,
                   checksum="f" * 64,
                   created_at=datetime.now(),
                   accessed_at=datetime.now(),
               )
   
       def test_negative_access_count_rejected(self):
           with pytest.raises(ValidationError):
               Memory(
                   id="mem-009",
                   content="test",
                   type=MemoryType.FACT,
                   checksum="g" * 64,
                   created_at=datetime.now(),
                   accessed_at=datetime.now(),
                   access_count=-1,
               )
   
   
   class TestMemoriaProvider:
       """Tests para la interfaz abstracta MemoriaProvider."""
   
       def test_cannot_instantiate_directly(self):
           with pytest.raises(TypeError):
               MemoriaProvider()
   
       def test_all_methods_are_abstract(self):
           abstract_methods = MemoriaProvider.__abstractmethods__
           expected = {
               "store",
               "recall",
               "recall_by_type",
               "get_by_id",
               "search_semantic",
               "promote_tier",
               "demote_tier",
               "get_stats",
               "health_check",
           }
           assert abstract_methods == expected
   
       def test_has_nine_abstract_methods(self):
           assert len(MemoriaProvider.__abstractmethods__) == 9
   
       def test_no_delete_method_exists(self):
           """FUNDAMENTAL: La memoria NUNCA se elimina."""
           assert not hasattr(MemoriaProvider, "delete")
           assert not hasattr(MemoriaProvider, "remove")
           assert not hasattr(MemoriaProvider, "drop")
           assert not hasattr(MemoriaProvider, "purge")

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/memory/test_memory_interfaces.py -v

VERIFICAR:
- [ ] Archivo src/memory/interfaces.py existe con MemoriaProvider, Memory, MemoryTier, MemoryType
- [ ] TODOS los tests pasan (0 failed)
- [ ] MemoriaProvider no se puede instanciar
- [ ] NO existe método delete/remove/drop/purge
- [ ] Memory requiere checksum de 64 caracteres (SHA-256)
- [ ] MemoryTier tiene exactamente 3 valores
- [ ] MemoryType tiene exactamente 5 valores
- [ ] Import funciona: `from src.memory.interfaces import MemoriaProvider, Memory`

SI FALLA:
- Import error: verificar __init__.py en src/ y src/memory/
- Pydantic error: `pip install pydantic`
- Optional import: requiere Python 3.11+ para `X | None` syntax

NO HACER:
- NO agregar método delete — la memoria es permanente por diseño
- No implementar el proveedor concreto (eso es Capa 2)
- No conectar a PostgreSQL todavía
- No agregar lógica de promoción/degradación automática de tiers

GATE: MemoriaProvider abstracta con 9 métodos, Memory valida checksum SHA-256, NO existe método delete, todos los tests pasan.
```
