/**
 * YeyoOS — UpdateNotification Component
 * Micro-fase 4.12 — Capa 4: Sistema Nervioso
 *
 * Notificación de actualizaciones disponibles para paquetes.
 */

import React from 'react';

export interface UpdateInfo {
  packageName: string;
  currentVersion: string;
  newVersion: string;
}

interface UpdateNotificationProps {
  updates: UpdateInfo[];
  onUpdate: (packageName: string) => void;
  onDismiss: (packageName: string) => void;
}

export function UpdateNotification({ updates, onUpdate, onDismiss }: UpdateNotificationProps) {
  if (updates.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-40 space-y-2 max-w-sm"
      data-testid="update-notification-container"
    >
      {updates.map((update) => (
        <div
          key={update.packageName}
          className="bg-gray-900 border border-blue-700 rounded-lg p-3 shadow-lg"
          data-testid={`update-notification-${update.packageName}`}
        >
          <div className="flex items-start justify-between mb-2">
            <div>
              <p className="text-white text-sm font-mono font-semibold">{update.packageName}</p>
              <p className="text-gray-400 text-xs">
                {update.currentVersion} → <span className="text-blue-300">{update.newVersion}</span>
              </p>
            </div>
            <button
              onClick={() => onDismiss(update.packageName)}
              className="text-gray-500 hover:text-gray-300 transition-colors text-lg leading-none"
              data-testid={`dismiss-update-${update.packageName}`}
              aria-label="Descartar actualización"
            >
              ×
            </button>
          </div>
          <button
            onClick={() => onUpdate(update.packageName)}
            className="w-full py-1.5 text-xs text-blue-300 border border-blue-800 hover:bg-blue-900/30 rounded transition-colors"
            data-testid={`update-button-${update.packageName}`}
          >
            Actualizar ahora
          </button>
        </div>
      ))}
    </div>
  );
}

export default UpdateNotification;
