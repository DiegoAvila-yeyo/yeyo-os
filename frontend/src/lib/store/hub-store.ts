// Zustand store — Hub Neural (extendido en micro-fase 3.0)
import { create } from 'zustand';
import type { Node } from '@/types';

export interface CanvasSize {
  width: number;
  height: number;
}

export interface HubState {
  // Canvas (añadido en 3.0)
  canvasSize: CanvasSize;
  setCanvasSize: (size: CanvasSize) => void;
  // Nodos
  nodes: Node[];
  selectedNodeId: string | null;
  addNode: (node: Node) => void;
  selectNode: (id: string | null) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
  removeNode: (id: string) => void;
}

export const useHubStore = create<HubState>((set) => ({
  canvasSize: { width: 0, height: 0 },
  setCanvasSize: (size) => set({ canvasSize: size }),
  nodes: [],
  selectedNodeId: null,
  addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),
  selectNode: (id) => set({ selectedNodeId: id }),
  updateNodePosition: (id, x, y) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === id ? { ...n, position: { x, y } } : n
      ),
    })),
  removeNode: (id) =>
    set((state) => ({ nodes: state.nodes.filter((n) => n.id !== id) })),
}));
