/**
 * YeyoOS — GridBackground
 * Micro-fase 3.18 — Capa 3: Cuerpo
 *
 * Componente React que renderiza el Double Grid GLSL shader
 * usando PixiJS 8. Acepta u_saturation para la transición gris→azul.
 * Se usa tanto en el Onboarding como en el Hub principal.
 */

import React, { useEffect, useRef } from 'react'
import * as PIXI from 'pixi.js'

export interface GridBackgroundProps {
  saturation?: number          // 0.0 = gris, 1.0 = azul
  color?: [number, number, number] // RGB 0-1, default: [0.310, 0.765, 0.969]
  style?: React.CSSProperties
  className?: string
}

// GLSL fragment shader inline (misma lógica que grid_background.glsl)
const FRAGMENT_SHADER = `
precision mediump float;
uniform float u_time;
uniform vec3 u_color;
uniform float u_saturation;
uniform vec2 u_resolution;

void main() {
  vec2 uv = gl_FragCoord.xy;
  vec3 bgColor = vec3(0.020, 0.039, 0.078);

  float gridSmall = 20.0;
  vec2 modSmall = mod(uv, gridSmall);
  float lineSmall = step(modSmall.x, 0.5) + step(modSmall.y, 0.5);
  lineSmall = clamp(lineSmall, 0.0, 1.0);
  float alphaSmall = 0.10;

  float gridLarge = 100.0;
  vec2 modLarge = mod(uv, gridLarge);
  float lineLarge = step(modLarge.x, 1.0) + step(modLarge.y, 1.0);
  lineLarge = clamp(lineLarge, 0.0, 1.0);
  float alphaLarge = 0.22;

  vec3 gridColorBase = vec3(0.310, 0.765, 0.969);
  vec3 gridColor = mix(gridColorBase, u_color, 0.5);
  float luma = dot(gridColor, vec3(0.299, 0.587, 0.114));
  vec3 gridColorSat = mix(vec3(luma), gridColor, u_saturation);

  vec3 finalColor = bgColor;
  finalColor = mix(finalColor, gridColorSat, lineSmall * alphaSmall);
  finalColor = mix(finalColor, gridColorSat, lineLarge * alphaLarge);

  gl_FragColor = vec4(finalColor, 1.0);
}
`

export function GridBackground({
  saturation = 1.0,
  color = [0.310, 0.765, 0.969],
  style,
  className,
}: GridBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<PIXI.Application | null>(null)
  const uniformsRef = useRef<{ u_time: number; u_color: number[]; u_saturation: number; u_resolution: number[] } | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const app = new PIXI.Application()
    appRef.current = app

    const container = containerRef.current
    const { width, height } = container.getBoundingClientRect()

    app.init({
      width: width || window.innerWidth,
      height: height || window.innerHeight,
      backgroundColor: 0x050A14,
      antialias: false,
      resolution: 1,
    }).then(() => {
      container.appendChild(app.canvas as HTMLCanvasElement)

      const uniforms = {
        u_time: 0.0,
        u_color: color,
        u_saturation: saturation,
        u_resolution: [app.screen.width, app.screen.height],
      }
      uniformsRef.current = uniforms

      const geometry = new PIXI.Geometry({
        attributes: {
          aPosition: [-1, -1, 1, -1, 1, 1, -1, 1],
        },
        indexBuffer: [0, 1, 2, 0, 2, 3],
      })

      const shader = PIXI.Shader.from({
        gl: {
          vertex: `
            attribute vec2 aPosition;
            void main() {
              gl_Position = vec4(aPosition, 0.0, 1.0);
            }
          `,
          fragment: FRAGMENT_SHADER,
        },
        resources: { uniforms: { u_time: { value: 0.0, type: 'f32' }, u_color: { value: color, type: 'vec3<f32>' }, u_saturation: { value: saturation, type: 'f32' }, u_resolution: { value: [app.screen.width, app.screen.height], type: 'vec2<f32>' } } },
      })

      const mesh = new PIXI.Mesh({ geometry, shader })
      app.stage.addChild(mesh)

      app.ticker.add((ticker) => {
        if (uniformsRef.current) {
          uniformsRef.current.u_time += ticker.deltaTime / 60
        }
      })
    })

    return () => {
      app.destroy(true, { children: true })
      appRef.current = null
    }
  }, [])

  // Actualizar saturation y color sin re-montar
  useEffect(() => {
    if (uniformsRef.current) {
      uniformsRef.current.u_saturation = saturation
      uniformsRef.current.u_color = color
    }
  }, [saturation, color])

  return (
    <div
      ref={containerRef}
      data-testid="grid-background"
      data-saturation={saturation}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        ...style,
      }}
    />
  )
}
