## ═══════════════════════════════════════
## MICRO-FASE 6.9 — Security Dashboard
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.9-1 [VSCODE] — Dashboard de seguridad en el frontend

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.9 de Capa 6 (Sistema Inmune): crear el dashboard de seguridad en el frontend para visualizar el estado de Guardian en tiempo real.

CONTEXTO:
- Micro-fases 6.0-6.8 completadas: Guardian completo, Anomaly, Auto-Response, Kill Switch, Snapshots, Backup, Anti-Ransomware, Honeypots, Firewall
- Frontend: Next.js 14 + Tailwind + Zustand
- Dashboard muestra en tiempo real: estado de Guardian, anomalías, alertas, Kill Switch, backups, honeypots
- WebSocket para actualizaciones en tiempo real
- Kill Switch toggle button prominente

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p frontend/src/components/security
   mkdir -p frontend/src/hooks

2. Crear archivo frontend/src/hooks/useGuardian.ts:

   Ruta: ~/yeyo-os/frontend/src/hooks/useGuardian.ts
   Contenido:

   /**
    * YeyoOS — Hook para Guardian API
    * Micro-fase 6.9 — Capa 6: Sistema Inmune
    *
    * Hook React para conectar con la API de Guardian en localhost:9090.
    * Polling cada 5 segundos para actualizar datos.
    */

   import { useState, useEffect, useCallback } from 'react';

   const GUARDIAN_API = 'http://localhost:9090';

   interface GuardianStatus {
     guardian: string;
     uptime_secs: number;
     heartbeat_count: number;
     resource_snapshot: ResourceSnapshot | null;
     active_alerts: number;
   }

   interface ResourceSnapshot {
     timestamp: string;
     cpu_usage_percent: number;
     ram_used_mb: number;
     ram_total_mb: number;
     ram_usage_percent: number;
     disk_used_gb: number;
     disk_total_gb: number;
     disk_usage_percent: number;
     process_count: number;
     network_rx_bytes: number;
     network_tx_bytes: number;
   }

   interface ResourceAlert {
     timestamp: string;
     level: string;
     resource: string;
     message: string;
     value: number;
     threshold: number;
   }

   interface HeartbeatInfo {
     timestamp: string;
     uptime_secs: number;
     beat_count: number;
     status: string;
   }

   interface UseGuardianReturn {
     status: GuardianStatus | null;
     alerts: ResourceAlert[];
     heartbeat: HeartbeatInfo | null;
     isConnected: boolean;
     isLoading: boolean;
     error: string | null;
     refresh: () => Promise<void>;
   }

   export function useGuardian(pollInterval: number = 5000): UseGuardianReturn {
     const [status, setStatus] = useState<GuardianStatus | null>(null);
     const [alerts, setAlerts] = useState<ResourceAlert[]>([]);
     const [heartbeat, setHeartbeat] = useState<HeartbeatInfo | null>(null);
     const [isConnected, setIsConnected] = useState(false);
     const [isLoading, setIsLoading] = useState(true);
     const [error, setError] = useState<string | null>(null);

     const fetchData = useCallback(async () => {
       try {
         const [statusRes, alertsRes, hbRes] = await Promise.all([
           fetch(`${GUARDIAN_API}/status`),
           fetch(`${GUARDIAN_API}/alerts`),
           fetch(`${GUARDIAN_API}/heartbeat`),
         ]);

         if (statusRes.ok) {
           setStatus(await statusRes.json());
           setIsConnected(true);
         }

         if (alertsRes.ok) {
           setAlerts(await alertsRes.json());
         }

         if (hbRes.ok) {
           setHeartbeat(await hbRes.json());
         }

         setError(null);
       } catch (err) {
         setIsConnected(false);
         setError('Guardian no disponible');
       } finally {
         setIsLoading(false);
       }
     }, []);

     const refresh = useCallback(async () => {
       setIsLoading(true);
       await fetchData();
     }, [fetchData]);

     useEffect(() => {
       fetchData();
       const interval = setInterval(fetchData, pollInterval);
       return () => clearInterval(interval);
     }, [fetchData, pollInterval]);

     return { status, alerts, heartbeat, isConnected, isLoading, error, refresh };
   }

