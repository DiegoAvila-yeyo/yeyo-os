/**
 * YeyoOS — Main Page
 * Capa 3: Cuerpo — Integración completa
 *
 * Flujo:
 *   1. Si onboarding pendiente → OnboardingScreen
 *   2. Si onboarding completo → Hub principal (Topbar + Sidebar + FreeCanvas + Workspace)
 */
'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useSystemStore } from '@/stores/systemStore';
import { useHubStore } from '@/stores/hubStore';
import { initKillSwitch } from '@/hooks/useKeyboardShortcuts';

// Onboarding
import { OnboardingScreen } from '@/components/onboarding/OnboardingScreen';

// Layout
import { Topbar, TabInfo } from '@/components/layout/Topbar';
import { HubSidebar, NodoMiniInfo } from '@/components/layout/HubSidebar';

// Hub
import { FreeCanvas, NodoLibreInfo } from '@/components/hub/FreeCanvas';
import { KillSwitchOverlay } from '@/components/security/KillSwitchOverlay';

// Node workspaces
import { ImageNodeLayout } from '@/components/nodes/ImageNodeLayout';
import { VideoNodeLayout } from '@/components/nodes/VideoNodeLayout';
import { CodeNodeLayout } from '@/components/nodes/CodeNodeLayout';
import { AutomationNodeLayout } from '@/components/nodes/AutomationNodeLayout';

// ─── Nodos disponibles en el Hub ───────────────────────────────────────────────
const NODOS_HUB: NodoLibreInfo[] = [
  { id: 'imagen',    label: 'Imagen',     tipo: 'image',      icono: '🖼️',  colorAcento: '#1e90ff' },
  { id: 'video',     label: 'Video',      tipo: 'video',      icono: '🎬',  colorAcento: '#9b59b6' },
  { id: 'codigo',    label: 'Código',     tipo: 'code',       icono: '💻',  colorAcento: '#2ecc71' },
  { id: 'automacion',label: 'Automatizar',tipo: 'automation', icono: '⚡',  colorAcento: '#ffa500' },
  { id: 'chat',      label: 'Chat',       tipo: 'chat',       icono: '💬',  colorAcento: '#ff4444' },
  { id: 'memoria',   label: 'Memoria',    tipo: 'memory',     icono: '🧠',  colorAcento: '#00bcd4' },
];

type WorkspaceId = 'imagen' | 'video' | 'codigo' | 'automacion' | null;

// ─── Workspace Router ──────────────────────────────────────────────────────────
function WorkspaceRouter({ nodeId, onClose }: { nodeId: WorkspaceId; onClose: () => void }) {
  if (!nodeId) return null;

  const closeButton = (
    <button
      onClick={onClose}
      style={{
        position: 'absolute', top: 8, right: 8, zIndex: 10,
        background: '#1a1a2e', border: '1px solid #333', color: '#888',
        borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontFamily: 'monospace', fontSize: 12,
      }}
    >✕ Cerrar</button>
  );

  const wrapper = (children: React.ReactNode) => (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {closeButton}
      {children}
    </div>
  );

  switch (nodeId) {
    case 'imagen':     return wrapper(<ImageNodeLayout />);
    case 'video':      return wrapper(<VideoNodeLayout />);
    case 'codigo':     return wrapper(<CodeNodeLayout />);
    case 'automacion': return wrapper(<AutomationNodeLayout />);
    default:           return null;
  }
}

