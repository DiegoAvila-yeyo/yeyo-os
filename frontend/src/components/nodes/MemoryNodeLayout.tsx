/**
 * YeyoOS — MemoryNodeLayout
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Vista del nodo de Memoria (Flash Memory).
 * Layout de 3 columnas:
 *   [Lista + filtros (280px)] | [Detalle + Stats (flex)] | [Chat IA (300px)]
 */
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useMemoryStore } from '@/stores/memoryStore';
import type { Memory, MemoryTier, MemoryType } from '@/types';

// ─── Colores por tier ──────────────────────────────────────────────────────────
const TIER_COLOR: Record<MemoryTier, { bg: string; border: string; label: string }> = {
  HOT:  { bg: 'rgba(255,80,80,0.12)',   border: '#ff5050', label: '🔥 HOT'  },
  WARM: { bg: 'rgba(255,185,0,0.10)',   border: '#ffb900', label: '♨️ WARM' },
  COLD: { bg: 'rgba(79,195,247,0.10)',  border: '#4fc3f7', label: '❄️ COLD' },
};

const TYPE_ICON: Record<MemoryType, string> = {
  conversation: '💬',
  preference:   '⭐',
  fact:         '📌',
  correction:   '✏️',
  skill:        '🧠',
};

// ─── Componente: badge de tier ─────────────────────────────────────────────────
function TierBadge({ tier }: { tier: MemoryTier }) {
  const c = TIER_COLOR[tier];
  return (
    <span style={{
      fontSize: 10, fontFamily: 'monospace', padding: '2px 6px',
      borderRadius: 4, background: c.bg, border: `1px solid ${c.border}`,
      color: c.border, whiteSpace: 'nowrap',
    }}>
      {c.label}
    </span>
  );
}

