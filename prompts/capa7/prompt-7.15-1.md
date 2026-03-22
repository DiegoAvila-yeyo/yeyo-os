## ═══════════════════════════════════════
## MICRO-FASE 7.15 — YEYO Store: UI Rediseñada + Backend de Instalación
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.15-1 [VSCODE] — Store con categorías, cards de zona de seguridad e instalación validada

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.15 de Capa 7 (Evolución): rediseñar la UI del YEYO Store con categorías, cards con zona de seguridad visual, y reforzar el backend de instalación con validación de checksum y GrafoValidador.

CONTEXTO:
- Micro-fase 7.3 completada: YEYO Store Server básico existe en src/store/
- Micro-fase 7.4 completada: Store Security Pipeline existe
- Micro-fase 7.5 completada: Store Frontend básico existe
- Micro-fase 3.18–3.20 completadas: GridBackground, Topbar, layouts de nodos disponibles
- Stack frontend: React + TypeScript (mismas convenciones que Capa 3)
- Stack backend: FastAPI + Python, src/store/ existente
- .ypkg = zip con manifest.json + código + assets
- GrafoValidador: src/core/grafo_validador.py existe (valida estructura de grafos)
- Los nodos instalados deben aparecer en hubStore.nodosInstalados (Capa 3)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Actualizar src/store/node_registry.py — NodeRegistryEntry dataclass:

   Ruta: ~/yeyo-os/src/store/node_registry.py
   Contenido:

   """
   YeyoOS — Node Registry
   Micro-fase 7.15 — Capa 7: Evolución

   Registro de nodos disponibles y nodos instalados.
   NodeRegistryEntry es la estructura de datos canónica de un nodo en el Store.
   """

   from __future__ import annotations
   import json
   import hashlib
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Literal, Optional
   import logging

   logger = logging.getLogger(__name__)

   ZonaSeguridad = Literal["verde", "amarilla", "roja"]


   @dataclass
   class NodeRegistryEntry:
       """Entrada completa de un nodo en el YEYO Store."""
       id: str
       nombre: str
       version: str
       autor: str
       descripcion: str
       icono: str                          # emoji o URL de imagen
       categoria: str                      # IA, Internet, Juegos, Dev, etc.
       zona_seguridad: ZonaSeguridad       # verde / amarilla / roja
       permisos: list[str]                 # ej: ["internet.read", "filesystem.write"]
       checksum: str                       # SHA-256 del .ypkg
       url_descarga: str                   # URL del .ypkg
       rating: float = 0.0                 # 0.0 - 5.0
       descargas: int = 0
       tags: list[str] = field(default_factory=list)
       instalado: bool = False
       version_instalada: Optional[str] = None

       def to_dict(self) -> dict:
           return {
               "id": self.id,
               "nombre": self.nombre,
               "version": self.version,
               "autor": self.autor,
               "descripcion": self.descripcion,
               "icono": self.icono,
               "categoria": self.categoria,
               "zona_seguridad": self.zona_seguridad,
               "permisos": self.permisos,
               "checksum": self.checksum,
               "url_descarga": self.url_descarga,
               "rating": self.rating,
               "descargas": self.descargas,
               "tags": self.tags,
               "instalado": self.instalado,
               "version_instalada": self.version_instalada,
           }

       @classmethod
       def from_dict(cls, data: dict) -> "NodeRegistryEntry":
           return cls(
               id=data["id"],
               nombre=data["nombre"],
               version=data["version"],
               autor=data["autor"],
               descripcion=data["descripcion"],
               icono=data.get("icono", "📦"),
               categoria=data.get("categoria", "Utilidad"),
               zona_seguridad=data.get("zona_seguridad", "verde"),
               permisos=data.get("permisos", []),
               checksum=data.get("checksum", ""),
               url_descarga=data.get("url_descarga", ""),
               rating=data.get("rating", 0.0),
               descargas=data.get("descargas", 0),
               tags=data.get("tags", []),
               instalado=data.get("instalado", False),
               version_instalada=data.get("version_instalada"),
           )


   class NodeRegistry:
       """Administra el registro de nodos del YEYO Store."""

       INSTALL_DIR = Path.home() / ".yeyo" / "nodes"
       REGISTRY_FILE = Path.home() / ".yeyo" / "registry.json"

       def __init__(self) -> None:
           self.INSTALL_DIR.mkdir(parents=True, exist_ok=True)
           self._entries: dict[str, NodeRegistryEntry] = {}
           self._cargar_registry()

       def _cargar_registry(self) -> None:
           if self.REGISTRY_FILE.exists():
               try:
                   with open(self.REGISTRY_FILE) as f:
                       data = json.load(f)
                   for item in data:
                       entry = NodeRegistryEntry.from_dict(item)
                       self._entries[entry.id] = entry
               except Exception as e:
                   logger.error(f"Error cargando registry: {e}")

       def _guardar_registry(self) -> None:
           try:
               with open(self.REGISTRY_FILE, "w") as f:
                   json.dump([e.to_dict() for e in self._entries.values()], f, indent=2)
           except Exception as e:
               logger.error(f"Error guardando registry: {e}")

       def obtener_todos(self, categoria: str | None = None) -> list[NodeRegistryEntry]:
           entries = list(self._entries.values())
           if categoria:
               entries = [e for e in entries if e.categoria.lower() == categoria.lower()]
           return entries

       def obtener_por_id(self, node_id: str) -> NodeRegistryEntry | None:
           return self._entries.get(node_id)

       def registrar_nodo(self, entry: NodeRegistryEntry) -> None:
           self._entries[entry.id] = entry
           self._guardar_registry()

       def marcar_instalado(self, node_id: str, version: str) -> None:
           if node_id in self._entries:
               self._entries[node_id].instalado = True
               self._entries[node_id].version_instalada = version
               self._guardar_registry()

       def obtener_instalados(self) -> list[str]:
           return [e.id for e in self._entries.values() if e.instalado]

       @staticmethod
       def calcular_checksum(ruta_archivo: Path) -> str:
           sha256 = hashlib.sha256()
           with open(ruta_archivo, "rb") as f:
               for chunk in iter(lambda: f.read(65536), b""):
                   sha256.update(chunk)
           return sha256.hexdigest()

