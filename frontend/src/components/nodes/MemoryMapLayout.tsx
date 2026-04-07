/**
 * YeyoOS — MemoryMapLayout — "LA MÁQUINA"
 * Micro-fase 3.20 — Capa 3: Cuerpo
 *
 * Spaceship control-panel / AI-brain-monitor for Flash Memory.
 * 3 modes: ⚛️ Engine (radial core) | 📊 Gauges (circular meters) | 🖥️ Console (diagnostics)
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

type ViewMode = 'engine' | 'gauges' | 'console' | 'pipeline' | 'grafo';

// ─── Palette ───────────────────────────────────────────────────────────────────
const C = {
  bg: '#0a0a0f',
  bgPanel: '#0d1117',
  accent: '#4fc3f7',
  accentDim: 'rgba(79,195,247,0.25)',
  text: '#b0bec5',
  textDim: '#556',
  border: '#1E3A5F',
  hot: '#ff5050',
  warm: '#ffb900',
  cold: '#4fc3f7',
  green: '#00e676',
  red: '#ff1744',
} as const;

const TIER_COLORS: Record<string, string> = { HOT: C.hot, WARM: C.warm, COLD: C.cold };

const NS_ICON: Record<string, string> = {
  chat: '💬', imagen: '🖼️', codigo: '💻', video: '🎬',
  automatizacion: '⚡', sistema: '⚙️', descartado: '🗑️',
};

const ACTION_COLOR: Record<string, string> = {
  CREATE: C.green, PROMOTE: '#7c4dff', DEMOTE: C.warm, ACCESS: C.accent, UPDATE: '#ffab40',
};

function nsIcon(ns: string): string {
  return NS_ICON[ns.split(':')[0]] || '📎';
}

function nsLabel(ns: string): string {
  return ns.replace(':', ' › ');
}

function tierBreakdown(cells: MapCell[], namespace: string) {
  const nsCells = cells.filter(c => c.namespace === namespace);
  const hot = nsCells.filter(c => c.tier === 'HOT').reduce((s, c) => s + c.count, 0);
  const warm = nsCells.filter(c => c.tier === 'WARM').reduce((s, c) => s + c.count, 0);
  const cold = nsCells.filter(c => c.tier === 'COLD').reduce((s, c) => s + c.count, 0);
  return { hot, warm, cold, total: hot + warm + cold };
}

// ─── Keyframe Animations (injected once) ───────────────────────────────────────
const STYLE_TAG = `
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.85; }
}
@keyframes corePulse {
  0%, 100% { box-shadow: 0 0 30px rgba(79,195,247,0.4), 0 0 60px rgba(79,195,247,0.15), inset 0 0 30px rgba(79,195,247,0.1); }
  50% { box-shadow: 0 0 50px rgba(79,195,247,0.7), 0 0 100px rgba(79,195,247,0.3), inset 0 0 50px rgba(79,195,247,0.2); }
}
@keyframes glow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}
@keyframes fadeInLine {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
@keyframes scanline {
  0% { top: -2px; }
  100% { top: 100%; }
}
@keyframes dataFlow {
  0% { stroke-dashoffset: 20; }
  100% { stroke-dashoffset: 0; }
}
@keyframes gaugeAppear {
  from { opacity: 0; transform: scale(0.8); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes nodeFloat {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-4px); }
}
`;

// ═══════════════════════════════════════════════════════════════════════════════
// VIEW 1: ENGINE — Radial Core Visualization
// ═══════════════════════════════════════════════════════════════════════════════
function EngineView({ cells, namespaces }: { cells: MapCell[]; namespaces: NamespaceSummary[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 800, h: 600 });
  const [hoveredNs, setHoveredNs] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setDims({ w: width, h: height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const totalMemories = namespaces.reduce((s, n) => s + n.count, 0);
  const totalAccesses = namespaces.reduce((s, n) => s + n.total_accesses, 0);

  const cx = dims.w / 2;
  const cy = dims.h / 2;
  const orbitRadius = Math.min(dims.w, dims.h) * 0.34;
  const coreRadius = Math.min(dims.w, dims.h) * 0.09;
  const nodeRadius = Math.min(dims.w, dims.h) * 0.065;

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* Orbital ring */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
        <defs>
          <radialGradient id="coreGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={C.accent} stopOpacity="0.3" />
            <stop offset="100%" stopColor={C.accent} stopOpacity="0" />
          </radialGradient>
          <filter id="glowFilter">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Ambient glow behind core */}
        <circle cx={cx} cy={cy} r={orbitRadius * 0.6} fill="url(#coreGrad)" />

        {/* Orbit track */}
        <circle cx={cx} cy={cy} r={orbitRadius} fill="none" stroke={C.border}
          strokeWidth="1" strokeDasharray="4 8" opacity="0.5" />
        <circle cx={cx} cy={cy} r={orbitRadius} fill="none" stroke={C.accent}
          strokeWidth="0.5" strokeDasharray="2 6" opacity="0.3"
          style={{ animation: 'rotate 60s linear infinite', transformOrigin: `${cx}px ${cy}px` }} />

        {/* Connection lines from core to each namespace node */}
        {namespaces.map((ns, i) => {
          const angle = (2 * Math.PI * i) / namespaces.length - Math.PI / 2;
          const nx = cx + Math.cos(angle) * orbitRadius;
          const ny = cy + Math.sin(angle) * orbitRadius;
          const isHovered = hoveredNs === ns.namespace;
          return (
            <g key={ns.namespace}>
              <line x1={cx} y1={cy} x2={nx} y2={ny}
                stroke={isHovered ? C.accent : C.border} strokeWidth={isHovered ? 2 : 1}
                strokeDasharray="6 4" opacity={isHovered ? 0.9 : 0.35}
                style={{ animation: 'dataFlow 1.5s linear infinite' }}
                filter={isHovered ? 'url(#glowFilter)' : undefined} />
              {/* Data flow particles */}
              {isHovered && (
                <>
                  <circle r="2" fill={C.accent} opacity="0.8">
                    <animateMotion dur="2s" repeatCount="indefinite"
                      path={`M${cx},${cy} L${nx},${ny}`} />
                  </circle>
                  <circle r="2" fill={C.accent} opacity="0.5">
                    <animateMotion dur="2s" repeatCount="indefinite" begin="0.7s"
                      path={`M${cx},${cy} L${nx},${ny}`} />
                  </circle>
                </>
              )}
            </g>
          );
        })}
      </svg>

      {/* Central CORE */}
      <div style={{
        position: 'absolute',
        left: cx - coreRadius, top: cy - coreRadius,
        width: coreRadius * 2, height: coreRadius * 2,
        borderRadius: '50%',
        background: `radial-gradient(circle, rgba(79,195,247,0.15) 0%, ${C.bg} 70%)`,
        border: `2px solid ${C.accent}`,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        animation: 'corePulse 3s ease-in-out infinite',
        zIndex: 10,
        cursor: 'default',
      }}>
        <div style={{ fontSize: Math.max(10, coreRadius * 0.22), color: C.textDim, fontFamily: 'monospace', letterSpacing: 2, textTransform: 'uppercase' }}>
          CORE
        </div>
        <div style={{ fontSize: Math.max(18, coreRadius * 0.5), fontWeight: 700, color: C.accent, fontFamily: 'monospace' }}>
          {totalMemories}
        </div>
        <div style={{ fontSize: Math.max(8, coreRadius * 0.16), color: C.textDim, fontFamily: 'monospace' }}>
          {totalAccesses} acc
        </div>
      </div>

      {/* Namespace MODULES orbiting the core */}
      {namespaces.map((ns, i) => {
        const angle = (2 * Math.PI * i) / namespaces.length - Math.PI / 2;
        const nx = cx + Math.cos(angle) * orbitRadius;
        const ny = cy + Math.sin(angle) * orbitRadius;
        const tb = tierBreakdown(cells, ns.namespace);
        const total = tb.total || 1;
        const isHovered = hoveredNs === ns.namespace;
        const floatDelay = `${i * 0.3}s`;

        return (
          <div key={ns.namespace}
            onMouseEnter={() => setHoveredNs(ns.namespace)}
            onMouseLeave={() => setHoveredNs(null)}
            style={{
              position: 'absolute',
              left: nx - nodeRadius, top: ny - nodeRadius,
              width: nodeRadius * 2, height: nodeRadius * 2,
              borderRadius: '16px',
              background: isHovered
                ? `linear-gradient(135deg, rgba(79,195,247,0.12), rgba(79,195,247,0.04))`
                : C.bgPanel,
              border: `1.5px solid ${isHovered ? C.accent : C.border}`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              zIndex: 10,
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              transform: isHovered ? 'scale(1.12)' : 'scale(1)',
              boxShadow: isHovered ? `0 0 20px rgba(79,195,247,0.3)` : 'none',
              animation: `nodeFloat 4s ease-in-out infinite`,
              animationDelay: floatDelay,
              gap: 2,
              padding: 4,
            }}>
            <div style={{ fontSize: Math.max(14, nodeRadius * 0.3) }}>
              {nsIcon(ns.namespace)}
            </div>
            <div style={{
              fontSize: Math.max(8, nodeRadius * 0.14), color: C.text, fontFamily: 'monospace',
              textAlign: 'center', lineHeight: 1.1, maxWidth: '90%',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {ns.namespace.split(':')[1] || ns.namespace.split(':')[0]}
            </div>
            <div style={{ fontSize: Math.max(12, nodeRadius * 0.24), fontWeight: 700, color: '#fff', fontFamily: 'monospace' }}>
              {ns.count}
            </div>
            {/* Mini tier bar */}
            <div style={{
              width: '70%', height: 4, borderRadius: 2, overflow: 'hidden',
              display: 'flex', background: 'rgba(255,255,255,0.05)',
            }}>
              <div style={{ width: `${(tb.hot / total) * 100}%`, background: C.hot, height: '100%' }} />
              <div style={{ width: `${(tb.warm / total) * 100}%`, background: C.warm, height: '100%' }} />
              <div style={{ width: `${(tb.cold / total) * 100}%`, background: C.cold, height: '100%' }} />
            </div>
            <div style={{ fontSize: Math.max(7, nodeRadius * 0.11), color: C.textDim, fontFamily: 'monospace' }}>
              {ns.total_accesses} acc
            </div>
          </div>
        );
      })}

      {/* Floating label for hovered ns */}
      {hoveredNs && (
        <div style={{
          position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(13,17,23,0.95)', border: `1px solid ${C.accent}`,
          padding: '6px 16px', borderRadius: 8, fontFamily: 'monospace', fontSize: 12,
          color: C.accent, zIndex: 20, backdropFilter: 'blur(8px)',
        }}>
          {nsIcon(hoveredNs)} {nsLabel(hoveredNs)} — {(() => {
            const tb = tierBreakdown(cells, hoveredNs);
            return `🔴 ${tb.hot} HOT  🟠 ${tb.warm} WARM  🔵 ${tb.cold} COLD`;
          })()}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// VIEW 2: GAUGES — Circular Meters
// ═══════════════════════════════════════════════════════════════════════════════
function CircularGauge({ ns, cells, maxCount }: { ns: NamespaceSummary; cells: MapCell[]; maxCount: number }) {
  const size = 140;
  const strokeW = 10;
  const radius = (size - strokeW) / 2 - 4;
  const circumference = 2 * Math.PI * radius;
  const tb = tierBreakdown(cells, ns.namespace);
  const total = tb.total;
  const fillPct = maxCount > 0 ? total / maxCount : 0;

  const hotPct = total > 0 ? tb.hot / total : 0;
  const warmPct = total > 0 ? tb.warm / total : 0;
  const coldPct = total > 0 ? tb.cold / total : 0;

  const hotLen = hotPct * fillPct * circumference;
  const warmLen = warmPct * fillPct * circumference;
  const coldLen = coldPct * fillPct * circumference;

  const hotOffset = 0;
  const warmOffset = hotLen;
  const coldOffset = hotLen + warmLen;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
      animation: 'gaugeAppear 0.5s ease-out both',
      padding: 12,
    }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Track */}
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={strokeW} />
        {/* Cold segment */}
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={C.cold} strokeWidth={strokeW}
          strokeDasharray={`${coldLen} ${circumference - coldLen}`}
          strokeDashoffset={-coldOffset} strokeLinecap="round"
          style={{ transition: 'all 0.8s ease' }} />
        {/* Warm segment */}
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={C.warm} strokeWidth={strokeW}
          strokeDasharray={`${warmLen} ${circumference - warmLen}`}
          strokeDashoffset={-warmOffset} strokeLinecap="round"
          style={{ transition: 'all 0.8s ease' }} />
        {/* Hot segment */}
        <circle cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={C.hot} strokeWidth={strokeW}
          strokeDasharray={`${hotLen} ${circumference - hotLen}`}
          strokeDashoffset={-hotOffset} strokeLinecap="round"
          style={{ transition: 'all 0.8s ease' }} />
        {/* Center text */}
        <text x={size / 2} y={size / 2 - 6} textAnchor="middle" dominantBaseline="central"
          fill="#fff" fontSize="20" fontWeight="700" fontFamily="monospace"
          style={{ transform: 'rotate(90deg)', transformOrigin: 'center' }}>
          {total}
        </text>
        <text x={size / 2} y={size / 2 + 12} textAnchor="middle" dominantBaseline="central"
          fill={C.textDim} fontSize="8" fontFamily="monospace" letterSpacing="1"
          style={{ transform: 'rotate(90deg)', transformOrigin: 'center' }}>
          {ns.total_accesses} ACC
        </text>
      </svg>

      {/* Label */}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 16, marginBottom: 2 }}>{nsIcon(ns.namespace)}</div>
        <div style={{
          fontSize: 10, color: C.text, fontFamily: 'monospace',
          maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {nsLabel(ns.namespace)}
        </div>
      </div>

      {/* Mini tier legend */}
      <div style={{ display: 'flex', gap: 8, fontSize: 9, fontFamily: 'monospace', color: C.textDim }}>
        <span><span style={{ color: C.hot }}>●</span> {tb.hot}</span>
        <span><span style={{ color: C.warm }}>●</span> {tb.warm}</span>
        <span><span style={{ color: C.cold }}>●</span> {tb.cold}</span>
      </div>
    </div>
  );
}

function GaugesView({ cells, namespaces }: { cells: MapCell[]; namespaces: NamespaceSummary[] }) {
  const maxCount = Math.max(...namespaces.map(n => n.count), 1);

  const allCells = cells;
  const totalHot = allCells.filter(c => c.tier === 'HOT').reduce((s, c) => s + c.count, 0);
  const totalWarm = allCells.filter(c => c.tier === 'WARM').reduce((s, c) => s + c.count, 0);
  const totalCold = allCells.filter(c => c.tier === 'COLD').reduce((s, c) => s + c.count, 0);
  const totalAll = totalHot + totalWarm + totalCold || 1;

  const tempScore = ((totalHot * 3 + totalWarm * 2 + totalCold * 1) / totalAll).toFixed(1);
  const tempLabel = Number(tempScore) > 2.3 ? 'CALIENTE' : Number(tempScore) > 1.5 ? 'TEMPLADO' : 'FRÍO';
  const tempColor = Number(tempScore) > 2.3 ? C.hot : Number(tempScore) > 1.5 ? C.warm : C.cold;

  return (
    <div style={{ width: '100%', height: '100%', overflowY: 'auto', padding: 16 }}>
      {/* System temperature header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24,
        padding: '12px 0', marginBottom: 16,
        borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{ fontFamily: 'monospace', fontSize: 10, color: C.textDim, letterSpacing: 2 }}>
          SYSTEM TEMPERATURE
        </div>
        <div style={{
          fontFamily: 'monospace', fontSize: 18, fontWeight: 700, color: tempColor,
          textShadow: `0 0 10px ${tempColor}40`,
        }}>
          {tempScore}
        </div>
        <div style={{
          fontFamily: 'monospace', fontSize: 10, color: tempColor, letterSpacing: 1,
          padding: '2px 8px', border: `1px solid ${tempColor}40`, borderRadius: 4,
        }}>
          {tempLabel}
        </div>
        <div style={{ display: 'flex', gap: 12, fontSize: 10, fontFamily: 'monospace', color: C.textDim }}>
          <span>🔴 HOT: {totalHot}</span>
          <span>🟠 WARM: {totalWarm}</span>
          <span>🔵 COLD: {totalCold}</span>
        </div>
      </div>

      {/* Gauge grid */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8,
      }}>
        {namespaces.map((ns, i) => (
          <div key={ns.namespace} style={{ animationDelay: `${i * 0.08}s` }}>
            <CircularGauge ns={ns} cells={cells} maxCount={maxCount} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// VIEW 3: CONSOLE — Diagnostic Terminal
// ═══════════════════════════════════════════════════════════════════════════════
function ConsoleView({ events }: { events: AuditEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
    if (events.length === 0) return;
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setVisibleCount(i);
      if (i >= events.length) clearInterval(timer);
    }, 60);
    return () => clearInterval(timer);
  }, [events.length]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [visibleCount]);

  function formatTs(ts: string | null): string {
    if (!ts) return '00:00:00';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', { hour12: false });
    } catch {
      return '??:??:??';
    }
  }

  function truncate(s: string, max: number): string {
    return s.length > max ? s.slice(0, max) + '…' : s;
  }

  const visible = events.slice(0, visibleCount);

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: '#000',
      borderTop: `1px solid ${C.border}`,
    }}>
      {/* Terminal header */}
      <div style={{
        padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 12,
        borderBottom: '1px solid #1a1a2e',
        background: 'linear-gradient(180deg, #0a0a14, #000)',
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%', background: C.green,
          boxShadow: `0 0 6px ${C.green}`, animation: 'pulse 2s ease-in-out infinite',
        }} />
        <div style={{
          fontFamily: 'monospace', fontSize: 11, color: C.accent, letterSpacing: 2, fontWeight: 700,
        }}>
          SYSTEM DIAGNOSTICS — MEMORY CORE v3.20
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ fontFamily: 'monospace', fontSize: 9, color: C.textDim }}>
          {events.length} EVENTS LOADED
        </div>
      </div>

      {/* Log body */}
      <div ref={scrollRef} style={{
        flex: 1, overflowY: 'auto', padding: '8px 16px', fontFamily: 'monospace', fontSize: 11,
        lineHeight: 1.7,
      }}>
        {/* Boot message */}
        <div style={{ color: C.textDim, marginBottom: 4 }}>
          {'>'} Initializing memory subsystem...
        </div>
        <div style={{ color: C.green, marginBottom: 8 }}>
          {'>'} Flash Memory online. {events.length} audit records retrieved.
        </div>

        {visible.map((ev, idx) => {
          const actionColor = ACTION_COLOR[ev.action] || C.text;
          return (
            <div key={ev.event_id || idx} style={{
              animation: 'fadeInLine 0.2s ease-out both',
              display: 'flex', gap: 0, whiteSpace: 'nowrap',
              borderLeft: `2px solid ${actionColor}20`,
              paddingLeft: 8, marginBottom: 1,
            }}>
              <span style={{ color: C.textDim, minWidth: 72 }}>{formatTs(ev.timestamp)}</span>
              <span style={{ color: '#333', margin: '0 6px' }}>│</span>
              <span style={{
                color: actionColor, fontWeight: 700, minWidth: 64,
                textShadow: `0 0 8px ${actionColor}40`,
              }}>
                {ev.action.padEnd(8)}
              </span>
              <span style={{ color: '#333', margin: '0 6px' }}>│</span>
              <span style={{ color: TIER_COLORS[ev.memory_tier] || C.textDim, minWidth: 44 }}>
                {(ev.memory_tier || '—').padEnd(5)}
              </span>
              <span style={{ color: '#333', margin: '0 6px' }}>│</span>
              <span style={{ color: C.accent, minWidth: 180 }}>
                {truncate(ev.memory_namespace || '—', 25)}
              </span>
              <span style={{ color: '#333', margin: '0 6px' }}>│</span>
              <span style={{ color: '#778', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {truncate(ev.memory_content || '', 80)}
              </span>
            </div>
          );
        })}

        {/* Blinking cursor */}
        <div style={{ display: 'flex', alignItems: 'center', marginTop: 4, height: 18 }}>
          <span style={{ color: C.green, marginRight: 4 }}>{'>'}</span>
          <span style={{
            display: 'inline-block', width: 8, height: 14,
            background: C.accent, animation: 'blink 1s step-end infinite',
          }} />
        </div>
      </div>

      {/* Scanline overlay */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)',
      }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PIPELINE VIEW — Visual flow of AI extraction
// ═══════════════════════════════════════════════════════════════════════════════

interface PipelineStep {
  pipeline_id: string;
  step: string;
  status: string;
  detail: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

interface Pipeline {
  pipeline_id: string;
  source: string;
  status: string;
  steps: PipelineStep[];
  steps_completed: string[];
  step_defs: { key: string; icon: string; label: string }[];
  started_at: string | null;
  message_preview: string;
}

interface StepStats {
  [step: string]: { total: number; ok: number; error: number; skip: number };
}

// Color assignments by step key
const STEP_COLORS: Record<string, string> = {
  RECEIVED:           '#4fc3f7',
  NOISE_CHECK:        '#ffb900',
  TYPE_CLASSIFY:      '#9c27b0',
  EMBEDDING:          '#2196f3',
  STORED:             '#4caf50',
  NAMESPACE_CLASSIFY: '#00bcd4',
  ARCHITECT:          '#ff9800',
  BACKEND_GEN:        '#7c4dff',
  CRITIC_EVAL:        '#e91e63',
  AST_PARSE:          '#8bc34a',
  TESTS_RUN:          '#00bcd4',
  SECURITY_SCAN:      '#f44336',
  PERF_ANALYSIS:      '#ffc107',
  GENERATE:           '#e040fb',
  CONTEXT_LOAD:       '#26c6da',
  EXECUTE:            '#66bb6a',
};

// Fallback definitions (used for the global stats diagram)
const STEP_DEFS = [
  { key: 'RECEIVED',           icon: '📨', label: 'RECIBIDO',   color: '#4fc3f7' },
  { key: 'NOISE_CHECK',        icon: '🧹', label: 'FILTRO',     color: '#ffb900' },
  { key: 'TYPE_CLASSIFY',      icon: '🏷️', label: 'TIPO',       color: '#9c27b0' },
  { key: 'EMBEDDING',          icon: '🧬', label: 'EMBEDDING',  color: '#2196f3' },
  { key: 'STORED',             icon: '💾', label: 'GUARDADO',   color: '#4caf50' },
  { key: 'NAMESPACE_CLASSIFY', icon: '📂', label: 'NAMESPACE',  color: '#00bcd4' },
];

const STATUS_COLOR: Record<string, string> = {
  ok: '#4caf50',
  error: '#ff5050',
  skip: '#ffb900',
};

function PipelineView() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [stepStats, setStepStats] = useState<StepStats>({});
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket('ws://localhost:8000/ws/pipeline');
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send('ping');
      };

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          if (data.type === 'pipeline:init') {
            setPipelines(data.pipelines ?? []);
            setStepStats(data.step_stats ?? {});
            setLoading(false);
          } else if (data.type === 'pipeline:event') {
            // Re-fetch full state on each event for consistency
            fetch(`${API}/map/pipeline?limit=15`)
              .then(r => r.json())
              .then(d => {
                setPipelines(d.pipelines ?? []);
                setStepStats(d.step_stats ?? {});
              })
              .catch(() => {});
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        if (!cancelled) {
          reconnectRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      cancelled = true;
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, []);

  // Calculate error rate per step
  const getErrorRate = (step: string) => {
    const s = stepStats[step];
    if (!s || s.total === 0) return 0;
    return s.error / s.total;
  };

  const formatTime = (ts: string | null) => {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div style={{ padding: 20, overflowY: 'auto', height: '100%', display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* ─── Pipeline Steps Diagram ─────────────────────────────────────────── */}
      <div>
        <div style={{ fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 2, marginBottom: 16 }}>
          EXTRACTION PIPELINE — PASO A PASO
        </div>

        {/* Step nodes connected by lines */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0, padding: '10px 0' }}>
          {STEP_DEFS.map((step, i) => {
            const stats = stepStats[step.key];
            const total = stats?.total ?? 0;
            const errors = stats?.error ?? 0;
            const errorRate = getErrorRate(step.key);
            const hasErrors = errors > 0;

            return (
              <React.Fragment key={step.key}>
                {/* Node */}
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
                  position: 'relative',
                }}>
                  {/* Circle */}
                  <div style={{
                    width: 56, height: 56, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: hasErrors
                      ? `radial-gradient(circle, rgba(255,80,80,0.2), rgba(255,80,80,0.05))`
                      : `radial-gradient(circle, ${step.color}22, ${step.color}08)`,
                    border: `2px solid ${hasErrors ? '#ff5050' : step.color}`,
                    boxShadow: hasErrors
                      ? '0 0 15px rgba(255,80,80,0.4)'
                      : `0 0 10px ${step.color}33`,
                    animation: hasErrors ? 'pulse 1.5s infinite' : 'none',
                    transition: 'all 300ms',
                  }}>
                    <span style={{ fontSize: 22 }}>{step.icon}</span>
                  </div>

                  {/* Label */}
                  <span style={{ fontSize: 9, color: step.color, fontFamily: 'monospace', letterSpacing: 1 }}>
                    {step.label}
                  </span>

                  {/* Stats below */}
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#4caf50', fontFamily: 'monospace' }}>
                      {total > 0 ? `${total - errors}✓` : '—'}
                    </span>
                    {errors > 0 && (
                      <span style={{ fontSize: 10, color: '#ff5050', fontFamily: 'monospace', fontWeight: 700 }}>
                        {errors}✗
                      </span>
                    )}
                  </div>

                  {/* Error rate bar */}
                  {total > 0 && (
                    <div style={{ width: 40, height: 3, background: '#1a1a2e', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{
                        width: `${(1 - errorRate) * 100}%`, height: '100%',
                        background: errorRate > 0.1 ? '#ff5050' : '#4caf50',
                        borderRadius: 2, transition: 'width 500ms',
                      }} />
                    </div>
                  )}
                </div>

                {/* Connector line */}
                {i < STEP_DEFS.length - 1 && (
                  <div style={{
                    width: 40, height: 2, position: 'relative',
                    background: `linear-gradient(90deg, ${step.color}66, ${STEP_DEFS[i + 1].color}66)`,
                    marginBottom: 30,
                    overflow: 'hidden',
                  }}>
                    {/* Animated particle */}
                    <div style={{
                      position: 'absolute', top: -2, width: 6, height: 6,
                      borderRadius: '50%', background: step.color,
                      boxShadow: `0 0 6px ${step.color}`,
                      animation: 'dataFlow 2s infinite linear',
                    }} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ─── Live Pipeline Stream ───────────────────────────────────────────── */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <span style={{ fontSize: 10, color: '#4fc3f7', fontFamily: 'monospace', letterSpacing: 2 }}>
            FLUJOS RECIENTES
          </span>
          <div style={{
            width: 8, height: 8, borderRadius: '50%', background: '#4caf50',
            animation: 'pulse 2s infinite',
          }} />
          <span style={{ fontSize: 9, color: '#334', fontFamily: 'monospace' }}>
            polling 3s
          </span>
        </div>

        {loading ? (
          <div style={{ color: '#556', fontSize: 12, fontFamily: 'monospace', textAlign: 'center', padding: 30 }}>
            Esperando actividad del pipeline…
          </div>
        ) : pipelines.length === 0 ? (
          <div style={{ color: '#334', fontSize: 12, fontFamily: 'monospace', textAlign: 'center', padding: 30 }}>
            Envía un mensaje en el chat para ver el flujo aquí
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pipelines.map(pipe => {
              const isError = pipe.status === 'error';
              return (
                <div
                  key={pipe.pipeline_id}
                  style={{
                    background: isError ? 'rgba(255,80,80,0.06)' : 'rgba(79,195,247,0.03)',
                    border: `1px solid ${isError ? '#ff505033' : '#1E3A5F'}`,
                    borderRadius: 10, padding: '12px 16px',
                    animation: 'fadeInLine 0.4s ease-out',
                  }}
                >
                  {/* Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={{
                      fontSize: 10, fontFamily: 'monospace', padding: '2px 6px',
                      borderRadius: 4,
                      background: isError ? 'rgba(255,80,80,0.15)' : 'rgba(76,175,80,0.15)',
                      color: isError ? '#ff5050' : '#4caf50',
                      border: `1px solid ${isError ? '#ff505044' : '#4caf5044'}`,
                    }}>
                      {isError ? '❌ ERROR' : '✅ OK'}
                    </span>
                    <span style={{
                      fontSize: 9, fontFamily: 'monospace', padding: '2px 6px',
                      borderRadius: 4, background: 'rgba(124,77,255,0.12)',
                      color: '#b388ff', border: '1px solid #7c4dff33',
                    }}>
                      {pipe.source === 'code_dojo' ? '⚙️ CODE' : pipe.source === 'chat' ? '💬 CHAT' : pipe.source === 'image' ? '🎨 IMG' : pipe.source === 'automation' ? '🤖 AUTO' : pipe.source?.toUpperCase()}
                    </span>
                    <span style={{ fontSize: 10, color: '#556', fontFamily: 'monospace' }}>
                      {pipe.pipeline_id}
                    </span>
                    <span style={{ fontSize: 10, color: '#445', fontFamily: 'monospace', marginLeft: 'auto' }}>
                      {formatTime(pipe.started_at)}
                    </span>
                  </div>

                  {/* Message preview */}
                  {pipe.message_preview && (
                    <div style={{
                      fontSize: 11, color: '#90caf9', marginBottom: 10, padding: '6px 10px',
                      background: '#0a0a0f', borderRadius: 6, border: '1px solid #1a1a2e',
                      overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                    }}>
                      &quot;{pipe.message_preview}&quot;
                    </div>
                  )}

                  {/* Step flow visualization — uses pipeline-specific step defs */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                    {(pipe.step_defs ?? STEP_DEFS).map((stepDef: { key: string; icon: string; label: string }, i: number, arr: { key: string; icon: string; label: string }[]) => {
                      const stepEvent = pipe.steps.find(s => s.step === stepDef.key);
                      const completed = pipe.steps_completed.includes(stepDef.key);
                      const status = stepEvent?.status ?? 'pending';
                      const stepColor = STEP_COLORS[stepDef.key] || '#556';

                      return (
                        <React.Fragment key={stepDef.key}>
                          {/* Mini node */}
                          <div
                            title={stepEvent?.detail || stepDef.label}
                            style={{
                              width: 28, height: 28, borderRadius: '50%',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                              fontSize: 13,
                              background: !completed ? '#0d0d1a'
                                : status === 'ok' ? `${STATUS_COLOR.ok}18`
                                : status === 'error' ? `${STATUS_COLOR.error}22`
                                : `${STATUS_COLOR.skip}18`,
                              border: `2px solid ${!completed ? '#1a1a2e'
                                : STATUS_COLOR[status] || '#556'}`,
                              boxShadow: status === 'error' && completed ? '0 0 8px rgba(255,80,80,0.5)' : 'none',
                              transition: 'all 300ms',
                            }}
                          >
                            {!completed ? (
                              <span style={{ fontSize: 8, color: '#334' }}>•</span>
                            ) : status === 'error' ? (
                              <span style={{ fontSize: 11 }}>❌</span>
                            ) : status === 'skip' ? (
                              <span style={{ fontSize: 11 }}>⏭️</span>
                            ) : (
                              <span style={{ fontSize: 11 }}>{stepDef.icon}</span>
                            )}
                          </div>

                          {/* Connector */}
                          {i < arr.length - 1 && (
                            <div style={{
                              flex: 1, height: 2, minWidth: 8,
                              background: completed && pipe.steps_completed.includes(arr[i + 1]?.key)
                                ? (status === 'error' ? '#ff505066' : '#4caf5066')
                                : '#1a1a2e',
                              transition: 'background 300ms',
                            }} />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>

                  {/* Step details on error */}
                  {isError && pipe.steps.filter(s => s.status === 'error').map(s => (
                    <div key={s.step} style={{
                      marginTop: 8, padding: '6px 10px', borderRadius: 6,
                      background: 'rgba(255,80,80,0.08)', border: '1px solid #ff505022',
                      fontSize: 10, color: '#ff8a80', fontFamily: 'monospace',
                    }}>
                      ⚠ {s.step}: {s.detail}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// GRAFO VIEW — React Flow network graph
// ═══════════════════════════════════════════════════════════════════════════════

const NS_ICONS: Record<string, string> = {
  'chat': '💬', 'codigo': '⚙️', 'imagen': '🎨',
  'video': '🎬', 'automatizacion': '🤖',
};

const TIER_NODE_COLORS: Record<string, { bg: string; border: string }> = {
  HOT: { bg: '#2a0a0a', border: '#ff5050' },
  WARM: { bg: '#2a1a0a', border: '#ffb900' },
  COLD: { bg: '#0a1a2a', border: '#4fc3f7' },
};

function GrafoView({ cells, namespaces }: { cells: MapCell[]; namespaces: NamespaceSummary[] }) {
  // Build nodes from namespaces — each namespace is a node
  // Edges connect namespaces that share a prefix (e.g., chat:usuario ↔ chat:conocimiento)

  const prefixGroups: Record<string, NamespaceSummary[]> = {};
  namespaces.forEach(ns => {
    const prefix = ns.namespace.split(':')[0];
    if (!prefixGroups[prefix]) prefixGroups[prefix] = [];
    prefixGroups[prefix].push(ns);
  });

  // Layout: prefix groups in a circle, members spaced around group center
  const prefixes = Object.keys(prefixGroups);
  const centerX = 300;
  const centerY = 250;
  const groupRadius = 200;

  type GNode = {
    id: string; x: number; y: number; label: string;
    count: number; icon: string; tiers: Record<string, number>;
    totalAccesses: number;
  };
  type GEdge = { from: string; to: string; };

  const nodes: GNode[] = [];
  const edges: GEdge[] = [];

  // Central "CORE" node
  const totalMem = namespaces.reduce((s, n) => s + n.count, 0);
  nodes.push({
    id: '__core__', x: centerX, y: centerY,
    label: 'CORE', count: totalMem, icon: '🧠',
    tiers: {
      HOT: cells.filter(c => c.tier === 'HOT').reduce((s, c) => s + c.count, 0),
      WARM: cells.filter(c => c.tier === 'WARM').reduce((s, c) => s + c.count, 0),
      COLD: cells.filter(c => c.tier === 'COLD').reduce((s, c) => s + c.count, 0),
    },
    totalAccesses: namespaces.reduce((s, n) => s + n.total_accesses, 0),
  });

  prefixes.forEach((prefix, pi) => {
    const angle = (pi / prefixes.length) * Math.PI * 2 - Math.PI / 2;
    const groupCx = centerX + Math.cos(angle) * groupRadius;
    const groupCy = centerY + Math.sin(angle) * groupRadius;
    const members = prefixGroups[prefix];

    members.forEach((ns, mi) => {
      const memberAngle = angle + ((mi - (members.length - 1) / 2) * 0.4);
      const memberR = members.length > 1 ? 60 : 0;
      const x = groupCx + (members.length > 1 ? Math.cos(memberAngle) * memberR : 0);
      const y = groupCy + (members.length > 1 ? Math.sin(memberAngle) * memberR : 0);

      const nsCells = cells.filter(c => c.namespace === ns.namespace);
      const tiers: Record<string, number> = { HOT: 0, WARM: 0, COLD: 0 };
      nsCells.forEach(c => { tiers[c.tier] = (tiers[c.tier] || 0) + c.count; });

      nodes.push({
        id: ns.namespace, x, y,
        label: ns.namespace.split(':')[1] || ns.namespace,
        count: ns.count, icon: NS_ICONS[prefix] || '📦',
        tiers, totalAccesses: ns.total_accesses,
      });

      // Edge to core
      edges.push({ from: '__core__', to: ns.namespace });
    });

    // Edges between members of same group
    if (members.length > 1) {
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          edges.push({ from: members[i].namespace, to: members[j].namespace });
        }
      }
    }
  });

  const maxCount = Math.max(...nodes.map(n => n.count), 1);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
      <svg width="100%" height="100%" viewBox="0 0 600 500" style={{ position: 'absolute', top: 0, left: 0 }}>
        {/* Edges */}
        {edges.map((e, i) => {
          const from = nodes.find(n => n.id === e.from);
          const to = nodes.find(n => n.id === e.to);
          if (!from || !to) return null;
          const isCore = e.from === '__core__';
          return (
            <line key={i}
              x1={from.x} y1={from.y} x2={to.x} y2={to.y}
              stroke={isCore ? 'rgba(79,195,247,0.15)' : 'rgba(255,185,0,0.2)'}
              strokeWidth={isCore ? 1 : 1.5}
              strokeDasharray={isCore ? '4,4' : 'none'}
            />
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map(node => {
        const isCore = node.id === '__core__';
        const size = isCore ? 80 : 40 + (node.count / maxCount) * 40;
        const dominant = Object.entries(node.tiers).sort((a, b) => b[1] - a[1])[0];
        const tierColor = dominant ? TIER_NODE_COLORS[dominant[0]] : TIER_NODE_COLORS.WARM;

        return (
          <div key={node.id} style={{
            position: 'absolute',
            left: node.x - size / 2,
            top: node.y - size / 2,
            width: size, height: size,
            borderRadius: '50%',
            background: isCore
              ? 'radial-gradient(circle, #1a1a3e 0%, #0a0a1a 70%)'
              : tierColor.bg,
            border: `2px solid ${isCore ? C.accent : tierColor.border}`,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            cursor: 'default',
            boxShadow: isCore
              ? `0 0 30px ${C.accentDim}, inset 0 0 20px ${C.accentDim}`
              : `0 0 12px ${tierColor.border}33`,
            transition: 'transform 200ms, box-shadow 200ms',
            zIndex: isCore ? 10 : 5,
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.15)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}
          title={`${node.id}\n${node.count} memories\n${node.totalAccesses} accesses\nHOT:${node.tiers.HOT} WARM:${node.tiers.WARM} COLD:${node.tiers.COLD}`}
          >
            <span style={{ fontSize: isCore ? 20 : 14 }}>{node.icon}</span>
            {size > 50 && (
              <span style={{
                fontSize: 8, fontFamily: 'monospace', color: C.text,
                textTransform: 'uppercase', letterSpacing: 1,
                marginTop: 2, textAlign: 'center', lineHeight: '10px',
              }}>
                {node.label}
              </span>
            )}
            <span style={{
              fontSize: isCore ? 12 : 9, fontFamily: 'monospace',
              color: isCore ? C.accent : tierColor.border, fontWeight: 'bold',
            }}>
              {node.count}
            </span>
          </div>
        );
      })}

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 12, right: 12,
        padding: '8px 12px', borderRadius: 8,
        background: 'rgba(13,17,23,0.9)', border: `1px solid ${C.border}`,
        fontSize: 9, fontFamily: 'monospace', color: C.textDim,
        display: 'flex', gap: 12,
      }}>
        <span>🔴 HOT</span>
        <span>🟡 WARM</span>
        <span>🔵 COLD</span>
        <span style={{ color: C.text }}>
          {nodes.length - 1} namespaces · {totalMem} memories
        </span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN EXPORT
// ═══════════════════════════════════════════════════════════════════════════════
export function MemoryMapLayout() {
  const [view, setView] = useState<ViewMode>('engine');
  const [cells, setCells] = useState<MapCell[]>([]);
  const [namespaces, setNamespaces] = useState<NamespaceSummary[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [uptime, setUptime] = useState(0);

  // Uptime counter
  useEffect(() => {
    const t = setInterval(() => setUptime(u => u + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [mapRes, auditRes] = await Promise.all([
        fetch(`${API}/map/distribution`),
        fetch(`${API}/debug/audit?limit=50`),
      ]);
      if (mapRes.ok) {
        const data = await mapRes.json();
        setCells(data.cells || []);
        setNamespaces(data.namespaces || []);
      }
      if (auditRes.ok) {
        const data = await auditRes.json();
        setEvents(data.events || []);
      }
    } catch {
      // silent — machine stays quiet on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Computed stats
  const totalMem = namespaces.reduce((s, n) => s + n.count, 0);
  const allHot = cells.filter(c => c.tier === 'HOT').reduce((s, c) => s + c.count, 0);
  const allWarm = cells.filter(c => c.tier === 'WARM').reduce((s, c) => s + c.count, 0);
  const allCold = cells.filter(c => c.tier === 'COLD').reduce((s, c) => s + c.count, 0);

  function fmtUptime(s: number): string {
    const h = Math.floor(s / 3600).toString().padStart(2, '0');
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${h}:${m}:${sec}`;
  }

  const modes: { key: ViewMode; icon: string; label: string }[] = [
    { key: 'engine', icon: '⚛️', label: 'ENGINE' },
    { key: 'gauges', icon: '📊', label: 'GAUGES' },
    { key: 'console', icon: '🖥️', label: 'CONSOLE' },
    { key: 'pipeline', icon: '🔬', label: 'PIPELINE' },
    { key: 'grafo', icon: '🌐', label: 'GRAFO' },
  ];

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: C.bg, color: C.text, fontFamily: 'monospace', position: 'relative',
      overflow: 'hidden',
    }}>
      <style dangerouslySetInnerHTML={{ __html: STYLE_TAG }} />

      {/* ── HEADER BAR ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 0,
        borderBottom: `1px solid ${C.border}`,
        background: 'linear-gradient(180deg, #0d1117, #0a0a0f)',
        padding: 0, flexShrink: 0,
      }}>
        {/* Title */}
        <div style={{
          padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8,
          borderRight: `1px solid ${C.border}`,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: loading ? C.warm : C.green,
            boxShadow: `0 0 6px ${loading ? C.warm : C.green}`,
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{ fontSize: 11, fontWeight: 700, color: C.accent, letterSpacing: 2 }}>
            LA MÁQUINA
          </span>
        </div>

        {/* Mode switcher */}
        <div style={{ display: 'flex', gap: 0 }}>
          {modes.map(m => {
            const active = view === m.key;
            return (
              <button key={m.key} onClick={() => setView(m.key)} style={{
                background: active
                  ? `linear-gradient(180deg, rgba(79,195,247,0.12), rgba(79,195,247,0.04))`
                  : 'transparent',
                border: 'none',
                borderRight: `1px solid ${C.border}`,
                borderBottom: active ? `2px solid ${C.accent}` : '2px solid transparent',
                padding: '10px 16px',
                color: active ? C.accent : C.textDim,
                fontFamily: 'monospace', fontSize: 10, fontWeight: 700,
                letterSpacing: 1.5, cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <span style={{ fontSize: 14 }}>{m.icon}</span>
                {m.label}
              </button>
            );
          })}
        </div>

        {/* Status bar (right side) */}
        <div style={{ flex: 1 }} />
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16, padding: '0 16px',
          fontSize: 9, color: C.textDim, letterSpacing: 1,
        }}>
          <span>MEM: <span style={{ color: '#fff', fontWeight: 700 }}>{totalMem}</span></span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: C.hot }} />
            {allHot}
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: C.warm, marginLeft: 4 }} />
            {allWarm}
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: C.cold, marginLeft: 4 }} />
            {allCold}
          </span>
          <span style={{ color: C.accent }}>⏱ {fmtUptime(uptime)}</span>
        </div>
      </div>

      {/* ── BODY ── */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {loading ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            height: '100%', gap: 12,
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: '50%',
              border: `3px solid ${C.border}`, borderTopColor: C.accent,
              animation: 'rotate 1s linear infinite',
            }} />
            <div style={{ fontSize: 10, color: C.textDim, letterSpacing: 2 }}>
              INITIALIZING MEMORY CORE...
            </div>
          </div>
        ) : view === 'engine' ? (
          <EngineView cells={cells} namespaces={namespaces} />
        ) : view === 'gauges' ? (
          <GaugesView cells={cells} namespaces={namespaces} />
        ) : view === 'pipeline' ? (
          <PipelineView />
        ) : view === 'grafo' ? (
          <GrafoView cells={cells} namespaces={namespaces} />
        ) : (
          <ConsoleView events={events} />
        )}
      </div>
    </div>
  );
}
