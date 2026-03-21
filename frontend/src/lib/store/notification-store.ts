/**
 * YeyoOS — Notification Store
 * Micro-fase 3.9 — Capa 3: Cuerpo
 */

import { create } from 'zustand';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  createdAt: number;
  autoDismiss: boolean;
}

export interface NotificationState {
  notifications: Notification[];
  maxVisible: number;
  addNotification: (type: NotificationType, message: string, autoDismiss?: boolean) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

export const MAX_VISIBLE = 5;
export const AUTO_DISMISS_MS = 5000;

function generateNotificationId(): string {
  return `notif-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  maxVisible: MAX_VISIBLE,

  addNotification: (type, message, autoDismiss = true) => {
    const id = generateNotificationId();
    const notification: Notification = {
      id,
      type,
      message,
      createdAt: Date.now(),
      autoDismiss,
    };

    set((state) => {
      const updated = [...state.notifications, notification];
      if (updated.length > MAX_VISIBLE) {
        return { notifications: updated.slice(-MAX_VISIBLE) };
      }
      return { notifications: updated };
    });

    if (autoDismiss) {
      setTimeout(() => {
        get().removeNotification(id);
      }, AUTO_DISMISS_MS);
    }

    return id;
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearAll: () => set({ notifications: [] }),
}));
