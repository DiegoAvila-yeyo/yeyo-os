/**
 * YeyoOS — VignetteOverlay
 * Micro-fase 3.19 — Capa 3: Cuerpo
 *
 * Overlay con radial gradient negro en los bordes.
 * Aparece (fade-in 500ms) cuando un pipeline corre.
 * Desaparece (fade-out 1000ms) al terminar el pipeline.
 * ~30% opacidad máxima.
 */

import React, { useEffect, useState } from 'react'

export interface VignetteOverlayProps {
  visible: boolean
  maxOpacity?: number    // default: 0.30
  fadeInMs?: number      // default: 500
  fadeOutMs?: number     // default: 1000
  style?: React.CSSProperties
}

export function VignetteOverlay({
  visible,
  maxOpacity = 0.30,
  fadeInMs = 500,
  fadeOutMs = 1000,
  style,
}: VignetteOverlayProps) {
  const [opacity, setOpacity] = useState(0)

  useEffect(() => {
    if (visible) {
      setOpacity(maxOpacity)
    } else {
      setOpacity(0)
    }
  }, [visible, maxOpacity])

  return (
    <div
      data-testid="vignette-overlay"
      data-visible={visible}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,1) 100%)',
        opacity,
        transition: visible
          ? `opacity ${fadeInMs}ms ease-in`
          : `opacity ${fadeOutMs}ms ease-out`,
        zIndex: 5,
        ...style,
      }}
    />
  )
}
