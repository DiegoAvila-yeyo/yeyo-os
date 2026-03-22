/**
 * YeyoOS — PermissionDialog Component
 * Micro-fase 4.12 — Capa 4: Sistema Nervioso
 *
 * ALLOWLIST: muestra los permisos solicitados por un paquete.
 * El usuario debe aprobar CADA permiso individualmente.
 * NO HAY opción "Aprobar todo" — cada permiso se decide por separado.
 */

import React, { useState } from 'react';

export interface PermissionRequest {
  permission: string;
  description: string;
  risk: 'low' | 'medium' | 'high';
}

interface PermissionDialogProps {
  packageName: string;
  permissions: PermissionRequest[];
  onConfirm: (granted: string[], denied: string[]) => void;
  onCancel: () => void;
}

const RISK_STYLES = {
  low: 'border-green-800 bg-green-900/20',
  medium: 'border-yellow-800 bg-yellow-900/20',
  high: 'border-red-800 bg-red-900/20',
};

const RISK_BADGE = {
  low: 'text-green-400',
  medium: 'text-yellow-400',
  high: 'text-red-400',
};

export function PermissionDialog({
  packageName,
  permissions,
  onConfirm,
  onCancel,
}: PermissionDialogProps) {
  const [grantedPerms, setGrantedPerms] = useState<Set<string>>(new Set());

  const togglePermission = (permission: string) => {
    setGrantedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(permission)) {
        next.delete(permission);
      } else {
        next.add(permission);
      }
      return next;
    });
  };

  const handleConfirm = () => {
    const granted = Array.from(grantedPerms);
    const denied = permissions
      .map((p) => p.permission)
      .filter((p) => !grantedPerms.has(p));
    onConfirm(granted, denied);
  };

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      data-testid="permission-dialog"
    >
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md p-6">
        <h2 className="text-white font-semibold text-lg mb-1">
          Permisos solicitados
        </h2>
        <p className="text-gray-400 text-sm mb-4">
          <span className="text-blue-300 font-mono">{packageName}</span> solicita los siguientes permisos.
          Aprueba solo los que consideres necesarios.
        </p>

        <div className="space-y-3 mb-6">
          {permissions.map((perm) => (
            <div
              key={perm.permission}
              className={`border rounded-lg p-3 cursor-pointer transition-all ${RISK_STYLES[perm.risk]} ${
                grantedPerms.has(perm.permission) ? 'ring-1 ring-blue-500' : ''
              }`}
              onClick={() => togglePermission(perm.permission)}
              data-testid={`permission-item-${perm.permission}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={grantedPerms.has(perm.permission)}
                    onChange={() => togglePermission(perm.permission)}
                    className="w-4 h-4 accent-blue-500"
                    data-testid={`permission-checkbox-${perm.permission}`}
                  />
                  <span className="text-white font-mono text-sm">{perm.permission}</span>
                </div>
                <span className={`text-xs font-bold uppercase ${RISK_BADGE[perm.risk]}`}>
                  {perm.risk}
                </span>
              </div>
              <p className="text-gray-400 text-xs mt-1 ml-6">{perm.description}</p>
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2 text-sm text-gray-300 border border-gray-600 hover:bg-gray-800 rounded-lg transition-colors"
            data-testid="cancel-button"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            className="flex-1 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            data-testid="confirm-button"
          >
            Confirmar ({grantedPerms.size} aprobados)
          </button>
        </div>
      </div>
    </div>
  );
}

export default PermissionDialog;
