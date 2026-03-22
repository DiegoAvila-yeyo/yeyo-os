from .interfaces import IAProvider, IAMessage, IAResponse
from .ollama_provider import OllamaProvider

# Módulos que requieren sentence-transformers (opcional en dev)
try:
    from .embeddings import EmbeddingService
except ImportError:
    EmbeddingService = None

try:
    from .anti_hallucination import AntiHallucination
except ImportError:
    AntiHallucination = None

try:
    from .rag import RAGPipeline
except ImportError:
    RAGPipeline = None
