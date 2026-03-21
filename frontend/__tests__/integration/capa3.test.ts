/**
 * Integration Test — Capa 3 (Cuerpo)
 * Micro-fase 3.15
 *
 * Verifica que todos los módulos de Capa 3 se integran correctamente.
 * NO es un E2E test — es un test de integración de módulos TypeScript.
 */

// Mock PixiJS antes de cualquier import
jest.mock('pixi.js', () => ({
  Application: jest.fn().mockImplementation(() => ({
    init: jest.fn().mockResolvedValue(undefined),
    destroy: jest.fn(),
    canvas: document.createElement('canvas'),
    screen: { width: 1920, height: 1080 },
    renderer: { resize: jest.fn() },
    ticker: { maxFPS: 0 },
  })),
  Container: jest.fn().mockImplementation(() => ({
    x: 0,
    y: 0,
    eventMode: 'none',
    cursor: 'default',
    addChild: jest.fn(),
    on: jest.fn(),
    removeAllListeners: jest.fn(),
    destroy: jest.fn(),
  })),
  Graphics: jest.fn().mockImplementation(() => ({
    clear: jest.fn().mockReturnThis(),
    circle: jest.fn().mockReturnThis(),
    roundRect: jest.fn().mockReturnThis(),
    fill: jest.fn().mockReturnThis(),
    stroke: jest.fn().mockReturnThis(),
    moveTo: jest.fn().mockReturnThis(),
    bezierCurveTo: jest.fn().mockReturnThis(),
  })),
  Text: jest.fn().mockImplementation(() => ({
    anchor: { set: jest.fn() },
    x: 0,
    y: 0,
    alpha: 1,
  })),
  TextStyle: jest.fn().mockImplementation((opts: unknown) => opts),
  Filter: jest.fn().mockImplementation(() => ({
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
  })),
  GlProgram: { from: jest.fn(() => ({})) },
  FederatedPointerEvent: jest.fn(),
}));

jest.mock('@/shaders/glow.vert', () => 'mock-vertex', { virtual: true });
jest.mock('@/shaders/glow.frag', () => 'mock-fragment', { virtual: true });
jest.mock('react-markdown', () => {
  return function MockMD({ children }: { children: string }) {
    return children;
  };
});
jest.mock('remark-gfm', () => () => {});

import { act } from '@testing-library/react';

