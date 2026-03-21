/**
 * YeyoOS — Store Index
 * Micro-fase 3.11 — Capa 3: Cuerpo
 *
 * Re-exporta todos los stores para import centralizado.
 */

export { useHubStore } from './hub-store';
export type { HubState, CanvasSize } from './hub-store';

export { useChatStore } from './chat-store';
export type { ChatState, ChatMessage } from './chat-store';

export { useUIStore } from './ui-store';
export type { UIState, ActivePanel, ThemeMode } from './ui-store';

export { useSystemStore } from './system-store';
export type {
  SystemState,
  ConnectionStatus,
  GPUStatus,
  ServiceHealth,
} from './system-store';

export { useNotificationStore } from './notification-store';
export type {
  NotificationState,
  NotificationType,
  Notification,
} from './notification-store';
