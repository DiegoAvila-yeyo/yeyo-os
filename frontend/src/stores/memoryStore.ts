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

  // Acciones
  fetchRecent: (limit?: number) => Promise<void>;
  searchMemories: (q: string, limit?: number) => Promise<void>;
  fetchStats: () => Promise<void>;
  selectMemory: (memory: Memory | null) => void;
  fetchAssociations: (memoryId: string) => Promise<void>;
  setSearchQuery: (q: string) => void;
  setFilter: <K extends keyof MemoryFilters>(key: K, value: MemoryFilters[K]) => void;
  clearError: () => void;
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

  fetchRecent: async (limit = 50) => {
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
}));
