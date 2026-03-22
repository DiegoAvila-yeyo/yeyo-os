"""
YeyoOS — GrafoMultiNodo: Hacer Reel
Micro-fase 4.21 — Capa 4: Sistema Nervioso

Flujo: generar guión → imágenes paralelas (3 ó 5) → componer video → guardar
Demuestra coordinación entre múltiples Hub Nodes (GrafoMultiNodo).
"""

from typing import Optional, Any
from ..estado import EstadoGrafo
from ..nodo import nodo, NodoFuncion
from ..grafo import YeyoGrafo
from ..paralelo import NodoParalelo
from ..edge import FIN_GRAFO
from ..catalogo import CatalogoNodos


def _crear_mock_imagen(idx: int):
    """Nodo imagen mock para usar cuando hub.imagen.generar no está disponible."""
    async def fn(estado: EstadoGrafo) -> EstadoGrafo:
        imagenes = estado.salida.get("imagenes", [])
        imagenes.append(f"imagen_mock_{idx}.png")
        estado.salida["imagenes"] = imagenes
        return estado
    n = NodoFuncion(id=f"mock_imagen_{idx}", fn=fn, timeout=10.0,
                    nombre_display=f"Mock Imagen {idx}")
    n.descripcion = f"Genera imagen mock #{idx} (hub.imagen.generar no disponible)"
    return n


def crear_grafo_hacer_reel(
    ollama_provider: Optional[Any] = None,
    hub_imagen: Optional[Any] = None,
    hub_video: Optional[Any] = None,
    flash_memory: Optional[Any] = None,
) -> YeyoGrafo:
    """
    Factory: crea y retorna el GrafoMultiNodo para hacer un reel.

    Flujo de nodos:
    1. generar_guion: llama a nodo_chat para crear guión con escenas
    2a. generar_imagenes_x5: NodoParalelo con 5 instancias (si guión > 5 escenas)
    2b. generar_imagenes_x3: NodoParalelo con 3 instancias (si guión ≤ 5 escenas)
    3. componer_video: llama a hub.video.componer con las imágenes generadas
    4. guardar: llama a nodo_guardar_memoria para persistir el resultado

    Entrada esperada en estado.entrada:
      - "tema": str — tema o descripción del reel
      - "usuario_id": str (opcional) — ID del usuario

    Salida en estado.salida:
      - "guion": str — guión generado
      - "imagenes": list[str] — rutas de imágenes generadas
      - "video_path": str — ruta del video compuesto
    """
    catalogo = CatalogoNodos(
        ollama_provider=ollama_provider,
        flash_memory=flash_memory,
    )

    if hub_imagen is not None:
        catalogo.registrar("hub.imagen.generar", hub_imagen)
    if hub_video is not None:
        catalogo.registrar("hub.video.componer", hub_video)

    @nodo(id="generar_guion")
    async def generar_guion(estado: EstadoGrafo) -> EstadoGrafo:
        tema = estado.entrada.get("tema", "reel genérico")
        if ollama_provider is None:
            estado.salida["guion"] = "ESCENA 1: Intro\nESCENA 2: Desarrollo\nESCENA 3: Cierre"
            estado.salida["num_escenas"] = 3
            return estado
        respuesta = await ollama_provider.chat(
            f"Crea un guión corto para un reel sobre: {tema}. Numera cada escena como ESCENA N:"
        )
        guion = respuesta.content
        estado.salida["guion"] = guion
        estado.salida["num_escenas"] = guion.count("ESCENA")
        return estado

    def _rama_imagenes(estado: EstadoGrafo) -> str:
        return "muchas" if estado.salida.get("num_escenas", 0) > 5 else "pocas"

    nodo_imagen = catalogo.obtener("hub.imagen.generar") if hub_imagen else None

    def _combinar_imagenes(resultados):
        imagenes = []
        for r in resultados:
            imagenes.extend(r.salida.get("imagenes", []))
        return {"imagenes": imagenes}

    imagenes_x5 = NodoParalelo(
        id="generar_imagenes_x5",
        nodos=[nodo_imagen or _crear_mock_imagen(i) for i in range(5)],
        combinar=_combinar_imagenes,
    )
    imagenes_x3 = NodoParalelo(
        id="generar_imagenes_x3",
        nodos=[nodo_imagen or _crear_mock_imagen(i) for i in range(3)],
        combinar=_combinar_imagenes,
    )

    @nodo(id="componer_video")
    async def componer_video(estado: EstadoGrafo) -> EstadoGrafo:
        imagenes = estado.salida.get("imagenes", [])
        if hub_video is not None:
            resultado = await hub_video.ejecutar(estado)
            estado.salida["video_path"] = resultado.salida.get("video_path", "reel.mp4")
        else:
            estado.salida["video_path"] = f"reel_{len(imagenes)}_frames_mock.mp4"
        return estado

    nodo_guardar = catalogo.obtener("nodo_guardar_memoria")

    grafo = (
        YeyoGrafo("grafo_hacer_reel",
                  "GrafoMultiNodo: guión → imágenes paralelas → video → guardado")
        .agregar_nodo(generar_guion)
        .agregar_nodo(imagenes_x5)
        .agregar_nodo(imagenes_x3)
        .agregar_nodo(componer_video)
        .agregar_nodo(nodo_guardar)
        .inicio("generar_guion")
        .edge_condicional("generar_guion", _rama_imagenes_mapped)
        .edge("generar_imagenes_x5", "componer_video")
        .edge("generar_imagenes_x3", "componer_video")
        .edge("componer_video", "nodo_guardar_memoria")
        .fin("nodo_guardar_memoria")
    )
    return grafo


def _rama_imagenes_mapped(estado: EstadoGrafo) -> str:
    """Maps rama result to actual node IDs."""
    return "generar_imagenes_x5" if estado.salida.get("num_escenas", 0) > 5 else "generar_imagenes_x3"
