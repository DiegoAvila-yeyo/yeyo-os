/**
 * YeyoOS — GridBackground
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Double grid CSS: líneas finas (20px) + gruesas (100px).
 * La saturación controla la transición gris→azul sin WebGL.
 * Se usa tanto en el Onboarding como en el Hub principal.
 */

import React, { useMemo } from 'react'

export interface GridBackgroundProps {
  saturation?: number                     // 0.0 = gris, 1.0 = azul
  color?: [number, number, number]        // RGB 0-1, default: [0.310, 0.765, 0.969]
  style?: React.CSSProperties
  className?: string
}

export function GridBackground({
  saturation = 1.0,
  color = [0.310, 0.765, 0.969],
  style,
  className,
}: GridBackgroundProps) {
  // Interpolar entre gris y azul según saturation
  const gridColor = useMemo(() => {
    const luma = color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114
    const r = Math.round((luma + (color[0] - luma) * saturation) * 255)
    const g = Math.round((luma + (color[1] - luma) * saturation) * 255)
    const b = Math.round((luma + (color[2] - luma) * saturation) * 255)
    return `rgb(${r},${g},${b})`
  }, [saturation, color])

  return (
    <div
      data-testid="grid-background"
      data-saturation={saturation}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        backgroundColor: '#050A14',
        // Líneas finas cada 20px + líneas gruesas cada 100px
        backgroundImage: `
          linear-gradient(${gridColor}1a 1px, transparent 1px),
          linear-gradient(90deg, ${gridColor}1a 1px, transparent 1px),
          linear-gradient(${gridColor}38 1px, transparent 1px),
          linear-gradient(90deg, ${gridColor}38 1px, transparent 1px)
        `,
        backgroundSize: '20px 20px, 20px 20px, 100px 100px, 100px 100px',
        ...style,
      }}
    />
  )
}
