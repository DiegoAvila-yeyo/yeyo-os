// Zustand store base — Micro-fase 0.5
import { create } from 'zustand';
import type { Node } from '@/types';

interface HubState {
  nodes: Node[];
  selectedNodeId: string | null;
  addNode: (node: Node) => void;
  selectNode: (id: string | null) => void;
  updateNodePosition: (id: string, x: number, y: number) => void;
}

export const useHubStore = create<HubState>((set) => ({
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
}));
