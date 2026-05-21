"""
YeyoOS — NamespaceClassifier
Fase 2 — Arquitectura de Memoria por Namespace

Clasifica mensajes en el namespace correcto para que
las memorias se guarden donde corresponde por nodo y tipo.

Corre en background (async) — no bloquea el flujo del chat.
Degradación graceful: falla silenciosa con default 'chat:usuario'.
"""

import logging
from typing import Optional

from src.ia.interfaces import IAProvider, IAMessage

logger = logging.getLogger("yeyoos.memory.classifier")

VALID_NAMESPACES = {
    "chat:usuario",
    "imagen:usuario",
    "imagen:conocimiento",
    "codigo:usuario",
    "codigo:conocimiento",
    "video:usuario",
    "video:conocimiento",
    "video:acciones_humanas",
    "automatizacion:usuario",
    "automatizacion:conocimiento",
    "herramienta:usuario",
    "herramienta:resultado",
    "sistema:docs",
    "sistema:prompts",
    "descartado",
}

DEFAULT_NAMESPACE = "chat:usuario"

CLASSIFICATION_PROMPT = """Clasifica el siguiente texto en exactamente uno de estos namespaces.
Responde SOLO con el namespace, sin explicación, sin comillas, sin puntuación extra.

Namespaces disponibles:
- chat:usuario → nombre, edad, familia, hobbies, preferencias personales generales
- imagen:usuario → estilos visuales preferidos, prompts de imagen favoritos del usuario
- imagen:conocimiento → técnicas de prompt, vocabulario técnico (bokeh, HDR), composición
- codigo:usuario → lenguajes preferidos del usuario, proyectos, stack personal
- codigo:conocimiento → patrones SOLID, snippets reutilizables, buenas prácticas
- video:usuario → estilo de edición del usuario, plataformas, temas de contenido
- video:conocimiento → técnicas narrativas, formatos por plataforma, transiciones
- video:acciones_humanas → movimientos corporales, poses, gestos, acciones físicas (caminar, saltar, bailar)
- automatizacion:usuario → flujos y servicios del usuario, APIs que usa
- automatizacion:conocimiento → patrones de automatización, webhooks, retry patterns
- herramienta:usuario → herramientas preferidas del usuario, APIs, configs de tool calls
- herramienta:resultado → resultados de ejecución de herramientas externas, output de bash/web_search
- descartado → saludos, confirmaciones, ruido ("ok", "gracias", "sí", "no", "hola")

Texto: {content}

Namespace:"""


class NamespaceClassifier:
    """
    Clasifica contenido en el namespace correcto usando IA.
    Diseñado para correr en background — nunca bloquea ni crashea.
    """

    def __init__(self, ia_provider: IAProvider, timeout: float = 10.0):
        self.ia = ia_provider
        self.timeout = timeout

    async def classify(self, content: str) -> str:
        """
        Retorna el namespace correcto para este contenido.
        Siempre retorna un namespace válido — nunca lanza excepciones.
        """
        if not content or not content.strip():
            return "descartado"

        # Ruido puro: menos de 3 palabras
        words = content.strip().split()
        if len(words) <= 2:
            return "descartado"

        try:
            messages = [
                IAMessage(
                    role="system",
                    content="Eres un clasificador. Respondes SOLO con el namespace exacto, sin nada más.",
                ),
                IAMessage(
                    role="user",
                    content=CLASSIFICATION_PROMPT.format(content=content[:500]),
                ),
            ]
            response = await self.ia.chat(messages, temperature=0.0)
            namespace = response.content.strip().lower().replace('"', '').replace("'", '')

            if namespace in VALID_NAMESPACES:
                logger.debug(f"Clasificado '{content[:50]}' → {namespace}")
                return namespace

            logger.warning(f"Namespace inválido '{namespace}', usando default")
            return DEFAULT_NAMESPACE

        except Exception as e:
            logger.warning(f"Clasificador falló ({e}), usando default")
            return DEFAULT_NAMESPACE

    async def classify_batch(self, contents: list[str]) -> list[str]:
        """Clasifica múltiples contenidos. Cada uno independiente."""
        results = []
        for content in contents:
            ns = await self.classify(content)
            results.append(ns)
        return results
