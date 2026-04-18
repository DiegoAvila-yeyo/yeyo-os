/**
 * YeyoOS — YeyoNetNodeLayout
 * Dashboard de la red de satélites YeyoNet.
 *
 * 4 pestañas:
 *   🛰 Satélites | 🖥 Render Farm | 🔄 Sync | ⚙️ Config
 */
'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  useYeyoNetStore,
  type Satellite,
  type YeyoNetTab,
} from '@/stores/yeyonetStore';

// ─── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return 'nunca';
  const diff = Date.now() - new Date(iso).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `hace ${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `hace ${days}d`;
}

const STATUS_DOT: Record<string, string> = {
  online: '🟢',
  idle: '🟡',
  offline: '⭘',
};

const MODE_LABEL: Record<string, string> = {
  full: 'Completo',
  lite: 'Ligero',
  minimal: 'Mínimo',
};

const PERMISSIONS_ALL = ['chat', 'grafos', 'memoria', 'control'];

// ─── Shared styles ─────────────────────────────────────────────────────────────

const S = {
  root: {
    display: 'flex',
    flexDirection: 'column' as const,
    width: '100%',
    height: '100%',
    background: '#0d0d1a',
    fontFamily: 'monospace',
    color: '#ccc',
    overflow: 'hidden',
  },
  tabBar: {
    display: 'flex',
    gap: 0,
    borderBottom: '1px solid #1a1a2e',
    background: '#0a0a14',
    flexShrink: 0,
  },
  tab: (active: boolean): React.CSSProperties => ({
    padding: '10px 20px',
    fontSize: 13,
    fontFamily: 'monospace',
    cursor: 'pointer',
    color: active ? '#4fc3f7' : '#888',
    background: active ? 'rgba(79,195,247,0.08)' : 'transparent',
    transition: 'color 150ms, background 150ms, border-bottom-color 150ms',
    borderTop: '0 none',
    borderLeft: '0 none',
    borderRight: '0 none',
    borderBottom: active ? '2px solid #4fc3f7' : '2px solid transparent',
    whiteSpace: 'nowrap' as const,
    outline: 'none',
  }),
  content: {
    flex: 1,
    overflow: 'auto',
    padding: 20,
  },
  card: {
    background: '#111122',
    border: '1px solid #1a1a2e',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 11,
    color: '#4fc3f7',
    fontFamily: 'monospace',
    letterSpacing: 1,
    marginBottom: 12,
    textTransform: 'uppercase' as const,
  },
  bigNumber: {
    fontSize: 28,
    fontWeight: 700,
    color: '#e0f7fa',
    fontFamily: 'monospace',
  },
  mutedLabel: {
    fontSize: 11,
    color: '#888',
    fontFamily: 'monospace',
  },
  statBox: (color: string) => ({
    flex: 1,
    minWidth: 80,
    padding: '10px 12px',
    borderRadius: 8,
    background: `${color}15`,
    border: `1px solid ${color}40`,
    textAlign: 'center' as const,
  }),
  btn: (color: string) => ({
    padding: '8px 16px',
    fontSize: 12,
    fontFamily: 'monospace',
    background: `${color}20`,
    border: `1px solid ${color}60`,
    color,
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 150ms',
  }),
  input: {
    padding: '8px 12px',
    fontSize: 12,
    fontFamily: 'monospace',
    background: '#0d0d1a',
    border: '1px solid #1a1a2e',
    color: '#ccc',
    borderRadius: 6,
    outline: 'none',
    width: '100%',
  },
  select: {
    padding: '8px 12px',
    fontSize: 12,
    fontFamily: 'monospace',
    background: '#0d0d1a',
    border: '1px solid #1a1a2e',
    color: '#ccc',
    borderRadius: 6,
    outline: 'none',
  },
  tag: (color: string) => ({
    display: 'inline-block',
    padding: '2px 8px',
    fontSize: 10,
    fontFamily: 'monospace',
    borderRadius: 4,
    background: `${color}18`,
    border: `1px solid ${color}50`,
    color,
    marginRight: 4,
    marginBottom: 4,
  }),
  progressBar: (pct: number, color: string) => ({
    outer: {
      width: '100%',
      height: 8,
      background: '#1a1a2e',
      borderRadius: 4,
      overflow: 'hidden' as const,
    },
    inner: {
      width: `${Math.min(100, Math.max(0, pct))}%`,
      height: '100%',
      background: color,
      borderRadius: 4,
      transition: 'width 300ms',
    },
  }),
  errorBanner: {
    padding: '8px 12px',
    background: 'rgba(255,80,80,0.1)',
    border: '1px solid #ff505060',
    borderRadius: 6,
    color: '#ff5050',
    fontSize: 12,
    fontFamily: 'monospace',
    marginBottom: 12,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
};

// ─── Tab: Satélites ────────────────────────────────────────────────────────────

function SatellitesTab() {
  const {
    satellites, loading, fetchSatellites, createInvitation, triggerSync,
  } = useYeyoNetStore();

  const [showInvite, setShowInvite] = useState(false);
  const [invName, setInvName] = useState('');
  const [invPerms, setInvPerms] = useState<string[]>(['chat', 'grafos', 'memoria', 'control']);
  const [invVisibility, setInvVisibility] = useState(4);
  const [invExpiry, setInvExpiry] = useState(7);
  const [invResult, setInvResult] = useState<{ code: string; expires_at: string } | null>(null);
  const [inviting, setInviting] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchSatellites();
    intervalRef.current = setInterval(fetchSatellites, 30_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchSatellites]);

  const handleInvite = useCallback(async () => {
    if (!invName.trim()) return;
    setInviting(true);
    try {
      const result = await createInvitation({
        satellite_name: invName.trim(),
        permissions: invPerms,
        visibility_level: invVisibility,
        expires_in_days: invExpiry,
      });
      setInvResult(result);
      setInvName('');
    } catch (err) {
      setInvResult(null);
      alert(`Error al crear invitación: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setInviting(false);
    }
  }, [invName, invPerms, invVisibility, invExpiry, createInvitation]);

  const togglePerm = (p: string) => {
    setInvPerms(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  };

  const online = satellites.filter(s => s.status === 'online').length;
  const totalCores = satellites.reduce((a, s) => a + (s.resources?.cpu_cores ?? 0), 0);
  const totalRam = satellites.reduce((a, s) => a + (s.resources?.ram_gb ?? 0), 0);

  return (
    <div>
      {/* Summary card */}
      <div style={S.card}>
        <div style={S.cardTitle}>📡 Resumen de Red</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div style={S.statBox('#4fc3f7')}>
            <div style={S.bigNumber}>{satellites.length}</div>
            <div style={S.mutedLabel}>Satélites</div>
          </div>
          <div style={S.statBox('#00e676')}>
            <div style={{ ...S.bigNumber, color: '#00e676' }}>{online}</div>
            <div style={S.mutedLabel}>En línea</div>
          </div>
          <div style={S.statBox('#ffb900')}>
            <div style={{ ...S.bigNumber, color: '#ffb900' }}>{totalCores}</div>
            <div style={S.mutedLabel}>CPU Cores</div>
          </div>
          <div style={S.statBox('#9b59b6')}>
            <div style={{ ...S.bigNumber, color: '#9b59b6' }}>{totalRam.toFixed(1)} GB</div>
            <div style={S.mutedLabel}>RAM Total</div>
          </div>
        </div>
      </div>

      {/* Invite button / form */}
      <div style={{ marginBottom: 16 }}>
        {!showInvite && !invResult && (
          <button style={S.btn('#00e676')} onClick={() => setShowInvite(true)}>
            ➕ Invitar Satélite
          </button>
        )}

        {showInvite && !invResult && (
          <div style={{ ...S.card, borderColor: '#00e67640' }}>
            <div style={S.cardTitle}>🛰 Nueva Invitación</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={S.mutedLabel}>Nombre del satélite</label>
                <input
                  style={{ ...S.input, marginTop: 4 }}
                  placeholder="ej: workstation-2"
                  value={invName}
                  onChange={e => setInvName(e.target.value)}
                />
              </div>
              <div>
                <label style={S.mutedLabel}>Permisos</label>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
                  {PERMISSIONS_ALL.map(p => (
                    <label key={p} style={{
                      display: 'flex', alignItems: 'center', gap: 4,
                      fontSize: 11, color: invPerms.includes(p) ? '#4fc3f7' : '#666',
                      cursor: 'pointer',
                    }}>
                      <input
                        type="checkbox"
                        checked={invPerms.includes(p)}
                        onChange={() => togglePerm(p)}
                        style={{ accentColor: '#4fc3f7' }}
                      />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={S.mutedLabel}>Visibilidad</label>
                  <select
                    style={{ ...S.select, width: '100%', marginTop: 4 }}
                    value={invVisibility}
                    onChange={e => setInvVisibility(Number(e.target.value))}
                  >
                    <option value={4}>4 — Control total</option>
                    <option value={3}>3 — Alta</option>
                    <option value={2}>2 — Media</option>
                    <option value={1}>1 — Mínima</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={S.mutedLabel}>Expiración (días)</label>
                  <input
                    type="number"
                    style={{ ...S.input, marginTop: 4 }}
                    value={invExpiry}
                    onChange={e => setInvExpiry(Number(e.target.value))}
                    min={1}
                    max={9999}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  style={S.btn('#00e676')}
                  onClick={handleInvite}
                  disabled={inviting || !invName.trim()}
                >
                  {inviting ? '⏳ Generando...' : '✅ Generar Código'}
                </button>
                <button style={S.btn('#888')} onClick={() => setShowInvite(false)}>
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}

        {invResult && (
          <div style={{
            ...S.card,
            borderColor: '#00e676',
            background: 'rgba(0,230,118,0.05)',
          }}>
            <div style={S.cardTitle}>🎟️ Código de Invitación</div>
            <div style={{
              fontSize: 28, fontWeight: 700, fontFamily: 'monospace',
              color: '#00e676', textAlign: 'center', padding: '16px 0',
              letterSpacing: 4, userSelect: 'all',
              background: '#0d0d1a', borderRadius: 8, border: '1px dashed #00e67660',
            }}>
              {invResult.code}
            </div>
            <div style={{ fontSize: 11, color: '#888', textAlign: 'center', marginTop: 8 }}>
              Expira: {new Date(invResult.expires_at).toLocaleString('es-MX')}
            </div>
            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <button style={S.btn('#888')} onClick={() => { setInvResult(null); setShowInvite(false); }}>
                Cerrar
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Satellite list */}
      {loading && satellites.length === 0 && (
        <div style={{ color: '#556', fontSize: 12, padding: 16 }}>Cargando satélites...</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {satellites.map(sat => (
          <SatelliteCard key={sat.id} sat={sat} onTriggerSync={triggerSync} />
        ))}
        {!loading && satellites.length === 0 && (
          <div style={{ color: '#556', fontSize: 13, textAlign: 'center', padding: 32 }}>
            🛰 No hay satélites conectados. Invita uno para comenzar.
          </div>
        )}
      </div>
    </div>
  );
}

function SatelliteCard({ sat, onTriggerSync }: { sat: Satellite; onTriggerSync: (id: string) => void }) {
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try { await onTriggerSync(sat.id); } finally { setSyncing(false); }
  };

  return (
    <div style={{
      ...S.card,
      display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 0,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 16 }}>{STATUS_DOT[sat.status] ?? '⭘'}</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: '#e0f7fa' }}>{sat.name}</span>
        <span style={S.tag('#9b59b6')}>{MODE_LABEL[sat.mode] ?? sat.mode}</span>
        <span style={{ fontSize: 10, color: '#556', marginLeft: 'auto' }}>
          {relativeTime(sat.last_seen_at)}
        </span>
      </div>

      {/* Resources */}
      {sat.resources && (
        <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#888' }}>
          {sat.resources.cpu_cores != null && (
            <span>🔲 {sat.resources.cpu_cores} cores</span>
          )}
          {sat.resources.ram_gb != null && (
            <span>💾 {sat.resources.ram_gb} GB RAM</span>
          )}
          {sat.resources.gpu_name && (
            <span>🎮 {sat.resources.gpu_name}</span>
          )}
        </div>
      )}

      {/* Permissions + actions */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
        {sat.permissions.map(p => (
          <span key={p} style={S.tag('#4fc3f7')}>{p}</span>
        ))}
        {sat.status === 'online' && (
          <button
            style={{ ...S.btn('#4fc3f7'), marginLeft: 'auto', padding: '4px 12px', fontSize: 11 }}
            onClick={handleSync}
            disabled={syncing}
          >
            {syncing ? '⏳' : '🔄'} Sync
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Tab: Render Farm ──────────────────────────────────────────────────────────

function RenderFarmTab() {
  const { jobs, jobStats, fetchJobs, fetchJobStats, cancelJob } = useYeyoNetStore();
  const [activeForm, setActiveForm] = useState<'none' | 'text' | 'image' | 'custom'>('none');
  const [creating, setCreating] = useState(false);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  // Text inference form
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('qwen2.5:3b');
  const [temperature, setTemperature] = useState(0.7);

  // Image form
  const [imgPrompt, setImgPrompt] = useState('');
  const [imgSteps, setImgSteps] = useState(20);
  const [imgWidth, setImgWidth] = useState(512);
  const [imgHeight, setImgHeight] = useState(512);

  // Custom form
  const [customType, setCustomType] = useState('custom');
  const [customPayload, setCustomPayload] = useState('');
  const [jobPriority, setJobPriority] = useState(7);

  useEffect(() => {
    fetchJobs();
    fetchJobStats();
    const iv = setInterval(() => { fetchJobs(); fetchJobStats(); }, 5_000);
    return () => clearInterval(iv);
  }, [fetchJobs, fetchJobStats]);

  const submitJob = useCallback(async (type: string, payload: Record<string, unknown>, priority = 7) => {
    setCreating(true);
    try {
      const res = await fetch('/api/v1/yeyonet/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, payload, priority, timeout_seconds: 120 }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setActiveForm('none');
      setPrompt('');
      setImgPrompt('');
      setCustomPayload('');
      fetchJobs();
      fetchJobStats();
    } catch {
      // handled
    } finally {
      setCreating(false);
    }
  }, [fetchJobs, fetchJobStats]);

  const running = jobs.filter(j => ['running', 'assigned'].includes(j.status));
  const queued = jobs.filter(j => j.status === 'queued');
  const completed = jobs.filter(j => j.status === 'completed').slice(0, 15);
  const failed = jobs.filter(j => j.status === 'failed').slice(0, 5);
  const sts = jobStats?.by_status;

  return (
    <div>
      {/* Stats */}
      <div style={S.card}>
        <div style={S.cardTitle}>🖥 Render Farm</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div style={S.statBox('#4fc3f7')}>
            <div style={S.bigNumber}>{jobStats?.total ?? 0}</div>
            <div style={S.mutedLabel}>Total</div>
          </div>
          <div style={S.statBox('#00e676')}>
            <div style={{ ...S.bigNumber, color: '#00e676' }}>{sts?.completed ?? 0}</div>
            <div style={S.mutedLabel}>Completados</div>
          </div>
          <div style={S.statBox('#ffb900')}>
            <div style={{ ...S.bigNumber, color: '#ffb900' }}>{(sts?.running ?? 0) + (sts?.assigned ?? 0)}</div>
            <div style={S.mutedLabel}>Ejecutando</div>
          </div>
          <div style={S.statBox('#888')}>
            <div style={{ ...S.bigNumber, color: '#aaa' }}>{sts?.queued ?? 0}</div>
            <div style={S.mutedLabel}>En cola</div>
          </div>
          <div style={S.statBox('#ff5050')}>
            <div style={{ ...S.bigNumber, color: '#ff5050' }}>{sts?.failed ?? 0}</div>
            <div style={S.mutedLabel}>Fallidos</div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <button
          style={{
            ...S.btn(activeForm === 'text' ? '#00e676' : '#4fc3f7'),
            display: 'flex', alignItems: 'center', gap: 6,
          }}
          onClick={() => setActiveForm(activeForm === 'text' ? 'none' : 'text')}
        >
          💬 Inferencia de Texto
        </button>
        <button
          style={{
            ...S.btn(activeForm === 'image' ? '#00e676' : '#e040fb'),
            display: 'flex', alignItems: 'center', gap: 6,
          }}
          onClick={() => setActiveForm(activeForm === 'image' ? 'none' : 'image')}
        >
          🎨 Generar Imagen
        </button>
        <button
          style={{
            ...S.btn(activeForm === 'custom' ? '#00e676' : '#888'),
            display: 'flex', alignItems: 'center', gap: 6,
          }}
          onClick={() => setActiveForm(activeForm === 'custom' ? 'none' : 'custom')}
        >
          ⚙️ Job Custom
        </button>
      </div>

      {/* Text Inference Form */}
      {activeForm === 'text' && (
        <div style={{ ...S.card, borderColor: '#4fc3f740' }}>
          <div style={S.cardTitle}>💬 Inferencia de Texto — Ollama Distribuido</div>
          <p style={{ color: '#889', fontSize: 12, margin: '0 0 12px' }}>
            Envía un prompt a un satélite con Ollama. Se ejecuta en la máquina remota y el resultado regresa aquí.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={S.mutedLabel}>Prompt</label>
              <textarea
                style={{ ...S.input, marginTop: 4, minHeight: 80, resize: 'vertical' }}
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                placeholder="Escribe tu pregunta o prompt aquí..."
              />
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Modelo</label>
                <select
                  style={{ ...S.select, width: '100%', marginTop: 4 }}
                  value={model}
                  onChange={e => setModel(e.target.value)}
                >
                  <option value="qwen2.5:3b">qwen2.5:3b (rápido)</option>
                  <option value="qwen2.5:0.5b">qwen2.5:0.5b (ultra rápido)</option>
                  <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (código)</option>
                  <option value="qwen3:4b">qwen3:4b (potente)</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Temperatura: {temperature}</label>
                <input
                  type="range"
                  min={0} max={1.5} step={0.1}
                  style={{ width: '100%', marginTop: 8 }}
                  value={temperature}
                  onChange={e => setTemperature(Number(e.target.value))}
                />
              </div>
            </div>
            <button
              style={S.btn('#4fc3f7')}
              disabled={creating || !prompt.trim()}
              onClick={() => submitJob('text_inference', {
                prompt: prompt.trim(), model, temperature,
              }, 8)}
            >
              {creating ? '⏳ Enviando...' : '🚀 Enviar a Satélite'}
            </button>
          </div>
        </div>
      )}

      {/* Image Form */}
      {activeForm === 'image' && (
        <div style={{ ...S.card, borderColor: '#e040fb40' }}>
          <div style={S.cardTitle}>🎨 Generar Imagen — GPU Distribuida</div>
          <p style={{ color: '#889', fontSize: 12, margin: '0 0 12px' }}>
            Envía un prompt de imagen a un satélite con GPU. Se ejecutará con Stable Diffusion / Flux.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={S.mutedLabel}>Prompt</label>
              <textarea
                style={{ ...S.input, marginTop: 4, minHeight: 60, resize: 'vertical' }}
                value={imgPrompt}
                onChange={e => setImgPrompt(e.target.value)}
                placeholder="A cyberpunk city at sunset, neon lights, volumetric fog..."
              />
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Ancho</label>
                <select style={{ ...S.select, width: '100%', marginTop: 4 }} value={imgWidth}
                  onChange={e => setImgWidth(Number(e.target.value))}
                >
                  <option value={256}>256px</option>
                  <option value={512}>512px</option>
                  <option value={768}>768px</option>
                  <option value={1024}>1024px</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Alto</label>
                <select style={{ ...S.select, width: '100%', marginTop: 4 }} value={imgHeight}
                  onChange={e => setImgHeight(Number(e.target.value))}
                >
                  <option value={256}>256px</option>
                  <option value={512}>512px</option>
                  <option value={768}>768px</option>
                  <option value={1024}>1024px</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Steps: {imgSteps}</label>
                <input
                  type="range" min={5} max={50} step={5}
                  style={{ width: '100%', marginTop: 8 }}
                  value={imgSteps}
                  onChange={e => setImgSteps(Number(e.target.value))}
                />
              </div>
            </div>
            <button
              style={S.btn('#e040fb')}
              disabled={creating || !imgPrompt.trim()}
              onClick={() => submitJob('image_generate', {
                prompt: imgPrompt.trim(), width: imgWidth, height: imgHeight, steps: imgSteps,
              }, 7)}
            >
              {creating ? '⏳ Enviando...' : '🎨 Generar Imagen'}
            </button>
          </div>
        </div>
      )}

      {/* Custom Job Form */}
      {activeForm === 'custom' && (
        <div style={{ ...S.card, borderColor: '#88888840' }}>
          <div style={S.cardTitle}>⚙️ Job Custom</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Tipo</label>
                <select style={{ ...S.select, width: '100%', marginTop: 4 }} value={customType}
                  onChange={e => setCustomType(e.target.value)}
                >
                  <option value="text_inference">text_inference</option>
                  <option value="image_generate">image_generate</option>
                  <option value="video_render">video_render</option>
                  <option value="training_step">training_step</option>
                  <option value="memory_sync">memory_sync</option>
                  <option value="custom">custom</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={S.mutedLabel}>Prioridad (1-10)</label>
                <input type="number" style={{ ...S.input, marginTop: 4 }}
                  value={jobPriority} onChange={e => setJobPriority(Number(e.target.value))}
                  min={1} max={10}
                />
              </div>
            </div>
            <div>
              <label style={S.mutedLabel}>Payload (JSON)</label>
              <textarea
                style={{ ...S.input, marginTop: 4, minHeight: 80, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                value={customPayload}
                onChange={e => setCustomPayload(e.target.value)}
                placeholder='{"prompt": "...", "model": "qwen2.5:3b"}'
              />
            </div>
            <button style={S.btn('#888')} disabled={creating}
              onClick={() => {
                let payload: Record<string, unknown> = {};
                try { payload = JSON.parse(customPayload); } catch { payload = { raw: customPayload }; }
                submitJob(customType, payload, jobPriority);
              }}
            >
              {creating ? '⏳ Enviando...' : '🚀 Enviar Job'}
            </button>
          </div>
        </div>
      )}

      {/* Queued */}
      {queued.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>⏳ En Cola ({queued.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {queued.map(job => (
              <div key={job.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', background: '#0d0d1a', borderRadius: 6, fontSize: 12,
              }}>
                <span style={S.tag('#aaa')}>{job.type}</span>
                <span style={{ color: '#556' }}>esperando asignación...</span>
                <button style={{ ...S.btn('#ff5050'), padding: '2px 8px', fontSize: 10, marginLeft: 'auto' }}
                  onClick={() => cancelJob(job.id)}
                >✕</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Running / Assigned */}
      {running.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>⚡ Ejecutando ({running.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {running.map(job => {
              const pct = job.progress ?? 0;
              const pb = S.progressBar(pct, '#ffb900');
              return (
                <div key={job.id} style={{
                  padding: 12, background: '#0d0d1a', borderRadius: 6,
                  border: '1px solid #1a1a2e',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span style={S.tag('#ffb900')}>{job.type}</span>
                    <span style={{ fontSize: 12, color: '#e0f7fa' }}>{pct}%</span>
                    {job.progress_detail && (
                      <span style={{ fontSize: 11, color: '#889' }}>{job.progress_detail}</span>
                    )}
                    {(job.assigned_node || job.assigned_to) && (
                      <span style={{ fontSize: 10, color: '#556', marginLeft: 'auto' }}>
                        📍 {(job.assigned_node || job.assigned_to || '').slice(0, 8)}...
                      </span>
                    )}
                    <button
                      style={{ ...S.btn('#ff5050'), padding: '2px 8px', fontSize: 10 }}
                      onClick={() => cancelJob(job.id)}
                    >✕</button>
                  </div>
                  <div style={pb.outer}><div style={pb.inner} /></div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed — with expandable results */}
      {completed.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>✅ Completados</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {completed.map(job => {
              const durationMs = job.completed_at && job.started_at
                ? new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()
                : null;
              const durationStr = durationMs != null ? `${(durationMs / 1000).toFixed(1)}s` : '—';
              const isExpanded = expandedJob === job.id;
              const result = (job.result || {}) as Record<string, string | number | boolean | null>;

              return (
                <div key={job.id}>
                  <div
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 12px', background: '#0d0d1a', borderRadius: isExpanded ? '6px 6px 0 0' : 6,
                      fontSize: 12, cursor: 'pointer',
                    }}
                    onClick={() => setExpandedJob(isExpanded ? null : job.id)}
                  >
                    <span style={S.tag('#00e676')}>{job.type}</span>
                    <span style={{ color: '#888' }}>⏱ {durationStr}</span>
                    {job.type === 'text_inference' && result.tokens && (
                      <span style={{ color: '#4fc3f7', fontSize: 10 }}>
                        {result.tokens} tokens
                      </span>
                    )}
                    <span style={{ color: '#556', fontSize: 10, marginLeft: 'auto' }}>
                      {isExpanded ? '▼' : '▶'} {relativeTime(job.completed_at)}
                    </span>
                  </div>

                  {/* Expanded result */}
                  {isExpanded && (
                    <div style={{
                      padding: 12, background: '#080812', borderRadius: '0 0 6px 6px',
                      border: '1px solid #1a1a2e', borderTop: 'none',
                    }}>
                      {job.type === 'text_inference' && result.response ? (
                        <div>
                          <div style={{ fontSize: 11, color: '#889', marginBottom: 8 }}>
                            Modelo: {result.model} · {result.tokens} tokens · {result.duration_ms}ms
                          </div>
                          <div style={{
                            padding: 12, background: '#0d0d1a', borderRadius: 6,
                            fontSize: 13, color: '#e0f7fa', lineHeight: 1.5,
                            whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto',
                          }}>
                            {result.response}
                          </div>
                        </div>
                      ) : job.type === 'image_generate' ? (
                        <div>
                          <div style={{ fontSize: 11, color: '#889', marginBottom: 8 }}>
                            Prompt: &quot;{result.prompt}&quot; · {result.width}x{result.height} · {result.steps} steps
                          </div>
                          <div style={{
                            padding: 16, background: '#0d0d1a', borderRadius: 6,
                            textAlign: 'center', color: '#e040fb',
                          }}>
                            {result.status === 'placeholder_generated'
                              ? '🎨 Placeholder — integrar Stable Diffusion para imágenes reales'
                              : '✅ Imagen generada'}
                          </div>
                        </div>
                      ) : (
                        <pre style={{
                          padding: 10, background: '#0d0d1a', borderRadius: 6,
                          fontSize: 11, color: '#aaa', whiteSpace: 'pre-wrap',
                          maxHeight: 200, overflowY: 'auto', margin: 0,
                        }}>
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Failed */}
      {failed.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>❌ Fallidos</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {failed.map(job => (
              <div key={job.id} style={{
                padding: '8px 12px', background: '#1a0d0d', borderRadius: 6,
                fontSize: 12, border: '1px solid #3a1010',
              }}>
                <span style={S.tag('#ff5050')}>{job.type}</span>
                <span style={{ color: '#ff8888', marginLeft: 8 }}>
                  {String(job.result?.error || 'Error desconocido')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {jobs.length === 0 && (
        <div style={{ color: '#556', fontSize: 13, textAlign: 'center', padding: 32 }}>
          🖥 No hay jobs. Usa los botones de arriba para enviar trabajo a los satélites.
        </div>
      )}
    </div>
  );
}

// ─── Tab: Sync ─────────────────────────────────────────────────────────────────

function SyncTab() {
  const { syncStats, satellites, fetchSyncStats, fetchSatellites, triggerSync } = useYeyoNetStore();

  useEffect(() => {
    fetchSyncStats();
    fetchSatellites();
    const iv = setInterval(fetchSyncStats, 20_000);
    return () => clearInterval(iv);
  }, [fetchSyncStats, fetchSatellites]);

  const total = syncStats?.total_memories ?? 0;
  const synced = syncStats?.synced_memories ?? 0;
  const queueSize = syncStats?.offline_queue_size ?? 0;
  const pct = total > 0 ? Math.round((synced / total) * 100) : 0;
  const pb = S.progressBar(pct, '#4fc3f7');

  return (
    <div>
      {/* Sync stats card */}
      <div style={S.card}>
        <div style={S.cardTitle}>🔄 Estado de Sincronización</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          <div style={S.statBox('#4fc3f7')}>
            <div style={S.bigNumber}>{total}</div>
            <div style={S.mutedLabel}>Memorias Totales</div>
          </div>
          <div style={S.statBox('#00e676')}>
            <div style={{ ...S.bigNumber, color: '#00e676' }}>{synced}</div>
            <div style={S.mutedLabel}>Sincronizadas</div>
          </div>
          <div style={S.statBox('#ffb900')}>
            <div style={{ ...S.bigNumber, color: '#ffb900' }}>{queueSize}</div>
            <div style={S.mutedLabel}>Cola Offline</div>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={S.mutedLabel}>Progreso de sincronización</span>
            <span style={{ fontSize: 12, color: '#4fc3f7', fontFamily: 'monospace' }}>{pct}%</span>
          </div>
          <div style={pb.outer}><div style={pb.inner} /></div>
        </div>
      </div>

      {/* Per-node offline queues */}
      {syncStats?.offline_queues && Object.keys(syncStats.offline_queues).length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>📬 Colas Offline por Nodo</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(syncStats.offline_queues).map(([nodeId, count]) => (
              <div key={nodeId} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px', background: '#0d0d1a', borderRadius: 6,
              }}>
                <span style={{ fontSize: 12, color: '#e0f7fa', flex: 1 }}>{nodeId}</span>
                <span style={S.tag('#ffb900')}>{count} pendientes</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Satellite sync buttons */}
      <div style={S.card}>
        <div style={S.cardTitle}>🛰 Sincronización Manual</div>
        {satellites.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {satellites.map(sat => (
              <SyncSatelliteRow key={sat.id} sat={sat} onTriggerSync={triggerSync} />
            ))}
          </div>
        ) : (
          <div style={{ color: '#556', fontSize: 12 }}>
            No hay satélites disponibles para sincronizar.
          </div>
        )}
      </div>
    </div>
  );
}

function SyncSatelliteRow({ sat, onTriggerSync }: { sat: Satellite; onTriggerSync: (id: string) => void }) {
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try { await onTriggerSync(sat.id); } finally { setSyncing(false); }
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px', background: '#0d0d1a', borderRadius: 6,
    }}>
      <span style={{ fontSize: 14 }}>{STATUS_DOT[sat.status] ?? '⭘'}</span>
      <span style={{ fontSize: 12, color: '#e0f7fa', flex: 1 }}>{sat.name}</span>
      <span style={{ fontSize: 10, color: '#556' }}>{relativeTime(sat.last_seen_at)}</span>
      <button
        style={{ ...S.btn('#4fc3f7'), padding: '4px 12px', fontSize: 11 }}
        onClick={handleSync}
        disabled={syncing || sat.status === 'offline'}
      >
        {syncing ? '⏳' : '🔄'} Sync
      </button>
    </div>
  );
}

// ─── Tab: Config ───────────────────────────────────────────────────────────────

function ConfigTab() {
  const {
    identity, fetchIdentity,
    registerAsSatellite,
    connectionStatus, fetchConnectionStatus,
    connectAsSatellite, disconnectSatellite,
  } = useYeyoNetStore();

  const [showRegister, setShowRegister] = useState(false);
  const [regUrl, setRegUrl] = useState('');
  const [regCode, setRegCode] = useState('');
  const [regName, setRegName] = useState('');
  const [regMode, setRegMode] = useState('completo');
  const [registering, setRegistering] = useState(false);
  const [regResult, setRegResult] = useState<{ node_id: string; auth_token: string } | null>(null);
  const [regError, setRegError] = useState('');
  const [disconnecting, setDisconnecting] = useState(false);
  const suggestedCentralUrl = identity?.role === 'central'
    ? (identity.suggested_central_urls.find(url => !url.includes('localhost') && !url.includes('127.0.0.1'))
      ?? identity.suggested_central_urls[0]
      ?? null)
    : null;

  useEffect(() => { fetchIdentity(); fetchConnectionStatus(); }, [fetchIdentity, fetchConnectionStatus]);

  // Poll connection status while configured
  useEffect(() => {
    if (!connectionStatus?.configured) return;
    const interval = setInterval(() => fetchConnectionStatus(), 5000);
    return () => clearInterval(interval);
  }, [connectionStatus?.configured, fetchConnectionStatus]);

  const handleRegister = useCallback(async () => {
    if (!regUrl.trim() || !regCode.trim() || !regName.trim()) return;
    setRegistering(true);
    setRegError('');
    try {
      const result = await registerAsSatellite(regUrl.trim(), regCode.trim(), regName.trim(), regMode);
      setRegResult(result);
      // Refresh connection status
      fetchConnectionStatus();
    } catch (e) {
      setRegError(String(e));
    } finally {
      setRegistering(false);
    }
  }, [regUrl, regCode, regName, regMode, registerAsSatellite, fetchConnectionStatus]);

  const handleDisconnect = useCallback(async () => {
    setDisconnecting(true);
    try {
      await disconnectSatellite();
      setRegResult(null);
      setShowRegister(false);
    } finally {
      setDisconnecting(false);
    }
  }, [disconnectSatellite]);

  const handleReconnect = useCallback(async () => {
    await connectAsSatellite();
    setTimeout(() => fetchConnectionStatus(), 2000);
  }, [connectAsSatellite, fetchConnectionStatus]);

  return (
    <div>
      {/* Identity card */}
      <div style={S.card}>
        <div style={S.cardTitle}>🪪 Identidad del Nodo</div>
        {identity ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={S.mutedLabel}>Node ID:</span>
              <span style={{
                fontSize: 13, color: '#4fc3f7', fontFamily: 'monospace',
                background: '#0d0d1a', padding: '4px 10px', borderRadius: 4,
                userSelect: 'all',
              }}>
                {identity.node_id}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={S.mutedLabel}>Nombre:</span>
              <span style={{ fontSize: 14, color: '#e0f7fa', fontWeight: 600 }}>
                {identity.node_name}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={S.mutedLabel}>Rol:</span>
              <span style={S.tag('#00e676')}>{identity.role}</span>
            </div>
            {suggestedCentralUrl && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={S.mutedLabel}>URL sugerida para satélites:</span>
                <span style={{
                  fontSize: 13, color: '#4fc3f7', fontFamily: 'monospace',
                  background: '#0d0d1a', padding: '6px 10px', borderRadius: 4,
                  userSelect: 'all', wordBreak: 'break-all',
                }}>
                  {suggestedCentralUrl}
                </span>
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: '#556', fontSize: 12 }}>Cargando identidad...</div>
        )}
      </div>

      {/* Connected Devices */}
      <div style={S.card}>
        <div style={S.cardTitle}>🔗 Dispositivos Conectados</div>
        {connectionStatus?.configured ? (
          <div style={{
            background: connectionStatus.connected ? 'rgba(0,230,118,0.05)' : 'rgba(255,185,0,0.05)',
            border: `1px solid ${connectionStatus.connected ? '#00e67640' : '#ffb90040'}`,
            borderRadius: 8, padding: 14,
          }}>
            <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
              Conectado como satélite a:
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 14 }}>{connectionStatus.connected ? '🟢' : '🟡'}</span>
              <span style={{ fontSize: 13, color: '#e0f7fa', fontWeight: 600 }}>
                Central: {connectionStatus.central_name || connectionStatus.central_ws_url || '—'}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>
              Node ID: <span style={{ color: '#4fc3f7', fontFamily: 'monospace' }}>
                {connectionStatus.node_id ? connectionStatus.node_id.slice(0, 12) + '...' : '—'}
              </span>
            </div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 10 }}>
              Estado: <span style={{
                color: connectionStatus.connected ? '#00e676' : '#ffb900',
                fontWeight: 600,
              }}>
                {connectionStatus.connected ? 'conectado' : 'conectando...'}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {!connectionStatus.connected && (
                <button style={S.btn('#4fc3f7')} onClick={handleReconnect}>
                  🔄 Reconectar
                </button>
              )}
              <button
                style={S.btn('#ff5050')}
                onClick={handleDisconnect}
                disabled={disconnecting}
              >
                {disconnecting ? '⏳...' : '⛔ Desconectar'}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: '#556', padding: '8px 0' }}>
            ⭘ No conectado a ninguna Central
          </div>
        )}
      </div>

      {/* Network settings */}
      <div style={S.card}>
        <div style={S.cardTitle}>🌐 Configuración de Red</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={S.mutedLabel}>API Base:</span>
            <span style={{ fontSize: 12, color: '#888' }}>/api/v1/yeyonet</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={S.mutedLabel}>Protocolo:</span>
            <span style={{ fontSize: 12, color: '#888' }}>HTTP + WebSocket</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={S.mutedLabel}>Cifrado:</span>
            <span style={S.tag('#00e676')}>AES-256-GCM</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={S.mutedLabel}>Auto-refresh:</span>
            <span style={{ fontSize: 12, color: '#888' }}>30s (satélites), 15s (jobs), 20s (sync)</span>
          </div>
        </div>
      </div>

      {/* Services status */}
      <div style={S.card}>
        <div style={S.cardTitle}>🔌 Estado de Servicios</div>
        <ServiceStatus label="YeyoNet Core" endpoint="/api/v1/yeyonet/identity" />
        <ServiceStatus label="Satellite Manager" endpoint="/api/v1/yeyonet/satellites" />
        <ServiceStatus label="Job Scheduler" endpoint="/api/v1/yeyonet/jobs/stats" />
        <ServiceStatus label="Sync Engine" endpoint="/api/v1/yeyonet/sync/stats" />
        <ServiceStatus label="Cloud Sync" endpoint="/api/v1/cloud-sync/status" />
      </div>

      {/* Register as Satellite */}
      <div style={S.card}>
        <div style={S.cardTitle}>🛰 Registrar como Satélite</div>
        <div style={{ fontSize: 11, color: '#888', marginBottom: 12 }}>
          ¿Tienes un código de invitación? Pégalo aquí para conectar esta PC a otra Central.
        </div>

        {!showRegister && !regResult && (
          <button style={S.btn('#9b59b6')} onClick={() => setShowRegister(true)}>
            🔗 Tengo un código de invitación
          </button>
        )}

        {showRegister && !regResult && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <label style={S.mutedLabel}>URL de la Central (IP o dominio)</label>
              <input
                style={{ ...S.input, marginTop: 4, width: '100%' }}
                placeholder="ej: http://192.168.1.100:8000"
                value={regUrl}
                onChange={e => setRegUrl(e.target.value)}
              />
            </div>
            <div>
              <label style={S.mutedLabel}>Código de invitación</label>
              <input
                style={{ ...S.input, marginTop: 4, width: '100%', letterSpacing: 2, fontSize: 16 }}
                placeholder="YEYO-XXXX-XXXX-XXXX"
                value={regCode}
                onChange={e => setRegCode(e.target.value.toUpperCase())}
              />
            </div>
            <div>
              <label style={S.mutedLabel}>Nombre de esta PC</label>
              <input
                style={{ ...S.input, marginTop: 4, width: '100%' }}
                placeholder="ej: Desktop Diego"
                value={regName}
                onChange={e => setRegName(e.target.value)}
              />
            </div>
            <div>
              <label style={S.mutedLabel}>Modo</label>
              <select
                style={{ ...S.select, width: '100%', marginTop: 4 }}
                value={regMode}
                onChange={e => setRegMode(e.target.value)}
              >
                <option value="completo">Completo (GPU + Chat + Memoria)</option>
                <option value="ligero">Ligero (solo Chat)</option>
                <option value="minimo">Mínimo (solo UI)</option>
              </select>
            </div>

            {regError && (
              <div style={{ fontSize: 11, color: '#ff5050', background: 'rgba(255,80,80,0.08)', padding: '6px 10px', borderRadius: 4 }}>
                ❌ {regError}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                style={S.btn('#9b59b6')}
                onClick={handleRegister}
                disabled={registering || !regUrl.trim() || !regCode.trim() || !regName.trim()}
              >
                {registering ? '⏳ Registrando...' : '✅ Registrar'}
              </button>
              <button style={S.btn('#888')} onClick={() => { setShowRegister(false); setRegError(''); }}>
                Cancelar
              </button>
            </div>
          </div>
        )}

        {regResult && (
          <div style={{
            background: 'rgba(0,230,118,0.05)', border: '1px solid #00e67640',
            borderRadius: 8, padding: 16,
          }}>
            <div style={{ fontSize: 14, color: '#00e676', fontWeight: 600, marginBottom: 8 }}>
              ✅ ¡Registrado exitosamente!
            </div>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>
              Node ID: <span style={{ color: '#4fc3f7', fontFamily: 'monospace' }}>{regResult.node_id}</span>
            </div>
            <div style={{ fontSize: 11, color: '#888' }}>
              Token: <span style={{ color: '#4fc3f7', fontFamily: 'monospace' }}>{regResult.auth_token.slice(0, 16)}...</span>
            </div>
            <div style={{ marginTop: 10 }}>
              <button style={S.btn('#888')} onClick={() => { setRegResult(null); setShowRegister(false); }}>
                Cerrar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ServiceStatus({ label, endpoint }: { label: string; endpoint: string }) {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    let cancelled = false;
    fetch(endpoint)
      .then(res => { if (!cancelled) setStatus(res.ok ? 'online' : 'offline'); })
      .catch(() => { if (!cancelled) setStatus('offline'); });
    return () => { cancelled = true; };
  }, [endpoint]);

  const dotColor = status === 'online' ? '#00e676' : status === 'offline' ? '#ff5050' : '#ffb900';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '6px 0', fontSize: 12,
    }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%',
        background: dotColor, display: 'inline-block', flexShrink: 0,
      }} />
      <span style={{ color: '#ccc', flex: 1 }}>{label}</span>
      <span style={{ color: dotColor, fontSize: 10 }}>
        {status === 'checking' ? 'verificando...' : status}
      </span>
    </div>
  );
}

// ─── Main Layout ───────────────────────────────────────────────────────────────

const TABS: { id: YeyoNetTab; label: string; icono: string }[] = [
  { id: 'satellites', label: 'Satélites',    icono: '🛰' },
  { id: 'render',     label: 'Render Farm',  icono: '🖥' },
  { id: 'sync',       label: 'Sync',         icono: '🔄' },
  { id: 'config',     label: 'Config',       icono: '⚙️' },
];

export function YeyoNetNodeLayout() {
  const { activeTab, setActiveTab, error, clearError } = useYeyoNetStore();

  return (
    <div style={S.root}>
      {/* Tab bar */}
      <div style={S.tabBar}>
        {TABS.map(t => (
          <button
            key={t.id}
            style={S.tab(activeTab === t.id)}
            onClick={() => setActiveTab(t.id)}
          >
            {t.icono} {t.label}
          </button>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div style={{ padding: '0 20px', paddingTop: 12 }}>
          <div style={S.errorBanner}>
            <span>❌ {error}</span>
            <button
              onClick={clearError}
              style={{ background: 'none', border: 'none', color: '#ff5050', cursor: 'pointer', fontFamily: 'monospace' }}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Active tab content */}
      <div style={S.content}>
        {activeTab === 'satellites' && <SatellitesTab />}
        {activeTab === 'render' && <RenderFarmTab />}
        {activeTab === 'sync' && <SyncTab />}
        {activeTab === 'config' && <ConfigTab />}
      </div>
    </div>
  );
}
