/**
 * YeyoOS — Hook para Guardian API
 * Micro-fase 6.9 — Capa 6: Sistema Inmune
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
      if (statusRes.ok) { setStatus(await statusRes.json()); setIsConnected(true); }
      if (alertsRes.ok) { setAlerts(await alertsRes.json()); }
      if (hbRes.ok) { setHeartbeat(await hbRes.json()); }
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
