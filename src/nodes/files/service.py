"""
YeyoOS — Files Node
Micro-fase 5.12 — Capa 5: Órganos

Explorador de archivos con búsqueda semántica por embeddings.
REGLA: NO delete sin confirmación. Siempre diálogo.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.nodes.base import NodeBase, PrivilegeLevel


PREVIEWABLE_EXTENSIONS = {
    "text": {".txt", ".md", ".log", ".csv", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh", ".bash", ".sql"},
    "image": {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"},
    "pdf": {".pdf"},
}


@dataclass
class FileInfo:
    """Información de un archivo o directorio."""
    name: str
    path: str
    is_directory: bool
    size: int = 0
    extension: str = ""
    modified_at: Optional[str] = None
    children: list = field(default_factory=list)


class FilesNode(NodeBase):
    """
    Nodo de Archivos — órgano de gestión de archivos de YeyoOS.
    Tree view, búsqueda semántica, preview.
    """

    def __init__(self, root_path: str = "~/"):
        super().__init__(
            name="Files",
            version="1.0.0",
            privilege_level=PrivilegeLevel.USER,
            container_config={"memory_limit": "512m", "cpu_shares": 256},
        )
        self._root_path = Path(root_path).expanduser().resolve()
        self._indexed_files: dict[str, list[float]] = {}

    async def initialize(self) -> None:
        if not self._root_path.exists():
            raise FileNotFoundError(f"Root path not found: {self._root_path}")

    async def render_ui(self) -> dict:
        return {
            "component": "FilesNode",
            "props": {
                "rootPath": str(self._root_path),
                "tree": self._get_tree(self._root_path, depth=2),
            },
        }

    async def process(self, input_data: dict) -> dict:
        action = input_data.get("action", "")

        if action == "list":
            return self._list_directory(input_data.get("path", str(self._root_path)))
        elif action == "preview":
            return await self._preview_file(input_data.get("path", ""))
        elif action == "search":
            return await self._semantic_search(input_data.get("query", ""))
        elif action == "copy":
            return self._copy_file(input_data.get("source", ""), input_data.get("dest", ""))
        elif action == "move":
            return self._move_file(input_data.get("source", ""), input_data.get("dest", ""))
        elif action == "delete":
            return {"requires_confirmation": True, "path": input_data.get("path", ""),
                    "message": "¿Estás seguro de que quieres eliminar este archivo?"}
        elif action == "confirm_delete":
            return self._delete_file(input_data.get("path", ""), confirmed=True)
        else:
            return {"error": f"Acción desconocida: {action}"}

    async def cleanup(self) -> None:
        self._indexed_files.clear()

    # ═══════════════════════════════════
    # MÉTODOS ESPECÍFICOS
    # ═══════════════════════════════════

    def _get_tree(self, path: Path, depth: int = 2) -> list[dict]:
        """Genera tree view de directorio."""
        if depth <= 0 or not path.is_dir():
            return []

        items = []
        try:
            for entry in sorted(path.iterdir()):
                if entry.name.startswith("."):
                    continue
                info = {
                    "name": entry.name,
                    "path": str(entry),
                    "isDirectory": entry.is_dir(),
                }
                if entry.is_dir():
                    info["children"] = self._get_tree(entry, depth - 1)
                else:
                    info["size"] = entry.stat().st_size
                    info["extension"] = entry.suffix
                items.append(info)
        except PermissionError:
            pass
        return items

    def _list_directory(self, path: str) -> dict:
        """Lista contenido de un directorio."""
        p = Path(path)
        if not p.exists() or not p.is_dir():
            return {"error": "Directorio no encontrado"}
        files = self._get_tree(p, depth=1)
        return {"path": str(p), "files": files, "count": len(files)}

    async def _preview_file(self, path: str) -> dict:
        """Preview de un archivo."""
        p = Path(path)
        if not p.exists():
            return {"error": "Archivo no encontrado"}

        ext = p.suffix.lower()
        preview_type = "unknown"
        for ptype, exts in PREVIEWABLE_EXTENSIONS.items():
            if ext in exts:
                preview_type = ptype
                break

        if preview_type in ("text", "code"):
            try:
                content = p.read_text(encoding="utf-8", errors="replace")[:10000]
                return {"type": preview_type, "content": content, "path": str(p)}
            except Exception as e:
                return {"error": f"Cannot read file: {e}"}
        elif preview_type == "image":
            import base64
            data = base64.b64encode(p.read_bytes()).decode("utf-8")
            return {"type": "image", "data_base64": data, "path": str(p)}
        else:
            return {"type": "binary", "size": p.stat().st_size, "path": str(p)}

    async def _semantic_search(self, query: str) -> dict:
        """Búsqueda semántica usando embeddings."""
        from src.ia.ollama_provider import OllamaProvider

        provider = OllamaProvider()
        query_embedding = await provider.get_embedding(query)

        results = []
        for file_path, file_embedding in self._indexed_files.items():
            similarity = self._cosine_similarity(query_embedding, file_embedding)
            if similarity > 0.5:
                results.append({
                    "path": file_path,
                    "similarity": round(similarity, 3),
                    "name": Path(file_path).name,
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return {"query": query, "results": results[:20]}

    async def index_file(self, path: str) -> dict:
        """Indexa un archivo para búsqueda semántica."""
        p = Path(path)
        if not p.exists():
            return {"error": "Archivo no encontrado"}

        try:
            content = p.read_text(encoding="utf-8", errors="replace")[:5000]
        except Exception:
            return {"error": "Cannot read file for indexing"}

        from src.ia.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        embedding = await provider.get_embedding(content)
        self._indexed_files[str(p)] = embedding

        return {"indexed": str(p)}

    def _copy_file(self, source: str, dest: str) -> dict:
        """Copia un archivo."""
        try:
            src = Path(source)
            dst = Path(dest)
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            return {"copied": source, "to": dest}
        except Exception as e:
            return {"error": f"Error copiando: {e}"}

    def _move_file(self, source: str, dest: str) -> dict:
        """Mueve un archivo."""
        try:
            shutil.move(source, dest)
            return {"moved": source, "to": dest}
        except Exception as e:
            return {"error": f"Error moviendo: {e}"}

    def _delete_file(self, path: str, confirmed: bool = False) -> dict:
        """Elimina un archivo SOLO si está confirmado."""
        if not confirmed:
            return {"requires_confirmation": True, "path": path}
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                p.unlink()
            return {"deleted": path}
        except Exception as e:
            return {"error": f"Error eliminando: {e}"}

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calcula similitud coseno entre dos vectores."""
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x ** 2 for x in a) ** 0.5
        mag_b = sum(x ** 2 for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)
