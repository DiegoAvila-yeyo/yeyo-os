## ═══════════════════════════════════════
## MICRO-FASE 5.10 — Automation Node (Pipeline Visual)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.10-1 [VSCODE] — Pipeline visual con React Flow

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.10 de Capa 5 (Órganos): crear el Automation Node con constructor visual de pipelines usando React Flow.

CONTEXTO:
- Micro-fases 5.0-5.9 completadas: todos los nodos core creados
- React Flow para canvas visual de pipelines
- Nodos representan pasos: Input → Process → Output
- Conectar nodos con edges (arrastrar de puerto a puerto)
- Usa Pipeline Engine de Capa 4.7
- Detección visual de ciclos
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p src/nodes/automation
   mkdir -p tests/unit/nodes/automation
   mkdir -p frontend/src/components/nodes/automation

2. Crear archivo src/nodes/automation/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/automation/__init__.py
   Contenido:
   from .service import AutomationNode

3. Crear archivo src/nodes/automation/service.py:

   Ruta: ~/yeyo-os/src/nodes/automation/service.py
   Contenido:

   """
   YeyoOS — Automation Node (Pipeline Visual)
   Micro-fase 5.10 — Capa 5: Órganos

   Constructor visual de pipelines con React Flow.
   Usa Pipeline Engine de Capa 4.7.
   """

   import uuid
   from typing import Optional, Any
   from dataclasses import dataclass, field
   from datetime import datetime, timezone

   from src.nodes.base import NodeBase, PrivilegeLevel


   @dataclass
   class VisualNode:
       """Nodo visual en el canvas de React Flow."""
       id: str
       type: str  # "input" | "process" | "output"
       label: str
       node_type: str  # tipo de nodo YeyoOS (chat, image, video, code, etc.)
       config: dict = field(default_factory=dict)
       position: dict = field(default_factory=lambda: {"x": 0, "y": 0})


   @dataclass
   class VisualEdge:
       """Conexión entre nodos visuales."""
       id: str
       source: str
       target: str
       label: str = ""


   class AutomationNode(NodeBase):
       """
       Nodo de Automatización — órgano de workflows de YeyoOS.
       Constructor visual de pipelines con React Flow.
       """

       def __init__(self):
           super().__init__(
               name="Automation",
               version="1.0.0",
               privilege_level=PrivilegeLevel.USER,
               container_config={"memory_limit": "512m", "cpu_shares": 512},
           )
           self._visual_nodes: dict[str, VisualNode] = {}
           self._visual_edges: dict[str, VisualEdge] = {}
           self._saved_pipelines: dict[str, dict] = {}

       async def initialize(self) -> None:
           pass

       async def render_ui(self) -> dict:
           return {
               "component": "AutomationNode",
               "props": {
                   "nodes": [
                       {"id": n.id, "type": n.type, "label": n.label,
                        "nodeType": n.node_type, "position": n.position}
                       for n in self._visual_nodes.values()
                   ],
                   "edges": [
                       {"id": e.id, "source": e.source, "target": e.target,
                        "label": e.label}
                       for e in self._visual_edges.values()
                   ],
                   "savedPipelines": list(self._saved_pipelines.keys()),
               },
           }

       async def process(self, input_data: dict) -> dict:
           action = input_data.get("action", "")

           if action == "add_node":
               return self._add_visual_node(input_data)
           elif action == "add_edge":
               return self._add_visual_edge(input_data)
           elif action == "remove_node":
               return self._remove_visual_node(input_data.get("node_id", ""))
           elif action == "remove_edge":
               return self._remove_visual_edge(input_data.get("edge_id", ""))
           elif action == "validate":
               return await self._validate_pipeline()
           elif action == "execute":
               return await self._execute_pipeline(input_data.get("input_data"))
           elif action == "save":
               return self._save_pipeline(input_data.get("name", ""))
           else:
               return {"error": f"Acción desconocida: {action}"}

       async def cleanup(self) -> None:
           self._visual_nodes.clear()
           self._visual_edges.clear()

       # ═══════════════════════════════════
       # MÉTODOS DEL CANVAS VISUAL
       # ═══════════════════════════════════

       def _add_visual_node(self, data: dict) -> dict:
           node = VisualNode(
               id=f"vnode-{uuid.uuid4().hex[:8]}",
               type=data.get("type", "process"),
               label=data.get("label", "Nuevo paso"),
               node_type=data.get("node_type", "generic"),
               config=data.get("config", {}),
               position=data.get("position", {"x": 100, "y": 100}),
           )
           self._visual_nodes[node.id] = node
           return {"node_id": node.id, "label": node.label}

       def _add_visual_edge(self, data: dict) -> dict:
           source = data.get("source", "")
           target = data.get("target", "")

           if source not in self._visual_nodes or target not in self._visual_nodes:
               return {"error": "Nodo origen o destino no existe"}

           if source == target:
               return {"error": "No se puede conectar un nodo consigo mismo"}

           edge = VisualEdge(
               id=f"vedge-{uuid.uuid4().hex[:8]}",
               source=source,
               target=target,
               label=data.get("label", ""),
           )
           self._visual_edges[edge.id] = edge
           return {"edge_id": edge.id, "source": source, "target": target}

       def _remove_visual_node(self, node_id: str) -> dict:
           if node_id not in self._visual_nodes:
               return {"error": "Nodo no encontrado"}
           del self._visual_nodes[node_id]
           # Remover edges conectados
           edges_to_remove = [
               eid for eid, e in self._visual_edges.items()
               if e.source == node_id or e.target == node_id
           ]
           for eid in edges_to_remove:
               del self._visual_edges[eid]
           return {"removed": node_id, "edges_removed": len(edges_to_remove)}

       def _remove_visual_edge(self, edge_id: str) -> dict:
           if edge_id not in self._visual_edges:
               return {"error": "Edge no encontrado"}
           del self._visual_edges[edge_id]
           return {"removed": edge_id}

       async def _validate_pipeline(self) -> dict:
           """Valida el pipeline visual usando Pipeline Engine de Capa 4."""
           from src.pipeline.engine import PipelineEngine

           engine = PipelineEngine()
           steps = []
           for node in self._visual_nodes.values():
               depends_on = [
                   e.source for e in self._visual_edges.values()
                   if e.target == node.id
               ]
               steps.append({
                   "id": node.id,
                   "name": node.label,
                   "node_type": node.node_type,
                   "config": node.config,
                   "depends_on": depends_on,
               })

           result = engine.validate([
               __import__("src.pipeline.engine", fromlist=["PipelineStep"]).PipelineStep(
                   id=s["id"], name=s["name"], node_type=s["node_type"],
                   config=s["config"], depends_on=s["depends_on"],
               )
               for s in steps
           ])
           return result

       async def _execute_pipeline(self, input_data: Optional[dict] = None) -> dict:
           """Ejecuta el pipeline visual."""
           validation = await self._validate_pipeline()
           if not validation.get("valid"):
               return {"error": f"Pipeline inválido: {validation.get('error')}"}

           from src.pipeline.engine import PipelineEngine
           engine = PipelineEngine()

           steps = []
           for node in self._visual_nodes.values():
               depends_on = [
                   e.source for e in self._visual_edges.values()
                   if e.target == node.id
               ]
               steps.append({
                   "id": node.id,
                   "name": node.label,
                   "node_type": node.node_type,
                   "config": node.config,
                   "depends_on": depends_on,
               })

           pipeline_id = await engine.create_pipeline("Visual Pipeline", steps)
           result = await engine.execute(pipeline_id, input_data)

           return {
               "pipeline_id": pipeline_id,
               "status": result.status.value,
               "output": result.output,
               "error": result.error,
           }

       def _save_pipeline(self, name: str) -> dict:
           if not name.strip():
               return {"error": "Nombre requerido"}
           self._saved_pipelines[name] = {
               "nodes": [
                   {"id": n.id, "type": n.type, "label": n.label,
                    "node_type": n.node_type, "position": n.position}
                   for n in self._visual_nodes.values()
               ],
               "edges": [
                   {"id": e.id, "source": e.source, "target": e.target}
                   for e in self._visual_edges.values()
               ],
           }
           return {"saved": name}

