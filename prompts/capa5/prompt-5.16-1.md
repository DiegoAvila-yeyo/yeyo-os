## ═══════════════════════════════════════
## MICRO-FASE 5.16 — Node Registry
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.16-1 [VSCODE] — Registro central de todos los tipos de nodo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.16 de Capa 5 (Órganos): crear el Node Registry, registro central de todos los tipos de nodo del sistema.

CONTEXTO:
- Micro-fases 5.0-5.15 completadas: todos los nodos individuales creados
- NodeRegistry: singleton que conoce todos los tipos de nodo disponibles
- Permite registrar, crear instancias, listar y obtener info de nodos
- Factory pattern: NodeRegistry.create("chat") → ChatNode()
- Backend: Python 3.11 + FastAPI

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/registry.py:

   Ruta: ~/yeyo-os/src/nodes/registry.py
   Contenido:

   """
   YeyoOS — Node Registry
   Micro-fase 5.16 — Capa 5: Órganos

   Registro central de todos los tipos de nodo.
   Factory pattern para crear instancias de nodos.
   """

   from typing import Optional
   from src.nodes.base import NodeBase


   class NodeNotFoundError(Exception):
       """Error cuando se solicita un tipo de nodo no registrado."""
       pass


   class NodeRegistry:
       """
       Registro central de todos los tipos de nodo de YeyoOS.
       Singleton: una sola instancia en todo el sistema.
       """

       _nodes: dict[str, type[NodeBase]] = {}
       _metadata: dict[str, dict] = {}
       _instance: Optional["NodeRegistry"] = None

       @classmethod
       def get_instance(cls) -> "NodeRegistry":
           """Retorna la instancia singleton."""
           if cls._instance is None:
               cls._instance = cls()
           return cls._instance

       @classmethod
       def register(
           cls,
           node_type: str,
           node_class: type[NodeBase],
           metadata: Optional[dict] = None,
       ) -> None:
           """
           Registra un tipo de nodo.
           node_type: identificador único (ej: "chat", "image", "video")
           node_class: clase que hereda de NodeBase
           """
           if not issubclass(node_class, NodeBase):
               raise TypeError(f"{node_class} no hereda de NodeBase")
           cls._nodes[node_type] = node_class
           cls._metadata[node_type] = metadata or {}

       @classmethod
       def create(cls, node_type: str) -> NodeBase:
           """Crea una instancia de un nodo por su tipo."""
           if node_type not in cls._nodes:
               raise NodeNotFoundError(
                   f"Tipo de nodo '{node_type}' no registrado. "
                   f"Disponibles: {list(cls._nodes.keys())}"
               )
           return cls._nodes[node_type]()

       @classmethod
       def list_types(cls) -> list[str]:
           """Lista todos los tipos de nodo registrados."""
           return list(cls._nodes.keys())

       @classmethod
       def get_info(cls, node_type: str) -> dict:
           """Obtiene información de un tipo de nodo."""
           if node_type not in cls._nodes:
               raise NodeNotFoundError(f"Tipo de nodo '{node_type}' no registrado")

           node_class = cls._nodes[node_type]
           metadata = cls._metadata.get(node_type, {})

           return {
               "type": node_type,
               "class_name": node_class.__name__,
               "module": node_class.__module__,
               **metadata,
           }

       @classmethod
       def is_registered(cls, node_type: str) -> bool:
           """Verifica si un tipo de nodo está registrado."""
           return node_type in cls._nodes

       @classmethod
       def unregister(cls, node_type: str) -> bool:
           """Desregistra un tipo de nodo."""
           if node_type in cls._nodes:
               del cls._nodes[node_type]
               cls._metadata.pop(node_type, None)
               return True
           return False

       @classmethod
       def clear(cls) -> None:
           """Limpia el registro (útil para tests)."""
           cls._nodes.clear()
           cls._metadata.clear()
           cls._instance = None

       @classmethod
       def register_all_defaults(cls) -> None:
           """Registra todos los nodos predeterminados de YeyoOS."""
           from src.nodes.chat.service import ChatNode
           from src.nodes.image.service import ImageGenerationNode
           from src.nodes.video.service import VideoNode
           from src.nodes.code.service import CodeNode
           from src.nodes.automation.service import AutomationNode
           from src.nodes.files.service import FilesNode
           from src.nodes.browser.service import BrowserNode
           from src.nodes.config.service import ConfigNode
           from src.nodes.mining.service import MiningNode

           defaults = {
               "chat": (ChatNode, {"icon": "💬", "description": "Chat con IA"}),
               "image": (ImageGenerationNode, {"icon": "🎨", "description": "Generación de imágenes"}),
               "video": (VideoNode, {"icon": "🎬", "description": "Procesamiento de video"}),
               "code": (CodeNode, {"icon": "💻", "description": "Editor de código"}),
               "automation": (AutomationNode, {"icon": "🔄", "description": "Pipelines de automatización"}),
               "files": (FilesNode, {"icon": "📁", "description": "Explorador de archivos"}),
               "browser": (BrowserNode, {"icon": "🌐", "description": "Navegador web"}),
               "config": (ConfigNode, {"icon": "⚙️", "description": "Configuración del sistema"}),
               "mining": (MiningNode, {"icon": "⛏️", "description": "Dashboard ASIC (GPU NUNCA)"}),
           }

           for node_type, (node_class, metadata) in defaults.items():
               cls.register(node_type, node_class, metadata)

