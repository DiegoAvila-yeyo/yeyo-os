"""
YeyoOS — Grafo de Chat Contextual
Micro-fase 4.21 — Capa 4: Sistema Nervioso

Flujo: mejora prompt → chat con LLM → extrae memorias relevantes → guarda en Flash Memory
"""

from typing import Optional, Any
from ..estado import EstadoGrafo
from ..nodo import nodo, NodoFuncion
from ..grafo import YeyoGrafo
from ..catalogo import CatalogoNodos


def crear_grafo_chat_contextual(
    ollama_provider: Optional[Any] = None,
    flash_memory: Optional[Any] = None,
) -> YeyoGrafo:
    """
    Factory: crea y retorna el grafo de chat contextual configurado.

    Flujo de nodos:
    1. mejorar_prompt: enriquece el prompt con contexto del historial
    2. nodo_chat: envía el prompt mejorado a Ollama
    3. extraer_memorias: identifica datos importantes en la respuesta
    4. nodo_guardar_memoria: guarda las memorias extraídas

    Entrada esperada en estado.entrada:
      - "mensaje": str — mensaje del usuario
      - "historial": list (opcional) — mensajes previos
      - "usuario_id": str (opcional) — ID del usuario

    Salida en estado.salida:
      - "respuesta": str — respuesta final del LLM
      - "memorias_guardadas": int — cantidad de memorias nuevas guardadas
    """
    catalogo = CatalogoNodos(
        ollama_provider=ollama_provider,
        flash_memory=flash_memory,
    )

    @nodo(id="mejorar_prompt", timeout=10.0)
    async def mejorar_prompt(estado: EstadoGrafo) -> EstadoGrafo:
        """Enriquece el prompt con contexto del sistema."""
        mensaje_original = estado.entrada.get("mensaje", "")
        usuario_id = estado.entrada.get("usuario_id", "anonimo")
        historial = estado.entrada.get("historial", [])

        # El prompt mejorado incluye el sistema base de YeyoOS
        estado.contexto["mensaje_mejorado"] = mensaje_original
        estado.contexto["historial_procesado"] = historial
        estado.contexto["usuario_id"] = usuario_id

        # Preparar entrada para nodo_chat
        estado.entrada["mensaje"] = mensaje_original
        estado.entrada["sistema"] = (
            "Eres YeyoOS, un asistente AI nativo e inteligente. "
            "Responde de forma concisa y útil."
        )
        estado.entrada["historial"] = historial
        return estado

    @nodo(id="extraer_memorias", timeout=15.0)
    async def extraer_memorias(estado: EstadoGrafo) -> EstadoGrafo:
        """
        Identifica datos importantes en la respuesta del LLM
        y los prepara para guardar en Flash Memory.
        """
        respuesta = estado.salida.get("respuesta", "")
        mensaje_usuario = estado.entrada.get("mensaje", "")

        # Preparar dato para nodo_guardar_memoria
        estado.entrada["dato"] = f"Usuario: {mensaje_usuario}\nAsistente: {respuesta}"
        estado.entrada["tipo"] = "conversacion"
        estado.entrada["importancia"] = 0.6
        return estado

    @nodo(id="finalizar_chat", timeout=5.0)
    async def finalizar_chat(estado: EstadoGrafo) -> EstadoGrafo:
        """Finaliza el flujo y prepara la respuesta final."""
        memoria_id = estado.salida.get("memoria_id")
        estado.salida["memorias_guardadas"] = 1 if memoria_id else 0
        return estado

    nodo_chat = catalogo.obtener("nodo_chat")
    nodo_guardar = catalogo.obtener("nodo_guardar_memoria")

    grafo = (
        YeyoGrafo(
            "grafo_chat_contextual",
            "Conversación contextual con memoria: mejora prompt → chat → guarda memoria"
        )
        .agregar_nodo(mejorar_prompt)
        .agregar_nodo(nodo_chat)
        .agregar_nodo(extraer_memorias)
        .agregar_nodo(nodo_guardar)
        .agregar_nodo(finalizar_chat)
        .inicio("mejorar_prompt")
        .edge("mejorar_prompt", "nodo_chat")
        .edge("nodo_chat", "extraer_memorias")
        .edge("extraer_memorias", "nodo_guardar_memoria")
        .edge("nodo_guardar_memoria", "finalizar_chat")
        .fin("finalizar_chat")
    )

    return grafo