2. Actualizar src/store/store_api.py — endpoints completos:

   Ruta: ~/yeyo-os/src/store/store_api.py
   Contenido:

   """
   YeyoOS — Store API
   Micro-fase 7.15 — Capa 7: Evolución

   Endpoints del YEYO Store:
     GET  /api/store/nodes           — lista todos los nodos (filtro por categoría)
     GET  /api/store/nodes/{node_id} — detalle de un nodo
     POST /api/store/install/{node_id} — instalar un nodo
     GET  /api/store/installed       — lista de IDs instalados
   """

   import zipfile
   import tempfile
   import hashlib
   import json
   import logging
   from pathlib import Path
   from typing import Optional

   import httpx
   from fastapi import APIRouter, HTTPException, Query
   from pydantic import BaseModel

   from .node_registry import NodeRegistry, NodeRegistryEntry

   logger = logging.getLogger(__name__)
   router = APIRouter(prefix="/api/store", tags=["store"])

   # Singleton del registry (en producción, inyectar como dependencia)
   _registry = NodeRegistry()


   class InstallResponse(BaseModel):
       ok: bool
       node_id: str
       mensaje: str


   class InstallError(BaseModel):
       ok: bool
       node_id: str
       error: str


   @router.get("/nodes", response_model=list[dict])
   async def listar_nodos(
       categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
       buscar: Optional[str] = Query(None, description="Buscar por nombre o descripción"),
   ) -> list[dict]:
       """Lista todos los nodos disponibles en el Store."""
       nodos = _registry.obtener_todos(categoria=categoria)
       if buscar:
           buscar_lower = buscar.lower()
           nodos = [
               n for n in nodos
               if buscar_lower in n.nombre.lower() or buscar_lower in n.descripcion.lower()
           ]
       return [n.to_dict() for n in nodos]


   @router.get("/nodes/{node_id}", response_model=dict)
   async def obtener_nodo(node_id: str) -> dict:
       """Obtiene el detalle de un nodo específico."""
       nodo = _registry.obtener_por_id(node_id)
       if not nodo:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado")
       return nodo.to_dict()


   @router.post("/install/{node_id}", response_model=InstallResponse)
   async def instalar_nodo(node_id: str) -> InstallResponse:
       """
       Instala un nodo desde el Store.
       Proceso:
         1. Obtener entrada del registry
         2. Descargar .ypkg
         3. Validar checksum SHA-256
         4. Validar estructura con GrafoValidador
         5. Instalar en ~/.yeyo/nodes/
         6. Marcar como instalado en el registry
       """
       nodo = _registry.obtener_por_id(node_id)
       if not nodo:
           raise HTTPException(status_code=404, detail=f"Nodo '{node_id}' no encontrado en el Store")

       if nodo.instalado:
           return InstallResponse(ok=True, node_id=node_id, mensaje=f"'{nodo.nombre}' ya está instalado")

       # Descargar .ypkg
       try:
           async with httpx.AsyncClient(timeout=60.0) as client:
               response = await client.get(nodo.url_descarga)
               response.raise_for_status()
               ypkg_bytes = response.content
       except Exception as e:
           logger.error(f"Error descargando {node_id}: {e}")
           raise HTTPException(status_code=502, detail=f"Error descargando el paquete: {e}")

       # Validar checksum
       checksum_calculado = hashlib.sha256(ypkg_bytes).hexdigest()
       if checksum_calculado != nodo.checksum:
           raise HTTPException(
               status_code=422,
               detail=f"Checksum inválido. Esperado: {nodo.checksum[:16]}... Got: {checksum_calculado[:16]}..."
           )

       # Guardar temporalmente y extraer
       with tempfile.NamedTemporaryFile(suffix=".ypkg", delete=False) as tmp:
           tmp.write(ypkg_bytes)
           tmp_path = Path(tmp.name)

       try:
           install_path = NodeRegistry.INSTALL_DIR / node_id
           install_path.mkdir(parents=True, exist_ok=True)

           with zipfile.ZipFile(tmp_path) as zf:
               # Verificar estructura del .ypkg
               nombres = zf.namelist()
               if "manifest.json" not in nombres:
                   raise HTTPException(status_code=422, detail="El .ypkg no contiene manifest.json")

               manifest_raw = zf.read("manifest.json")
               manifest = json.loads(manifest_raw)

               # Validar manifest mínimo
               campos_requeridos = ["id", "nombre", "version", "grafo"]
               for campo in campos_requeridos:
                   if campo not in manifest:
                       raise HTTPException(status_code=422, detail=f"manifest.json falta campo: {campo}")

               # Validar grafo con GrafoValidador
               try:
                   from src.core.grafo_validador import GrafoValidador
                   validador = GrafoValidador()
                   resultado = validador.validar(manifest["grafo"])
                   if not resultado.valido:
                       raise HTTPException(status_code=422, detail=f"Grafo inválido: {resultado.errores}")
               except ImportError:
                   logger.warning("GrafoValidador no disponible — omitiendo validación de grafo")

               # Extraer todos los archivos
               zf.extractall(install_path)

           # Marcar como instalado
           _registry.marcar_instalado(node_id, nodo.version)
           logger.info(f"Nodo '{node_id}' instalado exitosamente en {install_path}")

           return InstallResponse(ok=True, node_id=node_id, mensaje=f"'{nodo.nombre}' instalado correctamente")

       finally:
           tmp_path.unlink(missing_ok=True)


   @router.get("/installed", response_model=list[str])
   async def listar_instalados() -> list[str]:
       """Retorna los IDs de todos los nodos instalados."""
       return _registry.obtener_instalados()

