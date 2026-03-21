/**
 * YeyoOS — Notifications (Toast Stack)
 * Micro-fase 3.9 — Capa 3: Cuerpo
 *
 * Stack de notificaciones toast en la esquina bottom-right.
 */

'use client';

import { useNotificationStore, type NotificationType } from '@/lib/store/notification-store';

export const TYPE_STYLES: Record<NotificationType, { bg: string; border: string; icon: string }> = {
  info: {
    bg: 'bg-blue-900/80',
    border: 'border-blue-500',
    icon: 'ℹ️',
  },
  success: {
    bg: 'bg-green-900/80',
    border: 'border-green-500',
    icon: '✅',
  },
  warning: {
    bg: 'bg-yellow-900/80',
    border: 'border-yellow-500',
    icon: '⚠️',
  },
  error: {
    bg: 'bg-red-900/80',
    border: 'border-red-500',
    icon: '❌',
  },
};

export default function Notifications() {
  const { notifications, removeNotification } = useNotificationStore();

  if (notifications.length === 0) return null;

  return (
    <div
      data-testid="notification-stack"
      className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-sm"
    >
      {notifications.map((notif) => {
        const style = TYPE_STYLES[notif.type];
        return (
          <div
            key={notif.id}
            data-testid={`notification-${notif.id}`}
            data-type={notif.type}
            className={`${style.bg} ${style.border} border rounded-lg px-4 py-3 shadow-lg backdrop-blur-sm animate-fade-in flex items-start gap-2`}
          >
            <span className="text-sm flex-shrink-0">{style.icon}</span>
            <p className="text-sm text-gray-200 flex-1">{notif.message}</p>
            <button
              data-testid={`close-${notif.id}`}
              onClick={() => removeNotification(notif.id)}
              className="text-gray-400 hover:text-white text-xs flex-shrink-0 ml-2"
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