3. Crear archivo frontend/src/components/security/KillSwitchButton.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/KillSwitchButton.tsx
   Contenido:

   /**
    * YeyoOS — Kill Switch Button
    * Micro-fase 6.9 — Capa 6: Sistema Inmune
    *
    * Botón prominente de Kill Switch.
    * Rojo = pausar toda la IA.
    * Verde = IA corriendo normalmente.
    */

   'use client';

   import React, { useState, useCallback } from 'react';

   interface KillSwitchButtonProps {
     isPaused: boolean;
     onToggle: () => Promise<void>;
     className?: string;
   }

   export default function KillSwitchButton({
     isPaused,
     onToggle,
     className = '',
   }: KillSwitchButtonProps) {
     const [isToggling, setIsToggling] = useState(false);

     const handleClick = useCallback(async () => {
       if (isToggling) return;

       const confirmed = window.confirm(
         isPaused
           ? '¿Reanudar toda la IA del sistema?'
           : '⚠️ ¿PAUSAR toda la IA del sistema? Esto detendrá todos los procesos de IA.'
       );

       if (!confirmed) return;

       setIsToggling(true);
       try {
         await onToggle();
       } finally {
         setIsToggling(false);
       }
     }, [isPaused, onToggle, isToggling]);

     return (
       <button
         onClick={handleClick}
         disabled={isToggling}
         className={`
           relative flex items-center gap-3 px-6 py-4 rounded-xl
           font-bold text-lg transition-all duration-300
           ${isPaused
             ? 'bg-red-600 hover:bg-red-700 text-white shadow-red-500/50 shadow-lg animate-pulse'
             : 'bg-green-600 hover:bg-green-700 text-white shadow-green-500/30 shadow-md'
           }
           ${isToggling ? 'opacity-50 cursor-wait' : 'cursor-pointer'}
           ${className}
         `}
         aria-label={isPaused ? 'Reanudar IA' : 'Pausar IA (Kill Switch)'}
       >
         <span className="text-2xl">
           {isPaused ? '🔴' : '🟢'}
         </span>

         <div className="flex flex-col items-start">
           <span className="text-xs uppercase tracking-wider opacity-80">
             Kill Switch
           </span>
           <span>
             {isToggling
               ? 'Procesando...'
               : isPaused
                 ? 'IA PAUSADA — Click para reanudar'
                 : 'IA Activa — Click para pausar'
             }
           </span>
         </div>

         {isPaused && (
           <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-400 rounded-full animate-ping" />
         )}
       </button>
     );
   }