2. Actualizar src/nodes/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/__init__.py
   Contenido:
   from .base import NodeBase, NodeStatus, PrivilegeLevel
   from .registry import NodeRegistry, NodeNotFoundError

3. Crear archivo tests/unit/nodes/test_registry.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/test_registry.py
   Contenido:

   """Tests para Node Registry — Micro-fase 5.16"""

   import pytest
   from src.nodes.base import NodeBase, PrivilegeLevel
   from src.nodes.registry import NodeRegistry, NodeNotFoundError


   class FakeNode(NodeBase):
       async def initialize(self): pass
       async def render_ui(self) -> dict: return {}
       async def process(self, input_data: dict) -> dict: return {}
       async def cleanup(self): pass

       def __init__(self):
           super().__init__(name="Fake", version="1.0")


   class TestNodeRegistryRegister:

       def setup_method(self):
           NodeRegistry.clear()

       def test_register_adds_node(self):
           NodeRegistry.register("fake", FakeNode)
           assert "fake" in NodeRegistry.list_types()

       def test_register_non_nodebase_raises(self):
           with pytest.raises(TypeError):
               NodeRegistry.register("bad", dict)

       def test_register_with_metadata(self):
           NodeRegistry.register("fake", FakeNode, {"icon": "🧪"})
           info = NodeRegistry.get_info("fake")
           assert info["icon"] == "🧪"


   class TestNodeRegistryCreate:

       def setup_method(self):
           NodeRegistry.clear()

       def test_create_returns_instance(self):
           NodeRegistry.register("fake", FakeNode)
           node = NodeRegistry.create("fake")
           assert isinstance(node, FakeNode)
           assert isinstance(node, NodeBase)

       def test_create_unknown_raises(self):
           with pytest.raises(NodeNotFoundError):
               NodeRegistry.create("nonexistent")


   class TestNodeRegistryList:

       def setup_method(self):
           NodeRegistry.clear()

       def test_list_types(self):
           NodeRegistry.register("a", FakeNode)
           NodeRegistry.register("b", FakeNode)
           types = NodeRegistry.list_types()
           assert "a" in types
           assert "b" in types

       def test_is_registered(self):
           NodeRegistry.register("fake", FakeNode)
           assert NodeRegistry.is_registered("fake") is True
           assert NodeRegistry.is_registered("nope") is False

       def test_get_info(self):
           NodeRegistry.register("fake", FakeNode)
           info = NodeRegistry.get_info("fake")
           assert info["type"] == "fake"
           assert info["class_name"] == "FakeNode"

       def test_get_info_unknown_raises(self):
           with pytest.raises(NodeNotFoundError):
               NodeRegistry.get_info("nonexistent")


   class TestNodeRegistryUnregister:

       def setup_method(self):
           NodeRegistry.clear()

       def test_unregister(self):
           NodeRegistry.register("fake", FakeNode)
           assert NodeRegistry.unregister("fake") is True
           assert "fake" not in NodeRegistry.list_types()

       def test_unregister_unknown_returns_false(self):
           assert NodeRegistry.unregister("nonexistent") is False

       def test_clear(self):
           NodeRegistry.register("a", FakeNode)
           NodeRegistry.register("b", FakeNode)
           NodeRegistry.clear()
           assert len(NodeRegistry.list_types()) == 0

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/test_registry.py -v

VERIFICAR:
- [ ] register añade nodo al registry
- [ ] create retorna instancia correcta
- [ ] Tipo desconocido lanza NodeNotFoundError
- [ ] list_types muestra todos los registrados
- [ ] get_info retorna metadata del nodo
- [ ] Solo clases que heredan de NodeBase se registran
- [ ] clear limpia todo (para tests)
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- Circular import: register_all_defaults usa lazy imports

NO HACER:
- No instanciar nodos reales en register_all_defaults (lazy imports)
- No hacer el registry mutable desde fuera (solo via register/unregister)

GATE: NodeRegistry registra, crea, lista y obtiene info de nodos. Solo NodeBase subclasses. Singleton. Todos los tests pasan.
```
