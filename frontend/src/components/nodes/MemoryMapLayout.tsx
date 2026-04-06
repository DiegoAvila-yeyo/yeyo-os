/**
 * YeyoOS — MemoryMapLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Observatorio visual de Flash Memory.
 * 3 vistas: Árbol jerárquico | Heatmap namespace×tier | Activity log en vivo
 */
'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';

const API = 'http://localhost:8000/api/v1/memory';

// ─── Types ─────────────────────────────────────────────────────────────────────
interface MapCell {
  namespace: string;
  tier: string;
  type: string;
  count: number;
  total_accesses: number;
  avg_importance: number;
}

interface NamespaceSummary {
  namespace: string;
  count: number;
  total_accesses: number;
}

interface AuditEvent {
  event_id: string;
  memory_id: string;
  action: string;
  details: Record<string, unknown>;
  timestamp: string | null;
  memory_content: string;
  memory_type: string;
  memory_tier: string;
  memory_namespace: string;
}

type ViewMode = 'tree' | 'heatmap' | 'activity';

// ─── Colores ───────────────────────────────────────────────────────────────────
const TIER_COLORS: Record<string, string> = {
  HOT: '#ff5050',
  WARM: '#ffb900',
  COLD: '#4fc3f7',
};

const TIER_BG: Record<string, string> = {
  HOT: 'rgba(255,80,80,0.12)',
  WARM: 'rgba(255,185,0,0.10)',
  COLD: 'rgba(79,195,247,0.10)',
};

const TYPE_ICON: Record<string, string> = {
  conversation: '💬',
  preference: '⭐',
  fact: '📌',
  correction: '✏️',
  skill: '🧠',
};

const NS_ICON: Record<string, string> = {
  'chat': '💬',
  'imagen': '🖼️',
  'codigo': '💻',
  'video': '🎬',
  'automatizacion': '⚡',
  'sistema': '⚙️',
  'descartado': '🗑️',
};

const ACTION_ICON: Record<string, string> = {
  CREATE: '🆕',
  PROMOTE: '⬆️',
  DEMOTE: '⬇️',
  ACCESS: '👁️',
  UPDATE: '✏️',
};

function getNsIcon(ns: string): string {
  const domain = ns.split(':')[0];
  return NS_ICON[domain] || '📎';
}

