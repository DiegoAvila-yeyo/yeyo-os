/**
 * YeyoOS — Orbital Layout Engine
 * Micro-fase 3.3 — Capa 3: Cuerpo
 *
 * Posiciona nodos satélite en círculos concéntricos alrededor
 * del nodo central. Detección de colisiones y animación spring.
 */

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LayoutResult {
  id: string;
  targetX: number;
  targetY: number;
  ring: number;
}

export interface OrbitalConfig {
  centerX: number;
  centerY: number;
  firstRingRadius: number;
  ringSpacing: number;
  maxNodesPerRing: number;
  nodeMinSpacing: number;
}

export const DEFAULT_CONFIG: OrbitalConfig = {
  centerX: 960,
  centerY: 540,
  firstRingRadius: 180,
  ringSpacing: 120,
  maxNodesPerRing: 8,
  nodeMinSpacing: 20,
};

export function calculateOrbitalPositions(
  nodeIds: string[],
  config: Partial<OrbitalConfig> = {}
): LayoutResult[] {
  const cfg = { ...DEFAULT_CONFIG, ...config };
  const results: LayoutResult[] = [];

  if (nodeIds.length === 0) return results;

  let nodeIndex = 0;
  let ring = 0;

  while (nodeIndex < nodeIds.length) {
    const radius = cfg.firstRingRadius + ring * cfg.ringSpacing;
    const circumference = 2 * Math.PI * radius;
    const maxForRing = Math.min(
      cfg.maxNodesPerRing + ring * 2,
      Math.floor(circumference / (cfg.nodeMinSpacing + 140))
    );
    const nodesInRing = Math.min(maxForRing, nodeIds.length - nodeIndex);
    const angleStep = (2 * Math.PI) / nodesInRing;
    const startAngle = -Math.PI / 2;

    for (let i = 0; i < nodesInRing; i++) {
      const angle = startAngle + i * angleStep;
      results.push({
        id: nodeIds[nodeIndex],
        targetX: cfg.centerX + Math.cos(angle) * radius,
        targetY: cfg.centerY + Math.sin(angle) * radius,
        ring,
      });
      nodeIndex++;
    }
    ring++;
  }

  return results;
}

export function detectCollisions(
  nodes: LayoutNode[],
  minSpacing: number = 20
): Array<[string, string]> {
  const collisions: Array<[string, string]> = [];

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];

      const overlapX = Math.abs(a.x - b.x) < (a.width + b.width) / 2 + minSpacing;
      const overlapY = Math.abs(a.y - b.y) < (a.height + b.height) / 2 + minSpacing;

      if (overlapX && overlapY) {
        collisions.push([a.id, b.id]);
      }
    }
  }

  return collisions;
}

export function resolveCollisions(
  nodes: LayoutNode[],
  minSpacing: number = 20
): LayoutNode[] {
  const resolved = nodes.map((n) => ({ ...n }));
  const maxIterations = 50;

  for (let iter = 0; iter < maxIterations; iter++) {
    let hasCollision = false;

    for (let i = 0; i < resolved.length; i++) {
      for (let j = i + 1; j < resolved.length; j++) {
        const a = resolved[i];
        const b = resolved[j];

        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const minDistX = (a.width + b.width) / 2 + minSpacing;
        const minDistY = (a.height + b.height) / 2 + minSpacing;

        if (Math.abs(dx) < minDistX && Math.abs(dy) < minDistY) {
          hasCollision = true;
          const pushX = ((minDistX - Math.abs(dx)) / 2) * Math.sign(dx || 1);
          const pushY = ((minDistY - Math.abs(dy)) / 2) * Math.sign(dy || 1);

          a.x -= pushX;
          a.y -= pushY;
          b.x += pushX;
          b.y += pushY;
        }
      }
    }

    if (!hasCollision) break;
  }

  return resolved;
}

export interface SpringState {
  x: number;
  y: number;
  vx: number;
  vy: number;
  targetX: number;
  targetY: number;
  done: boolean;
}

export const SPRING_STIFFNESS = 0.12;
export const SPRING_DAMPING = 0.75;
const SETTLE_THRESHOLD = 0.5;

export function createSpringState(
  currentX: number,
  currentY: number,
  targetX: number,
  targetY: number
): SpringState {
  return {
    x: currentX,
    y: currentY,
    vx: 0,
    vy: 0,
    targetX,
    targetY,
    done: false,
  };
}

export function updateSpring(state: SpringState): SpringState {
  if (state.done) return state;

  const dx = state.targetX - state.x;
  const dy = state.targetY - state.y;

  const ax = dx * SPRING_STIFFNESS;
  const ay = dy * SPRING_STIFFNESS;

  const vx = (state.vx + ax) * SPRING_DAMPING;
  const vy = (state.vy + ay) * SPRING_DAMPING;

  const x = state.x + vx;
  const y = state.y + vy;

  const done =
    Math.abs(dx) < SETTLE_THRESHOLD &&
    Math.abs(dy) < SETTLE_THRESHOLD &&
    Math.abs(vx) < SETTLE_THRESHOLD &&
    Math.abs(vy) < SETTLE_THRESHOLD;

  return {
    x: done ? state.targetX : x,
    y: done ? state.targetY : y,
    vx: done ? 0 : vx,
    vy: done ? 0 : vy,
    targetX: state.targetX,
    targetY: state.targetY,
    done,
  };
}
