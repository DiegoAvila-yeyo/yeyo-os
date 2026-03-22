"""
YeyoOS — YeyoOrquestador
Micro-fase 4.19 — Capa 4: Sistema Nervioso

Conecta YeyoGrafo con Ollama tool calling.
Ollama analiza el mensaje y decide qué grafo ejecutar.
"""

import json
from typing import Optional, Any

from .estado import EstadoGrafo
from .grafo import YeyoGrafo, ResultadoGrafo


class OrquestadorError(Exception):
    """Error en el YeyoOrquestador."""
    pass


class RespuestaOrquestador:
    """Respuesta del YeyoOrquestador al procesar un mensaje."""

    def __init__(
        self,
        texto: str,
        grafo_ejecutado: Optional[str] = None,
        resultado_grafo: Optional[ResultadoGrafo] = None,
        exito: bool = True,
    ):
        self.texto = texto
        self.grafo_ejecutado = grafo_ejecutado
        self.resultado_grafo = resultado_grafo
        self.exito = exito

    def __repr__(self) -> str:
        return (
            f"RespuestaOrquestador("
            f"grafo={self.grafo_ejecutado!r}, "
            f"exito={self.exito}, "
            f"texto={self.texto[:50]!r})"
        )


class YeyoOrquestador:
    """
    Orquestador central de YeyoOS.

    Registra grafos como tools de Ollama.
    Cuando el usuario envía un mensaje, Ollama decide qué grafo ejecutar.
    Si no hay tool_call, retorna la respuesta textual de Ollama directamente.
    """

    def __init__(self, ollama_provider: Any, modelo: str = "llama3.2"):
        """
        Args:
            ollama_provider: instancia de OllamaProvider (o mock)
            modelo: nombre del modelo Ollama a usar
        """
        self._ollama = ollama_provider
        self.modelo = modelo
        self._grafos: dict[str, YeyoGrafo] = {}
        self._tools: dict[str, dict] = {}  # {grafo_id: tool_definition}

    # ─── Registro de grafos ───────────────────────────────────────────────────

    def registrar_grafo(self, grafo: YeyoGrafo) -> "YeyoOrquestador":
        """Registra un grafo para ejecución directa (sin tool calling)."""
        self._grafos[grafo.id] = grafo
        return self

    def registrar_grafo_como_tool(self, grafo: YeyoGrafo) -> "YeyoOrquestador":
        """
        Registra un grafo como tool de Ollama.
        Ollama podrá invocar este grafo automáticamente.
        """
        self.registrar_grafo(grafo)
        tool_def = self._grafo_a_tool(grafo)
        self._tools[grafo.id] = tool_def
        return self

    def _grafo_a_tool(self, grafo: YeyoGrafo) -> dict:
        """Convierte un YeyoGrafo en la definición de tool para Ollama."""
        return {
            "type": "function",
            "function": {
                "name": grafo.id,
                "description": grafo.descripcion or f"Ejecutar el grafo {grafo.id}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entrada": {
                            "type": "string",
                            "description": "Instrucción o dato de entrada para el grafo"
                        }
                    },
                    "required": ["entrada"],
                },
            },
        }

    def listar_grafos(self) -> list[str]:
        """Lista los IDs de todos los grafos registrados."""
        return list(self._grafos.keys())

    def listar_tools(self) -> list[str]:
        """Lista los IDs de grafos registrados como tools."""
        return list(self._tools.keys())

    # ─── Procesamiento ────────────────────────────────────────────────────────

    async def procesar(
        self,
        mensaje: str,
        contexto: Optional[dict] = None,
        on_evento: Optional[Any] = None,
    ) -> RespuestaOrquestador:
        """
        Procesa un mensaje:
        1. Llama a Ollama con los tools registrados
        2. Si Ollama retorna tool_call → ejecuta el grafo correspondiente
        3. Si no hay tool_call → retorna la respuesta textual
        """
        contexto = contexto or {}

        messages = self._construir_messages(mensaje, contexto)
        tools = list(self._tools.values()) if self._tools else None

        try:
            respuesta_ollama = await self._llamar_ollama(messages, tools)
        except Exception as e:
            raise OrquestadorError(f"Error al llamar a Ollama: {e}") from e

        # Verificar si hay tool_call
        tool_call = self._extraer_tool_call(respuesta_ollama)

        if tool_call:
            return await self._ejecutar_tool_call(tool_call, contexto, on_evento)

        # Sin tool_call: retornar respuesta textual
        texto = self._extraer_texto(respuesta_ollama)
        return RespuestaOrquestador(
            texto=texto,
            grafo_ejecutado=None,
            resultado_grafo=None,
            exito=True,
        )

    async def ejecutar_grafo_directo(
        self,
        grafo_id: str,
        entrada: dict,
        on_evento: Optional[Any] = None,
    ) -> ResultadoGrafo:
        """Ejecuta un grafo directamente por ID, sin pasar por Ollama."""
        if grafo_id not in self._grafos:
            raise OrquestadorError(f"Grafo '{grafo_id}' no registrado")
        grafo = self._grafos[grafo_id]
        return await grafo.ejecutar(entrada, on_evento=on_evento)

    # ─── Helpers privados ─────────────────────────────────────────────────────

    def _construir_messages(self, mensaje: str, contexto: dict) -> list[dict]:
        """Construye la lista de messages para Ollama."""
        messages = []

        # System prompt con contexto
        system_content = "Eres YeyoOS, un asistente AI nativo. Usa los tools disponibles cuando sea apropiado."
        if contexto.get("sistema"):
            system_content = contexto["sistema"]
        messages.append({"role": "system", "content": system_content})

        # Historial si existe
        if "historial" in contexto:
            messages.extend(contexto["historial"])

        # Mensaje del usuario
        messages.append({"role": "user", "content": mensaje})

        return messages

    async def _llamar_ollama(self, messages: list[dict], tools: Optional[list]) -> Any:
        """Llama al OllamaProvider con messages y tools opcionales."""
        kwargs: dict = {"messages": messages}
        if tools:
            kwargs["tools"] = tools
        return await self._ollama.chat(**kwargs)

    def _extraer_tool_call(self, respuesta: Any) -> Optional[dict]:
        """
        Extrae el tool_call de la respuesta de Ollama.
        Formato esperado: respuesta con .tool_calls o dict con "tool_calls"
        """
        # Soportar objeto con atributo tool_calls
        if hasattr(respuesta, "tool_calls") and respuesta.tool_calls:
            tc = respuesta.tool_calls[0]
            if hasattr(tc, "function"):
                return {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or {},
                }

        # Soportar dict
        if isinstance(respuesta, dict):
            tool_calls = respuesta.get("tool_calls") or []
            if tool_calls:
                tc = tool_calls[0]
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"entrada": args}
                return {"name": fn.get("name", ""), "arguments": args}

        return None

    def _extraer_texto(self, respuesta: Any) -> str:
        """Extrae el texto de la respuesta de Ollama."""
        if hasattr(respuesta, "content"):
            return str(respuesta.content)
        if hasattr(respuesta, "message") and hasattr(respuesta.message, "content"):
            return str(respuesta.message.content)
        if isinstance(respuesta, dict):
            return str(respuesta.get("content") or respuesta.get("message", {}).get("content", ""))
        return str(respuesta)

    async def _ejecutar_tool_call(
        self,
        tool_call: dict,
        contexto: dict,
        on_evento: Optional[Any],
    ) -> RespuestaOrquestador:
        """Ejecuta el grafo correspondiente al tool_call de Ollama."""
        grafo_id = tool_call["name"]
        args = tool_call.get("arguments", {})

        if grafo_id not in self._grafos:
            return RespuestaOrquestador(
                texto=f"Error: grafo '{grafo_id}' no encontrado",
                grafo_ejecutado=grafo_id,
                exito=False,
            )

        entrada = {
            "mensaje": args.get("entrada", ""),
            "contexto_usuario": contexto,
            **args,
        }

        grafo = self._grafos[grafo_id]
        resultado = await grafo.ejecutar(entrada, on_evento=on_evento)

        texto_respuesta = resultado.estado_final.salida.get(
            "respuesta",
            resultado.estado_final.salida.get(
                "texto",
                f"Grafo '{grafo_id}' completado"
            )
        )

        return RespuestaOrquestador(
            texto=str(texto_respuesta),
            grafo_ejecutado=grafo_id,
            resultado_grafo=resultado,
            exito=resultado.exito,
        )
