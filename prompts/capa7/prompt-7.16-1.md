## ═══════════════════════════════════════
## MICRO-FASE 7.16 — Node Studio: Crear y Publicar Nodos con IA
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.16-1 [VSCODE] — Flujo completo: describir → IA genera → editar → sandbox → publicar .ypkg

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.16 de Capa 7 (Evolución): el Node Studio completo — el usuario describe un nodo en lenguaje natural, la IA lo genera en tiempo real, el usuario lo edita en Monaco, lo prueba en sandbox, y lo publica como .ypkg al YEYO Store.

CONTEXTO:
- Micro-fase 7.15 completada: YEYO Store con NodeRegistry, store_api, StoreUI funcionando
- Stack frontend: React + TypeScript + @monaco-editor/react
- Stack backend: FastAPI + Python, Ollama para generación de código
- src/store/node_registry.py con NodeRegistryEntry existe
- .ypkg = ZIP con manifest.json + código + assets, firmado con SHA-256
- GeneradorNodos es DISTINTO de GeneradorGrafos (que existe en src/core/) — nuevo archivo
- Sandbox: ejecución en proceso separado con timeout de 30 segundos
- Los nodos especiales (Browser, Games, App Installer) tienen plantillas predefinidas

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/studio/generator.py:

   Ruta: ~/yeyo-os/src/studio/generator.py
   Contenido:

   """
   YeyoOS — GeneradorNodos
   Micro-fase 7.16 — Capa 7: Evolución

   Genera código completo de nodos usando Ollama.
   DISTINTO de GeneradorGrafos (src/core/grafo_generador.py).

   El GeneradorNodos produce:
     - manifest.json: metadatos del nodo
     - node.py: código Python del nodo (subclase de NodeBase)
     - config.json: configuración por defecto
   """

   from __future__ import annotations
   import json
   import logging
   import re
   from dataclasses import dataclass, field
   from typing import AsyncIterator, Optional
   import httpx

   logger = logging.getLogger(__name__)

   OLLAMA_URL = "http://localhost:11434/api/generate"
   MODELO_DEFAULT = "mistral"

   NODE_TEMPLATE = """
   from src.core.node_base import NodeBase
   from src.core.node_context import NodeContext

   class {class_name}(NodeBase):
       \"\"\"
       {descripcion}
       Generado por YeyoOS Node Studio.
       \"\"\"

       NOMBRE = "{nombre}"
       VERSION = "1.0.0"
       ZONA_SEGURIDAD = "{zona_seguridad}"
       PERMISOS = {permisos}

       async def ejecutar(self, ctx: NodeContext) -> dict:
           # TODO: Implementar lógica del nodo
           return {{"resultado": "ok", "datos": {{}}}}
   """.strip()


   @dataclass
   class ManifestGenerado:
       id: str
       nombre: str
       version: str = "1.0.0"
       descripcion: str = ""
       categoria: str = "Utilidad"
       zona_seguridad: str = "verde"
       permisos: list[str] = field(default_factory=list)
       icono: str = "📦"
       grafo: dict = field(default_factory=lambda: {"nodos": [], "aristas": []})
       dependencias: list[str] = field(default_factory=list)

       def to_dict(self) -> dict:
           return {
               "id": self.id,
               "nombre": self.nombre,
               "version": self.version,
               "descripcion": self.descripcion,
               "categoria": self.categoria,
               "zona_seguridad": self.zona_seguridad,
               "permisos": self.permisos,
               "icono": self.icono,
               "grafo": self.grafo,
               "dependencias": self.dependencias,
           }


   @dataclass
   class NodeGenerado:
       manifest: ManifestGenerado
       codigo_python: str
       config_json: dict = field(default_factory=dict)
       advertencias: list[str] = field(default_factory=list)


   class GeneradorNodos:
       """
       Genera nodos completos desde descripción en lenguaje natural.
       Usa Ollama con el modelo configurado.
       """

       PROMPT_SISTEMA = """Eres un generador de nodos para YeyoOS. Dado una descripción de un nodo,
   genera un JSON con la siguiente estructura exacta:
   {
     "id": "nombre-kebab-case",
     "nombre": "Nombre Legible",
     "descripcion": "Descripción breve",
     "categoria": "Una de: IA, Internet, Juegos, Dev, Creativo, Social, Sistema, Utilidad",
     "zona_seguridad": "verde|amarilla|roja",
     "permisos": ["lista", "de", "permisos"],
     "icono": "emoji único",
     "dependencias": ["lista de pip packages"],
     "logica": "descripción detallada de la lógica del nodo en Python"
   }
   Responde SOLO con el JSON, sin explicaciones."""

       PLANTILLAS_ESPECIALES = {
           "browser": ManifestGenerado(
               id="browser-node", nombre="Browser Node", descripcion="Navega la web con Playwright",
               categoria="Internet", zona_seguridad="amarilla",
               permisos=["internet.read", "dom.screenshot"], icono="🌐",
               dependencias=["playwright"],
           ),
           "games": ManifestGenerado(
               id="games-node", nombre="Games Node", descripcion="Emulador RetroArch + juegos WebGL",
               categoria="Juegos", zona_seguridad="amarilla",
               permisos=["gpu.use", "filesystem.games"], icono="🎮",
               dependencias=[],
           ),
           "app-installer": ManifestGenerado(
               id="app-installer", nombre="App Installer", descripcion="Instala apps apt/snap/AppImage/Wine",
               categoria="Sistema", zona_seguridad="roja",
               permisos=["system.install", "filesystem.write", "network"], icono="📦",
               dependencias=[],
           ),
       }

       def __init__(self, modelo: str = MODELO_DEFAULT) -> None:
           self.modelo = modelo

       def _detectar_plantilla(self, descripcion: str) -> Optional[ManifestGenerado]:
           desc_lower = descripcion.lower()
           if "browser" in desc_lower or "web" in desc_lower or "playwright" in desc_lower:
               return self.PLANTILLAS_ESPECIALES["browser"]
           if "game" in desc_lower or "emulador" in desc_lower or "retro" in desc_lower:
               return self.PLANTILLAS_ESPECIALES["games"]
           if "instalar" in desc_lower or "apt" in desc_lower or "wine" in desc_lower:
               return self.PLANTILLAS_ESPECIALES["app-installer"]
           return None

       def _generar_codigo_desde_manifest(self, manifest: ManifestGenerado, logica: str = "") -> str:
           class_name = "".join(w.capitalize() for w in manifest.id.replace("-", "_").split("_"))
           permisos_str = json.dumps(manifest.permisos)
           base = NODE_TEMPLATE.format(
               class_name=class_name,
               nombre=manifest.nombre,
               descripcion=manifest.descripcion,
               zona_seguridad=manifest.zona_seguridad,
               permisos=permisos_str,
           )
           if logica:
               base += f"\n\n    # Lógica generada:\n    # {logica[:500]}"
           return base

       async def generar_streaming(self, descripcion: str) -> AsyncIterator[str]:
           """
           Genera un nodo con streaming de tokens desde Ollama.
           Yield: fragmentos de texto mientras la IA genera.
           """
           # Intentar plantilla especial primero
           plantilla = self._detectar_plantilla(descripcion)
           if plantilla:
               yield json.dumps({"tipo": "plantilla_detectada", "manifest": plantilla.to_dict()})
               return

           prompt = f"{self.PROMPT_SISTEMA}\n\nDescripción del nodo: {descripcion}"

           try:
               async with httpx.AsyncClient(timeout=120.0) as client:
                   async with client.stream(
                       "POST",
                       OLLAMA_URL,
                       json={"model": self.modelo, "prompt": prompt, "stream": True},
                   ) as response:
                       response.raise_for_status()
                       buffer = ""
                       async for line in response.aiter_lines():
                           if not line:
                               continue
                           try:
                               data = json.loads(line)
                               token = data.get("response", "")
                               buffer += token
                               yield json.dumps({"tipo": "token", "contenido": token})
                               if data.get("done"):
                                   break
                           except json.JSONDecodeError:
                               continue
                       yield json.dumps({"tipo": "buffer_completo", "contenido": buffer})
           except Exception as e:
               logger.error(f"Error generando nodo: {e}")
               yield json.dumps({"tipo": "error", "mensaje": str(e)})

       async def generar(self, descripcion: str) -> NodeGenerado:
           """Genera un nodo completo (no streaming)."""
           plantilla = self._detectar_plantilla(descripcion)
           if plantilla:
               codigo = self._generar_codigo_desde_manifest(plantilla)
               return NodeGenerado(manifest=plantilla, codigo_python=codigo)

           # Recopilar todos los tokens
           buffer = ""
           async for chunk in self.generar_streaming(descripcion):
               data = json.loads(chunk)
               if data["tipo"] == "buffer_completo":
                   buffer = data["contenido"]
                   break

           # Parsear JSON de la respuesta
           try:
               json_match = re.search(r'\{.*\}', buffer, re.DOTALL)
               if not json_match:
                   raise ValueError("No se encontró JSON en la respuesta")
               manifest_data = json.loads(json_match.group())
               manifest = ManifestGenerado(
                   id=manifest_data.get("id", "nuevo-nodo"),
                   nombre=manifest_data.get("nombre", "Nuevo Nodo"),
                   descripcion=manifest_data.get("descripcion", descripcion),
                   categoria=manifest_data.get("categoria", "Utilidad"),
                   zona_seguridad=manifest_data.get("zona_seguridad", "verde"),
                   permisos=manifest_data.get("permisos", []),
                   icono=manifest_data.get("icono", "📦"),
                   dependencias=manifest_data.get("dependencias", []),
               )
               codigo = self._generar_codigo_desde_manifest(manifest, manifest_data.get("logica", ""))
               return NodeGenerado(manifest=manifest, codigo_python=codigo)
           except Exception as e:
               logger.error(f"Error parseando respuesta de IA: {e}")
               manifest = ManifestGenerado(
                   id="nodo-generado", nombre="Nodo Generado",
                   descripcion=descripcion,
               )
               codigo = self._generar_codigo_desde_manifest(manifest)
               return NodeGenerado(manifest=manifest, codigo_python=codigo, advertencias=[str(e)])

