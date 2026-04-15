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
  type Job,
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

const PERMISSIONS_ALL = ['memory_read', 'memory_write', 'compute', 'sync', 'admin'];

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
  const [invPerms, setInvPerms] = useState<string[]>(['memory_read', 'sync']);
  const [invVisibility, setInvVisibility] = useState('full');
  const [invExpiry, setInvExpiry] = useState(24);
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
        expires_hours: invExpiry,
      });
      setInvResult(result);
      setInvName('');
    } catch {
      // error handled by store
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
                    onChange={e => setInvVisibility(e.target.value)}
                  >
                    <option value="full">Completa</option>
                    <option value="partial">Parcial</option>
                    <option value="minimal">Mínima</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={S.mutedLabel}>Expiración (horas)</label>
                  <input
                    type="number"
                    style={{ ...S.input, marginTop: 4 }}
                    value={invExpiry}
                    onChange={e => setInvExpiry(Number(e.target.value))}
                    min={1}
                    max={168}
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
  const [showCreateJob, setShowCreateJob] = useState(false);
  const [jobType, setJobType] = useState('render');
  const [jobPayload, setJobPayload] = useState('');
  const [jobPriority, setJobPriority] = useState(5);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchJobs();
    fetchJobStats();
    const iv = setInterval(() => { fetchJobs(); fetchJobStats(); }, 15_000);
    return () => clearInterval(iv);
  }, [fetchJobs, fetchJobStats]);

  const handleCreateJob = useCallback(async () => {
    setCreating(true);
    try {
      let payload: Record<string, unknown> = {};
      try { payload = JSON.parse(jobPayload); } catch { payload = { raw: jobPayload }; }
      const res = await fetch('/api/v1/yeyonet/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: jobType, payload, priority: jobPriority }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setShowCreateJob(false);
      setJobPayload('');
      fetchJobs();
      fetchJobStats();
    } catch {
      // handled
    } finally {
      setCreating(false);
    }
  }, [jobType, jobPayload, jobPriority, fetchJobs, fetchJobStats]);

  const running = jobs.filter(j => j.status === 'running');
  const completed = jobs.filter(j => j.status === 'completed').slice(0, 10);
  const sts = jobStats?.by_status;

  return (
    <div>
      {/* Stats card */}
      <div style={S.card}>
        <div style={S.cardTitle}>🖥 Render Farm — Estadísticas</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div style={S.statBox('#4fc3f7')}>
            <div style={S.bigNumber}>{jobStats?.total ?? 0}</div>
            <div style={S.mutedLabel}>Total Jobs</div>
          </div>
          <div style={S.statBox('#00e676')}>
            <div style={{ ...S.bigNumber, color: '#00e676' }}>{sts?.completed ?? 0}</div>
            <div style={S.mutedLabel}>Completados</div>
          </div>
          <div style={S.statBox('#ffb900')}>
            <div style={{ ...S.bigNumber, color: '#ffb900' }}>{sts?.running ?? 0}</div>
            <div style={S.mutedLabel}>Ejecutando</div>
          </div>
          <div style={S.statBox('#ff5050')}>
            <div style={{ ...S.bigNumber, color: '#ff5050' }}>{sts?.failed ?? 0}</div>
            <div style={S.mutedLabel}>Fallidos</div>
          </div>
          <div style={S.statBox('#888')}>
            <div style={{ ...S.bigNumber, color: '#aaa' }}>{sts?.queued ?? 0}</div>
            <div style={S.mutedLabel}>En cola</div>
          </div>
        </div>
      </div>

      {/* Create Job */}
      <div style={{ marginBottom: 16 }}>
        {!showCreateJob ? (
          <button style={S.btn('#4fc3f7')} onClick={() => setShowCreateJob(true)}>
            ➕ Crear Job
          </button>
        ) : (
          <div style={{ ...S.card, borderColor: '#4fc3f740' }}>
            <div style={S.cardTitle}>📋 Nuevo Job</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <label style={S.mutedLabel}>Tipo</label>
                  <select
                    style={{ ...S.select, width: '100%', marginTop: 4 }}
                    value={jobType}
                    onChange={e => setJobType(e.target.value)}
                  >
                    <option value="render">Render</option>
                    <option value="transcode">Transcode</option>
                    <option value="inference">Inference</option>
                    <option value="batch_process">Batch Process</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={S.mutedLabel}>Prioridad (1-10)</label>
                  <input
                    type="number"
                    style={{ ...S.input, marginTop: 4 }}
                    value={jobPriority}
                    onChange={e => setJobPriority(Number(e.target.value))}
                    min={1} max={10}
                  />
                </div>
              </div>
              <div>
                <label style={S.mutedLabel}>Payload (JSON o texto)</label>
                <textarea
                  style={{ ...S.input, marginTop: 4, minHeight: 80, resize: 'vertical' }}
                  value={jobPayload}
                  onChange={e => setJobPayload(e.target.value)}
                  placeholder='{"scene": "main", "frames": [1, 250]}'
                />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button style={S.btn('#4fc3f7')} onClick={handleCreateJob} disabled={creating}>
                  {creating ? '⏳ Enviando...' : '🚀 Enviar Job'}
                </button>
                <button style={S.btn('#888')} onClick={() => setShowCreateJob(false)}>
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Running jobs */}
      {running.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>⚡ Jobs en Ejecución</div>
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
                    {job.assigned_node && (
                      <span style={{ fontSize: 10, color: '#556', marginLeft: 'auto' }}>
                        📍 {job.assigned_node}
                      </span>
                    )}
                    <button
                      style={{ ...S.btn('#ff5050'), padding: '2px 8px', fontSize: 10 }}
                      onClick={() => cancelJob(job.id)}
                    >
                      ✕
                    </button>
                  </div>
                  <div style={pb.outer}><div style={pb.inner} /></div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed jobs */}
      {completed.length > 0 && (
        <div style={S.card}>
          <div style={S.cardTitle}>✅ Recientes Completados</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {completed.map(job => {
              const durationMs = job.completed_at && job.started_at
                ? new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()
                : null;
              const durationStr = durationMs != null ? `${(durationMs / 1000).toFixed(1)}s` : '—';
              return (
                <div key={job.id} style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 12px', background: '#0d0d1a', borderRadius: 6,
                  fontSize: 12,
                }}>
                  <span style={S.tag('#00e676')}>{job.type}</span>
                  <span style={{ color: '#888' }}>⏱ {durationStr}</span>
                  <span style={{ color: '#556', fontSize: 10, marginLeft: 'auto' }}>
                    {relativeTime(job.completed_at)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {jobs.length === 0 && (
        <div style={{ color: '#556', fontSize: 13, textAlign: 'center', padding: 32 }}>
          🖥 No hay jobs registrados. Crea uno para comenzar.
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
  const { identity, fetchIdentity } = useYeyoNetStore();

  useEffect(() => { fetchIdentity(); }, [fetchIdentity]);

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
          </div>
        ) : (
          <div style={{ color: '#556', fontSize: 12 }}>Cargando identidad...</div>
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
