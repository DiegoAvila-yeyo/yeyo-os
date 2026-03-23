/**
 * YeyoOS — Security Dashboard
 * Micro-fase 6.9 — Capa 6: Sistema Inmune
 */

'use client';

import React, { useState, useCallback } from 'react';
import { useGuardian } from '../../hooks/useGuardian';
import KillSwitchButton from './KillSwitchButton';

const GUARDIAN_API = 'http://localhost:9090';

export default function SecurityDashboard() {
  const { status, alerts, heartbeat, isConnected, isLoading, error, refresh } = useGuardian(5000);
  const [killSwitchPaused, setKillSwitchPaused] = useState(false);

  const handleKillSwitchToggle = useCallback(async () => {
    try {
      const res = await fetch(`${GUARDIAN_API}/kill-switch/toggle`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setKillSwitchPaused(data.state === 'Paused');
      }
    } catch { console.error('Error toggling Kill Switch'); }
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">🛡️ Security Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">Capa 6: Sistema Inmune — Guardian v{status?.guardian || '?'}</p>
        </div>
        <KillSwitchButton isPaused={killSwitchPaused} onToggle={handleKillSwitchToggle} />
      </div>

      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${isConnected ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
        <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
        {isConnected ? `Guardian conectado — Uptime: ${formatUptime(status?.uptime_secs || 0)}` : `Guardian desconectado: ${error}`}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="CPU" value={status?.resource_snapshot?.cpu_usage_percent ?? 0} unit="%" threshold={90} icon="⚡" />
        <MetricCard title="RAM" value={status?.resource_snapshot?.ram_usage_percent ?? 0} unit="%" subtitle={`${status?.resource_snapshot?.ram_used_mb ?? 0} / ${status?.resource_snapshot?.ram_total_mb ?? 0} MB`} threshold={90} icon="🧠" />
        <MetricCard title="Disco" value={status?.resource_snapshot?.disk_usage_percent ?? 0} unit="%" subtitle={`${(status?.resource_snapshot?.disk_used_gb ?? 0).toFixed(1)} / ${(status?.resource_snapshot?.disk_total_gb ?? 0).toFixed(1)} GB`} threshold={90} icon="💾" />
        <MetricCard title="Procesos" value={status?.resource_snapshot?.process_count ?? 0} unit="" threshold={500} icon="📊" />
      </div>

      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">🚨 Alertas Recientes <span className="text-sm font-normal text-gray-400">({alerts.length})</span></h2>
        {alerts.length === 0 ? (
          <p className="text-gray-500 text-sm">Sin alertas activas — sistema estable</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {alerts.slice(-20).reverse().map((alert, i) => (
              <div key={i} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${alert.level === 'Critical' ? 'bg-red-900/30 border border-red-800' : alert.level === 'Warning' ? 'bg-yellow-900/30 border border-yellow-800' : 'bg-blue-900/30 border border-blue-800'}`}>
                <span>{alert.level === 'Critical' ? '🔴' : alert.level === 'Warning' ? '🟡' : '🔵'}</span>
                <div className="flex-1"><span className="font-medium">{alert.resource}</span><span className="text-gray-400 ml-2">{alert.message}</span></div>
                <span className="text-xs text-gray-500">{new Date(alert.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-lg font-semibold mb-3">💓 Heartbeat</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-400">Estado</span><span className="text-green-400">{heartbeat?.status ?? 'unknown'}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Beats</span><span>{heartbeat?.beat_count ?? 0}</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Uptime</span><span>{formatUptime(heartbeat?.uptime_secs ?? 0)}</span></div>
          </div>
        </div>
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-lg font-semibold mb-3">📦 Backup Status</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-400">Flash Memory</span><span className="text-green-400">Cada 1h</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Config</span><span className="text-green-400">Cada 6h</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Sistema</span><span className="text-green-400">Cada 24h</span></div>
            <div className="flex justify-between"><span className="text-gray-400">Regla 3-2-1</span><span className="text-yellow-400">Configurar</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps { title: string; value: number; unit: string; subtitle?: string; threshold: number; icon: string; }

function MetricCard({ title, value, unit, subtitle, threshold, icon }: MetricCardProps) {
  const isWarning = value > threshold * 0.8;
  const isCritical = value > threshold;
  return (
    <div className={`bg-gray-900 rounded-xl p-4 border ${isCritical ? 'border-red-600 shadow-red-500/20 shadow-lg' : isWarning ? 'border-yellow-600' : 'border-gray-800'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{icon} {title}</span>
        <span className={`text-2xl font-bold ${isCritical ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-green-400'}`}>
          {typeof value === 'number' ? value.toFixed(1) : value}{unit}
        </span>
      </div>
      <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${isCritical ? 'bg-red-500' : isWarning ? 'bg-yellow-500' : 'bg-green-500'}`} style={{ width: `${Math.min((value / threshold) * 100, 100)}%` }} />
      </div>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
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
