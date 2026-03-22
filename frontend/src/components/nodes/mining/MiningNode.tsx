/**
 * YeyoOS — Mining Node Frontend
 * Micro-fase 5.15 — Capa 5: Órganos
 *
 * ⚠️ GPU NUNCA PARA MINERÍA — EXCLUSIVAMENTE PARA IA ⚠️
 */

'use client';

import React from 'react';
import NodeWrapper from '../NodeWrapper';

interface ASICDevice {
  id: string;
  name: string;
  model: string;
  status: string;
  hashrate: number;
  temperature: number;
  power_watts: number;
}

interface MiningNodeProps {
  nodeId: string;
  devices: ASICDevice[];
  stats: {
    total_hashrate: number;
    estimated_daily_usd: number;
    devices_online: number;
    devices_total: number;
  };
  onAddDevice: () => void;
  onRefresh: () => void;
  onClose: (nodeId: string) => void;
}

export default function MiningNode({
  nodeId, devices, stats, onAddDevice, onRefresh, onClose,
}: MiningNodeProps) {
  return (
    <NodeWrapper nodeId={nodeId} title="Mining (ASIC)" icon="⛏️" onClose={onClose}>
      <div className="flex flex-col h-full gap-3">
        <div className="px-3 py-2 bg-red-900/30 border border-red-700 rounded-lg">
          <p className="text-xs text-red-400 font-medium">
            ⚠️ GPU exclusiva para IA — Minería solo via ASIC
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="px-3 py-2 bg-gray-800 rounded-lg">
            <p className="text-[10px] text-gray-500">Hashrate Total</p>
            <p className="text-sm font-bold text-green-400">{stats.total_hashrate} TH/s</p>
          </div>
          <div className="px-3 py-2 bg-gray-800 rounded-lg">
            <p className="text-[10px] text-gray-500">Estimado Diario</p>
            <p className="text-sm font-bold text-yellow-400">${stats.estimated_daily_usd}</p>
          </div>
          <div className="px-3 py-2 bg-gray-800 rounded-lg">
            <p className="text-[10px] text-gray-500">Dispositivos</p>
            <p className="text-sm font-bold text-blue-400">
              {stats.devices_online}/{stats.devices_total}
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-2">
          {devices.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-4">
              No hay dispositivos ASIC conectados
            </p>
          ) : (
            devices.map((device) => (
              <div key={device.id} className="px-3 py-2 bg-gray-800 rounded-lg
                                               border border-gray-700">
                <div className="flex justify-between">
                  <span className="text-xs text-white font-medium">{device.name}</span>
                  <span className={`text-xs ${
                    device.status === 'online' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {device.status}
                  </span>
                </div>
                <div className="flex gap-4 mt-1 text-[10px] text-gray-500">
                  <span>{device.hashrate} TH/s</span>
                  <span>{device.temperature}°C</span>
                  <span>{device.power_watts}W</span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex gap-2 shrink-0">
          <button onClick={onAddDevice}
            className="flex-1 px-3 py-1 text-xs bg-gray-700 text-gray-300
                       rounded hover:bg-gray-600">
            + Añadir ASIC
          </button>
          <button onClick={onRefresh}
            className="px-3 py-1 text-xs bg-blue-600 text-white rounded">
            🔄
          </button>
        </div>
      </div>
    </NodeWrapper>
  );
}