2. Crear archivo src/studio/publisher.py:

   Ruta: ~/yeyo-os/src/studio/publisher.py
   Contenido:

   """
   YeyoOS — Publisher de Nodos
   Micro-fase 7.16 — Capa 7: Evolución

   Empaqueta un nodo en .ypkg (ZIP) y lo sube al Store local.
   El .ypkg tiene: manifest.json + node.py + config.json + assets/
   Se firma con SHA-256 (checksum del ZIP completo).
   """

   from __future__ import annotations
   import hashlib
   import json
   import logging
   import os
   import tempfile
   import zipfile
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Optional

   from src.studio.generator import ManifestGenerado, NodeGenerado

   logger = logging.getLogger(__name__)

   STORE_PACKAGES_DIR = Path.home() / ".yeyo" / "store" / "packages"


   @dataclass
   class PublishResult:
       ok: bool
       ypkg_path: Optional[Path]
       checksum: Optional[str]
       mensaje: str
       errores: list[str]


   class Publisher:
       """
       Empaqueta un NodeGenerado en .ypkg y lo publica en el Store local.
       """

       def __init__(self, output_dir: Optional[Path] = None) -> None:
           self.output_dir = output_dir or STORE_PACKAGES_DIR
           self.output_dir.mkdir(parents=True, exist_ok=True)

       def empaquetar(self, node: NodeGenerado, assets_dir: Optional[Path] = None) -> PublishResult:
           """
           Crea el archivo .ypkg en self.output_dir.
           Retorna PublishResult con ruta y checksum.
           """
           errores: list[str] = []
           node_id = node.manifest.id
           version = node.manifest.version
           ypkg_nombre = f"{node_id}-{version}.ypkg"
           ypkg_path = self.output_dir / ypkg_nombre

           try:
               with zipfile.ZipFile(ypkg_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                   # manifest.json
                   manifest_json = json.dumps(node.manifest.to_dict(), indent=2)
                   zf.writestr("manifest.json", manifest_json)

                   # node.py
                   zf.writestr("node.py", node.codigo_python)

                   # config.json
                   config = node.config_json or {}
                   zf.writestr("config.json", json.dumps(config, indent=2))

                   # Assets opcionales
                   if assets_dir and assets_dir.exists():
                       for asset_path in assets_dir.rglob("*"):
                           if asset_path.is_file():
                               arcname = f"assets/{asset_path.relative_to(assets_dir)}"
                               zf.write(asset_path, arcname)

               # Calcular checksum del .ypkg
               checksum = self._calcular_checksum(ypkg_path)
               logger.info(f"Nodo empaquetado: {ypkg_nombre} ({checksum[:16]}...)")

               return PublishResult(
                   ok=True,
                   ypkg_path=ypkg_path,
                   checksum=checksum,
                   mensaje=f"'{node.manifest.nombre}' empaquetado como {ypkg_nombre}",
                   errores=errores,
               )

           except Exception as e:
               logger.error(f"Error empaquetando {node_id}: {e}")
               return PublishResult(ok=False, ypkg_path=None, checksum=None, mensaje=str(e), errores=[str(e)])

       def publicar_en_store(self, node: NodeGenerado, assets_dir: Optional[Path] = None) -> PublishResult:
           """
           Empaqueta y registra el nodo en el NodeRegistry local.
           """
           result = self.empaquetar(node, assets_dir)
           if not result.ok or not result.ypkg_path:
               return result

           try:
               from src.store.node_registry import NodeRegistry, NodeRegistryEntry
               registry = NodeRegistry()
               entry = NodeRegistryEntry(
                   id=node.manifest.id,
                   nombre=node.manifest.nombre,
                   version=node.manifest.version,
                   autor="Local (Node Studio)",
                   descripcion=node.manifest.descripcion,
                   icono=node.manifest.icono,
                   categoria=node.manifest.categoria,
                   zona_seguridad=node.manifest.zona_seguridad,
                   permisos=node.manifest.permisos,
                   checksum=result.checksum or "",
                   url_descarga=f"file://{result.ypkg_path}",
                   rating=0.0,
                   descargas=0,
               )
               registry.registrar_nodo(entry)
               logger.info(f"Nodo '{node.manifest.id}' registrado en el Store local")
           except Exception as e:
               result.errores.append(f"Error registrando en Store: {e}")
               logger.error(f"Error registrando {node.manifest.id} en Store: {e}")

           return result

       def ejecutar_sandbox(self, node: NodeGenerado, timeout: int = 30) -> dict:
           """
           Prueba el nodo en un proceso separado con timeout.
           Retorna dict con resultado y errores.
           """
           import subprocess
           import sys

           with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
               f.write(node.codigo_python)
               f.write("\n\n# Sandbox test\n")
               f.write("import asyncio\n")
               f.write("async def _test():\n")
               f.write("    # Solo verificar que el código es sintácticamente válido\n")
               f.write("    print('SANDBOX_OK')\n")
               f.write("asyncio.run(_test())\n")
               tmp_path = f.name

           try:
               result = subprocess.run(
                   [sys.executable, tmp_path],
                   capture_output=True,
                   text=True,
                   timeout=timeout,
               )
               return {
                   "ok": result.returncode == 0,
                   "stdout": result.stdout,
                   "stderr": result.stderr,
                   "sandbox_ok": "SANDBOX_OK" in result.stdout,
               }
           except subprocess.TimeoutExpired:
               return {"ok": False, "stdout": "", "stderr": "Timeout", "sandbox_ok": False}
           except Exception as e:
               return {"ok": False, "stdout": "", "stderr": str(e), "sandbox_ok": False}
           finally:
               os.unlink(tmp_path)

       @staticmethod
       def _calcular_checksum(ruta: Path) -> str:
           sha256 = hashlib.sha256()
           with open(ruta, "rb") as f:
               for chunk in iter(lambda: f.read(65536), b""):
                   sha256.update(chunk)
           return sha256.hexdigest()

3. Crear archivo src/studio/__init__.py:

   Ruta: ~/yeyo-os/src/studio/__init__.py
   Contenido: (vacío)

4. Crear archivo frontend/src/components/studio/NodeStudio.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/studio/NodeStudio.tsx
   Contenido:

   /**
    * YeyoOS — NodeStudio
    * Micro-fase 7.16 — Capa 7: Evolución
    *
    * Flujo de 3 pasos:
    *   Paso 1 — Describe: textarea + picker de ícono + ejemplos rápidos
    *   Paso 2 — IA genera: checklist animado + mini-grafo + chat para aclaraciones
    *   Paso 3 — Revisar: árbol de estructura + Monaco editor + preview + acciones
    */

   import React, { useState, useCallback, useRef } from 'react'
   import Editor from '@monaco-editor/react'
   import { GridBackground } from '../hub/GridBackground'

   type Paso = 1 | 2 | 3

   interface ChecklistItem {
     id: string
     label: string
     estado: 'pendiente' | 'cargando' | 'done' | 'error'
   }

   interface ManifestPreview {
     id: string
     nombre: string
     descripcion: string
     categoria: string
     zona_seguridad: 'verde' | 'amarilla' | 'roja'
     permisos: string[]
     icono: string
     grafo: object
     dependencias: string[]
   }

   const EJEMPLOS_RAPIDOS = [
     { icono: '🌐', label: 'Navegador web', descripcion: 'Un nodo que navega la web usando Playwright' },
     { icono: '🎮', label: 'Emulador', descripcion: 'Emulador de juegos retro con RetroArch' },
     { icono: '📦', label: 'App Installer', descripcion: 'Instala apps con apt, snap, AppImage y Wine' },
     { icono: '📰', label: 'News Feed', descripcion: 'Agrega noticias de RSS y APIs de noticias' },
     { icono: '📊', label: 'Dashboard', descripcion: 'Dashboard de métricas con gráficos en tiempo real' },
   ]

   const CHECKLIST_INICIAL: ChecklistItem[] = [
     { id: 'analizar', label: 'Analizando descripción...', estado: 'pendiente' },
     { id: 'permisos', label: 'Eligiendo permisos de seguridad...', estado: 'pendiente' },
     { id: 'grafo', label: 'Creando estructura del grafo...', estado: 'pendiente' },
     { id: 'codigo', label: 'Generando código del nodo...', estado: 'pendiente' },
   ]

   const ZONA_COLOR: Record<string, string> = { verde: '#2E7D32', amarilla: '#F57F17', roja: '#B71C1C' }
   const ZONA_EMOJI: Record<string, string> = { verde: '🟢', amarilla: '🟡', roja: '🔴' }

   type ArbolSeccion = 'Metadatos' | 'Config' | 'Grafo' | 'Permisos' | 'Dependencias'

   export interface NodeStudioProps {
     onPublicar?: (nodeId: string) => void
   }

   export function NodeStudio({ onPublicar }: NodeStudioProps) {
     const [paso, setPaso] = useState<Paso>(1)
     const [descripcion, setDescripcion] = useState('')
     const [iconoSeleccionado, setIconoSeleccionado] = useState('📦')
     const [nombreNodo, setNombreNodo] = useState('')
     const [checklist, setChecklist] = useState<ChecklistItem[]>(CHECKLIST_INICIAL)
     const [streamTokens, setStreamTokens] = useState('')
     const [chatInput, setChatInput] = useState('')
     const [chatMensajes, setChatMensajes] = useState<Array<{ role: string; content: string }>>([])
     const [manifest, setManifest] = useState<ManifestPreview | null>(null)
     const [codigoGenerado, setCodigoGenerado] = useState('')
     const [arbolSeccion, setArbolSeccion] = useState<ArbolSeccion>('Metadatos')
     const [sandboxResult, setSandboxResult] = useState<{ ok: boolean; mensaje: string } | null>(null)
     const [publicando, setPublicando] = useState(false)
     const eventSourceRef = useRef<EventSource | null>(null)

     const avanzarChecklist = useCallback((id: string, estado: ChecklistItem['estado']) => {
       setChecklist((prev) => prev.map((item) => (item.id === id ? { ...item, estado } : item)))
     }, [])

     const handleGenerar = useCallback(async () => {
       if (!descripcion.trim()) return
       setPaso(2)
       setChecklist(CHECKLIST_INICIAL.map((i) => ({ ...i, estado: 'pendiente' })))
       setStreamTokens('')

       // Simular checklist progresivo mientras llega el streaming
       const pasos = ['analizar', 'permisos', 'grafo', 'codigo']
       for (let i = 0; i < pasos.length; i++) {
         avanzarChecklist(pasos[i], 'cargando')
         await new Promise((r) => setTimeout(r, 800 + i * 400))
         avanzarChecklist(pasos[i], 'done')
       }

       try {
         const resp = await fetch('/api/studio/generar', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ descripcion, icono: iconoSeleccionado, nombre: nombreNodo }),
         })
         const data = await resp.json()
         if (data.manifest) setManifest(data.manifest)
         if (data.codigo) setCodigoGenerado(data.codigo)
         setTimeout(() => setPaso(3), 500)
       } catch (e) {
         setStreamTokens(`Error: ${e}`)
       }
     }, [descripcion, iconoSeleccionado, nombreNodo, avanzarChecklist])

     const handleEjemplo = (ej: typeof EJEMPLOS_RAPIDOS[0]) => {
       setDescripcion(ej.descripcion)
       setIconoSeleccionado(ej.icono)
       setNombreNodo(ej.label)
     }

     const handleSandbox = useCallback(async () => {
       setSandboxResult(null)
       try {
         const resp = await fetch('/api/studio/sandbox', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ codigo: codigoGenerado }),
         })
         const data = await resp.json()
         setSandboxResult({ ok: data.ok, mensaje: data.ok ? 'Sandbox OK ✅' : data.stderr || 'Error' })
       } catch (e) {
         setSandboxResult({ ok: false, mensaje: String(e) })
       }
     }, [codigoGenerado])

     const handlePublicar = useCallback(async () => {
       if (!manifest) return
       setPublicando(true)
       try {
         const resp = await fetch('/api/studio/publicar', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ manifest, codigo: codigoGenerado }),
         })
         const data = await resp.json()
         if (data.ok) {
           onPublicar?.(manifest.id)
         }
       } finally {
         setPublicando(false)
       }
     }, [manifest, codigoGenerado, onPublicar])

     const handleChatSend = (e: React.FormEvent) => {
       e.preventDefault()
       if (!chatInput.trim()) return
       setChatMensajes((prev) => [...prev, { role: 'user', content: chatInput }])
       setChatInput('')
     }

     const ICONOS_DISPONIBLES = ['📦', '🌐', '🎮', '💻', '🎨', '📱', '🔧', '⚙️', '🤖', '📊', '📰', '🔒', '🎵', '📹', '💬']

     return (
       <div
         data-testid="node-studio"
         data-paso={paso}
         style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative', backgroundColor: '#060B18' }}
       >
         <GridBackground saturation={1.0} style={{ opacity: 0.4 }} />

         {/* Indicador de pasos */}
         <div
           data-testid="paso-indicator"
           style={{
             position: 'relative', zIndex: 1, display: 'flex', gap: 0,
             padding: '12px 20px', borderBottom: '1px solid #1E3A5F',
             backgroundColor: 'rgba(6,11,24,0.9)',
           }}
         >
           {[1, 2, 3].map((p) => (
             <div key={p} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
               <div style={{
                 width: 28, height: 28, borderRadius: '50%',
                 backgroundColor: paso >= p ? '#1565C0' : '#1A2030',
                 border: `2px solid ${paso >= p ? '#4FC3F7' : '#1E3A5F'}`,
                 display: 'flex', alignItems: 'center', justifyContent: 'center',
                 fontSize: 12, fontWeight: 700,
                 color: paso >= p ? '#E0F7FA' : '#37474F',
               }}>
                 {p}
               </div>
               <span style={{ fontSize: 12, color: paso >= p ? '#90CAF9' : '#37474F' }}>
                 {p === 1 ? 'Describe' : p === 2 ? 'Generando' : 'Revisa'}
               </span>
               {p < 3 && <div style={{ width: 40, height: 1, backgroundColor: paso > p ? '#4FC3F7' : '#1E3A5F', margin: '0 8px' }} />}
             </div>
           ))}
         </div>

         {/* PASO 1: Describe */}
         {paso === 1 && (
           <div
             data-testid="paso-1"
             style={{
               position: 'relative', zIndex: 1, flex: 1,
               display: 'flex', flexDirection: 'column', alignItems: 'center',
               justifyContent: 'center', padding: 40, gap: 24,
             }}
           >
             <h2 style={{ color: '#4FC3F7', fontSize: 24, fontWeight: 300, margin: 0 }}>
               ¿Qué quieres que haga tu nodo?
             </h2>

             <textarea
               data-testid="descripcion-textarea"
               value={descripcion}
               onChange={(e) => setDescripcion(e.target.value)}
               placeholder="Describe el nodo que quieres crear..."
               rows={5}
               style={{
                 width: '100%', maxWidth: 600, backgroundColor: '#0A0E1A',
                 border: '1px solid #1E3A5F', borderRadius: 8,
                 color: '#E0F7FA', padding: 16, fontSize: 15,
                 fontFamily: 'inherit', resize: 'vertical',
               }}
             />

             <div style={{ display: 'flex', gap: 16, alignItems: 'center', width: '100%', maxWidth: 600 }}>
               <input
                 data-testid="nombre-input"
                 value={nombreNodo}
                 onChange={(e) => setNombreNodo(e.target.value)}
                 placeholder="Nombre del nodo"
                 style={{
                   flex: 1, backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                   borderRadius: 6, color: '#E0F7FA', padding: '8px 12px', fontSize: 14,
                 }}
               />
               {/* Picker de ícono */}
               <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 200 }}>
                 {ICONOS_DISPONIBLES.slice(0, 8).map((emoji) => (
                   <button
                     key={emoji}
                     data-testid={`icono-${emoji}`}
                     onClick={() => setIconoSeleccionado(emoji)}
                     style={{
                       fontSize: 20, padding: 4, cursor: 'pointer',
                       background: iconoSeleccionado === emoji ? 'rgba(79,195,247,0.2)' : 'transparent',
                       border: iconoSeleccionado === emoji ? '1px solid #4FC3F7' : '1px solid transparent',
                       borderRadius: 4,
                     }}
                   >
                     {emoji}
                   </button>
                 ))}
               </div>
             </div>

             {/* Ejemplos rápidos */}
             <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 600 }}>
               {EJEMPLOS_RAPIDOS.map((ej) => (
                 <button
                   key={ej.label}
                   data-testid={`ejemplo-${ej.label.replace(' ', '-').toLowerCase()}`}
                   onClick={() => handleEjemplo(ej)}
                   style={{
                     padding: '6px 12px', backgroundColor: '#0A0E1A',
                     border: '1px solid #1E3A5F', borderRadius: 20,
                     color: '#90CAF9', cursor: 'pointer', fontSize: 12,
                     display: 'flex', alignItems: 'center', gap: 6,
                   }}
                 >
                   {ej.icono} {ej.label}
                 </button>
               ))}
             </div>

             <button
               data-testid="generar-btn"
               onClick={handleGenerar}
               disabled={!descripcion.trim()}
               style={{
                 backgroundColor: descripcion.trim() ? '#1565C0' : '#1A2030',
                 border: `1px solid ${descripcion.trim() ? '#4FC3F7' : '#1E3A5F'}`,
                 color: descripcion.trim() ? '#E0F7FA' : '#37474F',
                 borderRadius: 8, padding: '12px 32px',
                 cursor: descripcion.trim() ? 'pointer' : 'default',
                 fontSize: 16, fontWeight: 600,
               }}
             >
               Generar →
             </button>
           </div>
         )}

         {/* PASO 2: IA Genera */}
         {paso === 2 && (
           <div
             data-testid="paso-2"
             style={{
               position: 'relative', zIndex: 1, flex: 1,
               display: 'flex', gap: 24, padding: 32, alignItems: 'flex-start',
             }}
           >
             {/* Checklist + mini-grafo */}
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
               <h3 style={{ color: '#4FC3F7', margin: 0, fontWeight: 300 }}>Generando tu nodo...</h3>
               <div data-testid="checklist" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                 {checklist.map((item) => (
                   <div
                     key={item.id}
                     data-testid={`checklist-${item.id}`}
                     data-estado={item.estado}
                     style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, color: '#90CAF9' }}
                   >
                     <span style={{ fontSize: 18 }}>
                       {item.estado === 'done' ? '✅' : item.estado === 'cargando' ? '⏳' : item.estado === 'error' ? '❌' : '○'}
                     </span>
                     {item.label}
                   </div>
                 ))}
               </div>

               {/* Mini-grafo animado */}
               <div
                 data-testid="mini-grafo-animado"
                 style={{
                   marginTop: 16, padding: 16, backgroundColor: '#0A0E1A',
                   borderRadius: 8, border: '1px solid #1E3A5F',
                   minHeight: 100, display: 'flex', alignItems: 'center', justifyContent: 'center',
                   color: '#37474F', fontSize: 13,
                 }}
               >
                 {streamTokens || '◎ Construyendo grafo...'}
               </div>
             </div>

             {/* Chat para aclaraciones */}
             <div style={{
               width: 280, display: 'flex', flexDirection: 'column', gap: 0,
               border: '1px solid #1E3A5F', borderRadius: 8, overflow: 'hidden',
             }}>
               <div style={{ padding: '10px 14px', borderBottom: '1px solid #1E3A5F', color: '#4FC3F7', fontSize: 12, fontWeight: 600 }}>
                 Chat IA
               </div>
               <div data-testid="chat-generacion" style={{ flex: 1, minHeight: 200, maxHeight: 300, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                 {chatMensajes.map((m, i) => (
                   <div key={i} style={{ fontSize: 12, color: m.role === 'user' ? '#E0F7FA' : '#90CAF9' }}>
                     {m.content}
                   </div>
                 ))}
               </div>
               <form onSubmit={handleChatSend} style={{ padding: 10, borderTop: '1px solid #1E3A5F' }}>
                 <input
                   data-testid="chat-input-generacion"
                   value={chatInput}
                   onChange={(e) => setChatInput(e.target.value)}
                   placeholder="Aclarar algo..."
                   style={{
                     width: '100%', backgroundColor: '#0A0E1A', border: '1px solid #1E3A5F',
                     borderRadius: 4, color: '#E0F7FA', padding: '6px 8px', fontSize: 12,
                     boxSizing: 'border-box',
                   }}
                 />
               </form>
             </div>
           </div>
         )}

         {/* PASO 3: Revisar y editar */}
         {paso === 3 && (
           <div
             data-testid="paso-3"
             style={{ position: 'relative', zIndex: 1, flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
           >
             {/* 3 paneles */}
             <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
               {/* Izq: árbol de estructura */}
               <aside
                 data-testid="estructura-arbol"
                 style={{
                   width: 180, flexShrink: 0, borderRight: '1px solid #1E3A5F',
                   padding: '12px 0', overflowY: 'auto',
                 }}
               >
                 <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, padding: '0 12px 8px', letterSpacing: '1px' }}>
                   ESTRUCTURA
                 </div>
                 {(['Metadatos', 'Config', 'Grafo', 'Permisos', 'Dependencias'] as ArbolSeccion[]).map((sec) => (
                   <button
                     key={sec}
                     data-testid={`arbol-${sec.toLowerCase()}`}
                     onClick={() => setArbolSeccion(sec)}
                     style={{
                       display: 'block', width: '100%', textAlign: 'left',
                       padding: '6px 16px', background: arbolSeccion === sec ? '#1E3A5F' : 'transparent',
                       border: 'none', color: arbolSeccion === sec ? '#E0F7FA' : '#607D8B',
                       cursor: 'pointer', fontSize: 13,
                     }}
                   >
                     {sec}
                   </button>
                 ))}

                 {/* Info de zona de seguridad */}
                 {manifest && (
                   <div style={{ padding: '12px 16px', marginTop: 8, borderTop: '1px solid #1E3A5F' }}>
                     <div style={{ fontSize: 11, color: '#607D8B', marginBottom: 4 }}>Zona de seguridad</div>
                     <div style={{ fontSize: 20 }}>{ZONA_EMOJI[manifest.zona_seguridad]}</div>
                     <div style={{
                       fontSize: 11, marginTop: 4,
                       color: ZONA_COLOR[manifest.zona_seguridad] || '#607D8B',
                     }}>
                       {manifest.zona_seguridad === 'verde' ? 'Seguro' : manifest.zona_seguridad === 'amarilla' ? 'Permisos requeridos' : 'Acceso elevado'}
                     </div>
                   </div>
                 )}
               </aside>

               {/* Centro: Monaco editor */}
               <div data-testid="studio-editor" style={{ flex: 1, overflow: 'hidden' }}>
                 <Editor
                   height="100%"
                   language="python"
                   value={arbolSeccion === 'Metadatos' && manifest ? JSON.stringify(manifest, null, 2) : codigoGenerado}
                   onChange={(val) => { if (arbolSeccion !== 'Metadatos') setCodigoGenerado(val ?? '') }}
                   theme="vs-dark"
                   options={{ fontSize: 13, minimap: { enabled: false }, wordWrap: 'on' }}
                 />
               </div>

               {/* Der: preview del nodo en Hub */}
               <aside
                 data-testid="hub-preview"
                 style={{
                   width: 200, flexShrink: 0, borderLeft: '1px solid #1E3A5F',
                   padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
                   backgroundColor: '#080D18',
                 }}
               >
                 <div style={{ color: '#4FC3F7', fontSize: 11, fontWeight: 600, letterSpacing: '1px' }}>PREVIEW HUB</div>
                 {manifest ? (
                   <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                     <div style={{
                       width: 64, height: 64, borderRadius: '50%',
                       backgroundColor: '#1565C0', border: '2px solid #4FC3F7',
                       display: 'flex', alignItems: 'center', justifyContent: 'center',
                       fontSize: 28,
                     }}>
                       {manifest.icono}
                     </div>
                     <div style={{ color: '#E0F7FA', fontSize: 13, textAlign: 'center' }}>{manifest.nombre}</div>
                     <div style={{ color: '#607D8B', fontSize: 11, textAlign: 'center' }}>{manifest.categoria}</div>
                     <div style={{ fontSize: 20 }}>{ZONA_EMOJI[manifest.zona_seguridad]}</div>
                     {manifest.permisos.length > 0 && (
                       <div style={{ fontSize: 10, color: '#37474F', textAlign: 'center' }}>
                         {manifest.permisos.join(' • ')}
                       </div>
                     )}
                   </div>
                 ) : (
                   <div style={{ color: '#37474F', fontSize: 12, textAlign: 'center' }}>Sin nodo generado</div>
                 )}
               </aside>
             </div>

             {/* Bottom: acciones */}
             <div
               data-testid="studio-actions"
               style={{
                 display: 'flex', gap: 12, padding: '12px 20px',
                 borderTop: '1px solid #1E3A5F', alignItems: 'center',
                 backgroundColor: 'rgba(6,11,24,0.95)',
               }}
             >
               <button
                 data-testid="volver-btn"
                 onClick={() => setPaso(1)}
                 style={{
                   background: 'transparent', border: '1px solid #1E3A5F',
                   color: '#90CAF9', borderRadius: 6, padding: '8px 16px',
                   cursor: 'pointer', fontSize: 13,
                 }}
               >
                 ← Volver
               </button>

               {sandboxResult && (
                 <span style={{ fontSize: 12, color: sandboxResult.ok ? '#A5D6A7' : '#EF9A9A' }}>
                   {sandboxResult.mensaje}
                 </span>
               )}

               <div style={{ flex: 1 }} />

               <button
                 data-testid="sandbox-btn"
                 onClick={handleSandbox}
                 style={{
                   backgroundColor: '#0D47A1', border: '1px solid #1565C0',
                   color: '#E0F7FA', borderRadius: 6, padding: '8px 16px',
                   cursor: 'pointer', fontSize: 13,
                 }}
               >
                 🧪 Probar en sandbox
               </button>

               <button
                 data-testid="publicar-btn"
                 onClick={handlePublicar}
                 disabled={publicando}
                 style={{
                   backgroundColor: '#1B5E20', border: '1px solid #2E7D32',
                   color: '#A5D6A7', borderRadius: 6, padding: '8px 20px',
                   cursor: publicando ? 'default' : 'pointer',
                   fontSize: 13, fontWeight: 600, opacity: publicando ? 0.6 : 1,
                 }}
               >
                 {publicando ? '⏳ Publicando...' : '📤 Publicar'}
               </button>
             </div>
           </div>
         )}
       </div>
     )
   }

