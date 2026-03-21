## ═══════════════════════════════════════
## MICRO-FASE 5.19 — MiniChat v3 (Actions)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.19-1 [VSCODE] — MiniChat v3 con ejecución de acciones en nodos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.19 de Capa 5 (Órganos): actualizar MiniChat a v3 con capacidad de ejecutar acciones dentro del nodo activo.

CONTEXTO:
- Micro-fase 5.18 completada: MiniChat v2 con contexto por nodo
- Evolución: v1(básico) → v2(contexto) → v3(acciones ejecutables)
- MiniChat v3: puede ejecutar acciones dentro del nodo, no solo chatear
- "Genera una imagen de un gato" → dispara generación en Image Node
- "Ejecuta este código" → corre código en Code Node sandbox
- "Recorta el video" → ejecuta ffmpeg en Video Node
- CRÍTICO: Detección de acción + diálogo de confirmación antes de ejecutar
- SIEMPRE confirmar antes de ejecutar una acción

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/minichat/actions.py:

   Ruta: ~/yeyo-os/src/minichat/actions.py
   Contenido:

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
       NONE = "none"  # No es una acción, solo chat


   @dataclass
   class DetectedAction:
       """Acción detectada en un mensaje."""
       action_type: ActionType
       confidence: float  # 0.0 a 1.0
       parameters: dict
       requires_confirmation: bool = True
       description: str = ""


   # Patrones para detectar acciones por nodo
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
           """
           Detecta si un mensaje contiene una intención de acción.
           Retorna DetectedAction con tipo y parámetros.
           """
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

           # No se detectó acción — es solo chat
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
           """Marca una acción como confirmada."""
           self._confirmed_actions.add(action_id)

       def is_confirmed(self, action_id: str) -> bool:
           return action_id in self._confirmed_actions

       async def execute(
           self, action: DetectedAction, node_type: str, node_id: str,
           action_id: str
       ) -> dict:
           """
           Ejecuta la acción en el nodo correspondiente.
           REQUIERE confirmación previa.
           """
           if action.requires_confirmation and not self.is_confirmed(action_id):
               return {
                   "requires_confirmation": True,
                   "action_id": action_id,
                   "action_type": action.action_type.value,
                   "description": action.description,
                   "message": f"¿Quieres ejecutar: {action.description}?",
               }

           # Ejecutar la acción vía API del nodo
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
           """Construye los datos para process() del nodo."""
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

2. Actualizar src/minichat/__init__.py:

   Ruta: ~/yeyo-os/src/minichat/__init__.py
   Contenido:
   from .service import MiniChatV2Service
   from .actions import ActionDetector, ActionExecutor, ActionType, DetectedAction

