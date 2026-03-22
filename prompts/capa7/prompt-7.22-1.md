## ═══════════════════════════════════════
## MICRO-FASE 7.22 — YeyoNet Cluster Mode: Dashboard UI
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.22-1 [VSCODE] — Cluster Dashboard: panel completo con nodos, métricas Prometheus en tiempo real y cola de tareas distribuidas

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.22 de Capa 7 (Evolución): implementar el Cluster Dashboard — interfaz completa en React/TypeScript para visualizar los nodos del cluster, sus métricas en tiempo real (GPU/CPU/RAM via Prometheus), las tareas distribuidas en ejecución, y permitir enviar nuevas tareas.

CONTEXTO:
- Micro-fases 7.19-7.21 completadas: Celery workers, GPUPool gRPC, Federated Learning funcionando
- Frontend: React + TypeScript + Vite, Tailwind CSS, Zustand para estado global
- Backend: src/api/cluster_api.py tiene endpoints GET /nodes/status, GET /tasks, POST /task
- WebSocket disponible en ws://localhost:8000/api/cluster/ws/nodes para métricas en tiempo real
- Estilo visual: dark mode, grid de tarjetas como en el Hub principal de YeyoOS
- Prometheus: cada nodo expone métricas en /metrics — el panel las muestra via WebSocket del Central
- Nodos pueden estar en estado: online (idle), active (procesando), offline
- Las tareas tienen progreso (0-100%), nodo asignado, tipo y botón cancelar

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo frontend/src/stores/clusterStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/clusterStore.ts
   Contenido:

   /**
    * YeyoNet Cluster Mode — Zustand Store
    * Micro-fase 7.22 — Capa 7: Evolución
    */

   import { create } from "zustand";
   import { devtools, subscribeWithSelector } from "zustand/middleware";

   // ── Types ─────────────────────────────────────────────────────────────────────

   export type NodeState = "online" | "active" | "offline";

   export interface ClusterNode {
     node_id: string;
     vram_total_mb: number;
     vram_free_mb: number;
     ram_free_mb: number;
     cpu_percent: number;
     is_idle: boolean;
     is_available: boolean;
     last_seen: number;
     tailscale_ip: string;
     state: NodeState;
     /** Progreso de la tarea activa (0-100), null si idle */
     active_task_progress?: number | null;
     active_task_id?: string | null;
   }

   export type TaskStatus =
     | "pending"
     | "assigned"
     | "running"
     | "success"
     | "failure"
     | "cancelled";

   export interface ClusterTask {
     task_id: string;
     task_type: string;
     status: TaskStatus;
     assigned_node: string | null;
     celery_task_id: string | null;
     created_at: number;
     started_at: number | null;
     completed_at: number | null;
     result: unknown | null;
     error: string | null;
     retry_count: number;
     /** Progreso estimado (0-100) */
     progress?: number;
   }

   export interface ClusterStats {
     total_vram_mb: number;
     total_vram_free_mb: number;
     total_ram_free_mb: number;
     online_nodes: number;
     idle_nodes: number;
     active_tasks: number;
     pending_tasks: number;
   }

   export interface SubmitTaskPayload {
     task_type: "generate_image" | "run_graph" | "train_lora";
     payload: Record<string, unknown>;
     priority?: number;
     vram_needed_mb?: number;
   }

   // ── Store ─────────────────────────────────────────────────────────────────────

   interface ClusterStore {
     nodes: ClusterNode[];
     tasks: ClusterTask[];
     stats: ClusterStats;
     isConnected: boolean;
     isLoading: boolean;
     error: string | null;
     wsRef: WebSocket | null;

     // Actions
     fetchNodes: () => Promise<void>;
     fetchTasks: () => Promise<void>;
     submitTask: (payload: SubmitTaskPayload) => Promise<ClusterTask>;
     cancelTask: (taskId: string) => Promise<void>;
     connectWebSocket: () => void;
     disconnectWebSocket: () => void;
     updateNodeFromWS: (nodeData: Partial<ClusterNode> & { node_id: string }) => void;
     computeStats: () => void;
   }

   const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
   const WS_BASE = API_BASE.replace(/^http/, "ws");

   function computeStats(nodes: ClusterNode[], tasks: ClusterTask[]): ClusterStats {
     const onlineNodes = nodes.filter((n) => n.state !== "offline");
     return {
       total_vram_mb: onlineNodes.reduce((s, n) => s + n.vram_total_mb, 0),
       total_vram_free_mb: onlineNodes.reduce((s, n) => s + n.vram_free_mb, 0),
       total_ram_free_mb: onlineNodes.reduce((s, n) => s + n.ram_free_mb, 0),
       online_nodes: onlineNodes.length,
       idle_nodes: nodes.filter((n) => n.is_idle && n.state !== "offline").length,
       active_tasks: tasks.filter((t) => t.status === "running").length,
       pending_tasks: tasks.filter((t) => t.status === "pending").length,
     };
   }

   function nodeStateFromData(node: Omit<ClusterNode, "state">): NodeState {
     const ageSeconds = Date.now() / 1000 - node.last_seen;
     if (ageSeconds > 120) return "offline";
     if (!node.is_idle) return "active";
     return "online";
   }

   export const useClusterStore = create<ClusterStore>()(
     devtools(
       subscribeWithSelector((set, get) => ({
         nodes: [],
         tasks: [],
         stats: {
           total_vram_mb: 0,
           total_vram_free_mb: 0,
           total_ram_free_mb: 0,
           online_nodes: 0,
           idle_nodes: 0,
           active_tasks: 0,
           pending_tasks: 0,
         },
         isConnected: false,
         isLoading: false,
         error: null,
         wsRef: null,

         fetchNodes: async () => {
           set({ isLoading: true, error: null });
           try {
             const resp = await fetch(`${API_BASE}/api/cluster/nodes/status`);
             if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
             const data: Omit<ClusterNode, "state">[] = await resp.json();
             const nodes: ClusterNode[] = data.map((n) => ({
               ...n,
               state: nodeStateFromData(n),
             }));
             set({ nodes, isLoading: false });
             get().computeStats();
           } catch (e) {
             set({ error: String(e), isLoading: false });
           }
         },

         fetchTasks: async () => {
           try {
             const resp = await fetch(`${API_BASE}/api/cluster/tasks`);
             if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
             const tasks: ClusterTask[] = await resp.json();
             set({ tasks });
             get().computeStats();
           } catch (e) {
             set({ error: String(e) });
           }
         },

         submitTask: async (payload: SubmitTaskPayload) => {
           const resp = await fetch(`${API_BASE}/api/cluster/task`, {
             method: "POST",
             headers: { "Content-Type": "application/json" },
             body: JSON.stringify(payload),
           });
           if (!resp.ok) {
             const err = await resp.text();
             throw new Error(`Error ${resp.status}: ${err}`);
           }
           const task: ClusterTask = await resp.json();
           set((s) => ({ tasks: [task, ...s.tasks] }));
           get().computeStats();
           return task;
         },

         cancelTask: async (taskId: string) => {
           const resp = await fetch(`${API_BASE}/api/cluster/tasks/${taskId}`, {
             method: "DELETE",
           });
           if (!resp.ok) throw new Error(`Error ${resp.status}`);
           set((s) => ({
             tasks: s.tasks.map((t) =>
               t.task_id === taskId ? { ...t, status: "cancelled" as TaskStatus } : t
             ),
           }));
           get().computeStats();
         },

         connectWebSocket: () => {
           const existing = get().wsRef;
           if (existing) existing.close();

           const ws = new WebSocket(`${WS_BASE}/api/cluster/ws/nodes`);

           ws.onopen = () => {
             set({ isConnected: true });
           };

           ws.onmessage = (evt) => {
             try {
               const msg = JSON.parse(evt.data as string);
               if (msg.type === "idle_state" || msg.node_id) {
                 get().updateNodeFromWS({
                   node_id: msg.node_id,
                   is_idle: msg.state === "idle",
                   last_seen: Date.now() / 1000,
                 });
               }
             } catch {
               // ignorar mensajes malformados
             }
           };

           ws.onclose = () => {
             set({ isConnected: false, wsRef: null });
             // Reconectar en 5 segundos
             setTimeout(() => get().connectWebSocket(), 5000);
           };

           ws.onerror = () => {
             set({ isConnected: false });
           };

           set({ wsRef: ws });
         },

         disconnectWebSocket: () => {
           const ws = get().wsRef;
           if (ws) ws.close();
           set({ wsRef: null, isConnected: false });
         },

         updateNodeFromWS: (nodeData) => {
           set((s) => {
             const existing = s.nodes.find((n) => n.node_id === nodeData.node_id);
             if (!existing) return s;

             const updated: ClusterNode = {
               ...existing,
               ...nodeData,
               state: nodeStateFromData({ ...existing, ...nodeData }),
             };
             return {
               nodes: s.nodes.map((n) =>
                 n.node_id === nodeData.node_id ? updated : n
               ),
             };
           });
           get().computeStats();
         },

         computeStats: () => {
           const { nodes, tasks } = get();
           set({ stats: computeStats(nodes, tasks) });
         },
       })),
       { name: "cluster-store" }
     )
   );

