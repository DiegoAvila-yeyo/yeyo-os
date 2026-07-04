"""
YeyoOS — Yeyo-pruebas Node API
Chat + pruebas rápidas con el modelo Ollama-HACK (dolphin-llama3:8b).

Off-by-default: requiere OLLAMA_HACK_ENABLED=true y una instancia Ollama-HACK corriendo.
"""

import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ia.interfaces import IAMessage
from src.ia.ollama_provider import OllamaProvider

logger = logging.getLogger("yeyoos.api.pruebas")

router = APIRouter(prefix="/api/v1/pruebas", tags=["pruebas"])

_default_ia = None
_hack_ia = None
_pruebas_ia: OllamaProvider | None = None

# Vault aislado (RAG cerrado): todo lo ingerido va a este namespace.
# No se mezcla con chat:usuario, codigo:usuario, etc.
_vault_namespace: str = os.getenv("PRUEBAS_VAULT_NAMESPACE", "pruebas:vault:yeyo-pruebas")

# Inyectados desde main.py si Postgres está disponible
_flash_memory = None
_embedding_service = None
_node_memory = None


def set_flash_memory(mem):
    global _flash_memory
    _flash_memory = mem


def set_embedding_service(emb):
    global _embedding_service
    _embedding_service = emb


def set_node_memory_service(nm):
    global _node_memory
    _node_memory = nm


def set_vault_namespace(ns: str) -> None:
    global _vault_namespace
    if ns and isinstance(ns, str):
        _vault_namespace = ns.strip()


def _get_pruebas_ia() -> OllamaProvider | None:
    """Retorna el provider a usar para Yeyo-pruebas.

    Prioridad:
    1) Ollama-HACK (si está habilitado y healthy en main.py)
    2) Fallback: Ollama normal (11434) pero con modelo dolphin
       (útil para pruebas rápidas sin levantar la segunda instancia)
    """
    global _pruebas_ia

    if _hack_ia is not None:
        return _hack_ia

    if _pruebas_ia is not None:
        return _pruebas_ia

    host = os.getenv("OLLAMA_PRUEBAS_HOST")
    if not host:
        host = getattr(_default_ia, "host", None) or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    model = os.getenv("OLLAMA_PRUEBAS_MODEL", "dolphin-uncensored")
    timeout = float(os.getenv("OLLAMA_PRUEBAS_TIMEOUT", "120"))

    try:
        _pruebas_ia = OllamaProvider(host=host, model=model, timeout=timeout)
        return _pruebas_ia
    except Exception:
        _pruebas_ia = None
        return None


def set_ia_provider(ia):
    global _default_ia
    _default_ia = ia


def set_hack_ia_provider(ia):
    global _hack_ia
    _hack_ia = ia


class PruebasChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=6000)
    history: list[dict] = Field(default_factory=list)
    use_vault: bool = Field(default=True, description="Si True, usa solo el vault aislado como contexto")


class PruebasChatResponse(BaseModel):
    response: str
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0


SYSTEM_PROMPT = (
    "Eres YEYO-PRUEBAS: un chat de experimentación con un vault aislado. "
    "Responde en español, directo y útil. "
    "Si el usuario pega código, puedes explicarlo, refactorizarlo o proponer mejoras. "
    "Si falta contexto, pregunta lo mínimo necesario. "
    "No inventes información: si no está en el vault, dilo explícitamente."
)


@router.post("/chat", response_model=PruebasChatResponse)
async def pruebas_chat(req: PruebasChatRequest) -> PruebasChatResponse:
    ia = _get_pruebas_ia()
    if ia is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "IA provider no disponible para Yeyo-pruebas. "
                "Opción A (recomendada): OLLAMA_HACK_ENABLED=true + instancia en :11435. "
                "Opción B: tener Ollama normal corriendo en :11434 con dolphin instalado."
            ),
        )

    vault_context = ""
    if req.use_vault and _node_memory is not None:
        # RAG cerrado: SOLO este namespace.
        vault_context = await _node_memory.get_context(
            query=req.message,
            namespaces=[_vault_namespace],
            limit=6,
            threshold=0.25,
        )

    system = SYSTEM_PROMPT
    if vault_context:
        system += "\n\n[VAULT CONTEXT]\n" + vault_context

    messages: list[IAMessage] = [IAMessage(role="system", content=system)]

    for msg in req.history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role not in ("system", "user", "assistant"):
            role = "user"
        if content:
            messages.append(IAMessage(role=role, content=content))

    messages.append(IAMessage(role="user", content=req.message))

    resp = await ia.chat(messages, temperature=0.7)
    return PruebasChatResponse(
        response=resp.content,
        model=resp.model,
        tokens_used=resp.tokens_used,
        latency_ms=resp.latency_ms,
    )
