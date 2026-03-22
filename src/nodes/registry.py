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
        if not issubclass(node_class, NodeBase):
            raise TypeError(f"{node_class} no hereda de NodeBase")
        cls._nodes[node_type] = node_class
        cls._metadata[node_type] = metadata or {}

    @classmethod
    def create(cls, node_type: str) -> NodeBase:
        if node_type not in cls._nodes:
            raise NodeNotFoundError(
                f"Tipo de nodo '{node_type}' no registrado. "
                f"Disponibles: {list(cls._nodes.keys())}"
            )
        return cls._nodes[node_type]()

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._nodes.keys())

    @classmethod
    def get_info(cls, node_type: str) -> dict:
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
        return node_type in cls._nodes

    @classmethod
    def unregister(cls, node_type: str) -> bool:
        if node_type in cls._nodes:
            del cls._nodes[node_type]
            cls._metadata.pop(node_type, None)
            return True
        return False

    @classmethod
    def clear(cls) -> None:
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
