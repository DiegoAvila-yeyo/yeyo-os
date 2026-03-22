/**
 * Tests — FirstTaskSequence + ScanReveal + firstTaskStore
 * Micro-fase 3.22
 */

import React from 'react'
import { render, screen, act } from '@testing-library/react'
import { renderHook } from '@testing-library/react'
import { FirstTaskSequence } from '../../components/hub/FirstTaskSequence'
import { ScanReveal } from '../../components/hub/ScanReveal'
import {
  useFirstTaskStore,
  detectarTipoNodo,
  FirstTaskResult,
  NODE_COLORS,
} from '../../stores/firstTaskStore'

// ── Mock PixiJS (no WebGL en Jest) ────────────────────────────
jest.mock('pixi.js', () => ({
  Application: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    stage: {
      addChild:    jest.fn(),
      removeChild: jest.fn(),
    },
    destroy: jest.fn(),
  })),
  Graphics: jest.fn().mockImplementation(() => ({
    circle:         jest.fn().mockReturnThis(),
    fill:           jest.fn().mockReturnThis(),
    clear:          jest.fn().mockReturnThis(),
    setStrokeStyle: jest.fn().mockReturnThis(),
    moveTo:         jest.fn().mockReturnThis(),
    lineTo:         jest.fn().mockReturnThis(),
    stroke:         jest.fn().mockReturnThis(),
    x: 0, y: 0, alpha: 1,
  })),
  Container: jest.fn().mockImplementation(() => ({ x: 0, y: 0, addChild: jest.fn() })),
}))

const DEFAULT_PROPS = {
  yeyoX: 400, yeyoY: 300,
  nodeX: 620, nodeY: 300,
  canvasWidth: 800, canvasHeight: 600,
}

beforeEach(() => {
  useFirstTaskStore.setState({
    phase: 'idle', taskText: '', nodeType: 'generic',
    nodeColor: '#60A5FA', result: null,
  })
  jest.useFakeTimers()
})

afterEach(() => {
  jest.useRealTimers()
})

// ─── detectarTipoNodo ─────────────────────────────────────────

describe('detectarTipoNodo', () => {
  test('detecta imagen con "genera una imagen"', () => {
    expect(detectarTipoNodo('genera una imagen de un atardecer')).toBe('image')
  })
  test('detecta imagen con "foto"', () => {
    expect(detectarTipoNodo('toma una foto del paisaje')).toBe('image')
  })
  test('detecta video con "video"', () => {
    expect(detectarTipoNodo('crea un video corto')).toBe('video')
  })
  test('detecta code con "código"', () => {
    expect(detectarTipoNodo('escribe código python para ordenar una lista')).toBe('code')
  })
  test('detecta audio con "música"', () => {
    expect(detectarTipoNodo('genera música relajante')).toBe('audio')
  })
  test('detecta text con "redacta"', () => {
    expect(detectarTipoNodo('redacta un email profesional')).toBe('text')
  })
  test('retorna generic para tarea desconocida', () => {
    expect(detectarTipoNodo('hola yeyo')).toBe('generic')
  })
})

// ─── firstTaskStore ───────────────────────────────────────────

describe('firstTaskStore', () => {
  test('estado inicial es idle', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    expect(result.current.phase).toBe('idle')
    expect(result.current.result).toBeNull()
  })

  test('iniciarPrimeraTarea pone phase=materializing', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('genera una imagen') })
    expect(result.current.phase).toBe('materializing')
  })

  test('iniciarPrimeraTarea asigna tipo y color correcto para imagen', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('genera una imagen') })
    expect(result.current.nodeType).toBe('image')
    expect(result.current.nodeColor).toBe(NODE_COLORS.image)
  })

  test('secuencia: materializing → drawing_line a los 800ms', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
    act(() => { jest.advanceTimersByTime(800) })
    expect(result.current.phase).toBe('drawing_line')
  })

  test('secuencia: drawing_line → processing a los 1200ms', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
    act(() => { jest.advanceTimersByTime(1200) })
    expect(result.current.phase).toBe('processing')
  })

  test('secuencia: scanning con resultado mock a los 3200ms', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
    act(() => { jest.advanceTimersByTime(3200) })
    expect(result.current.phase).toBe('scanning')
    expect(result.current.result).not.toBeNull()
  })

  test('secuencia: complete a los 3800ms', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
    act(() => { jest.advanceTimersByTime(3800) })
    expect(result.current.phase).toBe('complete')
  })

  test('reset vuelve a idle y borra result', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo') })
    act(() => { result.current.reset() })
    expect(result.current.phase).toBe('idle')
    expect(result.current.taskText).toBe('')
    expect(result.current.result).toBeNull()
  })

  test('tipoNodo override manual ignora detección automática', () => {
    const { result } = renderHook(() => useFirstTaskStore())
    act(() => { result.current.iniciarPrimeraTarea('hola yeyo', 'code') })
    expect(result.current.nodeType).toBe('code')
    expect(result.current.nodeColor).toBe(NODE_COLORS.code)
  })
})

