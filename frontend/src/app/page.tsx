/**
 * YeyoOS — Neural Hub Page (Demo)
 * Capa 3: Cuerpo
 */
'use client';

import { useEffect, useState } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import { GraphExecutionView } from '@/components/hub/GraphExecutionView';
import { useGraphStore } from '@/stores/graphStore';
import ChatPanel from '@/components/chat/ChatPanel';
import MiniChat from '@/components/chat/MiniChat';
import Notifications from '@/components/common/Notifications';
import { useUIStore } from '@/lib/store/ui-store';
import { useNotificationStore } from '@/lib/store/notification-store';
import { initKillSwitch, useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

const NODES = [
  { id: 'chat',   label: 'Chat',    icon: '\u{1F4AC}', color: '#1e90ff' },
  { id: 'memory', label: 'Memoria', icon: '\u{1F9E0}', color: '#9b59b6' },
  { id: 'files',  label: 'Archivos',icon: '\u{1F4C1}', color: '#2ecc71' },
  { id: 'code',   label: 'Codigo',  icon: '\u{1F4BB}', color: '#ffa500' },
  { id: 'vision', label: 'Vision',  icon: '\u{1F441}', color: '#ff4444' },
];

function SatelliteNodeUI({ node, index, total, onClick }: {
  node: typeof NODES[0]; index: number; total: number; onClick?: () => void;
}) {
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2;
  // Radio responsive: 22vmin se adapta a cualquier resolución
  const rVmin = 22;
  const cx = Math.cos(angle) * rVmin;
  const cy = Math.sin(angle) * rVmin;
  return (
    <div
      className="absolute z-10 cursor-pointer group"
      style={{
        left: `calc(50% + ${cx}vmin)`,
        top: `calc(50% + ${cy}vmin)`,
        transform: 'translate(-50%, -50%)',
      }}
      onClick={onClick}
    >
      <div
        className="rounded-xl flex flex-col items-center justify-center transition-all duration-200 group-hover:scale-110"
        style={{
          width: 'clamp(44px, 6vmin, 64px)',
          height: 'clamp(44px, 6vmin, 64px)',
          background: `${node.color}20`,
          border: `1px solid ${node.color}60`,
          boxShadow: `0 0 15px ${node.color}30`,
        }}
      >
        <span style={{ fontSize: 'clamp(14px, 2.5vmin, 22px)' }}>{node.icon}</span>
        <span className="mt-0.5 font-mono" style={{ color: node.color, fontSize: 'clamp(8px, 1.2vmin, 12px)' }}>
          {node.label}
        </span>
      </div>
    </div>
  );
}

// ─── Demo: simula eventos de grafo para mostrar GraphExecutionView ───────────
function GraphDemo() {
  const { procesarEvento, limpiarTodo } = useGraphStore();
  const [corriendo, setCorriendo] = useState(false);

  const simularGrafo = () => {
    if (corriendo) return;
    setCorriendo(true);
    limpiarTodo();

    const nodos = [
      { id: 'generar_guion', msg: 'Generando guión...' },
      { id: 'crear_imagenes', msg: 'Creando imágenes...' },
      { id: 'componer_video', msg: 'Componiendo video...' },
    ];
    const grafoId = 'demo_reel';
    let delay = 0;

    // Inicializar todos como pendiente
    nodos.forEach((n, i) => {
      setTimeout(() => {
        procesarEvento({ type: 'graph_event', grafo_id: grafoId, nodo_id: n.id,
          estado: 'pendiente', progreso: 0, mensaje: 'En espera', timestamp: new Date().toISOString(),
          nodos_totales: 3, conexiones: [{ desde: 'generar_guion', hasta: 'crear_imagenes' }, { desde: 'crear_imagenes', hasta: 'componer_video' }] });
      }, i * 50);
    });

    // Ejecutar nodos en secuencia
    nodos.forEach((n, i) => {
      delay += 800;
      setTimeout(() => {
        procesarEvento({ type: 'graph_event', grafo_id: grafoId, nodo_id: n.id,
          estado: 'activo', progreso: i / 3, mensaje: n.msg, timestamp: new Date().toISOString(), nodos_totales: 3 });
      }, delay);
      delay += 1500;
      setTimeout(() => {
        procesarEvento({ type: 'graph_event', grafo_id: grafoId, nodo_id: n.id,
          estado: 'completado', progreso: (i + 1) / 3, mensaje: '✓ Listo', timestamp: new Date().toISOString(), nodos_totales: 3 });
      }, delay);
    });

    setTimeout(() => setCorriendo(false), delay + 500);
  };

  return (
    <div className="absolute bottom-2 left-2 z-20 flex flex-col gap-2"
      style={{ maxWidth: 'min(340px, calc(100vw - 16px))' }}>
      <GraphExecutionView grafoId="demo_reel" style={{ width: '100%' }} />
      <button
        onClick={simularGrafo}
        disabled={corriendo}
        className="px-3 py-1.5 rounded font-mono text-xs transition-all"
        style={{
          background: corriendo ? '#1a2a1a' : '#0d2a0d',
          border: `1px solid ${corriendo ? '#2a4a2a' : '#4CAF50'}`,
          color: corriendo ? '#4a7a4a' : '#4CAF50',
          cursor: corriendo ? 'not-allowed' : 'pointer',
        }}
      >
        {corriendo ? '⏳ Ejecutando grafo...' : '▶ Simular pipeline (Script → Imagen → Video)'}
      </button>
    </div>
  );
}

function NeuralHubDemo() {
  const { setActivePanel } = useUIStore();
  return (
    <div
      className="w-full h-full relative overflow-hidden flex items-center justify-center select-none"
      style={{ background: 'radial-gradient(ellipse at center, #0d0d20 0%, #0a0a0f 70%)' }}
    >
      {/* Grid */}
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'linear-gradient(#1e90ff 1px, transparent 1px), linear-gradient(90deg, #1e90ff 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* Anillos */}
      {[180, 270].map((r, i) => (
        <div
          key={i}
          className="absolute rounded-full border border-blue-500/10"
          style={{ width: r * 2, height: r * 2, left: `calc(50% - ${r}px)`, top: `calc(50% - ${r}px)` }}
        />
      ))}

      {/* Nodo central */}
      <div className="absolute z-10" style={{ left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }}>
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 rounded-full bg-blue-500/10 animate-ping" style={{ animationDuration: '3s' }} />
          <div className="absolute w-24 h-24 rounded-full bg-blue-500/15 animate-pulse" />
          <div
            className="w-20 h-20 rounded-full flex flex-col items-center justify-center z-10"
            style={{
              width: 'clamp(60px, 9vmin, 90px)',
              height: 'clamp(60px, 9vmin, 90px)',
              background: 'radial-gradient(circle, #1e90ff30 0%, #0a0a0f 70%)',
              border: '2px solid #1e90ff50',
              boxShadow: '0 0 40px #1e90ff30, 0 0 80px #1e90ff10',
            }}
          >
            <span style={{ fontSize: 'clamp(20px, 4vmin, 32px)' }}>⚡</span>
            <span className="text-blue-300 font-mono mt-1" style={{ fontSize: 'clamp(8px, 1.2vmin, 12px)' }}>YeyoOS</span>
          </div>
        </div>
      </div>

      {/* Nodos satelite */}
      {NODES.map((node, i) => (
        <SatelliteNodeUI
          key={node.id}
          node={node}
          index={i}
          total={NODES.length}
          onClick={node.id === 'chat' ? () => setActivePanel('chat') : undefined}
        />
      ))}

      {/* Demo GraphExecutionView */}
      <GraphDemo />

      {/* Shortcuts hint */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-3 font-mono" style={{ color: '#333355', fontSize: '11px' }}>
        <span>Ctrl+Space = MiniChat</span>
        <span>·</span>
        <span>Ctrl+J = Chat</span>
        <span>·</span>
        <span>Ctrl+Alt+K = Kill Switch</span>
      </div>

      {/* Badge backend */}
      <div
        className="absolute top-4 right-4 flex items-center gap-1.5 px-3 py-1.5 rounded-full font-mono"
        style={{ background: '#ff444415', border: '1px solid #ff444430', color: '#ff6b6b', fontSize: '11px' }}
      >
        <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
        Backend offline — Capa 4 pendiente
      </div>
    </div>
  );
}

export default function NeuralHubPage() {
  const { toggleMiniChat, setActivePanel, closeActivePanel, activePanel } = useUIStore();
  const { addNotification } = useNotificationStore();

  useEffect(() => {
    const cleanup = initKillSwitch();
    return cleanup;
  }, []);

  useKeyboardShortcuts([
    { id: 'toggle-mini-chat', keys: 'ctrl+ ', handler: toggleMiniChat, description: 'Toggle MiniChat' },
    { id: 'open-chat', keys: 'ctrl+j', handler: () => setActivePanel('chat'), description: 'Abrir Chat' },
    { id: 'escape', keys: 'escape', handler: closeActivePanel, description: 'Cerrar panel' },
  ]);

  useEffect(() => {
    const t = setTimeout(() => {
      addNotification('success', 'YeyoOS Neural Hub cargado', true);
      setTimeout(() => addNotification('info', 'Click en el nodo Chat o Ctrl+J para abrir el chat', true), 2500);
    }, 1000);
    return () => clearTimeout(t);
  }, []);

  return (
    <AppLayout
      canvas={<NeuralHubDemo />}
      chatPanel={
        activePanel === 'chat' ? (
          <div className="fixed right-0 top-0 h-full z-50">
            <ChatPanel />
          </div>
        ) : null
      }
      miniChat={<MiniChat initialX={20} initialY={80} />}
      notifications={<Notifications />}
    />
  );
}
