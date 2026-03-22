/**
 * YeyoOS — Config Node Frontend
 * Micro-fase 5.14 — Capa 5: Órganos
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface ConfigNodeProps {
  nodeId: string;
  sections: string[];
  gpuStats?: { name: string; total_vram_mb: number; used_vram_mb: number; free_vram_mb: number };
  models?: { name: string; size: string }[];
  onGetModels: () => void;
  onPullModel: (name: string) => void;
  onGetGPUStats: () => void;
  onUpdateSetting: (key: string, value: any) => void;
  onClose: (nodeId: string) => void;
}

export default function ConfigNode({
  nodeId, sections, gpuStats, models,
  onGetModels, onPullModel, onGetGPUStats, onUpdateSetting, onClose,
}: ConfigNodeProps) {
  const [activeSection, setActiveSection] = useState('about');
  const [modelInput, setModelInput] = useState('');

  const vramPercent = gpuStats
    ? (gpuStats.used_vram_mb / gpuStats.total_vram_mb) * 100
    : 0;

  return (
    <NodeWrapper nodeId={nodeId} title="Config" icon="⚙️" onClose={onClose}>
      <div className="flex h-full">
        <div className="w-40 bg-gray-800 border-r border-gray-700 p-2 space-y-1 shrink-0">
          {sections.map((section) => (
            <button
              key={section}
              onClick={() => setActiveSection(section)}
              className={`w-full px-2 py-1 text-xs text-left rounded
                ${activeSection === section
                  ? 'bg-gray-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
            >
              {section.charAt(0).toUpperCase() + section.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex-1 p-3 space-y-3">
          {activeSection === 'gpu' && gpuStats && (
            <div>
              <h3 className="text-sm font-medium text-white mb-2">GPU Monitor</h3>
              <p className="text-xs text-gray-400">{gpuStats.name}</p>
              <div className="mt-2">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>VRAM</span>
                  <span>{gpuStats.used_vram_mb}MB / {gpuStats.total_vram_mb}MB</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      vramPercent > 80 ? 'bg-red-500' :
                      vramPercent > 50 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${vramPercent}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {activeSection === 'models' && (
            <div>
              <h3 className="text-sm font-medium text-white mb-2">Modelos Ollama</h3>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={modelInput}
                  onChange={(e) => setModelInput(e.target.value)}
                  placeholder="ej: qwen2.5:3b"
                  className="flex-1 px-2 py-1 text-xs bg-gray-700 text-white
                             rounded border border-gray-600"
                />
                <button onClick={() => { onPullModel(modelInput); setModelInput(''); }}
                  className="px-2 py-1 text-xs bg-green-600 text-white rounded">
                  Descargar
                </button>
              </div>
              {models?.map((m) => (
                <div key={m.name} className="flex justify-between px-2 py-1 text-xs
                                              bg-gray-800 rounded mb-1">
                  <span className="text-gray-300">{m.name}</span>
                  <span className="text-gray-500">{m.size}</span>
                </div>
              ))}
            </div>
          )}

          {activeSection === 'about' && (
            <div className="text-xs text-gray-400 space-y-1">
              <h3 className="text-sm font-medium text-white mb-2">About YeyoOS</h3>
              <p>Version: 0.5.0</p>
              <p>Capa: 5 — Órganos</p>
              <p>Hardware: GTX 1060 3GB VRAM, 16GB RAM</p>
              <p>Modelo: qwen2.5:3b</p>
              <p>Autor: Yeyo</p>
            </div>
          )}
        </div>
      </div>
    </NodeWrapper>
  );
}