// ─── FirstTaskSequence render ─────────────────────────────────

describe('FirstTaskSequence — render', () => {
  test('NO renderiza nada cuando phase=idle', () => {
    const { container } = render(<FirstTaskSequence {...DEFAULT_PROPS} />)
    expect(container.firstChild).toBeNull()
  })

  test('renderiza canvas y contenedor cuando phase=materializing', () => {
    useFirstTaskStore.setState({ phase: 'materializing', nodeColor: '#A855F7', nodeType: 'image' })
    render(<FirstTaskSequence {...DEFAULT_PROPS} />)
    expect(screen.getByTestId('first-task-sequence')).toBeInTheDocument()
    expect(screen.getByTestId('pixi-canvas')).toBeInTheDocument()
  })

  test('muestra label procesando cuando phase=processing', () => {
    useFirstTaskStore.setState({ phase: 'processing', nodeColor: '#A855F7', nodeType: 'image', result: null })
    render(<FirstTaskSequence {...DEFAULT_PROPS} />)
    expect(screen.getByTestId('processing-label')).toBeInTheDocument()
  })

  test('muestra ScanReveal cuando phase=scanning con result', () => {
    const mockResult: FirstTaskResult = { type: 'text', title: 'Texto', textContent: 'Hola' }
    useFirstTaskStore.setState({ phase: 'scanning', nodeColor: '#F59E0B', nodeType: 'text', result: mockResult })
    render(<FirstTaskSequence {...DEFAULT_PROPS} />)
    expect(screen.getByTestId('scan-reveal-container')).toBeInTheDocument()
  })

  test('NO muestra ScanReveal cuando result es null', () => {
    useFirstTaskStore.setState({ phase: 'scanning', nodeColor: '#F59E0B', nodeType: 'text', result: null })
    render(<FirstTaskSequence {...DEFAULT_PROPS} />)
    expect(screen.queryByTestId('scan-reveal-container')).toBeNull()
  })
})

// ─── ScanReveal ───────────────────────────────────────────────

describe('ScanReveal', () => {
  const textResult: FirstTaskResult = {
    type: 'text',
    title: 'Texto generado',
    textContent: 'Primera línea\nSegunda línea\nTercera línea',
  }

  test('renderiza el panel con borde del color del nodo', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
    const panel = screen.getByTestId('scan-reveal-panel')
    expect(panel).toBeInTheDocument()
    expect(panel.style.border.toLowerCase()).toContain('#f59e0b')
  })

  test('muestra el título del resultado', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
    expect(screen.getByTestId('result-title')).toHaveTextContent('Texto generado')
  })

  test('muestra scanner bar cuando isScanning=true', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={true} />)
    expect(screen.getByTestId('scanner-bar')).toBeInTheDocument()
  })

  test('NO muestra scanner bar cuando isScanning=false', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
    expect(screen.queryByTestId('scanner-bar')).toBeNull()
  })

  test('renderiza imagen para resultado tipo image', () => {
    const imageResult: FirstTaskResult = {
      type: 'image', title: 'Imagen generada',
      imageUrl: 'https://picsum.photos/320/200',
    }
    render(<ScanReveal result={imageResult} nodeColor="#A855F7" isScanning={false} />)
    expect(screen.getByTestId('result-image')).toBeInTheDocument()
  })

  test('renderiza líneas de texto para resultado tipo text', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
    expect(screen.getByTestId('text-line-0')).toBeInTheDocument()
    expect(screen.getByTestId('text-line-1')).toBeInTheDocument()
    expect(screen.getByTestId('text-line-2')).toBeInTheDocument()
  })

  test('NO renderiza img cuando el resultado es texto', () => {
    render(<ScanReveal result={textResult} nodeColor="#F59E0B" isScanning={false} />)
    expect(screen.queryByTestId('result-image')).toBeNull()
  })
})
