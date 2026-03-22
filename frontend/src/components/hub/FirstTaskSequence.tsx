/**
 * YeyoOS — FirstTaskSequence
 * Micro-fase 3.22 — Capa 3: Cuerpo
 *
 * Secuencia visual completa de la primera tarea:
 * 1. Partículas convergen → nodo materializa (PixiJS)
 * 2. Línea de energía se traza desde YEYO (PixiJS)
 * 3. Partículas de energía fluyen por la línea (PixiJS)
 * 4. Nodo pulsa en estado "procesando" (CSS)
 * 5. ScanReveal revela el resultado (CSS + CSS clip-path)
 * 6. Estado completado: nodo verde, línea tenue (CSS transition)
 */

import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as PIXI from 'pixi.js'
import { useFirstTaskStore, NodeType, FirstTaskResult, NODE_COLORS } from '../../stores/firstTaskStore'
import { ScanReveal } from './ScanReveal'

// ═══════════════════════════════════
// TIPOS INTERNOS
// ═══════════════════════════════════

interface Particle {
  gfx: PIXI.Graphics
  startX: number
  startY: number
  startTime: number
  duration: number
}

interface EnergyParticle {
  gfx: PIXI.Graphics
  progress: number
  speed: number
}

export interface FirstTaskSequenceProps {
  yeyoX: number
  yeyoY: number
  nodeX: number
  nodeY: number
  canvasWidth: number
  canvasHeight: number
}

// ═══════════════════════════════════
// HELPERS DE ANIMACIÓN
// ═══════════════════════════════════

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t
}

function hexToInt(hex: string): number {
  return parseInt(hex.replace('#', ''), 16)
}

// ═══════════════════════════════════
// COMPONENTE PRINCIPAL
// ═══════════════════════════════════

