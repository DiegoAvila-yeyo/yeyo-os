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

import { useChatStore } from '@/lib/store/chat-store';

// Node workspaces
import {
  ImageNodeLayout,
  type ChatMessage as ImageChatMessage,
  type ImageGenerada,
} from '@/components/nodes/ImageNodeLayout';
import { VideoNodeLayout } from '@/components/nodes/VideoNodeLayout';
import { CodeNodeLayout } from '@/components/nodes/CodeNodeLayout';
import { AutomationNodeLayout } from '@/components/nodes/AutomationNodeLayout';
import { MemoryNodeLayout } from '@/components/nodes/MemoryNodeLayout';
import { MemoryMapLayout } from '@/components/nodes/MemoryMapLayout';
import { YeyoNetNodeLayout } from '@/components/nodes/YeyoNetNodeLayout';
import { WorkflowNodeLayout } from '@/components/nodes/workflows/WorkflowNodeLayout';
import { ObservatoryNodeLayout } from '@/components/nodes/observatory/ObservatoryNodeLayout';
import ChatPanel from '@/components/chat/ChatPanel';

// ─── Nodos disponibles en el Hub ───────────────────────────────────────────────
const NODOS_HUB: NodoLibreInfo[] = [
  { id: 'imagen',      label: 'Imagen',      tipo: 'image',       icono: '🖼️',  colorAcento: '#1e90ff' },
  { id: 'video',       label: 'Video',       tipo: 'video',       icono: '🎬',  colorAcento: '#9b59b6' },
  { id: 'codigo',      label: 'Código',      tipo: 'code',        icono: '💻',  colorAcento: '#2ecc71' },
  { id: 'automacion',  label: 'Automatizar', tipo: 'automation',  icono: '⚡',  colorAcento: '#ffa500' },
  { id: 'chat',        label: 'Chat',        tipo: 'chat',        icono: '💬',  colorAcento: '#ff4444' },
  { id: 'memoria',     label: 'Memoria',     tipo: 'memory',      icono: '🧠',  colorAcento: '#00bcd4' },
  { id: 'mapa',        label: 'MemoryMap',   tipo: 'memory',      icono: '🗺️',  colorAcento: '#9c27b0' },
  { id: 'yeyonet',     label: 'YeyoNet',     tipo: 'network',     icono: '🌐',  colorAcento: '#00e676' },
  { id: 'workflows',   label: 'Workflows',   tipo: 'workflow',    icono: '⚙️',  colorAcento: '#6366F1' },
  { id: 'observatory', label: 'Observatory', tipo: 'observatory', icono: '🔭',  colorAcento: '#F59E0B' },
];

type WorkspaceId = 'imagen' | 'video' | 'codigo' | 'automacion' | 'memoria' | 'mapa' | 'yeyonet' | 'workflows' | 'observatory' | null;

// ─── Workspace Router ──────────────────────────────────────────────────────────
function WorkspaceRouter({
  nodeId,
  onClose,
  imageMessages,
  imageGallery,
  onImageChatSend,
  onImageAssistantMessage,
  codeMessages,
  onCodeChatSend,
  videoClips,
  videoMessages,
  onVideoClipAdd,
  onVideoChatSend,
}: {
  nodeId: WorkspaceId;
  onClose: () => void;
  imageMessages: ImageChatMessage[];
  imageGallery: ImageGenerada[];
  onImageChatSend: (mensaje: string) => void;
  onImageAssistantMessage: (mensaje: string) => void;
  codeMessages: Array<{ id: string; role: 'user' | 'assistant'; content: string }>;
  onCodeChatSend: (mensaje: string) => void;
  videoClips: import('@/components/nodes/VideoNodeLayout').ClipInfo[];
  videoMessages: Array<{ id: string; role: 'user' | 'assistant'; content: string }>;
  onVideoClipAdd: (clip: import('@/components/nodes/VideoNodeLayout').ClipInfo) => void;
  onVideoChatSend: (mensaje: string) => void;
}){
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
    case 'imagen':
      return wrapper(
        <ImageNodeLayout
          imagenes={imageGallery}
          chatMessages={imageMessages}
          onChatSend={onImageChatSend}
          onAssistantMessage={onImageAssistantMessage}
        />
      );
    case 'video':      return wrapper(<VideoNodeLayout clips={videoClips} chatMessages={videoMessages} onClipAdd={onVideoClipAdd} onChatSend={onVideoChatSend} />);
    case 'codigo':     return wrapper(<CodeNodeLayout chatMessages={codeMessages} onChatSend={onCodeChatSend} />);
    case 'automacion': return wrapper(<AutomationNodeLayout />);
    case 'memoria':    return wrapper(<MemoryNodeLayout />);
    case 'mapa':       return wrapper(<MemoryMapLayout />);
    case 'yeyonet':    return wrapper(<YeyoNetNodeLayout />);
    case 'workflows':  return wrapper(<WorkflowNodeLayout />);
    case 'observatory': return wrapper(<ObservatoryNodeLayout />);
    default:           return null;
  }
}

