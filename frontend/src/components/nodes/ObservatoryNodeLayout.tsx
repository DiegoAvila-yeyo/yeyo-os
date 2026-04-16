/**
 * ObservatoryNodeLayout.tsx
 * Phase 4: Observatory Town — 8 agent buildings in an isometric town view
 * All visuals via CSS + emoji, no sprites
 */
'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

// ─── Types ──────────────────────────────────────────────────────────────────────

interface ObservatoryAgent {
  name: string;
  emoji: string;
  building: string;
  description: string;
  quick_tasks: string[];
  status: 'idle' | 'working' | 'done';
  currentTask?: string;
  gradient: [string, string];
}

interface ObservatoryTask {
  id: string;
  agent_name: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  result_output: string;
  duration_ms: number;
  created_at: string;
  completed_at?: string;
}

interface CrewMission {
  id: string;
  title: string;
  description: string;
  agent_sequence: string[];
  status: string;
  current_agent_index: number;
  results: Array<{ agent: string; output: string }>;
}

interface BridgeMission {
  id: string;
  title: string;
  description: string;
  origin: string;
  created_by: string;
  finding: string;
  analysis: string;
  strategy: string;
  status: string;
  created_at?: string;
}

export interface ObservatoryNodeLayoutProps {}

// ─── Default Agents ─────────────────────────────────────────────────────────────

const DEFAULT_AGENTS: ObservatoryAgent[] = [
  { name: 'Miner', emoji: '⛏️', building: 'Error Mine', description: 'Excava errores y bugs del código', quick_tasks: ['Buscar errores en el código', 'Analizar logs recientes', 'Detectar warnings ignorados'], status: 'idle', gradient: ['#5D4037', '#795548'] },
  { name: 'Scientist', emoji: '🔬', building: 'Laboratorio', description: 'Investiga y analiza patrones del sistema', quick_tasks: ['Investigar rendimiento', 'Analizar dependencias', 'Revisar arquitectura'], status: 'idle', gradient: ['#1565C0', '#1976D2'] },
  { name: 'Tester', emoji: '💪', building: 'Gimnasio', description: 'Pone a prueba la resistencia del código', quick_tasks: ['Ejecutar tests unitarios', 'Pruebas de estrés', 'Verificar cobertura'], status: 'idle', gradient: ['#C62828', '#E53935'] },
  { name: 'Writer', emoji: '✍️', building: 'Biblioteca', description: 'Documenta y redacta para el sistema', quick_tasks: ['Generar documentación', 'Escribir README', 'Documentar API endpoints'], status: 'idle', gradient: ['#6A1B9A', '#8E24AA'] },
  { name: 'Optimizer', emoji: '⚡', building: 'Palacio de Patrones', description: 'Optimiza rendimiento y patrones', quick_tasks: ['Optimizar queries lentas', 'Reducir bundle size', 'Mejorar tiempos de carga'], status: 'idle', gradient: ['#E65100', '#F57C00'] },
  { name: 'Guard', emoji: '🛡️', building: 'Estación de Seguridad', description: 'Vigila la seguridad del sistema', quick_tasks: ['Auditoría de seguridad', 'Revisar permisos', 'Detectar vulnerabilidades'], status: 'idle', gradient: ['#1B5E20', '#388E3C'] },
  { name: 'Sage', emoji: '🧙', building: 'Torre del Sabio', description: 'Ofrece sabiduría y estrategia', quick_tasks: ['Sugerir refactoring', 'Revisar decisiones técnicas', 'Proponer mejoras de diseño'], status: 'idle', gradient: ['#4A148C', '#7B1FA2'] },
  { name: 'Robot', emoji: '🤖', building: 'Fábrica de Workflows', description: 'Automatiza flujos de trabajo', quick_tasks: ['Crear pipeline CI/CD', 'Automatizar deploy', 'Generar scripts de migración'], status: 'idle', gradient: ['#263238', '#455A64'] },
];

const API_BASE = 'http://localhost:8000/api/v1/observatory';
const MISSIONS_API = 'http://localhost:8000/api/v1/missions';

// ─── Keyframes (injected once) ──────────────────────────────────────────────────

const STYLE_ID = 'observatory-keyframes';