// ─── Componente: ítem de memoria en la lista ───────────────────────────────────
function MemoryItem({ memory, selected, onSelect }: {
  memory: Memory;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      style={{
        padding: '10px 12px',
        borderBottom: '1px solid #1a1a2e',
        cursor: 'pointer',
        background: selected ? 'rgba(79,195,247,0.08)' : 'transparent',
        borderLeft: selected ? '2px solid #4fc3f7' : '2px solid transparent',
        transition: 'background 150ms',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 13 }}>{TYPE_ICON[memory.type] ?? '📎'}</span>
        <TierBadge tier={memory.tier} />
        <span style={{ fontSize: 10, color: '#556', marginLeft: 'auto', fontFamily: 'monospace' }}>
          ×{memory.access_count}
        </span>
      </div>
      <p style={{
        margin: 0, fontSize: 12, color: '#b0bec5', lineHeight: 1.4,
        overflow: 'hidden', display: '-webkit-box',
        WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
      }}>
        {memory.content}
      </p>
      {memory.created_at && (
        <span style={{ fontSize: 10, color: '#445', fontFamily: 'monospace' }}>
          {new Date(memory.created_at).toLocaleDateString('es-MX', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
    </div>
  );
}

// ─── Componente: panel de estadísticas ────────────────────────────────────────
function StatsPanel() {
  const { stats, loadingStats } = useMemoryStore();

  if (loadingStats) return (
    <div style={{ padding: 16, color: '#556', fontSize: 12, fontFamily: 'monospace' }}>
      Cargando estadísticas...
    </div>
  );
  if (!stats) return null;

  return (
    <div style={{ padding: '16px', borderBottom: '1px solid #1a1a2e' }}>
      <p style={{ margin: '0 0 10px', fontSize: 11, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 1 }}>
        ESTADÍSTICAS GLOBALES
      </p>
      {/* Total */}
      <div style={{ fontSize: 28, fontWeight: 700, color: '#e0f7fa', fontFamily: 'monospace', marginBottom: 12 }}>
        {stats.total_memories}
        <span style={{ fontSize: 12, color: '#556', marginLeft: 8 }}>memorias totales</span>
      </div>
      {/* Por tier */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {(['HOT', 'WARM', 'COLD'] as MemoryTier[]).map(tier => {
          const count = stats.by_tier?.[tier] ?? 0;
          const c = TIER_COLOR[tier];
          return (
            <div key={tier} style={{
              flex: 1, minWidth: 60, padding: '8px 10px', borderRadius: 8,
              background: c.bg, border: `1px solid ${c.border}`, textAlign: 'center',
            }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: c.border, fontFamily: 'monospace' }}>{count}</div>
              <div style={{ fontSize: 10, color: c.border, opacity: 0.8 }}>{c.label}</div>
            </div>
          );
        })}
      </div>
      {/* Por tipo */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {Object.entries(stats.by_type ?? {}).map(([type, count]) => (
          <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#778', fontFamily: 'monospace' }}>
              {TYPE_ICON[type as MemoryType] ?? '📎'} {type}
            </span>
            <span style={{ fontSize: 11, color: '#90caf9', fontFamily: 'monospace' }}>{String(count)}</span>
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span style={{ fontSize: 11, color: '#778', fontFamily: 'monospace' }}>🔗 asociaciones</span>
          <span style={{ fontSize: 11, color: '#90caf9', fontFamily: 'monospace' }}>{stats.total_associations}</span>
        </div>
      </div>
    </div>
  );
}

// ─── Componente: detalle de una memoria ───────────────────────────────────────
function MemoryDetail({ memory }: { memory: Memory }) {
  const { associations, loadingAssociations } = useMemoryStore();
  const c = TIER_COLOR[memory.tier];

  return (
    <div style={{ padding: 20, overflowY: 'auto', height: '100%' }}>
      {/* Cabecera */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span style={{ fontSize: 20 }}>{TYPE_ICON[memory.type] ?? '📎'}</span>
        <TierBadge tier={memory.tier} />
        <span style={{ fontSize: 11, color: '#556', fontFamily: 'monospace', marginLeft: 'auto' }}>
          accesos: {memory.access_count}
        </span>
      </div>

      {/* Contenido */}
      <div style={{
        background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10,
        padding: '14px 16px', marginBottom: 16,
      }}>
        <p style={{ margin: 0, fontSize: 14, color: '#e0f7fa', lineHeight: 1.6 }}>
          {memory.content}
        </p>
      </div>

      {/* Metadatos */}
      <div style={{ marginBottom: 16 }}>
        <p style={{ margin: '0 0 8px', fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 1 }}>
          METADATOS
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>
          {[
            ['Tipo',       memory.type],
            ['Fuente',     memory.source],
            ['Namespace',  memory.namespace || '—'],
            ['Checksum',   memory.checksum?.slice(0, 12) + '…'],
            ['Creado',     memory.created_at ? new Date(memory.created_at).toLocaleString('es-MX') : '—'],
            ['Accedido',   memory.accessed_at ? new Date(memory.accessed_at).toLocaleString('es-MX') : '—'],
          ].map(([label, value]) => (
            <React.Fragment key={label}>
              <span style={{ fontSize: 10, color: '#556', fontFamily: 'monospace' }}>{label}</span>
              <span style={{ fontSize: 10, color: '#90caf9', fontFamily: 'monospace', wordBreak: 'break-all' }}>{value}</span>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Metadata JSON si hay */}
      {memory.metadata && Object.keys(memory.metadata).length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ margin: '0 0 6px', fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 1 }}>
            METADATA JSON
          </p>
          <pre style={{
            margin: 0, padding: 10, background: '#0d0d1a', borderRadius: 6,
            fontSize: 10, color: '#b0bec5', overflow: 'auto', maxHeight: 120,
          }}>
            {JSON.stringify(memory.metadata, null, 2)}
          </pre>
        </div>
      )}

      {/* Asociaciones */}
      <div>
        <p style={{ margin: '0 0 8px', fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 1 }}>
          ASOCIACIONES ({associations.length})
        </p>
        {loadingAssociations ? (
          <span style={{ fontSize: 11, color: '#556', fontFamily: 'monospace' }}>Cargando…</span>
        ) : associations.length === 0 ? (
          <span style={{ fontSize: 11, color: '#334', fontFamily: 'monospace' }}>Sin asociaciones</span>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {associations.map(a => (
              <div key={a.id} style={{
                padding: '8px 10px', background: '#0d0d1a', borderRadius: 6,
                border: '1px solid #1a1a2e',
              }}>
                <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                  <TierBadge tier={a.tier} />
                  {a.relation_type && (
                    <span style={{ fontSize: 10, color: '#556', fontFamily: 'monospace' }}>
                      {a.relation_type}
                    </span>
                  )}
                  {a.strength != null && (
                    <span style={{ fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', marginLeft: 'auto' }}>
                      {(a.strength * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <p style={{ margin: 0, fontSize: 11, color: '#b0bec5', lineHeight: 1.4 }}>
                  {a.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Componente principal ──────────────────────────────────────────────────────
export function MemoryNodeLayout() {
  const {
    memories, stats, selectedMemory, searchQuery, filters, loading, error,
    fetchRecent, fetchStats, searchMemories, selectMemory, setSearchQuery, setFilter, clearError,
  } = useMemoryStore();

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [chatMessages, setChatMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; content: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Carga inicial
  useEffect(() => {
    fetchRecent(50);
    fetchStats();
  }, [fetchRecent, fetchStats]);

  // Scroll chat al final
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Búsqueda con debounce
  const handleSearch = useCallback((q: string) => {
    setSearchQuery(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      searchMemories(q, 50);
    }, 400);
  }, [setSearchQuery, searchMemories]);

  // Filtrado local por tier/type
  const memoriasFiltradas = memories.filter(m => {
    if (filters.tier !== 'ALL' && m.tier !== filters.tier) return false;
    if (filters.type !== 'ALL' && m.type !== filters.type) return false;
    return true;
  });

  // Chat con memoria (busca en flash memory)
  const handleChatSend = useCallback(async () => {
    const msg = chatInput.trim();
    if (!msg) return;
    const userMsg = { id: `mem-${Date.now()}`, role: 'user' as const, content: msg };
    const loadingId = `mem-loading-${Date.now()}`;
    setChatMessages(prev => [...prev, userMsg, { id: loadingId, role: 'assistant', content: '🔍 Buscando en memorias…' }]);
    setChatInput('');
    try {
      const params = new URLSearchParams({ q: msg, limit: '10', threshold: '0.3' });
      const res = await fetch(`http://localhost:8000/api/v1/memory/search?${params}`);
      const data = await res.json();
      const results: Memory[] = data.results ?? [];
      let reply = results.length === 0
        ? '❌ No encontré memorias relacionadas.'
        : `Encontré **${results.length}** memori${results.length === 1 ? 'a' : 'as'} relacionada${results.length === 1 ? '' : 's'}:\n\n` +
          results.map((m, i) =>
            `**${i + 1}.** ${TYPE_ICON[m.type]} \`${m.tier}\` — ${m.content.slice(0, 120)}${m.content.length > 120 ? '…' : ''}`
          ).join('\n\n');
      setChatMessages(prev =>
        prev.map(m => m.id === loadingId ? { ...m, content: reply } : m)
      );
      if (results.length > 0) {
        // Actualiza la lista principal con los resultados de búsqueda
        searchMemories(msg);
      }
    } catch (err) {
      setChatMessages(prev =>
        prev.map(m => m.id === loadingId ? { ...m, content: `❌ Error: ${err}` } : m)
      );
    }
  }, [chatInput, searchMemories]);

  // ─── Estilos base ────────────────────────────────────────────────────────────
  const S = {
    root: {
      display: 'flex', height: '100%', width: '100%',
      background: '#0a0a0f', color: '#b0bec5', fontFamily: 'monospace',
      overflow: 'hidden',
    } as React.CSSProperties,
    col: (width: number | string, border = true) => ({
      width, flexShrink: 0, display: 'flex', flexDirection: 'column' as const,
      borderRight: border ? '1px solid #1E3A5F' : 'none', overflow: 'hidden',
    }),
    colHeader: {
      padding: '10px 14px', borderBottom: '1px solid #1E3A5F',
      fontSize: 11, color: '#4fc3f7', letterSpacing: 1, background: '#0a0a0f',
    } as React.CSSProperties,
  };

  return (
    <div style={S.root}>

      {/* ── COL 1: Lista de memorias (280px) ──────────────────────────────── */}
      <div style={{ ...S.col(280), flexShrink: 0 }}>
        <div style={S.colHeader}>🧠 FLASH MEMORY</div>

        {/* Barra de búsqueda */}
        <div style={{ padding: '8px 10px', borderBottom: '1px solid #1a1a2e' }}>
          <input
            value={searchQuery}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Buscar memorias…"
            style={{
              width: '100%', background: '#0d0d1a', border: '1px solid #1E3A5F',
              borderRadius: 6, padding: '6px 10px', color: '#e0f7fa', fontSize: 12,
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Filtros */}
        <div style={{ display: 'flex', gap: 6, padding: '6px 10px', borderBottom: '1px solid #1a1a2e', flexWrap: 'wrap' }}>
          {/* Tier */}
          {(['ALL', 'HOT', 'WARM', 'COLD'] as const).map(t => (
            <button
              key={t}
              onClick={() => { setFilter('tier', t); }}
              style={{
                fontSize: 10, padding: '3px 7px', borderRadius: 4, cursor: 'pointer',
                border: `1px solid ${filters.tier === t ? '#4fc3f7' : '#1E3A5F'}`,
                background: filters.tier === t ? 'rgba(79,195,247,0.15)' : 'transparent',
                color: filters.tier === t ? '#4fc3f7' : '#556',
              }}
            >
              {t === 'ALL' ? 'Todos' : TIER_COLOR[t as MemoryTier].label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6, padding: '6px 10px', borderBottom: '1px solid #1a1a2e', flexWrap: 'wrap' }}>
          {/* Type */}
          {(['ALL', 'conversation', 'preference', 'fact', 'correction', 'skill'] as const).map(t => (
            <button
              key={t}
              onClick={() => setFilter('type', t)}
              style={{
                fontSize: 10, padding: '3px 7px', borderRadius: 4, cursor: 'pointer',
                border: `1px solid ${filters.type === t ? '#4fc3f7' : '#1E3A5F'}`,
                background: filters.type === t ? 'rgba(79,195,247,0.15)' : 'transparent',
                color: filters.type === t ? '#4fc3f7' : '#556',
              }}
            >
              {t === 'ALL' ? 'Todos' : `${TYPE_ICON[t as MemoryType]} ${t}`}
            </button>
          ))}
        </div>

        {/* Contador */}
        <div style={{ padding: '4px 12px', fontSize: 10, color: '#334', borderBottom: '1px solid #1a1a2e' }}>
          {loading ? 'Cargando…' : `${memoriasFiltradas.length} memorias`}
          {error && <span style={{ color: '#ff5050', marginLeft: 8 }}>⚠ {error}</span>}
        </div>

        {/* Lista */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {!loading && memoriasFiltradas.length === 0 && (
            <div style={{ padding: 20, color: '#334', fontSize: 11, textAlign: 'center' }}>
              Sin memorias
            </div>
          )}
          {memoriasFiltradas.map(m => (
            <MemoryItem
              key={m.id}
              memory={m}
              selected={selectedMemory?.id === m.id}
              onSelect={() => selectMemory(m)}
            />
          ))}
        </div>
      </div>

      {/* ── COL 2: Detalle / Stats (flex) ─────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', borderRight: '1px solid #1E3A5F' }}>
        <div style={S.colHeader}>
          {selectedMemory ? `DETALLE — ${selectedMemory.id.slice(0, 8)}…` : 'ESTADÍSTICAS'}
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {selectedMemory ? (
            <>
              <div style={{ padding: '6px 14px', borderBottom: '1px solid #1a1a2e' }}>
                <button
                  onClick={() => selectMemory(null)}
                  style={{
                    fontSize: 10, padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
                    border: '1px solid #1E3A5F', background: 'transparent', color: '#556',
                  }}
                >
                  ← Volver a estadísticas
                </button>
              </div>
              <MemoryDetail memory={selectedMemory} />
            </>
          ) : (
            <StatsPanel />
          )}
        </div>

        {/* Botón refrescar */}
        <div style={{ padding: '8px 14px', borderTop: '1px solid #1a1a2e', display: 'flex', gap: 8 }}>
          <button
            onClick={() => { fetchRecent(50); fetchStats(); }}
            style={{
              fontSize: 11, padding: '5px 12px', borderRadius: 6, cursor: 'pointer',
              border: '1px solid #1E3A5F', background: 'rgba(79,195,247,0.08)',
              color: '#4fc3f7',
            }}
          >
            ↻ Actualizar
          </button>
        </div>
      </div>

      {/* ── COL 3: Chat IA (300px) ─────────────────────────────────────────── */}
      <div style={{ ...S.col(300, false), width: 300 }}>
        <div style={S.colHeader}>💬 BUSCAR EN MEMORIA</div>

        {/* Mensajes */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {chatMessages.length === 0 && (
            <div style={{ color: '#334', fontSize: 11, textAlign: 'center', marginTop: 20 }}>
              Pregunta algo para buscar en las memorias semánticamente
            </div>
          )}
          {chatMessages.map(msg => (
            <div
              key={msg.id}
              style={{
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '88%',
                padding: '8px 12px',
                borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                background: msg.role === 'user' ? 'rgba(79,195,247,0.15)' : '#0d0d1a',
                border: `1px solid ${msg.role === 'user' ? '#4fc3f7' : '#1E3A5F'}`,
                fontSize: 12, color: '#e0f7fa', lineHeight: 1.5, whiteSpace: 'pre-wrap',
              }}
            >
              {msg.content}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '8px 10px', borderTop: '1px solid #1E3A5F', display: 'flex', gap: 6 }}>
          <input
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleChatSend()}
            placeholder="¿Qué recuerdas sobre…?"
            style={{
              flex: 1, background: '#0d0d1a', border: '1px solid #1E3A5F',
              borderRadius: 6, padding: '7px 10px', color: '#e0f7fa', fontSize: 12, outline: 'none',
            }}
          />
          <button
            onClick={handleChatSend}
            style={{
              padding: '7px 12px', borderRadius: 6, cursor: 'pointer',
              background: 'rgba(79,195,247,0.15)', border: '1px solid #4fc3f7',
              color: '#4fc3f7', fontSize: 12,
            }}
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
