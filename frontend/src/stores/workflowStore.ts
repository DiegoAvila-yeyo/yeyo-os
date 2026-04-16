/**
 * YeyoOS — Workflow Orchestrator Store
 * Zustand store for workflow designer, execution tracking, and CRUD operations.
 */

import { create } from 'zustand'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ---------- Types ----------

interface WorkflowNodeData {
  id: string
  node_type: string
  label: string
  config: Record<string, any>
  position_x: number
  position_y: number
  next_node_ids: string[]
  true_branch?: string | null
  false_branch?: string | null
  loop_body: string[]
  loop_count: number
}

interface WorkflowEdgeData {
  id: string
  source_id: string
  target_id: string
  label: string
  edge_type: string
}

interface WorkflowData {
  id: string
  name: string
  description: string
  status: string
  nodes: WorkflowNodeData[]
  edges: WorkflowEdgeData[]
  trigger_type: string
  trigger_config: Record<string, any>
  variables: Record<string, any>
  created_at: string
  updated_at: string
}

interface ExecutionData {
  id: string
  workflow_id: string
  workflow_name: string
  status: string
  node_results: Array<{
    node_id: string
    node_type: string
    status: string
    output: any
    error?: string
    started_at: string
    completed_at?: string
    duration_ms: number
    retry_count: number
  }>
  variables: Record<string, any>
  robot_id?: string
  trigger_type: string
  started_at: string
  completed_at?: string
  error?: string
  current_node_index: number
  total_nodes: number
  progress: number
}

interface NodeTypeInfo {
  label: string
  description: string
  color: string
}

interface WorkflowStore {
  // State
  workflows: WorkflowData[]
  currentWorkflow: WorkflowData | null
  executions: ExecutionData[]
  currentExecution: ExecutionData | null
  nodeTypes: Record<string, NodeTypeInfo>
  nodeCategories: Record<string, string[]>
  isLoading: boolean
  error: string | null
  activeTab: 'list' | 'designer' | 'executions'

  // Designer state
  designerNodes: WorkflowNodeData[]
  designerEdges: WorkflowEdgeData[]
  selectedNodeId: string | null

  // Actions
  setActiveTab: (tab: 'list' | 'designer' | 'executions') => void
  setError: (error: string | null) => void

  // API actions
  fetchWorkflows: () => Promise<void>
  fetchWorkflow: (id: string) => Promise<void>
  createWorkflow: (data: Partial<WorkflowData>) => Promise<WorkflowData | null>
  updateWorkflow: (id: string, data: Partial<WorkflowData>) => Promise<void>
  deleteWorkflow: (id: string) => Promise<void>
  executeWorkflow: (id: string, variables?: Record<string, any>) => Promise<ExecutionData | null>
  fetchExecutions: (workflowId: string) => Promise<void>
  fetchExecution: (execId: string) => Promise<void>
  fetchNodeTypes: () => Promise<void>

  // Designer actions
  setDesignerNodes: (nodes: WorkflowNodeData[]) => void
  setDesignerEdges: (edges: WorkflowEdgeData[]) => void
  addDesignerNode: (node: WorkflowNodeData) => void
  removeDesignerNode: (nodeId: string) => void
  updateDesignerNode: (nodeId: string, updates: Partial<WorkflowNodeData>) => void
  addDesignerEdge: (edge: WorkflowEdgeData) => void
  removeDesignerEdge: (edgeId: string) => void
  selectNode: (nodeId: string | null) => void
  clearDesigner: () => void
  loadWorkflowToDesigner: (workflow: WorkflowData) => void
}

