"""
YeyoOS — GeneradorGrafos
Micro-fase 5.24 — Capa 5: Órganos

Permite a la IA generar YeyoGrafos desde descripción de lenguaje natural.
Los grafos generados solo pueden usar nodos del catálogo registrado.
Se ejecutan siempre en sandbox (nivel de privilegio L5).
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional, Any

from .estado import EstadoGrafo
from .grafo import YeyoGrafo
from .catalogo import CatalogoNodos


TIPO_GRAFO_GENERADO = "grafo_generado"
IMPORTANCIA_GRAFO_GENERADO = 0.9

PROMPT_GENERADOR = """Eres un experto en YeyoOS, un OS AI-nativo.
Tu tarea es generar código Python para un YeyoGrafo basándote en la descripción del usuario.

NODOS DISPONIBLES EN EL CATÁLOGO (solo puedes usar estos):
{nodos_disponibles}

FORMATO DEL GRAFO (OBLIGATORIO):
```python
from src.orquestador import YeyoGrafo
from src.orquestador.nodo import NodoFuncion

async def fn_paso1(estado):
    estado.salida["resultado"] = "valor"
    return estado

nodo_paso1 = NodoFuncion(id="paso1", fn=fn_paso1, timeout=30.0)

grafo = (
    YeyoGrafo("nombre_del_grafo", "descripción del grafo")
    .agregar_nodo(nodo_paso1)
    .inicio("paso1")
    .fin("paso1")
)
```

RESTRICCIONES ABSOLUTAS:
- Solo usar NodoFuncion para nodos personalizados
- NO usar imports excepto los ya disponibles
- NO usar eval, exec, __import__, os.system, subprocess
- NO usar bucles infinitos ni recursión
- La variable final debe llamarse exactamente: grafo

DESCRIPCIÓN DEL USUARIO: {descripcion}