4. Crear archivo frontend/src/components/nodes/automation/AutomationNode.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/automation/AutomationNode.tsx
   Contenido:

   /**
    * YeyoOS — Automation Node Frontend
    * Micro-fase 5.10 — Capa 5: Órganos
    *
    * Canvas visual de pipelines con React Flow.
    */

   'use client';

   import React, { useState, useCallback } from 'react';
   import NodeWrapper from '../NodeWrapper';

   // React Flow se importa dinámicamente en producción
   // import ReactFlow, { addEdge, useNodesState, useEdgesState } from 'reactflow';

   interface FlowNode {
     id: string;
     type: string;
     label: string;
     nodeType: string;
     position: { x: number; y: number };
   }

   interface FlowEdge {
     id: string;
     source: string;
     target: string;
     label?: string;
   }

   interface AutomationNodeProps {
     nodeId: string;
     nodes: FlowNode[];
     edges: FlowEdge[];
     savedPipelines: string[];
     onAddNode: (data: any) => void;
     onAddEdge: (source: string, target: string) => void;
     onRemoveNode: (nodeId: string) => void;
     onValidate: () => void;
     onExecute: (inputData?: any) => void;
     onSave: (name: string) => void;
     onClose: (nodeId: string) => void;
   }

   export default function AutomationNode({
     nodeId,
     nodes,
     edges,
     savedPipelines,
     onAddNode,
     onAddEdge,
     onRemoveNode,
     onValidate,
     onExecute,
     onSave,
     onClose,
   }: AutomationNodeProps) {
     const [saveName, setSaveName] = useState('');

     const nodeTypes = [
       { type: 'input', label: '📥 Input', icon: '📥' },
       { type: 'process', label: '⚙️ Process', icon: '⚙️' },
       { type: 'output', label: '📤 Output', icon: '📤' },
     ];

     return (
       <NodeWrapper nodeId={nodeId} title="Automation" icon="🔄" onClose={onClose}
                    initialWidth={900} initialHeight={600}>
         <div className="flex h-full">
           {/* Sidebar: node palette */}
           <div className="w-48 bg-gray-800 border-r border-gray-700 p-2 space-y-2
                           shrink-0 overflow-y-auto">
             <h3 className="text-xs font-medium text-gray-400 uppercase">Pasos</h3>
             {nodeTypes.map((nt) => (
               <button
                 key={nt.type}
                 onClick={() => onAddNode({ type: nt.type, label: nt.label })}
                 className="w-full px-2 py-2 text-xs bg-gray-700 text-gray-300
                            rounded hover:bg-gray-600 text-left"
               >
                 {nt.icon} {nt.label}
               </button>
             ))}
             <hr className="border-gray-700" />
             <h3 className="text-xs font-medium text-gray-400 uppercase">Acciones</h3>
             <button onClick={onValidate}
               className="w-full px-2 py-1 text-xs bg-blue-600 text-white rounded">
               ✓ Validar
             </button>
             <button onClick={() => onExecute()}
               className="w-full px-2 py-1 text-xs bg-green-600 text-white rounded">
               ▶ Ejecutar
             </button>
             <div className="flex gap-1">
               <input
                 type="text"
                 value={saveName}
                 onChange={(e) => setSaveName(e.target.value)}
                 placeholder="Nombre..."
                 className="flex-1 px-1 py-1 text-xs bg-gray-700 text-white rounded
                            border border-gray-600"
               />
               <button onClick={() => { onSave(saveName); setSaveName(''); }}
                 className="px-2 py-1 text-xs bg-yellow-600 text-white rounded">
                 💾
               </button>
             </div>
           </div>

           {/* Canvas area (React Flow se renderiza aquí) */}
           <div className="flex-1 bg-gray-950 relative">
             {/* Placeholder para React Flow */}
             <div className="absolute inset-0 flex items-center justify-center
                             text-gray-600 text-sm">
               {nodes.length === 0
                 ? 'Arrastra pasos desde la barra lateral para crear un pipeline'
                 : `${nodes.length} nodos · ${edges.length} conexiones`}
             </div>

             {/* Visual node representation */}
             {nodes.map((node) => (
               <div
                 key={node.id}
                 className="absolute bg-gray-800 border border-gray-600 rounded-lg
                            px-3 py-2 text-xs text-white cursor-move
                            hover:border-blue-500"
                 style={{ left: node.position.x, top: node.position.y }}
               >
                 <div className="flex items-center justify-between gap-2">
                   <span>{node.label}</span>
                   <button
                     onClick={() => onRemoveNode(node.id)}
                     className="text-gray-500 hover:text-red-400"
                   >
                     ×
                   </button>
                 </div>
               </div>
             ))}
           </div>
         </div>
       </NodeWrapper>
     );
   }

