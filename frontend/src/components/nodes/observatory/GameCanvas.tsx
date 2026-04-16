/**
 * YeyoOS — GameCanvas
 * Canvas 2D component for the Observatory 2D game.
 * Uses imageSmoothingEnabled=false for pixel-perfect rendering at 3x scale.
 */
'use client'

import React, { useRef, useEffect, useCallback } from 'react'
import { GameEngine, GameEvent } from './game/GameEngine'

interface GameCanvasProps {
  width?: number
  height?: number
  events?: GameEvent[]
  onCharacterClick?: (name: string) => void
  onBuildingClick?: (name: string) => void
}

export function GameCanvas({
  width = 960,
  height = 720,
  events = [],
  onCharacterClick,
  onBuildingClick,
}: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<GameEngine | null>(null)
  const processedCountRef = useRef(0)

  // Stable callback refs so engine doesn't need re-init on handler changes
  const charClickRef = useRef(onCharacterClick)
  charClickRef.current = onCharacterClick
  const buildClickRef = useRef(onBuildingClick)
  buildClickRef.current = onBuildingClick

  const handleCharacterClick = useCallback((name: string) => {
    charClickRef.current?.(name)
  }, [])

  const handleBuildingClick = useCallback((name: string) => {
    buildClickRef.current?.(name)
  }, [])

  // Init / destroy engine
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const engine = new GameEngine()
    engineRef.current = engine
    engine.onCharacterClick = handleCharacterClick
    engine.onBuildingClick = handleBuildingClick
    processedCountRef.current = 0

    engine.init(canvas).catch((err) => {
      console.error('[GameCanvas] Failed to initialise engine:', err)
    })

    return () => {
      engine.destroy()
      engineRef.current = null
    }
  }, [handleCharacterClick, handleBuildingClick])

  // Feed new events into the engine
  useEffect(() => {
    const engine = engineRef.current
    if (!engine || events.length === 0) return

    const newEvents = events.slice(processedCountRef.current)
    for (const evt of newEvents) {
      engine.handleEvent(evt)
    }
    processedCountRef.current = events.length
  }, [events])

  // Resize engine when dimensions change
  useEffect(() => {
    engineRef.current?.resize(width, height)
  }, [width, height])

  return (
    <div
      style={{
        width,
        height,
        overflow: 'hidden',
        position: 'relative',
        borderRadius: 4,
      }}
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{
          display: 'block',
          imageRendering: 'pixelated',
          background: '#1a1a2e',
          width,
          height,
        }}
      />
    </div>
  )
}

export default GameCanvas
