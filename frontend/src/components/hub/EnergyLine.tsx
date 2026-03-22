/**
 * YeyoOS — EnergyLine
 * Micro-fase 3.19 — Capa 3: Cuerpo
 *
 * Línea de energía con partículas que fluyen desde un punto origen
 * a un punto destino. Renderizado con PixiJS Graphics + Ticker.
 * Máximo 50 partículas por línea para no sobrecargar la GPU.
 *
 * Props:
 *   fromX, fromY — punto de origen (nodo central YEYO)
 *   toX, toY     — punto de destino (nodo activo del pipeline)
 *   active       — si false, no renderiza partículas
 *   intensity    — 0.0-1.0, controla velocidad y brillo de partículas
 *   container    — PIXI.Container donde dibujar (del FreeCanvas)
 */

import { useEffect, useRef } from 'react'
import * as PIXI from 'pixi.js'

interface Particle {
  progress: number  // 0.0 → 1.0 a lo largo de la línea
  speed: number
  size: number
  alpha: number
}

export interface EnergyLineProps {
  fromX: number
  fromY: number
  toX: number
  toY: number
  active?: boolean
  intensity?: number       // 0.0-1.0
  maxParticles?: number    // default: 30
  container: PIXI.Container
  app: PIXI.Application
}

const LINE_COLOR = 0x4FC3F7
const PARTICLE_COLOR = 0xB3E5FC
const LINE_ALPHA = 0.25
const PARTICLE_ALPHA_MAX = 0.9

export function useEnergyLine({
  fromX,
  fromY,
  toX,
  toY,
  active = true,
  intensity = 0.5,
  maxParticles = 30,
  container,
  app,
}: EnergyLineProps): void {
  const graphicsRef = useRef<PIXI.Graphics | null>(null)
  const particlesRef = useRef<Particle[]>([])
  const tickerCallbackRef = useRef<((ticker: PIXI.Ticker) => void) | null>(null)

  useEffect(() => {
    if (!active) {
      if (graphicsRef.current) {
        container.removeChild(graphicsRef.current)
        graphicsRef.current.destroy()
        graphicsRef.current = null
      }
      if (tickerCallbackRef.current) {
        app.ticker.remove(tickerCallbackRef.current)
        tickerCallbackRef.current = null
      }
      return
    }

    const gfx = new PIXI.Graphics()
    graphicsRef.current = gfx
    container.addChild(gfx)

    // Inicializar partículas escalonadas
    particlesRef.current = Array.from({ length: maxParticles }, (_, i) => ({
      progress: i / maxParticles,
      speed: 0.004 + intensity * 0.006 + Math.random() * 0.002,
      size: 2 + Math.random() * 2,
      alpha: 0.5 + Math.random() * 0.5,
    }))

    const onTick = (_ticker: PIXI.Ticker) => {
      gfx.clear()

      // Línea base
      gfx.moveTo(fromX, fromY)
      gfx.lineTo(toX, toY)
      gfx.stroke({ width: 1, color: LINE_COLOR, alpha: LINE_ALPHA })

      // Actualizar y dibujar partículas
      particlesRef.current.forEach((p) => {
        p.progress += p.speed * (1 + intensity)
        if (p.progress > 1) p.progress -= 1

        const x = fromX + (toX - fromX) * p.progress
        const y = fromY + (toY - fromY) * p.progress

        gfx.circle(x, y, p.size)
        gfx.fill({ color: PARTICLE_COLOR, alpha: p.alpha * PARTICLE_ALPHA_MAX })
      })
    }

    tickerCallbackRef.current = onTick
    app.ticker.add(onTick)

    return () => {
      if (tickerCallbackRef.current) {
        app.ticker.remove(tickerCallbackRef.current)
        tickerCallbackRef.current = null
      }
      if (graphicsRef.current) {
        container.removeChild(graphicsRef.current)
        graphicsRef.current.destroy()
        graphicsRef.current = null
      }
    }
  }, [fromX, fromY, toX, toY, active, intensity, maxParticles])
}