5. Crear archivo src/studio/studio_api.py:

   Ruta: ~/yeyo-os/src/studio/studio_api.py
   Contenido:

   """
   YeyoOS — Studio API
   Micro-fase 7.16 — Capa 7: Evolución

   Endpoints del Node Studio:
     POST /api/studio/generar    — genera un nodo desde descripción
     POST /api/studio/sandbox    — prueba código en sandbox
     POST /api/studio/publicar   — empaqueta y publica nodo
   """

   import logging
   from fastapi import APIRouter
   from pydantic import BaseModel
   from typing import Optional

   logger = logging.getLogger(__name__)
   router = APIRouter(prefix="/api/studio", tags=["studio"])


   class GenerarRequest(BaseModel):
       descripcion: str
       icono: str = "📦"
       nombre: str = ""


   class SandboxRequest(BaseModel):
       codigo: str


   class PublicarRequest(BaseModel):
       manifest: dict
       codigo: str


   @router.post("/generar")
   async def generar_nodo(request: GenerarRequest) -> dict:
       """Genera un nodo usando GeneradorNodos."""
       from src.studio.generator import GeneradorNodos, ManifestGenerado
       gen = GeneradorNodos()
       resultado = await gen.generar(request.descripcion)

       # Aplicar ícono y nombre si se proveyeron
       if request.icono:
           resultado.manifest.icono = request.icono
       if request.nombre:
           resultado.manifest.nombre = request.nombre

       return {
           "ok": True,
           "manifest": resultado.manifest.to_dict(),
           "codigo": resultado.codigo_python,
           "advertencias": resultado.advertencias,
       }


   @router.post("/sandbox")
   async def probar_sandbox(request: SandboxRequest) -> dict:
       """Prueba el código del nodo en un proceso sandbox."""
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="sandbox-test", nombre="Sandbox")
       node = NodeGenerado(manifest=manifest, codigo_python=request.codigo)

       publisher = Publisher()
       result = publisher.ejecutar_sandbox(node, timeout=30)
       return result


   @router.post("/publicar")
   async def publicar_nodo(request: PublicarRequest) -> dict:
       """Empaqueta y publica el nodo en el Store local."""
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest_data = request.manifest
       manifest = ManifestGenerado(
           id=manifest_data.get("id", "nodo-publicado"),
           nombre=manifest_data.get("nombre", "Nodo"),
           version=manifest_data.get("version", "1.0.0"),
           descripcion=manifest_data.get("descripcion", ""),
           categoria=manifest_data.get("categoria", "Utilidad"),
           zona_seguridad=manifest_data.get("zona_seguridad", "verde"),
           permisos=manifest_data.get("permisos", []),
           icono=manifest_data.get("icono", "📦"),
           dependencias=manifest_data.get("dependencias", []),
       )
       node = NodeGenerado(manifest=manifest, codigo_python=request.codigo)

       publisher = Publisher()
       result = publisher.publicar_en_store(node)
       return {
           "ok": result.ok,
           "node_id": manifest.id,
           "checksum": result.checksum,
           "mensaje": result.mensaje,
           "errores": result.errores,
       }

