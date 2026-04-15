/**
 * YeyoOS — YeyoNet Store
 * Estado global del nodo YeyoNet (red de satélites).
 * Conecta con /api/v1/yeyonet/* del backend.
 */
import { create } from 'zustand';

// ─── Interfaces ────────────────────────────────────────────────────────────────

export interface Satellite {
  id: string;
  name: string;
  role: string;
  mode: string;
  status: string;
  last_seen_at: string | null;
  resources: {
    cpu_cores?: number;
    ram_gb?: number;
    gpu_name?: string;
  } | null;
  visibility_level: number;
  permissions: string[];
}

export interface Job {
  id: string;
  type: string;
  status: string;
  priority: number;
  payload: Record<string, unknown>;
  assigned_node?: string;
  progress?: number;
  result?: Record<string, unknown>;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  timeout_seconds?: number;
}

export interface JobStats {
  total: number;
  by_status: {
    queued: number;
    running: number;
    completed: number;
    failed: number;
  };
  by_type: Record<string, number>;
}

export interface SyncStats {
  total_memories: number;
  synced_memories: number;
  offline_queue_size: number;
  offline_queues: Record<string, number>;
}

export interface NodeIdentity {
  node_id: string;
  node_name: string;
  role: string;
}

export interface InviteResult {
  code: string;
  satellite_name: string;
  expires_at: string;
}

export type YeyoNetTab = 'satellites' | 'render' | 'sync' | 'config';

interface YeyoNetState {
  satellites: Satellite[];
  jobs: Job[];
  jobStats: JobStats | null;
  syncStats: SyncStats | null;
  identity: NodeIdentity | null;
  activeTab: YeyoNetTab;
  loading: boolean;
  error: string | null;

  setActiveTab: (tab: YeyoNetTab) => void;
  fetchSatellites: () => Promise<void>;
  fetchJobs: (status?: string) => Promise<void>;
  fetchJobStats: () => Promise<void>;
  fetchSyncStats: () => Promise<void>;
  fetchIdentity: () => Promise<void>;
  createInvitation: (req: {
    satellite_name: string;
    permissions: string[];
    visibility_level: number;
    expires_in_days: number;
  }) => Promise<InviteResult>;
  cancelJob: (jobId: string) => Promise<void>;
  triggerSync: (nodeId: string) => Promise<void>;
  registerAsSatellite: (centralUrl: string, code: string, name: string, mode: string) => Promise<{ node_id: string; auth_token: string }>;
  clearError: () => void;
}

const API = '/api/v1/yeyonet';

export const useYeyoNetStore = create<YeyoNetState>((set, get) => ({
  satellites: [],
  jobs: [],
  jobStats: null,
  syncStats: null,
  identity: null,
  activeTab: 'satellites',
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  clearError: () => set({ error: null }),

  fetchSatellites: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API}/satellites`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ satellites: Array.isArray(data) ? data : [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchJobs: async (status?: string) => {
    set({ loading: true, error: null });
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (status) params.set('status', status);
      const res = await fetch(`${API}/jobs?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ jobs: Array.isArray(data) ? data : [], loading: false });
    } catch (err) {
      set({ error: String(err), loading: false });
    }
  },

  fetchJobStats: async () => {
    try {
      const res = await fetch(`${API}/jobs/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ jobStats: data });
    } catch (err) {
      set({ error: String(err) });
    }
  },

  fetchSyncStats: async () => {
    try {
      const res = await fetch(`${API}/sync/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ syncStats: data });
    } catch (err) {
      set({ error: String(err) });
    }
  },

  fetchIdentity: async () => {
    try {
      const res = await fetch(`${API}/identity`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      set({ identity: data });
    } catch (err) {
      set({ error: String(err) });
    }
  },

  createInvitation: async (req) => {
    const res = await fetch(`${API}/invite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `HTTP ${res.status}`);
    }
    const data: InviteResult = await res.json();
    // Refresh satellites after invite
    get().fetchSatellites();
    return data;
  },

  cancelJob: async (jobId: string) => {
    try {
      const res = await fetch(`${API}/jobs/${jobId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      get().fetchJobs();
      get().fetchJobStats();
    } catch (err) {
      set({ error: String(err) });
    }
  },

  triggerSync: async (nodeId: string) => {
    try {
      const res = await fetch(`${API}/sync/trigger/${nodeId}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      get().fetchSyncStats();
    } catch (err) {
      set({ error: String(err) });
    }
  },

  registerAsSatellite: async (centralUrl: string, code: string, name: string, mode: string) => {
    const url = `${centralUrl.replace(/\/$/, '')}/api/v1/yeyonet/register`;
    // Ensure code has dashes: YEYO-XXXX-XXXX-XXXX
    let formatted = code.replace(/-/g, '');
    if (formatted.length === 16) {
      formatted = `${formatted.slice(0,4)}-${formatted.slice(4,8)}-${formatted.slice(8,12)}-${formatted.slice(12,16)}`;
    }
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: formatted, node_name: name, mode }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail ?? err);
      throw new Error(detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
}));