3. Crear archivo frontend/src/components/store/StoreUI.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/store/StoreUI.tsx
   Contenido:

   /**
    * YeyoOS — StoreUI
    * Micro-fase 7.15 — Capa 7: Evolución
    *
    * UI completa del YEYO Store.
    * Layout: [Categorías sidebar (izq 200px)] | [Grid de cards (centro flex)]
    * Cards: ícono, nombre, descripción, zona seguridad (🟢/🟡/🔴), rating, descargas, autor
    * Botón [Instalar] / [Instalado ✓]
    */

   import React, { useState, useEffect } from 'react'
   import { GridBackground } from '../hub/GridBackground'

   export interface StoreNodeCard {
     id: string
     nombre: string
     descripcion: string
     icono: string
     categoria: string
     zona_seguridad: 'verde' | 'amarilla' | 'roja'
     permisos: string[]
     rating: number
     descargas: number
     autor: string
     instalado: boolean
   }

   export interface StoreUIProps {
     nodos?: StoreNodeCard[]
     onInstalar?: (nodeId: string) => Promise<void>
     instalandoId?: string | null
   }

   const CATEGORIAS = [
     { id: 'todos', icono: '🔍', label: 'Todos' },
     { id: 'IA', icono: '🤖', label: 'IA' },
     { id: 'Internet', icono: '🌐', label: 'Internet' },
     { id: 'Juegos', icono: '🎮', label: 'Juegos' },
     { id: 'Dev', icono: '💻', label: 'Dev' },
     { id: 'Creativo', icono: '🎨', label: 'Creativo' },
     { id: 'Social', icono: '📱', label: 'Social' },
     { id: 'Sistema', icono: '🔧', label: 'Sistema' },
     { id: 'Utilidad', icono: '⚙️', label: 'Utilidad' },
     { id: 'ZonaSegura', icono: '🔒', label: 'Zona Segura' },
   ]

   const ZONA_EMOJI: Record<string, string> = {
     verde: '🟢',
     amarilla: '🟡',
     roja: '🔴',
   }

   const ZONA_LABEL: Record<string, string> = {
     verde: 'Seguro',
     amarilla: 'Permisos',
     roja: 'Elevado',
   }

   export function StoreUI({ nodos = [], onInstalar, instalandoId }: StoreUIProps) {
     const [categoriaActiva, setCategoriaActiva] = useState('todos')
     const [busqueda, setBusqueda] = useState('')

     const nodosFiltrados = nodos.filter((n) => {
       const matchCategoria = categoriaActiva === 'todos' || n.categoria === categoriaActiva
       const matchBusqueda = !busqueda || n.nombre.toLowerCase().includes(busqueda.toLowerCase()) || n.descripcion.toLowerCase().includes(busqueda.toLowerCase())
       return matchCategoria && matchBusqueda
     })

     const renderStars = (rating: number) => {
       return Array.from({ length: 5 }, (_, i) => (
         <span key={i} style={{ color: i < Math.round(rating) ? '#FFC107' : '#37474F', fontSize: 12 }}>★</span>
       ))
     }

     return (
       <div
         data-testid="store-ui"
         style={{
           display: 'flex',
           flexDirection: 'column',
           height: '100%',
           position: 'relative',
           backgroundColor: '#060B18',
         }}
       >
         <GridBackground saturation={1.0} style={{ opacity: 0.3 }} />

         {/* Barra de búsqueda */}
         <div style={{
           position: 'relative', zIndex: 1,
           padding: '16px 20px',
           borderBottom: '1px solid #1E3A5F',
           backgroundColor: 'rgba(6,11,24,0.9)',
         }}>
           <input
             data-testid="store-search"
             value={busqueda}
             onChange={(e) => setBusqueda(e.target.value)}
             placeholder="🔍  Buscar nodos..."
             style={{
               width: '100%', backgroundColor: '#0A0E1A',
               border: '1px solid #1E3A5F', borderRadius: 8,
               color: '#E0F7FA', padding: '10px 16px', fontSize: 14,
               boxSizing: 'border-box', outline: 'none',
             }}
           />
         </div>

         {/* Body: sidebar + grid */}
         <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative', zIndex: 1 }}>
           {/* Categorías sidebar */}
           <nav
             data-testid="categorias-sidebar"
             style={{
               width: 200, flexShrink: 0, borderRight: '1px solid #1E3A5F',
               overflowY: 'auto', padding: '12px 0',
               backgroundColor: 'rgba(6,11,24,0.95)',
             }}
           >
             {CATEGORIAS.map((cat) => (
               <button
                 key={cat.id}
                 data-testid={`categoria-${cat.id}`}
                 onClick={() => setCategoriaActiva(cat.id)}
                 style={{
                   display: 'flex', alignItems: 'center', gap: 10,
                   width: '100%', padding: '8px 16px',
                   background: categoriaActiva === cat.id ? 'rgba(79,195,247,0.1)' : 'transparent',
                   border: 'none',
                   borderLeft: categoriaActiva === cat.id ? '2px solid #4FC3F7' : '2px solid transparent',
                   color: categoriaActiva === cat.id ? '#4FC3F7' : '#90CAF9',
                   cursor: 'pointer', fontSize: 13, textAlign: 'left',
                 }}
               >
                 <span style={{ fontSize: 16 }}>{cat.icono}</span>
                 <span>{cat.label}</span>
               </button>
             ))}
           </nav>

           {/* Grid de cards */}
           <main
             data-testid="nodos-grid"
             style={{
               flex: 1, overflowY: 'auto', padding: 20,
               display: 'grid',
               gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
               gap: 16, alignContent: 'start',
             }}
           >
             {nodosFiltrados.map((nodo) => (
               <div
                 key={nodo.id}
                 data-testid={`node-card-${nodo.id}`}
                 style={{
                   backgroundColor: '#0A0E1A', borderRadius: 10,
                   border: '1px solid #1E3A5F',
                   padding: 16, display: 'flex', flexDirection: 'column', gap: 10,
                   transition: 'border-color 200ms',
                 }}
               >
                 {/* Header de la card */}
                 <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                   <div style={{
                     width: 48, height: 48, borderRadius: 10,
                     backgroundColor: '#1565C0',
                     display: 'flex', alignItems: 'center', justifyContent: 'center',
                     fontSize: 24, flexShrink: 0,
                   }}>
                     {nodo.icono}
                   </div>
                   <div style={{ flex: 1, minWidth: 0 }}>
                     <div style={{ color: '#E0F7FA', fontWeight: 600, fontSize: 14, marginBottom: 2 }}>
                       {nodo.nombre}
                     </div>
                     <div style={{ color: '#607D8B', fontSize: 11 }}>
                       por {nodo.autor}
                     </div>
                   </div>
                   {/* Zona de seguridad */}
                   <div
                     data-testid={`zona-${nodo.id}`}
                     title={`Zona ${ZONA_LABEL[nodo.zona_seguridad]}`}
                     style={{ fontSize: 18, flexShrink: 0, cursor: 'help' }}
                   >
                     {ZONA_EMOJI[nodo.zona_seguridad]}
                   </div>
                 </div>

                 {/* Descripción */}
                 <div style={{ color: '#90CAF9', fontSize: 12, lineHeight: 1.5 }}>
                   {nodo.descripcion}
                 </div>

                 {/* Permisos si zona amarilla/roja */}
                 {nodo.zona_seguridad !== 'verde' && nodo.permisos.length > 0 && (
                   <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                     {nodo.permisos.slice(0, 3).map((p) => (
                       <span key={p} style={{
                         fontSize: 10, padding: '2px 6px', borderRadius: 4,
                         backgroundColor: '#1A2030', color: '#78909C',
                         border: '1px solid #1E3A5F',
                       }}>
                         {p}
                       </span>
                     ))}
                   </div>
                 )}

                 {/* Stats */}
                 <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: '#607D8B' }}>
                   <span>{renderStars(nodo.rating)}</span>
                   <span>{nodo.rating.toFixed(1)}</span>
                   <span>•</span>
                   <span>{nodo.descargas.toLocaleString()} descargas</span>
                 </div>

                 {/* Botón instalar */}
                 <button
                   data-testid={`instalar-btn-${nodo.id}`}
                   onClick={() => !nodo.instalado && onInstalar?.(nodo.id)}
                   disabled={nodo.instalado || instalandoId === nodo.id}
                   style={{
                     backgroundColor: nodo.instalado ? '#1B5E20' : '#1565C0',
                     border: `1px solid ${nodo.instalado ? '#2E7D32' : '#4FC3F7'}`,
                     color: nodo.instalado ? '#A5D6A7' : '#E0F7FA',
                     borderRadius: 6, padding: '8px 0', cursor: nodo.instalado ? 'default' : 'pointer',
                     fontWeight: 600, fontSize: 13, width: '100%',
                     opacity: instalandoId === nodo.id ? 0.6 : 1,
                   }}
                 >
                   {instalandoId === nodo.id ? '⏳ Instalando...' : nodo.instalado ? '✓ Instalado' : 'Instalar'}
                 </button>
               </div>
             ))}

             {nodosFiltrados.length === 0 && (
               <div style={{ color: '#37474F', fontSize: 14, gridColumn: '1/-1', textAlign: 'center', paddingTop: 60 }}>
                 No se encontraron nodos
               </div>
             )}
           </main>
         </div>
       </div>
     )
   }

