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
  assigned_to?: string;
  progress?: number;
  progress_detail?: string;
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
    assigned: number;
    running: number;
    completed: number;
    failed: number;
    cancelled: number;
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
  suggested_central_urls: string[];
}

export interface InviteResult {
  code: string;
  satellite_name: string;
  expires_at: string;
}

export interface ConnectionStatus {
  configured: boolean;
  connected: boolean;
  central_ws_url: string | null;
  node_id: string | null;
  central_name: string | null;
  connected_at: string | null;
}

export type YeyoNetTab = 'satellites' | 'render' | 'sync' | 'config';

interface YeyoNetState {
  satellites: Satellite[];
  jobs: Job[];
  jobStats: JobStats | null;
  syncStats: SyncStats | null;
  identity: NodeIdentity | null;
  connectionStatus: ConnectionStatus | null;
  activeTab: YeyoNetTab;
  loading: boolean;
  error: string | null;

  setActiveTab: (tab: YeyoNetTab) => void;
  fetchSatellites: () => Promise<void>;
  fetchJobs: (status?: string) => Promise<void>;
  fetchJobStats: () => Promise<void>;
  fetchSyncStats: () => Promise<void>;
  fetchIdentity: () => Promise<void>;
  fetchConnectionStatus: () => Promise<void>;
  connectAsSatellite: (config?: {
    node_id: string;
    auth_token: string;
    central_ws_url: string;
    central_name?: string;
  }) => Promise<void>;
  disconnectSatellite: () => Promise<void>;
  createInvitation: (req: {
    satellite_name: string;
    permissions: string[];
    visibility_level: number;
    expires_in_days: number;
  }) => Promise<InviteResult>;
  cancelJob: (jobId: string) => Promise<void>;
  triggerSync: (nodeId: string) => Promise<void>;
  registerAsSatellite: (centralUrl: string, code: string, name: string, mode: string) => Promise<{ node_id: string; auth_token: string; central_ws_url: string }>;
  clearError: () => void;
}

const API = '/api/v1/yeyonet';
const DEGRADED_PG_DETAIL = 'PostgreSQL not available';

async function readApiError(res: Response): Promise<string> {
  try {
    const text = await res.text();
    if (!text) return `HTTP ${res.status}`;

    try {
      const parsed = JSON.parse(text) as { detail?: unknown; error?: unknown };
      if (typeof parsed.detail === 'string' && parsed.detail.trim()) return parsed.detail;
      if (typeof parsed.error === 'string' && parsed.error.trim()) return parsed.error;
      const serialized = JSON.stringify(parsed.detail ?? parsed.error ?? parsed);
      return serialized !== '{}' ? serialized : `HTTP ${res.status}`;
    } catch {
      return text;
    }
  } catch {
    return `HTTP ${res.status}`;
  }
}

function isDegradedYeyoNetError(message: string): boolean {
  return message.includes(DEGRADED_PG_DETAIL);
}

function makeFallbackIdentity(current: ConnectionStatus | null): NodeIdentity {
  return {
    node_id: current?.node_id || 'local-no-db',
    node_name: current?.configured ? 'Satellite (degraded)' : 'Local (degraded)',
    role: current?.configured ? 'satellite' : 'degraded',
    suggested_central_urls: [],
  };
}

function normalizeIdentity(payload: unknown, current: ConnectionStatus | null): NodeIdentity {
  const data = payload && typeof payload === 'object'
    ? payload as Record<string, unknown>
    : {};

  const nodeId = typeof data.node_id === 'string' && data.node_id.trim()
    ? data.node_id
    : current?.node_id || 'local-no-db';
  const nodeName = typeof data.node_name === 'string' && data.node_name.trim()
    ? data.node_name
    : typeof data.name === 'string' && data.name.trim()
      ? data.name
      : (current?.configured ? 'Satellite (degraded)' : 'Local (degraded)');
  const role = typeof data.role === 'string' && data.role.trim()
    ? data.role
    : (current?.configured ? 'satellite' : 'degraded');
  const suggestedCentralUrls = Array.isArray(data.suggested_central_urls)
    ? data.suggested_central_urls.filter((url): url is string => typeof url === 'string' && url.trim().length > 0)
    : [];

  return {
    node_id: nodeId,
    node_name: nodeName,
    role,
    suggested_central_urls: suggestedCentralUrls,
  };
}

function emptyJobStats(): JobStats {
  return {
    total: 0,
    by_status: {
      queued: 0,
      assigned: 0,
      running: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    },
    by_type: {},
  };
}

function emptySyncStats(): SyncStats {
  return {
    total_memories: 0,
    synced_memories: 0,
    offline_queue_size: 0,
    offline_queues: {},
  };
}