2. Crear archivo frontend/src/components/cluster/NodeCard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/cluster/NodeCard.tsx
   Contenido:

   /**
    * YeyoNet Cluster Mode — NodeCard
    * Micro-fase 7.22 — Capa 7: Evolución
    *
    * Card de un nodo con métricas GPU/CPU/RAM en tiempo real.
    * Estado visual: verde (idle/online), amarillo (active), gris (offline).
    */

   import React from "react";
   import { ClusterNode, NodeState } from "../../stores/clusterStore";

   interface Props {
     node: ClusterNode;
   }

   function ProgressBar({
     value,
     max,
     colorClass,
     label,
   }: {
     value: number;
     max: number;
     colorClass: string;
     label: string;
   }) {
     const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
     return (
       <div className="space-y-0.5">
         <div className="flex justify-between text-xs text-gray-400">
           <span>{label}</span>
           <span>{pct}%</span>
         </div>
         <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
           <div
             className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
             style={{ width: `${pct}%` }}
             role="progressbar"
             aria-valuenow={pct}
             aria-valuemin={0}
             aria-valuemax={100}
             aria-label={label}
           />
         </div>
       </div>
     );
   }

   const STATE_CONFIG: Record<
     NodeState,
     { dot: string; badge: string; label: string }
   > = {
     online: {
       dot: "bg-green-400 shadow-green-400/50 shadow-md",
       badge: "bg-green-900/40 text-green-400 border border-green-700",
       label: "idle",
     },
     active: {
       dot: "bg-yellow-400 shadow-yellow-400/50 shadow-md animate-pulse",
       badge: "bg-yellow-900/40 text-yellow-400 border border-yellow-700",
       label: "procesando",
     },
     offline: {
       dot: "bg-gray-500",
       badge: "bg-gray-800 text-gray-500 border border-gray-700",
       label: "offline",
     },
   };

   function formatMB(mb: number): string {
     if (mb >= 1024) return `${(mb / 1024).toFixed(1)}GB`;
     return `${mb}MB`;
   }

   function timeAgo(unixSeconds: number): string {
     const diff = Math.floor(Date.now() / 1000 - unixSeconds);
     if (diff < 60) return `${diff}s`;
     if (diff < 3600) return `${Math.floor(diff / 60)}min`;
     return `${Math.floor(diff / 3600)}h`;
   }

   export function NodeCard({ node }: Props) {
     const cfg = STATE_CONFIG[node.state];
     const vramUsedPct =
       node.vram_total_mb > 0
         ? 100 - Math.round((node.vram_free_mb / node.vram_total_mb) * 100)
         : 0;
     const hasGPU = node.vram_total_mb > 0;

     return (
       <div
         className={`
           bg-gray-900 border rounded-xl p-4 space-y-3
           transition-all duration-300
           ${node.state === "offline" ? "border-gray-700 opacity-60" : "border-gray-700 hover:border-gray-500"}
         `}
         data-testid={`node-card-${node.node_id}`}
       >
         {/* Header */}
         <div className="flex items-center justify-between">
           <div className="flex items-center gap-2">
             <span
               className={`w-2.5 h-2.5 rounded-full inline-block flex-shrink-0 ${cfg.dot}`}
               aria-label={`Estado: ${cfg.label}`}
             />
             <span
               className="text-sm font-medium text-white truncate max-w-[120px]"
               title={node.node_id}
             >
               {node.node_id}
             </span>
           </div>
           <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>
             {cfg.label}
           </span>
         </div>

         {/* IP y última vez visto */}
         <div className="text-xs text-gray-500 flex justify-between">
           <span>{node.tailscale_ip || "sin IP"}</span>
           <span>hace {timeAgo(node.last_seen)}</span>
         </div>

         {/* Métricas */}
         <div className="space-y-2">
           {hasGPU && (
             <ProgressBar
               value={vramUsedPct}
               max={100}
               colorClass={
                 vramUsedPct > 85
                   ? "bg-red-500"
                   : vramUsedPct > 60
                   ? "bg-yellow-500"
                   : "bg-violet-500"
               }
               label={`VRAM ${formatMB(node.vram_free_mb)} libre / ${formatMB(node.vram_total_mb)}`}
             />
           )}

           {!hasGPU && (
             <p className="text-xs text-gray-600 italic">Sin GPU dedicada</p>
           )}

           <ProgressBar
             value={node.cpu_percent}
             max={100}
             colorClass={
               node.cpu_percent > 85
                 ? "bg-red-500"
                 : node.cpu_percent > 60
                 ? "bg-yellow-500"
                 : "bg-blue-500"
             }
             label={`CPU ${node.cpu_percent.toFixed(0)}%`}
           />
         </div>

         {/* Tarea activa */}
         {node.active_task_id && (
           <div className="bg-gray-800 rounded-lg p-2 space-y-1">
             <p className="text-xs text-yellow-400 font-medium truncate">
               🔄 {node.active_task_id.slice(0, 16)}…
             </p>
             {node.active_task_progress != null && (
               <div className="h-1 bg-gray-700 rounded-full overflow-hidden">
                 <div
                   className="h-full bg-yellow-400 rounded-full transition-all duration-500"
                   style={{ width: `${node.active_task_progress}%` }}
                 />
               </div>
             )}
           </div>
         )}
       </div>
     );
   }

   export default NodeCard;