4. Crear archivo tests/test_store_api.py:

   Ruta: ~/yeyo-os/tests/test_store_api.py
   Contenido:

   """
   Tests para YEYO Store API — Micro-fase 7.15
   """

   import zipfile
   import hashlib
   import json
   import tempfile
   from pathlib import Path
   from unittest.mock import patch, MagicMock, AsyncMock

   import pytest
   from fastapi.testclient import TestClient
   from fastapi import FastAPI


   @pytest.fixture
   def registry_vacio(tmp_path, monkeypatch):
       """Registry con directorio temporal vacío."""
       monkeypatch.setattr("src.store.node_registry.NodeRegistry.INSTALL_DIR", tmp_path / "nodes")
       monkeypatch.setattr("src.store.node_registry.NodeRegistry.REGISTRY_FILE", tmp_path / "registry.json")
       from src.store.node_registry import NodeRegistry
       return NodeRegistry()


   @pytest.fixture
   def client(registry_vacio, monkeypatch):
       """Cliente de test con registry vacío."""
       import src.store.store_api as store_api_module
       monkeypatch.setattr(store_api_module, "_registry", registry_vacio)
       app = FastAPI()
       from src.store.store_api import router
       app.include_router(router)
       return TestClient(app), registry_vacio


   def crear_ypkg_valido(tmp_path: Path, node_id: str = "test-node") -> tuple[Path, str]:
       """Crea un .ypkg válido y retorna (ruta, checksum)."""
       ypkg_path = tmp_path / f"{node_id}.ypkg"
       manifest = {
           "id": node_id,
           "nombre": "Test Node",
           "version": "1.0.0",
           "grafo": {"nodos": [], "aristas": []},
       }
       with zipfile.ZipFile(ypkg_path, "w") as zf:
           zf.writestr("manifest.json", json.dumps(manifest))
           zf.writestr("node.py", "# Test node")
       checksum = hashlib.sha256(ypkg_path.read_bytes()).hexdigest()
       return ypkg_path, checksum


   def test_listar_nodos_vacio(client):
       tc, _ = client
       response = tc.get("/api/store/nodes")
       assert response.status_code == 200
       assert response.json() == []


   def test_listar_nodos_con_datos(client, tmp_path):
       tc, registry = client
       from src.store.node_registry import NodeRegistryEntry
       entry = NodeRegistryEntry(
           id="img-node", nombre="Image Node", version="1.0", autor="YEYO",
           descripcion="Genera imágenes", icono="🎨", categoria="Creativo",
           zona_seguridad="verde", permisos=[], checksum="abc", url_descarga="http://x",
       )
       registry.registrar_nodo(entry)
       response = tc.get("/api/store/nodes")
       assert response.status_code == 200
       data = response.json()
       assert len(data) == 1
       assert data[0]["id"] == "img-node"


   def test_filtrar_por_categoria(client):
       tc, registry = client
       from src.store.node_registry import NodeRegistryEntry
       for cat, node_id in [("Creativo", "img"), ("Dev", "code")]:
           registry.registrar_nodo(NodeRegistryEntry(
               id=node_id, nombre=node_id, version="1.0", autor="YEYO",
               descripcion="Test", icono="📦", categoria=cat,
               zona_seguridad="verde", permisos=[], checksum="x", url_descarga="http://x",
           ))
       response = tc.get("/api/store/nodes?categoria=Dev")
       assert len(response.json()) == 1
       assert response.json()[0]["id"] == "code"


   def test_obtener_nodo_inexistente(client):
       tc, _ = client
       response = tc.get("/api/store/nodes/inexistente")
       assert response.status_code == 404


   def test_instalar_nodo_checksum_invalido(client, tmp_path):
       tc, registry = client
       from src.store.node_registry import NodeRegistryEntry
       registry.registrar_nodo(NodeRegistryEntry(
           id="bad-node", nombre="Bad Node", version="1.0", autor="YEYO",
           descripcion="Test", icono="📦", categoria="Dev",
           zona_seguridad="verde", permisos=[], checksum="checksum_incorrecto", url_descarga="http://x",
       ))
       ypkg_path, _ = crear_ypkg_valido(tmp_path, "bad-node")
       with patch("httpx.AsyncClient") as mock_client:
           mock_response = MagicMock()
           mock_response.content = ypkg_path.read_bytes()
           mock_response.raise_for_status = MagicMock()
           mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
           mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
           response = tc.post("/api/store/install/bad-node")
       assert response.status_code == 422
       assert "checksum" in response.json()["detail"].lower()


   def test_instalar_nodo_exitoso(client, tmp_path):
       tc, registry = client
       ypkg_path, checksum = crear_ypkg_valido(tmp_path, "good-node")
       from src.store.node_registry import NodeRegistryEntry
       registry.registrar_nodo(NodeRegistryEntry(
           id="good-node", nombre="Good Node", version="1.0", autor="YEYO",
           descripcion="Test", icono="📦", categoria="Dev",
           zona_seguridad="verde", permisos=[], checksum=checksum, url_descarga="http://x",
       ))
       with patch("httpx.AsyncClient") as mock_client:
           mock_response = MagicMock()
           mock_response.content = ypkg_path.read_bytes()
           mock_response.raise_for_status = MagicMock()
           mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_response)))
           mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
           with patch("src.store.store_api.GrafoValidador", create=True):
               response = tc.post("/api/store/install/good-node")
       assert response.status_code == 200
       assert response.json()["ok"] is True


   def test_listar_instalados(client, tmp_path):
       tc, registry = client
       from src.store.node_registry import NodeRegistryEntry
       registry.registrar_nodo(NodeRegistryEntry(
           id="installed", nombre="Installed", version="1.0", autor="YEYO",
           descripcion="Test", icono="📦", categoria="Dev",
           zona_seguridad="verde", permisos=[], checksum="x", url_descarga="http://x",
       ))
       registry.marcar_instalado("installed", "1.0")
       response = tc.get("/api/store/installed")
       assert "installed" in response.json()


   def test_node_registry_checksum():
       """Verifica que NodeRegistry.calcular_checksum retorna SHA-256 válido."""
       import tempfile, os
       from src.store.node_registry import NodeRegistry
       with tempfile.NamedTemporaryFile(delete=False) as f:
           f.write(b"test content")
           fname = f.name
       try:
           checksum = NodeRegistry.calcular_checksum(Path(fname))
           assert len(checksum) == 64
           assert checksum == hashlib.sha256(b"test content").hexdigest()
       finally:
           os.unlink(fname)