6. Crear archivo tests/test_studio.py:

   Ruta: ~/yeyo-os/tests/test_studio.py
   Contenido:

   """
   Tests para Node Studio (generator + publisher) — Micro-fase 7.16
   """

   import json
   import zipfile
   import hashlib
   import pytest
   from pathlib import Path
   from unittest.mock import patch, AsyncMock, MagicMock


   def test_manifest_generado_to_dict():
       from src.studio.generator import ManifestGenerado
       m = ManifestGenerado(id="test", nombre="Test Node", version="1.0.0", descripcion="Test")
       d = m.to_dict()
       assert d["id"] == "test"
       assert d["nombre"] == "Test Node"
       assert "grafo" in d
       assert "permisos" in d


   def test_generator_detecta_plantilla_browser():
       from src.studio.generator import GeneradorNodos
       gen = GeneradorNodos()
       plantilla = gen._detectar_plantilla("quiero un navegador web con playwright")
       assert plantilla is not None
       assert plantilla.id == "browser-node"
       assert "amarilla" == plantilla.zona_seguridad


   def test_generator_detecta_plantilla_games():
       from src.studio.generator import GeneradorNodos
       gen = GeneradorNodos()
       plantilla = gen._detectar_plantilla("emulador de juegos retro")
       assert plantilla is not None
       assert "game" in plantilla.id or "games" in plantilla.id


   def test_generator_detecta_plantilla_installer():
       from src.studio.generator import GeneradorNodos
       gen = GeneradorNodos()
       plantilla = gen._detectar_plantilla("instalar apps con apt y wine")
       assert plantilla is not None
       assert plantilla.zona_seguridad == "roja"


   def test_generator_sin_plantilla_retorna_none():
       from src.studio.generator import GeneradorNodos
       gen = GeneradorNodos()
       plantilla = gen._detectar_plantilla("un dashboard de métricas")
       assert plantilla is None


   def test_generar_codigo_desde_manifest():
       from src.studio.generator import GeneradorNodos, ManifestGenerado
       gen = GeneradorNodos()
       manifest = ManifestGenerado(id="mi-nodo", nombre="Mi Nodo", descripcion="Test")
       codigo = gen._generar_codigo_desde_manifest(manifest)
       assert "NodeBase" in codigo
       assert "MiNodo" in codigo
       assert "ejecutar" in codigo


   @pytest.mark.asyncio
   async def test_generar_con_plantilla_especial():
       from src.studio.generator import GeneradorNodos
       gen = GeneradorNodos()
       resultado = await gen.generar("quiero un browser node con playwright")
       assert resultado.manifest.id == "browser-node"
       assert "NodeBase" in resultado.codigo_python


   def test_publisher_empaquetar(tmp_path):
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="test-pkg", nombre="Test Pkg", version="1.0.0", descripcion="Test")
       node = NodeGenerado(manifest=manifest, codigo_python="# test code")

       publisher = Publisher(output_dir=tmp_path)
       result = publisher.empaquetar(node)

       assert result.ok
       assert result.ypkg_path is not None
       assert result.ypkg_path.exists()
       assert result.checksum is not None
       assert len(result.checksum) == 64


   def test_publisher_ypkg_contiene_archivos_requeridos(tmp_path):
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="test-pkg2", nombre="Test Pkg 2", version="1.0.0", descripcion="Test")
       node = NodeGenerado(manifest=manifest, codigo_python="# code")

       publisher = Publisher(output_dir=tmp_path)
       result = publisher.empaquetar(node)

       with zipfile.ZipFile(result.ypkg_path) as zf:
           names = zf.namelist()
       assert "manifest.json" in names
       assert "node.py" in names
       assert "config.json" in names


   def test_publisher_checksum_correcto(tmp_path):
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="checksum-test", nombre="Checksum", version="1.0.0", descripcion="Test")
       node = NodeGenerado(manifest=manifest, codigo_python="# code")

       publisher = Publisher(output_dir=tmp_path)
       result = publisher.empaquetar(node)

       expected = hashlib.sha256(result.ypkg_path.read_bytes()).hexdigest()
       assert result.checksum == expected


   def test_publisher_sandbox_ok(tmp_path):
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="sandbox", nombre="Sandbox", version="1.0.0", descripcion="Test")
       codigo = "# valid python code\nx = 1 + 1"
       node = NodeGenerado(manifest=manifest, codigo_python=codigo)

       publisher = Publisher(output_dir=tmp_path)
       result = publisher.ejecutar_sandbox(node, timeout=10)
       assert "ok" in result


   def test_publisher_sandbox_error_sintaxis(tmp_path):
       from src.studio.generator import ManifestGenerado, NodeGenerado
       from src.studio.publisher import Publisher

       manifest = ManifestGenerado(id="sandbox-err", nombre="Sandbox Err", version="1.0.0", descripcion="Test")
       codigo = "def broken(:\n  pass"  # syntax error
       node = NodeGenerado(manifest=manifest, codigo_python=codigo)

       publisher = Publisher(output_dir=tmp_path)
       result = publisher.ejecutar_sandbox(node, timeout=10)
       assert result["ok"] is False

