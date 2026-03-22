/**
 * YeyoOS — PackageManager Component
 * Micro-fase 4.12 — Capa 4: Sistema Nervioso
 *
 * Panel principal de gestión de paquetes.
 */

import React, { useState, useCallback } from 'react';
import { PackageCard, PackageInfo } from './PackageCard';
import { PermissionDialog, PermissionRequest } from './PermissionDialog';
import { UpdateNotification, UpdateInfo } from './UpdateNotification';


interface PackageManagerProps {
  packages: PackageInfo[];
  updates?: UpdateInfo[];
  onInstall?: (file: File) => Promise<void>;
  onUninstall?: (name: string) => Promise<void>;
  onUpdate?: (name: string) => Promise<void>;
  onPermissionsChange?: (name: string, granted: string[], denied: string[]) => Promise<void>;
}

export function PackageManager({
  packages,
  updates = [],
  onInstall,
  onUninstall,
  onUpdate,
  onPermissionsChange,
}: PackageManagerProps) {
  const [permDialog, setPermDialog] = useState<{
    packageName: string;
    permissions: PermissionRequest[];
  } | null>(null);
  const [pendingUpdates, setPendingUpdates] = useState<UpdateInfo[]>(updates);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleUninstall = useCallback(async (name: string) => {
    if (!onUninstall) return;
    setIsLoading(true);
    try {
      await onUninstall(name);
    } finally {
      setIsLoading(false);
    }
  }, [onUninstall]);

  const handlePermissionsClick = useCallback((name: string) => {
    const permsDefaults: PermissionRequest[] = [
      { permission: 'memory.read', description: 'Leer datos de memoria', risk: 'low' },
      { permission: 'memory.write', description: 'Escribir en memoria', risk: 'medium' },
    ];
    setPermDialog({ packageName: name, permissions: permsDefaults });
  }, []);

  const handlePermConfirm = useCallback(
    async (granted: string[], denied: string[]) => {
      if (!permDialog || !onPermissionsChange) {
        setPermDialog(null);
        return;
      }
      await onPermissionsChange(permDialog.packageName, granted, denied);
      setPermDialog(null);
    },
    [permDialog, onPermissionsChange]
  );

  const handleUpdate = useCallback(
    async (packageName: string) => {
      if (!onUpdate) return;
      setIsLoading(true);
      try {
        await onUpdate(packageName);
        setPendingUpdates((prev) => prev.filter((u) => u.packageName !== packageName));
      } finally {
        setIsLoading(false);
      }
    },
    [onUpdate]
  );

  const handleDismissUpdate = useCallback((packageName: string) => {
    setPendingUpdates((prev) => prev.filter((u) => u.packageName !== packageName));
  }, []);

  const handleFileDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (!onInstall) return;
      const file = e.dataTransfer.files[0];
      if (file && file.name.endsWith('.ypkg')) {
        setIsLoading(true);
        try {
          await onInstall(file);
        } finally {
          setIsLoading(false);
        }
      }
    },
    [onInstall]
  );

  const handleFileInput = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!onInstall) return;
      const file = e.target.files?.[0];
      if (file) {
        setIsLoading(true);
        try {
          await onInstall(file);
        } finally {
          setIsLoading(false);
        }
      }
    },
    [onInstall]
  );

  return (
    <div className="p-6 space-y-6" data-testid="package-manager">
      <div className="flex items-center justify-between">
        <h1 className="text-white text-xl font-semibold">
          YeyoPKG — Gestor de Paquetes
        </h1>
        <span className="text-gray-400 text-sm">{packages.length} paquetes instalados</span>
      </div>

      {onInstall && (
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
            isDragOver
              ? 'border-blue-500 bg-blue-900/20'
              : 'border-gray-700 hover:border-gray-500'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleFileDrop}
          data-testid="install-dropzone"
        >
          <p className="text-gray-400 text-sm mb-1">
            Arrastra un archivo <span className="font-mono text-blue-300">.ypkg</span> aquí
          </p>
          <label className="cursor-pointer text-blue-400 hover:text-blue-300 text-xs underline">
            o selecciona un archivo
            <input
              type="file"
              accept=".ypkg"
              className="hidden"
              onChange={handleFileInput}
              data-testid="file-input"
            />
          </label>
        </div>
      )}

      {packages.length === 0 ? (
        <div className="text-center py-12 text-gray-500" data-testid="empty-state">
          No hay paquetes instalados
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="packages-grid">
          {packages.map((pkg) => (
            <PackageCard
              key={pkg.name}
              package={pkg}
              onUninstall={onUninstall ? handleUninstall : undefined}
              onPermissions={handlePermissionsClick}
            />
          ))}
        </div>
      )}

      {permDialog && (
        <PermissionDialog
          packageName={permDialog.packageName}
          permissions={permDialog.permissions}
          onConfirm={handlePermConfirm}
          onCancel={() => setPermDialog(null)}
        />
      )}

      <UpdateNotification
        updates={pendingUpdates}
        onUpdate={handleUpdate}
        onDismiss={handleDismissUpdate}
      />
    </div>
  );
}

export default PackageManager;
