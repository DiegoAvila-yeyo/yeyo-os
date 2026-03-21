## ═══════════════════════════════════════
## MICRO-FASE 5.12 — Files Node
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.12-1 [VSCODE] — Explorador de archivos con búsqueda semántica

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.12 de Capa 5 (Órganos): crear el Files Node con explorador de archivos y búsqueda semántica.

CONTEXTO:
- Micro-fases 5.0-5.11 completadas
- File browser con tree view
- Búsqueda semántica: "find my tax documents" → busca por significado del contenido
- Preview: imágenes, texto, PDF, código
- Operaciones: open, copy, move (NO delete sin diálogo de confirmación)
- Backend usa embeddings para indexar contenido de archivos
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + Ollama qwen2.5:3b

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/files
   mkdir -p tests/unit/nodes/files
   mkdir -p frontend/src/components/nodes/files

2. Crear archivo src/nodes/files/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/files/__init__.py
   Contenido:
   from .service import FilesNode

3. Crear archivo src/nodes/files/service.py:

   Ruta: ~/yeyo-os/src/nodes/files/service.py
   Contenido:

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
           self._indexed_files: dict[str, list[float]] = {}  # path → embedding

       async def initialize(self) -> None:
           """Inicializa el explorador de archivos."""
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
               # SIEMPRE requiere confirmación
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

           # Buscar en archivos indexados
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

