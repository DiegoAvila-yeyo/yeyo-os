/**
 * LabNodeLayout — Laboratorio de Generación de Video
 * YeyoOS Phase 3: Video Generation Lab
 *
 * Futuristic lab aesthetic with floating screens, neon blue glow,
 * sequential illumination during generation, and a high-tech feel.
 */
'use client';

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';

// ─── Types ─────────────────────────────────────────────────────────────────────

interface LabClip {
  id: string;
  frame_index: number;
  status: 'idle' | 'generating' | 'completed' | 'error';
  output_url: string;
  duration: number;
  provider: string;
  error_message: string;
  image_url?: string;
  description?: string;
}

interface LabConfig {
  provider: string;
  quality: string;
  fps: number;
  resolution: string;
  transition_default: string;
  duration_default: number;
  consistency: string;
}

interface LabProject {
  id: string;
  storyboard_id: string;
  name: string;
  status: 'idle' | 'generating' | 'paused' | 'completed' | 'error';
  config: LabConfig;
  clips: LabClip[];
}

interface StoryboardSummary {
  id: string;
  name: string;
  description?: string;
  frames?: { id: string; image_url?: string; description?: string }[];
}

export interface LabNodeLayoutProps {
  projectId?: string;
  storyboardId?: string;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const API_LAB = 'http://localhost:8000/api/v1/lab';
const API_STORYBOARD = 'http://localhost:8000/api/v1/storyboard';

const COLORS = {
  bg: '#E3F2FD',
  bgGradEnd: '#BBDEFB',
  panel: '#FFFFFF',
  panelBorder: '#90CAF9',
  accent: '#2196F3',
  accentDark: '#1565C0',
  accentLight: '#64B5F6',
  neonGlow: 'rgba(33, 150, 243, 0.4)',
  neonGlowStrong: 'rgba(33, 150, 243, 0.7)',
  text: '#1A237E',
  textSecondary: '#546E7A',
  textLight: '#78909C',
  success: '#4CAF50',
  successBg: '#E8F5E9',
  error: '#F44336',
  errorBg: '#FFEBEE',
  warning: '#FF9800',
  warningBg: '#FFF3E0',
  idle: '#B0BEC5',
  generating: '#2196F3',
  gridLine: 'rgba(33, 150, 243, 0.08)',
  cardBg: 'rgba(255, 255, 255, 0.92)',
  cardBorder: '#90CAF9',
  toolbarBg: 'rgba(255, 255, 255, 0.95)',
  configBg: 'rgba(227, 242, 253, 0.95)',
};

const btnBase: React.CSSProperties = {
  border: 'none',
  borderRadius: 8,
  padding: '8px 16px',
  fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
};

const btnPrimary: React.CSSProperties = {
  ...btnBase,
  background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`,
  color: '#fff',
  boxShadow: `0 2px 12px ${COLORS.neonGlow}`,
};

const btnSecondary: React.CSSProperties = {
  ...btnBase,
  background: COLORS.panel,
  color: COLORS.accent,
  border: `1px solid ${COLORS.panelBorder}`,
};

const btnDanger: React.CSSProperties = {
  ...btnBase,
  background: COLORS.errorBg,
  color: COLORS.error,
  border: `1px solid ${COLORS.error}`,
};

const btnSmall: React.CSSProperties = {
  ...btnBase,
  padding: '4px 10px',
  fontSize: 11,
  borderRadius: 6,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: COLORS.textSecondary,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: 4,
  display: 'block',
};

const radioGroupStyle: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  flexWrap: 'wrap',
};

// ─── Helpers ───────────────────────────────────────────────────────────────────

function uid(): string {
  return `clip-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function statusIcon(status: LabClip['status']): string {
  switch (status) {
    case 'idle': return '⬜';
    case 'generating': return '⏳';
    case 'completed': return '✅';
    case 'error': return '❌';
    default: return '⬜';
  }
}

function statusColor(status: LabClip['status']): string {
  switch (status) {
    case 'idle': return COLORS.idle;
    case 'generating': return COLORS.generating;
    case 'completed': return COLORS.success;
    case 'error': return COLORS.error;
    default: return COLORS.idle;
  }
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function defaultConfig(): LabConfig {
  return {
    provider: 'fal',
    quality: 'standard',
    fps: 24,
    resolution: '720p',
    transition_default: 'fade',
    duration_default: 4,
    consistency: 'medium',
  };
}

// ─── Radio Button Component ────────────────────────────────────────────────────

function RadioOption({
  label,
  value,
  selected,
  onSelect,
  recommended,
}: {
  label: string;
  value: string;
  selected: boolean;
  onSelect: (v: string) => void;
  recommended?: boolean;
}) {
  return (
    <button
      onClick={() => onSelect(value)}
      style={{
        ...btnSmall,
        background: selected
          ? `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.accentDark})`
          : COLORS.panel,
        color: selected ? '#fff' : COLORS.text,
        border: `1px solid ${selected ? COLORS.accent : COLORS.panelBorder}`,
        boxShadow: selected ? `0 2px 8px ${COLORS.neonGlow}` : 'none',
        position: 'relative',
      }}
    >
      {label}
      {recommended && (
        <span style={{ fontSize: 9, marginLeft: 2, opacity: 0.8 }}>★</span>
      )}
    </button>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────

function LabNodeLayout({ projectId: initialProjectId, storyboardId: initialStoryboardId }: LabNodeLayoutProps) {
  // ── State ──────────────────────────────────────────────────────────────────
  const [project, setProject] = useState<LabProject | null>(null);
  const [projects, setProjects] = useState<LabProject[]>([]);
  const [storyboards, setStoryboards] = useState<StoryboardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState('');
  const [configOpen, setConfigOpen] = useState(true);
  const [editConfig, setEditConfig] = useState<LabConfig>(defaultConfig());
  const [savingConfig, setSavingConfig] = useState(false);
  const [showStoryboardPicker, setShowStoryboardPicker] = useState(false);
  const [creatingProject, setCreatingProject] = useState(false);
  const [previewClipUrl, setPreviewClipUrl] = useState<string | null>(null);
  const [hoveredClip, setHoveredClip] = useState<string | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [editPromptClipId, setEditPromptClipId] = useState<string | null>(null);
  const [editPromptText, setEditPromptText] = useState('');

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const statusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Helpers ────────────────────────────────────────────────────────────────

  const showStatus = useCallback((msg: string) => {
    setStatusMsg(msg);
    if (statusTimerRef.current) clearTimeout(statusTimerRef.current);
    statusTimerRef.current = setTimeout(() => setStatusMsg(''), 4000);
  }, []);

  // ── API Calls ──────────────────────────────────────────────────────────────

  const fetchProject = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_LAB}/projects/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: LabProject = await res.json();
      setProject(data);
      setEditConfig(data.config || defaultConfig());
      return data;
    } catch (err) {
      showStatus(`❌ Error cargando proyecto: ${err}`);
      return null;
    }
  }, [showStatus]);

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_LAB}/projects`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProjects(Array.isArray(data) ? data : data.projects || []);
    } catch {
      setProjects([]);
    }
  }, []);

  const fetchStoryboards = useCallback(async () => {
    try {
      const res = await fetch(`${API_STORYBOARD}/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStoryboards(Array.isArray(data) ? data : data.storyboards || []);
    } catch {
      setStoryboards([]);
    }
  }, []);

  const createProject = useCallback(async (sbId: string) => {
    setCreatingProject(true);
    try {
      const res = await fetch(`${API_LAB}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storyboard_id: sbId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: LabProject = await res.json();
      setProject(data);
      setEditConfig(data.config || defaultConfig());
      setShowStoryboardPicker(false);
      showStatus('✅ Proyecto creado exitosamente');
    } catch (err) {
      showStatus(`❌ Error creando proyecto: ${err}`);
    } finally {
      setCreatingProject(false);
    }
  }, [showStatus]);

  const generateAll = useCallback(async () => {
    if (!project) return;
    try {
      const res = await fetch(`${API_LAB}/projects/${project.id}/generate`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setProject(prev => prev ? { ...prev, status: 'generating', ...data } : prev);
      showStatus('🚀 Generación iniciada');
    } catch (err) {
      showStatus(`❌ Error iniciando generación: ${err}`);
    }
  }, [project, showStatus]);

  const generateSingle = useCallback(async (clipIdx: number) => {
    if (!project) return;
    try {
      const res = await fetch(`${API_LAB}/projects/${project.id}/clips/${clipIdx}/generate`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showStatus(`🔄 Generando clip ${clipIdx + 1}...`);
      // Immediately poll to get updated status
      await fetchProject(project.id);
    } catch (err) {
      showStatus(`❌ Error generando clip: ${err}`);
    }
  }, [project, showStatus, fetchProject]);

  const pauseProject = useCallback(async () => {
    if (!project) return;
    try {
      await fetch(`${API_LAB}/projects/${project.id}/pause`, { method: 'POST' });
      setProject(prev => prev ? { ...prev, status: 'paused' } : prev);
      showStatus('⏸ Generación pausada');
    } catch (err) {
      showStatus(`❌ Error pausando: ${err}`);
    }
  }, [project, showStatus]);

  const resumeProject = useCallback(async () => {
    if (!project) return;
    try {
      await fetch(`${API_LAB}/projects/${project.id}/resume`, { method: 'POST' });
      setProject(prev => prev ? { ...prev, status: 'generating' } : prev);
      showStatus('▶️ Generación reanudada');
    } catch (err) {
      showStatus(`❌ Error reanudando: ${err}`);
    }
  }, [project, showStatus]);

  const concatenateProject = useCallback(async () => {
    if (!project) return;
    try {
      showStatus('🔗 Concatenando clips...');
      const res = await fetch(`${API_LAB}/projects/${project.id}/concatenate`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showStatus('✅ Video concatenado exitosamente');
      await fetchProject(project.id);
    } catch (err) {
      showStatus(`❌ Error concatenando: ${err}`);
    }
  }, [project, showStatus, fetchProject]);

  const downloadProject = useCallback(async () => {
    if (!project) return;
    try {
      const url = `${API_LAB}/projects/${project.id}/download`;
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project.name || 'video'}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      showStatus('📤 Descarga iniciada');
    } catch (err) {
      showStatus(`❌ Error descargando: ${err}`);
    }
  }, [project, showStatus]);

  const saveConfig = useCallback(async () => {
    if (!project) return;
    setSavingConfig(true);
    try {
      const res = await fetch(`${API_LAB}/projects/${project.id}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editConfig),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setProject(prev => prev ? { ...prev, config: { ...editConfig } } : prev);
      showStatus('✅ Configuración guardada');
    } catch (err) {
      showStatus(`❌ Error guardando config: ${err}`);
    } finally {
      setSavingConfig(false);
    }
  }, [project, editConfig, showStatus]);

  // ── Init & Polling ─────────────────────────────────────────────────────────

  useEffect(() => {
    (async () => {
      setLoading(true);
      if (initialProjectId) {
        await fetchProject(initialProjectId);
      } else if (initialStoryboardId) {
        await createProject(initialStoryboardId);
      } else {
        await fetchProjects();
      }
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialProjectId, initialStoryboardId]);

  // Polling while generating
  useEffect(() => {
    if (project?.status === 'generating') {
      pollRef.current = setInterval(() => {
        fetchProject(project.id);
      }, 3000);
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [project?.status, project?.id, fetchProject]);

  // ── Derived Data ───────────────────────────────────────────────────────────

  const clips = useMemo(() => project?.clips || [], [project?.clips]);
  const completedCount = useMemo(() => clips.filter(c => c.status === 'completed').length, [clips]);
  const totalCount = clips.length;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
  const totalDuration = useMemo(() => clips.reduce((acc, c) => acc + (c.duration || 0), 0), [clips]);
  const isGenerating = project?.status === 'generating';
  const isPaused = project?.status === 'paused';
  const allCompleted = project?.status === 'completed' || (totalCount > 0 && completedCount === totalCount);

  const selectedClip = useMemo(
    () => clips.find(c => c.id === selectedClipId) || null,
    [clips, selectedClipId]
  );

  // ── Render: Loading ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div style={{
        width: '100%', height: '100%',
        background: `linear-gradient(180deg, ${COLORS.bg} 0%, ${COLORS.bgGradEnd} 100%)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16, animation: 'labPulse 1.5s infinite' }}>🧪</div>
          <div style={{ color: COLORS.text, fontSize: 16, fontWeight: 600 }}>Cargando Laboratorio...</div>
        </div>
      </div>
    );
  }

  // ── Render: Project Selection ──────────────────────────────────────────────

  if (!project) {
    return (
      <div style={{
        width: '100%', height: '100%',
        background: `linear-gradient(180deg, ${COLORS.bg} 0%, ${COLORS.bgGradEnd} 100%)`,
        backgroundImage: `
          linear-gradient(${COLORS.gridLine} 1px, transparent 1px),
          linear-gradient(90deg, ${COLORS.gridLine} 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', gap: 24,
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        padding: 32,
      }}>
        <div style={{ fontSize: 64, marginBottom: 8 }}>🧪</div>
        <h1 style={{ color: COLORS.text, fontSize: 28, fontWeight: 800, margin: 0 }}>
          Laboratorio de Video
        </h1>
        <p style={{ color: COLORS.textSecondary, fontSize: 14, margin: 0, textAlign: 'center', maxWidth: 400 }}>
          Genera clips de video a partir de tus storyboards con IA.
          Selecciona un proyecto existente o importa desde un storyboard.
        </p>

        {/* Existing Projects */}
        {projects.length > 0 && (
          <div style={{
            background: COLORS.panel, borderRadius: 16, padding: 20,
            border: `1px solid ${COLORS.panelBorder}`,
            boxShadow: `0 4px 20px ${COLORS.neonGlow}`,
            width: '100%', maxWidth: 500,
          }}>
            <div style={{ ...labelStyle, fontSize: 13, marginBottom: 12 }}>Proyectos existentes</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {projects.map(p => (
                <button
                  key={p.id}
                  onClick={() => fetchProject(p.id).then(() => setLoading(false))}
                  style={{
                    ...btnSecondary,
                    width: '100%', justifyContent: 'space-between',
                    padding: '12px 16px',
                  }}
                >
                  <span>🎬 {p.name || `Proyecto ${p.id.slice(0, 8)}`}</span>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 12,
                    background: p.status === 'completed' ? COLORS.successBg : COLORS.bgGradEnd,
                    color: p.status === 'completed' ? COLORS.success : COLORS.textSecondary,
                  }}>
                    {p.status}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Import from Storyboard */}
        {!showStoryboardPicker ? (
          <button
            onClick={() => { setShowStoryboardPicker(true); fetchStoryboards(); }}
            style={{ ...btnPrimary, padding: '14px 32px', fontSize: 15, borderRadius: 12 }}
          >
            📋 Importar desde Storyboard
          </button>
        ) : (
          <div style={{
            background: COLORS.panel, borderRadius: 16, padding: 20,
            border: `1px solid ${COLORS.panelBorder}`,
            boxShadow: `0 4px 20px ${COLORS.neonGlow}`,
            width: '100%', maxWidth: 500,
          }}>
            <div style={{ ...labelStyle, fontSize: 13, marginBottom: 12 }}>
              Selecciona un Storyboard
            </div>
            {storyboards.length === 0 ? (
              <p style={{ color: COLORS.textLight, fontSize: 13, textAlign: 'center', padding: 16 }}>
                No se encontraron storyboards. Crea uno primero en el nodo Storyboard.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {storyboards.map(sb => (
                  <button
                    key={sb.id}
                    onClick={() => createProject(sb.id)}
                    disabled={creatingProject}
                    style={{
                      ...btnSecondary, width: '100%',
                      padding: '12px 16px',
                      opacity: creatingProject ? 0.6 : 1,
                    }}
                  >
                    📋 {sb.name || `Storyboard ${sb.id.slice(0, 8)}`}
                    {sb.description && (
                      <span style={{ fontSize: 11, color: COLORS.textLight, marginLeft: 8 }}>
                        — {sb.description.slice(0, 40)}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={() => setShowStoryboardPicker(false)}
              style={{ ...btnSmall, marginTop: 12, color: COLORS.textSecondary }}
            >
              ← Cancelar
            </button>
          </div>
        )}

        {/* Status toast */}
        {statusMsg && (
          <div style={{
            position: 'fixed', top: 20, right: 20, zIndex: 100,
            background: COLORS.panel, border: `1px solid ${COLORS.panelBorder}`,
            borderRadius: 10, padding: '10px 18px',
            boxShadow: `0 4px 16px ${COLORS.neonGlow}`,
            color: COLORS.text, fontSize: 13, fontWeight: 500,
          }}>
            {statusMsg}
          </div>
        )}
      </div>
    );
  }

  // ── Render: Main Lab View ──────────────────────────────────────────────────

  return (
    <div style={{
      width: '100%', height: '100%',
      background: `linear-gradient(180deg, ${COLORS.bg} 0%, ${COLORS.bgGradEnd} 100%)`,
      backgroundImage: `
        linear-gradient(${COLORS.gridLine} 1px, transparent 1px),
        linear-gradient(90deg, ${COLORS.gridLine} 1px, transparent 1px),
        linear-gradient(180deg, ${COLORS.bg} 0%, ${COLORS.bgGradEnd} 100%)
      `,
      backgroundSize: '40px 40px, 40px 40px, 100% 100%',
      display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      overflow: 'hidden',
      position: 'relative',
    }}>

      {/* ── Floating Screens (main grid) ──────────────────────────────────── */}
      <div style={{
        flex: 1, overflow: 'auto', padding: '20px 24px 12px',
      }}>
        {/* Project header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
        }}>
          <span style={{ fontSize: 28 }}>🧪</span>
          <div>
            <h2 style={{
              margin: 0, fontSize: 20, fontWeight: 800, color: COLORS.text,
            }}>
              {project.name || 'Proyecto sin nombre'}
            </h2>
            <span style={{
              fontSize: 11, color: COLORS.textSecondary,
            }}>
              {totalCount} clips · {formatDuration(totalDuration)} estimados ·
              Estado: <span style={{
                color: statusColor(project.status as LabClip['status']),
                fontWeight: 700,
              }}>
                {project.status.toUpperCase()}
              </span>
            </span>
          </div>
          <button
            onClick={() => { setProject(null); fetchProjects(); }}
            style={{ ...btnSmall, marginLeft: 'auto', color: COLORS.textSecondary }}
          >
            ← Proyectos
          </button>
        </div>

        {/* Clip Cards Grid */}
        {clips.length === 0 ? (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 60, color: COLORS.textLight, fontSize: 15,
          }}>
            No hay clips en este proyecto. Importa frames desde un storyboard.
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16,
          }}>
            {clips.map((clip, idx) => {
              const isSelected = clip.id === selectedClipId;
              const isHovered = clip.id === hoveredClip;
              const isGen = clip.status === 'generating';
              const isDone = clip.status === 'completed';
              const isErr = clip.status === 'error';

              return (
                <div
                  key={clip.id || idx}
                  onClick={() => setSelectedClipId(clip.id)}
                  onMouseEnter={() => setHoveredClip(clip.id)}
                  onMouseLeave={() => setHoveredClip(null)}
                  style={{
                    background: COLORS.cardBg,
                    border: `2px solid ${isSelected ? COLORS.accent : isGen ? COLORS.generating : COLORS.cardBorder}`,
                    borderRadius: 14,
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'all 0.25s ease',
                    transform: isHovered ? 'translateY(-2px) scale(1.02)' : 'none',
                    boxShadow: isSelected
                      ? `0 4px 24px ${COLORS.neonGlowStrong}`
                      : isGen
                        ? `0 0 16px ${COLORS.neonGlow}, 0 0 32px ${COLORS.neonGlow}`
                        : isHovered
                          ? `0 8px 24px rgba(0,0,0,0.08)`
                          : `0 2px 8px rgba(0,0,0,0.04)`,
                    animation: isGen ? 'labScreenPulse 2s ease-in-out infinite' : 'none',
                    position: 'relative',
                  }}
                >
                  {/* Badge */}
                  <div style={{
                    position: 'absolute', top: 8, left: 8, zIndex: 2,
                    background: statusColor(clip.status),
                    color: '#fff', borderRadius: 8,
                    padding: '2px 8px', fontSize: 11, fontWeight: 700,
                    display: 'flex', alignItems: 'center', gap: 4,
                    boxShadow: `0 2px 8px rgba(0,0,0,0.15)`,
                  }}>
                    {statusIcon(clip.status)} F{idx + 1}
                  </div>

                  {/* Image Area */}
                  <div style={{
                    width: '100%', height: 140, overflow: 'hidden',
                    background: `linear-gradient(135deg, ${COLORS.bgGradEnd}, ${COLORS.bg})`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    position: 'relative',
                  }}>
                    {isDone && clip.output_url && isHovered ? (
                      <video
                        src={clip.output_url}
                        autoPlay muted loop
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : clip.image_url ? (
                      <img
                        src={clip.image_url}
                        alt={`Frame ${idx + 1}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <span style={{ fontSize: 36, opacity: 0.3 }}>🎞️</span>
                    )}
                    {isGen && (
                      <div style={{
                        position: 'absolute', inset: 0,
                        background: 'rgba(33, 150, 243, 0.15)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <div style={{
                          width: 40, height: 40, border: '3px solid transparent',
                          borderTopColor: COLORS.accent, borderRadius: '50%',
                          animation: 'labSpin 0.8s linear infinite',
                        }} />
                      </div>
                    )}
                  </div>

                  {/* Info area */}
                  <div style={{ padding: '10px 12px' }}>
                    <div style={{
                      fontSize: 12, color: COLORS.text, fontWeight: 500,
                      lineHeight: 1.3, marginBottom: 6,
                      overflow: 'hidden', textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {clip.description || 'Sin descripción'}
                    </div>

                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      fontSize: 10, color: COLORS.textLight, marginBottom: 8,
                    }}>
                      <span>⏱ {clip.duration || 4}s</span>
                      <span>🎬 {clip.provider || editConfig.provider}</span>
                    </div>

                    {isErr && clip.error_message && (
                      <div style={{
                        fontSize: 10, color: COLORS.error, background: COLORS.errorBg,
                        borderRadius: 6, padding: '4px 8px', marginBottom: 6,
                        lineHeight: 1.3,
                      }}>
                        {clip.error_message.slice(0, 80)}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {!isDone && !isGen && (
                        <button
                          onClick={(e) => { e.stopPropagation(); generateSingle(clip.frame_index); }}
                          style={{ ...btnSmall, background: COLORS.accent, color: '#fff', fontSize: 10 }}
                          title="Generar clip"
                        >
                          ▶️ Generar
                        </button>
                      )}
                      {(isDone || isErr) && (
                        <button
                          onClick={(e) => { e.stopPropagation(); generateSingle(clip.frame_index); }}
                          style={{ ...btnSmall, background: COLORS.warningBg, color: COLORS.warning, fontSize: 10 }}
                          title="Regenerar clip"
                        >
                          🔄 Regenerar
                        </button>
                      )}
                      {isDone && clip.output_url && (
                        <button
                          onClick={(e) => { e.stopPropagation(); setPreviewClipUrl(clip.output_url); }}
                          style={{ ...btnSmall, background: COLORS.successBg, color: COLORS.success, fontSize: 10 }}
                          title="Vista previa"
                        >
                          👁️ Ver
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditPromptClipId(clip.id);
                          setEditPromptText(clip.description || '');
                        }}
                        style={{ ...btnSmall, fontSize: 10 }}
                        title="Editar prompt"
                      >
                        ✏️
                      </button>
                    </div>
                  </div>

                  {/* Generating progress bar */}
                  {isGen && (
                    <div style={{
                      height: 3, background: COLORS.bgGradEnd,
                      position: 'relative', overflow: 'hidden',
                    }}>
                      <div style={{
                        position: 'absolute', height: '100%', width: '40%',
                        background: `linear-gradient(90deg, transparent, ${COLORS.accent}, transparent)`,
                        animation: 'labProgressSlide 1.5s ease-in-out infinite',
                      }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Central Platform (toolbar) ────────────────────────────────────── */}
      <div style={{
        background: COLORS.toolbarBg,
        borderTop: `1px solid ${COLORS.panelBorder}`,
        padding: '12px 24px',
        backdropFilter: 'blur(12px)',
      }}>
        {/* Progress bar */}
        {totalCount > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10,
          }}>
            <span style={{ fontSize: 12, color: COLORS.textSecondary, fontWeight: 600, minWidth: 90 }}>
              {completedCount}/{totalCount} clips
            </span>
            <div style={{
              flex: 1, height: 8, background: COLORS.bgGradEnd,
              borderRadius: 4, overflow: 'hidden',
            }}>
              <div style={{
                width: `${progressPct}%`, height: '100%',
                background: `linear-gradient(90deg, ${COLORS.accent}, ${COLORS.accentLight})`,
                borderRadius: 4,
                transition: 'width 0.5s ease',
                boxShadow: progressPct > 0 ? `0 0 8px ${COLORS.neonGlow}` : 'none',
              }} />
            </div>
            <span style={{ fontSize: 12, color: COLORS.accent, fontWeight: 700, minWidth: 40 }}>
              {progressPct}%
            </span>
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Generate All */}
          {!isGenerating && !isPaused && (
            <button
              onClick={generateAll}
              disabled={totalCount === 0}
              style={{
                ...btnPrimary,
                opacity: totalCount === 0 ? 0.5 : 1,
                cursor: totalCount === 0 ? 'not-allowed' : 'pointer',
              }}
            >
              ▶️ GENERAR TODO
            </button>
          )}

          {/* Pause */}
          {isGenerating && (
            <button onClick={pauseProject} style={btnSecondary}>
              ⏸ Pausar
            </button>
          )}

          {/* Resume */}
          {isPaused && (
            <button onClick={resumeProject} style={btnPrimary}>
              ▶️ Reanudar
            </button>
          )}

          {/* Preview Animatic */}
          <button
            onClick={() => {
              const firstDone = clips.find(c => c.status === 'completed' && c.output_url);
              if (firstDone) setPreviewClipUrl(firstDone.output_url);
              else showStatus('⚠️ No hay clips completados para previsualizar');
            }}
            style={btnSecondary}
          >
            🎬 Vista Previa
          </button>

          {/* Concatenate */}
          <button
            onClick={concatenateProject}
            disabled={!allCompleted}
            style={{
              ...btnSecondary,
              opacity: allCompleted ? 1 : 0.5,
              cursor: allCompleted ? 'pointer' : 'not-allowed',
            }}
          >
            🔗 Concatenar
          </button>

          {/* Download */}
          <button onClick={downloadProject} style={btnSecondary}>
            📤 Descargar
          </button>

          {/* Send to Editor (placeholder) */}
          <button
            onClick={() => showStatus('📧 Funcionalidad próximamente: Enviar a Editor')}
            style={{ ...btnSmall, color: COLORS.textLight }}
          >
            📧 Enviar a Editor
          </button>
        </div>
      </div>

      {/* ── Bottom Section: Mini Timeline + Config ────────────────────────── */}
      <div style={{
        display: 'flex',
        borderTop: `1px solid ${COLORS.panelBorder}`,
        minHeight: configOpen ? 200 : 48,
        maxHeight: configOpen ? 280 : 48,
        transition: 'all 0.3s ease',
      }}>
        {/* Mini Timeline */}
        <div style={{
          flex: 1, padding: '12px 24px', overflow: 'auto',
          borderRight: `1px solid ${COLORS.panelBorder}`,
          background: COLORS.toolbarBg,
        }}>
          <div style={{
            ...labelStyle, marginBottom: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span>🎞️ LÍNEA DE TIEMPO</span>
            <span style={{ fontSize: 10, fontWeight: 400, color: COLORS.textLight }}>
              {formatDuration(totalDuration)}
            </span>
          </div>
          <div style={{
            display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 4,
          }}>
            {clips.map((clip, idx) => (
              <div
                key={clip.id || idx}
                onClick={() => setSelectedClipId(clip.id)}
                style={{
                  minWidth: 48, height: 36,
                  borderRadius: 6, cursor: 'pointer',
                  border: `2px solid ${clip.id === selectedClipId ? COLORS.accent : 'transparent'}`,
                  background: clip.image_url
                    ? `url(${clip.image_url}) center/cover`
                    : statusColor(clip.status),
                  position: 'relative',
                  transition: 'border-color 0.2s',
                  flexShrink: 0,
                }}
              >
                {/* Status dot */}
                <div style={{
                  position: 'absolute', bottom: 2, right: 2,
                  width: 8, height: 8, borderRadius: '50%',
                  background: statusColor(clip.status),
                  border: '1px solid #fff',
                }} />
                {/* Frame number */}
                <div style={{
                  position: 'absolute', top: 1, left: 3,
                  fontSize: 8, fontWeight: 700, color: '#fff',
                  textShadow: '0 1px 2px rgba(0,0,0,0.6)',
                }}>
                  {idx + 1}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Config Panel */}
        <div style={{
          width: configOpen ? 320 : 48,
          transition: 'width 0.3s ease',
          background: COLORS.configBg,
          overflow: 'hidden',
          position: 'relative',
        }}>
          {/* Toggle button */}
          <button
            onClick={() => setConfigOpen(!configOpen)}
            style={{
              ...btnSmall, position: 'absolute', top: 8,
              left: configOpen ? 8 : '50%',
              transform: configOpen ? 'none' : 'translateX(-50%)',
              zIndex: 2, color: COLORS.accent, background: 'transparent',
            }}
          >
            {configOpen ? '⚙️ Configuración ▾' : '⚙️'}
          </button>

          {configOpen && (
            <div style={{
              padding: '36px 16px 12px', overflow: 'auto', height: '100%',
              display: 'flex', flexDirection: 'column', gap: 10,
            }}>
              {/* Provider */}
              <div>
                <label style={labelStyle}>Proveedor</label>
                <div style={radioGroupStyle}>
                  <RadioOption label="FAL" value="fal" selected={editConfig.provider === 'fal'} onSelect={v => setEditConfig(c => ({ ...c, provider: v }))} recommended />
                  <RadioOption label="Replicate" value="replicate" selected={editConfig.provider === 'replicate'} onSelect={v => setEditConfig(c => ({ ...c, provider: v }))} />
                  <RadioOption label="Local" value="local" selected={editConfig.provider === 'local'} onSelect={v => setEditConfig(c => ({ ...c, provider: v }))} />
                </div>
              </div>

              {/* Quality */}
              <div>
                <label style={labelStyle}>Calidad</label>
                <div style={radioGroupStyle}>
                  <RadioOption label="Borrador" value="draft" selected={editConfig.quality === 'draft'} onSelect={v => setEditConfig(c => ({ ...c, quality: v }))} />
                  <RadioOption label="Estándar" value="standard" selected={editConfig.quality === 'standard'} onSelect={v => setEditConfig(c => ({ ...c, quality: v }))} />
                  <RadioOption label="Alta" value="high" selected={editConfig.quality === 'high'} onSelect={v => setEditConfig(c => ({ ...c, quality: v }))} />
                </div>
              </div>

              {/* FPS */}
              <div>
                <label style={labelStyle}>FPS</label>
                <div style={radioGroupStyle}>
                  {[24, 30, 60].map(f => (
                    <RadioOption key={f} label={`${f}`} value={`${f}`} selected={editConfig.fps === f} onSelect={v => setEditConfig(c => ({ ...c, fps: parseInt(v) }))} />
                  ))}
                </div>
              </div>

              {/* Resolution */}
              <div>
                <label style={labelStyle}>Resolución</label>
                <div style={radioGroupStyle}>
                  <RadioOption label="720p" value="720p" selected={editConfig.resolution === '720p'} onSelect={v => setEditConfig(c => ({ ...c, resolution: v }))} />
                  <RadioOption label="1080p" value="1080p" selected={editConfig.resolution === '1080p'} onSelect={v => setEditConfig(c => ({ ...c, resolution: v }))} />
                </div>
              </div>

              {/* Transition */}
              <div>
                <label style={labelStyle}>Transición</label>
                <div style={radioGroupStyle}>
                  {['fade', 'cut', 'dissolve'].map(t => (
                    <RadioOption key={t} label={t.charAt(0).toUpperCase() + t.slice(1)} value={t} selected={editConfig.transition_default === t} onSelect={v => setEditConfig(c => ({ ...c, transition_default: v }))} />
                  ))}
                </div>
              </div>

              {/* Duration slider */}
              <div>
                <label style={labelStyle}>
                  Duración por frame: {editConfig.duration_default}s
                </label>
                <input
                  type="range"
                  min={2} max={8} step={0.5}
                  value={editConfig.duration_default}
                  onChange={e => setEditConfig(c => ({ ...c, duration_default: parseFloat(e.target.value) }))}
                  style={{ width: '100%', accentColor: COLORS.accent }}
                />
              </div>

              {/* Consistency */}
              <div>
                <label style={labelStyle}>Consistencia</label>
                <div style={radioGroupStyle}>
                  <RadioOption label="Baja" value="low" selected={editConfig.consistency === 'low'} onSelect={v => setEditConfig(c => ({ ...c, consistency: v }))} />
                  <RadioOption label="Media" value="medium" selected={editConfig.consistency === 'medium'} onSelect={v => setEditConfig(c => ({ ...c, consistency: v }))} />
                  <RadioOption label="Alta" value="high" selected={editConfig.consistency === 'high'} onSelect={v => setEditConfig(c => ({ ...c, consistency: v }))} />
                </div>
              </div>

              {/* Save config */}
              <button
                onClick={saveConfig}
                disabled={savingConfig}
                style={{
                  ...btnPrimary, width: '100%', justifyContent: 'center',
                  opacity: savingConfig ? 0.6 : 1, marginTop: 4,
                }}
              >
                {savingConfig ? '⏳ Guardando...' : '💾 Guardar Configuración'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Status Toast ──────────────────────────────────────────────────── */}
      {statusMsg && (
        <div style={{
          position: 'absolute', top: 16, right: 60, zIndex: 100,
          background: COLORS.panel,
          border: `1px solid ${COLORS.panelBorder}`,
          borderRadius: 10, padding: '10px 18px',
          boxShadow: `0 4px 16px ${COLORS.neonGlow}`,
          color: COLORS.text, fontSize: 13, fontWeight: 500,
          animation: 'labFadeIn 0.3s ease',
        }}>
          {statusMsg}
        </div>
      )}

      {/* ── Clip Preview Modal ────────────────────────────────────────────── */}
      {previewClipUrl && (
        <div
          onClick={() => setPreviewClipUrl(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 200,
            background: 'rgba(0, 0, 0, 0.8)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#111', borderRadius: 16,
              border: `2px solid ${COLORS.accent}`,
              boxShadow: `0 0 40px ${COLORS.neonGlowStrong}`,
              padding: 16, maxWidth: '80vw', maxHeight: '80vh',
              cursor: 'default',
            }}
          >
            <video
              src={previewClipUrl}
              controls autoPlay
              style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 8 }}
            />
            <div style={{
              display: 'flex', justifyContent: 'center', marginTop: 12,
            }}>
              <button
                onClick={() => setPreviewClipUrl(null)}
                style={{ ...btnSecondary, color: '#fff', borderColor: COLORS.accent }}
              >
                ✕ Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Edit Prompt Modal ─────────────────────────────────────────────── */}
      {editPromptClipId && (
        <div
          onClick={() => setEditPromptClipId(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 200,
            background: 'rgba(0, 0, 0, 0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: COLORS.panel, borderRadius: 16,
              border: `2px solid ${COLORS.accent}`,
              boxShadow: `0 0 30px ${COLORS.neonGlow}`,
              padding: 24, width: 420, maxWidth: '90vw',
            }}
          >
            <h3 style={{ margin: '0 0 12px', color: COLORS.text, fontSize: 16 }}>
              ✏️ Editar Prompt del Clip
            </h3>
            <textarea
              value={editPromptText}
              onChange={e => setEditPromptText(e.target.value)}
              rows={4}
              style={{
                width: '100%', borderRadius: 8,
                border: `1px solid ${COLORS.panelBorder}`,
                padding: '10px 12px', fontSize: 13,
                fontFamily: "'Inter', system-ui, sans-serif",
                resize: 'vertical', outline: 'none',
                boxSizing: 'border-box',
              }}
              placeholder="Descripción del clip..."
            />
            <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setEditPromptClipId(null)}
                style={btnSecondary}
              >
                Cancelar
              </button>
              <button
                onClick={() => {
                  setProject(prev => {
                    if (!prev) return prev;
                    return {
                      ...prev,
                      clips: prev.clips.map(c =>
                        c.id === editPromptClipId ? { ...c, description: editPromptText } : c
                      ),
                    };
                  });
                  setEditPromptClipId(null);
                  showStatus('✅ Prompt actualizado');
                }}
                style={btnPrimary}
              >
                💾 Guardar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── CSS Animations ────────────────────────────────────────────────── */}
      <style>{`
        @keyframes labPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.1); }
        }
        @keyframes labScreenPulse {
          0%, 100% { box-shadow: 0 0 16px ${COLORS.neonGlow}, 0 0 32px ${COLORS.neonGlow}; }
          50% { box-shadow: 0 0 24px ${COLORS.neonGlowStrong}, 0 0 48px ${COLORS.neonGlowStrong}; }
        }
        @keyframes labSpin {
          to { transform: rotate(360deg); }
        }
        @keyframes labProgressSlide {
          0% { left: -40%; }
          100% { left: 100%; }
        }
        @keyframes labFadeIn {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export { LabNodeLayout };
export default LabNodeLayout;
