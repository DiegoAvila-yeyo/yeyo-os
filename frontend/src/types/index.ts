// YeyoOS Type Definitions — Micro-fase 0.5

export interface Node {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  label: string;
  status: 'active' | 'idle' | 'error';
}

export type NodeType =
  | 'central'
  | 'chat'
  | 'image'
  | 'video'
  | 'code'
  | 'automation'
  | 'files'
  | 'browser'
  | 'config'
  | 'memory'
  | 'network'
  | 'workflow'
  | 'observatory'
  | 'arena';

// ─── Flash Memory Types ────────────────────────────────────────────────────────

export type MemoryTier = 'HOT' | 'WARM' | 'COLD';
export type MemoryType = 'conversation' | 'preference' | 'fact' | 'correction' | 'skill';

/** Memoria individual tal como la devuelve el backend */
export interface Memory {
  id: string;
  content: string;
  type: MemoryType;
  tier: MemoryTier;
  checksum: string;
  access_count: number;
  metadata: Record<string, unknown>;
  source: string;
  namespace?: string;
  importance?: number;
  tags?: string[];
  created_at: string | null;
  accessed_at: string | null;
}

/** Respuesta de /api/v1/memory/search */
export interface MemorySearchResponse {
  results: Memory[];
  total: number;
  query: string;
}

/** Respuesta de /api/v1/memory/stats */
export interface MemoryStats {
  total_memories: number;
  by_tier: Record<MemoryTier, number>;
  by_type: Record<MemoryType, number>;
  total_associations: number;
}

/** Asociación entre dos memorias */
export interface MemoryAssociation {
  id: string;
  content: string;
  type: MemoryType;
  tier: MemoryTier;
  relation_type: string | null;
  strength: number | null;
}
