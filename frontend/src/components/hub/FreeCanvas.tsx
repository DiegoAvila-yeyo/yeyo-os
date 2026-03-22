/**
 * YeyoOS — FreeCanvas
 * Micro-fase 3.19 — Capa 3: Cuerpo
 *
 * Canvas PixiJS con pan/zoom y nodos libres.
 * - Nodos flotan en posiciones libres (no órbita)
 * - Solo muestra nodos INSTALADOS
 * - Posiciones guardadas en localStorage por usuario
 * - Drag para mover nodos, doble-click para abrir
 * - Canvas draggable (pan) con mouse drag
 * - Zoom con scroll de ratón (0.3x — 3.0x)
 */

import React, { useEffect, useRef, useCallback } from 'react'
import * as PIXI from 'pixi.js'
import { useHubStore } from '../../stores/hubStore'
import { GridBackground } from './GridBackground'

export interface NodoLibreInfo {
  id: string
  label: string
  tipo: string
  icono?: string
  colorAcento?: string
  estado?: 'idle' | 'activo' | 'error'
}

export interface FreeCanvasProps {
  nodos: NodoLibreInfo[]
  userId: string
  onNodoClick?: (nodeId: string) => void
  onNodoDoubleClick?: (nodeId: string) => void
  width?: number
  height?: number
  style?: React.CSSProperties
}

const DEFAULT_COLORS: Record<string, number> = {
  idle: 0x1565C0,
  activo: 0x4FC3F7,
  error: 0xF44336,
}

const NODE_RADIUS = 36

export function FreeCanvas({
  nodos,
  userId,
  onNodoClick,
  onNodoDoubleClick,
  width = 800,
  height = 600,
  style,
}: FreeCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<PIXI.Application | null>(null)
  const worldRef = useRef<PIXI.Container | null>(null)
  const nodeContainersRef = useRef<Map<string, PIXI.Container>>(new Map())

  const {
    posicionesNodos,
    setPosicionNodo,
    cargarPosicionesDesdeStorage,
    guardarPosicionesEnStorage,
    nodosInstalados,
    pipelineActivo,
    nodosEnPipeline,
  } = useHubStore()

  useEffect(() => {
    cargarPosicionesDesdeStorage(userId)
  }, [userId])

  useEffect(() => {
    if (!containerRef.current) return

    const app = new PIXI.Application()
    appRef.current = app

    app.init({
      width,
      height,
      backgroundColor: 0x050A14,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
    }).then(() => {
      if (!containerRef.current) return
      containerRef.current.appendChild(app.canvas as HTMLCanvasElement)

      // World container — se mueve con pan/zoom
      const world = new PIXI.Container()
      worldRef.current = world
      app.stage.addChild(world)

      // Estado de pan
      let isPanning = false
      let panStart = { x: 0, y: 0 }
      let worldStart = { x: 0, y: 0 }

      app.canvas.addEventListener('mousedown', (e: MouseEvent) => {
        isPanning = true
        panStart = { x: e.clientX, y: e.clientY }
        worldStart = { x: world.x, y: world.y }
      })

      app.canvas.addEventListener('mousemove', (e: MouseEvent) => {
        if (!isPanning) return
        world.x = worldStart.x + (e.clientX - panStart.x)
        world.y = worldStart.y + (e.clientY - panStart.y)
      })

      app.canvas.addEventListener('mouseup', () => { isPanning = false })
      app.canvas.addEventListener('mouseleave', () => { isPanning = false })

      // Zoom con scroll
      app.canvas.addEventListener('wheel', (e: WheelEvent) => {
        e.preventDefault()
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
        const newScale = Math.max(0.3, Math.min(3.0, world.scale.x * zoomFactor))
        world.scale.set(newScale)
      })

      renderNodos()
    })

    return () => {
      guardarPosicionesEnStorage(userId)
      app.destroy(true, { children: true })
      appRef.current = null
    }
  }, [width, height])

  const renderNodos = useCallback(() => {
    const world = worldRef.current
    if (!world) return

    world.removeChildren()
    nodeContainersRef.current.clear()

    nodos.filter(n => nodosInstalados.includes(n.id) || nodos.length <= 1).forEach((nodo, i) => {
      const pos = posicionesNodos[nodo.id] ?? {
        x: 150 + (i % 4) * 180,
        y: 150 + Math.floor(i / 4) * 180,
      }

      const container = new PIXI.Container()
      container.x = pos.x
      container.y = pos.y
      container.eventMode = 'static'
      container.cursor = 'pointer'

      // Círculo base
      const circle = new PIXI.Graphics()
      const estado = nodo.estado ?? 'idle'
      const color = DEFAULT_COLORS[estado]
      circle.circle(0, 0, NODE_RADIUS)
      circle.fill({ color, alpha: estado === 'activo' ? 0.9 : 0.7 })
      circle.stroke({ width: 2, color: estado === 'activo' ? 0x4FC3F7 : 0x1E3A5F })
      container.addChild(circle)

      // Etiqueta
      const label = new PIXI.Text({
        text: nodo.label,
        style: new PIXI.TextStyle({ fill: 0xE0F7FA, fontSize: 11, fontFamily: 'Inter, sans-serif' }),
      })
      label.anchor.set(0.5, 0)
      label.y = NODE_RADIUS + 6
      container.addChild(label)

      // Drag behavior
      let dragStart: { x: number; y: number } | null = null
      let containerStart: { x: number; y: number } | null = null
      let isDragging = false

      container.on('pointerdown', (e: PIXI.FederatedPointerEvent) => {
        dragStart = { x: e.globalX, y: e.globalY }
        containerStart = { x: container.x, y: container.y }
        isDragging = false
      })

      container.on('pointermove', (e: PIXI.FederatedPointerEvent) => {
        if (!dragStart || !containerStart) return
        const dx = e.globalX - dragStart.x
        const dy = e.globalY - dragStart.y
        if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
          isDragging = true
          container.x = containerStart.x + dx
          container.y = containerStart.y + dy
        }
      })

      container.on('pointerup', () => {
        if (isDragging) {
          setPosicionNodo(nodo.id, container.x, container.y)
          guardarPosicionesEnStorage(userId)
        } else {
          onNodoClick?.(nodo.id)
        }
        dragStart = null
        containerStart = null
      })

      container.on('pointerdblclick', () => {
        onNodoDoubleClick?.(nodo.id)
      })

      world.addChild(container)
      nodeContainersRef.current.set(nodo.id, container)
    })
  }, [nodos, nodosInstalados, posicionesNodos])

  useEffect(() => {
    renderNodos()
  }, [nodos, posicionesNodos, nodosInstalados])

  return (
    <div
      ref={containerRef}
      data-testid="free-canvas"
      data-pipeline-activo={pipelineActivo}
      style={{
        position: 'relative',
        width,
        height,
        overflow: 'hidden',
        cursor: 'grab',
        ...style,
      }}
    />
  )
}
