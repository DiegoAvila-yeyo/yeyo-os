'use client';

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface StoryboardFrame {
  id: string;
  image_url: string;
  description: string;
  movement: string;
  duration: number;
  camera: string;
  emotion: string;
  transition: string;
  audio_text: string;
  prompt_extra: string;
  sort_order: number;
}

export interface Storyboard {
  id: string;
  name: string;
  description: string;
  frames: StoryboardFrame[];
}

export interface StoryboardNodeLayoutProps {
  storyboardId?: string;
  onSendToLab?: (storyboard: Storyboard) => void;
}

// ─── Constants ─────────────────────────────────────────────────────────────────

const API = 'http://localhost:8000/api/v1/storyboard';

const COLORS = {
  bg: '#F5F0E8',
  panel: '#EDE8DD',
  panelBorder: '#D5CDBE',
  accent: '#0066CC',
  gold: '#D4A847',
  text: '#2C2416',
  textMuted: '#6B5E4D',
  cardBg: '#FDFBF7',
  cardBorder: '#D5CDBE',
  selectedBorder: '#0066CC',
  toolbarBg: '#3A3224',
  toolbarText: '#F5F0E8',
  timelineBg: '#E8E2D6',
  badgeBg: '#E8E2D6',
  inputBg: '#FDFBF7',
  inputBorder: '#C8BFAD',
  hoverBg: '#E8E2D6',
};

const MOVEMENTS = ['static', 'walk', 'run', 'sit', 'turn', 'gesture', 'custom'];
const CAMERAS = ['static', 'pan_left', 'pan_right', 'zoom_in', 'zoom_out', 'dolly'];
const EMOTIONS: { key: string; emoji: string; label: string }[] = [
  { key: 'happy', emoji: '😊', label: 'Feliz' },
  { key: 'sad', emoji: '😢', label: 'Triste' },
  { key: 'surprised', emoji: '😮', label: 'Sorpresa' },
  { key: 'angry', emoji: '😠', label: 'Enojo' },
  { key: 'neutral', emoji: '😐', label: 'Neutral' },
];
const TRANSITIONS = ['cut', 'fade', 'dissolve', 'wipe'];

const ASSET_SECTIONS = [
  { key: 'chars', icon: '🧑', label: 'Personajes' },
  { key: 'bgds', icon: '🏔️', label: 'Fondos' },
  { key: 'audio', icon: '🎵', label: 'Audio' },
  { key: 'notes', icon: '📝', label: 'Notas' },
  { key: 'genai', icon: '✨', label: 'Generar con IA' },
];

const LEFT_W = 220;
const RIGHT_W = 280;
const TIMELINE_H = 56;
const TOOLBAR_H = 44;
const FRAME_W = 200;
const FRAME_IMG_H = 150;
const THUMB_W = 60;
const THUMB_H = 40;

// ─── Styles ────────────────────────────────────────────────────────────────────

const fontSerif = "'Georgia', 'Times New Roman', serif";
const fontMono = "'Menlo', 'Consolas', monospace";

const btnBase: React.CSSProperties = {
  border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12,
  padding: '6px 14px', transition: 'all 0.15s', fontFamily: fontSerif,
};

const btnPrimary: React.CSSProperties = {
  ...btnBase, background: COLORS.accent, color: '#fff',
};

const btnGold: React.CSSProperties = {
  ...btnBase, background: COLORS.gold, color: '#fff',
};

const btnToolbar: React.CSSProperties = {
  ...btnBase, background: 'transparent', color: COLORS.toolbarText,
  border: '1px solid rgba(255,255,255,0.15)', fontSize: 13,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11, fontFamily: fontMono, color: COLORS.textMuted,
  marginBottom: 4, display: 'block', textTransform: 'uppercase', letterSpacing: 0.5,
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '6px 8px', fontSize: 13, fontFamily: fontSerif,
  border: `1px solid ${COLORS.inputBorder}`, borderRadius: 5,
  background: COLORS.inputBg, color: COLORS.text, outline: 'none',
  boxSizing: 'border-box',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle, cursor: 'pointer',
};

const textareaStyle: React.CSSProperties = {
  ...inputStyle, resize: 'vertical', minHeight: 48, fontFamily: fontSerif,
};

// ─── Helpers ───────────────────────────────────────────────────────────────────