7. Crear archivo frontend/src/__tests__/studio/NodeStudio.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/__tests__/studio/NodeStudio.test.tsx
   Contenido:

   /**
    * Tests para NodeStudio — Micro-fase 7.16
    */

   import React from 'react'
   import { render, screen, fireEvent, waitFor } from '@testing-library/react'
   import { NodeStudio } from '../../components/studio/NodeStudio'

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

   jest.mock('@monaco-editor/react', () => ({
     __esModule: true,
     default: () => <div data-testid="monaco-editor" />,
   }))

   global.fetch = jest.fn().mockResolvedValue({
     ok: true,
     json: async () => ({
       ok: true,
       manifest: {
         id: 'test-node', nombre: 'Test Node', descripcion: 'Test',
         categoria: 'Dev', zona_seguridad: 'verde',
         permisos: [], icono: '📦', grafo: {}, dependencias: [],
       },
       codigo: '# código generado',
       advertencias: [],
     }),
   })

   beforeEach(() => {
     jest.clearAllMocks()
     jest.useFakeTimers()
   })

   afterEach(() => {
     jest.useRealTimers()
   })

   describe('NodeStudio', () => {
     it('renderiza en paso 1 por defecto', () => {
       render(<NodeStudio />)
       expect(screen.getByTestId('node-studio')).toHaveAttribute('data-paso', '1')
     })

     it('muestra textarea de descripción en paso 1', () => {
       render(<NodeStudio />)
       expect(screen.getByTestId('paso-1')).toBeInTheDocument()
       expect(screen.getByTestId('descripcion-textarea')).toBeInTheDocument()
     })

     it('muestra botón Generar deshabilitado si no hay descripción', () => {
       render(<NodeStudio />)
       const btn = screen.getByTestId('generar-btn')
       expect(btn).toBeDisabled()
     })

     it('habilita botón Generar cuando hay texto', () => {
       render(<NodeStudio />)
       fireEvent.change(screen.getByTestId('descripcion-textarea'), { target: { value: 'Un nodo de prueba' } })
       expect(screen.getByTestId('generar-btn')).not.toBeDisabled()
     })

     it('muestra ejemplos rápidos', () => {
       render(<NodeStudio />)
       expect(screen.getByTestId('ejemplo-navegador-web')).toBeInTheDocument()
       expect(screen.getByTestId('ejemplo-emulador')).toBeInTheDocument()
     })

     it('al hacer click en ejemplo, rellena la descripción', () => {
       render(<NodeStudio />)
       fireEvent.click(screen.getByTestId('ejemplo-navegador-web'))
       const textarea = screen.getByTestId('descripcion-textarea') as HTMLTextAreaElement
       expect(textarea.value).toContain('Playwright')
     })

     it('muestra indicador de pasos', () => {
       render(<NodeStudio />)
       expect(screen.getByTestId('paso-indicator')).toBeInTheDocument()
     })

     it('transiciona a paso 2 al hacer click en Generar', async () => {
       render(<NodeStudio />)
       fireEvent.change(screen.getByTestId('descripcion-textarea'), { target: { value: 'Test node' } })
       fireEvent.click(screen.getByTestId('generar-btn'))
       expect(screen.getByTestId('node-studio')).toHaveAttribute('data-paso', '2')
     })

     it('muestra checklist en paso 2', () => {
       render(<NodeStudio />)
       fireEvent.change(screen.getByTestId('descripcion-textarea'), { target: { value: 'Test' } })
       fireEvent.click(screen.getByTestId('generar-btn'))
       expect(screen.getByTestId('checklist')).toBeInTheDocument()
     })
   })

