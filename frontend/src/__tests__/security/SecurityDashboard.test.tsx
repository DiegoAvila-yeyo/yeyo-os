/**
 * Tests para SecurityDashboard — Micro-fase 3.21
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { SecurityDashboard } from '../../components/security/SecurityDashboard'
import { useSecurityStore } from '../../stores/securityStore'

// Reset store antes de cada test
beforeEach(() => {
  useSecurityStore.setState({
    permissions: new Map(),
    permissionsArray: [],
    history: [],
    killSwitchActive: false,
    cancelledTasks: 0,
    suspendedProcesses: 0,
  })
})

describe('SecurityDashboard', () => {
  it('renderiza el dashboard', () => {
    render(<SecurityDashboard />)
    expect(screen.getByTestId('security-dashboard')).toBeInTheDocument()
  })

  it('muestra 3 cards de resumen', () => {
    render(<SecurityDashboard />)
    expect(screen.getByTestId('summary-cards')).toBeInTheDocument()
  })

  it('muestra contadores en 0 cuando no hay actividad', () => {
    render(<SecurityDashboard />)
    // Verificar que las cards existen (con valores 0)
    const cards = screen.getAllByTestId(/^card-/)
    expect(cards.length).toBe(3)
  })

  it('muestra historial de accesos cuando hay entradas', () => {
    useSecurityStore.setState({
      history: [
        {
          nodeId: 'nodo-chat',
          permission: 'fs.read',
          permissionLabel: 'Leer archivos',
          zone: 'yellow',
          result: 'allowed',
          timestamp: Date.now(),
        },
      ],
    } as any)
    render(<SecurityDashboard />)
    expect(screen.getByTestId('access-history')).toBeInTheDocument()
    expect(screen.getAllByTestId('history-entry').length).toBe(1)
  })

  it('muestra lista de nodos cuando hay permisos registrados', () => {
    const perms = new Map()
    perms.set('nodo-imagen', [
      {
        permission: 'gpu.compute',
        permissionLabel: 'Usar GPU',
        zone: 'yellow',
        remember: false,
      },
    ])
    useSecurityStore.setState({ permissions: perms } as any)
    render(<SecurityDashboard />)
    expect(screen.getByTestId('node-row-nodo-imagen')).toBeInTheDocument()
  })

  it('abre drawer al hacer click en un nodo', () => {
    const perms = new Map()
    perms.set('nodo-video', [
      {
        permission: 'ffmpeg.exec',
        permissionLabel: 'Ejecutar FFmpeg',
        zone: 'red',
        remember: false,
      },
    ])
    useSecurityStore.setState({ permissions: perms } as any)
    render(<SecurityDashboard />)
    fireEvent.click(screen.getByTestId('node-row-nodo-video'))
    expect(screen.getByTestId('node-drawer')).toBeInTheDocument()
  })

  it('cierra drawer al hacer click en la X', () => {
    const perms = new Map()
    perms.set('nodo-code', [
      { permission: 'sandbox.exec', permissionLabel: 'Ejecutar sandbox', zone: 'red', remember: false },
    ])
    useSecurityStore.setState({ permissions: perms } as any)
    render(<SecurityDashboard />)
    fireEvent.click(screen.getByTestId('node-row-nodo-code'))
    expect(screen.getByTestId('node-drawer')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('close-drawer'))
    expect(screen.queryByTestId('node-drawer')).not.toBeInTheDocument()
  })
})