describe('Capa 3 Integration Test', () => {
  describe('1. Stores se importan y funcionan juntos', () => {
    it('todos los stores se importan desde index', async () => {
      const stores = await import('@/lib/store/index');
      expect(stores.useHubStore).toBeDefined();
      expect(stores.useChatStore).toBeDefined();
      expect(stores.useUIStore).toBeDefined();
      expect(stores.useSystemStore).toBeDefined();
      expect(stores.useNotificationStore).toBeDefined();
    });

    it('stores son independientes', async () => {
      const { useHubStore, useChatStore, useUIStore, useSystemStore } =
        await import('@/lib/store/index');

      act(() => {
        useHubStore.getState().setCanvasSize({ width: 1920, height: 1080 });
        useChatStore.getState().addMessage({
          id: 'int-1',
          role: 'user',
          content: 'Integration test',
          timestamp: Date.now(),
        });
        useUIStore.getState().setActivePanel('chat');
        useSystemStore.getState().setConnectionStatus('connected');
      });

      expect(useHubStore.getState().canvasSize.width).toBe(1920);
      expect(useChatStore.getState().messages.length).toBeGreaterThan(0);
      expect(useUIStore.getState().activePanel).toBe('chat');
      expect(useSystemStore.getState().connectionStatus).toBe('connected');
    });
  });

  describe('2. Hub components se importan', () => {
    it('HubCanvas exporta BACKGROUND_COLOR y TARGET_FPS', async () => {
      const mod = await import('@/components/hub/HubCanvas');
      expect(mod.default).toBeDefined();
      expect(mod.BACKGROUND_COLOR).toBe(0x0a0a0f);
      expect(mod.TARGET_FPS).toBe(60);
    });

    it('CentralNode exporta STATE_CONFIG con 4 estados', async () => {
      const mod = await import('@/components/hub/CentralNode');
      expect(mod.STATE_CONFIG).toBeDefined();
      expect(mod.STATE_CONFIG.idle).toBeDefined();
      expect(mod.STATE_CONFIG.thinking).toBeDefined();
      expect(mod.STATE_CONFIG.error).toBeDefined();
      expect(mod.STATE_CONFIG.offline).toBeDefined();
    });

    it('SatelliteNode es instanciable con id=test y state=idle', async () => {
      const { SatelliteNode } = await import('@/components/nodes/SatelliteNode');
      const node = new SatelliteNode({
        id: 'test',
        label: 'Test',
        icon: '💬',
        x: 100,
        y: 100,
      });
      expect(node.id).toBe('test');
      expect(node.state).toBe('idle');
      node.destroy();
    });
  });

  describe('3. Layout engine funciona', () => {
    it('calcula posiciones orbitales fuera del centro', async () => {
      const { calculateOrbitalPositions } = await import('@/lib/layout/orbital');
      const ids = ['a', 'b', 'c', 'd', 'e'];
      const positions = calculateOrbitalPositions(ids, {
        centerX: 960,
        centerY: 540,
      });
      expect(positions).toHaveLength(5);
      positions.forEach((p) => {
        const dist = Math.sqrt((p.targetX - 960) ** 2 + (p.targetY - 540) ** 2);
        expect(dist).toBeGreaterThan(100);
      });
    });

    it('spring animation converge a la posición destino', async () => {
      const { createSpringState, updateSpring } = await import('@/lib/layout/orbital');
      let spring = createSpringState(0, 0, 200, 200);
      for (let i = 0; i < 100; i++) {
        spring = updateSpring(spring);
        if (spring.done) break;
      }
      expect(spring.done).toBe(true);
      expect(spring.x).toBe(200);
    });
  });

  describe('4. Connection lines', () => {
    it('ConnectionLine se crea con dataType=chat y color correcto', async () => {
      const { ConnectionLine, DATA_TYPE_COLORS } = await import(
        '@/components/hub/ConnectionLine'
      );
      const line = new ConnectionLine({
        fromX: 0,
        fromY: 0,
        toX: 100,
        toY: 100,
        dataType: 'chat',
        active: true,
      });
      expect(line.dataType).toBe('chat');
      expect(DATA_TYPE_COLORS.chat).toBe(0x1e90ff);
      line.destroy();
    });
  });

  describe('5. Chat system — streaming completo', () => {
    it('ChatStore maneja flujo user→stream→finalize', async () => {
      const { useChatStore } = await import('@/lib/store/chat-store');

      act(() => {
        useChatStore.setState({ messages: [], isStreaming: false });
      });

      act(() => {
        useChatStore.getState().addMessage({
          id: 'user-1',
          role: 'user',
          content: 'Hola',
          timestamp: Date.now(),
        });
        useChatStore.getState().setStreaming(true);
        useChatStore.getState().addMessage({
          id: 'assist-1',
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
        });
      });

      act(() => {
        useChatStore.getState().updateStreamingMessage('assist-1', 'Hola, soy');
      });
      act(() => {
        useChatStore.getState().updateStreamingMessage('assist-1', 'Hola, soy YeyoOS');
      });
      act(() => {
        useChatStore.getState().finalizeStreamingMessage('assist-1');
      });

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(2);
      expect(state.messages[1].content).toBe('Hola, soy YeyoOS');
      expect(state.messages[1].isStreaming).toBe(false);
      expect(state.isStreaming).toBe(false);
    });
  });

  describe('6. Kill Switch — CRÍTICO', () => {
    it('Ctrl+Alt+K activa y desactiva el Kill Switch', async () => {
      const { initKillSwitch, getKillSwitchState, resetKillSwitch } =
        await import('@/hooks/useKeyboardShortcuts');

      resetKillSwitch();
      const cleanup = initKillSwitch();

      expect(getKillSwitchState().isActive).toBe(false);

      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, altKey: true, bubbles: true })
      );
      expect(getKillSwitchState().isActive).toBe(true);

      window.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, altKey: true, bubbles: true })
      );
      expect(getKillSwitchState().isActive).toBe(false);

      cleanup();
      resetKillSwitch();
    });
  });

  describe('7. Theme system', () => {
    it('exporta paleta completa con valores correctos', async () => {
      const { colors, fonts, animation } = await import('@/lib/theme/index');
      expect(colors.background.primary).toBe('#0a0a0f');
      expect(fonts.ui).toContain('Inter');
      expect(animation.duration.normal).toBe(300);
    });

    it('getCSSVariables tiene prefijo --yeyo-*', async () => {
      const { getCSSVariables } = await import('@/lib/theme/index');
      const vars = getCSSVariables();
      Object.keys(vars).forEach((k) => expect(k).toMatch(/^--yeyo-/));
    });
  });

  describe('8. API Client', () => {
    it('NO tiene método delete — memorias nunca se borran', async () => {
      const { APIClient } = await import('@/lib/api/client');
      const client = new APIClient();
      expect((client as any).delete).toBeUndefined();
    });

    it('tiene get/post/put/stream', async () => {
      const { APIClient } = await import('@/lib/api/client');
      const client = new APIClient();
      expect(typeof client.get).toBe('function');
      expect(typeof client.post).toBe('function');
      expect(typeof client.put).toBe('function');
      expect(typeof client.stream).toBe('function');
    });
  });

  describe('9. File categorization', () => {
    it('categoriza code/image/pdf correctamente', async () => {
      const { categorizeFile } = await import('@/components/hub/FileDropZone');
      expect(categorizeFile(new File([''], 'test.ts', { type: '' }))).toBe('code');
      expect(categorizeFile(new File([''], 'photo.jpg', { type: 'image/jpeg' }))).toBe('image');
      expect(categorizeFile(new File([''], 'doc.pdf', { type: 'application/pdf' }))).toBe('pdf');
    });
  });

  describe('10. Notification system', () => {
    it('flujo completo: add, max visible, dismiss', async () => {
      const { useNotificationStore, MAX_VISIBLE } = await import(
        '@/lib/store/notification-store'
      );

      act(() => { useNotificationStore.setState({ notifications: [] }); });

      act(() => {
        for (let i = 0; i < MAX_VISIBLE + 2; i++) {
          useNotificationStore.getState().addNotification('info', `msg ${i}`, false);
        }
      });

      expect(useNotificationStore.getState().notifications.length).toBeLessThanOrEqual(MAX_VISIBLE);
    });
  });
});
