/**
 * YeyoOS — PackageCard Component
 * Micro-fase 4.12 — Capa 4: Sistema Nervioso
 *
 * Muestra información de un paquete instalado.
 */

import React from 'react';

export interface PackageInfo {
  name: string;
  version: string;
  author: string;
  description: string;
  type: string;
  privilege_level: string;
  status: string;
  installed_at?: string;
}

interface PackageCardProps {
  package: PackageInfo;
  onUninstall?: (name: string) => void;
  onPermissions?: (name: string) => void;
}

const PRIVILEGE_COLORS: Record<string, string> = {
  L1: 'text-red-400',
  L2: 'text-yellow-400',
  L3: 'text-blue-400',
  L4: 'text-green-400',
  L5: 'text-purple-400',
};

const STATUS_COLORS: Record<string, string> = {
  installed: 'bg-green-900/50 text-green-300',
  updating: 'bg-yellow-900/50 text-yellow-300',
  error: 'bg-red-900/50 text-red-300',
};

export function PackageCard({ package: pkg, onUninstall, onPermissions }: PackageCardProps) {
  const privilegeColor = PRIVILEGE_COLORS[pkg.privilege_level] ?? 'text-gray-400';
  const statusStyle = STATUS_COLORS[pkg.status] ?? 'bg-gray-900/50 text-gray-300';

  return (
    <div
      className="bg-gray-900/80 border border-gray-700 rounded-lg p-4 hover:border-gray-500 transition-colors"
      data-testid="package-card"
      data-package-name={pkg.name}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-white font-mono font-semibold">{pkg.name}</span>
          <span className="text-gray-400 text-sm">v{pkg.version}</span>
          <span className={`text-xs font-bold ${privilegeColor}`}>{pkg.privilege_level}</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${statusStyle}`}>
          {pkg.status}
        </span>
      </div>

      <p className="text-gray-400 text-sm mb-3 line-clamp-2">{pkg.description}</p>

      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <span className="bg-gray-800 px-2 py-0.5 rounded">{pkg.type}</span>
        <span>by {pkg.author}</span>
      </div>

      <div className="flex gap-2">
        {onPermissions && (
          <button
            onClick={() => onPermissions(pkg.name)}
            className="flex-1 py-1.5 text-xs text-blue-300 border border-blue-800 hover:bg-blue-900/30 rounded transition-colors"
            data-testid="permissions-button"
          >
            Permisos
          </button>
        )}
        {onUninstall && (
          <button
            onClick={() => onUninstall(pkg.name)}
            className="flex-1 py-1.5 text-xs text-red-300 border border-red-800 hover:bg-red-900/30 rounded transition-colors"
            data-testid="uninstall-button"
          >
            Desinstalar
          </button>
        )}
      </div>
    </div>
  );
}

export default PackageCard;
