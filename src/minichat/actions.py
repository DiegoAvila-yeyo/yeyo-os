"""
YeyoOS — MiniChat v3 Actions
Micro-fase 5.19 — Capa 5: Órganos

MiniChat v3: detecta intención de acción en el mensaje y la ejecuta
dentro del nodo activo. SIEMPRE con confirmación.
"""

import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    GENERATE_IMAGE = "generate_image"
    TRANSFORM_IMAGE = "transform_image"
    DESCRIBE_IMAGE = "describe_image"
    EXECUTE_CODE = "execute_code"
    EXPLAIN_CODE = "explain_code"
    TRIM_VIDEO = "trim_video"
    TRANSCRIBE_VIDEO = "transcribe_video"
    SEARCH_FILES = "search_files"
    SUMMARIZE_PAGE = "summarize_page"
    NONE = "none"


@dataclass
class DetectedAction:
    """Acción detectada en un mensaje."""
    action_type: ActionType
    confidence: float  # 0.0 a 1.0
    parameters: dict
    requires_confirmation: bool = True
    description: str = ""


ACTION_PATTERNS: dict[str, list[tuple[str, ActionType, str]]] = {
    "image": [
        (r"(?:genera|crea|haz|dibuja)\s+(?:una\s+)?imagen\s+(?:de\s+)?(.+)",
         ActionType.GENERATE_IMAGE, "Generar imagen"),
        (r"(?:transforma|cambia|modifica|aplica)\s+(?:la\s+)?imagen\s+(.+)",
         ActionType.TRANSFORM_IMAGE, "Transformar imagen"),
        (r"(?:describe|qué\s+hay|qué\s+ves|analiza)\s+(?:en\s+)?(?:esta\s+)?(?:la\s+)?imagen",
         ActionType.DESCRIBE_IMAGE, "Describir imagen"),
    ],
    "code": [
        (r"(?:ejecuta|corre|run)\s+(?:este\s+)?(?:el\s+)?código",
         ActionType.EXECUTE_CODE, "Ejecutar código"),
        (r"(?:explica|qué\s+hace)\s+(?:este\s+)?(?:el\s+)?código",
         ActionType.EXPLAIN_CODE, "Explicar código"),
    ],
    "video": [
        (r"(?:recorta|corta|trim)\s+(?:del?\s+)?(?:minuto\s+)?(\d+)\s+(?:al?\s+)?(\d+)",
         ActionType.TRIM_VIDEO, "Recortar video"),
        (r"(?:transcribe|subtítulos|subtitula)\s+(?:este\s+)?(?:el\s+)?video",
         ActionType.TRANSCRIBE_VIDEO, "Transcribir video"),
    ],
    "files": [
        (r"(?:busca|encuentra|find)\s+(.+)",
         ActionType.SEARCH_FILES, "Buscar archivos"),
    ],
    "browser": [
        (r"(?:resume|resumen|summarize)\s+(?:esta\s+)?(?:la\s+)?página",
         ActionType.SUMMARIZE_PAGE, "Resumir página"),
    ],
}


class ActionDetector:
    """Detecta acciones en mensajes del usuario."""

    def detect(self, message: str, node_type: str) -> DetectedAction:
        message_lower = message.lower().strip()

        patterns = ACTION_PATTERNS.get(node_type, [])
        for pattern, action_type, description in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                params = {"groups": list(match.groups())} if match.groups() else {}
                return DetectedAction(
                    action_type=action_type,
                    confidence=0.8,
                    parameters=params,
                    requires_confirmation=True,
                    description=description,
                )

        return DetectedAction(
            action_type=ActionType.NONE,
            confidence=1.0,
            parameters={},
            requires_confirmation=False,
            description="",
        )


class ActionExecutor:
    """Ejecuta acciones detectadas en el nodo activo."""

    def __init__(self):
        self._confirmed_actions: set[str] = set()

    def confirm_action(self, action_id: str) -> None:
        self._confirmed_actions.add(action_id)

    def is_confirmed(self, action_id: str) -> bool:
        return action_id in self._confirmed_actions

    async def execute(
        self, action: DetectedAction, node_type: str, node_id: str,
        action_id: str
    ) -> dict:
        if action.requires_confirmation and not self.is_confirmed(action_id):
            return {
                "requires_confirmation": True,
                "action_id": action_id,
                "action_type": action.action_type.value,
                "description": action.description,
                "message": f"¿Quieres ejecutar: {action.description}?",
            }

        from src.api.routes.nodes import _active_nodes

        if node_id not in _active_nodes:
            return {"error": "Nodo no activo"}

        node = _active_nodes[node_id]
        process_data = self._build_process_data(action, node_type)

        try:
            result = await node.process(process_data)
            return {
                "executed": True,
                "action_type": action.action_type.value,
                "result": result,
            }
        except Exception as e:
            return {"error": f"Error ejecutando acción: {str(e)}"}

    def _build_process_data(self, action: DetectedAction, node_type: str) -> dict:
        params = action.parameters.get("groups", [])

        if action.action_type == ActionType.GENERATE_IMAGE:
            return {"action": "generate", "prompt": params[0] if params else ""}
        elif action.action_type == ActionType.EXECUTE_CODE:
            return {"action": "execute"}
        elif action.action_type == ActionType.TRIM_VIDEO:
            return {
                "action": "process",
                "command": f"recorta del minuto {params[0]} al {params[1]}" if len(params) >= 2 else "",
            }
        elif action.action_type == ActionType.SEARCH_FILES:
            return {"action": "search", "query": params[0] if params else ""}
        elif action.action_type == ActionType.SUMMARIZE_PAGE:
            return {"action": "summarize"}
        elif action.action_type == ActionType.DESCRIBE_IMAGE:
            return {"action": "analyze"}
        elif action.action_type == ActionType.EXPLAIN_CODE:
            return {"action": "explain"}
        elif action.action_type == ActionType.TRANSCRIBE_VIDEO:
            return {"action": "transcribe"}
        else:
            return {}
