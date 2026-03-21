/**
 * Tests para CentralNode — Micro-fase 3.1
 */

import {
  STATE_CONFIG,
  getCenterPosition,
  createCentralNodeGraphics,
  updateGlowUniforms,
  createGlowFilter,
} from '@/components/hub/CentralNode';
import type { AIState } from '@/components/hub/CentralNode';

jest.mock('pixi.js', () => {
  const mockGraphics = {
    circle: jest.fn().mockReturnThis(),
    fill: jest.fn().mockReturnThis(),
  };
  const makeFilter = () => ({
    resources: {
      uniforms: {
        uniforms: {
          uTime: 0,
          uPulseSpeed: 1.5,
          uGlowColor: new Float32Array([0, 0, 0]),
          uGlowIntensity: 0.8,
          uRadius: 0.35,
        },
      },
    },
  });
  return {
    Container: jest.fn(),
    Graphics: jest.fn(() => mockGraphics),
    Filter: jest.fn(() => makeFilter()),
    GlProgram: { from: jest.fn(() => ({})) },
  };
});

describe('CentralNode', () => {
  describe('STATE_CONFIG', () => {
    it('tiene configuración para los 4 estados', () => {
      expect(STATE_CONFIG).toHaveProperty('idle');
      expect(STATE_CONFIG).toHaveProperty('thinking');
      expect(STATE_CONFIG).toHaveProperty('error');
      expect(STATE_CONFIG).toHaveProperty('offline');
    });

    it('idle tiene glow azul con pulso lento', () => {
      expect(STATE_CONFIG.idle.color).toBe(0x1e90ff);
      expect(STATE_CONFIG.idle.pulseSpeed).toBe(1.5);
    });

    it('thinking tiene pulso rápido y alta intensidad', () => {
      expect(STATE_CONFIG.thinking.pulseSpeed).toBe(4.0);
      expect(STATE_CONFIG.thinking.intensity).toBe(1.2);
    });

    it('error tiene color rojo y pulso muy rápido', () => {
      expect(STATE_CONFIG.error.color).toBe(0xff4444);
      expect(STATE_CONFIG.error.pulseSpeed).toBe(6.0);
    });

    it('offline tiene baja intensidad', () => {
      expect(STATE_CONFIG.offline.intensity).toBe(0.3);
      expect(STATE_CONFIG.offline.pulseSpeed).toBe(0.5);
    });
  });

  describe('getCenterPosition', () => {
    it('calcula el centro del canvas', () => {
      const pos = getCenterPosition(1920, 1080);
      expect(pos.x).toBe(960);
      expect(pos.y).toBe(540);
    });

    it('maneja dimensiones impares', () => {
      const pos = getCenterPosition(1921, 1081);
      expect(pos.x).toBe(960.5);
      expect(pos.y).toBe(540.5);
    });

    it('maneja canvas pequeño', () => {
      const pos = getCenterPosition(800, 600);
      expect(pos.x).toBe(400);
      expect(pos.y).toBe(300);
    });
  });

  describe('createCentralNodeGraphics', () => {
    it('crea un gráfico circular con radio dado', () => {
      const g = createCentralNodeGraphics(50, 0x1e90ff);
      expect(g.circle).toHaveBeenCalledWith(0, 0, 50);
    });

    it('aplica el color dado', () => {
      const g = createCentralNodeGraphics(60, 0xff4444);
      expect(g.fill).toHaveBeenCalledWith({ color: 0xff4444 });
    });
  });

  describe('createGlowFilter', () => {
    it('crea un filtro sin errores', () => {
      const filter = createGlowFilter();
      expect(filter).toBeDefined();
    });

    it('el filtro tiene uniforms iniciales', () => {
      const filter = createGlowFilter();
      expect(filter.resources.uniforms.uniforms.uRadius).toBe(0.35);
    });
  });

  describe('updateGlowUniforms', () => {
    it('actualiza uniforms para estado idle', () => {
      const filter = createGlowFilter();
      updateGlowUniforms(filter, 'idle', 1.0);
      const u = filter.resources.uniforms.uniforms;
      expect(u.uTime).toBe(1.0);
      expect(u.uPulseSpeed).toBe(1.5);
      expect(u.uGlowIntensity).toBe(0.8);
    });

    it('actualiza uniforms para estado thinking', () => {
      const filter = createGlowFilter();
      updateGlowUniforms(filter, 'thinking', 2.0);
      const u = filter.resources.uniforms.uniforms;
      expect(u.uPulseSpeed).toBe(4.0);
      expect(u.uGlowIntensity).toBe(1.2);
    });

    it('actualiza uniforms para estado error', () => {
      const filter = createGlowFilter();
      updateGlowUniforms(filter, 'error', 3.0);
      const u = filter.resources.uniforms.uniforms;
      expect(u.uPulseSpeed).toBe(6.0);
    });

    it('actualiza uniforms para estado offline', () => {
      const filter = createGlowFilter();
      updateGlowUniforms(filter, 'offline', 0.0);
      const u = filter.resources.uniforms.uniforms;
      expect(u.uPulseSpeed).toBe(0.5);
      expect(u.uGlowIntensity).toBe(0.3);
    });

    it('cambia correctamente entre todos los estados', () => {
      const filter = createGlowFilter();
      const states: AIState[] = ['idle', 'thinking', 'error', 'offline'];
      states.forEach((state, i) => {
        updateGlowUniforms(filter, state, i);
        const u = filter.resources.uniforms.uniforms;
        expect(u.uPulseSpeed).toBe(STATE_CONFIG[state].pulseSpeed);
        expect(u.uGlowIntensity).toBe(STATE_CONFIG[state].intensity);
      });
    });
  });
});
