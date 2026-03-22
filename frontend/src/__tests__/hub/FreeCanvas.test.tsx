/**
 * Tests para FreeCanvas, EnergyLine, VignetteOverlay — Micro-fase 3.19
 */

import React from 'react'
import { render, screen, act } from '@testing-library/react'
import { VignetteOverlay } from '../../components/hub/VignetteOverlay'
import { useHubStore } from '../../stores/hubStore'

// Mock PixiJS
jest.mock('pixi.js', () => ({
  Application: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    destroy: jest.fn(),
    screen: { width: 800, height: 600 },
    stage: { addChild: jest.fn(), removeChildren: jest.fn() },
    ticker: { add: jest.fn(), remove: jest.fn() },
    canvas: document.createElement('canvas'),
  })),
  Container: jest.fn().mockImplementation(() => ({
    addChild: jest.fn(),
    removeChildren: jest.fn(),
    removeChild: jest.fn(),
    x: 0,
    y: 0,
    scale: { set: jest.fn(), x: 1 },
    eventMode: 'static',
    cursor: 'pointer',
    on: jest.fn(),
  })),
  Graphics: jest.fn().mockImplementation(() => ({
    circle: jest.fn().mockReturnThis(),
    fill: jest.fn().mockReturnThis(),
    stroke: jest.fn().mockReturnThis(),
    moveTo: jest.fn().mockReturnThis(),
    lineTo: jest.fn().mockReturnThis(),
    clear: jest.fn().mockReturnThis(),
    destroy: jest.fn(),
  })),
  Text: jest.fn().mockImplementation(() => ({
    anchor: { set: jest.fn() },
    y: 0,
  })),
  TextStyle: jest.fn(),
}))

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, val: string) => { store[key] = val },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

beforeEach(() => {
  localStorageMock.clear()
  useHubStore.setState({
    posicionesNodos: {},
    nodosInstalados: [],
    pipelineActivo: false,
    nodosEnPipeline: [],
  })
})

describe('hubStore — posiciones y pipeline', () => {
  it('setPosicionNodo guarda posición', () => {
    act(() => {
      useHubStore.getState().setPosicionNodo('node-1', 100, 200)
    })
    expect(useHubStore.getState().posicionesNodos['node-1']).toEqual({ x: 100, y: 200 })
  })

  it('guardarPosicionesEnStorage persiste en localStorage', () => {
    act(() => {
      useHubStore.getState().setPosicionNodo('node-1', 50, 75)
      useHubStore.getState().guardarPosicionesEnStorage('user-1')
    })
    const stored = JSON.parse(localStorageMock.getItem('yeyo_hub_positions_user-1') || '{}')
    expect(stored['node-1']).toEqual({ x: 50, y: 75 })
  })

  it('cargarPosicionesDesdeStorage restaura posiciones', () => {
    localStorageMock.setItem('yeyo_hub_positions_user-1', JSON.stringify({ 'node-2': { x: 300, y: 400 } }))
    act(() => {
      useHubStore.getState().cargarPosicionesDesdeStorage('user-1')
    })
    expect(useHubStore.getState().posicionesNodos['node-2']).toEqual({ x: 300, y: 400 })
  })

  it('setNodosInstalados actualiza lista', () => {
    act(() => {
      useHubStore.getState().setNodosInstalados(['img', 'code'])
    })
    expect(useHubStore.getState().esNodoInstalado('img')).toBe(true)
    expect(useHubStore.getState().esNodoInstalado('video')).toBe(false)
  })

  it('setPipelineActivo activa el pipeline con nodos', () => {
    act(() => {
      useHubStore.getState().setPipelineActivo(true, ['yeyo', 'img'])
    })
    expect(useHubStore.getState().pipelineActivo).toBe(true)
    expect(useHubStore.getState().nodosEnPipeline).toContain('img')
  })

  it('setPipelineActivo desactiva el pipeline', () => {
    act(() => {
      useHubStore.getState().setPipelineActivo(true, ['yeyo'])
      useHubStore.getState().setPipelineActivo(false)
    })
    expect(useHubStore.getState().pipelineActivo).toBe(false)
    expect(useHubStore.getState().nodosEnPipeline).toHaveLength(0)
  })
})

describe('VignetteOverlay', () => {
  it('renderiza con data-visible=false por defecto', () => {
    render(<VignetteOverlay visible={false} />)
    expect(screen.getByTestId('vignette-overlay')).toHaveAttribute('data-visible', 'false')
  })

  it('renderiza con data-visible=true cuando visible=true', () => {
    render(<VignetteOverlay visible={true} />)
    expect(screen.getByTestId('vignette-overlay')).toHaveAttribute('data-visible', 'true')
  })

  it('tiene pointer-events none (no bloquea interacción)', () => {
    render(<VignetteOverlay visible={true} />)
    const el = screen.getByTestId('vignette-overlay')
    expect(el).toHaveStyle('pointer-events: none')
  })

  it('opacity 0 cuando visible=false', () => {
    render(<VignetteOverlay visible={false} maxOpacity={0.3} />)
    const el = screen.getByTestId('vignette-overlay')
    expect(el).toHaveStyle('opacity: 0')
  })

  it('opacity maxOpacity cuando visible=true', () => {
    render(<VignetteOverlay visible={true} maxOpacity={0.3} />)
    const el = screen.getByTestId('vignette-overlay')
    expect(el).toHaveStyle('opacity: 0.3')
  })
})