3. Crear archivo frontend/src/components/cluster/TaskQueue.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/cluster/TaskQueue.tsx
   Contenido:

   /**
    * YeyoNet Cluster Mode — TaskQueue
    * Micro-fase 7.22 — Capa 7: Evolución
    *
    * Lista de tareas distribuidas con estado, progreso,
    * nodo asignado y botón de cancelar.
    */

   import React from "react";
   import { ClusterTask, TaskStatus, useClusterStore } from "../../stores/clusterStore";

   const STATUS_CONFIG: Record<
     TaskStatus,
     { icon: string; text: string; class: string }
   > = {
     pending: { icon: "⏳", text: "pendiente", class: "text-gray-400" },
     assigned: { icon: "📌", text: "asignada", class: "text-blue-400" },
     running: { icon: "🔄", text: "ejecutando", class: "text-yellow-400" },
     success: { icon: "✅", text: "completada", class: "text-green-400" },
     failure: { icon: "❌", text: "fallida", class: "text-red-400" },
     cancelled: { icon: "🚫", text: "cancelada", class: "text-gray-500" },
   };

   const TASK_TYPE_LABELS: Record<string, string> = {
     generate_image: "🎨 Generar imagen",
     run_graph: "🔷 Ejecutar grafo",
     train_lora: "🧠 Entrenar LoRA",
   };

   function timeAgo(unixSeconds: number | null): string {
     if (!unixSeconds) return "—";
     const diff = Math.floor(Date.now() / 1000 - unixSeconds);
     if (diff < 60) return `${diff}s`;
     if (diff < 3600) return `${Math.floor(diff / 60)}min`;
     return `${Math.floor(diff / 3600)}h`;
   }

   interface TaskRowProps {
     task: ClusterTask;
     onCancel: (id: string) => void;
   }

   function TaskRow({ task, onCancel }: TaskRowProps) {
     const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.pending;
     const canCancel = task.status === "pending" || task.status === "assigned" || task.status === "running";
     const typeLabel = TASK_TYPE_LABELS[task.task_type] ?? task.task_type;

     return (
       <div
         className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-gray-800/50 transition-colors"
         data-testid={`task-row-${task.task_id}`}
       >
         {/* Icono estado */}
         <span className="text-base flex-shrink-0" aria-label={cfg.text}>
           {cfg.icon}
         </span>

         {/* Info principal */}
         <div className="flex-1 min-w-0 space-y-0.5">
           <div className="flex items-center gap-2">
             <span className="text-sm text-white font-medium">{typeLabel}</span>
             <span className={`text-xs ${cfg.class}`}>{cfg.text}</span>
             {task.retry_count > 0 && (
               <span className="text-xs text-orange-400">retry #{task.retry_count}</span>
             )}
           </div>
           <div className="flex items-center gap-3 text-xs text-gray-500">
             <span title="ID de tarea">{task.task_id.slice(0, 12)}…</span>
             {task.assigned_node && (
               <span className="text-blue-400 truncate max-w-[120px]" title={task.assigned_node}>
                 📍 {task.assigned_node}
               </span>
             )}
             <span>hace {timeAgo(task.created_at)}</span>
           </div>

           {/* Progreso para tareas en ejecución */}
           {task.status === "running" && task.progress != null && (
             <div className="mt-1 h-1 bg-gray-700 rounded-full overflow-hidden">
               <div
                 className="h-full bg-yellow-400 rounded-full transition-all duration-500"
                 style={{ width: `${task.progress}%` }}
               />
             </div>
           )}

           {/* Error */}
           {task.error && (
             <p className="text-xs text-red-400 truncate" title={task.error}>
               {task.error}
             </p>
           )}
         </div>

         {/* Botón cancelar */}
         {canCancel && (
           <button
             onClick={() => onCancel(task.task_id)}
             className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-red-900/20 flex-shrink-0"
             aria-label={`Cancelar tarea ${task.task_id}`}
             title="Cancelar tarea"
           >
             ✕
           </button>
         )}
       </div>
     );
   }

   export function TaskQueue() {
     const tasks = useClusterStore((s) => s.tasks);
     const cancelTask = useClusterStore((s) => s.cancelTask);

     const activeTasks = tasks.filter((t) =>
       ["pending", "assigned", "running"].includes(t.status)
     );
     const completedTasks = tasks
       .filter((t) => ["success", "failure", "cancelled"].includes(t.status))
       .slice(0, 20);

     const handleCancel = async (taskId: string) => {
       try {
         await cancelTask(taskId);
       } catch (e) {
         console.error("Error cancelando tarea:", e);
       }
     };

     return (
       <div className="space-y-2" data-testid="task-queue">
         {activeTasks.length === 0 && completedTasks.length === 0 && (
           <p className="text-center text-gray-500 text-sm py-8">
             Sin tareas distribuidas
           </p>
         )}

         {activeTasks.length > 0 && (
           <div>
             <p className="text-xs text-gray-500 uppercase tracking-wide px-3 pb-1">
               En cola / ejecutando ({activeTasks.length})
             </p>
             <div className="divide-y divide-gray-800">
               {activeTasks.map((t) => (
                 <TaskRow key={t.task_id} task={t} onCancel={handleCancel} />
               ))}
             </div>
           </div>
         )}

         {completedTasks.length > 0 && (
           <div className="mt-2">
             <p className="text-xs text-gray-600 uppercase tracking-wide px-3 pb-1">
               Recientes
             </p>
             <div className="divide-y divide-gray-800/50 opacity-70">
               {completedTasks.map((t) => (
                 <TaskRow key={t.task_id} task={t} onCancel={handleCancel} />
               ))}
             </div>
           </div>
         )}
       </div>
     );
   }

   export default TaskQueue;

