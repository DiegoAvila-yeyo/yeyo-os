/**
 * YeyoOS — VideoNodeLayout v3
 * Editor de video custom con API para IA.
 * La IA puede controlar el editor via videoEditorRef.current.*
 */
"use client"

import React, {
  useState, useRef, useCallback, useEffect, useImperativeHandle, forwardRef
} from "react"

const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36)

// ─── Tipos ────────────────────────────────────────────────────────────────────

export interface ClipInfo {
  id: string
  nombre: string
  duracion: number          // duración del segmento en la timeline
  tipo: "video" | "audio" | "imagen"
  url?: string
  trackIndex: number        // 0=V1, 1=V2, 2=A1, 3=A2
  startTime: number         // inicio en el timeline (segundos)
  srcOffset: number         // inicio en el archivo fuente (segundos)
  thumbnails?: string[]     // data URLs de frames
}

export interface VideoEditorAPI {
  play: () => void
  pause: () => void
  seek: (t: number) => void
  splitAt: (t?: number) => void
  deleteClip: (id?: string) => void
  addClip: (url: string, name: string) => Promise<void>
  getState: () => { clips: ClipInfo[]; currentTime: number; duration: number }
}

export interface VideoNodeLayoutProps {
  clips?: ClipInfo[]
  onClipAdd?: (clip: ClipInfo) => void
  onStateChange?: (state: ReturnType<VideoEditorAPI["getState"]>) => void
  videoSrc?: string
  nodeId?: string
  chatMessages?: Array<{ id: string; role: "user" | "assistant"; content: string }>
  onChatSend?: (msg: string) => void
}

// ─── Constantes ───────────────────────────────────────────────────────────────

const PX_PER_SEC = 60
const TRACK_H = 48
const RULER_H = 24
const LABEL_W = 44
const TRACKS = [
  { id: "v1", label: "V1", color: "#1A56C4", idx: 0 },
  { id: "v2", label: "V2", color: "#1e40af", idx: 1 },
  { id: "a1", label: "A1", color: "#166534", idx: 2 },
  { id: "a2", label: "A2", color: "#065f46", idx: 3 },
]