5. Crear archivo frontend/src/__tests__/store/StoreUI.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/store/StoreUI.test.tsx
   Contenido:

   /**
    * Tests para StoreUI — Micro-fase 7.15
    */

   import React from 'react'
   import { render, screen, fireEvent } from '@testing-library/react'
   import { StoreUI, StoreNodeCard } from '../../components/store/StoreUI'

   jest.mock('pixi.js', () => ({
     Application: jest.fn().mockImplementation(() => ({
       init: jest.fn().mockResolvedValue(undefined),
       destroy: jest.fn(),
       screen: { width: 800, height: 600 },
       stage: { addChild: jest.fn() },
       ticker: { add: jest.fn() },
       canvas: document.createElement('canvas'),
     })),
   }))

   const NODOS_MOCK: StoreNodeCard[] = [
     {
       id: 'img', nombre: 'Image Node', descripcion: 'Genera imágenes con IA',
       icono: '🎨', categoria: 'Creativo', zona_seguridad: 'verde',
       permisos: [], rating: 4.5, descargas: 1200, autor: 'YEYO', instalado: false,
     },
     {
       id: 'browser', nombre: 'Browser Node', descripcion: 'Navega la web',
       icono: '🌐', categoria: 'Internet', zona_seguridad: 'amarilla',
       permisos: ['internet.read', 'dom.screenshot'], rating: 3.8, descargas: 800, autor: 'YEYO', instalado: false,
     },
     {
       id: 'sys', nombre: 'App Installer', descripcion: 'Instala apps del sistema',
       icono: '📦', categoria: 'Sistema', zona_seguridad: 'roja',
       permisos: ['system.install', 'filesystem.write'], rating: 4.0, descargas: 500, autor: 'YEYO', instalado: true,
     },
   ]

   describe('StoreUI', () => {
     it('renderiza sin errores', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('store-ui')).toBeInTheDocument()
     })

     it('muestra barra de búsqueda', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('store-search')).toBeInTheDocument()
     })

     it('muestra sidebar de categorías', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('categorias-sidebar')).toBeInTheDocument()
     })

     it('muestra todos los nodos por defecto', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('node-card-img')).toBeInTheDocument()
       expect(screen.getByTestId('node-card-browser')).toBeInTheDocument()
       expect(screen.getByTestId('node-card-sys')).toBeInTheDocument()
     })

     it('muestra zona de seguridad en cada card', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('zona-img')).toHaveTextContent('🟢')
       expect(screen.getByTestId('zona-browser')).toHaveTextContent('🟡')
       expect(screen.getByTestId('zona-sys')).toHaveTextContent('🔴')
     })

     it('filtra por categoría al hacer click', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       fireEvent.click(screen.getByTestId('categoria-Creativo'))
       expect(screen.getByTestId('node-card-img')).toBeInTheDocument()
       expect(screen.queryByTestId('node-card-browser')).not.toBeInTheDocument()
     })

     it('filtra por búsqueda de texto', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       fireEvent.change(screen.getByTestId('store-search'), { target: { value: 'Browser' } })
       expect(screen.queryByTestId('node-card-img')).not.toBeInTheDocument()
       expect(screen.getByTestId('node-card-browser')).toBeInTheDocument()
     })

     it('nodo instalado muestra "✓ Instalado"', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('instalar-btn-sys')).toHaveTextContent('✓ Instalado')
     })

     it('nodo no instalado muestra "Instalar"', () => {
       render(<StoreUI nodos={NODOS_MOCK} />)
       expect(screen.getByTestId('instalar-btn-img')).toHaveTextContent('Instalar')
     })

     it('llama onInstalar al hacer click en Instalar', () => {
       const onInstalar = jest.fn().mockResolvedValue(undefined)
       render(<StoreUI nodos={NODOS_MOCK} onInstalar={onInstalar} />)
       fireEvent.click(screen.getByTestId('instalar-btn-img'))
       expect(onInstalar).toHaveBeenCalledWith('img')
     })

     it('NO llama onInstalar si el nodo ya está instalado', () => {
       const onInstalar = jest.fn()
       render(<StoreUI nodos={NODOS_MOCK} onInstalar={onInstalar} />)
       fireEvent.click(screen.getByTestId('instalar-btn-sys'))
       expect(onInstalar).not.toHaveBeenCalled()
     })
   })