4. Crear archivo frontend/src/components/cluster/ClusterDashboard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/cluster/ClusterDashboard.tsx
   Contenido:

   /**
    * YeyoNet Cluster Mode — ClusterDashboard
    * Micro-fase 7.22 — Capa 7: Evolución
    *
    * Panel completo del cluster:
    * - Header con recursos totales de la red
    * - Grid de nodos con métricas en tiempo real
    * - Cola de tareas distribuidas
    * - Botón "Nueva tarea distribuida" con modal
    * - Botón "Límites de recursos"
    */

   import React, { useEffect, useRef, useState } from "react";
   import { useClusterStore, SubmitTaskPayload } from "../../stores/clusterStore";
   import { NodeCard } from "./NodeCard";
   import { TaskQueue } from "./TaskQueue";

   // ── Subcomponente: Estadística del header ─────────────────────────────────────

   function StatCard({
     label,
     value,
     unit,
     colorClass = "text-white",
   }: {
     label: string;
     value: string | number;
     unit?: string;
     colorClass?: string;
   }) {
     return (
       <div className="bg-gray-800/60 rounded-xl px-4 py-3 text-center">
         <p className={`text-xl font-bold ${colorClass}`}>
           {value}
           {unit && <span className="text-sm font-normal text-gray-400 ml-1">{unit}</span>}
         </p>
         <p className="text-xs text-gray-500 mt-0.5">{label}</p>
       </div>
     );
   }

   // ── Subcomponente: Modal nueva tarea ──────────────────────────────────────────

   interface NewTaskModalProps {
     onClose: () => void;
     onSubmit: (payload: SubmitTaskPayload) => Promise<void>;
   }

   function NewTaskModal({ onClose, onSubmit }: NewTaskModalProps) {
     const [taskType, setTaskType] = useState<SubmitTaskPayload["task_type"]>("run_graph");
     const [promptText, setPromptText] = useState("");
     const [vramNeeded, setVramNeeded] = useState(0);
     const [isSubmitting, setIsSubmitting] = useState(false);
     const [error, setError] = useState("");

     const handleSubmit = async (e: React.FormEvent) => {
       e.preventDefault();
       setIsSubmitting(true);
       setError("");

       try {
         const payload: Record<string, unknown> =
           taskType === "generate_image"
             ? { prompt: promptText, width: 512, height: 512, steps: 20 }
             : taskType === "run_graph"
             ? { graph_id: promptText || "default", inputs: {} }
             : { base_model: "qwen2.5:3b", epochs: 3 };

         await onSubmit({
           task_type: taskType,
           payload,
           priority: 5,
           vram_needed_mb: vramNeeded,
         });
         onClose();
       } catch (e) {
         setError(String(e));
       } finally {
         setIsSubmitting(false);
       }
     };

     return (
       <div
         className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50"
         role="dialog"
         aria-modal="true"
         aria-label="Nueva tarea distribuida"
         onClick={(e) => e.target === e.currentTarget && onClose()}
       >
         <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
           <div className="flex items-center justify-between mb-4">
             <h2 className="text-lg font-semibold text-white">Nueva tarea distribuida</h2>
             <button
               onClick={onClose}
               className="text-gray-400 hover:text-white transition-colors"
               aria-label="Cerrar modal"
             >
               ✕
             </button>
           </div>

           <form onSubmit={handleSubmit} className="space-y-4">
             {/* Tipo de tarea */}
             <div>
               <label className="block text-xs text-gray-400 mb-1.5">Tipo de tarea</label>
               <div className="grid grid-cols-3 gap-2">
                 {(
                   [
                     ["generate_image", "🎨", "Imagen"],
                     ["run_graph", "🔷", "Grafo"],
                     ["train_lora", "🧠", "LoRA"],
                   ] as const
                 ).map(([type, icon, label]) => (
                   <button
                     key={type}
                     type="button"
                     onClick={() => setTaskType(type)}
                     className={`p-2.5 rounded-lg border text-sm flex flex-col items-center gap-1 transition-colors ${
                       taskType === type
                         ? "border-violet-500 bg-violet-900/30 text-violet-300"
                         : "border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-500"
                     }`}
                   >
                     <span className="text-lg">{icon}</span>
                     <span>{label}</span>
                   </button>
                 ))}
               </div>
             </div>

             {/* Parámetro principal */}
             {(taskType === "generate_image" || taskType === "run_graph") && (
               <div>
                 <label className="block text-xs text-gray-400 mb-1.5">
                   {taskType === "generate_image" ? "Prompt" : "ID del grafo"}
                 </label>
                 <input
                   type="text"
                   value={promptText}
                   onChange={(e) => setPromptText(e.target.value)}
                   placeholder={
                     taskType === "generate_image"
                       ? "un paisaje futurista azul..."
                       : "mi-grafo-id"
                   }
                   className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500"
                 />
               </div>
             )}

             {/* VRAM necesaria */}
             <div>
               <label className="block text-xs text-gray-400 mb-1.5">
                 VRAM necesaria: {vramNeeded > 0 ? `${vramNeeded}MB` : "cualquiera"}
               </label>
               <input
                 type="range"
                 min={0}
                 max={12288}
                 step={512}
                 value={vramNeeded}
                 onChange={(e) => setVramNeeded(Number(e.target.value))}
                 className="w-full accent-violet-500"
                 aria-label="VRAM necesaria en MB"
               />
               <div className="flex justify-between text-xs text-gray-600 mt-0.5">
                 <span>cualquiera</span>
                 <span>12GB</span>
               </div>
             </div>

             {error && (
               <p className="text-xs text-red-400 bg-red-900/20 rounded-lg px-3 py-2">
                 {error}
               </p>
             )}

             <div className="flex gap-2 pt-1">
               <button
                 type="button"
                 onClick={onClose}
                 className="flex-1 py-2 rounded-lg border border-gray-700 text-sm text-gray-400 hover:text-white transition-colors"
               >
                 Cancelar
               </button>
               <button
                 type="submit"
                 disabled={isSubmitting}
                 className="flex-1 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-sm text-white font-medium transition-colors"
               >
                 {isSubmitting ? "Enviando…" : "Enviar tarea"}
               </button>
             </div>
           </form>
         </div>
       </div>
     );
   }

   // ── Dashboard principal ───────────────────────────────────────────────────────

   export function ClusterDashboard() {
     const {
       nodes,
       tasks,
       stats,
       isConnected,
       isLoading,
       error,
       fetchNodes,
       fetchTasks,
       submitTask,
       connectWebSocket,
       disconnectWebSocket,
     } = useClusterStore();

     const [showNewTask, setShowNewTask] = useState(false);
     const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

     useEffect(() => {
       // Cargar datos iniciales
       fetchNodes();
       fetchTasks();
       connectWebSocket();

       // Polling cada 10s para actualizar nodos y tareas
       pollRef.current = setInterval(() => {
         fetchNodes();
         fetchTasks();
       }, 10_000);

       return () => {
         if (pollRef.current) clearInterval(pollRef.current);
         disconnectWebSocket();
       };
     }, []);

     const handleSubmitTask = async (payload: SubmitTaskPayload) => {
       await submitTask(payload);
       fetchTasks();
     };

     const formatVRAM = (mb: number) =>
       mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${mb}MB`;

     const onlineNodes = nodes.filter((n) => n.state !== "offline");
     const idleNodes = nodes.filter((n) => n.state === "online");
     const activeTasksList = tasks.filter((t) =>
       ["pending", "assigned", "running"].includes(t.status)
     );

     return (
       <div className="min-h-screen bg-gray-950 text-white p-6 space-y-6" data-testid="cluster-dashboard">
         {/* Header */}
         <div className="flex items-center justify-between">
           <div>
             <h1 className="text-2xl font-bold text-white flex items-center gap-2">
               <span>🌐</span> YeyoNet Cluster
             </h1>
             <p className="text-sm text-gray-500 mt-0.5">
               Cómputo distribuido · {onlineNodes.length} nodos online
               <span
                 className={`inline-block w-2 h-2 rounded-full ml-2 ${
                   isConnected ? "bg-green-400" : "bg-gray-600"
                 }`}
                 title={isConnected ? "WebSocket conectado" : "WebSocket desconectado"}
               />
             </p>
           </div>
           <div className="flex gap-2">
             <button
               onClick={() => setShowNewTask(true)}
               className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5"
               aria-label="Nueva tarea distribuida"
             >
               <span>＋</span> Nueva tarea
             </button>
           </div>
         </div>

         {/* Error */}
         {error && (
           <div className="bg-red-900/20 border border-red-800 rounded-xl px-4 py-3 text-sm text-red-400">
             {error}
           </div>
         )}

         {/* Stats del cluster */}
         <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
           <StatCard
             label="GPU total"
             value={formatVRAM(stats.total_vram_mb)}
             colorClass="text-violet-400"
           />
           <StatCard
             label="GPU libre"
             value={formatVRAM(stats.total_vram_free_mb)}
             colorClass="text-green-400"
           />
           <StatCard
             label="Nodos online"
             value={stats.online_nodes}
             colorClass="text-blue-400"
           />
           <StatCard
             label="Nodos idle"
             value={stats.idle_nodes}
             colorClass="text-green-400"
           />
           <StatCard
             label="Tareas activas"
             value={stats.active_tasks}
             colorClass="text-yellow-400"
           />
           <StatCard
             label="En cola"
             value={stats.pending_tasks}
             colorClass="text-orange-400"
           />
         </div>

         {/* Layout principal */}
         <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
           {/* Grid de nodos */}
           <div className="lg:col-span-2 space-y-4">
             <div className="flex items-center justify-between">
               <h2 className="text-base font-semibold text-gray-200">Nodos</h2>
               <button
                 onClick={fetchNodes}
                 disabled={isLoading}
                 className="text-xs text-gray-500 hover:text-white transition-colors disabled:opacity-50"
                 aria-label="Actualizar nodos"
               >
                 {isLoading ? "↻ actualizando…" : "↻ actualizar"}
               </button>
             </div>

             {nodes.length === 0 && !isLoading && (
               <div className="text-center py-16 text-gray-600">
                 <p className="text-4xl mb-2">🌐</p>
                 <p>Sin nodos registrados</p>
                 <p className="text-xs mt-1">Los satélites aparecerán aquí al conectarse</p>
               </div>
             )}

             <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
               {nodes.map((node) => (
                 <NodeCard key={node.node_id} node={node} />
               ))}
             </div>
           </div>

           {/* Cola de tareas */}
           <div className="space-y-4">
             <div className="flex items-center justify-between">
               <h2 className="text-base font-semibold text-gray-200">
                 Tareas
                 {activeTasksList.length > 0 && (
                   <span className="ml-2 text-xs bg-yellow-900/40 text-yellow-400 px-1.5 py-0.5 rounded-full border border-yellow-700">
                     {activeTasksList.length}
                   </span>
                 )}
               </h2>
               <button
                 onClick={fetchTasks}
                 className="text-xs text-gray-500 hover:text-white transition-colors"
                 aria-label="Actualizar tareas"
               >
                 ↻
               </button>
             </div>
             <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
               <TaskQueue />
             </div>
           </div>
         </div>

         {/* Modal nueva tarea */}
         {showNewTask && (
           <NewTaskModal
             onClose={() => setShowNewTask(false)}
             onSubmit={handleSubmitTask}
           />
         )}
       </div>
     );
   }

   export default ClusterDashboard;

5. Crear archivo frontend/src/components/cluster/__tests__/ClusterDashboard.test.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/cluster/__tests__/ClusterDashboard.test.tsx
   Contenido:

   /**
    * Tests Jest para ClusterDashboard, NodeCard y TaskQueue
    */

   import React from "react";
   import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
   import { ClusterDashboard } from "../ClusterDashboard";
   import { NodeCard } from "../NodeCard";
   import { TaskQueue } from "../TaskQueue";
   import { useClusterStore } from "../../../stores/clusterStore";

   // Mock global fetch
   global.fetch = jest.fn();
   // Mock WebSocket
   global.WebSocket = jest.fn().mockImplementation(() => ({
     onopen: null,
     onmessage: null,
     onclose: null,
     onerror: null,
     send: jest.fn(),
     close: jest.fn(),
   })) as unknown as typeof WebSocket;

   const mockNode = {
     node_id: "sat-test-1",
     vram_total_mb: 6144,
     vram_free_mb: 4096,
     ram_free_mb: 8192,
     cpu_percent: 15,
     is_idle: true,
     is_available: true,
     last_seen: Date.now() / 1000 - 30,
     tailscale_ip: "100.64.0.2",
     state: "online" as const,
   };

   const mockTask = {
     task_id: "task-abc-123",
     task_type: "run_graph",
     status: "running" as const,
     assigned_node: "sat-test-1",
     celery_task_id: "celery-xyz",
     created_at: Date.now() / 1000 - 60,
     started_at: Date.now() / 1000 - 50,
     completed_at: null,
     result: null,
     error: null,
     retry_count: 0,
     progress: 45,
   };

   // Reset store entre tests
   beforeEach(() => {
     jest.clearAllMocks();
     useClusterStore.setState({
       nodes: [],
       tasks: [],
       stats: {
         total_vram_mb: 0,
         total_vram_free_mb: 0,
         total_ram_free_mb: 0,
         online_nodes: 0,
         idle_nodes: 0,
         active_tasks: 0,
         pending_tasks: 0,
       },
       isConnected: false,
       isLoading: false,
       error: null,
       wsRef: null,
     });
     (fetch as jest.Mock).mockResolvedValue({
       ok: true,
       json: async () => [],
     });
   });

   // ── NodeCard Tests ────────────────────────────────────────────────────────────

   describe("NodeCard", () => {
     it("renders node_id", () => {
       render(<NodeCard node={mockNode} />);
       expect(screen.getByText("sat-test-1")).toBeInTheDocument();
     });

     it("shows idle badge for online node", () => {
       render(<NodeCard node={mockNode} />);
       expect(screen.getByText("idle")).toBeInTheDocument();
     });

     it("shows offline state", () => {
       const offlineNode = { ...mockNode, state: "offline" as const };
       render(<NodeCard node={offlineNode} />);
       expect(screen.getByText("offline")).toBeInTheDocument();
     });

     it("shows active state", () => {
       const activeNode = { ...mockNode, state: "active" as const, is_idle: false };
       render(<NodeCard node={activeNode} />);
       expect(screen.getByText("procesando")).toBeInTheDocument();
     });

     it("shows VRAM info when GPU available", () => {
       render(<NodeCard node={mockNode} />);
       // Debe mostrar algo con VRAM
       expect(screen.getByRole("progressbar", { name: /VRAM/i })).toBeInTheDocument();
     });

     it("shows no GPU message when vram_total is 0", () => {
       render(<NodeCard node={{ ...mockNode, vram_total_mb: 0 }} />);
       expect(screen.getByText("Sin GPU dedicada")).toBeInTheDocument();
     });

     it("shows active task when present", () => {
       const nodeWithTask = {
         ...mockNode,
         active_task_id: "task-abc-123",
         active_task_progress: 45,
       };
       render(<NodeCard node={nodeWithTask} />);
       expect(screen.getByText(/task-abc/)).toBeInTheDocument();
     });

     it("shows tailscale IP", () => {
       render(<NodeCard node={mockNode} />);
       expect(screen.getByText("100.64.0.2")).toBeInTheDocument();
     });
   });

   // ── TaskQueue Tests ───────────────────────────────────────────────────────────

   describe("TaskQueue", () => {
     it("shows empty state when no tasks", () => {
       render(<TaskQueue />);
       expect(screen.getByText("Sin tareas distribuidas")).toBeInTheDocument();
     });

     it("renders running task", () => {
       useClusterStore.setState({ tasks: [mockTask] });
       render(<TaskQueue />);
       expect(screen.getByText(/ejecutando/)).toBeInTheDocument();
     });

     it("shows cancel button for running task", () => {
       useClusterStore.setState({ tasks: [mockTask] });
       render(<TaskQueue />);
       const cancelBtn = screen.getByLabelText(/Cancelar tarea/);
       expect(cancelBtn).toBeInTheDocument();
     });

     it("does not show cancel button for completed task", () => {
       const completedTask = { ...mockTask, status: "success" as const };
       useClusterStore.setState({ tasks: [completedTask] });
       render(<TaskQueue />);
       expect(screen.queryByLabelText(/Cancelar tarea/)).not.toBeInTheDocument();
     });

     it("shows task type label", () => {
       useClusterStore.setState({ tasks: [mockTask] });
       render(<TaskQueue />);
       expect(screen.getByText("🔷 Ejecutar grafo")).toBeInTheDocument();
     });

     it("shows assigned node", () => {
       useClusterStore.setState({ tasks: [mockTask] });
       render(<TaskQueue />);
       expect(screen.getByText(/sat-test-1/)).toBeInTheDocument();
     });
   });

   // ── ClusterDashboard Tests ────────────────────────────────────────────────────

   describe("ClusterDashboard", () => {
     it("renders dashboard title", async () => {
       render(<ClusterDashboard />);
       expect(screen.getByText(/YeyoNet Cluster/)).toBeInTheDocument();
     });

     it("renders stats cards", () => {
       render(<ClusterDashboard />);
       expect(screen.getByText("GPU total")).toBeInTheDocument();
       expect(screen.getByText("GPU libre")).toBeInTheDocument();
       expect(screen.getByText("Nodos online")).toBeInTheDocument();
     });

     it("renders node cards when nodes present", async () => {
       useClusterStore.setState({ nodes: [mockNode] });
       render(<ClusterDashboard />);
       await waitFor(() => {
         expect(screen.getByTestId("node-card-sat-test-1")).toBeInTheDocument();
       });
     });

     it("shows empty state when no nodes", () => {
       render(<ClusterDashboard />);
       expect(screen.getByText(/Sin nodos registrados/)).toBeInTheDocument();
     });

     it("opens new task modal on button click", async () => {
       render(<ClusterDashboard />);
       fireEvent.click(screen.getByText("＋ Nueva tarea"));
       await waitFor(() => {
         expect(screen.getByRole("dialog")).toBeInTheDocument();
         expect(screen.getByText("Nueva tarea distribuida")).toBeInTheDocument();
       });
     });

     it("closes modal on cancel", async () => {
       render(<ClusterDashboard />);
       fireEvent.click(screen.getByText("＋ Nueva tarea"));
       await waitFor(() => screen.getByRole("dialog"));
       fireEvent.click(screen.getByText("Cancelar"));
       await waitFor(() => {
         expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
       });
     });

     it("shows WebSocket connection status", () => {
       render(<ClusterDashboard />);
       const dot = document.querySelector('[title="WebSocket desconectado"]');
       expect(dot).toBeInTheDocument();
     });

     it("shows task counts in stats", async () => {
       useClusterStore.setState({
         tasks: [mockTask],
         stats: {
           total_vram_mb: 6144,
           total_vram_free_mb: 4096,
           total_ram_free_mb: 8192,
           online_nodes: 1,
           idle_nodes: 1,
           active_tasks: 1,
           pending_tasks: 0,
         },
       });
       render(<ClusterDashboard />);
       expect(screen.getByText("Tareas activas")).toBeInTheDocument();
     });
   });

VERIFICAR:
- [ ] frontend/src/stores/clusterStore.ts — Zustand con nodes[], tasks[], stats, fetchNodes, fetchTasks, submitTask, cancelTask, connectWebSocket
- [ ] frontend/src/components/cluster/NodeCard.tsx — Card con estado online/active/offline, VRAM/CPU progress bars, tarea activa
- [ ] frontend/src/components/cluster/TaskQueue.tsx — Lista con estado, tipo, nodo asignado, progreso, botón cancelar
- [ ] frontend/src/components/cluster/ClusterDashboard.tsx — Header stats, grid nodos, cola tareas, modal nueva tarea
- [ ] Tests Jest pasan: npx jest --testPathPattern=ClusterDashboard (≥22 tests)
- [ ] Dashboard carga nodos y tareas reales vía fetch al inicializar

SI FALLA:
- @testing-library/react no instalado: npm install -D @testing-library/react @testing-library/jest-dom
- Zustand subscribeWithSelector: npm install zustand (ya debería estar)
- WebSocket mock falló: verificar que global.WebSocket está antes de importar el store
- tailwind clases no funcionan en tests: tests son unitarios, no necesitan CSS real

NO HACER:
- No hacer polling más frecuente de 5 segundos (sobrecarga de red)
- No mostrar datos privados de Flash Memory de los satélites en el dashboard
- No implementar screenshare o control remoto en el dashboard (requiere permiso explícito nivel 4)
- No usar bibliotecas de charts pesadas (recharts/d3) — usar barras CSS simples

GATE: ClusterDashboard renderiza con nodos y tareas desde el store. NodeCard muestra VRAM/CPU con barras de progreso y estado correcto. TaskQueue permite cancelar tareas activas. Modal "Nueva tarea" envía POST al API. Todos los tests Jest pasan (≥22 tests). Dashboard muestra nodos con métricas en tiempo real vía WebSocket.
```