function fmt(s: number) {
  const m = Math.floor(s / 60), sec = Math.floor(s % 60), cs = Math.floor((s % 1) * 10)
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${cs}`
}

// ─── Extrae thumbnails de un video ────────────────────────────────────────────

async function extractFrames(url: string, count: number, srcOffset = 0): Promise<string[]> {
  return new Promise(resolve => {
    const v = document.createElement("video")
    v.src = url; v.crossOrigin = "anonymous"; v.muted = true
    const frames: string[] = []
    let i = 0
    v.addEventListener("loadedmetadata", () => {
      const dur = Math.min(v.duration - srcOffset, 99999)
      const step = dur / count
      const seek = () => {
        if (i >= count) { v.remove(); resolve(frames); return }
        v.currentTime = srcOffset + i * step
      }
      v.addEventListener("seeked", () => {
        const c = document.createElement("canvas")
        c.width = 80; c.height = 45
        c.getContext("2d")?.drawImage(v, 0, 0, 80, 45)
        frames.push(c.toDataURL("image/jpeg", 0.5))
        i++; seek()
      })
      seek()
    })
    v.load()
  })
}

// ─── Componente principal ─────────────────────────────────────────────────────

const VideoNodeLayout = forwardRef<VideoEditorAPI, VideoNodeLayoutProps>(
  function VideoNodeLayout({ onClipAdd, onStateChange, nodeId, chatMessages: externalMsgs, onChatSend }, ref) {
    const [clips, setClips] = useState<ClipInfo[]>([])
    const [currentTime, setCurrentTime] = useState(0)
    const [playing, setPlaying] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)
    const [thumbs, setThumbs] = useState<Record<string, string[]>>({})

    // ── Chat state ────────────────────────────────────────────────────────────
    const [localMsgs, setLocalMsgs] = useState<Array<{ id: string; role: "user" | "assistant"; content: string }>>([])
    const [chatInput, setChatInput] = useState("")
    const [aiTyping, setAiTyping] = useState(false)
    const chatEndRef = useRef<HTMLDivElement>(null)
    const chatMessages = externalMsgs ?? localMsgs

    const videoRef = useRef<HTMLVideoElement>(null)
    const rafRef = useRef<number | null>(null)
    const rafTickRef = useRef<((t: number) => void) | null>(null)
    const clipsRef = useRef(clips)
    const currentTimeRef = useRef(0)
    const activeClipIdRef = useRef("")
    const timelineRef = useRef<HTMLDivElement>(null)
    const scrubbingRef = useRef(false)

    useEffect(() => { clipsRef.current = clips }, [clips])

    const totalDuration = clips.reduce((max, c) => Math.max(max, c.startTime + c.duracion), 10)

    // ── Thumbnails ─────────────────────────────────────────────────────────────
    useEffect(() => {
      clips.forEach(c => {
        if (c.url && !thumbs[c.id] && c.duracion > 0 && c.tipo === "video") {
          extractFrames(c.url, Math.max(4, Math.ceil(c.duracion)), c.srcOffset)
            .then(frames => setThumbs(prev => ({ ...prev, [c.id]: frames })))
        }
      })
    }, [clips, thumbs])

    // ── Carga metadata de nuevos clips ─────────────────────────────────────────
    useEffect(() => {
      clips.filter(c => c.url && c.duracion === 0).forEach(c => {
        const v = document.createElement("video")
        v.src = c.url!; v.preload = "metadata"
        v.onloadedmetadata = () => {
          setClips(prev => prev.map(x =>
            x.id === c.id ? { ...x, duracion: v.duration } : x
          ))
          v.remove()
        }
        v.load()
      })
    }, [clips])

    // ── Sync video al tiempo t ──────────────────────────────────────────────────
    const syncVideoToTime = useCallback((t: number) => {
      const v = videoRef.current
      const clip = clipsRef.current.find(
        c => c.tipo === "video" && c.url && t >= c.startTime && t < c.startTime + c.duracion
      )
      if (!v || !clip) { v?.pause(); return }
      const srcTime = clip.srcOffset + (t - clip.startTime)
      if (v.src !== clip.url) v.src = clip.url!
      if (Math.abs(v.currentTime - srcTime) > 0.15) v.currentTime = srcTime
      activeClipIdRef.current = clip.id
    }, [])

    // ── RAF tick ────────────────────────────────────────────────────────────────
    rafTickRef.current = () => {
      const v = videoRef.current
      if (!v) { rafRef.current = requestAnimationFrame(() => rafTickRef.current!(0)); return }

      const t = currentTimeRef.current
      const clips = clipsRef.current
      const clip = clips.find(c => c.tipo === "video" && c.url && t >= c.startTime && t < c.startTime + c.duracion) ?? null

      if (clip) {
        const clipEndSrc = clip.srcOffset + clip.duracion
        if (v.currentTime >= clipEndSrc - 0.04) {
          // Hard cut al siguiente clip
          const nextT = clip.startTime + clip.duracion
          currentTimeRef.current = nextT; setCurrentTime(nextT)
          if (nextT >= totalDuration) { v.pause(); setPlaying(false); rafRef.current = null; return }
          const nextClip = clips.find(c => c.tipo === "video" && c.url && nextT >= c.startTime && nextT < c.startTime + c.duracion)
          if (nextClip) {
            activeClipIdRef.current = nextClip.id
            v.pause()
            if (v.src !== nextClip.url) v.src = nextClip.url!
            v.currentTime = nextClip.srcOffset
            v.play().catch(() => {})
          }
        } else if (activeClipIdRef.current !== clip.id) {
          // Cambio de clip por seek externo
          activeClipIdRef.current = clip.id
          v.pause()
          if (v.src !== clip.url) v.src = clip.url!
          v.currentTime = clip.srcOffset + (t - clip.startTime)
          v.play().catch(() => {})
        } else {
          // Derivo tiempo del timeline desde el video
          const derived = clip.startTime + (v.currentTime - clip.srcOffset)
          currentTimeRef.current = derived; setCurrentTime(derived)
        }
      }
      rafRef.current = requestAnimationFrame(() => rafTickRef.current!(0))
    }

    const play = useCallback(async () => {
      const v = videoRef.current; if (!v) return
      const t = currentTimeRef.current
      const clip = clipsRef.current.find(c => c.tipo === "video" && c.url && t >= c.startTime && t < c.startTime + c.duracion)
      if (clip) {
        if (v.src !== clip.url) v.src = clip.url!
        v.currentTime = clip.srcOffset + (t - clip.startTime)
        activeClipIdRef.current = clip.id
      }
      setPlaying(true)
      try { await v.play() } catch {}
      rafRef.current = requestAnimationFrame(() => rafTickRef.current!(0))
    }, [])

    const pause = useCallback(() => {
      if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
      videoRef.current?.pause(); setPlaying(false)
    }, [])

    const seek = useCallback((t: number) => {
      const clamped = Math.max(0, Math.min(t, totalDuration))
      currentTimeRef.current = clamped; setCurrentTime(clamped)
      syncVideoToTime(clamped)
    }, [totalDuration, syncVideoToTime])

    const splitAt = useCallback((t?: number) => {
      const splitTime = t ?? currentTimeRef.current
      const clip = clipsRef.current.find(c => c.id === selected) ??
        clipsRef.current.find(c => splitTime > c.startTime && splitTime < c.startTime + c.duracion)
      if (!clip) return
      const durA = splitTime - clip.startTime
      if (durA < 0.1 || durA > clip.duracion - 0.1) return
      const durB = clip.duracion - durA
      const clipA: ClipInfo = { ...clip, id: uid(), duracion: durA }
      const clipB: ClipInfo = {
        ...clip, id: uid(), duracion: durB,
        startTime: clip.startTime + durA, srcOffset: clip.srcOffset + durA
      }
      setClips(prev => prev.filter(c => c.id !== clip.id).concat(clipA, clipB))
      setSelected(clipA.id)
    }, [selected])

    const deleteClip = useCallback((id?: string) => {
      const targetId = id ?? selected
      if (!targetId) return
      setClips(prev => prev.filter(c => c.id !== targetId))
      setSelected(null)
    }, [selected])

    const addClip = useCallback(async (url: string, name: string) => {
      const lastEnd = clipsRef.current.reduce((max, c) => Math.max(max, c.startTime + c.duracion), 0)
      const newClip: ClipInfo = {
        id: uid(), nombre: name, duracion: 0, tipo: "video",
        url, trackIndex: 0, startTime: lastEnd, srcOffset: 0
      }
      setClips(prev => [...prev, newClip])
      onClipAdd?.(newClip)
    }, [onClipAdd])

    // ── Exponer API via ref para la IA ─────────────────────────────────────────
    useImperativeHandle(ref, () => ({
      play, pause, seek, splitAt, deleteClip, addClip,
      getState: () => ({
        clips: clipsRef.current,
        currentTime: currentTimeRef.current,
        duration: totalDuration
      })
    }), [play, pause, seek, splitAt, deleteClip, addClip, totalDuration])

    // ── Notificar cambios de estado ────────────────────────────────────────────
    useEffect(() => {
      onStateChange?.({ clips, currentTime, duration: totalDuration })
    }, [clips, currentTime, totalDuration, onStateChange])

    // ── Drop de video en el área ───────────────────────────────────────────────
    const handleDrop = useCallback(async (e: React.DragEvent) => {
      e.preventDefault()
      const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("video/"))
      for (const file of files) {
        const url = URL.createObjectURL(file)
        await addClip(url, file.name)
      }
    }, [addClip])

    // ── Scrubbing en la timeline ───────────────────────────────────────────────
    const scrubToX = useCallback((clientX: number) => {
      const rect = timelineRef.current?.getBoundingClientRect(); if (!rect) return
      const t = Math.max(0, Math.min((clientX - rect.left - LABEL_W) / PX_PER_SEC, totalDuration))
      currentTimeRef.current = t; setCurrentTime(t)
      if (!playing) syncVideoToTime(t)
    }, [totalDuration, playing, syncVideoToTime])

    const handleRulerDown = (e: React.MouseEvent) => {
      scrubbingRef.current = true; scrubToX(e.clientX)
    }
    const handleMouseMove = (e: React.MouseEvent) => {
      if (scrubbingRef.current) scrubToX(e.clientX)
    }
    const handleMouseUp = () => { scrubbingRef.current = false }

    // ── Auto-scroll chat ──────────────────────────────────────────────────────
    useEffect(() => {
      if (chatEndRef.current?.scrollIntoView) {
        chatEndRef.current.scrollIntoView({ behavior: "smooth" })
      }
    }, [chatMessages, aiTyping])

    // ── Ejecuta comandos que devuelve la IA ───────────────────────────────────
    const executeAICommands = useCallback((commands: Array<{ action: string; [k: string]: unknown }>) => {
      commands.forEach(cmd => {
        switch (cmd.action) {
          case "split":    splitAt(typeof cmd.time === "number" ? cmd.time : undefined); break
          case "delete":   deleteClip(typeof cmd.clipId === "string" ? cmd.clipId : undefined); break
          case "seek":     if (typeof cmd.time === "number") seek(cmd.time); break
          case "play":     play(); break
          case "pause":    pause(); break
          case "addClip":  if (typeof cmd.url === "string") addClip(cmd.url, (cmd.name as string) ?? "clip"); break
        }
      })
    }, [splitAt, deleteClip, seek, play, pause, addClip])

    // ── Envía mensaje al backend y ejecuta respuesta ──────────────────────────
    const handleChatSend = useCallback(async (e: React.FormEvent) => {
      e.preventDefault()
      const text = chatInput.trim(); if (!text) return
      setChatInput("")

      const userMsg = { id: uid(), role: "user" as const, content: text }
      if (onChatSend) {
        onChatSend(text)
      } else {
        setLocalMsgs(prev => [...prev, userMsg])
      }

      setAiTyping(true)
      try {
        const state = { clips: clipsRef.current, currentTime: currentTimeRef.current, duration: totalDuration }
        const res = await fetch("http://localhost:8000/api/v1/video/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, editor_state: state, node_id: nodeId ?? "default" })
        })
        const data = await res.json()
        const assistantMsg = { id: uid(), role: "assistant" as const, content: data.respuesta ?? data.message ?? "✓" }
        if (!onChatSend) setLocalMsgs(prev => [...prev, assistantMsg])
        if (Array.isArray(data.commands)) executeAICommands(data.commands)
      } catch {
        if (!onChatSend) setLocalMsgs(prev => [...prev, { id: uid(), role: "assistant", content: "Error al conectar con la IA." }])
      } finally {
        setAiTyping(false)
      }
    }, [chatInput, onChatSend, totalDuration, nodeId, executeAICommands])

    const timelineWidth = Math.max(totalDuration * PX_PER_SEC + 120, 600)
    const playheadX = LABEL_W + currentTime * PX_PER_SEC

    return (
      <div
        data-testid="video-node-layout"
        style={{ display: "flex", flexDirection: "row", height: "100%", minHeight: 520,
          background: "#111827", color: "#f3f4f6", fontFamily: "sans-serif", userSelect: "none" }}
        onDrop={handleDrop} onDragOver={e => e.preventDefault()}
      >
        {/* ── Editor principal ─────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* ── Preview ──────────────────────────────────────────────────────── */}
        <div style={{ flex: "0 0 auto", background: "#000", display: "flex",
          justifyContent: "center", alignItems: "center", height: 220, position: "relative" }}>
          <video
            ref={videoRef}
            style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
            playsInline muted={false}
          />
          {clips.length === 0 && (
            <div style={{ position: "absolute", color: "#6b7280", textAlign: "center", pointerEvents: "none" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎬</div>
              <div style={{ fontSize: 13 }}>Arrastra un video aquí</div>
            </div>
          )}
        </div>

        {/* ── Controles ────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 12px",
          background: "#1f2937", borderBottom: "1px solid #374151" }}>
          <button
            onClick={() => playing ? pause() : play()}
            style={{ background: "#2563eb", border: "none", borderRadius: 6, color: "#fff",
              padding: "4px 14px", cursor: "pointer", fontSize: 16 }}
          >{playing ? "⏸" : "▶"}</button>
          <button
            onClick={() => { pause(); currentTimeRef.current = 0; setCurrentTime(0); syncVideoToTime(0) }}
            style={{ background: "#374151", border: "none", borderRadius: 6, color: "#9ca3af",
              padding: "4px 10px", cursor: "pointer" }}>⏹</button>
          <span style={{ fontSize: 12, color: "#9ca3af", minWidth: 90, textAlign: "center" }}>
            {fmt(currentTime)} / {fmt(totalDuration)}
          </span>
          <div style={{ flex: 1 }} />
          <button
            disabled={!selected}
            onClick={() => splitAt()}
            style={{ background: selected ? "#7c3aed" : "#374151", border: "none", borderRadius: 6,
              color: selected ? "#fff" : "#6b7280", padding: "4px 12px", cursor: selected ? "pointer" : "default", fontSize: 12 }}>
            ✂ Cortar
          </button>
          <button
            disabled={!selected}
            onClick={() => deleteClip()}
            style={{ background: selected ? "#dc2626" : "#374151", border: "none", borderRadius: 6,
              color: selected ? "#fff" : "#6b7280", padding: "4px 12px", cursor: selected ? "pointer" : "default", fontSize: 12 }}>
            🗑 Eliminar
          </button>
        </div>

        {/* ── Timeline ─────────────────────────────────────────────────────── */}
        <div
          ref={timelineRef}
          data-testid="timeline"
          style={{ flex: 1, overflowX: "auto", overflowY: "hidden", position: "relative" }}
          onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
        >
          <div style={{ width: timelineWidth, position: "relative" }}>
            {/* Ruler */}
            <div
              style={{ height: RULER_H, display: "flex", alignItems: "flex-end",
                background: "#1f2937", cursor: "col-resize", position: "sticky", top: 0, zIndex: 2 }}
              onMouseDown={handleRulerDown}
            >
              <div style={{ width: LABEL_W, flexShrink: 0 }} />
              {Array.from({ length: Math.ceil(totalDuration) + 1 }).map((_, i) => (
                <div key={i} style={{ position: "absolute", left: LABEL_W + i * PX_PER_SEC,
                  height: "100%", borderLeft: "1px solid #374151", paddingLeft: 3,
                  fontSize: 10, color: "#6b7280", display: "flex", alignItems: "flex-end", paddingBottom: 3 }}>
                  {i}s
                </div>
              ))}
            </div>

            {/* Tracks */}
            {TRACKS.map(track => (
              <div key={track.id} style={{ display: "flex", height: TRACK_H, borderBottom: "1px solid #1f2937" }}>
                <div style={{ width: LABEL_W, flexShrink: 0, display: "flex", alignItems: "center",
                  justifyContent: "center", fontSize: 11, color: "#6b7280", background: "#1f2937",
                  borderRight: "1px solid #374151" }}>{track.label}</div>
                <div style={{ flex: 1, position: "relative", background: "#111827" }}>
                  {clips.filter(c => c.trackIndex === track.idx).map(clip => {
                    const frames = thumbs[clip.id] ?? []
                    const isSelected = selected === clip.id
                    return (
                      <div
                        key={clip.id}
                        onClick={e => { e.stopPropagation(); setSelected(clip.id) }}
                        style={{
                          position: "absolute",
                          left: clip.startTime * PX_PER_SEC,
                          width: Math.max(clip.duracion * PX_PER_SEC, 4),
                          height: "100%",
                          background: track.color,
                          borderRadius: 4,
                          border: isSelected ? "2px solid #fff" : "2px solid transparent",
                          overflow: "hidden",
                          cursor: "pointer",
                          display: "flex",
                          boxSizing: "border-box",
                        }}
                      >
                        {/* Thumbnails */}
                        {frames.map((f, i) => (
                          <img key={i} src={f} alt=""
                            style={{ height: "100%", width: 80, objectFit: "cover", flexShrink: 0, opacity: 0.85 }} />
                        ))}
                        {/* Nombre del clip */}
                        <span style={{ position: "absolute", bottom: 2, left: 4, fontSize: 10,
                          color: "#fff", opacity: 0.9, whiteSpace: "nowrap", overflow: "hidden",
                          textOverflow: "ellipsis", maxWidth: "90%", textShadow: "0 1px 2px #000" }}>
                          {clip.nombre}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}

            {/* Playhead */}
            <div style={{ position: "absolute", top: 0, left: playheadX,
              width: 2, height: "100%", background: "#ef4444", pointerEvents: "none", zIndex: 3 }}>
              <div style={{ width: 10, height: 10, background: "#ef4444", borderRadius: "50%",
                marginLeft: -4, marginTop: -1 }} />
            </div>
          </div>
        </div>

        {/* ── Assets (drop zone) ───────────────────────────────────────────── */}
        <div data-testid="assets-panel"
          style={{ height: 60, background: "#1f2937", borderTop: "1px solid #374151",
            display: "flex", alignItems: "center", padding: "0 12px", gap: 8 }}>
          <span style={{ fontSize: 12, color: "#6b7280" }}>Assets:</span>
          {clips.filter((c, i, arr) => arr.findIndex(x => x.url === c.url) === i).map(c => (
            <div key={c.id} style={{ fontSize: 11, background: "#374151", borderRadius: 4,
              padding: "2px 8px", color: "#d1d5db", cursor: "pointer", whiteSpace: "nowrap",
              maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis" }}
              title={c.nombre}>{c.nombre}</div>
          ))}
          {clips.length === 0 && (
            <span style={{ fontSize: 11, color: "#4b5563" }}>Arrastra videos para agregar</span>
          )}
        </div>
        </div>{/* fin editor principal */}

        {/* ── Chat IA ──────────────────────────────────────────────────────── */}
        <aside data-testid="chat-panel"
          style={{ width: 280, flexShrink: 0, borderLeft: "1px solid #1f2937",
            display: "flex", flexDirection: "column", background: "#0f172a" }}>
          {/* Header */}
          <div style={{ padding: "8px 12px", borderBottom: "1px solid #1f2937",
            fontSize: 12, color: "#60a5fa", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            🤖 IA Video Editor
            <span style={{ marginLeft: "auto", fontSize: 10, color: "#374151" }}>
              {nodeId ? `#${nodeId.slice(0,6)}` : ""}
            </span>
          </div>

          {/* Mensajes */}
          <div style={{ flex: 1, overflowY: "auto", padding: "8px", display: "flex", flexDirection: "column", gap: 6 }}>
            {chatMessages.length === 0 && (
              <div style={{ color: "#4b5563", fontSize: 11, textAlign: "center", marginTop: 16, lineHeight: 1.6 }}>
                Dile a la IA qué hacer:<br />
                <span style={{ color: "#374151" }}>
                  "corta en el segundo 5"<br />
                  "elimina el último clip"<br />
                  "reproduce desde el inicio"
                </span>
              </div>
            )}
            {chatMessages.map(msg => (
              <div key={msg.id} style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "90%",
                background: msg.role === "user" ? "#1d4ed8" : "#1f2937",
                borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                padding: "6px 10px", fontSize: 12, color: "#f3f4f6", lineHeight: 1.4,
              }}>{msg.content}</div>
            ))}
            {aiTyping && (
              <div style={{ alignSelf: "flex-start", background: "#1f2937", borderRadius: "12px 12px 12px 2px",
                padding: "6px 10px", fontSize: 12, color: "#9ca3af" }}>
                <span style={{ animation: "pulse 1s infinite" }}>⏳ Pensando...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleChatSend}
            style={{ padding: "8px", borderTop: "1px solid #1f2937", display: "flex", gap: 6 }}>
            <input
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              placeholder="Ej: corta en el segundo 5..."
              disabled={aiTyping}
              style={{ flex: 1, background: "#1f2937", border: "1px solid #374151", borderRadius: 6,
                color: "#f3f4f6", padding: "5px 8px", fontSize: 11, outline: "none" }}
            />
            <button type="submit" disabled={aiTyping || !chatInput.trim()}
              style={{ background: "#2563eb", border: "none", borderRadius: 6, color: "#fff",
                padding: "5px 10px", cursor: "pointer", fontSize: 13, flexShrink: 0 }}>
              ➤
            </button>
          </form>
        </aside>
      </div>
    )
  }
)

export { VideoNodeLayout }
export default VideoNodeLayout