function injectKeyframes() {
  if (typeof document === 'undefined') return;
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes obs-pulse {
      0%, 100% { box-shadow: 0 0 8px 2px rgba(255,165,0,0.4); }
      50% { box-shadow: 0 0 20px 6px rgba(255,165,0,0.8); }
    }
    @keyframes obs-spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes obs-flash-green {
      0% { box-shadow: 0 0 0 0 rgba(76,175,80,0.7); }
      50% { box-shadow: 0 0 24px 8px rgba(76,175,80,0.9); }
      100% { box-shadow: 0 0 0 0 rgba(76,175,80,0); }
    }
    @keyframes obs-fade-in {
      from { opacity: 0; transform: scale(0.95); }
      to { opacity: 1; transform: scale(1); }
    }
    @keyframes obs-crew-glow {
      0%, 100% { box-shadow: 0 0 8px 2px rgba(255,215,0,0.3); }
      50% { box-shadow: 0 0 24px 8px rgba(255,215,0,0.8); }
    }
  `;
  document.head.appendChild(style);
}

// ─── Main Component ─────────────────────────────────────────────────────────────

export function ObservatoryNodeLayout(_props: ObservatoryNodeLayoutProps) {
  const [agents, setAgents] = useState<ObservatoryAgent[]>(DEFAULT_AGENTS);
  const [tasks, setTasks] = useState<ObservatoryTask[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<ObservatoryAgent | null>(null);
  const [taskInput, setTaskInput] = useState('');
  const [taskSending, setTaskSending] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // CREW state
  const [crewOpen, setCrewOpen] = useState(false);
  const [crewTitle, setCrewTitle] = useState('');
  const [crewDesc, setCrewDesc] = useState('');
  const [crewAgents, setCrewAgents] = useState<string[]>([]);
  const [crewSending, setCrewSending] = useState(false);
  const [activeMission, setActiveMission] = useState<CrewMission | null>(null);

  // Missions bridge state
  const [missions, setMissions] = useState<BridgeMission[]>([]);
  const [missionsOpen, setMissionsOpen] = useState(false);
  const [missionToast, setMissionToast] = useState('');

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const crewPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Inject CSS keyframes on mount
  useEffect(() => { injectKeyframes(); }, []);

  // ─── Fetch agents from backend ──────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/agents`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setAgents(prev => prev.map(a => {
              const remote = data.find((r: Record<string, unknown>) => r.name === a.name);
              if (remote) {
                return {
                  ...a,
                  description: (remote.description as string) || a.description,
                  quick_tasks: Array.isArray(remote.quick_tasks) ? remote.quick_tasks : a.quick_tasks,
                };
              }
              return a;
            }));
          }
        }
      } catch { /* backend not reachable, use defaults */ }
    })();
  }, []);

  // ─── Fetch tasks ────────────────────────────────────────────────────────────
  const fetchTasks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setTasks(data);
        else if (data.tasks) setTasks(data.tasks);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  // ─── Poll running tasks ────────────────────────────────────────────────────
  useEffect(() => {
    const hasRunning = tasks.some(t => t.status === 'running' || t.status === 'pending');
    if (hasRunning) {
      if (!pollRef.current) {
        pollRef.current = setInterval(async () => {
          await fetchTasks();
        }, 3000);
      }
    } else {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };
  }, [tasks, fetchTasks]);

  // ─── Sync agent status from tasks ──────────────────────────────────────────
  useEffect(() => {
    setAgents(prev => prev.map(a => {
      const agentTasks = tasks.filter(t => t.agent_name === a.name);
      const running = agentTasks.find(t => t.status === 'running' || t.status === 'pending');
      if (running) return { ...a, status: 'working' as const, currentTask: running.description };
      const recentDone = agentTasks.find(t => t.status === 'completed');
      if (recentDone) return { ...a, status: 'done' as const, currentTask: undefined };
      return { ...a, status: 'idle' as const, currentTask: undefined };
    }));
  }, [tasks]);

  // ─── Assign task ────────────────────────────────────────────────────────────
  const assignTask = useCallback(async (agentName: string, description: string) => {
    if (!description.trim()) return;
    setTaskSending(true);
    try {
      const res = await fetch(`${API_BASE}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: agentName, description }),
      });
      if (res.ok) {
        setTaskInput('');
        setSelectedAgent(null);
        await fetchTasks();
      }
    } catch { /* ignore */ }
    setTaskSending(false);
  }, [fetchTasks]);

  // ─── CREW mission ──────────────────────────────────────────────────────────
  const startCrewMission = useCallback(async () => {
    if (!crewTitle.trim() || !crewDesc.trim() || crewAgents.length === 0) return;
    setCrewSending(true);
    try {
      const res = await fetch(`${API_BASE}/crew`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: crewTitle, description: crewDesc, agent_sequence: crewAgents }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveMission(data);
        setCrewOpen(false);
        setCrewTitle('');
        setCrewDesc('');
        setCrewAgents([]);
      }
    } catch { /* ignore */ }
    setCrewSending(false);
  }, [crewTitle, crewDesc, crewAgents]);

  // ─── Poll crew mission ─────────────────────────────────────────────────────
  useEffect(() => {
    if (activeMission && activeMission.status !== 'completed' && activeMission.status !== 'error') {
      crewPollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/crew/${activeMission.id}`);
          if (res.ok) {
            const data = await res.json();
            setActiveMission(data);
            if (data.status === 'completed' || data.status === 'error') {
              if (crewPollRef.current) clearInterval(crewPollRef.current);
              await fetchTasks();
            }
          }
        } catch { /* ignore */ }
      }, 3000);
    }
    return () => { if (crewPollRef.current) { clearInterval(crewPollRef.current); crewPollRef.current = null; } };
  }, [activeMission, fetchTasks]);

  const toggleCrewAgent = useCallback((name: string) => {
    setCrewAgents(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  }, []);

  // ─── Missions bridge ───────────────────────────────────────────────────────
  const fetchMissions = useCallback(async () => {
    try {
      const res = await fetch(`${MISSIONS_API}?limit=20`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) setMissions(data);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchMissions(); }, [fetchMissions]);

  const createMissionFromTask = useCallback(async (task: ObservatoryTask) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${task.id}/to-mission`, { method: 'POST' });
      if (res.ok) {
        setMissionToast('✅ Misión creada desde tarea');
        await fetchMissions();
      } else {
        const err = await res.json().catch(() => ({ detail: 'Error' }));
        setMissionToast(`❌ ${err.detail || 'Error al crear misión'}`);
      }
    } catch { setMissionToast('❌ Error de conexión'); }
  }, [fetchMissions]);

  const sendMissionToWorkshop = useCallback(async (missionId: string) => {
    try {
      const res = await fetch(`${MISSIONS_API}/${missionId}/send-to-workshop`, { method: 'POST' });
      if (res.ok) {
        setMissionToast('🏗️ Misión enviada al Workshop');
        await fetchMissions();
      } else {
        const err = await res.json().catch(() => ({ detail: 'Error' }));
        setMissionToast(`❌ ${err.detail || 'Error al enviar'}`);
      }
    } catch { setMissionToast('❌ Error de conexión'); }
  }, [fetchMissions]);

  // Auto-clear toast
  useEffect(() => {
    if (missionToast) {
      const t = setTimeout(() => setMissionToast(''), 3000);
      return () => clearTimeout(t);
    }
  }, [missionToast]);

  // ─── Filtered tasks ────────────────────────────────────────────────────────
  const filteredTasks = tasks.filter(t => {
    if (filterAgent !== 'all' && t.agent_name !== filterAgent) return false;
    if (filterStatus !== 'all' && t.status !== filterStatus) return false;
    return true;
  });

  // ─── Status helpers ─────────────────────────────────────────────────────────
  const statusBadge = (status: string) => {
    const map: Record<string, { bg: string; text: string; label: string }> = {
      idle: { bg: '#555', text: '#aaa', label: '💤 Inactivo' },
      working: { bg: '#E65100', text: '#fff', label: '🔄 Trabajando' },
      done: { bg: '#2E7D32', text: '#fff', label: '✅ Listo' },
      pending: { bg: '#795548', text: '#fff', label: '⏳ Pendiente' },
      running: { bg: '#E65100', text: '#fff', label: '🔄 Ejecutando' },
      completed: { bg: '#2E7D32', text: '#fff', label: '✅ Completado' },
      error: { bg: '#C62828', text: '#fff', label: '❌ Error' },
    };
    const s = map[status] || map.idle;
    return (
      <span style={{ background: s.bg, color: s.text, padding: '2px 8px', borderRadius: 8, fontSize: 11, fontWeight: 600 }}>
        {s.label}
      </span>
    );
  };

  const agentEmoji = (name: string) => {
    const a = agents.find(ag => ag.name === name);
    return a ? a.emoji : '🔭';
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTime = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch { return iso; }
  };

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: 'linear-gradient(180deg, #0a1a0a 0%, #1B5E20 40%, #0d260d 100%)',
      fontFamily: "'Segoe UI', system-ui, sans-serif", color: '#e0e0e0', overflow: 'hidden',
    }}>
      {/* ═══ HEADER ═══ */}
      <div style={{
        padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid rgba(76,175,80,0.3)',
        background: 'linear-gradient(90deg, rgba(27,94,32,0.6) 0%, rgba(10,26,10,0.8) 100%)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 28 }}>🔭</span>
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: 1 }}>OBSERVATORY TOWN</span>
          <span style={{ fontSize: 12, color: '#81C784', marginLeft: 8 }}>
            {agents.filter(a => a.status === 'working').length} agentes activos
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => { setMissionsOpen(!missionsOpen); fetchMissions(); }}
            style={{
              background: 'linear-gradient(135deg, #1565C0, #1976D2)', border: 'none', color: '#fff',
              padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontWeight: 700, fontSize: 13,
              transition: 'transform 0.15s', position: 'relative',
            }}
            onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.05)')}
            onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
          >
            📋 Misiones
            {missions.filter(m => m.status === 'pending').length > 0 && (
              <span style={{
                position: 'absolute', top: -6, right: -6,
                background: '#f44336', color: '#fff', fontSize: 10, fontWeight: 700,
                width: 18, height: 18, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {missions.filter(m => m.status === 'pending').length}
              </span>
            )}
          </button>
          <button
            onClick={() => setCrewOpen(true)}
            style={{
              background: 'linear-gradient(135deg, #FF6F00, #FFA000)', border: 'none', color: '#fff',
              padding: '8px 16px', borderRadius: 8, cursor: 'pointer', fontWeight: 700, fontSize: 13,
              transition: 'transform 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.05)')}
            onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
          >🎯 Nueva Misión (CREW)</button>
          <button
            onClick={fetchTasks}
            style={{
              background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
              color: '#ccc', padding: '8px 14px', borderRadius: 8, cursor: 'pointer', fontSize: 13,
            }}
          >📋 Actualizar</button>
        </div>
      </div>

      {/* ═══ MAIN CONTENT ═══ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* ─── TOWN VIEW: Agent Buildings Grid ─── */}
        <div style={{
          padding: '16px 20px', flex: '0 0 auto',
          backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(76,175,80,0.08) 0%, transparent 50%), radial-gradient(circle at 80% 30%, rgba(76,175,80,0.05) 0%, transparent 50%)',
        }}>
          {/* Active Mission Banner */}
          {activeMission && activeMission.status !== 'completed' && activeMission.status !== 'error' && (
            <div style={{
              marginBottom: 12, padding: '10px 16px', borderRadius: 10,
              background: 'linear-gradient(90deg, rgba(255,152,0,0.2), rgba(255,193,7,0.1))',
              border: '1px solid rgba(255,152,0,0.4)', display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{ fontSize: 20, animation: 'obs-spin 2s linear infinite', display: 'inline-block' }}>🎯</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13 }}>Misión en curso: {activeMission.title}</div>
                <div style={{ fontSize: 11, color: '#aaa' }}>
                  Agente actual: {activeMission.agent_sequence[activeMission.current_agent_index] || '...'} 
                  ({activeMission.current_agent_index + 1}/{activeMission.agent_sequence.length})
                </div>
              </div>
            </div>
          )}

          {/* Building Cards Grid */}
          <div className="obs-grid-override" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 14,
          }}>
            {agents.map((agent, idx) => {
              const isWorking = agent.status === 'working';
              const isDone = agent.status === 'done';
              const isCrewActive = activeMission &&
                activeMission.status !== 'completed' &&
                activeMission.agent_sequence[activeMission.current_agent_index] === agent.name;

              return (
                <div
                  key={agent.name}
                  onClick={() => { setSelectedAgent(agent); setTaskInput(''); }}
                  style={{
                    background: `linear-gradient(135deg, ${agent.gradient[0]}, ${agent.gradient[1]})`,
                    borderRadius: 12, padding: '14px 12px', cursor: 'pointer',
                    border: isCrewActive
                      ? '2px solid #FFD700'
                      : isWorking
                        ? '2px solid #FF9800'
                        : '2px solid rgba(255,255,255,0.1)',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    animation: isCrewActive
                      ? 'obs-crew-glow 1.5s ease-in-out infinite'
                      : isWorking
                        ? 'obs-pulse 2s ease-in-out infinite'
                        : isDone
                          ? 'obs-flash-green 1s ease-out'
                          : 'none',
                    position: 'relative', overflow: 'hidden',
                    minHeight: 140,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-4px) scale(1.02)';
                    e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.4)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0) scale(1)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {/* Building Name */}
                  <div style={{
                    fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1,
                    color: 'rgba(255,255,255,0.7)', marginBottom: 6, textAlign: 'center',
                  }}>
                    {agent.building}
                  </div>

                  {/* Emoji */}
                  <div style={{
                    fontSize: 48, lineHeight: 1, marginBottom: 6,
                    animation: isWorking ? 'obs-spin 3s linear infinite' : 'none',
                    display: 'inline-block',
                  }}>
                    {agent.emoji}
                  </div>

                  {/* Agent Name */}
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 4 }}>
                    {agent.name}
                  </div>

                  {/* Status Badge */}
                  {statusBadge(agent.status)}

                  {/* Current Task Preview */}
                  {isWorking && agent.currentTask && (
                    <div style={{
                      fontSize: 10, color: 'rgba(255,255,255,0.6)', marginTop: 4,
                      textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      maxWidth: '90%',
                    }}>
                      {agent.currentTask}
                    </div>
                  )}

                  {/* Crew sequence indicator */}
                  {activeMission && activeMission.agent_sequence.includes(agent.name) && (
                    <div style={{
                      position: 'absolute', top: 6, right: 8, fontSize: 10, fontWeight: 700,
                      background: 'rgba(255,215,0,0.3)', color: '#FFD700', padding: '1px 6px', borderRadius: 6,
                    }}>
                      #{activeMission.agent_sequence.indexOf(agent.name) + 1}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ─── TASK HISTORY PANEL ─── */}
        <div style={{
          flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column',
          borderTop: '1px solid rgba(76,175,80,0.2)',
          background: 'rgba(0,0,0,0.3)',
        }}>
          {/* Filters */}
          <div style={{
            padding: '10px 20px', display: 'flex', alignItems: 'center', gap: 12,
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(0,0,0,0.2)',
          }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#81C784' }}>📋 Historial de Tareas</span>
            <select
              value={filterAgent}
              onChange={e => setFilterAgent(e.target.value)}
              style={{
                background: '#1a2a1a', border: '1px solid #333', color: '#ccc',
                padding: '4px 8px', borderRadius: 6, fontSize: 11,
              }}
            >
              <option value="all">Todos los agentes</option>
              {agents.map(a => (
                <option key={a.name} value={a.name}>{a.emoji} {a.name}</option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              style={{
                background: '#1a2a1a', border: '1px solid #333', color: '#ccc',
                padding: '4px 8px', borderRadius: 6, fontSize: 11,
              }}
            >
              <option value="all">Todos los estados</option>
              <option value="pending">⏳ Pendiente</option>
              <option value="running">🔄 Ejecutando</option>
              <option value="completed">✅ Completado</option>
              <option value="error">❌ Error</option>
            </select>
            <span style={{ fontSize: 11, color: '#666', marginLeft: 'auto' }}>
              {filteredTasks.length} tarea{filteredTasks.length !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Task List */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 20px' }}>
            {filteredTasks.length === 0 ? (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100%', color: '#555', fontSize: 14,
              }}>
                🔭 No hay tareas aún — haz clic en un edificio para asignar una
              </div>
            ) : (
              filteredTasks.map(task => (
                <div key={task.id} style={{ marginBottom: 6 }}>
                  {/* Row */}
                  <div
                    onClick={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      background: expandedTaskId === task.id ? 'rgba(76,175,80,0.1)' : 'rgba(255,255,255,0.03)',
                      borderRadius: 8, cursor: 'pointer',
                      border: expandedTaskId === task.id ? '1px solid rgba(76,175,80,0.3)' : '1px solid transparent',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => { if (expandedTaskId !== task.id) e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
                    onMouseLeave={e => { if (expandedTaskId !== task.id) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                  >
                    <span style={{ fontSize: 18 }}>{agentEmoji(task.agent_name)}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#ccc', minWidth: 70 }}>{task.agent_name}</span>
                    <span style={{
                      fontSize: 12, color: '#999', flex: 1,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>{task.description}</span>
                    {statusBadge(task.status)}
                    {task.duration_ms > 0 && (
                      <span style={{ fontSize: 11, color: '#666', minWidth: 50, textAlign: 'right' }}>
                        ⏱ {formatDuration(task.duration_ms)}
                      </span>
                    )}
                    <span style={{ fontSize: 10, color: '#555', minWidth: 60, textAlign: 'right' }}>
                      {formatTime(task.created_at)}
                    </span>
                    <span style={{ fontSize: 11, color: '#555', transition: 'transform 0.2s', transform: expandedTaskId === task.id ? 'rotate(90deg)' : 'rotate(0deg)' }}>
                      ▶
                    </span>
                  </div>

                  {/* Expanded Result */}
                  {expandedTaskId === task.id && (
                    <div style={{
                      margin: '4px 0 4px 40px', padding: '12px 16px',
                      background: 'rgba(0,0,0,0.4)', borderRadius: 8,
                      border: '1px solid rgba(255,255,255,0.08)',
                      animation: 'obs-fade-in 0.2s ease-out',
                      maxHeight: 300, overflowY: 'auto',
                    }}>
                      {task.result_output ? (
                        <>
                          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#ddd' }}>
                            <ReactMarkdown>{task.result_output}</ReactMarkdown>
                          </div>
                          {task.status === 'completed' && (
                            <button
                              onClick={(e) => { e.stopPropagation(); createMissionFromTask(task); }}
                              style={{
                                marginTop: 8, background: 'linear-gradient(135deg, #1565C0, #1976D2)',
                                border: 'none', color: '#fff', padding: '6px 14px', borderRadius: 6,
                                cursor: 'pointer', fontWeight: 600, fontSize: 12,
                              }}
                            >📋 Crear Misión</button>
                          )}
                        </>
                      ) : (
                        <div style={{ fontSize: 12, color: '#666', fontStyle: 'italic' }}>
                          {task.status === 'running' ? '🔄 Procesando...' : 'Sin resultado disponible'}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* ─── Active Mission Results ─── */}
        {activeMission && activeMission.results && activeMission.results.length > 0 && (
          <div style={{
            borderTop: '1px solid rgba(255,152,0,0.3)',
            background: 'rgba(255,152,0,0.05)', padding: '12px 20px',
            maxHeight: 200, overflowY: 'auto',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#FFA000', marginBottom: 8 }}>
              🎯 Resultados de Misión: {activeMission.title}
              {activeMission.status === 'completed' && <span style={{ color: '#4CAF50', marginLeft: 8 }}>✅ Completada</span>}
              {activeMission.status === 'error' && <span style={{ color: '#f44336', marginLeft: 8 }}>❌ Error</span>}
            </div>
            {activeMission.results.map((r, i) => (
              <div key={i} style={{
                marginBottom: 8, padding: '8px 12px', background: 'rgba(0,0,0,0.3)',
                borderRadius: 8, border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#FFB74D', marginBottom: 4 }}>
                  {agentEmoji(r.agent)} {r.agent}
                </div>
                <div style={{ fontSize: 12, color: '#ccc', lineHeight: 1.5 }}>
                  <ReactMarkdown>{r.output}</ReactMarkdown>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ═══ AGENT DIALOG (MODAL) ═══ */}
      {selectedAgent && (
        <div
          onClick={() => setSelectedAgent(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '90%', maxWidth: 600,
              background: 'linear-gradient(180deg, #1a2a1a 0%, #0d1a0d 100%)',
              borderRadius: 16, border: '1px solid rgba(76,175,80,0.3)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
              animation: 'obs-fade-in 0.25s ease-out',
              overflow: 'hidden',
            }}
          >
            {/* Dialog Header */}
            <div style={{
              padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 16,
              background: `linear-gradient(135deg, ${selectedAgent.gradient[0]}88, ${selectedAgent.gradient[1]}44)`,
              borderBottom: '1px solid rgba(255,255,255,0.1)',
            }}>
              <span style={{ fontSize: 56 }}>{selectedAgent.emoji}</span>
              <div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>{selectedAgent.name}</div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)' }}>{selectedAgent.building}</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>{selectedAgent.description}</div>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                style={{
                  marginLeft: 'auto', background: 'rgba(255,255,255,0.1)', border: 'none',
                  color: '#aaa', width: 32, height: 32, borderRadius: 8, cursor: 'pointer', fontSize: 16,
                }}
              >✕</button>
            </div>

            {/* Working State */}
            {selectedAgent.status === 'working' && (
              <div style={{
                padding: '12px 24px', background: 'rgba(255,152,0,0.1)',
                borderBottom: '1px solid rgba(255,152,0,0.2)',
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <span style={{ animation: 'obs-spin 2s linear infinite', display: 'inline-block', fontSize: 18 }}>⏳</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#FFA000' }}>Trabajando en una tarea</div>
                  <div style={{ fontSize: 11, color: '#aaa' }}>{selectedAgent.currentTask}</div>
                </div>
              </div>
            )}

            {/* Task Input */}
            <div style={{ padding: '20px 24px' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#81C784', marginBottom: 10 }}>
                ¿Qué quieres que haga?
              </div>

              {/* Quick Task Chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
                {selectedAgent.quick_tasks.map((qt, i) => (
                  <button
                    key={i}
                    onClick={() => setTaskInput(qt)}
                    style={{
                      background: 'rgba(76,175,80,0.15)', border: '1px solid rgba(76,175,80,0.3)',
                      color: '#A5D6A7', padding: '5px 12px', borderRadius: 20, cursor: 'pointer',
                      fontSize: 11, transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = 'rgba(76,175,80,0.3)';
                      e.currentTarget.style.color = '#fff';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = 'rgba(76,175,80,0.15)';
                      e.currentTarget.style.color = '#A5D6A7';
                    }}
                  >{qt}</button>
                ))}
              </div>

              {/* Input + Send */}
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  value={taskInput}
                  onChange={e => setTaskInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); assignTask(selectedAgent.name, taskInput); } }}
                  placeholder="Describe la tarea..."
                  style={{
                    flex: 1, background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)',
                    color: '#e0e0e0', padding: '10px 14px', borderRadius: 10, fontSize: 13,
                    outline: 'none',
                  }}
                />
                <button
                  onClick={() => assignTask(selectedAgent.name, taskInput)}
                  disabled={taskSending || !taskInput.trim()}
                  style={{
                    background: taskSending ? '#555' : 'linear-gradient(135deg, #4CAF50, #66BB6A)',
                    border: 'none', color: '#fff', padding: '10px 20px', borderRadius: 10,
                    cursor: taskSending ? 'wait' : 'pointer', fontWeight: 700, fontSize: 13,
                    opacity: !taskInput.trim() ? 0.5 : 1,
                    transition: 'opacity 0.15s',
                  }}
                >
                  {taskSending ? '⏳' : '🚀'} Asignar tarea
                </button>
              </div>
            </div>

            {/* Recent Results for this Agent */}
            {(() => {
              const agentResults = tasks.filter(t => t.agent_name === selectedAgent.name && t.result_output);
              if (agentResults.length === 0) return null;
              const latest = agentResults[0];
              return (
                <div style={{
                  padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.08)',
                  background: 'rgba(0,0,0,0.2)',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#81C784', marginBottom: 8 }}>
                    Último resultado
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
                    {latest.description} — {statusBadge(latest.status)}
                    {latest.duration_ms > 0 && <span style={{ marginLeft: 8 }}>⏱ {formatDuration(latest.duration_ms)}</span>}
                  </div>
                  <div style={{
                    background: 'rgba(0,0,0,0.4)', borderRadius: 8, padding: '10px 14px',
                    maxHeight: 200, overflowY: 'auto', fontSize: 13, lineHeight: 1.6, color: '#ddd',
                  }}>
                    <ReactMarkdown>{latest.result_output}</ReactMarkdown>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* ═══ TOAST NOTIFICATION ═══ */}
      {missionToast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 2000,
          background: 'rgba(0,0,0,0.85)', color: '#fff', padding: '12px 20px',
          borderRadius: 10, fontSize: 13, fontWeight: 600, boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
          animation: 'obs-fade-in 0.2s ease-out',
          border: '1px solid rgba(255,255,255,0.15)',
        }}>
          {missionToast}
        </div>
      )}

      {/* ═══ MISSIONS PANEL (MODAL) ═══ */}
      {missionsOpen && (
        <div
          onClick={() => setMissionsOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '90%', maxWidth: 640, maxHeight: '80vh',
              background: 'linear-gradient(180deg, #0d1a2e 0%, #0d0d1a 100%)',
              borderRadius: 16, border: '1px solid rgba(21,101,192,0.3)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
              animation: 'obs-fade-in 0.25s ease-out',
              overflow: 'hidden', display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '16px 24px', display: 'flex', alignItems: 'center', gap: 12,
              background: 'linear-gradient(135deg, rgba(21,101,192,0.3), rgba(25,118,210,0.1))',
              borderBottom: '1px solid rgba(21,101,192,0.2)',
            }}>
              <span style={{ fontSize: 28 }}>📋</span>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#90CAF9' }}>Misiones</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                  {missions.length} misión{missions.length !== 1 ? 'es' : ''} — Puente Observatory ↔ Workshop
                </div>
              </div>
              <button
                onClick={() => setMissionsOpen(false)}
                style={{
                  marginLeft: 'auto', background: 'rgba(255,255,255,0.1)', border: 'none',
                  color: '#aaa', width: 32, height: 32, borderRadius: 8, cursor: 'pointer', fontSize: 16,
                }}
              >✕</button>
            </div>

            {/* Mission list */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '12px 24px' }}>
              {missions.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#555', padding: '40px 0', fontSize: 14 }}>
                  No hay misiones aún. Completa una tarea y crea una misión desde el resultado.
                </div>
              ) : (
                missions.map(m => (
                  <div key={m.id} style={{
                    marginBottom: 10, padding: '12px 16px', borderRadius: 10,
                    background: 'rgba(255,255,255,0.04)',
                    border: m.status === 'pending' ? '1px solid rgba(21,101,192,0.3)' : '1px solid rgba(255,255,255,0.06)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 14 }}>
                        {m.origin === 'observatory' ? '🔭' : '👤'}
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: '#ddd', flex: 1 }}>
                        {m.title}
                      </span>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 8, fontWeight: 600,
                        background: m.status === 'pending' ? 'rgba(21,101,192,0.2)' : m.status === 'completed' ? 'rgba(76,175,80,0.2)' : 'rgba(255,152,0,0.2)',
                        color: m.status === 'pending' ? '#90CAF9' : m.status === 'completed' ? '#A5D6A7' : '#FFB74D',
                      }}>
                        {m.status}
                      </span>
                    </div>
                    {m.created_by && m.created_by !== 'user' && (
                      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>
                        Agente: {m.created_by}
                      </div>
                    )}
                    {m.finding && (
                      <div style={{ fontSize: 11, color: '#999', marginBottom: 6, maxHeight: 60, overflow: 'hidden' }}>
                        {m.finding.slice(0, 200)}…
                      </div>
                    )}
                    {(m.status === 'pending' || m.status === 'spec_review') && (
                      <button
                        onClick={() => sendMissionToWorkshop(m.id)}
                        style={{
                          background: 'linear-gradient(135deg, #FF9800, #F57C00)', border: 'none',
                          color: '#fff', padding: '5px 12px', borderRadius: 6,
                          cursor: 'pointer', fontWeight: 600, fontSize: 11,
                        }}
                      >🏗️ Enviar al Workshop</button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ CREW MISSION MODAL ═══ */}
      {crewOpen && (
        <div
          onClick={() => setCrewOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '90%', maxWidth: 560,
              background: 'linear-gradient(180deg, #1a1a2e 0%, #0d0d1a 100%)',
              borderRadius: 16, border: '1px solid rgba(255,152,0,0.3)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
              animation: 'obs-fade-in 0.25s ease-out',
              overflow: 'hidden',
            }}
          >
            {/* Crew Header */}
            <div style={{
              padding: '20px 24px',
              background: 'linear-gradient(135deg, rgba(255,111,0,0.3), rgba(255,160,0,0.1))',
              borderBottom: '1px solid rgba(255,152,0,0.2)',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontSize: 32 }}>🎯</span>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#FFB74D' }}>Nueva Misión CREW</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                  Selecciona agentes y define la misión
                </div>
              </div>
              <button
                onClick={() => setCrewOpen(false)}
                style={{
                  marginLeft: 'auto', background: 'rgba(255,255,255,0.1)', border: 'none',
                  color: '#aaa', width: 32, height: 32, borderRadius: 8, cursor: 'pointer', fontSize: 16,
                }}
              >✕</button>
            </div>

            {/* Crew Form */}
            <div style={{ padding: '20px 24px' }}>
              {/* Title */}
              <label style={{ fontSize: 12, fontWeight: 600, color: '#FFB74D', display: 'block', marginBottom: 6 }}>
                Título de la misión
              </label>
              <input
                value={crewTitle}
                onChange={e => setCrewTitle(e.target.value)}
                placeholder="Ej: Auditoría completa del sistema"
                style={{
                  width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)',
                  color: '#e0e0e0', padding: '10px 14px', borderRadius: 10, fontSize: 13,
                  outline: 'none', marginBottom: 14, boxSizing: 'border-box',
                }}
              />

              {/* Description */}
              <label style={{ fontSize: 12, fontWeight: 600, color: '#FFB74D', display: 'block', marginBottom: 6 }}>
                Describe la misión
              </label>
              <textarea
                value={crewDesc}
                onChange={e => setCrewDesc(e.target.value)}
                placeholder="Describe lo que quieres lograr..."
                rows={3}
                style={{
                  width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)',
                  color: '#e0e0e0', padding: '10px 14px', borderRadius: 10, fontSize: 13,
                  outline: 'none', resize: 'vertical', marginBottom: 14, boxSizing: 'border-box',
                  fontFamily: 'inherit',
                }}
              />

              {/* Agent Picker */}
              <label style={{ fontSize: 12, fontWeight: 600, color: '#FFB74D', display: 'block', marginBottom: 8 }}>
                Selecciona agentes (en orden de ejecución)
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6, marginBottom: 14 }}>
                {agents.map(a => {
                  const isSelected = crewAgents.includes(a.name);
                  const idx = crewAgents.indexOf(a.name);
                  return (
                    <div
                      key={a.name}
                      onClick={() => toggleCrewAgent(a.name)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                        background: isSelected ? 'rgba(255,152,0,0.2)' : 'rgba(255,255,255,0.03)',
                        border: isSelected ? '1px solid rgba(255,152,0,0.5)' : '1px solid rgba(255,255,255,0.08)',
                        borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s',
                      }}
                    >
                      <span style={{ fontSize: 20 }}>{a.emoji}</span>
                      <span style={{ fontSize: 12, fontWeight: 600, color: isSelected ? '#FFB74D' : '#aaa' }}>
                        {a.name}
                      </span>
                      {isSelected && (
                        <span style={{
                          marginLeft: 'auto', background: '#FF6F00', color: '#fff',
                          width: 20, height: 20, borderRadius: '50%', display: 'flex',
                          alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700,
                        }}>
                          {idx + 1}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Selected order preview */}
              {crewAgents.length > 0 && (
                <div style={{ fontSize: 11, color: '#888', marginBottom: 14 }}>
                  Orden: {crewAgents.map((n, i) => `${i + 1}. ${agentEmoji(n)} ${n}`).join(' → ')}
                </div>
              )}

              {/* Submit */}
              <button
                onClick={startCrewMission}
                disabled={crewSending || !crewTitle.trim() || !crewDesc.trim() || crewAgents.length === 0}
                style={{
                  width: '100%',
                  background: crewSending ? '#555' : 'linear-gradient(135deg, #FF6F00, #FFA000)',
                  border: 'none', color: '#fff', padding: '12px', borderRadius: 10,
                  cursor: crewSending ? 'wait' : 'pointer', fontWeight: 700, fontSize: 14,
                  opacity: (!crewTitle.trim() || !crewDesc.trim() || crewAgents.length === 0) ? 0.5 : 1,
                  transition: 'opacity 0.15s',
                }}
              >
                {crewSending ? '⏳ Iniciando...' : '🚀 Iniciar Misión'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Responsive: inject media query ═══ */}
      <style>{`
        @media (max-width: 800px) {
          .obs-grid-override { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>
    </div>
  );
}

export default ObservatoryNodeLayout;