3. Crear archivo tests/unit/minichat/test_minichat_v3.py:

   Ruta: ~/yeyo-os/tests/unit/minichat/test_minichat_v3.py
   Contenido:

   """Tests para MiniChat v3 Actions — Micro-fase 5.19"""

   import pytest
   from src.minichat.actions import (
       ActionDetector, ActionExecutor, ActionType, DetectedAction,
   )


   class TestActionDetection:

       def setup_method(self):
           self.detector = ActionDetector()

       def test_detect_generate_image(self):
           action = self.detector.detect("genera una imagen de un gato", "image")
           assert action.action_type == ActionType.GENERATE_IMAGE
           assert action.requires_confirmation is True

       def test_detect_describe_image(self):
           action = self.detector.detect("describe esta imagen", "image")
           assert action.action_type == ActionType.DESCRIBE_IMAGE

       def test_detect_execute_code(self):
           action = self.detector.detect("ejecuta este código", "code")
           assert action.action_type == ActionType.EXECUTE_CODE

       def test_detect_explain_code(self):
           action = self.detector.detect("explica este código", "code")
           assert action.action_type == ActionType.EXPLAIN_CODE

       def test_detect_trim_video(self):
           action = self.detector.detect("recorta del minuto 2 al 5", "video")
           assert action.action_type == ActionType.TRIM_VIDEO
           assert "2" in action.parameters.get("groups", [])
           assert "5" in action.parameters.get("groups", [])

       def test_detect_transcribe_video(self):
           action = self.detector.detect("transcribe este video", "video")
           assert action.action_type == ActionType.TRANSCRIBE_VIDEO

       def test_detect_search_files(self):
           action = self.detector.detect("busca mis documentos", "files")
           assert action.action_type == ActionType.SEARCH_FILES

       def test_detect_summarize_page(self):
           action = self.detector.detect("resume esta página", "browser")
           assert action.action_type == ActionType.SUMMARIZE_PAGE

       def test_non_action_message_detected(self):
           action = self.detector.detect("hola, cómo estás?", "image")
           assert action.action_type == ActionType.NONE
           assert action.requires_confirmation is False

       def test_wrong_node_no_action(self):
           """Acción de imagen en nodo de código no se detecta."""
           action = self.detector.detect("genera una imagen", "code")
           assert action.action_type == ActionType.NONE


   class TestActionExecution:

       def test_confirmation_required(self):
           executor = ActionExecutor()
           action = DetectedAction(
               action_type=ActionType.GENERATE_IMAGE,
               confidence=0.8,
               parameters={},
               requires_confirmation=True,
               description="Generar imagen",
           )

       def test_confirm_action(self):
           executor = ActionExecutor()
           executor.confirm_action("action-123")
           assert executor.is_confirmed("action-123") is True

       def test_unconfirmed_action(self):
           executor = ActionExecutor()
           assert executor.is_confirmed("action-999") is False

       @pytest.mark.asyncio
       async def test_execute_without_confirmation_returns_prompt(self):
           executor = ActionExecutor()
           action = DetectedAction(
               action_type=ActionType.GENERATE_IMAGE,
               confidence=0.8,
               parameters={"groups": ["un gato"]},
               requires_confirmation=True,
               description="Generar imagen",
           )
           result = await executor.execute(action, "image", "node-1", "action-1")
           assert result["requires_confirmation"] is True
           assert "action_id" in result

   class TestActionBuildData:

       def setup_method(self):
           self.executor = ActionExecutor()

       def test_build_generate_image(self):
           action = DetectedAction(
               action_type=ActionType.GENERATE_IMAGE,
               confidence=0.8,
               parameters={"groups": ["un gato"]},
           )
           data = self.executor._build_process_data(action, "image")
           assert data["action"] == "generate"
           assert data["prompt"] == "un gato"

       def test_build_trim_video(self):
           action = DetectedAction(
               action_type=ActionType.TRIM_VIDEO,
               confidence=0.8,
               parameters={"groups": ["2", "5"]},
           )
           data = self.executor._build_process_data(action, "video")
           assert data["action"] == "process"
           assert "2" in data["command"]
           assert "5" in data["command"]

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/minichat/test_minichat_v3.py -v

VERIFICAR:
- [ ] Detecta acción de generar imagen desde texto
- [ ] Detecta acción de ejecutar código
- [ ] Detecta acción de recortar video con minutos
- [ ] Detecta acción de buscar archivos
- [ ] Detecta acción de resumir página
- [ ] Mensajes normales (no-acción) detectados como NONE
- [ ] Acción en nodo equivocado no se detecta
- [ ] Confirmación SIEMPRE requerida antes de ejecutar
- [ ] Build process data correcto para cada acción
- [ ] TODOS los tests pasan

SI FALLA:
- Regex: verificar patrones en ACTION_PATTERNS
- Import error: verificar __init__.py

NO HACER:
- No ejecutar acciones sin confirmación JAMÁS
- No detectar acciones en nodos que no las soportan
- No cambiar MiniChat v1 o v2 (backward compatible)

GATE: MiniChat v3 detecta acciones, pide confirmación, ejecuta en nodo correcto, mensajes normales no afectados, todos los tests pasan.
```
