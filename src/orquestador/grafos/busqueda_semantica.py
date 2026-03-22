"""
YeyoOS — Grafo de Búsqueda Semántica
Micro-fase 4.21 — Capa 4: Sistema Nervioso

Flujo: embedding → buscar en Flash Memory → rankear → responder con contexto
"""

from typing import Optional, Any
from ..estado import EstadoGrafo
from ..nodo import nodo
from ..grafo import YeyoGrafo
from ..catalogo import CatalogoNodos


def crear_grafo_busqueda_semantica(
    ollama_provider: Optional[Any] = None,
    flash_memory: Optional[Any] = None,
) -> YeyoGrafo:
    """
    Factory: crea y retorna el grafo de búsqueda semántica configurado.

    Flujo de nodos:
    1. preparar_busqueda: normaliza la query de búsqueda
    2. nodo_embeddings: genera embedding de la query
    3. nodo_buscar_memoria: busca en Flash Memory por similitud
    4. rankear_resultados: ordena y filtra los resultados
    5. generar_respuesta: usa LLM para sintetizar los resultados

    Entrada esperada en estado.entrada:
      - "query": str — consulta del usuario
      - "limite": int (opcional) — máximo de resultados (default: 5)

    Salida en estado.salida:
      - "respuesta": str — respuesta sintetizada con los resultados
      - "resultados": list[dict] — resultados crudos de la búsqueda
      - "total_encontrados": int — cantidad de resultados
    """
    catalogo = CatalogoNodos(
        ollama_provider=ollama_provider,
        flash_memory=flash_memory,
    )

    @nodo(id="preparar_busqueda", timeout=5.0)
    async def preparar_busqueda(estado: EstadoGrafo) -> EstadoGrafo:
        """Normaliza la query y prepara los parámetros de búsqueda."""
        query = estado.entrada.get("query", "")
        limite = estado.entrada.get("limite", 5)

        estado.contexto["query_original"] = query
        # Para nodo_embeddings
        estado.entrada["texto"] = query
        # Para nodo_buscar_memoria
        estado.contexto["limite_busqueda"] = limite
        return estado

    @nodo(id="preparar_consulta_memoria", timeout=5.0)
    async def preparar_consulta_memoria(estado: EstadoGrafo) -> EstadoGrafo:
        """Transfiere parámetros del embedding a la búsqueda en memoria."""
        estado.entrada["query"] = estado.contexto.get("query_original", "")
        estado.entrada["limite"] = estado.contexto.get("limite_busqueda", 5)
        return estado

    @nodo(id="rankear_resultados", timeout=5.0)
    async def rankear_resultados(estado: EstadoGrafo) -> EstadoGrafo:
        """Ordena y filtra los resultados por score de relevancia."""
        resultados = estado.salida.get("resultados", [])

        # Filtrar resultados con score >= 0.5 y ordenar descendente
        resultados_filtrados = sorted(
            [r for r in resultados if r.get("score", 0) >= 0.5],
            key=lambda r: r.get("score", 0),
            reverse=True
        )

        estado.salida["resultados"] = resultados_filtrados
        estado.salida["total_encontrados"] = len(resultados_filtrados)

        # Preparar contexto para la respuesta final
        if resultados_filtrados:
            contexto_resultados = "\n".join([
                f"- {r.get('contenido', '')}" for r in resultados_filtrados[:3]
            ])
            estado.entrada["mensaje"] = (
                f"Basándote en estos resultados encontrados:\n{contexto_resultados}\n\n"
                f"Responde a la pregunta: {estado.contexto.get('query_original', '')}"
            )
            estado.entrada["sistema"] = "Sintetiza la información encontrada de forma clara y concisa."
        else:
            estado.entrada["mensaje"] = (
                f"No encontré información relevante sobre: "
                f"{estado.contexto.get('query_original', '')}"
            )
            estado.entrada["sistema"] = "Indica amablemente que no se encontró información relevante."

        return estado

    nodo_embeddings = catalogo.obtener("nodo_embeddings")
    nodo_buscar = catalogo.obtener("nodo_buscar_memoria")
    nodo_chat = catalogo.obtener("nodo_chat")

    grafo = (
        YeyoGrafo(
            "grafo_busqueda_semantica",
            "Búsqueda semántica: embedding → buscar en memoria → rankear → responder"
        )
        .agregar_nodo(preparar_busqueda)
        .agregar_nodo(nodo_embeddings)
        .agregar_nodo(preparar_consulta_memoria)
        .agregar_nodo(nodo_buscar)
        .agregar_nodo(rankear_resultados)
        .agregar_nodo(nodo_chat)
        .inicio("preparar_busqueda")
        .edge("preparar_busqueda", "nodo_embeddings")
        .edge("nodo_embeddings", "preparar_consulta_memoria")
        .edge("preparar_consulta_memoria", "nodo_buscar_memoria")
        .edge("nodo_buscar_memoria", "rankear_resultados")
        .edge("rankear_resultados", "nodo_chat")
        .fin("nodo_chat")
    )

    return grafo
