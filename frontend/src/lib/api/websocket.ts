/**
 * YeyoOS — WebSocket Client
 * Micro-fase 3.12 — Capa 3: Cuerpo
 *
 * Cliente WebSocket con auto-reconnect exponential backoff.
 * Conecta al backend (Capa 1.7) para updates en tiempo real.
 */

import { getKillSwitchState } from '@/hooks/useKeyboardShortcuts';

export type WSEventType = 'chat.message' | 'system.status' | 'gpu.update' | 'node.event';

export interface WSMessage {
  type: WSEventType;
  payload: unknown;
  timestamp: number;
}

export type WSEventHandler = (payload: unknown) => void;
export type WSConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
export type WSStatusListener = (status: WSConnectionStatus) => void;

export interface WSClientConfig {
  url: string;
  maxReconnectAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

export const DEFAULT_CONFIG: Required<WSClientConfig> = {
  url: 'ws://localhost:8000/ws',
  maxReconnectAttempts: 10,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
};

export class WSClient {
  private ws: WebSocket | null = null;
  private config: Required<WSClientConfig>;
  private handlers: Map<WSEventType, Set<WSEventHandler>> = new Map();
  private statusListeners: Set<WSStatusListener> = new Set();
  private reconnectAttempts: number = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private status: WSConnectionStatus = 'disconnected';
  private manualClose: boolean = false;

  constructor(config: Partial<WSClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  public connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.manualClose = false;
    this.setStatus('connecting');

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventListeners();
    } catch {
      this.setStatus('error');
      this.scheduleReconnect();
    }
  }

  private setupEventListeners(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus('connected');
    };

    this.ws.onclose = () => {
      this.setStatus('disconnected');
      if (!this.manualClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.setStatus('error');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.dispatchMessage(message);
      } catch {
        console.warn('[YeyoOS WS] Failed to parse message:', event.data);
      }
    };
  }

  private dispatchMessage(message: WSMessage): void {
    const killSwitch = getKillSwitchState();
    if (killSwitch.isActive && message.type !== 'system.status') {
      return;
    }

    const handlers = this.handlers.get(message.type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message.payload);
        } catch (err) {
          console.error(`[YeyoOS WS] Error in handler for ${message.type}:`, err);
        }
      });
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.warn('[YeyoOS WS] Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(
      this.config.baseDelayMs * Math.pow(2, this.reconnectAttempts),
      this.config.maxDelayMs
    );

    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private setStatus(status: WSConnectionStatus): void {
    this.status = status;
    this.statusListeners.forEach((listener) => {
      try {
        listener(status);
      } catch {
        // ignore listener errors
      }
    });
  }

  public on(type: WSEventType, handler: WSEventHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  public onStatusChange(listener: WSStatusListener): () => void {
    this.statusListeners.add(listener);
    return () => {
      this.statusListeners.delete(listener);
    };
  }

  public getStatus(): WSConnectionStatus {
    return this.status;
  }

  public getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  public send(message: WSMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[YeyoOS WS] Cannot send: not connected');
      return;
    }
    this.ws.send(JSON.stringify(message));
  }

  public disconnect(): void {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('disconnected');
  }

  public destroy(): void {
    this.disconnect();
    this.handlers.clear();
    this.statusListeners.clear();
  }
}
