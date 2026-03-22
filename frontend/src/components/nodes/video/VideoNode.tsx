/**
 * YeyoOS — Video Node Frontend
 * Micro-fase 5.5 — Capa 5: Órganos
 */

'use client';

import React, { useState } from 'react';
import NodeWrapper from '../NodeWrapper';

interface VideoJob {
  id: string;
  status: string;
  progress: number;
  command: string;
}

interface VideoNodeProps {
  nodeId: string;
  jobs: VideoJob[];
  onProcess: (command: string, inputFile: string) => void;
  onClose: (nodeId: string) => void;
}

export default function VideoNode({
  nodeId,
  jobs,
  onProcess,
  onClose,
}: VideoNodeProps) {
  const [command, setCommand] = useState('');
  const [inputFile, setInputFile] = useState('');

  const handleProcess = () => {
    if (!command.trim()) return;
    onProcess(command.trim(), inputFile);
    setCommand('');
  };

  return (
    <NodeWrapper nodeId={nodeId} title="Video" icon="🎬" onClose={onClose}>
      <div className="flex flex-col h-full gap-3">
        {/* Video preview placeholder */}
        <div className="aspect-video bg-gray-800 rounded-lg flex items-center
                        justify-center text-gray-500 border border-gray-700">
          <span>📹 Arrastra un video aquí o selecciona archivo</span>
        </div>

        {/* Command input */}
        <div className="space-y-2">
          <input
            type="text"
            value={inputFile}
            onChange={(e) => setInputFile(e.target.value)}
            placeholder="Archivo de entrada..."
            className="w-full px-3 py-1 text-sm bg-gray-700 text-white
                       rounded border border-gray-600 focus:outline-none"
          />
          <div className="flex gap-2">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleProcess()}
              placeholder="Ej: recorta del minuto 2 al 5..."
              className="flex-1 px-3 py-2 text-sm bg-gray-700 text-white
                         rounded-lg border border-gray-600 focus:border-green-500
                         focus:outline-none"
            />
            <button
              onClick={handleProcess}
              disabled={!command.trim()}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm
                         hover:bg-green-500 disabled:opacity-50"
            >
              ▶ Procesar
            </button>
          </div>
        </div>

        {/* Jobs */}
        <div className="flex-1 overflow-y-auto space-y-2">
          {jobs.map((job) => (
            <div key={job.id} className="px-3 py-2 bg-gray-800 rounded-lg
                                         border border-gray-700">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300 truncate">{job.command}</span>
                <span className={`font-medium ${
                  job.status === 'completed' ? 'text-green-400' :
                  job.status === 'failed' ? 'text-red-400' :
                  job.status === 'running' ? 'text-yellow-400' : 'text-gray-400'
                }`}>
                  {job.status}
                </span>
              </div>
              {job.status === 'running' && (
                <div className="mt-1 w-full bg-gray-700 rounded-full h-1">
                  <div
                    className="bg-green-500 h-1 rounded-full transition-all"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </NodeWrapper>
  );
}
