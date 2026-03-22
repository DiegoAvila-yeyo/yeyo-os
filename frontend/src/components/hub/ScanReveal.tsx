/**
 * YeyoOS — ScanReveal
 * Micro-fase 3.22 — Capa 3: Cuerpo
 *
 * Panel de resultado con efecto scanner que barre de arriba a abajo en 600ms.
 * - Scanner bar: rectángulo semitransparente 4px de alto con glow del color del nodo
 * - Imagen: se revela usando CSS clip-path sincronizado con la posición del scanner
 * - Texto: las líneas aparecen conforme el scanner las alcanza
 * - Al terminar: scanner bar desaparece (fade-out 200ms), panel queda con glow border
 */

import React, { useEffect, useState, useRef } from 'react'
import { FirstTaskResult } from '../../stores/firstTaskStore'

export interface ScanRevealProps {
  result: FirstTaskResult
  nodeColor: string
  isScanning: boolean
}

const PANEL_WIDTH    = 320
const PANEL_HEIGHT   = 220
const SCAN_DURATION  = 600
const FADE_DURATION  = 200

export function ScanReveal({ result, nodeColor, isScanning }: ScanRevealProps) {
  const [scanY, setScanY]         = useState(0)
  const [scanDone, setScanDone]   = useState(false)
  const [barOpacity, setBarOpacity] = useState(1)
  const animRef  = useRef<number>(0)

  useEffect(() => {
    if (!isScanning) {
      setScanDone(true)
      return
    }

    setScanY(0)
    setScanDone(false)
    setBarOpacity(1)

    const scanStart = performance.now()

    function frameScan(now: number) {
      const t = Math.min((now - scanStart) / SCAN_DURATION, 1)
      setScanY(t)
      if (t < 1) {
        animRef.current = requestAnimationFrame(frameScan)
      } else {
        // Fade-out del scanner bar
        const fadeStart = performance.now()
        function frameFade(now2: number) {
          const tf = Math.min((now2 - fadeStart) / FADE_DURATION, 1)
          setBarOpacity(1 - tf)
          if (tf < 1) {
            animRef.current = requestAnimationFrame(frameFade)
          } else {
            setScanDone(true)
          }
        }
        animRef.current = requestAnimationFrame(frameFade)
      }
    }

    animRef.current = requestAnimationFrame(frameScan)
    return () => cancelAnimationFrame(animRef.current)
  }, [isScanning])

  const isImage = result.type === 'image' && !!result.imageUrl

  return (
    <div
      data-testid="scan-reveal-panel"
      style={{
        width:      PANEL_WIDTH,
        minHeight:  PANEL_HEIGHT,
        background: 'rgba(8, 8, 20, 0.93)',
        border:     `1.5px solid ${nodeColor}`,
        borderRadius: 12,
        overflow:   'hidden',
        position:   'relative',
        boxShadow:  scanDone ? `0 0 22px ${nodeColor}44, inset 0 0 10px ${nodeColor}11` : 'none',
        transition: 'box-shadow 0.5s ease',
      }}
    >
      {/* Contenido */}
      <div style={{ padding: '16px 18px', position: 'relative' }}>
        {/* Título */}
        <div
          data-testid="result-title"
          style={{
            fontSize:   13,
            fontWeight: 700,
            color:      nodeColor,
            marginBottom: 12,
            fontFamily: 'monospace',
            opacity:    scanY > 0.05 ? 1 : 0,
            transition: 'opacity 0.2s ease',
          }}
        >
          {result.title}
        </div>

        {/* Imagen: clip-path revela de arriba a abajo */}
        {isImage && (
          <div
            style={{
              width:        '100%',
              height:       148,
              borderRadius: 8,
              overflow:     'hidden',
            }}
          >
            <img
              src={result.imageUrl}
              alt={result.title}
              data-testid="result-image"
              style={{
                width:      '100%',
                height:     '100%',
                objectFit:  'cover',
                clipPath:   `inset(0 0 ${(1 - scanY) * 100}% 0)`,
                transition: 'clip-path 16ms linear',
              }}
            />
          </div>
        )}

        {/* Texto: líneas aparecen conforme el scanner las alcanza */}
        {!isImage && result.textContent && (
          <TextReveal
            content={result.textContent}
            progress={scanY}
            nodeColor={nodeColor}
          />
        )}
      </div>

      {/* Scanner bar */}
      {!scanDone && (
        <div
          data-testid="scanner-bar"
          style={{
            position:   'absolute',
            left:       0,
            right:      0,
            top:        `${scanY * 100}%`,
            height:     4,
            background: `${nodeColor}99`,
            boxShadow:  `0 0 10px ${nodeColor}, 0 0 20px ${nodeColor}66`,
            pointerEvents: 'none',
            zIndex:     10,
            transform:  'translateY(-50%)',
            opacity:    barOpacity,
          }}
        />
      )}
    </div>
  )
}

// ── TextReveal: revela líneas de texto conforme pasa el scanner ──

interface TextRevealProps {
  content:   string
  progress:  number
  nodeColor: string
}

function TextReveal({ content, progress, nodeColor }: TextRevealProps) {
  const lines = content.split('\n')
  return (
    <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#e2e8f0', lineHeight: 1.6 }}>
      {lines.map((line, i) => {
        const threshold   = (i + 1) / lines.length
        const lineVisible = progress >= threshold * 0.88
        const isCode      = /^\s+|^def |^class |^import |^from /.test(line)
        return (
          <div
            key={i}
            data-testid={`text-line-${i}`}
            style={{
              opacity:    lineVisible ? 1 : 0,
              transition: 'opacity 0.15s ease',
              minHeight:  18,
              color:      isCode ? '#a5f3fc' : '#e2e8f0',
              paddingBottom: 1,
            }}
          >
            {line || '\u00A0'}
          </div>
        )
      })}
    </div>
  )
}