function uid(): string {
  return `f-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function makeFrame(order: number): StoryboardFrame {
  return {
    id: uid(),
    image_url: '',
    description: '',
    movement: 'static',
    duration: 4,
    camera: 'static',
    emotion: 'neutral',
    transition: 'cut',
    audio_text: '',
    prompt_extra: '',
    sort_order: order,
  };
}

function movementIcon(m: string): string {
  const map: Record<string, string> = {
    static: '⏹️', walk: '🚶', run: '🏃', sit: '🪑', turn: '🔄', gesture: '🤲', custom: '✏️',
  };
  return map[m] || '⏹️';
}

function cameraIcon(c: string): string {
  const map: Record<string, string> = {
    static: '📷', pan_left: '⬅️', pan_right: '➡️', zoom_in: '🔍', zoom_out: '🔭', dolly: '🎥',
  };
  return map[c] || '📷';
}

// ─── Component ─────────────────────────────────────────────────────────────────

const StoryboardNodeLayout: React.FC<StoryboardNodeLayoutProps> = ({
  storyboardId,
  onSendToLab,
}) => {
  // State
  const [storyboard, setStoryboard] = useState<Storyboard>({
    id: storyboardId || '',
    name: 'Nuevo Storyboard',
    description: '',
    frames: [makeFrame(0), makeFrame(1), makeFrame(2)],
  });
  const [selectedFrameId, setSelectedFrameId] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [directorNotes, setDirectorNotes] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [autoGenModalOpen, setAutoGenModalOpen] = useState(false);
  const [autoGenPrompt, setAutoGenPrompt] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);

  const frames = storyboard.frames;
  const selectedFrame = useMemo(
    () => frames.find(f => f.id === selectedFrameId) || null,
    [frames, selectedFrameId]
  );

  const totalDuration = useMemo(() => frames.reduce((s, f) => s + f.duration, 0), [frames]);

  // ── Load storyboard from backend ──────────────────────────────────────────
  useEffect(() => {
    if (!storyboardId) return;
    (async () => {
      try {
        const res = await fetch(`${API}/${storyboardId}`);
        if (res.ok) {
          const data = await res.json();
          setStoryboard(data);
          if (data.frames?.length) setSelectedFrameId(data.frames[0].id);
        }
      } catch { /* silently fail */ }
    })();
  }, [storyboardId]);

  // ── Frame helpers ─────────────────────────────────────────────────────────
  const updateFrames = useCallback((updater: (prev: StoryboardFrame[]) => StoryboardFrame[]) => {
    setStoryboard(prev => ({ ...prev, frames: updater(prev.frames) }));
  }, []);

  const updateSelectedFrame = useCallback((patch: Partial<StoryboardFrame>) => {
    if (!selectedFrameId) return;
    updateFrames(prev =>
      prev.map(f => f.id === selectedFrameId ? { ...f, ...patch } : f)
    );
  }, [selectedFrameId, updateFrames]);

  const addFrame = useCallback(() => {
    const newFrame = makeFrame(frames.length);
    updateFrames(prev => [...prev, newFrame]);
    setSelectedFrameId(newFrame.id);
  }, [frames.length, updateFrames]);

  const toggleSection = useCallback((key: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }, []);

  // ── Drag and drop reorder ─────────────────────────────────────────────────
  const handleDragStart = useCallback((idx: number) => {
    setDragIdx(idx);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, idx: number) => {
    e.preventDefault();
    setDragOverIdx(idx);
  }, []);

  const handleDrop = useCallback((targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) {
      setDragIdx(null);
      setDragOverIdx(null);
      return;
    }
    updateFrames(prev => {
      const next = [...prev];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(targetIdx, 0, moved);
      return next.map((f, i) => ({ ...f, sort_order: i }));
    });
    setDragIdx(null);
    setDragOverIdx(null);
  }, [dragIdx, updateFrames]);

  // ── API calls ─────────────────────────────────────────────────────────────
  const showStatus = useCallback((msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(''), 3000);
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const method = storyboard.id ? 'PUT' : 'POST';
      const url = storyboard.id ? `${API}/${storyboard.id}` : API;
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(storyboard),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      if (data.id) setStoryboard(prev => ({ ...prev, id: data.id }));
      showStatus('✅ Guardado exitosamente');
    } catch (err) {
      showStatus(`❌ Error al guardar: ${err}`);
    } finally {
      setSaving(false);
    }
  }, [storyboard, showStatus]);

  const handleExport = useCallback(async () => {
    if (!storyboard.id) {
      showStatus('⚠️ Guarda el storyboard primero');
      return;
    }
    try {
      const res = await fetch(`${API}/${storyboard.id}/export`, { method: 'POST' });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${storyboard.name || 'storyboard'}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showStatus('📥 Exportado');
    } catch (err) {
      showStatus(`❌ Error al exportar: ${err}`);
    }
  }, [storyboard, showStatus]);

  const handleGenerate = useCallback(async (prompt: string) => {
    if (!prompt.trim()) return;
    setGenerating(true);
    try {
      const res = await fetch(`${API}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), num_frames: 6 }),
      });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      if (data.frames) {
        setStoryboard(prev => ({
          ...prev,
          name: data.name || prev.name,
          description: data.description || prev.description,
          frames: data.frames.map((f: StoryboardFrame, i: number) => ({
            ...makeFrame(i),
            ...f,
            id: f.id || uid(),
            sort_order: i,
          })),
        }));
        showStatus(`✨ Generado: ${data.frames.length} frames`);
      }
    } catch (err) {
      showStatus(`❌ Error al generar: ${err}`);
    } finally {
      setGenerating(false);
      setAutoGenModalOpen(false);
    }
  }, [showStatus]);

  // ── Animatic Preview ──────────────────────────────────────────────────────
  const AnimaticPreview = useMemo(() => {
    if (!previewOpen) return null;
    return (
      <AnimaticModal
        frames={frames}
        onClose={() => setPreviewOpen(false)}
      />
    );
  }, [previewOpen, frames]);

  // ═══════════════════════════════════════════════════════════════════════════
  //  RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', width: '100%', height: '100%',
      background: COLORS.bg, color: COLORS.text, fontFamily: fontSerif,
      overflow: 'hidden', position: 'relative',
    }}>
      {/* ── Status toast ──────────────────────────────────────────────── */}
      {statusMsg && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 100, background: COLORS.toolbarBg, color: COLORS.toolbarText,
          padding: '8px 20px', borderRadius: 8, fontSize: 13, fontFamily: fontMono,
          boxShadow: '0 4px 16px rgba(0,0,0,0.2)', animation: 'fadeIn 0.2s ease',
        }}>
          {statusMsg}
        </div>
      )}

      {/* ── Main body (3 columns) ─────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

        {/* ═══ LEFT PANEL — Assets ═══════════════════════════════════════ */}
        <aside style={{
          width: LEFT_W, flexShrink: 0, background: COLORS.panel,
          borderRight: `1px solid ${COLORS.panelBorder}`,
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
        }}>
          <div style={{
            padding: '14px 12px 8px', fontFamily: fontSerif, fontSize: 15,
            fontWeight: 700, color: COLORS.gold, borderBottom: `1px solid ${COLORS.panelBorder}`,
            letterSpacing: 0.5,
          }}>
            📋 Assets
          </div>

          {ASSET_SECTIONS.map(sec => {
            const collapsed = collapsedSections.has(sec.key);
            return (
              <div key={sec.key}>
                <button
                  onClick={() => toggleSection(sec.key)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 12px', border: 'none', background: 'transparent',
                    cursor: 'pointer', fontSize: 13, fontFamily: fontSerif,
                    color: COLORS.text, borderBottom: `1px solid ${COLORS.panelBorder}`,
                    textAlign: 'left',
                  }}
                >
                  <span style={{ fontSize: 10, opacity: 0.6 }}>{collapsed ? '▶' : '▼'}</span>
                  <span>{sec.icon}</span>
                  <span style={{ fontWeight: 600 }}>{sec.label}</span>
                </button>

                {!collapsed && (
                  <div style={{ padding: '8px 12px' }}>
                    {sec.key === 'chars' && (
                      <div style={{ fontSize: 12, color: COLORS.textMuted, fontStyle: 'italic' }}>
                        Importar desde nodo Imagen
                      </div>
                    )}
                    {sec.key === 'bgds' && (
                      <div style={{ fontSize: 12, color: COLORS.textMuted, fontStyle: 'italic' }}>
                        Importar desde nodo Imagen
                      </div>
                    )}
                    {sec.key === 'audio' && (
                      <div style={{ fontSize: 12, color: COLORS.textMuted, fontStyle: 'italic' }}>
                        Grabar / importar audio
                      </div>
                    )}
                    {sec.key === 'notes' && (
                      <textarea
                        value={directorNotes}
                        onChange={e => setDirectorNotes(e.target.value)}
                        placeholder="Notas del director..."
                        style={{ ...textareaStyle, minHeight: 72, fontSize: 12 }}
                      />
                    )}
                    {sec.key === 'genai' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <input
                          value={aiPrompt}
                          onChange={e => setAiPrompt(e.target.value)}
                          placeholder="Describe tu historia..."
                          style={inputStyle}
                          onKeyDown={e => e.key === 'Enter' && handleGenerate(aiPrompt)}
                        />
                        <button
                          onClick={() => handleGenerate(aiPrompt)}
                          disabled={generating}
                          style={{
                            ...btnGold,
                            opacity: generating ? 0.6 : 1,
                          }}
                        >
                          {generating ? '⏳ Generando...' : '✨ Generar Storyboard'}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Storyboard info at bottom */}
          <div style={{
            marginTop: 'auto', padding: '10px 12px',
            borderTop: `1px solid ${COLORS.panelBorder}`, fontSize: 11,
            fontFamily: fontMono, color: COLORS.textMuted,
          }}>
            <input
              value={storyboard.name}
              onChange={e => setStoryboard(prev => ({ ...prev, name: e.target.value }))}
              style={{
                ...inputStyle, fontSize: 13, fontWeight: 700,
                fontFamily: fontSerif, marginBottom: 6,
              }}
              placeholder="Nombre del storyboard"
            />
            <textarea
              value={storyboard.description}
              onChange={e => setStoryboard(prev => ({ ...prev, description: e.target.value }))}
              style={{ ...textareaStyle, fontSize: 11, minHeight: 40 }}
              placeholder="Descripción..."
            />
          </div>
        </aside>

        {/* ═══ CENTER — Storyboard Canvas ════════════════════════════════ */}
        <main style={{
          flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{
            padding: '10px 16px 6px', fontSize: 17, fontWeight: 700,
            color: COLORS.gold, fontFamily: fontSerif, letterSpacing: 0.5,
            display: 'flex', alignItems: 'center', gap: 8,
            borderBottom: `1px solid ${COLORS.panelBorder}`,
          }}>
            <span style={{ fontSize: 20 }}>🎬</span>
            <span>Storyboard Canvas</span>
            <span style={{
              fontSize: 11, fontFamily: fontMono, color: COLORS.textMuted,
              marginLeft: 'auto',
            }}>
              {frames.length} frames · ⏱ {totalDuration}s
            </span>
          </div>

          <div style={{
            flex: 1, overflowY: 'auto', padding: 16,
            display: 'flex', flexWrap: 'wrap', gap: 14,
            alignContent: 'flex-start',
          }}>
            {frames.map((frame, idx) => {
              const isSelected = frame.id === selectedFrameId;
              const isDragOver = dragOverIdx === idx && dragIdx !== idx;
              return (
                <div
                  key={frame.id}
                  draggable
                  onDragStart={() => handleDragStart(idx)}
                  onDragOver={e => handleDragOver(e, idx)}
                  onDrop={() => handleDrop(idx)}
                  onDragEnd={() => { setDragIdx(null); setDragOverIdx(null); }}
                  onClick={() => setSelectedFrameId(frame.id)}
                  style={{
                    width: FRAME_W,
                    background: COLORS.cardBg,
                    border: `2px solid ${isSelected ? COLORS.selectedBorder : isDragOver ? COLORS.gold : COLORS.cardBorder}`,
                    borderRadius: 8,
                    overflow: 'hidden',
                    cursor: 'pointer',
                    boxShadow: isSelected
                      ? `0 0 0 2px ${COLORS.accent}33, 0 4px 12px rgba(0,0,0,0.08)`
                      : '0 2px 6px rgba(0,0,0,0.05)',
                    transition: 'all 0.2s',
                    opacity: dragIdx === idx ? 0.5 : 1,
                    transform: isDragOver ? 'scale(1.02)' : 'none',
                  }}
                >
                  {/* Image area */}
                  <div style={{
                    width: '100%', height: FRAME_IMG_H,
                    background: frame.image_url
                      ? `url(${frame.image_url}) center/cover`
                      : `linear-gradient(135deg, ${COLORS.badgeBg} 0%, ${COLORS.panel} 100%)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    position: 'relative',
                  }}>
                    {!frame.image_url && (
                      <span style={{
                        fontSize: 32, opacity: 0.3, fontFamily: fontSerif,
                      }}>
                        {idx + 1}
                      </span>
                    )}
                    {/* Frame number badge */}
                    <span style={{
                      position: 'absolute', top: 4, left: 4,
                      background: 'rgba(0,0,0,0.5)', color: '#fff',
                      fontSize: 10, fontFamily: fontMono,
                      padding: '1px 6px', borderRadius: 4,
                    }}>
                      #{idx + 1}
                    </span>
                  </div>

                  {/* Description */}
                  <div style={{
                    padding: '6px 8px', fontSize: 12, color: COLORS.text,
                    lineHeight: 1.3, height: 34, overflow: 'hidden',
                    display: '-webkit-box', WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical' as const,
                  }}>
                    {frame.description || <span style={{ color: COLORS.textMuted, fontStyle: 'italic' }}>Sin descripción</span>}
                  </div>

                  {/* Badges */}
                  <div style={{
                    display: 'flex', gap: 4, padding: '2px 8px 6px',
                    flexWrap: 'wrap',
                  }}>
                    <span style={{
                      fontSize: 10, background: COLORS.badgeBg, borderRadius: 4,
                      padding: '1px 5px', fontFamily: fontMono,
                    }}>
                      {movementIcon(frame.movement)}
                    </span>
                    <span style={{
                      fontSize: 10, background: COLORS.badgeBg, borderRadius: 4,
                      padding: '1px 5px', fontFamily: fontMono,
                    }}>
                      {frame.duration}s
                    </span>
                    <span style={{
                      fontSize: 10, background: COLORS.badgeBg, borderRadius: 4,
                      padding: '1px 5px', fontFamily: fontMono,
                    }}>
                      {cameraIcon(frame.camera)}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Add frame button */}
            <div
              onClick={addFrame}
              style={{
                width: FRAME_W, height: FRAME_IMG_H + 60,
                background: 'transparent',
                border: `2px dashed ${COLORS.panelBorder}`,
                borderRadius: 8, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'all 0.2s',
                gap: 6,
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLDivElement).style.borderColor = COLORS.accent;
                (e.currentTarget as HTMLDivElement).style.background = `${COLORS.accent}08`;
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLDivElement).style.borderColor = COLORS.panelBorder;
                (e.currentTarget as HTMLDivElement).style.background = 'transparent';
              }}
            >
              <span style={{ fontSize: 28, color: COLORS.textMuted }}>+</span>
              <span style={{ fontSize: 12, color: COLORS.textMuted, fontFamily: fontMono }}>
                Agregar frame
              </span>
            </div>
          </div>
        </main>

        {/* ═══ RIGHT PANEL — Frame Details ═══════════════════════════════ */}
        <aside style={{
          width: RIGHT_W, flexShrink: 0, background: COLORS.panel,
          borderLeft: `1px solid ${COLORS.panelBorder}`,
          display: 'flex', flexDirection: 'column', overflowY: 'auto',
        }}>
          <div style={{
            padding: '14px 12px 8px', fontFamily: fontSerif, fontSize: 15,
            fontWeight: 700, color: COLORS.gold,
            borderBottom: `1px solid ${COLORS.panelBorder}`,
          }}>
            🎞️ Detalles del Frame
          </div>

          {selectedFrame ? (
            <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Description */}
              <div>
                <label style={labelStyle}>Descripción</label>
                <textarea
                  value={selectedFrame.description}
                  onChange={e => updateSelectedFrame({ description: e.target.value })}
                  placeholder="¿Qué sucede en esta escena?"
                  style={{ ...textareaStyle, minHeight: 64 }}
                />
              </div>

              {/* Movement */}
              <div>
                <label style={labelStyle}>Movimiento</label>
                <select
                  value={selectedFrame.movement}
                  onChange={e => updateSelectedFrame({ movement: e.target.value })}
                  style={selectStyle}
                >
                  {MOVEMENTS.map(m => (
                    <option key={m} value={m}>{movementIcon(m)} {m}</option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div>
                <label style={labelStyle}>Duración: {selectedFrame.duration}s</label>
                <input
                  type="range"
                  min={2} max={8} step={0.5}
                  value={selectedFrame.duration}
                  onChange={e => updateSelectedFrame({ duration: parseFloat(e.target.value) })}
                  style={{ width: '100%', accentColor: COLORS.accent }}
                />
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 10, fontFamily: fontMono, color: COLORS.textMuted,
                }}>
                  <span>2s</span><span>8s</span>
                </div>
              </div>

              {/* Camera */}
              <div>
                <label style={labelStyle}>Cámara</label>
                <select
                  value={selectedFrame.camera}
                  onChange={e => updateSelectedFrame({ camera: e.target.value })}
                  style={selectStyle}
                >
                  {CAMERAS.map(c => (
                    <option key={c} value={c}>{cameraIcon(c)} {c}</option>
                  ))}
                </select>
              </div>

              {/* Emotion */}
              <div>
                <label style={labelStyle}>Emoción</label>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {EMOTIONS.map(em => (
                    <button
                      key={em.key}
                      onClick={() => updateSelectedFrame({ emotion: em.key })}
                      title={em.label}
                      style={{
                        ...btnBase,
                        padding: '4px 8px', fontSize: 18,
                        background: selectedFrame.emotion === em.key ? COLORS.accent : COLORS.badgeBg,
                        border: selectedFrame.emotion === em.key
                          ? `2px solid ${COLORS.accent}`
                          : `1px solid ${COLORS.inputBorder}`,
                        borderRadius: 8,
                        filter: selectedFrame.emotion === em.key ? 'none' : 'grayscale(0.4)',
                        transform: selectedFrame.emotion === em.key ? 'scale(1.1)' : 'none',
                      }}
                    >
                      {em.emoji}
                    </button>
                  ))}
                </div>
              </div>

              {/* Transition */}
              <div>
                <label style={labelStyle}>Transición</label>
                <select
                  value={selectedFrame.transition}
                  onChange={e => updateSelectedFrame({ transition: e.target.value })}
                  style={selectStyle}
                >
                  {TRANSITIONS.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Audio / Dialogue */}
              <div>
                <label style={labelStyle}>Audio / Diálogo</label>
                <textarea
                  value={selectedFrame.audio_text}
                  onChange={e => updateSelectedFrame({ audio_text: e.target.value })}
                  placeholder="Diálogo o indicaciones de audio..."
                  style={{ ...textareaStyle, minHeight: 48 }}
                />
              </div>

              {/* Prompt Extra */}
              <div>
                <label style={labelStyle}>Prompt Extra (IA)</label>
                <textarea
                  value={selectedFrame.prompt_extra}
                  onChange={e => updateSelectedFrame({ prompt_extra: e.target.value })}
                  placeholder="Hints adicionales para generación IA..."
                  style={{ ...textareaStyle, minHeight: 48, fontSize: 11, fontFamily: fontMono }}
                />
              </div>

              {/* Delete frame */}
              <button
                onClick={() => {
                  if (frames.length <= 1) return;
                  updateFrames(prev => prev.filter(f => f.id !== selectedFrameId));
                  setSelectedFrameId(frames[0]?.id !== selectedFrameId ? frames[0]?.id : frames[1]?.id || null);
                }}
                style={{
                  ...btnBase, background: '#dc3545', color: '#fff',
                  marginTop: 4, fontSize: 11,
                  opacity: frames.length <= 1 ? 0.4 : 1,
                  cursor: frames.length <= 1 ? 'not-allowed' : 'pointer',
                }}
                disabled={frames.length <= 1}
              >
                🗑️ Eliminar Frame
              </button>
            </div>
          ) : (
            <div style={{
              padding: 24, textAlign: 'center', color: COLORS.textMuted,
              fontStyle: 'italic', fontSize: 13,
            }}>
              Selecciona un frame para editar sus detalles
            </div>
          )}
        </aside>
      </div>

      {/* ═══ TIMELINE BAR ════════════════════════════════════════════════════ */}
      <div
        ref={timelineRef}
        style={{
          height: TIMELINE_H, background: COLORS.timelineBg,
          borderTop: `1px solid ${COLORS.panelBorder}`,
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '0 12px', overflowX: 'auto', flexShrink: 0,
        }}
      >
        <span style={{
          fontSize: 11, fontFamily: fontMono, color: COLORS.textMuted,
          marginRight: 6, whiteSpace: 'nowrap',
        }}>
          ⏱ {totalDuration}s ({frames.length} frames)
        </span>

        {frames.map((frame, idx) => (
          <div
            key={frame.id}
            onClick={() => setSelectedFrameId(frame.id)}
            style={{
              width: THUMB_W, height: THUMB_H, flexShrink: 0,
              background: frame.image_url
                ? `url(${frame.image_url}) center/cover`
                : `linear-gradient(135deg, ${COLORS.cardBg}, ${COLORS.badgeBg})`,
              border: `2px solid ${frame.id === selectedFrameId ? COLORS.accent : COLORS.cardBorder}`,
              borderRadius: 4, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'border-color 0.15s',
              position: 'relative',
            }}
          >
            {!frame.image_url && (
              <span style={{ fontSize: 12, color: COLORS.textMuted, fontFamily: fontMono }}>
                {idx + 1}
              </span>
            )}
            <span style={{
              position: 'absolute', bottom: 1, right: 2,
              fontSize: 8, fontFamily: fontMono, color: COLORS.textMuted,
              background: 'rgba(255,255,255,0.7)', padding: '0 2px', borderRadius: 2,
            }}>
              {frame.duration}s
            </span>
          </div>
        ))}
      </div>

      {/* ═══ TOOLBAR ═════════════════════════════════════════════════════════ */}
      <div style={{
        height: TOOLBAR_H, background: COLORS.toolbarBg,
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '0 14px', flexShrink: 0,
      }}>
        <button onClick={handleSave} disabled={saving} style={{
          ...btnToolbar, opacity: saving ? 0.6 : 1,
        }}>
          💾 {saving ? 'Guardando...' : 'Guardar'}
        </button>
        <button onClick={handleExport} style={btnToolbar}>
          📤 Exportar JSON
        </button>
        <button onClick={() => setPreviewOpen(true)} style={btnToolbar}>
          ▶️ Preview Animatic
        </button>
        <button onClick={() => setAutoGenModalOpen(true)} style={{
          ...btnToolbar, color: COLORS.gold, borderColor: `${COLORS.gold}44`,
        }}>
          🤖 Auto Generar
        </button>

        <div style={{ flex: 1 }} />

        <button
          onClick={() => onSendToLab?.(storyboard)}
          style={{
            ...btnToolbar, color: COLORS.gold, borderColor: `${COLORS.gold}44`,
          }}
        >
          🎬 Enviar al Lab
        </button>
      </div>

      {/* ═══ Animatic Preview Modal ══════════════════════════════════════════ */}
      {AnimaticPreview}

      {/* ═══ Auto Generate Modal ═════════════════════════════════════════════ */}
      {autoGenModalOpen && (
        <div
          onClick={() => setAutoGenModalOpen(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 200,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: COLORS.cardBg, borderRadius: 12, padding: 24,
              width: 440, boxShadow: '0 16px 48px rgba(0,0,0,0.25)',
              border: `2px solid ${COLORS.gold}44`,
            }}
          >
            <h3 style={{
              margin: '0 0 12px', fontSize: 18, fontFamily: fontSerif,
              color: COLORS.gold,
            }}>
              🤖 Auto Generar Storyboard
            </h3>
            <p style={{ fontSize: 13, color: COLORS.textMuted, marginBottom: 12 }}>
              Describe tu historia y la IA generará frames automáticamente.
            </p>
            <textarea
              value={autoGenPrompt}
              onChange={e => setAutoGenPrompt(e.target.value)}
              placeholder="Ej: Una historia sobre un robot que descubre las emociones..."
              style={{ ...textareaStyle, minHeight: 100, marginBottom: 12 }}
              autoFocus
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setAutoGenModalOpen(false)} style={{
                ...btnBase, background: COLORS.badgeBg, color: COLORS.text,
              }}>
                Cancelar
              </button>
              <button
                onClick={() => handleGenerate(autoGenPrompt)}
                disabled={generating}
                style={{ ...btnGold, opacity: generating ? 0.6 : 1 }}
              >
                {generating ? '⏳ Generando...' : '✨ Generar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Animatic Preview Modal ────────────────────────────────────────────────────

function AnimaticModal({
  frames,
  onClose,
}: {
  frames: StoryboardFrame[];
  onClose: () => void;
}) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const frame = frames[currentIdx];
  const total = frames.length;

  // Auto-advance
  useEffect(() => {
    if (!playing || !frame) return;
    timerRef.current = setTimeout(() => {
      setCurrentIdx(prev => (prev + 1 < total ? prev + 1 : 0));
    }, frame.duration * 1000);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [currentIdx, playing, frame, total]);

  const goPrev = useCallback(() => {
    setCurrentIdx(prev => (prev > 0 ? prev - 1 : total - 1));
  }, [total]);

  const goNext = useCallback(() => {
    setCurrentIdx(prev => (prev + 1 < total ? prev + 1 : 0));
  }, [total]);

  // Keyboard controls
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
      if (e.key === ' ') { e.preventDefault(); setPlaying(p => !p); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose, goPrev, goNext]);

  if (!frame) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 300,
        background: 'rgba(0,0,0,0.85)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div onClick={e => e.stopPropagation()} style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 12, maxWidth: 840,
      }}>
        {/* Frame info */}
        <div style={{
          color: '#fff', fontSize: 13, fontFamily: fontMono,
          background: 'rgba(0,0,0,0.5)', padding: '4px 14px',
          borderRadius: 6,
        }}>
          Frame {currentIdx + 1}/{total} — {frame.duration}s
          {frame.description ? ` — ${frame.description.slice(0, 50)}` : ''}
        </div>

        {/* Frame display with Ken Burns */}
        <div style={{
          width: 800, height: 450, borderRadius: 8, overflow: 'hidden',
          position: 'relative', background: '#111',
        }}>
          <div
            key={`kb-${currentIdx}-${playing}`}
            style={{
              width: '100%', height: '100%',
              background: frame.image_url
                ? `url(${frame.image_url}) center/cover`
                : `linear-gradient(135deg, #2C2416 0%, #3A3224 50%, #2C2416 100%)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              animation: playing ? `kenBurns ${frame.duration}s ease-in-out forwards` : 'none',
              transformOrigin: 'center center',
            }}
          >
            {!frame.image_url && (
              <span style={{
                fontSize: 64, color: 'rgba(255,255,255,0.15)', fontFamily: fontSerif,
              }}>
                {currentIdx + 1}
              </span>
            )}
          </div>

          {/* Description overlay */}
          {frame.description && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              background: 'linear-gradient(transparent, rgba(0,0,0,0.75))',
              padding: '24px 20px 14px',
              color: '#fff', fontSize: 15, fontFamily: fontSerif,
              textShadow: '0 1px 4px rgba(0,0,0,0.5)',
            }}>
              {frame.description}
            </div>
          )}
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button onClick={goPrev} style={{
            ...btnBase, background: 'rgba(255,255,255,0.15)', color: '#fff',
            fontSize: 18, padding: '6px 16px',
          }}>◀️</button>
          <button onClick={() => setPlaying(p => !p)} style={{
            ...btnBase, background: 'rgba(255,255,255,0.15)', color: '#fff',
            fontSize: 18, padding: '6px 16px',
          }}>
            {playing ? '⏸️' : '▶️'}
          </button>
          <button onClick={goNext} style={{
            ...btnBase, background: 'rgba(255,255,255,0.15)', color: '#fff',
            fontSize: 18, padding: '6px 16px',
          }}>▶️</button>
          <button onClick={onClose} style={{
            ...btnBase, background: 'rgba(220,53,69,0.8)', color: '#fff',
            fontSize: 12, padding: '6px 14px', marginLeft: 12,
          }}>
            ✕ Cerrar
          </button>
        </div>

        {/* Progress bar */}
        <div style={{
          width: 800, height: 4, background: 'rgba(255,255,255,0.15)',
          borderRadius: 2, overflow: 'hidden',
        }}>
          <div style={{
            width: `${((currentIdx + 1) / total) * 100}%`,
            height: '100%', background: COLORS.gold,
            transition: 'width 0.3s',
          }} />
        </div>
      </div>

      {/* Ken Burns keyframe animation injected via style tag */}
      <style>{`
        @keyframes kenBurns {
          0% { transform: scale(1.0); }
          100% { transform: scale(1.05); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateX(-50%) translateY(-8px); }
          to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      `}</style>
    </div>
  );
}

// ─── Exports ───────────────────────────────────────────────────────────────────

export { StoryboardNodeLayout };
export default StoryboardNodeLayout;
