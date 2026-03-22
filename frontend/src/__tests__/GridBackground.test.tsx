/**
 * Tests para GridBackground — Micro-fase 3.18
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import { GridBackground } from '@/components/hub/GridBackground'

// Mock PixiJS
jest.mock('pixi.js', () => ({
  Application: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    destroy: jest.fn(),
    screen: { width: 1920, height: 1080 },
    stage: { addChild: jest.fn() },
    ticker: { add: jest.fn() },
    canvas: document.createElement('canvas'),
  })),
  Geometry: jest.fn(),
  Shader: { from: jest.fn() },
  Mesh: jest.fn().mockImplementation(() => ({})),
}))

describe('GridBackground', () => {
  it('renderiza el contenedor', () => {
    render(<GridBackground />)
    expect(screen.getByTestId('grid-background')).toBeInTheDocument()
  })

  it('establece saturation por defecto en 1.0', () => {
    render(<GridBackground />)
    const element = screen.getByTestId('grid-background')
    expect(element).toHaveAttribute('data-saturation', '1')
  })

  it('acepta saturation prop', () => {
    render(<GridBackground saturation={0.5} />)
    const element = screen.getByTestId('grid-background')
    expect(element).toHaveAttribute('data-saturation', '0.5')
  })

  it('acepta color prop', () => {
    render(<GridBackground color={[1, 0, 0]} />)
    expect(screen.getByTestId('grid-background')).toBeInTheDocument()
  })

  it('aplica className si se proporciona', () => {
    render(<GridBackground className="custom-class" />)
    expect(screen.getByTestId('grid-background')).toHaveClass('custom-class')
  })

  it('posición y estilos CSS correctos', () => {
    render(<GridBackground />)
    const element = screen.getByTestId('grid-background')
    expect(element).toHaveStyle('position: absolute')
    expect(element).toHaveStyle('overflow: hidden')
  })
})