// ─── Hub Principal ─────────────────────────────────────────────────────────────
function HubPrincipal() {
  const userName = useSystemStore((s) => s.userName);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>(null);
  const [tabs, setTabs] = useState<TabInfo[]>([]);

  const WORKSPACE_LABELS: Record<string, { label: string; icono: string }> = {
    imagen:     { label: 'Imagen',      icono: '🖼️' },
    video:      { label: 'Video',       icono: '🎬' },
    codigo:     { label: 'Código',      icono: '💻' },
    automacion: { label: 'Automatizar', icono: '⚡' },
  };

  const abrirNodo = useCallback((nodeId: string) => {
    if (!['imagen', 'video', 'codigo', 'automacion'].includes(nodeId)) return;
    const ws = nodeId as WorkspaceId;
    setActiveWorkspace(ws);
    const info = WORKSPACE_LABELS[nodeId];
    setTabs(prev => {
      const exists = prev.find(t => t.id === nodeId);
      if (exists) return prev.map(t => ({ ...t, activo: t.id === nodeId }));
      return [
        ...prev.map(t => ({ ...t, activo: false })),
        { id: nodeId, label: info.label, icono: info.icono, activo: true },
      ];
    });
  }, []);

  const cerrarTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const remaining = prev.filter(t => t.id !== tabId);
      if (activeWorkspace === tabId) {
        const last = remaining[remaining.length - 1];
        setActiveWorkspace(last ? last.id as WorkspaceId : null);
        return remaining.map((t, i) => ({ ...t, activo: i === remaining.length - 1 }));
      }
      return remaining;
    });
  }, [activeWorkspace]);

  const clickTab = useCallback((tabId: string) => {
    setActiveWorkspace(tabId as WorkspaceId);
    setTabs(prev => prev.map(t => ({ ...t, activo: t.id === tabId })));
  }, []);

  const nodosMini: NodoMiniInfo[] = NODOS_HUB.map(n => ({
    id: n.id, label: n.label, icono: n.icono, estado: 'idle',
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0a0a0f', overflow: 'hidden' }}>
      {/* TOPBAR */}
      <Topbar
        tabs={tabs}
        onTabClick={clickTab}
        onTabClose={cerrarTab}
        onToggleSidebar={() => setSidebarOpen(o => !o)}
        sidebarOpen={sidebarOpen}
      />

      {/* BODY */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* SIDEBAR */}
        <HubSidebar
          open={sidebarOpen}
          nodos={nodosMini}
          onNodoClick={abrirNodo}
        />

        {/* WORKSPACE o CANVAS */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {activeWorkspace ? (
            <WorkspaceRouter
              nodeId={activeWorkspace}
              onClose={() => activeWorkspace && cerrarTab(activeWorkspace)}
            />
          ) : (
            /* HUB libre — FreeCanvas con pan/zoom */
            <FreeCanvas
              nodos={NODOS_HUB}
              userId={userName ?? 'yeyo'}
              onNodoDoubleClick={abrirNodo}
              style={{ width: '100%', height: '100%' }}
            />
          )}
        </div>
      </div>

      {/* KILL SWITCH OVERLAY (siempre montado, activa con Ctrl+Alt+K) */}
      <KillSwitchOverlay />
    </div>
  );
}

// ─── Entry Point ───────────────────────────────────────────────────────────────
export default function YeyoOSPage() {
  const setOnboardingComplete = useSystemStore((s) => s.setOnboardingComplete);
  const setUserName = useSystemStore((s) => s.setUserName);

  // Leer localStorage SINCRÓNICAMENTE en el primer render
  // para evitar el flash onboarding → hub
  const [clientReady, setClientReady] = useState(false);
  const [skipOnboarding, setSkipOnboarding] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem('yeyo_onboarding_complete') === '1';
    const savedName = localStorage.getItem('yeyo_user_name');
    if (done && savedName) {
      setUserName(savedName);
      setOnboardingComplete(true);
      setSkipOnboarding(true);
    }
    setClientReady(true);
  }, [setOnboardingComplete, setUserName]);

  // Registrar Kill Switch global al inicio
  useEffect(() => {
    const cleanup = initKillSwitch();
    return cleanup;
  }, []);

  // Mientras detectamos si ya hizo onboarding, no renderizar nada
  if (!clientReady) return null;

  if (skipOnboarding) return <HubPrincipal />;

  return (
    <OnboardingScreen
      onComplete={(nombre) => {
        console.log('[YeyoOS] onboarding complete for:', nombre);
        localStorage.setItem('yeyo_onboarding_complete', '1');
        localStorage.setItem('yeyo_user_name', nombre);
        setUserName(nombre);
        setOnboardingComplete(true);
        setSkipOnboarding(true);
      }}
    />
  );
}