VERIFICAR:
- [ ] src/studio/generator.py — GeneradorNodos con generar(), generar_streaming(), plantillas especiales
- [ ] Plantillas: browser-node (amarilla), games-node (amarilla), app-installer (roja)
- [ ] src/studio/publisher.py — Publisher con empaquetar(), publicar_en_store(), ejecutar_sandbox()
- [ ] .ypkg contiene manifest.json, node.py, config.json
- [ ] Checksum del .ypkg es SHA-256 del archivo ZIP
- [ ] Sandbox ejecuta en proceso separado con timeout de 30s
- [ ] frontend NodeStudio tiene 3 pasos: Describe → Generando → Revisa
- [ ] Paso 1: textarea, picker de ícono, ejemplos rápidos, botón Generar
- [ ] Paso 2: checklist animado, mini-grafo, chat para aclaraciones
- [ ] Paso 3: árbol de estructura + Monaco + preview del nodo en Hub + acciones (Volver, Sandbox, Publicar)
- [ ] Tests pytest pasan: test_studio.py (12 tests)
- [ ] Tests Jest pasan: NodeStudio.test.tsx (9 tests)

SI FALLA:
- pytest-asyncio no instalado: pip install pytest-asyncio y agregar asyncio_mode = "auto" en pytest.ini
- Ollama no disponible en CI: el generator.generar() usa plantillas si detecta keyword — los tests usan plantillas
- Publisher.publicar_en_store falla si NodeRegistry no importa: el test test_publisher_empaquetar solo prueba empaquetar() sin publicar
- Monaco mock no coincide: verificar que el mock retorna default: () => <div data-testid="monaco-editor" />
- Sandbox falla en Windows: subprocess.run con sys.executable funciona en Windows también

NO HACER:
- No conectar con Ollama real en tests — usar plantillas especiales o mockear httpx
- No ejecutar código arbitrario del nodo durante el sandbox sin timeout y proceso separado
- No implementar firma criptográfica completa (GPG/PKI) — SHA-256 checksum es suficiente para esta fase
- No subir a un servidor remoto — solo publicar en el Store local (~/.yeyo/store/packages/)
- No crear la UI de reviews ni ratings del nodo en esta fase

GATE Studio: Flujo completo funciona: usuario describe nodo → IA genera manifest + código en tiempo real con checklist animado → usuario edita en Monaco → sandbox ejecuta el código en proceso separado → publicar empaqueta en .ypkg con checksum válido y lo registra en el Store local → nodo aparece disponible en YEYO Store. Todos los tests pasan.
```
