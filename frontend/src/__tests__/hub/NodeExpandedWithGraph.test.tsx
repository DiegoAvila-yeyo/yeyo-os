/**
 * Tests para NodeExpandedWithGraph y GraphOverlay — Micro-fase 3.17
 */

import '@testing-library/jest-dom'
import React from 'react'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { NodeExpandedWithGraph } from '../../components/hub/NodeExpandedWithGraph'
import { GraphOverlay } from '../../components/hub/GraphOverlay'
import { useHubStore } from '../../stores/hubStore'
import { useGraphStore, GraphEventPayload } from '../../stores/graphStore'

beforeEach(() => {
  useHubStore.getState().setNodoGrafoActivo('test-node', null)
  useGraphStore.getState().limpiarTodo()
})

afterEach(() => {
  jest.clearAllTimers()
})

const eventoBase: GraphEventPayload = {
  type: 'graph_event',
  grafo_id: 'grafo_test',
  nodo_id: 'nodo_a',
  estado: 'activo',
  progreso: 0.5,
  mensaje: 'Ejecutando...',
  timestamp: '2025-01-01T00:00:00Z',
  nodos_totales: 2,
}

describe('hubStore — nodoGrafoActivo', () => {
  it('inicialmente no hay grafos activos en nodos', () => {
    expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBeUndefined()
  })

  it('setNodoGrafoActivo asigna grafo a nodo', () => {
    act(() => {
      useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
    })
    expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBe('grafo_test')
  })

  it('setNodoGrafoActivo con null elimina la asignación', () => {
    act(() => {
      useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
      useHubStore.getState().setNodoGrafoActivo('test-node', null)
    })
    expect(useHubStore.getState().obtenerGrafoDeNodo('test-node')).toBeUndefined()
  })

  it('múltiples nodos pueden tener grafos activos simultáneamente', () => {
    act(() => {
      useHubStore.getState().setNodoGrafoActivo('node-1', 'grafo_a')
      useHubStore.getState().setNodoGrafoActivo('node-2', 'grafo_b')
    })
    expect(useHubStore.getState().obtenerGrafoDeNodo('node-1')).toBe('grafo_a')
    expect(useHubStore.getState().obtenerGrafoDeNodo('node-2')).toBe('grafo_b')
  })
})

describe('NodeExpandedWithGraph', () => {
  it('renderiza el contenido hijo correctamente', () => {
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div data-testid="contenido-hijo">Contenido del nodo</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.getByTestId('contenido-hijo')).toBeInTheDocument()
  })

  it('no muestra overlay cuando no hay grafo activo', () => {
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div>Contenido</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.queryByTestId('graph-overlay')).not.toBeInTheDocument()
  })

  it('muestra overlay cuando hubStore tiene grafo activo para el nodo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
    })
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div>Contenido</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.getByTestId('graph-overlay')).toBeInTheDocument()
  })

  it('data-tiene-grafo es true cuando hay overlay activo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
    })
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div>Contenido</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.getByTestId('node-expanded-test-node')).toHaveAttribute('data-tiene-grafo', 'true')
  })

  it('data-tiene-grafo es false cuando no hay overlay', () => {
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div>Contenido</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.getByTestId('node-expanded-test-node')).toHaveAttribute('data-tiene-grafo', 'false')
  })

  it('el overlay tiene el grafo-id correcto', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useHubStore.getState().setNodoGrafoActivo('test-node', 'grafo_test')
    })
    render(
      <NodeExpandedWithGraph nodeId="test-node">
        <div>Contenido</div>
      </NodeExpandedWithGraph>
    )
    expect(screen.getByTestId('graph-overlay')).toHaveAttribute('data-grafo-id', 'grafo_test')
  })
})

describe('GraphOverlay', () => {
  it('renderiza GraphExecutionView dentro del overlay', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    render(<GraphOverlay grafoId="grafo_test" onCerrar={jest.fn()} />)
    expect(screen.getByTestId('graph-overlay')).toBeInTheDocument()
  })

  it('llama onCerrar al hacer click en el backdrop', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    const onCerrar = jest.fn()
    render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} />)
    fireEvent.click(screen.getByTestId('graph-overlay'))
    expect(onCerrar).toHaveBeenCalledTimes(1)
  })

  it('auto-cierra después de delay cuando autoCerrar=true', () => {
    jest.useFakeTimers()
    act(() => {
      useGraphStore.getState().procesarEvento({
        ...eventoBase,
        nodo_id: 'nodo_a',
        estado: 'completado',
        nodos_totales: 1,
      })
    })
    const onCerrar = jest.fn()
    render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} autoCerrarDelay={500} />)
    act(() => {
      jest.advanceTimersByTime(600)
    })
    expect(onCerrar).toHaveBeenCalledTimes(1)
    jest.useRealTimers()
  })

  it('NO auto-cierra cuando autoCerrar=false', () => {
    jest.useFakeTimers()
    act(() => {
      useGraphStore.getState().procesarEvento({
        ...eventoBase,
        nodo_id: 'nodo_a',
        estado: 'completado',
        nodos_totales: 1,
      })
    })
    const onCerrar = jest.fn()
    render(<GraphOverlay grafoId="grafo_test" onCerrar={onCerrar} autoCerrar={false} />)
    act(() => {
      jest.advanceTimersByTime(5000)
    })
    expect(onCerrar).not.toHaveBeenCalled()
    jest.useRealTimers()
  })
})
