/**
 * YeyoOS — CentralNode (Nodo Central del Neural Hub)
 * Micro-fase 3.1 — Capa 3: Cuerpo
 *
 * Nodo central pulsante con shader GLSL de glow.
 * Representa la IA. Siempre al centro del canvas. NO es draggable.
 */

'use client';

import { useEffect, useRef, useCallback } from 'react';
import { Container, Graphics, Filter, GlProgram } from 'pixi.js';
import { useHubStore } from '@/lib/store/hub-store';

import glowVert from '@/shaders/glow.vert';
import glowFrag from '@/shaders/glow.frag';

export type AIState = 'idle' | 'thinking' | 'error' | 'offline';

export interface CentralNodeConfig {
  radius: number;
  state: AIState;
}

export const STATE_CONFIG: Record<
  AIState,
  { color: number; glowColor: [number, number, number]; pulseSpeed: number; intensity: number }
> = {
  idle: {
    color: 0x1e90ff,
    glowColor: [0.12, 0.56, 1.0],
    pulseSpeed: 1.5,
    intensity: 0.8,
  },
  thinking: {
    color: 0x00bfff,
    glowColor: [0.0, 0.75, 1.0],
    pulseSpeed: 4.0,
    intensity: 1.2,
  },
  error: {
    color: 0xff4444,
    glowColor: [1.0, 0.27, 0.27],
    pulseSpeed: 6.0,
    intensity: 1.0,
  },
  offline: {
    color: 0x444466,
    glowColor: [0.27, 0.27, 0.4],
    pulseSpeed: 0.5,
    intensity: 0.3,
  },
};

export function createGlowFilter(): Filter {
  const glProgram = GlProgram.from({
    vertex: glowVert as string,
    fragment: glowFrag as string,
  });

  return new Filter({
    glProgram,
    resources: {
      uniforms: {
        uTime: { value: 0, type: 'f32' },
        uPulseSpeed: { value: 1.5, type: 'f32' },
        uGlowColor: { value: new Float32Array([0.12, 0.56, 1.0]), type: 'vec3<f32>' },
        uGlowIntensity: { value: 0.8, type: 'f32' },
        uRadius: { value: 0.35, type: 'f32' },
      },
    },
  });
}

export function createCentralNodeGraphics(radius: number, color: number): Graphics {
  const g = new Graphics();
  g.circle(0, 0, radius);
  g.fill({ color });
  return g;
}

export function updateGlowUniforms(filter: Filter, state: AIState, time: number): void {
  const config = STATE_CONFIG[state];
  const uniforms = (filter.resources as any).uniforms.uniforms;
  uniforms.uTime = time;
  uniforms.uPulseSpeed = config.pulseSpeed;
  uniforms.uGlowColor = new Float32Array(config.glowColor);
  uniforms.uGlowIntensity = config.intensity;
}

export function getCenterPosition(canvasWidth: number, canvasHeight: number) {
  return {
    x: canvasWidth / 2,
    y: canvasHeight / 2,
  };
}
