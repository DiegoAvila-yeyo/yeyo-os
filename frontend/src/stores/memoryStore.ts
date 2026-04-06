/**
 * YeyoOS — Memory Store
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Estado global del nodo de Memoria (Flash Memory).
 * Conecta con /api/v1/memory/* del backend.
 */
import { create } from 'zustand';
import type { Memory, MemoryStats, MemoryAssociation, MemoryTier, MemoryType } from '@/types';

const API = 'http://localhost:8000/api/v1/memory';

interface MemoryFilters {
  tier: MemoryTier | 'ALL';
  type: MemoryType | 'ALL';
  namespace: string;
}

interface MemoryState {
  // Datos
  memories: Memory[];
  stats: MemoryStats | null;
  selectedMemory: Memory | null;
  associations: MemoryAssociation[];

  // Búsqueda y filtros
  searchQuery: string;
  filters: MemoryFilters;

  // UI
  loading: boolean;
  loadingStats: boolean;
  loadingAssociations: boolean;
  error: string | null;
  mode: 'browse' | 'add';

  // Acciones de lectura
  fetchRecent: (limit?: number) => Promise<void>;
  searchMemories: (q: string, limit?: number) => Promise<void>;
  fetchStats: () => Promise<void>;
  selectMemory: (memory: Memory | null) => void;
  fetchAssociations: (memoryId: string) => Promise<void>;
  setSearchQuery: (q: string) => void;
  setFilter: <K extends keyof MemoryFilters>(key: K, value: MemoryFilters[K]) => void;
  clearError: () => void;
  setMode: (mode: 'browse' | 'add') => void;

  // Acciones de escritura
  createMemory: (content: string, type: MemoryType, namespace: string, importance?: number) => Promise<boolean>;
  updateImportance: (id: string, importance: number) => Promise<boolean>;
  sendFeedback: (id: string, feedbackType: string, comment?: string) => Promise<boolean>;
  promoteTier: (id: string) => Promise<boolean>;
  demoteTier: (id: string) => Promise<boolean>;
}

export const useMemoryStore = create<MemoryState>((set, get) => ({
  memories: [],
  stats: null,
  selectedMemory: null,
  associations: [],
  searchQuery: '',
  filters: { tier: 'ALL', type: 'ALL', namespace: '' },
  loading: false,
  loadingStats: false,
  loadingAssociations: false,
  error: null,
  mode: 'browse',

  fetchRecent: async (limit = 100) => {
    set({ loading: true, error: null });
    try {
      const { filters } = get();
      const params = new URLSearchParams({ limit: String(limit) });
      if (filters.namespace) params.set('namespace', filters.namespace);
      const res = await fetch(`${API}/debug/recent?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // debug/recent devuelve { memories: [...], total: n }
      set({ memories: data.memories ?? [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  searchMemories: async (q: string, limit = 50) => {
    if (!q.trim()) {
      get().fetchRecent(limit);
      return;
    }
    set({ loading: true, error: null });
    try {
      const { filters } = get();
      const params = new URLSearchParams({ q, limit: String(limit), threshold: '0.0' });
      if (filters.namespace) params.set('namespace', filters.namespace);
      const res = await fetch(`${API}/search?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ memories: data.results ?? [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchStats: async () => {
    set({ loadingStats: true });
    try {
      const res = await fetch(`${API}/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ stats: data, loadingStats: false });
    } catch (err) {
      set({ error: String(err), loadingStats: false });
    }
  },

  selectMemory: (memory) => {
    set({ selectedMemory: memory, associations: [] });
    if (memory) get().fetchAssociations(memory.id);
  },

  fetchAssociations: async (memoryId: string) => {
    set({ loadingAssociations: true });
    try {
      const res = await fetch(`${API}/${memoryId}/associations?limit=10`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ associations: data ?? [], loadingAssociations: false });
    } catch (err) {
      set({ associations: [], loadingAssociations: false });
    }
  },

  setSearchQuery: (q) => set({ searchQuery: q }),

  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),

  clearError: () => set({ error: null }),

  setMode: (mode) => set({ mode }),

  // ─── Acciones de escritura ──────────────────────────────────────────────────

  createMemory: async (content, type, namespace, importance = 0.5) => {
    try {
      const res = await fetch(`${API}/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, type, namespace, importance }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      // Refrescar lista y stats
      get().fetchRecent(50);
      get().fetchStats();
      return true;
    } catch (err) {
      set({ error: String(err) });
      return false;
    }
  },

  updateImportance: async (id, importance) => {
    try {
      const res = await fetch(`${API}/${id}/importance`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ importance }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Actualizar memoria seleccionada in-place
      const { selectedMemory } = get();
      if (selectedMemory?.id === id) {
        set({ selectedMemory: { ...selectedMemory, importance } });
      }
      return true;
    } catch (err) {
      set({ error: String(err) });
      return false;
    }
  },

  sendFeedback: async (id, feedbackType, comment) => {
    try {
      const res = await fetch(`${API}/${id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback_type: feedbackType, comment }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return true;
    } catch (err) {
      set({ error: String(err) });
      return false;
    }
  },

  promoteTier: async (id) => {
    try {
      const res = await fetch(`${API}/${id}/promote-tier`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Actualizar tier de la memoria seleccionada
      const { selectedMemory, memories } = get();
      if (selectedMemory?.id === id) {
        set({ selectedMemory: { ...selectedMemory, tier: data.to } });
      }
      set({ memories: memories.map(m => m.id === id ? { ...m, tier: data.to } : m) });
      get().fetchStats();
      return true;
    } catch (err) {
      set({ error: String(err) });
      return false;
    }
  },

  demoteTier: async (id) => {
    try {
      const res = await fetch(`${API}/${id}/demote-tier`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const { selectedMemory, memories } = get();
      if (selectedMemory?.id === id) {
        set({ selectedMemory: { ...selectedMemory, tier: data.to } });
      }
      set({ memories: memories.map(m => m.id === id ? { ...m, tier: data.to } : m) });
      get().fetchStats();
      return true;
    } catch (err) {
      set({ error: String(err) });
      return false;
    }
  },
}));
