## ═══════════════════════════════════════
## MICRO-FASE 4.12 — Package Frontend UI
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.12-1 [VSCODE] — UI de gestión de paquetes

```
Estamos construyendo YeyoOS, un OS AI-nativo con interfaz Neural Hub. Esta es la micro-fase 4.12 de Capa 4 (Sistema Nervioso): crear la UI para gestionar paquetes y permisos.

CONTEXTO:
- Micro-fases 4.0-4.11 completadas: todo el backend de paquetes y API
- UI components: PackageManager, PermissionDialog, PackageCard, UpdateNotification
- PermissionDialog estilo Android/iOS — popup de solicitud de permisos
- Next.js + React + Tailwind (configurado en Capa 3)

Abre el directorio ~/yeyo-os/frontend en VS Code.

CREAR:

1. Crear directorio si no existe:
   mkdir -p src/components/packages

2. Crear archivo src/components/packages/PackageCard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/packages/PackageCard.tsx
   Contenido:

   /**
    * YeyoOS — PackageCard Component
    * Micro-fase 4.12 — Capa 4: Sistema Nervioso
    *
    * Muestra información de un paquete instalado.
    */

   'use client';

   import { type ReactNode } from 'react';

   export interface PackageCardProps {
     name: string;
     version: string;
     author: string;
     description: string;
     type: string;
     privilegeLevel: string;
     status: string;
     onUninstall?: (name: string) => void;
     onManagePermissions?: (name: string) => void;
   }

   const TYPE_ICONS: Record<string, string> = {
     node: '🔵',
     service: '⚙️',
     theme: '🎨',
     plugin: '🔌',
   };

   const LEVEL_COLORS: Record<string, string> = {
     L0: 'text-red-500',
     L1: 'text-orange-500',
     L2: 'text-blue-500',
     L3: 'text-yellow-500',
     L4: 'text-gray-400',
     L5: 'text-gray-600',
   };

   export default function PackageCard({
     name,
     version,
     author,
     description,
     type,
     privilegeLevel,
     status,
     onUninstall,
     onManagePermissions,
   }: PackageCardProps) {
     const icon = TYPE_ICONS[type] || '📦';
     const levelColor = LEVEL_COLORS[privilegeLevel] || 'text-gray-500';

     return (
       <div
         data-testid={`package-card-${name}`}
         className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-blue-500 transition-colors"
       >
         <div className="flex items-start justify-between">
           <div className="flex items-center gap-2">
             <span className="text-2xl">{icon}</span>
             <div>
               <h3 className="text-white font-medium">{name}</h3>
               <p className="text-gray-400 text-sm">v{version} · {author}</p>
             </div>
           </div>
           <span
             data-testid={`privilege-level-${name}`}
             className={`text-xs font-mono ${levelColor}`}
           >
             {privilegeLevel}
           </span>
         </div>

         <p className="text-gray-300 text-sm mt-2">{description}</p>

         <div className="flex items-center justify-between mt-3">
           <span
             data-testid={`package-status-${name}`}
             className={`text-xs px-2 py-0.5 rounded ${
               status === 'installed'
                 ? 'bg-green-900/50 text-green-400'
                 : 'bg-yellow-900/50 text-yellow-400'
             }`}
           >
             {status}
           </span>

           <div className="flex gap-2">
             {onManagePermissions && (
               <button
                 data-testid={`btn-permissions-${name}`}
                 onClick={() => onManagePermissions(name)}
                 className="text-xs text-blue-400 hover:text-blue-300"
               >
                 Permisos
               </button>
             )}
             {onUninstall && (
               <button
                 data-testid={`btn-uninstall-${name}`}
                 onClick={() => onUninstall(name)}
                 className="text-xs text-red-400 hover:text-red-300"
               >
                 Desinstalar
               </button>
             )}
           </div>
         </div>
       </div>
     );
   }

3. Crear archivo src/components/packages/PermissionDialog.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/packages/PermissionDialog.tsx
   Contenido:

   /**
    * YeyoOS — PermissionDialog Component
    * Micro-fase 4.12 — Capa 4: Sistema Nervioso
    *
    * Diálogo estilo Android/iOS para solicitar permisos.
    * ALLOWLIST: cada permiso se aprueba individualmente.
    */

   'use client';

   import { useState } from 'react';

   export interface PermissionDialogProps {
     packageName: string;
     permissions: string[];
     onAccept: (granted: string[], denied: string[]) => void;
     onCancel: () => void;
     isOpen: boolean;
   }

   const PERMISSION_LABELS: Record<string, string> = {
     'memory.read': '📖 Leer memoria compartida',
     'memory.write': '✏️ Escribir en memoria compartida',
     'gpu.inference': '🧠 Usar GPU para inferencia',
     'gpu.training': '🔥 Usar GPU para entrenamiento',
     'network.localhost': '🏠 Acceso a red local',
     'network.internet': '🌐 Acceso a internet',
     'filesystem.read': '📂 Leer archivos',
     'filesystem.write': '💾 Escribir archivos',
     'camera': '📷 Acceso a cámara',
     'microphone': '🎤 Acceso a micrófono',
     'clipboard': '📋 Acceso al portapapeles',
   };

   export default function PermissionDialog({
     packageName,
     permissions,
     onAccept,
     onCancel,
     isOpen,
   }: PermissionDialogProps) {
     const [selected, setSelected] = useState<Set<string>>(new Set());

     if (!isOpen) return null;

     const togglePermission = (perm: string) => {
       const next = new Set(selected);
       if (next.has(perm)) {
         next.delete(perm);
       } else {
         next.add(perm);
       }
       setSelected(next);
     };

     const handleAccept = () => {
       const granted = permissions.filter((p) => selected.has(p));
       const denied = permissions.filter((p) => !selected.has(p));
       onAccept(granted, denied);
     };

     return (
       <div
         data-testid="permission-dialog"
         className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
       >
         <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 border border-gray-700">
           <div className="text-center mb-4">
             <span className="text-4xl">🔒</span>
             <h2 className="text-white text-lg font-medium mt-2">
               Permisos solicitados
             </h2>
             <p className="text-gray-400 text-sm mt-1">
               <span className="text-blue-400 font-medium">{packageName}</span>
               {' '}solicita los siguientes permisos:
             </p>
           </div>

           <div className="space-y-2 mb-6">
             {permissions.map((perm) => (
               <label
                 key={perm}
                 data-testid={`perm-toggle-${perm}`}
                 className="flex items-center gap-3 p-2 rounded hover:bg-gray-700 cursor-pointer"
               >
                 <input
                   type="checkbox"
                   checked={selected.has(perm)}
                   onChange={() => togglePermission(perm)}
                   className="w-4 h-4 accent-blue-500"
                 />
                 <span className="text-gray-200 text-sm">
                   {PERMISSION_LABELS[perm] || perm}
                 </span>
               </label>
             ))}
           </div>

           <div className="flex gap-3">
             <button
               data-testid="btn-deny-all"
               onClick={onCancel}
               className="flex-1 px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm"
             >
               Denegar todo
             </button>
             <button
               data-testid="btn-accept"
               onClick={handleAccept}
               className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-sm"
             >
               Aceptar ({selected.size}/{permissions.length})
             </button>
           </div>
         </div>
       </div>
     );
   }

4. Crear archivo src/components/packages/UpdateNotification.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/packages/UpdateNotification.tsx
   Contenido:

   /**
    * YeyoOS — UpdateNotification Component
    * Micro-fase 4.12 — Capa 4: Sistema Nervioso
    *
    * Banner de notificación de actualizaciones disponibles.
    */

   'use client';

   export interface UpdateNotificationProps {
     updates: Array<{
       packageName: string;
       currentVersion: string;
       newVersion: string;
     }>;
     onUpdateAll?: () => void;
     onDismiss?: () => void;
     isVisible: boolean;
   }

   export default function UpdateNotification({
     updates,
     onUpdateAll,
     onDismiss,
     isVisible,
   }: UpdateNotificationProps) {
     if (!isVisible || updates.length === 0) return null;

     return (
       <div
         data-testid="update-notification"
         className="bg-blue-900/50 border border-blue-700 rounded-lg p-3 flex items-center justify-between"
       >
         <div className="flex items-center gap-2">
           <span className="text-xl">🔄</span>
           <div>
             <p className="text-blue-200 text-sm font-medium">
               {updates.length} actualización{updates.length > 1 ? 'es' : ''} disponible{updates.length > 1 ? 's' : ''}
             </p>
             <p className="text-blue-400/70 text-xs">
               {updates.map((u) => u.packageName).join(', ')}
             </p>
           </div>
         </div>
         <div className="flex gap-2">
           {onDismiss && (
             <button
               data-testid="btn-dismiss-updates"
               onClick={onDismiss}
               className="text-xs text-gray-400 hover:text-gray-300 px-2 py-1"
             >
               Después
             </button>
           )}
           {onUpdateAll && (
             <button
               data-testid="btn-update-all"
               onClick={onUpdateAll}
               className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-500"
             >
               Actualizar todo
             </button>
           )}
         </div>
       </div>
     );
   }

5. Crear archivo src/components/packages/PackageManager.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/packages/PackageManager.tsx
   Contenido:

   /**
    * YeyoOS — PackageManager Component
    * Micro-fase 4.12 — Capa 4: Sistema Nervioso
    *
    * Vista principal de gestión de paquetes.
    * Lista paquetes, instala, busca, gestiona permisos.
    */

   'use client';

   import { useState } from 'react';
   import PackageCard from './PackageCard';
   import PermissionDialog from './PermissionDialog';
   import UpdateNotification from './UpdateNotification';

   export interface PackageData {
     name: string;
     version: string;
     author: string;
     description: string;
     type: string;
     privilegeLevel: string;
     status: string;
     permissions?: string[];
   }

   export interface PackageManagerProps {
     packages: PackageData[];
     updates?: Array<{
       packageName: string;
       currentVersion: string;
       newVersion: string;
     }>;
     onInstall?: (file: File) => void;
     onUninstall?: (name: string) => void;
     onUpdateAll?: () => void;
     onPermissionChange?: (name: string, granted: string[], denied: string[]) => void;
   }

   export default function PackageManager({
     packages,
     updates = [],
     onInstall,
     onUninstall,
     onUpdateAll,
     onPermissionChange,
   }: PackageManagerProps) {
     const [search, setSearch] = useState('');
     const [permDialog, setPermDialog] = useState<{
       packageName: string;
       permissions: string[];
     } | null>(null);
     const [showUpdates, setShowUpdates] = useState(true);

     const filtered = packages.filter(
       (pkg) =>
         pkg.name.toLowerCase().includes(search.toLowerCase()) ||
         pkg.description.toLowerCase().includes(search.toLowerCase())
     );

     const handleManagePermissions = (name: string) => {
       const pkg = packages.find((p) => p.name === name);
       if (pkg?.permissions) {
         setPermDialog({ packageName: name, permissions: pkg.permissions });
       }
     };

     const handlePermissionAccept = (granted: string[], denied: string[]) => {
       if (permDialog && onPermissionChange) {
         onPermissionChange(permDialog.packageName, granted, denied);
       }
       setPermDialog(null);
     };

     return (
       <div data-testid="package-manager" className="p-4 space-y-4">
         <div className="flex items-center justify-between">
           <h1 className="text-white text-xl font-bold">📦 Paquetes</h1>
           {onInstall && (
             <label
               data-testid="btn-install"
               className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-500 cursor-pointer"
             >
               Instalar .ypkg
               <input
                 type="file"
                 accept=".ypkg"
                 className="hidden"
                 onChange={(e) => {
                   const file = e.target.files?.[0];
                   if (file) onInstall(file);
                 }}
               />
             </label>
           )}
         </div>

         <UpdateNotification
           updates={updates}
           onUpdateAll={onUpdateAll}
           onDismiss={() => setShowUpdates(false)}
           isVisible={showUpdates}
         />

         <input
           data-testid="search-input"
           type="text"
           placeholder="Buscar paquetes..."
           value={search}
           onChange={(e) => setSearch(e.target.value)}
           className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg text-sm placeholder-gray-400 border border-gray-600 focus:border-blue-500 focus:outline-none"
         />

         <div data-testid="package-list" className="grid gap-3">
           {filtered.length === 0 ? (
             <p className="text-gray-500 text-center py-8">
               No se encontraron paquetes
             </p>
           ) : (
             filtered.map((pkg) => (
               <PackageCard
                 key={pkg.name}
                 name={pkg.name}
                 version={pkg.version}
                 author={pkg.author}
                 description={pkg.description}
                 type={pkg.type}
                 privilegeLevel={pkg.privilegeLevel}
                 status={pkg.status}
                 onUninstall={onUninstall}
                 onManagePermissions={
                   pkg.permissions ? handleManagePermissions : undefined
                 }
               />
             ))
           )}
         </div>

         {permDialog && (
           <PermissionDialog
             packageName={permDialog.packageName}
             permissions={permDialog.permissions}
             onAccept={handlePermissionAccept}
             onCancel={() => setPermDialog(null)}
             isOpen={true}
           />
         )}
       </div>
     );
   }

6. Crear archivo src/components/packages/index.ts:

   Ruta: ~/yeyo-os/frontend/src/components/packages/index.ts
   Contenido:

   export { default as PackageManager } from './PackageManager';
   export { default as PackageCard } from './PackageCard';
   export { default as PermissionDialog } from './PermissionDialog';
   export { default as UpdateNotification } from './UpdateNotification';

7. Crear archivo __tests__/components/packages/PackageUI.test.tsx:

   Ruta: ~/yeyo-os/frontend/__tests__/components/packages/PackageUI.test.tsx
   Contenido:

   /**
    * Tests para Package Frontend UI — Micro-fase 4.12
    */

   import { render, screen, fireEvent } from '@testing-library/react';
   import PackageCard from '@/components/packages/PackageCard';
   import PermissionDialog from '@/components/packages/PermissionDialog';
   import UpdateNotification from '@/components/packages/UpdateNotification';
   import PackageManager from '@/components/packages/PackageManager';
   import type { PackageData } from '@/components/packages/PackageManager';

   const SAMPLE_PACKAGE: PackageData = {
     name: 'test-node',
     version: '1.0.0',
     author: 'YeyoOS',
     description: 'Test node package',
     type: 'node',
     privilegeLevel: 'L2',
     status: 'installed',
     permissions: ['memory.read', 'gpu.inference'],
   };

   describe('PackageCard', () => {
     it('renderiza información del paquete', () => {
       render(
         <PackageCard
           name="test-node"
           version="1.0.0"
           author="YeyoOS"
           description="Test node"
           type="node"
           privilegeLevel="L2"
           status="installed"
         />
       );
       expect(screen.getByText('test-node')).toBeInTheDocument();
       expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
       expect(screen.getByText('installed')).toBeInTheDocument();
     });

     it('muestra nivel de privilegio', () => {
       render(
         <PackageCard
           name="test-node"
           version="1.0.0"
           author="YeyoOS"
           description="Test"
           type="node"
           privilegeLevel="L5"
           status="installed"
         />
       );
       expect(screen.getByTestId('privilege-level-test-node')).toHaveTextContent('L5');
     });

     it('botón desinstalar llama callback', () => {
       const onUninstall = jest.fn();
       render(
         <PackageCard
           name="test-node"
           version="1.0.0"
           author="YeyoOS"
           description="Test"
           type="node"
           privilegeLevel="L2"
           status="installed"
           onUninstall={onUninstall}
         />
       );
       fireEvent.click(screen.getByTestId('btn-uninstall-test-node'));
       expect(onUninstall).toHaveBeenCalledWith('test-node');
     });
   });

   describe('PermissionDialog', () => {
     it('muestra diálogo cuando isOpen es true', () => {
       render(
         <PermissionDialog
           packageName="test-pkg"
           permissions={['memory.read', 'gpu.inference']}
           onAccept={jest.fn()}
           onCancel={jest.fn()}
           isOpen={true}
         />
       );
       expect(screen.getByTestId('permission-dialog')).toBeInTheDocument();
       expect(screen.getByText('test-pkg')).toBeInTheDocument();
     });

     it('no muestra diálogo cuando isOpen es false', () => {
       render(
         <PermissionDialog
           packageName="test-pkg"
           permissions={['memory.read']}
           onAccept={jest.fn()}
           onCancel={jest.fn()}
           isOpen={false}
         />
       );
       expect(screen.queryByTestId('permission-dialog')).not.toBeInTheDocument();
     });

     it('botón denegar todo llama onCancel', () => {
       const onCancel = jest.fn();
       render(
         <PermissionDialog
           packageName="test-pkg"
           permissions={['memory.read']}
           onAccept={jest.fn()}
           onCancel={onCancel}
           isOpen={true}
         />
       );
       fireEvent.click(screen.getByTestId('btn-deny-all'));
       expect(onCancel).toHaveBeenCalled();
     });

     it('botón aceptar llama onAccept con seleccionados', () => {
       const onAccept = jest.fn();
       render(
         <PermissionDialog
           packageName="test-pkg"
           permissions={['memory.read', 'gpu.inference']}
           onAccept={onAccept}
           onCancel={jest.fn()}
           isOpen={true}
         />
       );
       fireEvent.click(screen.getByTestId('btn-accept'));
       expect(onAccept).toHaveBeenCalledWith([], ['memory.read', 'gpu.inference']);
     });
   });

   describe('UpdateNotification', () => {
     it('muestra notificación con updates', () => {
       render(
         <UpdateNotification
           updates={[
             { packageName: 'pkg-a', currentVersion: '1.0.0', newVersion: '2.0.0' },
           ]}
           isVisible={true}
         />
       );
       expect(screen.getByTestId('update-notification')).toBeInTheDocument();
       expect(screen.getByText(/1 actualización disponible/)).toBeInTheDocument();
     });

     it('no muestra cuando isVisible es false', () => {
       render(
         <UpdateNotification
           updates={[
             { packageName: 'pkg-a', currentVersion: '1.0.0', newVersion: '2.0.0' },
           ]}
           isVisible={false}
         />
       );
       expect(screen.queryByTestId('update-notification')).not.toBeInTheDocument();
     });

     it('no muestra cuando no hay updates', () => {
       render(
         <UpdateNotification
           updates={[]}
           isVisible={true}
         />
       );
       expect(screen.queryByTestId('update-notification')).not.toBeInTheDocument();
     });
   });

   describe('PackageManager', () => {
     it('renderiza lista de paquetes', () => {
       render(
         <PackageManager packages={[SAMPLE_PACKAGE]} />
       );
       expect(screen.getByTestId('package-manager')).toBeInTheDocument();
       expect(screen.getByText('test-node')).toBeInTheDocument();
     });

     it('campo de búsqueda filtra paquetes', () => {
       render(
         <PackageManager
           packages={[
             SAMPLE_PACKAGE,
             { ...SAMPLE_PACKAGE, name: 'other-pkg', description: 'Other' },
           ]}
         />
       );
       fireEvent.change(screen.getByTestId('search-input'), {
         target: { value: 'other' },
       });
       expect(screen.queryByText('test-node')).not.toBeInTheDocument();
       expect(screen.getByText('other-pkg')).toBeInTheDocument();
     });

     it('muestra mensaje vacío sin paquetes', () => {
       render(<PackageManager packages={[]} />);
       expect(screen.getByText(/No se encontraron paquetes/)).toBeInTheDocument();
     });

     it('botón instalar existe', () => {
       render(
         <PackageManager packages={[]} onInstall={jest.fn()} />
       );
       expect(screen.getByTestId('btn-install')).toBeInTheDocument();
     });
   });

8. Ejecutar tests:
   cd ~/yeyo-os/frontend
   npx jest __tests__/components/packages/PackageUI.test.tsx --no-cache

VERIFICAR:
- [ ] Archivos PackageCard, PermissionDialog, UpdateNotification, PackageManager existen
- [ ] PackageCard renderiza nombre, versión, nivel de privilegio, status
- [ ] PermissionDialog muestra popup estilo Android/iOS
- [ ] PermissionDialog permite seleccionar permisos individualmente (ALLOWLIST)
- [ ] UpdateNotification muestra banner de actualizaciones
- [ ] PackageManager lista paquetes, busca, instala
- [ ] Búsqueda filtra paquetes correctamente
- [ ] TODOS los tests pasan

SI FALLA:
- @testing-library/react no instalado: npm install --save-dev @testing-library/react
- Jest config: verificar que soporta JSX/TSX
- Import paths: verificar que @/ resuelve a src/

NO HACER:
- No conectar con la API real (eso es integración)
- No implementar lógica de estado global (Zustand ya está en Capa 3)
- No agregar animaciones complejas

GATE: UI de paquetes funcional, PermissionDialog ALLOWLIST, búsqueda, notificaciones de update, todos los tests pasan.
```