export function FirstTaskSequence({
  yeyoX,
  yeyoY,
  nodeX,
  nodeY,
  canvasWidth,
  canvasHeight,
}: FirstTaskSequenceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const appRef    = useRef<PIXI.Application | null>(null)
  const lineGfxRef = useRef<PIXI.Graphics | null>(null)
  const particlesRef = useRef<Particle[]>([])
  const energyRef    = useRef<EnergyParticle[]>([])
  const animRef      = useRef<number>(0)
  const energyAnimRef = useRef<number>(0)

  const [nodeScale, setNodeScale]         = useState(0)
  const [lineProgress, setLineProgress]   = useState(0)
  const [lineOpacity, setLineOpacity]     = useState(1)
  const [showProcessing, setShowProcessing] = useState(false)
  const [showScan, setShowScan]           = useState(false)

  const { phase, nodeColor, nodeType, result } = useFirstTaskStore()

  // ── Inicializar PixiJS ──────────────────────────────────────
  useEffect(() => {
    if (!canvasRef.current || appRef.current) return

    const app = new PIXI.Application()
    app.init({
      canvas: canvasRef.current,
      width: canvasWidth,
      height: canvasHeight,
      backgroundAlpha: 0,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
    }).then(() => {
      appRef.current = app
      const lg = new PIXI.Graphics()
      app.stage.addChild(lg)
      lineGfxRef.current = lg
    })

    return () => {
      cancelAnimationFrame(animRef.current)
      cancelAnimationFrame(energyAnimRef.current)
      app.destroy(false)
      appRef.current = null
    }
  }, [canvasWidth, canvasHeight])

  // ── Fase MATERIALIZING: crear partículas dispersas ──────────
  useEffect(() => {
    if (phase !== 'materializing' || !appRef.current) return

    const app = appRef.current
    const colorInt = hexToInt(nodeColor)
    const NUM = 10
    const now = performance.now()
    particlesRef.current = []

    for (let i = 0; i < NUM; i++) {
      const angle = (i / NUM) * Math.PI * 2 + (Math.random() - 0.5) * 0.6
      const dist  = 65 + Math.random() * 20
      const startX = nodeX + Math.cos(angle) * dist
      const startY = nodeY + Math.sin(angle) * dist
      const size   = 2.5 + Math.random() * 2.5

      const gfx = new PIXI.Graphics()
      gfx.circle(0, 0, size)
      gfx.fill({ color: colorInt, alpha: 0.9 })
      gfx.x = startX
      gfx.y = startY
      app.stage.addChild(gfx)

      particlesRef.current.push({
        gfx,
        startX,
        startY,
        startTime: now + i * 18,
        duration: 530 + Math.random() * 80,
      })
    }

    function animateConverge(ts: number) {
      let allDone = true
      particlesRef.current.forEach((p) => {
        const elapsed = ts - p.startTime
        if (elapsed < 0) { allDone = false; return }
        const t    = Math.min(elapsed / p.duration, 1)
        const ease = easeInOut(t)
        p.gfx.x    = lerp(p.startX, nodeX, ease)
        p.gfx.y    = lerp(p.startY, nodeY, ease)
        p.gfx.alpha = 0.9 - ease * 0.4
        if (t < 1) allDone = false
      })

      if (!allDone) {
        animRef.current = requestAnimationFrame(animateConverge)
      } else {
        particlesRef.current.forEach((p) => {
          appRef.current?.stage.removeChild(p.gfx)
        })
        particlesRef.current = []
        animateNodePop()
      }
    }

    animRef.current = requestAnimationFrame(animateConverge)
  }, [phase, nodeColor, nodeX, nodeY])

  // ── Pop del nodo: scale 0 → 1.2 → 1.0 en 200ms ─────────────
  const animateNodePop = useCallback(() => {
    const start    = performance.now()
    const DURATION = 200

    function frame(ts: number) {
      const t = Math.min((ts - start) / DURATION, 1)
      const scale = t < 0.65
        ? lerp(0, 1.2, t / 0.65)
        : lerp(1.2, 1.0, (t - 0.65) / 0.35)
      setNodeScale(scale)
      if (t < 1) animRef.current = requestAnimationFrame(frame)
    }

    animRef.current = requestAnimationFrame(frame)
  }, [])

  // ── Fase DRAWING_LINE: animar progreso de la línea ───────────
  useEffect(() => {
    if (phase !== 'drawing_line') return

    const start    = performance.now()
    const DURATION = 400

    function animateLine(ts: number) {
      const t = Math.min((ts - start) / DURATION, 1)
      setLineProgress(t)
      if (t < 1) {
        animRef.current = requestAnimationFrame(animateLine)
      } else {
        startEnergyFlow()
      }
    }

    animRef.current = requestAnimationFrame(animateLine)
  }, [phase])

  // ── Partículas de energía fluyendo por la línea ──────────────
  const startEnergyFlow = useCallback(() => {
    if (!appRef.current) return
    const app      = appRef.current
    const colorInt = hexToInt(nodeColor)
    const NUM      = 5

    for (let i = 0; i < NUM; i++) {
      const gfx = new PIXI.Graphics()
      gfx.circle(0, 0, 2.5)
      gfx.fill({ color: colorInt, alpha: 0.85 })
      app.stage.addChild(gfx)
      energyRef.current.push({
        gfx,
        progress: i / NUM,
        speed: 0.0038 + Math.random() * 0.0022,
      })
    }

    function animateEnergy() {
      energyRef.current.forEach((ep) => {
        ep.progress = (ep.progress + ep.speed) % 1
        ep.gfx.x = lerp(yeyoX, nodeX, ep.progress)
        ep.gfx.y = lerp(yeyoY, nodeY, ep.progress)
        const fade = 0.12
        if      (ep.progress < fade)       ep.gfx.alpha = (ep.progress / fade) * 0.85
        else if (ep.progress > 1 - fade)   ep.gfx.alpha = ((1 - ep.progress) / fade) * 0.85
        else                               ep.gfx.alpha = 0.85
      })
      energyAnimRef.current = requestAnimationFrame(animateEnergy)
    }

    energyAnimRef.current = requestAnimationFrame(animateEnergy)
  }, [nodeColor, nodeX, nodeY, yeyoX, yeyoY])

  // ── Sincronizar estados de UI con la fase ────────────────────
  useEffect(() => {
    if (phase === 'processing')  { setShowProcessing(true) }
    if (phase === 'scanning')    { setShowProcessing(false); setShowScan(true) }
    if (phase === 'complete')    { setLineOpacity(0.4) }
  }, [phase])

  // ── Redibujar línea en PixiJS ────────────────────────────────
  useEffect(() => {
    const lg = lineGfxRef.current
    if (!lg || lineProgress <= 0) { lg?.clear(); return }

    const endX    = lerp(yeyoX, nodeX, lineProgress)
    const endY    = lerp(yeyoY, nodeY, lineProgress)
    const colorInt = hexToInt(nodeColor)

    lg.clear()
    lg.setStrokeStyle({ width: 2, color: colorInt, alpha: lineOpacity })
    lg.moveTo(yeyoX, yeyoY)
    lg.lineTo(endX, endY)
    lg.stroke()
  }, [lineProgress, lineOpacity, yeyoX, yeyoY, nodeX, nodeY, nodeColor])

  if (phase === 'idle') return null

  const NODE_D    = 48
  const isComplete = phase === 'complete'

  return (
    <div
      data-testid="first-task-sequence"
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
    >
      {/* Canvas PixiJS — partículas y línea */}
      <canvas
        ref={canvasRef}
        data-testid="pixi-canvas"
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      />

      {/* Nodo satélite (CSS) */}
      {nodeScale > 0 && (
        <div
          data-testid="satellite-node"
          style={{
            position: 'absolute',
            left:   nodeX - NODE_D / 2,
            top:    nodeY - NODE_D / 2,
            width:  NODE_D,
            height: NODE_D,
            borderRadius: '50%',
            background:  isComplete ? '#4CAF50' : nodeColor,
            boxShadow:   `0 0 18px ${isComplete ? '#4CAF5088' : nodeColor + '88'}`,
            transform:   `scale(${nodeScale})`,
            transition:  isComplete ? 'background 0.5s ease, box-shadow 0.5s ease' : 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: phase === 'processing'
              ? 'yeyoNodePulse 1.2s ease-in-out infinite'
              : 'none',
          }}
        >
          <NodeIcon type={nodeType} />
        </div>
      )}

      {/* Label "procesando..." */}
      {showProcessing && (
        <div
          data-testid="processing-label"
          style={{
            position:   'absolute',
            left:       nodeX - 52,
            top:        nodeY + NODE_D / 2 + 10,
            color:      nodeColor,
            fontSize:   11,
            fontFamily: 'monospace',
            opacity:    0.85,
            animation:  'yeyoFadeInUp 0.3s ease',
          }}
        >
          procesando<AnimatedDots />
        </div>
      )}

      {/* Panel ScanReveal */}
      {showScan && result && (
        <div
          data-testid="scan-reveal-container"
          style={{
            position:     'absolute',
            left:         nodeX + NODE_D / 2 + 18,
            top:          nodeY - 110,
            pointerEvents: 'auto',
          }}
        >
          <ScanReveal
            result={result}
            nodeColor={nodeColor}
            isScanning={phase === 'scanning'}
          />
        </div>
      )}

      <style>{`
        @keyframes yeyoNodePulse {
          0%,100% { transform: scale(1);    box-shadow: 0 0 18px ${nodeColor}88; }
          50%     { transform: scale(1.09); box-shadow: 0 0 30px ${nodeColor}cc; }
        }
        @keyframes yeyoFadeInUp {
          from { opacity: 0; transform: translateY(5px); }
          to   { opacity: 0.85; transform: translateY(0); }
        }
        @keyframes yeyoDotBlink {
          0%,80%,100% { opacity: 0; }
          40%         { opacity: 1; }
        }
      `}</style>
    </div>
  )
}

// ── Sub-componentes ──────────────────────────────────────────

function NodeIcon({ type }: { type: NodeType }) {
  const icons: Record<NodeType, string> = {
    image:   '🖼',
    video:   '🎬',
    code:    '⌨',
    text:    '📝',
    audio:   '🎵',
    generic: '✦',
  }
  return <span style={{ fontSize: 20, lineHeight: 1 }}>{icons[type]}</span>
}

function AnimatedDots() {
  return (
    <span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            display:   'inline-block',
            animation: `yeyoDotBlink 1.4s ${i * 0.2}s infinite`,
          }}
        >.</span>
      ))}
    </span>
  )
}
