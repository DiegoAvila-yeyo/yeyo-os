/**
 * YeyoOS — VideoNodeLayout v4 "CapCut Pro"
 * Editor de video estilo CapCut con 5 tracks (V1, V2, T, A1, A2),
 * panel lateral con pestañas (Efectos, Texto, IA), undo/redo, y exportación.
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
  duracion: number
  tipo: "video" | "audio" | "imagen" | "subtitle"
  url?: string
  trackIndex: number       // 0=V1, 1=V2, 2=T, 3=A1, 4=A2
  startTime: number
  srcOffset: number
  thumbnails?: string[]
  filter?: string
  speed?: number
  transition?: string
  transitionDuration?: number
  text?: string
  textStyle?: {
    position: string
    fontSize: number
    color: string
  }
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
const MAX_HISTORY = 50
const SIDE_W = 300

const TRACKS = [
  { id: "v1", label: "V1", color: "#1A56C4", idx: 0 },
  { id: "v2", label: "V2", color: "#1e40af", idx: 1 },
  { id: "t",  label: "T",  color: "#C2185B", idx: 2 },
  { id: "a1", label: "A1", color: "#166534", idx: 3 },
  { id: "a2", label: "A2", color: "#065f46", idx: 4 },
]

const FILTERS = [
  { id: "sepia",     label: "Sepia",      swatch: "linear-gradient(135deg, #704214, #c4a35a)" },
  { id: "bw",        label: "B&W",        swatch: "linear-gradient(135deg, #222, #999)" },
  { id: "vintage",   label: "Vintage",    swatch: "linear-gradient(135deg, #8b6914, #e8d5b7)" },
  { id: "cinematic", label: "Cinemático", swatch: "linear-gradient(135deg, #0a1628, #1a365d)" },
]

const TRANSITIONS = [
  { id: "fade",     label: "Fade",     icon: "◐" },
  { id: "dissolve", label: "Dissolve", icon: "◑" },
  { id: "wipe",     label: "Wipe",     icon: "◧" },
  { id: "zoom",     label: "Zoom",     icon: "⊕" },
  { id: "slide",    label: "Slide",    icon: "◫" },
]

const SPEEDS = [0.5, 1, 2, 4]

const TEXT_POSITIONS = [
  "top-left", "top-center", "top-right",
  "center",
  "bottom-left", "bottom-center", "bottom-right",
]

const TEXT_COLORS = [
  { id: "white",  hex: "#ffffff" },
  { id: "black",  hex: "#000000" },
  { id: "yellow", hex: "#facc15" },
  { id: "red",    hex: "#ef4444" },
  { id: "blue",   hex: "#3b82f6" },
  { id: "green",  hex: "#22c55e" },
]

const TITLE_TEMPLATES = [
  { id: "intro",       label: "Intro",       text: "TÍTULO DEL VIDEO",  position: "center",        fontSize: 36, color: "#ffffff" },
  { id: "outro",       label: "Outro",       text: "Gracias por ver",   position: "center",        fontSize: 28, color: "#facc15" },
  { id: "lower-third", label: "Lower Third", text: "Nombre · Título",   position: "bottom-left",   fontSize: 18, color: "#ffffff" },
]

type SideTab = "effects" | "text" | "ai"

function fmt(s: number) {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  const cs = Math.floor((s % 1) * 10)
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}.${cs}`
}

// ─── Estilos reutilizables ────────────────────────────────────────────────────

const btnBase: React.CSSProperties = {
  border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12,
  padding: "5px 12px", transition: "background 0.15s",
}

const btnPrimary: React.CSSProperties = {
  ...btnBase, background: "#2563eb", color: "#fff",
}

const btnGhost: React.CSSProperties = {
  ...btnBase, background: "#374151", color: "#9ca3af",
}

const btnDanger: React.CSSProperties = {
  ...btnBase, background: "#dc2626", color: "#fff",
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

// ─── Modal de Exportación ─────────────────────────────────────────────────────

interface ExportModalProps {
  clips: ClipInfo[]
  onClose: () => void
}

function ExportModal({ clips, onClose }: ExportModalProps) {
  const [resolution, setResolution] = useState<"720p" | "1080p">("1080p")
  const [fps, setFps] = useState<24 | 30 | 60>(30)
  const [includeSubs, setIncludeSubs] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleExport = async () => {
    setExporting(true); setProgress(0); setError(null); setDownloadUrl(null)
    const interval = setInterval(() => setProgress(p => Math.min(p + 8, 90)), 500)
    try {
      const subtitles = includeSubs ? clips.filter(c => c.tipo === "subtitle") : []
      const res = await fetch("http://localhost:8000/api/v1/video/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clips: clips.filter(c => c.tipo !== "subtitle"),
          subtitles,
          resolution,
          fps,
          include_subtitles: includeSubs,
        }),
      })
      clearInterval(interval)
      if (!res.ok) throw new Error(`Error ${res.status}`)
      const data = await res.json()
      setProgress(100)
      setDownloadUrl(data.download_url ?? data.url ?? null)
    } catch (err: unknown) {
      clearInterval(interval)
      setError(err instanceof Error ? err.message : "Error al exportar")
    } finally {
      setExporting(false)
    }
  }

  const radioStyle = (active: boolean): React.CSSProperties => ({
    ...btnBase,
    background: active ? "#2563eb" : "#1f2937",
    color: active ? "#fff" : "#9ca3af",
    border: active ? "1px solid #3b82f6" : "1px solid #374151",
  })

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 9999,
      background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: "#1e293b", borderRadius: 12, padding: 24, width: 360,
        color: "#f3f4f6", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <span style={{ fontSize: 16, fontWeight: 600 }}>📤 Exportar Video</span>
          <button onClick={onClose} style={{ ...btnGhost, fontSize: 16, padding: "2px 8px" }}>✕</button>
        </div>

        {/* Resolución */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 6 }}>Resolución</div>
          <div style={{ display: "flex", gap: 6 }}>
            {(["720p", "1080p"] as const).map(r => (
              <button key={r} onClick={() => setResolution(r)} style={radioStyle(resolution === r)}>{r}</button>
            ))}
          </div>
        </div>

        {/* FPS */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 6 }}>FPS</div>
          <div style={{ display: "flex", gap: 6 }}>
            {([24, 30, 60] as const).map(f => (
              <button key={f} onClick={() => setFps(f)} style={radioStyle(fps === f)}>{f}</button>
            ))}
          </div>
        </div>

        {/* Subtítulos */}
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, fontSize: 12, cursor: "pointer" }}>
          <input type="checkbox" checked={includeSubs} onChange={e => setIncludeSubs(e.target.checked)}
            style={{ accentColor: "#2563eb" }} />
          Incluir subtítulos
        </label>

        {/* Progreso */}
        {(exporting || progress > 0) && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ height: 6, background: "#374151", borderRadius: 3, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "#2563eb", borderRadius: 3,
                transition: "width 0.3s" }} />
            </div>
            <div style={{ fontSize: 10, color: "#9ca3af", marginTop: 4, textAlign: "center" }}>{progress}%</div>
          </div>
        )}

        {error && <div style={{ fontSize: 11, color: "#ef4444", marginBottom: 8 }}>{error}</div>}

        {downloadUrl && (
          <a href={downloadUrl} target="_blank" rel="noopener noreferrer"
            style={{ display: "block", textAlign: "center", ...btnPrimary, padding: "8px 16px",
              textDecoration: "none", marginBottom: 8 }}>
            ⬇ Descargar Video
          </a>
        )}

        {!downloadUrl && (
          <button onClick={handleExport} disabled={exporting}
            style={{ ...btnPrimary, width: "100%", padding: "8px 16px", opacity: exporting ? 0.6 : 1 }}>
            {exporting ? "Exportando…" : "Exportar"}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Componente principal ─────────────────────────────────────────────────────

const VideoNodeLayout = forwardRef<VideoEditorAPI, VideoNodeLayoutProps>(
  function VideoNodeLayout({ onClipAdd, onStateChange, nodeId, chatMessages: externalMsgs, onChatSend }, ref) {

    // ── Core state ──────────────────────────────────────────────────────────
    const [clips, setClips] = useState<ClipInfo[]>([])
    const [currentTime, setCurrentTime] = useState(0)
    const [playing, setPlaying] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)
    const [thumbs, setThumbs] = useState<Record<string, string[]>>({})

    // ── Undo / Redo ─────────────────────────────────────────────────────────
    const [history, setHistory] = useState<ClipInfo[][]>([])
    const [historyIdx, setHistoryIdx] = useState(-1)

    const pushHistory = useCallback((newClips: ClipInfo[]) => {
      setHistory(prev => {
        const trimmed = prev.slice(0, historyIdx + 1)
        const next = [...trimmed, newClips].slice(-MAX_HISTORY)
        return next
      })
      setHistoryIdx(prev => Math.min(prev + 1, MAX_HISTORY - 1))
    }, [historyIdx])

    const setClipsWithHistory = useCallback((updater: ClipInfo[] | ((prev: ClipInfo[]) => ClipInfo[])) => {
      setClips(prev => {
        const next = typeof updater === "function" ? updater(prev) : updater
        pushHistory(next)
        return next
      })
    }, [pushHistory])

    const undo = useCallback(() => {
      if (historyIdx <= 0) return
      const newIdx = historyIdx - 1
      setHistoryIdx(newIdx)
      setClips(history[newIdx])
    }, [history, historyIdx])

    const redo = useCallback(() => {
      if (historyIdx >= history.length - 1) return
      const newIdx = historyIdx + 1
      setHistoryIdx(newIdx)
      setClips(history[newIdx])
    }, [history, historyIdx])

    // ── Side panel ──────────────────────────────────────────────────────────
    const [sideTab, setSideTab] = useState<SideTab>("effects")
    const [showExport, setShowExport] = useState(false)

    // ── Text panel state ────────────────────────────────────────────────────
    const [customText, setCustomText] = useState("")
    const [textPos, setTextPos] = useState("bottom-center")
    const [textSize, setTextSize] = useState(20)
    const [textColor, setTextColor] = useState("#ffffff")
    const [textDuration, setTextDuration] = useState(3)
    const [subtitlesLoading, setSubtitlesLoading] = useState(false)

    // ── Chat state ──────────────────────────────────────────────────────────
    const [localMsgs, setLocalMsgs] = useState<Array<{ id: string; role: "user" | "assistant"; content: string }>>([])
    const [chatInput, setChatInput] = useState("")
    const [aiTyping, setAiTyping] = useState(false)
    const chatEndRef = useRef<HTMLDivElement>(null)
    const chatMessages = externalMsgs ?? localMsgs

    // ── Editing subtitle inline ─────────────────────────────────────────────
    const [editingSubId, setEditingSubId] = useState<string | null>(null)
    const [editingSubText, setEditingSubText] = useState("")

    // ── Refs ────────────────────────────────────────────────────────────────
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

    // ── Keyboard shortcuts ──────────────────────────────────────────────────
    useEffect(() => {
      const handler = (e: KeyboardEvent) => {
        if ((e.target as HTMLElement).tagName === "INPUT" || (e.target as HTMLElement).tagName === "TEXTAREA") return
        if (e.key === "z" && (e.metaKey || e.ctrlKey) && e.shiftKey) { e.preventDefault(); redo() }
        else if (e.key === "z" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); undo() }
      }
      window.addEventListener("keydown", handler)
      return () => window.removeEventListener("keydown", handler)
    }, [undo, redo])

    // ── Thumbnails ──────────────────────────────────────────────────────────
    useEffect(() => {
      clips.forEach(c => {
        if (c.url && !thumbs[c.id] && c.duracion > 0 && c.tipo === "video") {
          extractFrames(c.url, Math.max(4, Math.ceil(c.duracion)), c.srcOffset)
            .then(frames => setThumbs(prev => ({ ...prev, [c.id]: frames })))
        }
      })
    }, [clips, thumbs])

    // ── Carga metadata de nuevos clips ──────────────────────────────────────
    useEffect(() => {
      clips.filter(c => c.url && c.duracion === 0 && c.tipo !== "subtitle").forEach(c => {
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

    // ── Sync video al tiempo t ──────────────────────────────────────────────
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

    // ── RAF tick ────────────────────────────────────────────────────────────
    rafTickRef.current = () => {
      const v = videoRef.current
      if (!v) { rafRef.current = requestAnimationFrame(() => rafTickRef.current!(0)); return }

      const t = currentTimeRef.current
      const allClips = clipsRef.current
      const clip = allClips.find(c => c.tipo === "video" && c.url && t >= c.startTime && t < c.startTime + c.duracion) ?? null

      if (clip) {
        const speed = clip.speed ?? 1
        if (v.playbackRate !== speed) v.playbackRate = speed
        const clipEndSrc = clip.srcOffset + clip.duracion
        if (v.currentTime >= clipEndSrc - 0.04) {
          const nextT = clip.startTime + clip.duracion
          currentTimeRef.current = nextT; setCurrentTime(nextT)
          if (nextT >= totalDuration) { v.pause(); setPlaying(false); rafRef.current = null; return }
          const nextClip = allClips.find(c => c.tipo === "video" && c.url && nextT >= c.startTime && nextT < c.startTime + c.duracion)
          if (nextClip) {
            activeClipIdRef.current = nextClip.id
            v.pause()
            if (v.src !== nextClip.url) v.src = nextClip.url!
            v.currentTime = nextClip.srcOffset
            v.playbackRate = nextClip.speed ?? 1
            v.play().catch(() => {})
          }
        } else if (activeClipIdRef.current !== clip.id) {
          activeClipIdRef.current = clip.id
          v.pause()
          if (v.src !== clip.url) v.src = clip.url!
          v.currentTime = clip.srcOffset + (t - clip.startTime)
          v.playbackRate = speed
          v.play().catch(() => {})
        } else {
          const derived = clip.startTime + (v.currentTime - clip.srcOffset)
          currentTimeRef.current = derived; setCurrentTime(derived)
        }
      }
      rafRef.current = requestAnimationFrame(() => rafTickRef.current!(0))
    }

    // ── Playback controls ───────────────────────────────────────────────────
    const play = useCallback(async () => {
      const v = videoRef.current; if (!v) return
      const t = currentTimeRef.current
      const clip = clipsRef.current.find(c => c.tipo === "video" && c.url && t >= c.startTime && t < c.startTime + c.duracion)
      if (clip) {
        if (v.src !== clip.url) v.src = clip.url!
        v.currentTime = clip.srcOffset + (t - clip.startTime)
        v.playbackRate = clip.speed ?? 1
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
        startTime: clip.startTime + durA, srcOffset: clip.srcOffset + durA,
      }
      setClipsWithHistory(prev => prev.filter(c => c.id !== clip.id).concat(clipA, clipB))
      setSelected(clipA.id)
    }, [selected, setClipsWithHistory])

    const deleteClip = useCallback((id?: string) => {
      const targetId = id ?? selected
      if (!targetId) return
      setClipsWithHistory(prev => prev.filter(c => c.id !== targetId))
      setSelected(null)
    }, [selected, setClipsWithHistory])

    const addClip = useCallback(async (url: string, name: string) => {
      const lastEnd = clipsRef.current.filter(c => c.trackIndex === 0).reduce((max, c) => Math.max(max, c.startTime + c.duracion), 0)
      const newClip: ClipInfo = {
        id: uid(), nombre: name, duracion: 0, tipo: "video",
        url, trackIndex: 0, startTime: lastEnd, srcOffset: 0, speed: 1,
      }
      setClipsWithHistory(prev => [...prev, newClip])
      onClipAdd?.(newClip)
    }, [onClipAdd, setClipsWithHistory])

    // ── Exponer API via ref ─────────────────────────────────────────────────
    useImperativeHandle(ref, () => ({
      play, pause, seek, splitAt, deleteClip, addClip,
      getState: () => ({
        clips: clipsRef.current,
        currentTime: currentTimeRef.current,
        duration: totalDuration,
      }),
    }), [play, pause, seek, splitAt, deleteClip, addClip, totalDuration])

    // ── Notificar cambios ───────────────────────────────────────────────────
    useEffect(() => {
      onStateChange?.({ clips, currentTime, duration: totalDuration })
    }, [clips, currentTime, totalDuration, onStateChange])

    // ── Drop ────────────────────────────────────────────────────────────────
    const handleDrop = useCallback(async (e: React.DragEvent) => {
      e.preventDefault()
      const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("video/") || f.type.startsWith("audio/"))
      for (const file of files) {
        const url = URL.createObjectURL(file)
        await addClip(url, file.name)
      }
    }, [addClip])

    // ── Scrubbing ───────────────────────────────────────────────────────────
    const scrubToX = useCallback((clientX: number) => {
      const rect = timelineRef.current?.getBoundingClientRect(); if (!rect) return
      const t = Math.max(0, Math.min((clientX - rect.left - LABEL_W) / PX_PER_SEC, totalDuration))
      currentTimeRef.current = t; setCurrentTime(t)
      if (!playing) syncVideoToTime(t)
    }, [totalDuration, playing, syncVideoToTime])

    const handleRulerDown = (e: React.MouseEvent) => { scrubbingRef.current = true; scrubToX(e.clientX) }
    const handleMouseMove = (e: React.MouseEvent) => { if (scrubbingRef.current) scrubToX(e.clientX) }
    const handleMouseUp = () => { scrubbingRef.current = false }

    // ── Effects: apply filter ───────────────────────────────────────────────
    const applyFilter = useCallback((filterId: string) => {
      if (!selected) return
      setClipsWithHistory(prev => prev.map(c =>
        c.id === selected ? { ...c, filter: c.filter === filterId ? undefined : filterId } : c
      ))
      fetch("http://localhost:8000/api/v1/video/filter/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clip_id: selected, filter: filterId }),
      }).catch(() => {})
    }, [selected, setClipsWithHistory])

    // ── Effects: apply transition ───────────────────────────────────────────
    const applyTransition = useCallback((transId: string) => {
      if (!selected) return
      setClipsWithHistory(prev => prev.map(c =>
        c.id === selected ? { ...c, transition: c.transition === transId ? undefined : transId, transitionDuration: 0.5 } : c
      ))
      fetch("http://localhost:8000/api/v1/video/transition/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clip_id: selected, transition: transId, duration: 0.5 }),
      }).catch(() => {})
    }, [selected, setClipsWithHistory])

    // ── Effects: set speed ──────────────────────────────────────────────────
    const setSpeed = useCallback((speed: number) => {
      if (!selected) return
      setClipsWithHistory(prev => prev.map(c =>
        c.id === selected ? { ...c, speed } : c
      ))
    }, [selected, setClipsWithHistory])

    // ── Text: auto-subtitles ────────────────────────────────────────────────
    const generateSubtitles = useCallback(async () => {
      const videoClip = clipsRef.current.find(c => c.tipo === "video" && c.url)
      if (!videoClip?.url) return
      setSubtitlesLoading(true)
      try {
        const blob = await fetch(videoClip.url).then(r => r.blob())
        const form = new FormData()
        form.append("file", blob, videoClip.nombre || "video.mp4")
        const res = await fetch("http://localhost:8000/api/v1/video/subtitles/generate", {
          method: "POST", body: form,
        })
        const data = await res.json()
        const entries: Array<{ text: string; start: number; end: number }> = data.subtitles ?? data.entries ?? []
        if (entries.length > 0) {
          const newSubs: ClipInfo[] = entries.map(e => ({
            id: uid(), nombre: e.text.slice(0, 20), duracion: e.end - e.start,
            tipo: "subtitle" as const, trackIndex: 2, startTime: e.start, srcOffset: 0,
            text: e.text,
            textStyle: { position: "bottom-center", fontSize: 20, color: "#ffffff" },
          }))
          setClipsWithHistory(prev => [...prev.filter(c => c.trackIndex !== 2), ...newSubs])
        }
      } catch {
        // Silently fail — the user will notice no subtitles appeared
      } finally {
        setSubtitlesLoading(false)
      }
    }, [setClipsWithHistory])

    // ── Text: add custom text to Track T ────────────────────────────────────
    const addTextToTrack = useCallback((text: string, pos: string, size: number, color: string, dur: number) => {
      if (!text.trim()) return
      const lastEnd = clipsRef.current.filter(c => c.trackIndex === 2).reduce((max, c) => Math.max(max, c.startTime + c.duracion), currentTimeRef.current)
      const newClip: ClipInfo = {
        id: uid(), nombre: text.slice(0, 20), duracion: dur,
        tipo: "subtitle", trackIndex: 2, startTime: lastEnd, srcOffset: 0,
        text,
        textStyle: { position: pos, fontSize: size, color },
      }
      setClipsWithHistory(prev => [...prev, newClip])
    }, [setClipsWithHistory])

    // ── Subtitle inline edit ────────────────────────────────────────────────
    const commitSubtitleEdit = useCallback(() => {
      if (!editingSubId) return
      setClipsWithHistory(prev => prev.map(c =>
        c.id === editingSubId ? { ...c, text: editingSubText, nombre: editingSubText.slice(0, 20) } : c
      ))
      setEditingSubId(null)
    }, [editingSubId, editingSubText, setClipsWithHistory])

    // ── Auto-scroll chat ────────────────────────────────────────────────────
    useEffect(() => {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [chatMessages, aiTyping])

    // ── AI command execution ────────────────────────────────────────────────
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

    // ── Chat send ───────────────────────────────────────────────────────────
    const handleChatSend = useCallback(async (e: React.FormEvent) => {
      e.preventDefault()
      const text = chatInput.trim(); if (!text) return
      setChatInput("")

      const userMsg = { id: uid(), role: "user" as const, content: text }
      if (onChatSend) { onChatSend(text) } else { setLocalMsgs(prev => [...prev, userMsg]) }

      setAiTyping(true)
      try {
        const state = { clips: clipsRef.current, currentTime: currentTimeRef.current, duration: totalDuration }
        const res = await fetch("http://localhost:8000/api/v1/video/process", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text, editor_state: state, node_id: nodeId ?? "default" }),
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

    const sendChip = useCallback((text: string) => {
      setChatInput(text)
      setTimeout(() => {
        const form = document.querySelector<HTMLFormElement>("[data-testid='chat-form']")
        form?.requestSubmit()
      }, 50)
    }, [])

    // ── Computed ─────────────────────────────────────────────────────────────
    const timelineWidth = Math.max(totalDuration * PX_PER_SEC + 120, 600)
    const playheadX = LABEL_W + currentTime * PX_PER_SEC
    const selectedClip = clips.find(c => c.id === selected)
    const canUndo = historyIdx > 0
    const canRedo = historyIdx < history.length - 1

    // ─────────────────────────────────────────────────────────────────────────
    // RENDER
    // ─────────────────────────────────────────────────────────────────────────

    return (
      <div
        data-testid="video-node-layout"
        style={{
          display: "flex", flexDirection: "row", height: "100%", minHeight: 560,
          background: "#111827", color: "#f3f4f6", fontFamily: "sans-serif", userSelect: "none",
        }}
        onDrop={handleDrop} onDragOver={e => e.preventDefault()}
      >
        {/* ════════════════════════════════════════════════════════════════════
            EDITOR PRINCIPAL (left)
            ════════════════════════════════════════════════════════════════════ */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

          {/* ── Video Preview (16:9 area) ──────────────────────────────────── */}
          <div style={{
            flex: "1 1 0", background: "#000", display: "flex",
            justifyContent: "center", alignItems: "center", position: "relative",
            minHeight: 180, aspectRatio: "16/9", maxHeight: 340,
          }}>
            <video
              ref={videoRef}
              style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
              playsInline muted={false}
            />
            {/* Subtitle overlay */}
            {clips.filter(c => c.tipo === "subtitle" && currentTime >= c.startTime && currentTime < c.startTime + c.duracion).map(sub => {
              const pos = sub.textStyle?.position ?? "bottom-center"
              const posMap: Record<string, React.CSSProperties> = {
                "top-left":      { top: 12, left: 12 },
                "top-center":    { top: 12, left: "50%", transform: "translateX(-50%)" },
                "top-right":     { top: 12, right: 12 },
                "center":        { top: "50%", left: "50%", transform: "translate(-50%,-50%)" },
                "bottom-left":   { bottom: 12, left: 12 },
                "bottom-center": { bottom: 12, left: "50%", transform: "translateX(-50%)" },
                "bottom-right":  { bottom: 12, right: 12 },
              }
              return (
                <div key={sub.id} style={{
                  position: "absolute", ...posMap[pos],
                  color: sub.textStyle?.color ?? "#fff",
                  fontSize: sub.textStyle?.fontSize ?? 20,
                  fontWeight: 700, textShadow: "0 2px 8px rgba(0,0,0,0.8)",
                  pointerEvents: "none", maxWidth: "80%", textAlign: "center",
                }}>
                  {sub.text}
                </div>
              )
            })}
            {clips.length === 0 && (
              <div style={{ position: "absolute", color: "#6b7280", textAlign: "center", pointerEvents: "none" }}>
                <div style={{ fontSize: 40, marginBottom: 8 }}>🎬</div>
                <div style={{ fontSize: 13 }}>Arrastra un video aquí</div>
              </div>
            )}
          </div>

          {/* ── Transport Controls ─────────────────────────────────────────── */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6, padding: "6px 12px",
            background: "#1f2937", borderBottom: "1px solid #374151", flexWrap: "wrap",
          }}>
            <button onClick={() => playing ? pause() : play()}
              style={{ ...btnPrimary, padding: "4px 14px", fontSize: 16 }}>
              {playing ? "⏸" : "▶"}
            </button>
            <button onClick={() => { pause(); currentTimeRef.current = 0; setCurrentTime(0); syncVideoToTime(0) }}
              style={{ ...btnGhost, padding: "4px 10px" }}>⏹</button>
            <span style={{ fontSize: 12, color: "#9ca3af", minWidth: 100, textAlign: "center" }}>
              {fmt(currentTime)} / {fmt(totalDuration)}
            </span>

            <div style={{ width: 1, height: 20, background: "#374151", margin: "0 4px" }} />

            <button onClick={undo} disabled={!canUndo}
              style={{ ...btnGhost, opacity: canUndo ? 1 : 0.4 }} title="Deshacer (Ctrl+Z)">↩ Deshacer</button>
            <button onClick={redo} disabled={!canRedo}
              style={{ ...btnGhost, opacity: canRedo ? 1 : 0.4 }} title="Rehacer (Ctrl+Shift+Z)">↪ Rehacer</button>

            <div style={{ width: 1, height: 20, background: "#374151", margin: "0 4px" }} />

            <button disabled={!selected} onClick={() => splitAt()}
              style={{ ...(selected ? { ...btnBase, background: "#7c3aed", color: "#fff" } : btnGhost), opacity: selected ? 1 : 0.5 }}>
              ✂ Cortar
            </button>
            <button disabled={!selected} onClick={() => deleteClip()}
              style={{ ...(selected ? btnDanger : btnGhost), opacity: selected ? 1 : 0.5 }}>
              🗑 Eliminar
            </button>

            <div style={{ flex: 1 }} />
            <button onClick={() => setShowExport(true)}
              style={{ ...btnPrimary, background: "#059669" }}>
              📤 Exportar
            </button>
          </div>

          {/* ── Timeline ───────────────────────────────────────────────────── */}
          <div
            ref={timelineRef}
            data-testid="timeline"
            style={{ flex: "0 0 auto", height: TRACKS.length * TRACK_H + RULER_H + 4, overflowX: "auto", overflowY: "hidden", position: "relative" }}
            onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
          >
            <div style={{ width: timelineWidth, position: "relative" }}>
              {/* Ruler */}
              <div
                style={{
                  height: RULER_H, display: "flex", alignItems: "flex-end",
                  background: "#1f2937", cursor: "col-resize", position: "sticky", top: 0, zIndex: 2,
                }}
                onMouseDown={handleRulerDown}
              >
                <div style={{ width: LABEL_W, flexShrink: 0 }} />
                {Array.from({ length: Math.ceil(totalDuration) + 1 }).map((_, i) => (
                  <div key={i} style={{
                    position: "absolute", left: LABEL_W + i * PX_PER_SEC,
                    height: "100%", borderLeft: "1px solid #374151", paddingLeft: 3,
                    fontSize: 10, color: "#6b7280", display: "flex", alignItems: "flex-end", paddingBottom: 3,
                  }}>
                    {i}s
                  </div>
                ))}
              </div>

              {/* Tracks */}
              {TRACKS.map(track => (
                <div key={track.id} style={{ display: "flex", height: TRACK_H, borderBottom: "1px solid #1f2937" }}>
                  <div style={{
                    width: LABEL_W, flexShrink: 0, display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: 11, color: "#6b7280", background: "#1f2937",
                    borderRight: "1px solid #374151",
                  }}>{track.label}</div>
                  <div style={{ flex: 1, position: "relative", background: "#111827" }}>
                    {clips.filter(c => c.trackIndex === track.idx).map(clip => {
                      const frames = thumbs[clip.id] ?? []
                      const isSelected = selected === clip.id
                      const isSubtitle = clip.tipo === "subtitle"
                      const isEditing = editingSubId === clip.id

                      return (
                        <div
                          key={clip.id}
                          onClick={e => { e.stopPropagation(); setSelected(clip.id) }}
                          onDoubleClick={() => {
                            if (isSubtitle) { setEditingSubId(clip.id); setEditingSubText(clip.text ?? "") }
                          }}
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
                          {/* Video thumbnails */}
                          {!isSubtitle && frames.map((f, i) => (
                            <img key={i} src={f} alt=""
                              style={{ height: "100%", width: 80, objectFit: "cover", flexShrink: 0, opacity: 0.85 }} />
                          ))}

                          {/* Subtitle text display */}
                          {isSubtitle && !isEditing && (
                            <span style={{
                              display: "flex", alignItems: "center", padding: "0 6px",
                              fontSize: 10, color: "#fff", whiteSpace: "nowrap", overflow: "hidden",
                              textOverflow: "ellipsis", width: "100%",
                            }}>
                              {clip.text}
                            </span>
                          )}

                          {/* Subtitle inline editing */}
                          {isSubtitle && isEditing && (
                            <input
                              autoFocus
                              value={editingSubText}
                              onChange={e => setEditingSubText(e.target.value)}
                              onBlur={commitSubtitleEdit}
                              onKeyDown={e => { if (e.key === "Enter") commitSubtitleEdit() }}
                              style={{
                                width: "100%", height: "100%", background: "rgba(0,0,0,0.5)",
                                border: "none", color: "#fff", fontSize: 10, padding: "0 4px", outline: "none",
                              }}
                              onClick={e => e.stopPropagation()}
                            />
                          )}

                          {/* Clip name label (non-subtitle) */}
                          {!isSubtitle && (
                            <span style={{
                              position: "absolute", bottom: 2, left: 4, fontSize: 10,
                              color: "#fff", opacity: 0.9, whiteSpace: "nowrap", overflow: "hidden",
                              textOverflow: "ellipsis", maxWidth: "90%", textShadow: "0 1px 2px #000",
                            }}>
                              {clip.nombre}
                            </span>
                          )}

                          {/* Filter badge */}
                          {clip.filter && (
                            <span style={{
                              position: "absolute", top: 2, left: 4, fontSize: 8,
                              background: "rgba(0,0,0,0.6)", color: "#facc15", borderRadius: 3,
                              padding: "1px 4px",
                            }}>
                              {clip.filter}
                            </span>
                          )}

                          {/* Transition icon */}
                          {clip.transition && (
                            <span style={{
                              position: "absolute", top: 2, right: 4, fontSize: 10,
                              background: "rgba(0,0,0,0.6)", color: "#60a5fa", borderRadius: 3,
                              padding: "0 3px",
                            }} title={clip.transition}>
                              {TRANSITIONS.find(t => t.id === clip.transition)?.icon ?? "◐"}
                            </span>
                          )}

                          {/* Speed badge */}
                          {clip.speed && clip.speed !== 1 && (
                            <span style={{
                              position: "absolute", top: 2, right: clip.transition ? 24 : 4, fontSize: 8,
                              background: "rgba(0,0,0,0.6)", color: "#a78bfa", borderRadius: 3,
                              padding: "1px 4px",
                            }}>
                              {clip.speed}x
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}

              {/* Playhead */}
              <div style={{
                position: "absolute", top: 0, left: playheadX,
                width: 2, height: "100%", background: "#ef4444", pointerEvents: "none", zIndex: 3,
              }}>
                <div style={{
                  width: 10, height: 10, background: "#ef4444", borderRadius: "50%",
                  marginLeft: -4, marginTop: -1,
                }} />
              </div>
            </div>
          </div>

          {/* ── Assets Bar ─────────────────────────────────────────────────── */}
          <div data-testid="assets-panel" style={{
            height: 52, background: "#1f2937", borderTop: "1px solid #374151",
            display: "flex", alignItems: "center", padding: "0 12px", gap: 8,
          }}>
            <span style={{ fontSize: 12, color: "#6b7280", flexShrink: 0 }}>Assets:</span>
            <div style={{ display: "flex", gap: 6, overflowX: "auto", flex: 1 }}>
              {clips.filter((c, i, arr) => c.url && arr.findIndex(x => x.url === c.url) === i).map(c => (
                <div key={c.id} style={{
                  fontSize: 11, background: "#374151", borderRadius: 4,
                  padding: "2px 8px", color: "#d1d5db", cursor: "pointer", whiteSpace: "nowrap",
                  maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", flexShrink: 0,
                }} title={c.nombre}>{c.nombre}</div>
              ))}
              {clips.length === 0 && (
                <span style={{ fontSize: 11, color: "#4b5563" }}>Arrastra videos para agregar</span>
              )}
            </div>
          </div>
        </div>
        {/* fin editor principal */}

        {/* ════════════════════════════════════════════════════════════════════
            SIDE PANEL (right)
            ════════════════════════════════════════════════════════════════════ */}
        <aside data-testid="side-panel" style={{
          width: SIDE_W, flexShrink: 0, borderLeft: "1px solid #1f2937",
          display: "flex", flexDirection: "column", background: "#0f172a",
        }}>
          {/* Tab bar */}
          <div style={{
            display: "flex", borderBottom: "1px solid #1f2937",
          }}>
            {([
              { key: "effects" as SideTab, icon: "🎨", label: "Efectos" },
              { key: "text" as SideTab,    icon: "✏️", label: "Texto" },
              { key: "ai" as SideTab,      icon: "🤖", label: "IA" },
            ]).map(tab => (
              <button key={tab.key} onClick={() => setSideTab(tab.key)} style={{
                flex: 1, background: "transparent", border: "none",
                borderBottom: sideTab === tab.key ? "2px solid #2563eb" : "2px solid transparent",
                color: sideTab === tab.key ? "#f3f4f6" : "#6b7280",
                padding: "8px 0", cursor: "pointer", fontSize: 12, fontWeight: 600,
                transition: "all 0.15s",
              }}>
                <div style={{ fontSize: 16 }}>{tab.icon}</div>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>

            {/* ─── EFECTOS TAB ─────────────────────────────────────────────── */}
            {sideTab === "effects" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Filters */}
                <div>
                  <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8, fontWeight: 600 }}>Filtros Visuales</div>
                  {!selected && <div style={{ fontSize: 10, color: "#4b5563", marginBottom: 6 }}>Selecciona un clip primero</div>}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                    {FILTERS.map(f => (
                      <button key={f.id} onClick={() => applyFilter(f.id)} disabled={!selected}
                        style={{
                          ...btnBase, padding: 0, overflow: "hidden", height: 52, position: "relative",
                          opacity: selected ? 1 : 0.4,
                          border: selectedClip?.filter === f.id ? "2px solid #2563eb" : "2px solid #374151",
                          borderRadius: 8,
                        }}>
                        <div style={{ width: "100%", height: "100%", background: f.swatch }} />
                        <span style={{
                          position: "absolute", bottom: 2, left: 0, right: 0, textAlign: "center",
                          fontSize: 10, color: "#fff", textShadow: "0 1px 3px #000",
                        }}>{f.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Transitions */}
                <div>
                  <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8, fontWeight: 600 }}>Transiciones</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
                    {TRANSITIONS.map(t => (
                      <button key={t.id} onClick={() => applyTransition(t.id)} disabled={!selected}
                        style={{
                          ...btnBase, display: "flex", flexDirection: "column", alignItems: "center",
                          gap: 2, padding: "6px 4px", opacity: selected ? 1 : 0.4,
                          background: selectedClip?.transition === t.id ? "#1e3a5f" : "#1f2937",
                          border: selectedClip?.transition === t.id ? "1px solid #2563eb" : "1px solid #374151",
                          borderRadius: 8,
                        }}>
                        <span style={{ fontSize: 18 }}>{t.icon}</span>
                        <span style={{ fontSize: 9, color: "#d1d5db" }}>{t.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Speed */}
                <div>
                  <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8, fontWeight: 600 }}>Velocidad</div>
                  <div style={{ display: "flex", gap: 6 }}>
                    {SPEEDS.map(s => (
                      <button key={s} onClick={() => setSpeed(s)} disabled={!selected}
                        style={{
                          ...btnBase, flex: 1, textAlign: "center", opacity: selected ? 1 : 0.4,
                          background: (selectedClip?.speed ?? 1) === s ? "#2563eb" : "#1f2937",
                          color: (selectedClip?.speed ?? 1) === s ? "#fff" : "#9ca3af",
                          border: (selectedClip?.speed ?? 1) === s ? "1px solid #3b82f6" : "1px solid #374151",
                        }}>
                        {s}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ─── TEXTO TAB ───────────────────────────────────────────────── */}
            {sideTab === "text" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Auto-subtítulos */}
                <div>
                  <button onClick={generateSubtitles} disabled={subtitlesLoading}
                    style={{
                      ...btnPrimary, width: "100%", padding: "10px 16px", fontSize: 13,
                      opacity: subtitlesLoading ? 0.6 : 1,
                    }}>
                    {subtitlesLoading ? "⏳ Generando…" : "🎤 Auto-subtítulos"}
                  </button>
                  <div style={{ fontSize: 10, color: "#4b5563", marginTop: 4 }}>
                    Genera subtítulos del primer video con IA
                  </div>
                </div>

                {/* Texto personalizado */}
                <div>
                  <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8, fontWeight: 600 }}>Texto Personalizado</div>
                  <textarea
                    value={customText}
                    onChange={e => setCustomText(e.target.value)}
                    placeholder="Escribe tu texto aquí…"
                    rows={3}
                    style={{
                      width: "100%", background: "#1f2937", border: "1px solid #374151", borderRadius: 6,
                      color: "#f3f4f6", padding: "6px 8px", fontSize: 12, outline: "none", resize: "vertical",
                      boxSizing: "border-box",
                    }}
                  />

                  {/* Position */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 4 }}>Posición</div>
                    <select value={textPos} onChange={e => setTextPos(e.target.value)}
                      style={{
                        width: "100%", background: "#1f2937", border: "1px solid #374151", borderRadius: 6,
                        color: "#f3f4f6", padding: "4px 6px", fontSize: 11, outline: "none",
                      }}>
                      {TEXT_POSITIONS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>

                  {/* Font size */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 4 }}>
                      Tamaño: {textSize}px
                    </div>
                    <input type="range" min={12} max={48} value={textSize}
                      onChange={e => setTextSize(Number(e.target.value))}
                      style={{ width: "100%", accentColor: "#2563eb" }}
                    />
                  </div>

                  {/* Color */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 4 }}>Color</div>
                    <div style={{ display: "flex", gap: 6 }}>
                      {TEXT_COLORS.map(c => (
                        <button key={c.id} onClick={() => setTextColor(c.hex)}
                          style={{
                            width: 24, height: 24, borderRadius: "50%", background: c.hex,
                            border: textColor === c.hex ? "2px solid #2563eb" : "2px solid #374151",
                            cursor: "pointer", padding: 0,
                          }}
                          title={c.id}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Duration */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: "#6b7280", marginBottom: 4 }}>
                      Duración: {textDuration}s
                    </div>
                    <input type="range" min={1} max={10} value={textDuration}
                      onChange={e => setTextDuration(Number(e.target.value))}
                      style={{ width: "100%", accentColor: "#2563eb" }}
                    />
                  </div>

                  <button onClick={() => { addTextToTrack(customText, textPos, textSize, textColor, textDuration); setCustomText("") }}
                    disabled={!customText.trim()}
                    style={{
                      ...btnPrimary, width: "100%", marginTop: 8,
                      opacity: customText.trim() ? 1 : 0.4,
                    }}>
                    Agregar al Track T
                  </button>
                </div>

                {/* Title Templates */}
                <div>
                  <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 8, fontWeight: 600 }}>Plantillas de Título</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {TITLE_TEMPLATES.map(tmpl => (
                      <button key={tmpl.id}
                        onClick={() => addTextToTrack(tmpl.text, tmpl.position, tmpl.fontSize, tmpl.color, 4)}
                        style={{
                          ...btnGhost, textAlign: "left", display: "flex", alignItems: "center", gap: 8,
                          padding: "8px 10px",
                        }}>
                        <span style={{ fontSize: 16, flexShrink: 0 }}>
                          {tmpl.id === "intro" ? "🎬" : tmpl.id === "outro" ? "🎞️" : "📺"}
                        </span>
                        <div>
                          <div style={{ fontSize: 12, color: "#f3f4f6" }}>{tmpl.label}</div>
                          <div style={{ fontSize: 10, color: "#6b7280" }}>{tmpl.text}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ─── IA TAB ──────────────────────────────────────────────────── */}
            {sideTab === "ai" && (
              <div style={{ display: "flex", flexDirection: "column", height: "100%", marginTop: -12, marginLeft: -12, marginRight: -12, marginBottom: -12 }}>
                {/* Header */}
                <div style={{
                  padding: "8px 12px", borderBottom: "1px solid #1f2937",
                  fontSize: 12, color: "#60a5fa", fontWeight: 600, display: "flex", alignItems: "center", gap: 6,
                }}>
                  🤖 IA Video Editor
                  <span style={{ marginLeft: "auto", fontSize: 10, color: "#374151" }}>
                    {nodeId ? `#${nodeId.slice(0, 6)}` : ""}
                  </span>
                </div>

                {/* Suggestion chips */}
                <div style={{ display: "flex", gap: 4, padding: "6px 8px", flexWrap: "wrap" }}>
                  {["Añade subtítulos", "Cortes dinámicos", "Mejora el edit"].map(chip => (
                    <button key={chip} onClick={() => sendChip(chip)}
                      style={{
                        ...btnBase, fontSize: 10, padding: "3px 8px",
                        background: "#1e293b", color: "#60a5fa", border: "1px solid #1e3a5f",
                        borderRadius: 12,
                      }}>
                      {chip}
                    </button>
                  ))}
                </div>

                {/* Messages */}
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
                    <div style={{
                      alignSelf: "flex-start", background: "#1f2937", borderRadius: "12px 12px 12px 2px",
                      padding: "6px 10px", fontSize: 12, color: "#9ca3af",
                    }}>
                      ⏳ Pensando...
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input */}
                <form data-testid="chat-form" onSubmit={handleChatSend}
                  style={{ padding: "8px", borderTop: "1px solid #1f2937", display: "flex", gap: 6 }}>
                  <input
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    placeholder="Ej: corta en el segundo 5..."
                    disabled={aiTyping}
                    style={{
                      flex: 1, background: "#1f2937", border: "1px solid #374151", borderRadius: 6,
                      color: "#f3f4f6", padding: "5px 8px", fontSize: 11, outline: "none",
                    }}
                  />
                  <button type="submit" disabled={aiTyping || !chatInput.trim()}
                    style={{
                      ...btnPrimary, padding: "5px 10px", fontSize: 13, flexShrink: 0,
                    }}>
                    ➤
                  </button>
                </form>
              </div>
            )}
          </div>
        </aside>

        {/* Export Modal */}
        {showExport && <ExportModal clips={clips} onClose={() => setShowExport(false)} />}
      </div>
    )
  }
)

export { VideoNodeLayout }
export default VideoNodeLayout