4. Crear archivo frontend/src/components/nodes/files/FilesNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/files/FilesNode.tsx
   Contenido:

   /**
    * YeyoOS — Files Node Frontend
    * Micro-fase 5.12 — Capa 5: Órganos
    */

   'use client';

   import React, { useState } from 'react';
   import NodeWrapper from '../NodeWrapper';

   interface FileTreeItem {
     name: string;
     path: string;
     isDirectory: boolean;
     size?: number;
     extension?: string;
     children?: FileTreeItem[];
   }

   interface FilesNodeProps {
     nodeId: string;
     rootPath: string;
     tree: FileTreeItem[];
     onNavigate: (path: string) => void;
     onPreview: (path: string) => void;
     onSearch: (query: string) => void;
     onClose: (nodeId: string) => void;
   }

   function FileTree({ items, onNavigate, onPreview, depth = 0 }: {
     items: FileTreeItem[];
     onNavigate: (path: string) => void;
     onPreview: (path: string) => void;
     depth?: number;
   }) {
     return (
       <div style={{ paddingLeft: depth * 16 }}>
         {items.map((item) => (
           <div key={item.path}>
             <div
               onClick={() => item.isDirectory ? onNavigate(item.path) : onPreview(item.path)}
               className="flex items-center gap-1 px-1 py-0.5 text-xs
                          hover:bg-gray-700 rounded cursor-pointer text-gray-300"
             >
               <span>{item.isDirectory ? '📁' : '📄'}</span>
               <span className="truncate">{item.name}</span>
               {!item.isDirectory && item.size && (
                 <span className="text-gray-500 ml-auto text-[10px]">
                   {(item.size / 1024).toFixed(1)}KB
                 </span>
               )}
             </div>
             {item.isDirectory && item.children && (
               <FileTree items={item.children} onNavigate={onNavigate}
                         onPreview={onPreview} depth={depth + 1} />
             )}
           </div>
         ))}
       </div>
     );
   }

   export default function FilesNode({
     nodeId, rootPath, tree, onNavigate, onPreview, onSearch, onClose,
   }: FilesNodeProps) {
     const [searchQuery, setSearchQuery] = useState('');

     return (
       <NodeWrapper nodeId={nodeId} title="Files" icon="📁" onClose={onClose}>
         <div className="flex flex-col h-full">
           {/* Search */}
           <div className="flex items-center gap-2 px-2 py-2 bg-gray-800
                           border-b border-gray-700 shrink-0">
             <input
               type="text"
               value={searchQuery}
               onChange={(e) => setSearchQuery(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && onSearch(searchQuery)}
               placeholder="Buscar por significado..."
               className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white
                          rounded border border-gray-600 focus:outline-none"
             />
             <button
               onClick={() => onSearch(searchQuery)}
               className="px-2 py-1 text-xs bg-blue-600 text-white rounded"
             >
               🔍
             </button>
           </div>

           {/* File tree */}
           <div className="flex-1 overflow-y-auto py-1">
             <FileTree items={tree} onNavigate={onNavigate} onPreview={onPreview} />
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/files/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/files/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/files/test_files_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/files/test_files_node.py
   Contenido:

   """Tests para Files Node — Micro-fase 5.12"""

   import pytest
   import tempfile
   from pathlib import Path
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.files.service import FilesNode


   class TestFilesNodeTree:

       def test_get_tree(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               Path(tmpdir, "file.txt").write_text("hello")
               Path(tmpdir, "subdir").mkdir()
               Path(tmpdir, "subdir", "inner.py").write_text("x=1")

               node = FilesNode(root_path=tmpdir)
               tree = node._get_tree(Path(tmpdir), depth=2)
               names = [item["name"] for item in tree]
               assert "file.txt" in names
               assert "subdir" in names

       def test_hidden_files_excluded(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               Path(tmpdir, ".hidden").write_text("secret")
               Path(tmpdir, "visible.txt").write_text("hello")

               node = FilesNode(root_path=tmpdir)
               tree = node._get_tree(Path(tmpdir))
               names = [item["name"] for item in tree]
               assert ".hidden" not in names
               assert "visible.txt" in names


   class TestFilesNodeOperations:

       def test_copy_file(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               src = Path(tmpdir, "original.txt")
               src.write_text("content")
               dst = Path(tmpdir, "copy.txt")

               node = FilesNode(root_path=tmpdir)
               result = node._copy_file(str(src), str(dst))
               assert "copied" in result
               assert dst.exists()

       def test_move_file(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               src = Path(tmpdir, "to_move.txt")
               src.write_text("content")
               dst = Path(tmpdir, "moved.txt")

               node = FilesNode(root_path=tmpdir)
               result = node._move_file(str(src), str(dst))
               assert "moved" in result
               assert not src.exists()
               assert dst.exists()

       def test_delete_requires_confirmation(self):
           node = FilesNode()
           result = node._delete_file("/some/path", confirmed=False)
           assert result["requires_confirmation"] is True

       def test_delete_with_confirmation(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               f = Path(tmpdir, "to_delete.txt")
               f.write_text("bye")

               node = FilesNode(root_path=tmpdir)
               result = node._delete_file(str(f), confirmed=True)
               assert "deleted" in result
               assert not f.exists()


   class TestFilesNodeSearch:

       def test_cosine_similarity(self):
           sim = FilesNode._cosine_similarity([1, 0], [1, 0])
           assert abs(sim - 1.0) < 0.001

       def test_cosine_similarity_orthogonal(self):
           sim = FilesNode._cosine_similarity([1, 0], [0, 1])
           assert abs(sim) < 0.001

       def test_cosine_similarity_empty(self):
           sim = FilesNode._cosine_similarity([], [])
           assert sim == 0.0

       @pytest.mark.asyncio
       async def test_no_delete_action_without_confirmation(self):
           node = FilesNode()
           result = await node.process({"action": "delete", "path": "/test"})
           assert result["requires_confirmation"] is True

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/files/test_files_node.py -v

VERIFICAR:
- [ ] Tree view muestra archivos y directorios
- [ ] Archivos ocultos (.) excluidos del tree
- [ ] Búsqueda semántica por embeddings funciona
- [ ] Preview de texto, código, imágenes
- [ ] Copy y move funcionan
- [ ] Delete SIEMPRE requiere confirmación
- [ ] No silent delete NUNCA
- [ ] Cosine similarity calculada correctamente
- [ ] TODOS los tests pasan

SI FALLA:
- tempfile: viene con Python estándar
- OllamaProvider: search semántica usa mock
- Import error: verificar __init__.py

NO HACER:
- No implementar delete sin confirmación JAMÁS
- No indexar archivos del sistema fuera del home
- No mostrar archivos sensibles (.env, .ssh, etc.)

GATE: FilesNode con tree view, búsqueda semántica, preview, copy/move, delete SIEMPRE con confirmación, todos los tests pasan.
```