4. Crear archivo frontend/src/components/security/SecurityDashboard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/SecurityDashboard.tsx
   Contenido:

   /**
    * YeyoOS — Security Dashboard
    * Micro-fase 6.9 — Capa 6: Sistema Inmune
    *
    * Dashboard principal de seguridad.
    * Muestra: estado Guardian, anomalías, alertas, Kill Switch,
    * backups, honeypots, firewall.
    */

   'use client';

   import React, { useState, useCallback } from 'react';
   import { useGuardian } from '../../hooks/useGuardian';
   import KillSwitchButton from './KillSwitchButton';

   const GUARDIAN_API = 'http://localhost:9090';

   export default function SecurityDashboard() {
     const {
       status,
       alerts,
       heartbeat,
       isConnected,
       isLoading,
       error,
       refresh,
     } = useGuardian(5000);

     const [killSwitchPaused, setKillSwitchPaused] = useState(false);

     const handleKillSwitchToggle = useCallback(async () => {
       try {
         const res = await fetch(`${GUARDIAN_API}/kill-switch/toggle`, {
           method: 'POST',
         });
         if (res.ok) {
           const data = await res.json();
           setKillSwitchPaused(data.state === 'Paused');
         }
       } catch {
         console.error('Error toggling Kill Switch');
       }
     }, []);

     if (isLoading) {
       return (
         <div className="flex items-center justify-center h-64">
           <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
         </div>
       );
     }

     return (
       <div className="flex flex-col gap-6 p-6 bg-gray-950 min-h-screen text-gray-100">
         {/* Header */}
         <div className="flex items-center justify-between">
           <div>
             <h1 className="text-2xl font-bold flex items-center gap-2">
               🛡️ Security Dashboard
             </h1>
             <p className="text-sm text-gray-400 mt-1">
               Capa 6: Sistema Inmune — Guardian v{status?.guardian || '?'}
             </p>
           </div>

           {/* Kill Switch prominente */}
           <KillSwitchButton
             isPaused={killSwitchPaused}
             onToggle={handleKillSwitchToggle}
           />
         </div>

         {/* Connection Status */}
         <div className={`
           flex items-center gap-2 px-3 py-2 rounded-lg text-sm
           ${isConnected ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}
         `}>
           <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
           {isConnected
             ? `Guardian conectado — Uptime: ${formatUptime(status?.uptime_secs || 0)}`
             : `Guardian desconectado: ${error}`
           }
         </div>

         {/* Grid de métricas */}
         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
           {/* CPU */}
           <MetricCard
             title="CPU"
             value={status?.resource_snapshot?.cpu_usage_percent ?? 0}
             unit="%"
             threshold={90}
             icon="⚡"
           />

           {/* RAM */}
           <MetricCard
             title="RAM"
             value={status?.resource_snapshot?.ram_usage_percent ?? 0}
             unit="%"
             subtitle={`${status?.resource_snapshot?.ram_used_mb ?? 0} / ${status?.resource_snapshot?.ram_total_mb ?? 0} MB`}
             threshold={90}
             icon="🧠"
           />

           {/* Disco */}
           <MetricCard
             title="Disco"
             value={status?.resource_snapshot?.disk_usage_percent ?? 0}
             unit="%"
             subtitle={`${(status?.resource_snapshot?.disk_used_gb ?? 0).toFixed(1)} / ${(status?.resource_snapshot?.disk_total_gb ?? 0).toFixed(1)} GB`}
             threshold={90}
             icon="💾"
           />

           {/* Procesos */}
           <MetricCard
             title="Procesos"
             value={status?.resource_snapshot?.process_count ?? 0}
             unit=""
             threshold={500}
             icon="📊"
           />
         </div>

         {/* Alertas recientes */}
         <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
           <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
             🚨 Alertas Recientes
             <span className="text-sm font-normal text-gray-400">
               ({alerts.length})
             </span>
           </h2>

           {alerts.length === 0 ? (
             <p className="text-gray-500 text-sm">Sin alertas activas — sistema estable</p>
           ) : (
             <div className="space-y-2 max-h-64 overflow-y-auto">
               {alerts.slice(-20).reverse().map((alert, i) => (
                 <div
                   key={i}
                   className={`
                     flex items-center gap-3 px-3 py-2 rounded-lg text-sm
                     ${alert.level === 'Critical'
                       ? 'bg-red-900/30 border border-red-800'
                       : alert.level === 'Warning'
                         ? 'bg-yellow-900/30 border border-yellow-800'
                         : 'bg-blue-900/30 border border-blue-800'
                     }
                   `}
                 >
                   <span>
                     {alert.level === 'Critical' ? '🔴' : alert.level === 'Warning' ? '🟡' : '🔵'}
                   </span>
                   <div className="flex-1">
                     <span className="font-medium">{alert.resource}</span>
                     <span className="text-gray-400 ml-2">{alert.message}</span>
                   </div>
                   <span className="text-xs text-gray-500">
                     {new Date(alert.timestamp).toLocaleTimeString()}
                   </span>
                 </div>
               ))}
             </div>
           )}
         </div>

         {/* Heartbeat & Backup Status */}
         <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           {/* Heartbeat */}
           <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
             <h2 className="text-lg font-semibold mb-3">💓 Heartbeat</h2>
             <div className="space-y-2 text-sm">
               <div className="flex justify-between">
                 <span className="text-gray-400">Estado</span>
                 <span className="text-green-400">{heartbeat?.status ?? 'unknown'}</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Beats</span>
                 <span>{heartbeat?.beat_count ?? 0}</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Uptime</span>
                 <span>{formatUptime(heartbeat?.uptime_secs ?? 0)}</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Último</span>
                 <span className="text-xs">
                   {heartbeat?.timestamp
                     ? new Date(heartbeat.timestamp).toLocaleTimeString()
                     : '—'}
                 </span>
               </div>
             </div>
           </div>

           {/* Backup Status placeholder */}
           <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
             <h2 className="text-lg font-semibold mb-3">📦 Backup Status</h2>
             <div className="space-y-2 text-sm">
               <div className="flex justify-between">
                 <span className="text-gray-400">Flash Memory</span>
                 <span className="text-green-400">Cada 1h</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Config</span>
                 <span className="text-green-400">Cada 6h</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Sistema</span>
                 <span className="text-green-400">Cada 24h</span>
               </div>
               <div className="flex justify-between">
                 <span className="text-gray-400">Regla 3-2-1</span>
                 <span className="text-yellow-400">Configurar</span>
               </div>
             </div>
           </div>
         </div>
       </div>
     );
   }

   // ═══════════════════════════════════
   // COMPONENTES AUXILIARES
   // ═══════════════════════════════════

   interface MetricCardProps {
     title: string;
     value: number;
     unit: string;
     subtitle?: string;
     threshold: number;
     icon: string;
   }

   function MetricCard({ title, value, unit, subtitle, threshold, icon }: MetricCardProps) {
     const isWarning = value > threshold * 0.8;
     const isCritical = value > threshold;

     return (
       <div className={`
         bg-gray-900 rounded-xl p-4 border
         ${isCritical
           ? 'border-red-600 shadow-red-500/20 shadow-lg'
           : isWarning
             ? 'border-yellow-600'
             : 'border-gray-800'
         }
       `}>
         <div className="flex items-center justify-between mb-2">
           <span className="text-sm text-gray-400">{icon} {title}</span>
           <span className={`
             text-2xl font-bold
             ${isCritical ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-green-400'}
           `}>
             {typeof value === 'number' ? value.toFixed(1) : value}{unit}
           </span>
         </div>

         {/* Progress bar */}
         <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
           <div
             className={`h-full rounded-full transition-all duration-500
               ${isCritical ? 'bg-red-500' : isWarning ? 'bg-yellow-500' : 'bg-green-500'}
             `}
             style={{ width: `${Math.min((value / threshold) * 100, 100)}%` }}
           />
         </div>

         {subtitle && (
           <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
         )}
       </div>
     );
   }

   function formatUptime(seconds: number): string {
     const h = Math.floor(seconds / 3600);
     const m = Math.floor((seconds % 3600) / 60);
     const s = seconds % 60;
     if (h > 0) return `${h}h ${m}m`;
     if (m > 0) return `${m}m ${s}s`;
     return `${s}s`;
   }