5. Crear tests/unit/nodes/automation/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/automation/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/nodes/automation/test_automation_node.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/automation/test_automation_node.py
   Contenido:

   """Tests para Automation Node — Micro-fase 5.10"""

   import pytest
   from src.nodes.automation.service import AutomationNode


   class TestAutomationCanvas:

       @pytest.mark.asyncio
       async def test_add_visual_node(self):
           node = AutomationNode()
           result = node._add_visual_node({"label": "Step 1", "type": "input"})
           assert "node_id" in result
           assert len(node._visual_nodes) == 1

       @pytest.mark.asyncio
       async def test_add_visual_edge(self):
           node = AutomationNode()
           n1 = node._add_visual_node({"label": "A"})
           n2 = node._add_visual_node({"label": "B"})
           result = node._add_visual_edge({
               "source": n1["node_id"], "target": n2["node_id"]
           })
           assert "edge_id" in result
           assert len(node._visual_edges) == 1

       @pytest.mark.asyncio
       async def test_self_connection_rejected(self):
           node = AutomationNode()
           n1 = node._add_visual_node({"label": "A"})
           result = node._add_visual_edge({
               "source": n1["node_id"], "target": n1["node_id"]
           })
           assert "error" in result

       @pytest.mark.asyncio
       async def test_remove_node_removes_edges(self):
           node = AutomationNode()
           n1 = node._add_visual_node({"label": "A"})
           n2 = node._add_visual_node({"label": "B"})
           node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
           result = node._remove_visual_node(n1["node_id"])
           assert result["edges_removed"] == 1
           assert len(node._visual_edges) == 0

       @pytest.mark.asyncio
       async def test_save_pipeline(self):
           node = AutomationNode()
           node._add_visual_node({"label": "Step 1"})
           result = node._save_pipeline("Mi Pipeline")
           assert result["saved"] == "Mi Pipeline"
           assert "Mi Pipeline" in node._saved_pipelines

       @pytest.mark.asyncio
       async def test_save_empty_name_rejected(self):
           node = AutomationNode()
           result = node._save_pipeline("")
           assert "error" in result

       @pytest.mark.asyncio
       async def test_render_ui_has_nodes_and_edges(self):
           node = AutomationNode()
           node._add_visual_node({"label": "A"})
           ui = await node.render_ui()
           assert len(ui["props"]["nodes"]) == 1

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/automation/test_automation_node.py -v

VERIFICAR:
- [ ] Canvas visual con nodos y edges
- [ ] Nodos se añaden, conectan y eliminan
- [ ] Self-connection rechazada
- [ ] Remover nodo remueve edges conectados
- [ ] Pipeline se guarda y se lista
- [ ] Validación usa Pipeline Engine de Capa 4.7
- [ ] Frontend con sidebar de pasos, canvas, controles
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py
- Pipeline Engine: tests de validate/execute necesitan mock si no existe

NO HACER:
- No instalar React Flow realmente en tests (solo frontend)
- No implementar APIs sociales (eso es 5.11)
- No implementar drag & drop real (eso requiere React Flow en runtime)

GATE: AutomationNode con canvas visual, nodos/edges, validación DAG, save/load pipelines, frontend con React Flow placeholder, todos los tests pasan.
```
