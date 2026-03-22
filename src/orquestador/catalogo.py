"""
YeyoOS — CatalogoNodos
Micro-fase 4.20 — Capa 4: Sistema Nervioso

Registro de nodos base disponibles para construir grafos.
La IA solo puede usar nodos del catálogo registrado.
"""

from typing import Optional, Any
from .estado import EstadoGrafo
from .nodo import Nodo, NodoFuncion, nodo


class CatalogoError(Exception):
    """Error en el CatalogoNodos."""
    pass


class CatalogoNodos:
    """
    Registro central de nodos disponibles para construir grafos.

    Los nodos base incluidos por defecto cubren las operaciones más comunes:
    - nodo_chat: conversación con LLM via OllamaProvider
    - nodo_embeddings: genera embeddings de texto
    - nodo_guardar_memoria: guarda datos en Flash Memory
    - nodo_buscar_memoria: busca en Flash Memory
    - nodo_log: registra un mensaje en los logs del sistema

    Se pueden registrar nodos adicionales con registrar().
    """

    def __init__(
        self,
        ollama_provider: Optional[Any] = None,
        flash_memory: Optional[Any] = None,
    ):
        self._ollama = ollama_provider
        self._flash_memory = flash_memory
        self._nodos: dict[str, Nodo] = {}
        self._registrar_nodos_base()

    def _registrar_nodos_base(self) -> None:
        """Registra los 5 nodos base en el catálogo."""
        self.registrar(self._crear_nodo_chat())
        self.registrar(self._crear_nodo_embeddings())
        self.registrar(self._crear_nodo_guardar_memoria())
        self.registrar(self._crear_nodo_buscar_memoria())
        self.registrar(self._crear_nodo_log())

    # ─── Registro ─────────────────────────────────────────────────────────────

    def registrar(self, nodo_or_id, nodo_obj: Optional[Nodo] = None) -> "CatalogoNodos":
        """Registra un nodo en el catálogo. Acepta (nodo) o (id, nodo)."""
        if nodo_obj is not None:
            # Called as registrar(id, nodo)
            self._nodos[nodo_or_id] = nodo_obj
        else:
            # Called as registrar(nodo)
            self._nodos[nodo_or_id.id] = nodo_or_id
        return self

    def obtener(self, nodo_id: str) -> Nodo:
        """Obtiene un nodo por ID. Lanza CatalogoError si no existe."""
        if nodo_id not in self._nodos:
            raise CatalogoError(
                f"Nodo '{nodo_id}' no encontrado en el catálogo. "
                f"Disponibles: {list(self._nodos.keys())}"
            )
        return self._nodos[nodo_id]

    def listar(self) -> list[str]:
        """Lista los IDs de todos los nodos registrados."""
        return list(self._nodos.keys())

    def existe(self, nodo_id: str) -> bool:
        """Retorna True si el nodo existe en el catálogo."""
        return nodo_id in self._nodos

    def describir(self) -> dict[str, str]:
        """Retorna dict {nodo_id: descripcion} para todos los nodos."""
        return {
            nodo_id: getattr(n, "descripcion", n.id)
            for nodo_id, n in self._nodos.items()
        }

    # ─── Nodos base ───────────────────────────────────────────────────────────

    def _crear_nodo_chat(self) -> Nodo:
        """
        nodo_chat: Conversación con LLM via OllamaProvider.

        Entrada esperada en estado.entrada:
          - "mensaje": str — el mensaje del usuario
          - "sistema": str (opcional) — prompt del sistema
          - "historial": list (opcional) — historial de mensajes previos

        Escribe en estado.salida:
          - "respuesta": str — la respuesta del LLM
        """
        ollama = self._ollama

        async def fn(estado: EstadoGrafo) -> EstadoGrafo:
            mensaje = estado.entrada.get("mensaje", "")
            sistema = estado.entrada.get("sistema", "")
            historial = estado.entrada.get("historial", [])

            messages = []
            if sistema:
                messages.append({"role": "system", "content": sistema})
            messages.extend(historial)
            messages.append({"role": "user", "content": mensaje})

            if ollama is None:
                estado.salida["respuesta"] = f"[mock] Respuesta a: {mensaje}"
                return estado

            respuesta = await ollama.chat(messages=messages)
            if hasattr(respuesta, "content"):
                estado.salida["respuesta"] = respuesta.content
            elif isinstance(respuesta, dict):
                estado.salida["respuesta"] = respuesta.get("content", str(respuesta))
            else:
                estado.salida["respuesta"] = str(respuesta)
            return estado

        n = NodoFuncion(id="nodo_chat", fn=fn, timeout=60.0, nombre_display="Chat LLM")
        n.descripcion = "Conversación con LLM via OllamaProvider"
        return n

    def _crear_nodo_embeddings(self) -> Nodo:
        """
        nodo_embeddings: Genera embeddings de texto.

        Entrada esperada en estado.entrada:
          - "texto": str — el texto a embeder

        Escribe en estado.salida:
          - "embedding": list[float] — vector de embeddings
          - "embedding_dim": int — dimensión del vector
        """
        ollama = self._ollama

        async def fn(estado: EstadoGrafo) -> EstadoGrafo:
            texto = estado.entrada.get("texto", "")

            if ollama is None:
                # Mock: embedding de dimensión 4 para tests
                estado.salida["embedding"] = [0.1, 0.2, 0.3, 0.4]
                estado.salida["embedding_dim"] = 4
                return estado

            embedding = await ollama.embeddings(texto)
            estado.salida["embedding"] = embedding
            estado.salida["embedding_dim"] = len(embedding)
            return estado

        n = NodoFuncion(id="nodo_embeddings", fn=fn, timeout=30.0, nombre_display="Embeddings")
        n.descripcion = "Genera embeddings de texto via OllamaProvider"
        return n

    def _crear_nodo_guardar_memoria(self) -> Nodo:
        """
        nodo_guardar_memoria: Guarda datos en Flash Memory.

        Entrada esperada en estado.entrada:
          - "dato": str — el dato a guardar
          - "tipo": str (opcional) — tipo de memoria (default: "general")
          - "importancia": float (opcional) — importancia 0.0-1.0 (default: 0.5)

        Escribe en estado.salida:
          - "memoria_id": str — ID de la memoria guardada
        También registra en estado.memoria_ids
        """
        flash_memory = self._flash_memory

        async def fn(estado: EstadoGrafo) -> EstadoGrafo:
            dato = estado.entrada.get("dato", "")
            tipo = estado.entrada.get("tipo", "general")
            importancia = estado.entrada.get("importancia", 0.5)

            if flash_memory is None:
                memoria_id = f"mock-mem-{hash(dato) % 10000:04d}"
                estado.salida["memoria_id"] = memoria_id
                estado.registrar_memoria(memoria_id)
                return estado

            memoria_id = await flash_memory.guardar(
                dato=dato,
                metadata={"tipo": tipo, "importancia": importancia}
            )
            estado.salida["memoria_id"] = memoria_id
            estado.registrar_memoria(memoria_id)
            return estado

        n = NodoFuncion(id="nodo_guardar_memoria", fn=fn, timeout=15.0, nombre_display="Guardar Memoria")
        n.descripcion = "Guarda datos en Flash Memory"
        return n

    def _crear_nodo_buscar_memoria(self) -> Nodo:
        """
        nodo_buscar_memoria: Busca en Flash Memory.

        Entrada esperada en estado.entrada:
          - "query": str — consulta de búsqueda
          - "tipo": str (opcional) — filtrar por tipo
          - "limite": int (opcional) — máximo de resultados (default: 5)

        Escribe en estado.salida:
          - "resultados": list[dict] — resultados de la búsqueda
          - "total_encontrados": int — cantidad de resultados
        """
        flash_memory = self._flash_memory

        async def fn(estado: EstadoGrafo) -> EstadoGrafo:
            query = estado.entrada.get("query", "")
            tipo = estado.entrada.get("tipo")
            limite = estado.entrada.get("limite", 5)

            if flash_memory is None:
                estado.salida["resultados"] = [
                    {"id": "mock-1", "contenido": f"Resultado mock para: {query}", "score": 0.9}
                ]
                estado.salida["total_encontrados"] = 1
                return estado

            resultados = await flash_memory.buscar(
                query=query,
                tipo=tipo,
                limite=limite
            )
            estado.salida["resultados"] = resultados
            estado.salida["total_encontrados"] = len(resultados)
            return estado

        n = NodoFuncion(id="nodo_buscar_memoria", fn=fn, timeout=15.0, nombre_display="Buscar Memoria")
        n.descripcion = "Busca en Flash Memory por relevancia semántica"
        return n

    def _crear_nodo_log(self) -> Nodo:
        """
        nodo_log: Registra un mensaje en los logs.

        Entrada esperada en estado.entrada:
          - "mensaje_log": str — el mensaje a registrar
          - "nivel": str (opcional) — "debug"|"info"|"warning"|"error" (default: "info")

        Escribe en estado.salida:
          - "log_registrado": bool — True si se registró
        """
        import logging
        logger = logging.getLogger("yeyo.orquestador.nodo_log")

        async def fn(estado: EstadoGrafo) -> EstadoGrafo:
            mensaje = estado.entrada.get("mensaje_log", "")
            nivel = estado.entrada.get("nivel", "info").lower()

            log_fn = getattr(logger, nivel, logger.info)
            log_fn(f"[nodo_log] {mensaje}")

            estado.salida["log_registrado"] = True
            return estado

        n = NodoFuncion(id="nodo_log", fn=fn, timeout=5.0, nombre_display="Log")
        n.descripcion = "Registra un mensaje en los logs del sistema"
        return n

# ── Hub Nodes (Capa 5) ──────────────────────────────────────────────────
# Los nodos del Hub se registrarán aquí en Capa 5:
# catalogo.registrar("hub.imagen.generar", ...)
# catalogo.registrar("hub.video.componer", ...)
# catalogo.registrar("hub.codigo.ejecutar", ...)
# Esto permite grafos que coordinan múltiples nodos del Hub (GrafoMultiNodo)