5. Ejecutar verificación:
   cd ~/yeyo-os
   # Verificar que TypeScript compila (si hay tsconfig)
   # npx tsc --noEmit frontend/src/components/security/SecurityDashboard.tsx

VERIFICAR:
- [ ] frontend/src/hooks/useGuardian.ts existe con polling a Guardian API
- [ ] frontend/src/components/security/KillSwitchButton.tsx existe
- [ ] frontend/src/components/security/SecurityDashboard.tsx existe
- [ ] Dashboard muestra: CPU, RAM, disco, procesos en cards
- [ ] Alertas recientes con color por nivel
- [ ] Kill Switch button prominente con confirmación
- [ ] Heartbeat status visible
- [ ] Backup status visible
- [ ] Indicador de conexión Guardian (verde/rojo)

SI FALLA:
- Guardian API no disponible: el hook maneja error gracefully
- TypeScript errors: verificar tipos de interfaces
- Tailwind no configurado: verificar tailwind.config.js

NO HACER:
- No hardcodear datos (siempre desde Guardian API)
- No permitir Kill Switch sin confirmación
- No ocultar alertas críticas
- No ejecutar acciones destructivas desde el dashboard

GATE: SecurityDashboard renderiza, muestra métricas en tiempo real, Kill Switch button funciona con confirmación, alertas coloreadas por nivel, heartbeat visible, backup status visible.
```