// ─── Vista: Árbol jerárquico ───────────────────────────────────────────────────
function TreeView({ cells, namespaces }: { cells: MapCell[]; namespaces: NamespaceSummary[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(namespaces.map(n => n.namespace)));

  const toggle = (ns: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(ns) ? next.delete(ns) : next.add(ns);
      return next;
    });
  };

  // Group cells by namespace
  const grouped: Record<string, MapCell[]> = {};
  for (const c of cells) {
    (grouped[c.namespace] ??= []).push(c);
  }

  const totalMemories = namespaces.reduce((s, n) => s + n.count, 0);

  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ fontSize: 10, color: '#556', fontFamily: 'monospace', marginBottom: 12, letterSpacing: 1 }}>
        FLASH MEMORY — {totalMemories} MEMORIAS EN {namespaces.length} NAMESPACES
      </div>

      {namespaces.map(ns => {
        const isOpen = expanded.has(ns.namespace);
        const nsCells = grouped[ns.namespace] || [];
        const domain = ns.namespace.split(':')[0];
        const sublayer = ns.namespace.split(':')[1] || '';
        const pct = totalMemories > 0 ? (ns.count / totalMemories * 100) : 0;

        return (
          <div key={ns.namespace} style={{ marginBottom: 8 }}>
            {/* Namespace header */}
            <div
              onClick={() => toggle(ns.namespace)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                background: 'rgba(79,195,247,0.04)', borderRadius: 8,
                cursor: 'pointer', border: '1px solid #1a1a2e',
                transition: 'background 150ms',
              }}
            >
              <span style={{ fontSize: 14 }}>{getNsIcon(ns.namespace)}</span>
              <span style={{ fontSize: 12, color: '#e0f7fa', fontFamily: 'monospace', fontWeight: 600 }}>
                {domain}
              </span>
              <span style={{ fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace' }}>
                :{sublayer}
              </span>
              <span style={{ fontSize: 10, color: '#556', fontFamily: 'monospace', marginLeft: 'auto' }}>
                {ns.count} mem
              </span>
              {/* Bar */}
              <div style={{ width: 60, height: 6, background: '#0d0d1a', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  width: `${pct}%`, height: '100%',
                  background: `linear-gradient(90deg, #4fc3f7, #00bcd4)`,
                  borderRadius: 3,
                }} />
              </div>
              <span style={{ fontSize: 11, color: '#556', transition: 'transform 200ms', transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}>
                ▶
              </span>
            </div>

            {/* Children: tier × type breakdown */}
            {isOpen && (
              <div style={{ marginLeft: 28, marginTop: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
                {nsCells.map(cell => (
                  <div
                    key={`${cell.tier}-${cell.type}`}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '5px 10px', borderRadius: 6,
                      background: TIER_BG[cell.tier] || 'transparent',
                      border: `1px solid ${TIER_COLORS[cell.tier] || '#1a1a2e'}22`,
                    }}
                  >
                    <span style={{ fontSize: 11 }}>{TYPE_ICON[cell.type] || '📎'}</span>
                    <span style={{
                      fontSize: 9, fontFamily: 'monospace', padding: '1px 5px',
                      borderRadius: 3, background: TIER_BG[cell.tier],
                      border: `1px solid ${TIER_COLORS[cell.tier] || '#556'}`,
                      color: TIER_COLORS[cell.tier] || '#556',
                    }}>
                      {cell.tier}
                    </span>
                    <span style={{ fontSize: 10, color: '#90caf9', fontFamily: 'monospace' }}>
                      {cell.type}
                    </span>
                    <span style={{ fontSize: 10, color: '#778', fontFamily: 'monospace', marginLeft: 'auto' }}>
                      ×{cell.count}
                    </span>
                    <span style={{ fontSize: 9, color: '#556', fontFamily: 'monospace' }}>
                      👁️{cell.total_accesses}
                    </span>
                    {/* Importance dot */}
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: `hsl(${cell.avg_importance * 120}, 80%, 50%)`,
                    }} title={`Importancia: ${(cell.avg_importance * 100).toFixed(0)}%`} />
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Vista: Heatmap namespace × tier ──────────────────────────────────────────
function HeatmapView({ cells, namespaces }: { cells: MapCell[]; namespaces: NamespaceSummary[] }) {
  const tiers = ['HOT', 'WARM', 'COLD'];

  // Aggregate by namespace × tier
  const heatData: Record<string, Record<string, { count: number; accesses: number }>> = {};
  let maxCount = 1;

  for (const c of cells) {
    if (!heatData[c.namespace]) heatData[c.namespace] = {};
    if (!heatData[c.namespace][c.tier]) heatData[c.namespace][c.tier] = { count: 0, accesses: 0 };
    heatData[c.namespace][c.tier].count += c.count;
    heatData[c.namespace][c.tier].accesses += c.total_accesses;
    maxCount = Math.max(maxCount, heatData[c.namespace][c.tier].count);
  }

  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ fontSize: 10, color: '#556', fontFamily: 'monospace', marginBottom: 16, letterSpacing: 1 }}>
        HEATMAP — NAMESPACE × TIER (intensidad = cantidad de memorias)
      </div>

      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: '180px repeat(3, 1fr)', gap: 4, marginBottom: 4 }}>
        <div />
        {tiers.map(t => (
          <div key={t} style={{
            textAlign: 'center', fontSize: 10, fontFamily: 'monospace',
            color: TIER_COLORS[t], padding: '4px 0',
          }}>
            {t === 'HOT' ? '🔥' : t === 'WARM' ? '♨️' : '❄️'} {t}
          </div>
        ))}
      </div>

      {/* Rows */}
      {namespaces.map(ns => (
        <div
          key={ns.namespace}
          style={{ display: 'grid', gridTemplateColumns: '180px repeat(3, 1fr)', gap: 4, marginBottom: 4 }}
        >
          {/* NS label */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px',
            background: '#0d0d1a', borderRadius: 6, overflow: 'hidden',
          }}>
            <span style={{ fontSize: 12 }}>{getNsIcon(ns.namespace)}</span>
            <span style={{ fontSize: 10, color: '#b0bec5', fontFamily: 'monospace', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {ns.namespace}
            </span>
          </div>

          {/* Cells */}
          {tiers.map(tier => {
            const d = heatData[ns.namespace]?.[tier];
            const count = d?.count ?? 0;
            const accesses = d?.accesses ?? 0;
            const intensity = count / maxCount;
            const tierColor = TIER_COLORS[tier];

            return (
              <div
                key={tier}
                style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  padding: '8px 4px', borderRadius: 6,
                  background: count > 0
                    ? `rgba(${tier === 'HOT' ? '255,80,80' : tier === 'WARM' ? '255,185,0' : '79,195,247'},${0.05 + intensity * 0.35})`
                    : '#0a0a12',
                  border: count > 0 ? `1px solid ${tierColor}44` : '1px solid #111',
                  transition: 'all 300ms',
                  minHeight: 50,
                }}
              >
                {count > 0 ? (
                  <>
                    <span style={{ fontSize: 18, fontWeight: 700, color: tierColor, fontFamily: 'monospace' }}>
                      {count}
                    </span>
                    <span style={{ fontSize: 9, color: `${tierColor}88`, fontFamily: 'monospace' }}>
                      👁️{accesses}
                    </span>
                  </>
                ) : (
                  <span style={{ fontSize: 10, color: '#222' }}>—</span>
                )}
              </div>
            );
          })}
        </div>
      ))}

      {/* Legend */}
      <div style={{ marginTop: 20, display: 'flex', gap: 16, justifyContent: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(79,195,247,0.08)' }} />
          <span style={{ fontSize: 9, color: '#556', fontFamily: 'monospace' }}>Pocas</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(79,195,247,0.25)' }} />
          <span style={{ fontSize: 9, color: '#556', fontFamily: 'monospace' }}>Varias</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: 'rgba(79,195,247,0.40)' }} />
          <span style={{ fontSize: 9, color: '#556', fontFamily: 'monospace' }}>Muchas</span>
        </div>
      </div>
    </div>
  );
}

// ─── Vista: Activity Log ──────────────────────────────────────────────────────
function ActivityView() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debug/audit?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      setEvents(data.events ?? []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
    // Poll every 5 seconds for "live" updates
    intervalRef.current = setInterval(fetchEvents, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchEvents]);

  const formatTime = (ts: string | null) => {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div style={{ padding: 16, overflowY: 'auto', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 10, color: '#556', fontFamily: 'monospace', letterSpacing: 1 }}>
          ACTIVIDAD EN VIVO — {events.length} eventos (polling 5s)
        </span>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4caf50', animation: 'pulse 2s infinite' }} />
      </div>

      {loading ? (
        <div style={{ color: '#556', fontSize: 12, fontFamily: 'monospace', textAlign: 'center', padding: 40 }}>
          Cargando actividad…
        </div>
      ) : events.length === 0 ? (
        <div style={{ color: '#334', fontSize: 12, fontFamily: 'monospace', textAlign: 'center', padding: 40 }}>
          Sin actividad registrada
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {events.map(ev => (
            <div
              key={ev.event_id}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 8,
                padding: '8px 12px', borderRadius: 8,
                background: '#0d0d1a', border: '1px solid #1a1a2e',
                transition: 'background 200ms',
              }}
            >
              {/* Time */}
              <span style={{ fontSize: 10, color: '#445', fontFamily: 'monospace', whiteSpace: 'nowrap', minWidth: 65 }}>
                {formatTime(ev.timestamp)}
              </span>

              {/* Action icon */}
              <span style={{ fontSize: 14, minWidth: 20, textAlign: 'center' }}>
                {ACTION_ICON[ev.action] || '📝'}
              </span>

              {/* Action badge */}
              <span style={{
                fontSize: 9, fontFamily: 'monospace', padding: '2px 6px',
                borderRadius: 3, whiteSpace: 'nowrap',
                background: ev.action === 'CREATE' ? 'rgba(76,175,80,0.15)' :
                  ev.action === 'PROMOTE' ? 'rgba(255,80,80,0.12)' :
                  ev.action === 'DEMOTE' ? 'rgba(79,195,247,0.12)' : 'rgba(255,255,255,0.05)',
                color: ev.action === 'CREATE' ? '#4caf50' :
                  ev.action === 'PROMOTE' ? '#ff5050' :
                  ev.action === 'DEMOTE' ? '#4fc3f7' : '#778',
                border: `1px solid ${ev.action === 'CREATE' ? '#4caf5044' :
                  ev.action === 'PROMOTE' ? '#ff505044' :
                  ev.action === 'DEMOTE' ? '#4fc3f744' : '#33333344'}`,
              }}>
                {ev.action}
              </span>

              {/* Content */}
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 2 }}>
                  <span style={{ fontSize: 11 }}>{TYPE_ICON[ev.memory_type] || '📎'}</span>
                  <span style={{ fontSize: 10, color: '#90caf9', fontFamily: 'monospace' }}>
                    {ev.memory_namespace || '—'}
                  </span>
                  <span style={{
                    fontSize: 9, fontFamily: 'monospace', padding: '1px 4px',
                    borderRadius: 3,
                    background: TIER_BG[ev.memory_tier],
                    color: TIER_COLORS[ev.memory_tier],
                    border: `1px solid ${TIER_COLORS[ev.memory_tier] || '#556'}`,
                  }}>
                    {ev.memory_tier}
                  </span>
                </div>
                <p style={{
                  margin: 0, fontSize: 11, color: '#b0bec5', lineHeight: 1.4,
                  overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                }}>
                  {ev.memory_content || '—'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

// ─── Componente principal ──────────────────────────────────────────────────────
export function MemoryMapLayout() {
  const [view, setView] = useState<ViewMode>('tree');
  const [cells, setCells] = useState<MapCell[]>([]);
  const [namespaces, setNamespaces] = useState<NamespaceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDistribution = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/map/distribution`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCells(data.cells ?? []);
      setNamespaces(data.namespaces ?? []);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDistribution();
  }, [fetchDistribution]);

  const viewBtnStyle = (active: boolean): React.CSSProperties => ({
    fontSize: 11, padding: '5px 12px', borderRadius: 6, cursor: 'pointer',
    border: `1px solid ${active ? '#4fc3f7' : '#1E3A5F'}`,
    background: active ? 'rgba(79,195,247,0.15)' : 'transparent',
    color: active ? '#4fc3f7' : '#556',
    transition: 'all 150ms',
    fontFamily: 'monospace',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%', width: '100%',
      background: '#0a0a0f', color: '#b0bec5', fontFamily: 'monospace',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px', borderBottom: '1px solid #1E3A5F',
        background: '#0a0a0f',
      }}>
        <span style={{ fontSize: 11, color: '#4fc3f7', letterSpacing: 1 }}>🗺️ MEMORY MAP</span>

        <div style={{ display: 'flex', gap: 6, marginLeft: 16 }}>
          <button onClick={() => setView('tree')} style={viewBtnStyle(view === 'tree')}>
            🌳 Árbol
          </button>
          <button onClick={() => setView('heatmap')} style={viewBtnStyle(view === 'heatmap')}>
            🔥 Heatmap
          </button>
          <button onClick={() => setView('activity')} style={viewBtnStyle(view === 'activity')}>
            ⚡ Actividad
          </button>
        </div>

        <button
          onClick={fetchDistribution}
          style={{
            marginLeft: 'auto', fontSize: 11, padding: '4px 10px', borderRadius: 5,
            cursor: 'pointer', border: '1px solid #1E3A5F',
            background: 'transparent', color: '#556', fontFamily: 'monospace',
          }}
        >
          ↻ Actualizar
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(255,80,80,0.08)', color: '#ff5050', fontSize: 11, fontFamily: 'monospace' }}>
          ⚠ {error}
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {loading && view !== 'activity' ? (
          <div style={{ padding: 40, color: '#556', fontSize: 12, fontFamily: 'monospace', textAlign: 'center' }}>
            Cargando distribución de memorias…
          </div>
        ) : (
          <>
            {view === 'tree' && <TreeView cells={cells} namespaces={namespaces} />}
            {view === 'heatmap' && <HeatmapView cells={cells} namespaces={namespaces} />}
            {view === 'activity' && <ActivityView />}
          </>
        )}
      </div>
    </div>
  );
}
