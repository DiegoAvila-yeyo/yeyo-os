/**
 * Tests para Topbar, HubSidebar, y 4 layouts de nodos — Micro-fase 3.20
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Topbar, TabInfo } from '../../components/layout/Topbar'
import { HubSidebar } from '../../components/layout/HubSidebar'
import { ImageNodeLayout } from '../../components/nodes/ImageNodeLayout'
import { VideoNodeLayout } from '../../components/nodes/VideoNodeLayout'
import { CodeNodeLayout } from '../../components/nodes/CodeNodeLayout'
import { AutomationNodeLayout } from '../../components/nodes/AutomationNodeLayout'
import { useHubStore } from '../../stores/hubStore'

// Mock CSS modules
jest.mock('reactflow/dist/style.css', () => ({}), { virtual: true })

// Mock GridBackground to avoid PIXI issues
jest.mock('../../components/hub/GridBackground', () => ({
  GridBackground: () => <div data-testid="grid-background" />,
}))

// Mock VignetteOverlay
jest.mock('../../components/hub/VignetteOverlay', () => ({
  VignetteOverlay: () => <div data-testid="vignette-overlay" />,
}))

// Mocks
jest.mock('pixi.js', () => ({
  Application: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    destroy: jest.fn(),
    screen: { width: 800, height: 600 },
    stage: { addChild: jest.fn() },
    ticker: { add: jest.fn() },
    canvas: document.createElement('canvas'),
  })),
}))

jest.mock('@monaco-editor/react', () => ({
  __esModule: true,
  default: () => <div data-testid="monaco-editor" />,
}))

jest.mock('reactflow', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="react-flow">{children}</div>,
  Controls: () => <div />,
  Background: () => <div />,
  BackgroundVariant: { Dots: 'dots' },
  useNodesState: (nodes: unknown[]) => [nodes, jest.fn(), jest.fn()],
  useEdgesState: (edges: unknown[]) => [edges, jest.fn(), jest.fn()],
  addEdge: jest.fn(),
}))

const TABS_MOCK: TabInfo[] = [
  { id: 'img', label: 'Image', icono: '🎨', activo: true },
  { id: 'code', label: 'Code', icono: '💻', activo: false },
]

beforeEach(() => {
  useHubStore.setState({ pipelineActivo: false, nodosEnPipeline: [], nodosInstalados: [] })
})

describe('Topbar', () => {
  it('renderiza el topbar', () => {
    render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    expect(screen.getByTestId('topbar')).toBeInTheDocument()
  })

  it('muestra el botón de toggle sidebar', () => {
    render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    expect(screen.getByTestId('toggle-sidebar-btn')).toBeInTheDocument()
  })

  it('llama onToggleSidebar al hacer click en toggle', () => {
    const onToggle = jest.fn()
    render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={onToggle} sidebarOpen={false} />)
    fireEvent.click(screen.getByTestId('toggle-sidebar-btn'))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('muestra las tabs', () => {
    render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    expect(screen.getByTestId('tab-img')).toBeInTheDocument()
    expect(screen.getByTestId('tab-code')).toBeInTheDocument()
  })

  it('Kill Switch siempre visible', () => {
    render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    expect(screen.getByTestId('kill-switch-btn')).toBeInTheDocument()
  })

  it('indicador de pipeline visible pero inactivo por defecto', () => {
    render(<Topbar tabs={[]} onTabClick={jest.fn()} onTabClose={jest.fn()} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    expect(screen.getByTestId('pipeline-indicator')).toHaveAttribute('data-pipeline-activo', 'false')
  })

  it('llama onTabClose al cerrar una tab', () => {
    const onClose = jest.fn()
    render(<Topbar tabs={TABS_MOCK} onTabClick={jest.fn()} onTabClose={onClose} onToggleSidebar={jest.fn()} sidebarOpen={false} />)
    fireEvent.click(screen.getByTestId('close-tab-img'))
    expect(onClose).toHaveBeenCalledWith('img')
  })
})

describe('HubSidebar', () => {
  const NODOS = [{ id: 'img', label: 'Image', icono: '🎨', estado: 'idle' as const }]

  it('renderiza con data-open=false cuando cerrado', () => {
    render(<HubSidebar open={false} nodos={NODOS} onNodoClick={jest.fn()} />)
    expect(screen.getByTestId('hub-sidebar')).toHaveAttribute('data-open', 'false')
  })

  it('renderiza con data-open=true cuando abierto', () => {
    render(<HubSidebar open={true} nodos={NODOS} onNodoClick={jest.fn()} />)
    expect(screen.getByTestId('hub-sidebar')).toHaveAttribute('data-open', 'true')
  })

  it('muestra nodo en sidebar cuando está abierto', () => {
    render(<HubSidebar open={true} nodos={NODOS} onNodoClick={jest.fn()} />)
    expect(screen.getByTestId('sidebar-node-img')).toBeInTheDocument()
  })

  it('llama onNodoClick al hacer click en un nodo', () => {
    const onClick = jest.fn()
    render(<HubSidebar open={true} nodos={NODOS} onNodoClick={onClick} />)
    fireEvent.click(screen.getByTestId('sidebar-node-img'))
    expect(onClick).toHaveBeenCalledWith('img')
  })
})

describe('ImageNodeLayout', () => {
  it('renderiza sin errores', () => {
    render(<ImageNodeLayout />)
    expect(screen.getByTestId('image-node-layout')).toBeInTheDocument()
  })

  it('chat siempre visible', () => {
    render(<ImageNodeLayout />)
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('panel de controles visible', () => {
    render(<ImageNodeLayout />)
    expect(screen.getByTestId('image-controls')).toBeInTheDocument()
  })

  it('galería visible', () => {
    render(<ImageNodeLayout />)
    expect(screen.getByTestId('gallery-area')).toBeInTheDocument()
  })
})

describe('VideoNodeLayout', () => {
  it('renderiza sin errores', () => {
    render(<VideoNodeLayout />)
    expect(screen.getByTestId('video-node-layout')).toBeInTheDocument()
  })

  it('chat siempre visible', () => {
    render(<VideoNodeLayout />)
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('timeline visible', () => {
    render(<VideoNodeLayout />)
    expect(screen.getByTestId('timeline')).toBeInTheDocument()
  })

  it('assets panel visible', () => {
    render(<VideoNodeLayout />)
    expect(screen.getByTestId('assets-panel')).toBeInTheDocument()
  })
})

describe('CodeNodeLayout', () => {
  it('renderiza sin errores', () => {
    render(<CodeNodeLayout />)
    expect(screen.getByTestId('code-node-layout')).toBeInTheDocument()
  })

  it('chat siempre visible', () => {
    render(<CodeNodeLayout />)
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('Monaco editor visible', () => {
    render(<CodeNodeLayout />)
    expect(screen.getByTestId('monaco-editor-container')).toBeInTheDocument()
  })

  it('file explorer visible', () => {
    render(<CodeNodeLayout />)
    expect(screen.getByTestId('file-explorer')).toBeInTheDocument()
  })
})

describe('AutomationNodeLayout', () => {
  it('renderiza sin errores', () => {
    render(<AutomationNodeLayout />)
    expect(screen.getByTestId('automation-node-layout')).toBeInTheDocument()
  })

  it('chat siempre visible', () => {
    render(<AutomationNodeLayout />)
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('pipeline canvas visible', () => {
    render(<AutomationNodeLayout />)
    expect(screen.getByTestId('pipeline-canvas')).toBeInTheDocument()
  })

  it('muestra historial cuando hay ejecuciones', () => {
    const historial = [{ id: 'e1', timestamp: Date.now(), estado: 'completado' as const, duracionMs: 1500 }]
    render(<AutomationNodeLayout historialEjecuciones={historial} />)
    expect(screen.getByTestId('historial-ejecuciones')).toBeInTheDocument()
  })
})