export const useYeyoNetStore = create<YeyoNetState>((set, get) => ({
  satellites: [],
  jobs: [],
  jobStats: null,
  syncStats: null,
  identity: null,
  connectionStatus: null,
  activeTab: 'config',
  loading: false,
  error: null,

  setActiveTab: (tab) => set({ activeTab: tab }),
  clearError: () => set({ error: null }),

  fetchSatellites: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${API}/satellites`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      set({ satellites: Array.isArray(data) ? data : [], loading: false });
    } catch (err) {
      const message = String(err);
      if (isDegradedYeyoNetError(message)) {
        set({ satellites: [], loading: false });
        return;
      }
      set({ error: String(err), loading: false });
    }
  },

  fetchJobs: async (status?: string) => {
    set({ loading: true, error: null });
    try {
      const params = new URLSearchParams({ limit: '50' });
      if (status) params.set('status', status);
      const res = await fetch(`${API}/jobs?${params}`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      set({ jobs: Array.isArray(data) ? data : [], loading: false });
    } catch (err) {
      const message = String(err);
      if (isDegradedYeyoNetError(message)) {
        set({ jobs: [], loading: false });
        return;
      }
      set({ error: String(err), loading: false });
    }
  },

  fetchJobStats: async () => {
    try {
      const res = await fetch(`${API}/jobs/stats`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      set({ jobStats: data });
    } catch (err) {
      const message = String(err);
      if (isDegradedYeyoNetError(message)) {
        set({ jobStats: emptyJobStats() });
        return;
      }
      set({ error: String(err) });
    }
  },

  fetchSyncStats: async () => {
    try {
      const res = await fetch(`${API}/sync/stats`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      set({ syncStats: data });
    } catch (err) {
      const message = String(err);
      if (isDegradedYeyoNetError(message)) {
        set({ syncStats: emptySyncStats() });
        return;
      }
      set({ error: String(err) });
    }
  },

  fetchIdentity: async () => {
    try {
      const res = await fetch(`${API}/identity`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      set({ identity: normalizeIdentity(data, get().connectionStatus) });
    } catch (err) {
      const message = String(err);
      if (isDegradedYeyoNetError(message)) {
        set({ identity: makeFallbackIdentity(get().connectionStatus) });
        return;
      }
      set({ error: String(err) });
    }
  },

  fetchConnectionStatus: async () => {
    try {
      const res = await fetch(`${API}/connection`);
      if (!res.ok) throw new Error(await readApiError(res));
      const data = await res.json();
      const currentIdentity = get().identity;
      set({
        connectionStatus: data,
        identity: !currentIdentity || currentIdentity.role === 'degraded'
          ? makeFallbackIdentity(data)
          : currentIdentity,
      });
    } catch (err) {
      set({ error: String(err) });
    }
  },

  connectAsSatellite: async (config) => {
    try {
      const res = await fetch(`${API}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config ?? {}),
      });
      if (!res.ok) throw new Error(await readApiError(res));
      // Refresh connection status after a short delay to allow WS handshake
      setTimeout(() => get().fetchConnectionStatus(), 2000);
      get().fetchConnectionStatus();
    } catch (err) {
      set({ error: String(err) });
    }
  },

  disconnectSatellite: async () => {
    try {
      const res = await fetch(`${API}/disconnect`, { method: 'POST' });
      if (!res.ok) throw new Error(await readApiError(res));
      const disconnected = {
        configured: false,
        connected: false,
        central_ws_url: null,
        node_id: null,
        central_name: null,
        connected_at: null,
      };
      set({
        connectionStatus: disconnected,
        identity: makeFallbackIdentity(disconnected),
      });
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
    if (!res.ok) throw new Error(await readApiError(res));
    const data: InviteResult = await res.json();
    // Refresh satellites after invite
    get().fetchSatellites();
    return data;
  },

  cancelJob: async (jobId: string) => {
    try {
      const res = await fetch(`${API}/jobs/${jobId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(await readApiError(res));
      get().fetchJobs();
      get().fetchJobStats();
    } catch (err) {
      set({ error: String(err) });
    }
  },

  triggerSync: async (nodeId: string) => {
    try {
      const res = await fetch(`${API}/sync/trigger/${nodeId}`, { method: 'POST' });
      if (!res.ok) throw new Error(await readApiError(res));
      get().fetchSyncStats();
    } catch (err) {
      set({ error: String(err) });
    }
  },

  registerAsSatellite: async (centralUrl: string, code: string, name: string, mode: string) => {
    const central = centralUrl.trim().replace(/\/$/, '');
    // Ensure code has dashes: YEYO-XXXX-XXXX-XXXX
    let formatted = code.replace(/-/g, '');
    if (formatted.length === 16) {
      formatted = `${formatted.slice(0,4)}-${formatted.slice(4,8)}-${formatted.slice(8,12)}-${formatted.slice(12,16)}`;
    }
    const res = await fetch(`${API}/register-via-central`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ central_url: central, code: formatted, node_name: name, mode }),
    });
    if (!res.ok) throw new Error(await readApiError(res));
    const result = await res.json();

    // Save config and start WebSocket client via local backend
    await get().connectAsSatellite({
      node_id: result.node_id,
      auth_token: result.auth_token,
      central_ws_url: result.central_ws_url,
      central_name: central,
    });

    return result;
  },
}));
