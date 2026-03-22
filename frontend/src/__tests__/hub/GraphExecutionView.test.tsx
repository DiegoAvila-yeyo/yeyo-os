/**
 * Tests para GraphExecutionView y graphStore — Micro-fase 3.16
 */

import React from 'react'
import { render, screen, act } from '@testing-library/react'
import { GraphExecutionView } from '../../components/hub/GraphExecutionView'
import { useGraphStore, GraphEventPayload } from '../../stores/graphStore'

// Resetear store antes de cada test
beforeEach(() => {
  useGraphStore.getState().limpiarTodo()
})

const eventoBase: GraphEventPayload = {
  type: 'graph_event',
  grafo_id: 'test_grafo',
  nodo_id: 'nodo_a',
  estado: 'activo',
  progreso: 0.33,
  mensaje: 'Procesando...',
  timestamp: '2025-01-01T00:00:00Z',
  nodos_totales: 3,
}

describe('graphStore', () => {
  it('inicialmente no tiene grafos activos', () => {
    const store = useGraphStore.getState()
    expect(Object.keys(store.grafosActivos)).toHaveLength(0)
    expect(store.hayGrafosActivos()).toBe(false)
  })

  it('procesa evento y crea grafo nuevo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    const grafo = useGraphStore.getState().grafosActivos['test_grafo']
    expect(grafo).toBeDefined()
    expect(grafo.grafoId).toBe('test_grafo')
    expect(grafo.nodos).toHaveLength(1)
    expect(grafo.nodos[0].id).toBe('nodo_a')
    expect(grafo.nodos[0].estado).toBe('activo')
  })

  it('actualiza estado de nodo existente', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useGraphStore.getState().procesarEvento({
        ...eventoBase,
        estado: 'completado',
        progreso: 1,
        mensaje: 'Listo',
      })
    })
    const grafo = useGraphStore.getState().grafosActivos['test_grafo']
    expect(grafo.nodos[0].estado).toBe('completado')
    expect(grafo.nodos[0].mensaje).toBe('Listo')
  })

  it('agrega múltiples nodos al grafo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'activo' })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_c', estado: 'pendiente' })
    })
    const grafo = useGraphStore.getState().grafosActivos['test_grafo']
    expect(grafo.nodos).toHaveLength(3)
  })

  it('calcula progreso global correctamente', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 3 })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'saltado', nodos_totales: 3 })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_c', estado: 'activo', nodos_totales: 3 })
    })
    const grafo = useGraphStore.getState().grafosActivos['test_grafo']
    // 2 de 3 terminados = 0.666...
    expect(grafo.progreso).toBeCloseTo(0.666, 1)
  })

  it('marca grafo como completado cuando todos los nodos terminan', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 2 })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'completado', nodos_totales: 2 })
    })
    const grafo = useGraphStore.getState().grafosActivos['test_grafo']
    expect(grafo.completado).toBe(true)
    expect(grafo.activo).toBe(false)
  })

  it('limpia grafo correctamente', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useGraphStore.getState().limpiarGrafo('test_grafo')
    })
    expect(useGraphStore.getState().grafosActivos['test_grafo']).toBeUndefined()
  })

  it('limpiaTodo elimina todos los grafos', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
      useGraphStore.getState().procesarEvento({ ...eventoBase, grafo_id: 'otro_grafo' })
      useGraphStore.getState().limpiarTodo()
    })
    expect(Object.keys(useGraphStore.getState().grafosActivos)).toHaveLength(0)
  })

  it('hayGrafosActivos retorna true cuando hay un grafo activo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    expect(useGraphStore.getState().hayGrafosActivos()).toBe(true)
  })
})

describe('GraphExecutionView', () => {
  it('muestra mensaje de espera cuando no hay grafo', () => {
    render(<GraphExecutionView grafoId="no_existe" />)
    expect(screen.getByTestId('graph-execution-view-vacio')).toBeInTheDocument()
  })

  it('muestra el componente cuando hay grafo activo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    expect(screen.getByTestId('graph-execution-view')).toBeInTheDocument()
  })

  it('muestra los nodos del grafo', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_b', estado: 'activo' })
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    expect(screen.getByTestId('nodo-grafo-nodo_a')).toBeInTheDocument()
    expect(screen.getByTestId('nodo-grafo-nodo_b')).toBeInTheDocument()
  })

  it('nodo activo tiene atributo data-estado correcto', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'activo' })
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    const nodo = screen.getByTestId('nodo-grafo-nodo_a')
    expect(nodo).toHaveAttribute('data-estado', 'activo')
  })

  it('nodo completado tiene atributo data-estado correcto', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado' })
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    const nodo = screen.getByTestId('nodo-grafo-nodo_a')
    expect(nodo).toHaveAttribute('data-estado', 'completado')
  })

  it('muestra barra de progreso', () => {
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, progreso: 0.5 })
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    expect(screen.getByTestId('barra-progreso')).toBeInTheDocument()
  })

  it('llama onCompletar cuando el grafo completa', () => {
    const onCompletar = jest.fn()
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'completado', nodos_totales: 1 })
    })
    render(<GraphExecutionView grafoId="test_grafo" onCompletar={onCompletar} />)
    expect(onCompletar).toHaveBeenCalledWith('test_grafo')
  })

  it('llama onError cuando hay un nodo con error', () => {
    const onError = jest.fn()
    act(() => {
      useGraphStore.getState().procesarEvento({ ...eventoBase, nodo_id: 'nodo_a', estado: 'error', mensaje: 'fallo grave' })
    })
    render(<GraphExecutionView grafoId="test_grafo" onError={onError} />)
    expect(onError).toHaveBeenCalledWith('test_grafo', 'fallo grave')
  })

  it('el data-grafo-id coincide con el grafoId prop', () => {
    act(() => {
      useGraphStore.getState().procesarEvento(eventoBase)
    })
    render(<GraphExecutionView grafoId="test_grafo" />)
    expect(screen.getByTestId('graph-execution-view')).toHaveAttribute('data-grafo-id', 'test_grafo')
  })
})
