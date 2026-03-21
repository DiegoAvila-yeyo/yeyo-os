/**
 * Tests para Orbital Layout Engine — Micro-fase 3.3
 */

import {
  calculateOrbitalPositions,
  detectCollisions,
  resolveCollisions,
  createSpringState,
  updateSpring,
  DEFAULT_CONFIG,
} from '@/lib/layout/orbital';
import type { LayoutNode } from '@/lib/layout/orbital';

describe('Orbital Layout Engine', () => {
  describe('calculateOrbitalPositions', () => {
    it('retorna array vacío para 0 nodos', () => {
      expect(calculateOrbitalPositions([])).toEqual([]);
    });

    it('posiciona 1 nodo en el primer anillo', () => {
      const result = calculateOrbitalPositions(['node-1']);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('node-1');
      expect(result[0].ring).toBe(0);
    });

    it('posiciona nodo en el radio correcto del primer anillo', () => {
      const result = calculateOrbitalPositions(['node-1'], {
        centerX: 500,
        centerY: 500,
        firstRingRadius: 200,
      });
      const dx = result[0].targetX - 500;
      const dy = result[0].targetY - 500;
      const dist = Math.sqrt(dx * dx + dy * dy);
      expect(dist).toBeCloseTo(200, 0);
    });

    it('distribuye múltiples nodos uniformemente en el mismo anillo', () => {
      // Radio 300 para que quepan 4 nodos (circunferencia ~1885, max ~11 nodos)
      const result = calculateOrbitalPositions(['a', 'b', 'c', 'd'], {
        centerX: 0,
        centerY: 0,
        firstRingRadius: 300,
      });
      expect(result).toHaveLength(4);
      result.forEach((r) => {
        const dist = Math.sqrt(r.targetX ** 2 + r.targetY ** 2);
        expect(dist).toBeCloseTo(300, 0);
      });
    });

    it('usa segundo anillo cuando el primero está lleno', () => {
      const ids = Array.from({ length: 20 }, (_, i) => `node-${i}`);
      const result = calculateOrbitalPositions(ids);
      const rings = new Set(result.map((r) => r.ring));
      expect(rings.size).toBeGreaterThan(1);
    });

    it('asigna todos los nodos a algún anillo', () => {
      const ids = Array.from({ length: 15 }, (_, i) => `node-${i}`);
      const result = calculateOrbitalPositions(ids);
      expect(result).toHaveLength(15);
    });

    it('los nodos no se superponen (dist > 50px)', () => {
      const ids = Array.from({ length: 6 }, (_, i) => `node-${i}`);
      const result = calculateOrbitalPositions(ids);
      for (let i = 0; i < result.length; i++) {
        for (let j = i + 1; j < result.length; j++) {
          const dx = result[i].targetX - result[j].targetX;
          const dy = result[i].targetY - result[j].targetY;
          expect(Math.sqrt(dx * dx + dy * dy)).toBeGreaterThan(50);
        }
      }
    });

    it('respeta el centerX/centerY personalizado', () => {
      const result = calculateOrbitalPositions(['n'], { centerX: 100, centerY: 200 });
      const dx = result[0].targetX - 100;
      const dy = result[0].targetY - 200;
      const dist = Math.sqrt(dx * dx + dy * dy);
      expect(dist).toBeCloseTo(DEFAULT_CONFIG.firstRingRadius, 0);
    });
  });

  describe('detectCollisions', () => {
    it('no detecta colisiones con nodos separados', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 300, y: 300, width: 100, height: 50 },
      ];
      expect(detectCollisions(nodes)).toEqual([]);
    });

    it('detecta colisión cuando nodos se superponen', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 50, y: 20, width: 100, height: 50 },
      ];
      const collisions = detectCollisions(nodes);
      expect(collisions).toHaveLength(1);
      expect(collisions[0]).toEqual(['a', 'b']);
    });

    it('retorna vacío para array vacío', () => {
      expect(detectCollisions([])).toEqual([]);
    });

    it('detecta múltiples colisiones', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 10, y: 0, width: 100, height: 50 },
        { id: 'c', x: 20, y: 0, width: 100, height: 50 },
      ];
      const collisions = detectCollisions(nodes);
      expect(collisions.length).toBeGreaterThan(1);
    });
  });

  describe('resolveCollisions', () => {
    it('separa nodos que colisionan', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 10, y: 5, width: 100, height: 50 },
      ];
      const resolved = resolveCollisions(nodes);
      expect(detectCollisions(resolved)).toHaveLength(0);
    });

    it('no modifica nodos ya separados', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 500, y: 500, width: 100, height: 50 },
      ];
      const resolved = resolveCollisions(nodes);
      expect(resolved[0].x).toBe(0);
      expect(resolved[1].x).toBe(500);
    });

    it('no modifica el array original', () => {
      const nodes: LayoutNode[] = [
        { id: 'a', x: 0, y: 0, width: 100, height: 50 },
        { id: 'b', x: 10, y: 5, width: 100, height: 50 },
      ];
      const originalX0 = nodes[0].x;
      resolveCollisions(nodes);
      expect(nodes[0].x).toBe(originalX0);
    });
  });

  describe('Spring Animation', () => {
    it('crea spring con posición inicial y target', () => {
      const s = createSpringState(0, 0, 100, 100);
      expect(s.x).toBe(0);
      expect(s.y).toBe(0);
      expect(s.targetX).toBe(100);
      expect(s.targetY).toBe(100);
      expect(s.done).toBe(false);
    });

    it('se mueve hacia el target en primer update', () => {
      let s = createSpringState(0, 0, 100, 100);
      s = updateSpring(s);
      expect(s.x).toBeGreaterThan(0);
      expect(s.y).toBeGreaterThan(0);
    });

    it('converge al target después de múltiples updates', () => {
      let s = createSpringState(0, 0, 100, 100);
      for (let i = 0; i < 200; i++) {
        s = updateSpring(s);
        if (s.done) break;
      }
      expect(s.done).toBe(true);
      expect(s.x).toBe(100);
      expect(s.y).toBe(100);
    });

    it('no modifica spring ya completado', () => {
      let s = createSpringState(100, 100, 100, 100);
      s = { ...s, done: true };
      const updated = updateSpring(s);
      expect(updated.x).toBe(100);
      expect(updated.done).toBe(true);
    });

    it('spring en posición igual al target termina rápido', () => {
      let s = createSpringState(100, 100, 100, 100);
      s = updateSpring(s);
      expect(s.done).toBe(true);
    });
  });

  describe('DEFAULT_CONFIG', () => {
    it('firstRingRadius > 100', () => {
      expect(DEFAULT_CONFIG.firstRingRadius).toBeGreaterThan(100);
    });

    it('ringSpacing > 50', () => {
      expect(DEFAULT_CONFIG.ringSpacing).toBeGreaterThan(50);
    });

    it('maxNodesPerRing > 4', () => {
      expect(DEFAULT_CONFIG.maxNodesPerRing).toBeGreaterThan(4);
    });
  });
});