// ─── Hub Principal ─────────────────────────────────────────────────────────────
function HubPrincipal() {
  const userName = useSystemStore((s) => s.userName);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>(null);
  const [tabs, setTabs] = useState<TabInfo[]>([]);
  const [imageMessages, setImageMessages] = useState<ImageChatMessage[]>([]);
  const [imageGallery, setImageGallery] = useState<ImageGenerada[]>([]);
  const [codeMessages, setCodeMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; content: string }>>([]);
  const [videoClips, setVideoClips] = useState<import('@/components/nodes/VideoNodeLayout').ClipInfo[]>([]);
  const [videoMessages, setVideoMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; content: string }>>([]);

  const WORKSPACE_LABELS: Record<string, { label: string; icono: string }> = {
    imagen:      { label: 'Imagen',      icono: '🖼️' },
    video:       { label: 'Video',       icono: '🎬' },
    codigo:      { label: 'Código',      icono: '💻' },
    automacion:  { label: 'Automatizar', icono: '⚡' },
    memoria:     { label: 'Memoria',     icono: '🧠' },
    mapa:        { label: 'MemoryMap',   icono: '🗺️' },
    yeyonet:     { label: 'YeyoNet',     icono: '🌐' },
    workflows:   { label: 'Workflows',   icono: '⚙️' },
    observatory: { label: 'Observatory', icono: '🔭' },
  };

  const abrirNodo = useCallback((nodeId: string) => {
    // Chat: abrir panel lateral
    if (nodeId === 'chat') {
      useChatStore.getState().setPanelOpen(true);
      return;
    }
    if (!['imagen', 'video', 'codigo', 'automacion', 'memoria', 'mapa', 'yeyonet', 'workflows', 'observatory'].includes(nodeId)) return;
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

  const appendImageMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    setImageMessages(prev => ([
      ...prev,
      {
        id: `image-chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role,
        content,
      },
    ]));
  }, []);

  // ImageNodeLayout handles ALL generation directly to localhost:8000 (no proxy).
  // page.tsx only manages chat message display.

  const handleImageChatSend = useCallback((mensaje: string) => {
    appendImageMessage('user', mensaje);
  }, [appendImageMessage]);

  const handleImageAssistantMessage = useCallback((mensaje: string) => {
    appendImageMessage('assistant', mensaje);
  }, [appendImageMessage]);

  const handleCodeChatSend = useCallback(async (mensaje: string) => {
    const userMsg = { id: `code-${Date.now()}`, role: 'user' as const, content: mensaje };
    const loadingId = `code-loading-${Date.now()}`;
    const loadingMsg = { id: loadingId, role: 'assistant' as const, content: '🤔 Analizando...' };
    setCodeMessages(prev => [...prev, userMsg, loadingMsg]);
    try {
      // Build history for planner context
      const recentHistory = codeMessages.slice(-6).map(m => ({
        role: m.role, content: m.content,
      }));

      const res = await fetch('http://localhost:8000/api/v1/code/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: mensaje, history: recentHistory }),
      });
      const data = await res.json();

      // Planner needs more info — show questions
      if (data?.type === 'question') {
        setCodeMessages(prev => prev.map(m =>
          m.id === loadingId ? { ...m, content: data.message } : m
        ));
        return;
      }

      // Dojo generated code — show results
      const codigo = data?.codigo || '';
      const aprobado = data?.aprobado ?? false;
      const lang = data?.lenguaje || 'python';

      let content = '';
      if (codigo) {
        content += `\`\`\`${lang}\n${codigo}\n\`\`\`\n`;
      }

      const astIcon = data?.ast_valido ? '✅' : '❌';
      const testsIcon = data?.tests_pasaron ? '✅' : '❌';
      const funcIcon = data?.func_verificado ? '✅' : '❌';
      const estado = aprobado ? '✅ APROBADO' : '❌ RECHAZADO';

      content += `${estado}`;
      content += ` | Crítico: ${(data?.score ?? 0).toFixed(1)}/10`;
      content += ` | Seguridad: ${(data?.score_seguridad ?? 0).toFixed(1)}/10`;
      content += ` | Performance: ${(data?.score_performance ?? 0).toFixed(1)}/10`;
      content += ` | AST: ${astIcon}`;
      content += ` | Tests: ${testsIcon}`;
      content += ` | Func: ${funcIcon}`;

      if (!aprobado && data?.razon_falla) {
        content += `\n\n⚠️ **Razón**: ${data.razon_falla}`;
      }

      if (!data?.tests_pasaron && data?.tests_output) {
        content += `\n\n📋 **Test output**:\n\`\`\`\n${data.tests_output}\n\`\`\``;
      }

      if (!codigo && !aprobado) {
        content = `❌ No se pudo generar código\n\n⚠️ ${data?.razon_falla || data?.detail || 'Error desconocido'}`;
      }

      setCodeMessages(prev => prev.map(m =>
        m.id === loadingId ? { ...m, content } : m
      ));
    } catch (err) {
      setCodeMessages(prev => prev.map(m =>
        m.id === loadingId ? { ...m, content: `❌ Error: ${err}` } : m
      ));
    }
  }, [codeMessages]);

  const handleVideoChatSend = useCallback(async (mensaje: string) => {
    const userMsg = { id: `video-${Date.now()}`, role: 'user' as const, content: mensaje };
    const loadingId = `video-loading-${Date.now()}`;
    const loadingMsg = { id: loadingId, role: 'assistant' as const, content: '⏳ Procesando...' };
    setVideoMessages(prev => [...prev, userMsg, loadingMsg]);
    try {
      const res = await fetch('http://localhost:8000/api/v1/video/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: mensaje }),
      });
      const data = await res.json();
      const respuesta = data?.comando || data?.respuesta || data?.detail || 'Sin respuesta del servidor';
      setVideoMessages(prev => prev.map(m =>
        m.id === loadingId ? { ...m, content: respuesta } : m
      ));
    } catch (err) {
      setVideoMessages(prev => prev.map(m =>
        m.id === loadingId ? { ...m, content: `❌ Error: ${err}` } : m
      ));
    }
  }, []);

  const isFullscreenWorkspace = activeWorkspace === 'observatory';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0a0a0f', overflow: 'hidden' }}>

      {/* FULLSCREEN OBSERVATORY */}
      {isFullscreenWorkspace && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: '#060B18' }}>
          <ObservatoryNodeLayout onExit={() => cerrarTab('observatory')} />
        </div>
      )}

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
              imageMessages={imageMessages}
              imageGallery={imageGallery}
              onImageChatSend={handleImageChatSend}
              onImageAssistantMessage={handleImageAssistantMessage}
              codeMessages={codeMessages}
              onCodeChatSend={handleCodeChatSend}
              videoClips={videoClips}
              videoMessages={videoMessages}
              onVideoClipAdd={(clip) => setVideoClips(prev => [...prev, clip])}
              onVideoChatSend={handleVideoChatSend}
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

      {/* CHAT PANEL (slide-in desde la derecha) */}
      <ChatPanel />
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