// ---------- Store ----------

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  // Initial state
  workflows: [],
  currentWorkflow: null,
  executions: [],
  currentExecution: null,
  nodeTypes: {},
  nodeCategories: {},
  isLoading: false,
  error: null,
  activeTab: 'list',

  designerNodes: [],
  designerEdges: [],
  selectedNodeId: null,

  // Simple setters
  setActiveTab: (tab) => set({ activeTab: tab }),
  setError: (error) => set({ error }),

  // ---- API actions ----

  fetchWorkflows: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows`)
      if (!res.ok) throw new Error(`Failed to fetch workflows: ${res.statusText}`)
      const data = await res.json()
      set({ workflows: data })
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to fetch workflows' })
    } finally {
      set({ isLoading: false })
    }
  },

  fetchWorkflow: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${id}`)
      if (!res.ok) throw new Error(`Failed to fetch workflow: ${res.statusText}`)
      const data: WorkflowData = await res.json()
      set({ currentWorkflow: data })
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to fetch workflow' })
    } finally {
      set({ isLoading: false })
    }
  },

  createWorkflow: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error(`Failed to create workflow: ${res.statusText}`)
      const created: WorkflowData = await res.json()
      set((state) => ({ workflows: [...state.workflows, created] }))
      return created
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to create workflow' })
      return null
    } finally {
      set({ isLoading: false })
    }
  },

  updateWorkflow: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error(`Failed to update workflow: ${res.statusText}`)
      const updated: WorkflowData = await res.json()
      set((state) => ({
        workflows: state.workflows.map((w) => (w.id === id ? updated : w)),
        currentWorkflow: state.currentWorkflow?.id === id ? updated : state.currentWorkflow,
      }))
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to update workflow' })
    } finally {
      set({ isLoading: false })
    }
  },

  deleteWorkflow: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`Failed to delete workflow: ${res.statusText}`)
      set((state) => ({
        workflows: state.workflows.filter((w) => w.id !== id),
        currentWorkflow: state.currentWorkflow?.id === id ? null : state.currentWorkflow,
      }))
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to delete workflow' })
    } finally {
      set({ isLoading: false })
    }
  },

  executeWorkflow: async (id, variables) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ variables: variables ?? {} }),
      })
      if (!res.ok) throw new Error(`Failed to execute workflow: ${res.statusText}`)
      const execution: ExecutionData = await res.json()
      set((state) => ({ executions: [execution, ...state.executions], currentExecution: execution }))
      return execution
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to execute workflow' })
      return null
    } finally {
      set({ isLoading: false })
    }
  },

  fetchExecutions: async (workflowId) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${workflowId}/executions`)
      if (!res.ok) throw new Error(`Failed to fetch executions: ${res.statusText}`)
      const data: ExecutionData[] = await res.json()
      set({ executions: data })
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to fetch executions' })
    } finally {
      set({ isLoading: false })
    }
  },

  fetchExecution: async (execId) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/executions/${execId}`)
      if (!res.ok) throw new Error(`Failed to fetch execution: ${res.statusText}`)
      const data: ExecutionData = await res.json()
      set({ currentExecution: data })
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to fetch execution' })
    } finally {
      set({ isLoading: false })
    }
  },

  fetchNodeTypes: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/api/workflows/node-types`)
      if (!res.ok) throw new Error(`Failed to fetch node types: ${res.statusText}`)
      const data = await res.json()
      set({ nodeTypes: data.types ?? {}, nodeCategories: data.categories ?? {} })
    } catch (err: any) {
      set({ error: err.message ?? 'Failed to fetch node types' })
    } finally {
      set({ isLoading: false })
    }
  },

  // ---- Designer actions ----

  setDesignerNodes: (nodes) => set({ designerNodes: nodes }),
  setDesignerEdges: (edges) => set({ designerEdges: edges }),

  addDesignerNode: (node) =>
    set((state) => ({ designerNodes: [...state.designerNodes, node] })),

  removeDesignerNode: (nodeId) =>
    set((state) => ({
      designerNodes: state.designerNodes.filter((n) => n.id !== nodeId),
      designerEdges: state.designerEdges.filter(
        (e) => e.source_id !== nodeId && e.target_id !== nodeId,
      ),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
    })),

  updateDesignerNode: (nodeId, updates) =>
    set((state) => ({
      designerNodes: state.designerNodes.map((n) =>
        n.id === nodeId ? { ...n, ...updates } : n,
      ),
    })),

  addDesignerEdge: (edge) =>
    set((state) => ({ designerEdges: [...state.designerEdges, edge] })),

  removeDesignerEdge: (edgeId) =>
    set((state) => ({
      designerEdges: state.designerEdges.filter((e) => e.id !== edgeId),
    })),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  clearDesigner: () =>
    set({ designerNodes: [], designerEdges: [], selectedNodeId: null }),

  loadWorkflowToDesigner: (workflow) =>
    set({
      designerNodes: workflow.nodes,
      designerEdges: workflow.edges,
      selectedNodeId: null,
      currentWorkflow: workflow,
    }),
}))