Responde SOLO con el código Python del grafo, sin explicaciones adicionales."""


class GeneradorGrafosError(Exception):
    """Error en el GeneradorGrafos."""
    pass


class GeneradorGrafos:
    """
    Genera YeyoGrafos desde descripción de lenguaje natural usando Ollama.
    """

    def __init__(
        self,
        ollama_provider: Any,
        flash_memory: Optional[Any] = None,
        catalogo: Optional[CatalogoNodos] = None,
    ):
        self._ollama = ollama_provider
        self._flash = flash_memory
        self.catalogo = catalogo or CatalogoNodos(
            ollama_provider=ollama_provider,
            flash_memory=flash_memory,
        )
        self.grafos_generados: list[dict] = []

    async def generar(
        self,
        descripcion: str,
        usuario_id: str = "anonimo",
        nombre_sugerido: Optional[str] = None,
    ) -> YeyoGrafo:
        if not descripcion.strip():
            raise GeneradorGrafosError("La descripción no puede estar vacía")

        codigo_generado = await self._llamar_ollama(descripcion)
        codigo_limpio = self._extraer_codigo(codigo_generado)

        # Use AST validation if validador available, otherwise basic
        self._validar_codigo(codigo_limpio)

        grafo = self._ejecutar_en_sandbox(codigo_limpio)

        if not isinstance(grafo, YeyoGrafo):
            raise GeneradorGrafosError(
                f"El código generado no produjo un YeyoGrafo válido. "
                f"Tipo obtenido: {type(grafo).__name__}"
            )

        grafo_id = grafo.id
        await self._guardar_en_flash(descripcion, codigo_limpio, grafo_id, usuario_id)

        self.grafos_generados.append({
            "id": grafo_id,
            "descripcion": descripcion,
            "usuario_id": usuario_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return grafo

    async def listar_generados(self, usuario_id: str = "anonimo") -> list[dict]:
        if not self._flash:
            return [g for g in self.grafos_generados if g.get("usuario_id") == usuario_id]

        try:
            resultados = await self._flash.buscar(
                query=f"usuario_id:{usuario_id}",
                tipo=TIPO_GRAFO_GENERADO,
                limite=50,
            )
            grafos = []
            for r in resultados:
                try:
                    contenido = r.get("contenido", "")
                    if isinstance(contenido, str):
                        data = json.loads(contenido)
                    elif isinstance(contenido, dict):
                        data = contenido
                    else:
                        continue
                    if data.get("usuario_id") == usuario_id:
                        grafos.append(data)
                except Exception:
                    continue
            return grafos
        except Exception:
            return []

    async def _llamar_ollama(self, descripcion: str) -> str:
        nodos_disponibles = "\n".join([
            f"- {nodo_id}: {desc}"
            for nodo_id, desc in self.catalogo.describir().items()
        ])

        prompt = PROMPT_GENERADOR.format(
            nodos_disponibles=nodos_disponibles,
            descripcion=descripcion,
        )

        try:
            respuesta = await self._ollama.chat(messages=[
                {"role": "user", "content": prompt}
            ])
            if hasattr(respuesta, "content"):
                return respuesta.content
            elif isinstance(respuesta, dict):
                return respuesta.get("content", "")
            return str(respuesta)
        except Exception as e:
            raise GeneradorGrafosError(f"Error al llamar a Ollama: {e}") from e

    def _extraer_codigo(self, texto: str) -> str:
        patron = r"```python\s*(.*?)\s*```"
        match = re.search(patron, texto, re.DOTALL)
        if match:
            return match.group(1).strip()

        patron2 = r"```\s*(.*?)\s*```"
        match2 = re.search(patron2, texto, re.DOTALL)
        if match2:
            return match2.group(1).strip()

        return texto.strip()

    def _validar_codigo(self, codigo: str) -> None:
        """
        Validation: uses GrafoValidador (AST) if available, falls back to basic string checks.
        """
        try:
            from .validador import GrafoValidador
            nodos_permitidos = self.catalogo.listar()
            validador = GrafoValidador(nodos_permitidos=nodos_permitidos)
            resultado = validador.validar(codigo)
            if not resultado.is_valid:
                errores_str = "; ".join(resultado.errores)
                raise GeneradorGrafosError(
                    f"Código inválido ({len(resultado.errores)} errores): {errores_str}"
                )
        except ImportError:
            self._validar_codigo_basico(codigo)

    def _validar_codigo_basico(self, codigo: str) -> None:
        imports_peligrosos = [
            "import os", "import sys", "import subprocess",
            "import shutil", "import socket", "import requests",
            "__import__", "importlib",
        ]
        patrones_peligrosos = [
            r"\beval\s*\(", r"\bexec\s*\(", r"\bcompile\s*\(",
            r"os\.system", r"os\.popen", r"subprocess\.",
            r"__import__\s*\(",
        ]

        for imp_peligroso in imports_peligrosos:
            if imp_peligroso in codigo:
                raise GeneradorGrafosError(
                    f"Código peligroso detectado: '{imp_peligroso}' no está permitido"
                )

        for patron in patrones_peligrosos:
            if re.search(patron, codigo):
                raise GeneradorGrafosError(
                    f"Patrón peligroso detectado: '{patron}'"
                )

        if "grafo" not in codigo:
            raise GeneradorGrafosError(
                "El código debe definir una variable llamada 'grafo'"
            )

    def _ejecutar_en_sandbox(self, codigo: str) -> YeyoGrafo:
        from .nodo import NodoFuncion, NodoInline
        from .edge import EdgeDirecto, EdgeCondicional

        globals_sandbox = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "None": None,
                "True": True,
                "False": False,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "getattr": getattr,
            },
            "YeyoGrafo": YeyoGrafo,
            "NodoFuncion": NodoFuncion,
            "NodoInline": NodoInline,
            "EdgeDirecto": EdgeDirecto,
            "EdgeCondicional": EdgeCondicional,
            "EstadoGrafo": EstadoGrafo,
            "catalogo": self.catalogo,
        }

        locals_sandbox: dict = {}

        try:
            exec(codigo, globals_sandbox, locals_sandbox)
        except Exception as e:
            raise GeneradorGrafosError(f"Error ejecutando código generado: {e}") from e

        grafo = locals_sandbox.get("grafo") or globals_sandbox.get("grafo")
        if grafo is None:
            raise GeneradorGrafosError(
                "El código no definió la variable 'grafo'"
            )
        return grafo

    async def _guardar_en_flash(
        self,
        descripcion: str,
        codigo: str,
        grafo_id: str,
        usuario_id: str,
    ) -> None:
        if not self._flash:
            return
        try:
            data = {
                "grafo_id": grafo_id,
                "descripcion": descripcion,
                "codigo": codigo,
                "usuario_id": usuario_id,
                "tipo": TIPO_GRAFO_GENERADO,
                "generado_en": datetime.now(timezone.utc).isoformat(),
            }
            await self._flash.guardar(
                dato=json.dumps(data, ensure_ascii=False),
                metadata={
                    "tipo": TIPO_GRAFO_GENERADO,
                    "grafo_id": grafo_id,
                    "usuario_id": usuario_id,
                    "importancia": IMPORTANCIA_GRAFO_GENERADO,
                }
            )
        except Exception:
            pass