VERIFICAR:
- [ ] src/store/node_registry.py — NodeRegistryEntry dataclass con todos los campos, NodeRegistry con CRUD
- [ ] NodeRegistry.calcular_checksum(path) retorna SHA-256 hexdigest de 64 chars
- [ ] src/store/store_api.py — GET /api/store/nodes, GET /api/store/nodes/{id}, POST /api/store/install/{id}, GET /api/store/installed
- [ ] Instalación valida checksum antes de extraer
- [ ] Instalación valida manifest.json tiene campos requeridos (id, nombre, version, grafo)
- [ ] StoreUI.tsx muestra categorías sidebar, barra de búsqueda, grid de cards
- [ ] Cards muestran 🟢/🟡/🔴 según zona_seguridad
- [ ] Botón muestra "✓ Instalado" si ya instalado, "Instalar" si no
- [ ] Tests pytest pasan: test_store_api.py (9 tests)
- [ ] Tests Jest pasan: StoreUI.test.tsx (11 tests)

SI FALLA:
- GrafoValidador no existe en src/core/: el store_api lo importa dentro de try/except — fallará silenciosamente
- httpx no instalado: pip install httpx
- NodeRegistry._cargar_registry falla: verificar que el archivo registry.json existe o manejar FileNotFoundError
- Tests de instalación async: usar patch("httpx.AsyncClient") con AsyncMock
- Categoría sidebar no filtra: verificar que nodo.categoria coincide exactamente con cat.id

NO HACER:
- No implementar pagos o monetización en el Store
- No implementar reviews de usuarios en esta micro-fase
- No ejecutar el código del nodo durante la instalación — solo extraer archivos
- No conectar con un servidor Store real — usar el registry local con seed data para tests
- No mostrar detalles del grafo en la UI del Store — solo el manifest básico

GATE Store: Store muestra nodos con zona de seguridad (🟢/🟡/🔴), instalación descarga .ypkg, valida checksum SHA-256, valida manifest.json y grafo, instala en ~/.yeyo/nodes/, nodo aparece en lista de instalados. UI filtra por categoría y búsqueda. Todos los tests pasan.
```
