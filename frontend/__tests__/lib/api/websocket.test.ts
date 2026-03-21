/**
 * Tests para WebSocket Client — Micro-fase 3.12
 */

import { WSClient, DEFAULT_CONFIG } from '@/lib/api/websocket';
import type { WSMessage } from '@/lib/api/websocket';

// Mock Kill Switch
jest.mock('@/hooks/useKeyboardShortcuts', () => ({
  getKillSwitchState: jest.fn(() => ({ isActive: false, toggledAt: null })),
}));

import { getKillSwitchState } from '@/hooks/useKeyboardShortcuts';
const mockGetKillSwitch = getKillSwitchState as jest.Mock;

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;

  send = jest.fn();
  close = jest.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  });

  simulateOpen(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: WSMessage): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  simulateError(): void {
    this.onerror?.();
  }
}

let mockWS: MockWebSocket;

beforeAll(() => {
  (global as any).WebSocket = jest.fn().mockImplementation(() => {
    mockWS = new MockWebSocket();
    return mockWS;
  });
  (global.WebSocket as any).OPEN = 1;
});

describe('WSClient', () => {
  let client: WSClient;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
    mockGetKillSwitch.mockReturnValue({ isActive: false, toggledAt: null });
    client = new WSClient({ url: 'ws://test:8000/ws' });
  });

  afterEach(() => {
    client.destroy();
    jest.useRealTimers();
  });

  describe('connect', () => {
    it('crea WebSocket y se conecta', () => {
      client.connect();
      expect(global.WebSocket).toHaveBeenCalledWith('ws://test:8000/ws');
    });

    it('status cambia a connecting', () => {
      client.connect();
      expect(client.getStatus()).toBe('connecting');
    });

    it('status cambia a connected al abrir', () => {
      client.connect();
      mockWS.simulateOpen();
      expect(client.getStatus()).toBe('connected');
    });

    it('no crea segunda conexion si ya esta abierta', () => {
      client.connect();
      mockWS.simulateOpen();
      const callsBefore = (global.WebSocket as jest.Mock).mock.calls.length;
      client.connect();
      expect((global.WebSocket as jest.Mock).mock.calls.length).toBe(callsBefore);
    });

    it('status cambia a error si WebSocket lanza excepcion', () => {
      (global.WebSocket as jest.Mock).mockImplementationOnce(() => {
        throw new Error('connection refused');
      });
      client.connect();
      expect(client.getStatus()).toBe('error');
    });
  });

  describe('event handlers', () => {
    it('registra y ejecuta handler para chat.message', () => {
      const handler = jest.fn();
      client.on('chat.message', handler);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'chat.message',
        payload: { text: 'hello' },
        timestamp: Date.now(),
      });
      expect(handler).toHaveBeenCalledWith({ text: 'hello' });
    });

    it('registra handler para gpu.update', () => {
      const handler = jest.fn();
      client.on('gpu.update', handler);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'gpu.update',
        payload: { vramUsed: 1500 },
        timestamp: Date.now(),
      });
      expect(handler).toHaveBeenCalledWith({ vramUsed: 1500 });
    });

    it('multiples handlers para el mismo tipo', () => {
      const h1 = jest.fn();
      const h2 = jest.fn();
      client.on('node.event', h1);
      client.on('node.event', h2);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'node.event',
        payload: { nodeId: 'abc' },
        timestamp: Date.now(),
      });
      expect(h1).toHaveBeenCalled();
      expect(h2).toHaveBeenCalled();
    });

    it('unsubscribe funciona', () => {
      const handler = jest.fn();
      const unsub = client.on('gpu.update', handler);
      unsub();
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'gpu.update',
        payload: {},
        timestamp: Date.now(),
      });
      expect(handler).not.toHaveBeenCalled();
    });

    it('ignora mensaje con JSON invalido', () => {
      client.connect();
      mockWS.simulateOpen();
      expect(() => {
        mockWS.onmessage?.({ data: 'not-json' });
      }).not.toThrow();
    });
  });

  describe('Kill Switch integration', () => {
    it('ignora chat.message cuando Kill Switch esta activo', () => {
      mockGetKillSwitch.mockReturnValue({ isActive: true, toggledAt: Date.now() });
      const handler = jest.fn();
      client.on('chat.message', handler);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'chat.message',
        payload: { text: 'hello' },
        timestamp: Date.now(),
      });
      expect(handler).not.toHaveBeenCalled();
    });

    it('ignora gpu.update cuando Kill Switch esta activo', () => {
      mockGetKillSwitch.mockReturnValue({ isActive: true, toggledAt: Date.now() });
      const handler = jest.fn();
      client.on('gpu.update', handler);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({ type: 'gpu.update', payload: {}, timestamp: Date.now() });
      expect(handler).not.toHaveBeenCalled();
    });

    it('permite system.status incluso con Kill Switch activo', () => {
      mockGetKillSwitch.mockReturnValue({ isActive: true, toggledAt: Date.now() });
      const handler = jest.fn();
      client.on('system.status', handler);
      client.connect();
      mockWS.simulateOpen();

      mockWS.simulateMessage({
        type: 'system.status',
        payload: { ok: true },
        timestamp: Date.now(),
      });
      expect(handler).toHaveBeenCalledWith({ ok: true });
    });
  });

  describe('reconnect', () => {
    it('intenta reconectar al desconectarse', () => {
      client.connect();
      mockWS.simulateOpen();
      const wsCallCount = (global.WebSocket as jest.Mock).mock.calls.length;

      mockWS.simulateClose();
      jest.advanceTimersByTime(DEFAULT_CONFIG.baseDelayMs + 100);

      expect((global.WebSocket as jest.Mock).mock.calls.length).toBeGreaterThan(wsCallCount);
    });

    it('no reconecta despues de disconnect() manual', () => {
      client.connect();
      mockWS.simulateOpen();
      client.disconnect();
      const wsCallCount = (global.WebSocket as jest.Mock).mock.calls.length;

      jest.advanceTimersByTime(DEFAULT_CONFIG.baseDelayMs * 10);
      expect((global.WebSocket as jest.Mock).mock.calls.length).toBe(wsCallCount);
    });

    it('incrementa reconnectAttempts', () => {
      client.connect();
      mockWS.simulateOpen();
      mockWS.simulateClose();
      expect(client.getReconnectAttempts()).toBe(1);
    });

    it('resetea reconnectAttempts al reconectar exitosamente', () => {
      client.connect();
      mockWS.simulateOpen();
      mockWS.simulateClose();
      jest.advanceTimersByTime(DEFAULT_CONFIG.baseDelayMs + 100);
      mockWS.simulateOpen();
      expect(client.getReconnectAttempts()).toBe(0);
    });
  });

  describe('status listeners', () => {
    it('notifica cambio a connecting', () => {
      const listener = jest.fn();
      client.onStatusChange(listener);
      client.connect();
      expect(listener).toHaveBeenCalledWith('connecting');
    });

    it('notifica cambio a connected', () => {
      const listener = jest.fn();
      client.onStatusChange(listener);
      client.connect();
      mockWS.simulateOpen();
      expect(listener).toHaveBeenCalledWith('connected');
    });

    it('unsubscribe funciona', () => {
      const listener = jest.fn();
      const unsub = client.onStatusChange(listener);
      unsub();
      client.connect();
      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('send', () => {
    it('envia mensaje serializado', () => {
      client.connect();
      mockWS.simulateOpen();

      const msg: WSMessage = {
        type: 'chat.message',
        payload: { text: 'test' },
        timestamp: 12345,
      };
      client.send(msg);
      expect(mockWS.send).toHaveBeenCalledWith(JSON.stringify(msg));
    });

    it('no lanza si no esta conectado', () => {
      expect(() => {
        client.send({ type: 'chat.message', payload: {}, timestamp: Date.now() });
      }).not.toThrow();
    });
  });

  describe('disconnect y destroy', () => {
    it('disconnect cambia status a disconnected', () => {
      client.connect();
      mockWS.simulateOpen();
      client.disconnect();
      expect(client.getStatus()).toBe('disconnected');
    });

    it('destroy limpia todo sin lanzar error', () => {
      const handler = jest.fn();
      client.on('chat.message', handler);
      client.connect();
      mockWS.simulateOpen();
      expect(() => client.destroy()).not.toThrow();
    });
  });

  describe('DEFAULT_CONFIG', () => {
    it('maxReconnectAttempts es 10', () => {
      expect(DEFAULT_CONFIG.maxReconnectAttempts).toBe(10);
    });

    it('baseDelayMs es 1000ms', () => {
      expect(DEFAULT_CONFIG.baseDelayMs).toBe(1000);
    });

    it('maxDelayMs es 30000ms', () => {
      expect(DEFAULT_CONFIG.maxDelayMs).toBe(30000);
    });

    it('url apunta a localhost:8000', () => {
      expect(DEFAULT_CONFIG.url).toContain('localhost:8000');
    });
  });
});
