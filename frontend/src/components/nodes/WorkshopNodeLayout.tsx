/**
 * WorkshopNodeLayout.tsx — YeyoOS Workshop (Fábrica de Código)
 *
 * Layout 3 paneles + barra inferior:
 *   Left:   Gates Pipeline (200px)
 *   Center: Code Editor (Monaco / fallback <pre>)
 *   Right:  Terminal + Preview (split vertical)
 *   Bottom: Progress bar + controles
 */
'use client';

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from 'react';
import dynamic from 'next/dynamic';

// Monaco — dynamic import for SSR safety
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div style={{ width: '100%', height: '100%', background: '#1e1e1e', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#555', fontFamily: 'monospace' }}>
      Cargando editor…
    </div>
  ),
});

// ─── Constants ──────────────────────────────────────────────────────────────────

const API_BASE = 'http://localhost:8000/api/v1/workshop';
const MISSIONS_API = 'http://localhost:8000/api/v1/missions';

const GATE_NAMES: Record<number, string> = {
  0: 'Spec',
  1: 'Arquitectura',
  2: 'Coder',
  3: 'AST Validación',
  4: 'Type Check',
  5: 'Auto Tests',
  6: 'Cobertura',
  7: 'Seguridad',
  8: 'Rendimiento',
  9: 'Documentación',
  10: 'Linting',
  11: 'Edge Cases',
  12: 'Integración',
  13: 'Refactor',
  14: 'Revisión Final',
  15: 'Aprobación Humana',
  16: 'Contrato',
};

const STATUS_ICONS: Record<GateStatusValue, string> = {
  pending: '⬜',
  running: '⏳',
  passed: '✅',
  failed: '❌',
  skipped: '⏭️',
  waiting_approval: '⏸',
};

const STATUS_COLORS: Record<GateStatusValue, string> = {
  pending: '#6b7280',
  running: '#f59e0b',
  passed: '#22c55e',
  failed: '#ef4444',
  skipped: '#6b7280',
  waiting_approval: '#eab308',
};

// ─── Types ──────────────────────────────────────────────────────────────────────

type GateStatusValue = 'pending' | 'running' | 'passed' | 'failed' | 'skipped' | 'waiting_approval';

export interface GateStatus {
  gate_number: number;
  gate_name: string;
  status: GateStatusValue;
  output: string;
  duration_ms: number;
  attempts: number;
}

export interface MissionSpec {
  inputs: Array<{ name: string; type: string }>;
  outputs: Array<{ name: string; type: string }>;
  edge_cases: string[];
  error_handling: string[];
  constraints: string[];
  acceptance_criteria: string[];
}

export interface WorkshopMission {
  id: string;
  title: string;
  description?: string;
  status: string;
  spec: MissionSpec;
  gates: GateStatus[];
  code_files: Array<{ name: string; content: string }>;
}

export interface WorkshopNodeLayoutProps {
  missionId?: string;
}

// ─── Quick Templates ────────────────────────────────────────────────────────────

interface QuickTemplate {
  label: string;
  title: string;
  description: string;
  spec: MissionSpec;
}

const QUICK_TEMPLATES: QuickTemplate[] = [
  {
    label: '🔢 Función de ordenamiento',
    title: 'Función de Ordenamiento',
    description: 'Implementar una función de ordenamiento eficiente con validación de tipos',
    spec: {
      inputs: [{ name: 'arr', type: 'List[int]' }],
      outputs: [{ name: 'sorted_arr', type: 'List[int]' }],
      edge_cases: ['Lista vacía', 'Un solo elemento', 'Elementos duplicados', 'Lista ya ordenada', 'Números negativos'],
      error_handling: ['TypeError si no es lista', 'TypeError si contiene no-numéricos'],
      constraints: ['Complejidad O(n log n)', 'No modificar lista original'],
      acceptance_criteria: ['Ordena correctamente ascendente', 'Maneja listas de 10k+ elementos', 'Pasa todos los edge cases'],
    },
  },
  {
    label: '🌐 API Endpoint',
    title: 'API REST Endpoint',
    description: 'Crear un endpoint REST con validación, autenticación y manejo de errores',
    spec: {
      inputs: [{ name: 'request_body', type: 'dict' }, { name: 'auth_token', type: 'str' }],
      outputs: [{ name: 'response', type: 'JSONResponse' }],
      edge_cases: ['Token expirado', 'Body vacío', 'Campos faltantes', 'Rate limit excedido'],
      error_handling: ['401 para auth inválida', '422 para validación', '500 para errores internos'],
      constraints: ['Latencia < 200ms', 'Usar Pydantic para validación'],
      acceptance_criteria: ['CRUD completo', 'Tests de integración', 'Documentación OpenAPI'],
    },
  },
  {
    label: '🔧 Clase de utilidad',
    title: 'Clase de Utilidad',
    description: 'Crear una clase de utilidad reutilizable con interfaz limpia',
    spec: {
      inputs: [{ name: 'config', type: 'dict' }],
      outputs: [{ name: 'instance', type: 'UtilityClass' }],
      edge_cases: ['Config vacía', 'Parámetros inválidos', 'Uso concurrente'],
      error_handling: ['ValueError para config inválida', 'Logging de errores'],
      constraints: ['Thread-safe', 'Inmutable después de init'],
      acceptance_criteria: ['100% cobertura de tests', 'Docstrings completos', 'Type hints'],
    },
  },
];

// ─── Default gate list ──────────────────────────────────────────────────────────

function makeDefaultGates(): GateStatus[] {
  return Array.from({ length: 17 }, (_, i) => ({
    gate_number: i,
    gate_name: GATE_NAMES[i] || `Gate ${i}`,
    status: 'pending' as GateStatusValue,
    output: '',
    duration_ms: 0,
    attempts: 0,
  }));
}

// ─── API helpers ────────────────────────────────────────────────────────────────

async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`POST ${path} → ${res.status}: ${txt}`);
  }
  return res.json();
}

async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`GET ${path} → ${res.status}: ${txt}`);
  }
  return res.json();
}

// ─── Sub-components ─────────────────────────────────────────────────────────────

/** Input/Output field row for spec form */
function IOFieldRow({
  item,
  onChange,
  onRemove,
}: {
  item: { name: string; type: string };
  onChange: (field: 'name' | 'type', value: string) => void;
  onRemove: () => void;
}) {
  const inputStyle: React.CSSProperties = {
    flex: 1,
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    color: '#e5e7eb',
    padding: '6px 8px',
    fontSize: 13,
    fontFamily: 'monospace',
    outline: 'none',
  };
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
      <input
        placeholder="nombre"
        value={item.name}
        onChange={e => onChange('name', e.target.value)}
        style={inputStyle}
      />
      <input
        placeholder="tipo"
        value={item.type}
        onChange={e => onChange('type', e.target.value)}
        style={inputStyle}
      />
      <button
        onClick={onRemove}
        style={{
          background: '#7f1d1d',
          border: 'none',
          color: '#fca5a5',
          borderRadius: 4,
          padding: '4px 8px',
          cursor: 'pointer',
          fontSize: 12,
        }}
      >
        ✕
      </button>
    </div>
  );
}

// ─── Observatory Missions Bridge Section ────────────────────────────────────────

interface ObsMission {
  id: string;
  title: string;
  description: string;
  origin: string;
  created_by: string;
  finding: string;
  analysis: string;
  strategy: string;
  status: string;
  spec: Record<string, unknown>;
  created_at?: string;
}

function ObservatoryMissionsPanel({
  onLoadMission,
}: {
  onLoadMission: (m: ObsMission) => void;
}) {
  const [missions, setMissions] = useState<ObsMission[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${MISSIONS_API}?origin=observatory&limit=10`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            setMissions(data.filter((m: ObsMission) =>
              m.status === 'pending' || m.status === 'spec_review'
            ));
          }
        }
      } catch { /* ignore */ }
      setLoading(false);
    })();
  }, []);

  if (missions.length === 0 && !loading) return null;

  return (
    <div style={{
      marginBottom: 16,
      background: 'rgba(21,101,192,0.08)',
      border: '1px solid rgba(21,101,192,0.2)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
          cursor: 'pointer', userSelect: 'none',
        }}
      >
        <span>{expanded ? '▼' : '▶'}</span>
        <span style={{ fontSize: 14 }}>🔭</span>
        <span style={{ color: '#90CAF9', fontSize: 13, fontWeight: 700 }}>
          Misiones del Observatory
        </span>
        <span style={{
          background: 'rgba(21,101,192,0.3)', color: '#90CAF9',
          fontSize: 10, fontWeight: 700, padding: '1px 7px', borderRadius: 10,
          marginLeft: 4,
        }}>
          {loading ? '…' : missions.length}
        </span>
      </div>
      {expanded && (
        <div style={{ padding: '0 14px 12px' }}>
          {loading ? (
            <div style={{ color: '#666', fontSize: 12 }}>Cargando…</div>
          ) : (
            missions.map(m => (
              <div key={m.id} style={{
                marginBottom: 8, padding: '10px 12px', borderRadius: 8,
                background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{ fontSize: 12 }}>
                    {m.created_by === 'Miner' ? '⛏️' : m.created_by === 'Scientist' ? '🔬' : m.created_by === 'Guard' ? '🛡️' : m.created_by === 'Optimizer' ? '⚡' : m.created_by === 'Tester' ? '💪' : m.created_by === 'Sage' ? '🧙' : m.created_by === 'Robot' ? '🤖' : m.created_by === 'Writer' ? '✍️' : '🔭'}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#ddd', flex: 1 }}>
                    {m.title}
                  </span>
                </div>
                {m.finding && (
                  <div style={{ fontSize: 11, color: '#999', marginBottom: 6, maxHeight: 40, overflow: 'hidden' }}>
                    {m.finding.slice(0, 150)}…
                  </div>
                )}
                {m.analysis && (
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>
                    📊 {m.analysis.slice(0, 100)}…
                  </div>
                )}
                <button
                  onClick={() => onLoadMission(m)}
                  style={{
                    background: 'linear-gradient(135deg, #FF9800, #F57C00)', border: 'none',
                    color: '#fff', padding: '5px 14px', borderRadius: 6,
                    cursor: 'pointer', fontWeight: 600, fontSize: 11,
                  }}
                >🔍 Revisar y Ejecutar</button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── Mission Creation Form ──────────────────────────────────────────────────────

function MissionCreationForm({
  onCreated,
}: {
  onCreated: (mission: WorkshopMission) => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [inputs, setInputs] = useState<Array<{ name: string; type: string }>>([{ name: '', type: '' }]);
  const [outputs, setOutputs] = useState<Array<{ name: string; type: string }>>([{ name: '', type: '' }]);
  const [edgeCases, setEdgeCases] = useState('');
  const [errorHandling, setErrorHandling] = useState('');
  const [constraints, setConstraints] = useState('');
  const [acceptance, setAcceptance] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    inputs: true,
    outputs: true,
    edge_cases: false,
    error_handling: false,
    constraints: false,
    acceptance: false,
  });

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const applyTemplate = (tpl: QuickTemplate) => {
    setTitle(tpl.title);
    setDescription(tpl.description);
    setInputs(tpl.spec.inputs.length ? [...tpl.spec.inputs] : [{ name: '', type: '' }]);
    setOutputs(tpl.spec.outputs.length ? [...tpl.spec.outputs] : [{ name: '', type: '' }]);
    setEdgeCases(tpl.spec.edge_cases.join('\n'));
    setErrorHandling(tpl.spec.error_handling.join('\n'));
    setConstraints(tpl.spec.constraints.join('\n'));
    setAcceptance(tpl.spec.acceptance_criteria.join('\n'));
    setExpandedSections({ inputs: true, outputs: true, edge_cases: true, error_handling: true, constraints: true, acceptance: true });
  };

  const loadFromObservatory = (m: ObsMission) => {
    setTitle(m.title);
    setDescription(m.description || m.finding?.slice(0, 500) || '');
    if (m.spec && typeof m.spec === 'object' && Object.keys(m.spec).length > 0) {
      const s = m.spec as Record<string, unknown>;
      if (Array.isArray(s.inputs) && s.inputs.length > 0) setInputs(s.inputs as Array<{ name: string; type: string }>);
      if (Array.isArray(s.outputs) && s.outputs.length > 0) setOutputs(s.outputs as Array<{ name: string; type: string }>);
      if (Array.isArray(s.edge_cases)) setEdgeCases((s.edge_cases as string[]).join('\n'));
      if (Array.isArray(s.error_handling)) setErrorHandling((s.error_handling as string[]).join('\n'));
      if (Array.isArray(s.constraints)) setConstraints((s.constraints as string[]).join('\n'));
      if (Array.isArray(s.acceptance_criteria)) setAcceptance((s.acceptance_criteria as string[]).join('\n'));
    }
    setExpandedSections({ inputs: true, outputs: true, edge_cases: true, error_handling: true, constraints: true, acceptance: true });
  };

  const updateIO = (
    list: Array<{ name: string; type: string }>,
    setter: React.Dispatch<React.SetStateAction<Array<{ name: string; type: string }>>>,
    idx: number,
    field: 'name' | 'type',
    value: string,
  ) => {
    setter(prev => prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError('El título es requerido');
      return;
    }
    setLoading(true);
    setError('');

    const splitLines = (s: string) => s.split('\n').map(l => l.trim()).filter(Boolean);
    const spec: MissionSpec = {
      inputs: inputs.filter(i => i.name.trim()),
      outputs: outputs.filter(o => o.name.trim()),
      edge_cases: splitLines(edgeCases),
      error_handling: splitLines(errorHandling),
      constraints: splitLines(constraints),
      acceptance_criteria: splitLines(acceptance),
    };

    try {
      const mission = await apiPost<WorkshopMission>('/missions', {
        title: title.trim(),
        description: description.trim(),
        spec,
      });
      // Execute the pipeline
      await apiPost(`/missions/${mission.id}/execute`);
      onCreated(mission);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setLoading(false);
    }
  };

  const sectionHeaderStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    cursor: 'pointer',
    padding: '8px 0',
    color: '#d1d5db',
    fontSize: 13,
    fontWeight: 600,
    userSelect: 'none',
    borderBottom: '1px solid #1f2937',
  };

  const textareaStyle: React.CSSProperties = {
    width: '100%',
    minHeight: 70,
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 6,
    color: '#e5e7eb',
    padding: '8px 10px',
    fontSize: 13,
    fontFamily: 'monospace',
    resize: 'vertical',
    outline: 'none',
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 6,
    color: '#e5e7eb',
    padding: '8px 10px',
    fontSize: 14,
    outline: 'none',
  };

  const addBtnStyle: React.CSSProperties = {
    background: 'none',
    border: '1px dashed #4b5563',
    borderRadius: 4,
    color: '#9ca3af',
    padding: '4px 12px',
    cursor: 'pointer',
    fontSize: 12,
    marginTop: 4,
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      width: '100%',
      height: '100%',
      background: '#111827',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px 12px',
        borderBottom: '1px solid #1f2937',
        flexShrink: 0,
      }}>
        <h2 style={{ margin: 0, color: '#f9fafb', fontSize: 20, fontWeight: 700 }}>
          🏗️ Workshop — Nueva Misión
        </h2>
        <p style={{ margin: '6px 0 0', color: '#9ca3af', fontSize: 13 }}>
          Define la especificación y el pipeline de 17 gates generará el código.
        </p>
      </div>

      {/* Scrollable form body */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px 24px' }}>
        {/* Observatory Missions Bridge */}
        <ObservatoryMissionsPanel onLoadMission={loadFromObservatory} />

        {/* Quick Templates */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
            Plantillas rápidas
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {QUICK_TEMPLATES.map((tpl, i) => (
              <button
                key={i}
                onClick={() => applyTemplate(tpl)}
                style={{
                  background: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: 6,
                  color: '#d1d5db',
                  padding: '6px 14px',
                  cursor: 'pointer',
                  fontSize: 13,
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = '#FF9800')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#374151')}
              >
                {tpl.label}
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div style={{ marginBottom: 12 }}>
          <label style={{ color: '#9ca3af', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>TÍTULO *</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Ej: Función quicksort optimizada"
            style={inputStyle}
          />
        </div>

        {/* Description */}
        <div style={{ marginBottom: 12 }}>
          <label style={{ color: '#9ca3af', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>DESCRIPCIÓN</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Describe qué debe hacer el código..."
            style={{ ...textareaStyle, minHeight: 60 }}
          />
        </div>

        {/* Inputs Section */}
        <div style={{ marginBottom: 8 }}>
          <div onClick={() => toggleSection('inputs')} style={sectionHeaderStyle}>
            <span>{expandedSections.inputs ? '▼' : '▶'}</span>
            <span>📥 Inputs ({inputs.filter(i => i.name.trim()).length})</span>
          </div>
          {expandedSections.inputs && (
            <div style={{ padding: '8px 0 0 16px' }}>
              {inputs.map((item, idx) => (
                <IOFieldRow
                  key={idx}
                  item={item}
                  onChange={(field, value) => updateIO(inputs, setInputs, idx, field, value)}
                  onRemove={() => setInputs(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev)}
                />
              ))}
              <button onClick={() => setInputs(prev => [...prev, { name: '', type: '' }])} style={addBtnStyle}>
                + Agregar input
              </button>
            </div>
          )}
        </div>

        {/* Outputs Section */}
        <div style={{ marginBottom: 8 }}>
          <div onClick={() => toggleSection('outputs')} style={sectionHeaderStyle}>
            <span>{expandedSections.outputs ? '▼' : '▶'}</span>
            <span>📤 Outputs ({outputs.filter(o => o.name.trim()).length})</span>
          </div>
          {expandedSections.outputs && (
            <div style={{ padding: '8px 0 0 16px' }}>
              {outputs.map((item, idx) => (
                <IOFieldRow
                  key={idx}
                  item={item}
                  onChange={(field, value) => updateIO(outputs, setOutputs, idx, field, value)}
                  onRemove={() => setOutputs(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev)}
                />
              ))}
              <button onClick={() => setOutputs(prev => [...prev, { name: '', type: '' }])} style={addBtnStyle}>
                + Agregar output
              </button>
            </div>
          )}
        </div>

        {/* Edge Cases */}
        <div style={{ marginBottom: 8 }}>
          <div onClick={() => toggleSection('edge_cases')} style={sectionHeaderStyle}>
            <span>{expandedSections.edge_cases ? '▼' : '▶'}</span>
            <span>🧊 Edge Cases</span>
          </div>
          {expandedSections.edge_cases && (
            <div style={{ padding: '8px 0 0 16px' }}>
              <textarea value={edgeCases} onChange={e => setEdgeCases(e.target.value)} placeholder="Un caso por línea..." style={textareaStyle} />
            </div>
          )}
        </div>

        {/* Error Handling */}
        <div style={{ marginBottom: 8 }}>
          <div onClick={() => toggleSection('error_handling')} style={sectionHeaderStyle}>
            <span>{expandedSections.error_handling ? '▼' : '▶'}</span>
            <span>🛡️ Manejo de Errores</span>
          </div>
          {expandedSections.error_handling && (
            <div style={{ padding: '8px 0 0 16px' }}>
              <textarea value={errorHandling} onChange={e => setErrorHandling(e.target.value)} placeholder="Un manejo por línea..." style={textareaStyle} />
            </div>
          )}
        </div>

        {/* Constraints */}
        <div style={{ marginBottom: 8 }}>
          <div onClick={() => toggleSection('constraints')} style={sectionHeaderStyle}>
            <span>{expandedSections.constraints ? '▼' : '▶'}</span>
            <span>⚙️ Restricciones</span>
          </div>
          {expandedSections.constraints && (
            <div style={{ padding: '8px 0 0 16px' }}>
              <textarea value={constraints} onChange={e => setConstraints(e.target.value)} placeholder="Una restricción por línea..." style={textareaStyle} />
            </div>
          )}
        </div>

        {/* Acceptance Criteria */}
        <div style={{ marginBottom: 16 }}>
          <div onClick={() => toggleSection('acceptance')} style={sectionHeaderStyle}>
            <span>{expandedSections.acceptance ? '▼' : '▶'}</span>
            <span>✅ Criterios de Aceptación</span>
          </div>
          {expandedSections.acceptance && (
            <div style={{ padding: '8px 0 0 16px' }}>
              <textarea value={acceptance} onChange={e => setAcceptance(e.target.value)} placeholder="Un criterio por línea..." style={textareaStyle} />
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: '#7f1d1d',
            border: '1px solid #ef4444',
            borderRadius: 6,
            padding: '8px 12px',
            color: '#fca5a5',
            fontSize: 13,
            marginBottom: 12,
          }}>
            ❌ {error}
          </div>
        )}
      </div>

      {/* Footer: Submit */}
      <div style={{
        padding: '12px 24px',
        borderTop: '1px solid #1f2937',
        flexShrink: 0,
        display: 'flex',
        justifyContent: 'flex-end',
      }}>
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            background: loading ? '#4b5563' : 'linear-gradient(135deg, #FF9800, #F57C00)',
            border: 'none',
            borderRadius: 8,
            color: '#fff',
            padding: '10px 28px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 15,
            fontWeight: 700,
            letterSpacing: 0.5,
            boxShadow: loading ? 'none' : '0 0 16px rgba(255,152,0,0.3)',
          }}
        >
          {loading ? '⏳ Creando...' : '🚀 Iniciar Pipeline'}
        </button>
      </div>
    </div>
  );
}

// ─── Gates Pipeline Panel (Left) ────────────────────────────────────────────────

function GatesPipelinePanel({
  gates,
  selectedGate,
  onSelectGate,
}: {
  gates: GateStatus[];
  selectedGate: number | null;
  onSelectGate: (n: number) => void;
}) {
  const passedCount = gates.filter(g => g.status === 'passed').length;
  const progressPercent = (passedCount / gates.length) * 100;

  const currentRunning = gates.find(g => g.status === 'running');

  return (
    <div style={{
      width: 200,
      minWidth: 200,
      background: '#0d1117',
      borderRight: '1px solid #1f2937',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 10px 8px',
        borderBottom: '1px solid #1f2937',
        flexShrink: 0,
      }}>
        <div style={{ color: '#f9fafb', fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
          🚦 Gates Pipeline
        </div>
        <div style={{ color: '#9ca3af', fontSize: 11 }}>
          {passedCount}/{gates.length} completados
        </div>
      </div>

      {/* Gate list with vertical progress bar */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex' }}>
        {/* Vertical progress bar */}
        <div style={{
          width: 4,
          background: '#1f2937',
          marginLeft: 8,
          marginTop: 8,
          marginBottom: 8,
          borderRadius: 2,
          position: 'relative',
          flexShrink: 0,
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: `${progressPercent}%`,
            background: 'linear-gradient(to bottom, #22c55e, #16a34a)',
            borderRadius: 2,
            transition: 'height 0.5s ease',
          }} />
        </div>

        {/* Gate rows */}
        <div style={{ flex: 1, padding: '4px 0' }}>
          {gates.map(gate => {
            const isRunning = gate.status === 'running';
            const isSelected = selectedGate === gate.gate_number;
            const statusColor = STATUS_COLORS[gate.status];

            return (
              <div
                key={gate.gate_number}
                onClick={() => onSelectGate(gate.gate_number)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 8px',
                  cursor: 'pointer',
                  background: isSelected
                    ? 'rgba(255,152,0,0.12)'
                    : isRunning
                      ? 'rgba(245,158,11,0.08)'
                      : 'transparent',
                  borderLeft: isSelected ? '2px solid #FF9800' : '2px solid transparent',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => {
                  if (!isSelected && !isRunning) e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                }}
                onMouseLeave={e => {
                  if (!isSelected && !isRunning) e.currentTarget.style.background = 'transparent';
                }}
              >
                {/* Status icon */}
                <span style={{
                  fontSize: 12,
                  flexShrink: 0,
                  animation: isRunning ? 'workshopPulse 1.5s ease-in-out infinite' : undefined,
                }}>
                  {STATUS_ICONS[gate.status]}
                </span>

                {/* Gate info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    color: isRunning ? '#fbbf24' : isSelected ? '#FF9800' : '#d1d5db',
                    fontSize: 11,
                    fontWeight: isRunning ? 700 : 500,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {gate.gate_number}: {gate.gate_name}
                  </div>
                  {gate.status === 'passed' && gate.duration_ms > 0 && (
                    <div style={{ color: '#6b7280', fontSize: 10 }}>
                      {gate.duration_ms < 1000
                        ? `${gate.duration_ms}ms`
                        : `${(gate.duration_ms / 1000).toFixed(1)}s`}
                    </div>
                  )}
                  {gate.status === 'failed' && gate.attempts > 1 && (
                    <div style={{ color: '#ef4444', fontSize: 10 }}>
                      {gate.attempts} intentos
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Current running indicator */}
      {currentRunning && (
        <div style={{
          padding: '8px 10px',
          borderTop: '1px solid #1f2937',
          background: 'rgba(245,158,11,0.06)',
          flexShrink: 0,
        }}>
          <div style={{ color: '#fbbf24', fontSize: 11, fontWeight: 600 }}>
            ⏳ Ejecutando
          </div>
          <div style={{ color: '#d1d5db', fontSize: 11 }}>
            Gate {currentRunning.gate_number}: {currentRunning.gate_name}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Terminal Panel ─────────────────────────────────────────────────────────────

function TerminalPanel({ logs }: { logs: TerminalLogEntry[] }) {
  const termRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (termRef.current) {
      termRef.current.scrollTop = termRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div
      ref={termRef}
      style={{
        flex: 1,
        background: '#000',
        overflow: 'auto',
        padding: '8px 10px',
        fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
        fontSize: 12,
        lineHeight: 1.5,
      }}
    >
      {logs.length === 0 ? (
        <div style={{ color: '#4b5563' }}>
          Terminal — esperando ejecución...
        </div>
      ) : (
        logs.map((entry, i) => (
          <div key={i} style={{ color: entry.color, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {entry.prefix && (
              <span style={{ color: '#6b7280', marginRight: 6 }}>{entry.prefix}</span>
            )}
            {entry.text}
          </div>
        ))
      )}
    </div>
  );
}

interface TerminalLogEntry {
  text: string;
  color: string;
  prefix?: string;
}

// ─── Preview Panel ──────────────────────────────────────────────────────────────

function PreviewPanel({
  codeFiles,
  onRerun,
}: {
  codeFiles: Array<{ name: string; content: string }>;
  onRerun?: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const htmlFile = codeFiles.find(f => f.name.endsWith('.html'));
  const mainCode = codeFiles.find(f => f.name.endsWith('.py')) || codeFiles[0];

  const handleCopy = () => {
    if (mainCode?.content) {
      navigator.clipboard.writeText(mainCode.content).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  return (
    <div style={{
      flex: 1,
      background: '#0d1117',
      borderTop: '1px solid #1f2937',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Preview header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 10px',
        borderBottom: '1px solid #1f2937',
        flexShrink: 0,
      }}>
        <span style={{ color: '#9ca3af', fontSize: 11, fontWeight: 600 }}>PREVIEW</span>
        <div style={{ display: 'flex', gap: 6 }}>
          {onRerun && (
            <button
              onClick={onRerun}
              style={{
                background: '#1f2937',
                border: '1px solid #374151',
                borderRadius: 4,
                color: '#d1d5db',
                padding: '2px 8px',
                cursor: 'pointer',
                fontSize: 11,
              }}
            >
              🔄 Re-run
            </button>
          )}
          <button
            onClick={handleCopy}
            style={{
              background: '#1f2937',
              border: '1px solid #374151',
              borderRadius: 4,
              color: copied ? '#22c55e' : '#d1d5db',
              padding: '2px 8px',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            {copied ? '✅ Copiado' : '📋 Copiar código'}
          </button>
        </div>
      </div>

      {/* Preview content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
        {htmlFile ? (
          <iframe
            srcDoc={htmlFile.content}
            style={{
              width: '100%',
              height: '100%',
              border: '1px solid #374151',
              borderRadius: 4,
              background: '#fff',
            }}
            sandbox="allow-scripts"
            title="preview"
          />
        ) : mainCode ? (
          <div style={{ color: '#9ca3af', fontSize: 12, fontFamily: 'monospace' }}>
            <div style={{ marginBottom: 8, color: '#6b7280' }}>
              📄 {mainCode.name} — {mainCode.content.split('\n').length} líneas
            </div>
            <div style={{
              background: '#000',
              borderRadius: 4,
              padding: '8px 10px',
              color: '#4ade80',
              fontSize: 11,
              whiteSpace: 'pre-wrap',
              maxHeight: 150,
              overflow: 'auto',
            }}>
              {`$ python ${mainCode.name}\n# Ejecutar para ver resultado`}
            </div>
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#4b5563',
            fontSize: 13,
          }}>
            Sin preview disponible
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Bottom Bar ─────────────────────────────────────────────────────────────────

function BottomBar({
  gates,
  missionStatus,
  onPause,
  onResume,
  onCancel,
  onApprove,
}: {
  gates: GateStatus[];
  missionStatus: string;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onApprove: () => void;
}) {
  const runningGate = gates.find(g => g.status === 'running');
  const waitingApproval = gates.find(g => g.status === 'waiting_approval');
  const passedCount = gates.filter(g => g.status === 'passed').length;
  const totalGates = gates.length;
  const progressPercent = Math.round((passedCount / totalGates) * 100);

  const currentGate = runningGate || waitingApproval || gates.find(g => g.status !== 'passed' && g.status !== 'skipped');
  const isPaused = missionStatus === 'paused';
  const isRunning = missionStatus === 'running' || missionStatus === 'executing';
  const isCompleted = missionStatus === 'completed' || missionStatus === 'done';
  const isFailed = missionStatus === 'failed';

  const barWidth = `${progressPercent}%`;
  const filledBlocks = Math.round(progressPercent / 5);
  const emptyBlocks = 20 - filledBlocks;
  const progressBar = '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);

  const btnStyle = (active: boolean, color: string): React.CSSProperties => ({
    background: active ? color : '#1f2937',
    border: `1px solid ${active ? color : '#374151'}`,
    borderRadius: 6,
    color: active ? '#fff' : '#6b7280',
    padding: '6px 14px',
    cursor: active ? 'pointer' : 'not-allowed',
    fontSize: 12,
    fontWeight: 600,
    opacity: active ? 1 : 0.5,
    transition: 'all 0.15s',
  });

  return (
    <div style={{
      background: '#0d1117',
      borderTop: '1px solid #1f2937',
      padding: '10px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      flexShrink: 0,
    }}>
      {/* Progress section */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Progress bar background */}
        <div style={{
          height: 6,
          background: '#1f2937',
          borderRadius: 3,
          overflow: 'hidden',
          marginBottom: 4,
        }}>
          <div style={{
            height: '100%',
            width: barWidth,
            background: isCompleted
              ? 'linear-gradient(90deg, #22c55e, #16a34a)'
              : isFailed
                ? 'linear-gradient(90deg, #ef4444, #dc2626)'
                : 'linear-gradient(90deg, #FF9800, #F57C00)',
            borderRadius: 3,
            transition: 'width 0.5s ease',
          }} />
        </div>
        {/* Progress text */}
        <div style={{
          color: '#d1d5db',
          fontSize: 12,
          fontFamily: 'monospace',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {currentGate
            ? `Gate ${currentGate.gate_number}/${totalGates - 1}: ${currentGate.gate_name} — ${progressPercent}% ${progressBar}`
            : isCompleted
              ? `✅ Completado — ${progressPercent}% ${progressBar}`
              : isFailed
                ? `❌ Fallido — ${progressPercent}% ${progressBar}`
                : `${progressPercent}% ${progressBar}`
          }
        </div>
      </div>

      {/* Control buttons */}
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          onClick={onPause}
          disabled={!isRunning}
          style={btnStyle(isRunning, '#f59e0b')}
          title="Pausar pipeline"
        >
          ⏸ Pausar
        </button>
        <button
          onClick={onCancel}
          disabled={!isRunning && !isPaused}
          style={btnStyle(isRunning || isPaused, '#ef4444')}
          title="Cancelar pipeline"
        >
          ⏹ Cancelar
        </button>
        <button
          onClick={onResume}
          disabled={!isPaused}
          style={btnStyle(isPaused, '#22c55e')}
          title="Continuar pipeline"
        >
          ▶ Continuar
        </button>
        <button
          onClick={onApprove}
          disabled={!waitingApproval}
          style={btnStyle(!!waitingApproval, '#8b5cf6')}
          title="Aprobar gate humano"
        >
          👤 Aprobar
        </button>
      </div>
    </div>
  );
}

// ─── CSS keyframes (injected once) ──────────────────────────────────────────────

function useInjectStyles() {
  useEffect(() => {
    const id = 'workshop-keyframes';
    if (document.getElementById(id)) return;
    const style = document.createElement('style');
    style.id = id;
    style.textContent = `
      @keyframes workshopPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }
    `;
    document.head.appendChild(style);
    return () => {
      const el = document.getElementById(id);
      if (el) el.remove();
    };
  }, []);
}

// ─── Code Editor Panel ──────────────────────────────────────────────────────────

function CodeEditorPanel({
  codeFiles,
  selectedGate,
  gates,
}: {
  codeFiles: Array<{ name: string; content: string }>;
  selectedGate: number | null;
  gates: GateStatus[];
}) {
  const [activeFileIdx, setActiveFileIdx] = useState(0);

  // Show gate output if a non-code gate is selected
  const gateOutput = useMemo(() => {
    if (selectedGate === null) return null;
    const gate = gates.find(g => g.gate_number === selectedGate);
    if (!gate || !gate.output) return null;
    // Gates that show their output in the editor rather than code
    const outputGates = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
    if (outputGates.includes(selectedGate) && gate.status !== 'pending') {
      return { gate, content: gate.output };
    }
    return null;
  }, [selectedGate, gates]);

  const displayContent = useMemo(() => {
    if (gateOutput) {
      return {
        filename: `Gate ${gateOutput.gate.gate_number}: ${gateOutput.gate.gate_name}`,
        content: gateOutput.content,
        language: 'plaintext',
      };
    }
    if (codeFiles.length === 0) {
      return {
        filename: 'sin archivos',
        content: '# Esperando generación de código...\n# El código aparecerá aquí cuando el pipeline avance.',
        language: 'python',
      };
    }
    const file = codeFiles[Math.min(activeFileIdx, codeFiles.length - 1)];
    const ext = file.name.split('.').pop() || '';
    const langMap: Record<string, string> = {
      py: 'python',
      js: 'javascript',
      ts: 'typescript',
      json: 'json',
      html: 'html',
      css: 'css',
      md: 'markdown',
      yaml: 'yaml',
      yml: 'yaml',
      toml: 'toml',
      txt: 'plaintext',
    };
    return {
      filename: file.name,
      content: file.content,
      language: langMap[ext] || 'python',
    };
  }, [gateOutput, codeFiles, activeFileIdx]);

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: '#1e1e1e',
      overflow: 'hidden',
    }}>
      {/* File tabs */}
      <div style={{
        display: 'flex',
        background: '#0d1117',
        borderBottom: '1px solid #1f2937',
        overflowX: 'auto',
        flexShrink: 0,
      }}>
        {codeFiles.length > 0 ? (
          codeFiles.map((file, idx) => (
            <button
              key={idx}
              onClick={() => setActiveFileIdx(idx)}
              style={{
                background: (activeFileIdx === idx && !gateOutput) ? '#1e1e1e' : 'transparent',
                border: 'none',
                borderBottom: (activeFileIdx === idx && !gateOutput) ? '2px solid #FF9800' : '2px solid transparent',
                color: (activeFileIdx === idx && !gateOutput) ? '#e5e7eb' : '#6b7280',
                padding: '8px 14px',
                cursor: 'pointer',
                fontSize: 12,
                fontFamily: 'monospace',
                whiteSpace: 'nowrap',
              }}
            >
              {file.name}
            </button>
          ))
        ) : (
          <div style={{ padding: '8px 14px', color: '#4b5563', fontSize: 12, fontFamily: 'monospace' }}>
            Sin archivos
          </div>
        )}
        {gateOutput && (
          <div style={{
            padding: '8px 14px',
            color: '#FF9800',
            fontSize: 12,
            fontFamily: 'monospace',
            borderBottom: '2px solid #FF9800',
            background: '#1e1e1e',
            marginLeft: 'auto',
          }}>
            📋 {displayContent.filename}
          </div>
        )}
      </div>

      {/* Editor */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <MonacoEditor
          height="100%"
          language={displayContent.language}
          theme="vs-dark"
          value={displayContent.content}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            padding: { top: 8 },
            renderLineHighlight: 'gutter',
            smoothScrolling: true,
            cursorBlinking: 'smooth',
          }}
        />
      </div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────────

function WorkshopNodeLayout({ missionId: propMissionId }: WorkshopNodeLayoutProps) {
  useInjectStyles();

  // Mission state
  const [mission, setMission] = useState<WorkshopMission | null>(null);
  const [gates, setGates] = useState<GateStatus[]>(makeDefaultGates());
  const [codeFiles, setCodeFiles] = useState<Array<{ name: string; content: string }>>([]);
  const [missionStatus, setMissionStatus] = useState('idle');
  const [selectedGate, setSelectedGate] = useState<number | null>(null);
  const [terminalLogs, setTerminalLogs] = useState<TerminalLogEntry[]>([]);
  const [showCreationForm, setShowCreationForm] = useState(!propMissionId);
  const [loadError, setLoadError] = useState('');

  // Previous gates ref for diffing log updates
  const prevGatesRef = useRef<GateStatus[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ─── Load mission if propMissionId given ────────────────────────────────────
  useEffect(() => {
    if (propMissionId) {
      fetchMission(propMissionId);
    }
  }, [propMissionId]);

  // ─── Fetch mission data ─────────────────────────────────────────────────────
  const fetchMission = useCallback(async (id: string) => {
    try {
      const data = await apiGet<WorkshopMission>(`/missions/${id}`);
      setMission(data);
      setMissionStatus(data.status || 'idle');

      if (data.gates && data.gates.length > 0) {
        setGates(data.gates);
        updateTerminalFromGates(data.gates);
      }
      if (data.code_files && data.code_files.length > 0) {
        setCodeFiles(data.code_files);
      }
      setLoadError('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setLoadError(msg);
    }
  }, []);

  // ─── Terminal log builder ───────────────────────────────────────────────────
  const updateTerminalFromGates = useCallback((newGates: GateStatus[]) => {
    const prevGates = prevGatesRef.current;
    const newLogs: TerminalLogEntry[] = [];

    for (const gate of newGates) {
      const prev = prevGates.find(g => g.gate_number === gate.gate_number);
      const prevStatus = prev?.status || 'pending';

      if (prevStatus !== gate.status) {
        switch (gate.status) {
          case 'running':
            newLogs.push({
              text: `▶ Gate ${gate.gate_number}: ${gate.gate_name} — ejecutando...`,
              color: '#fbbf24',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            });
            break;
          case 'passed':
            newLogs.push({
              text: `✅ Gate ${gate.gate_number}: ${gate.gate_name} — PASÓ ${gate.duration_ms > 0 ? `(${gate.duration_ms}ms)` : ''}`,
              color: '#4ade80',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            });
            break;
          case 'failed':
            newLogs.push({
              text: `❌ Gate ${gate.gate_number}: ${gate.gate_name} — FALLÓ`,
              color: '#ef4444',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            });
            if (gate.output) {
              newLogs.push({
                text: gate.output,
                color: '#f87171',
              });
            }
            break;
          case 'waiting_approval':
            newLogs.push({
              text: `⏸ Gate ${gate.gate_number}: ${gate.gate_name} — esperando aprobación humana`,
              color: '#eab308',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            });
            break;
          case 'skipped':
            newLogs.push({
              text: `⏭ Gate ${gate.gate_number}: ${gate.gate_name} — omitido`,
              color: '#6b7280',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            });
            break;
        }
      }

      // Append new output if gate has output and it changed
      if (gate.output && gate.output !== prev?.output && gate.status === 'running') {
        const newOutput = prev?.output ? gate.output.slice(prev.output.length) : gate.output;
        if (newOutput.trim()) {
          newLogs.push({
            text: newOutput,
            color: '#9ca3af',
          });
        }
      }
    }

    if (newLogs.length > 0) {
      setTerminalLogs(prev => [...prev, ...newLogs]);
    }
    prevGatesRef.current = newGates;
  }, []);

  // ─── Polling ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mission?.id) return;
    const isActive = ['running', 'executing', 'paused'].includes(missionStatus);
    if (!isActive) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }

    pollingRef.current = setInterval(async () => {
      try {
        const data = await apiGet<WorkshopMission>(`/missions/${mission.id}`);
        setMission(data);
        setMissionStatus(data.status || 'idle');

        if (data.gates && data.gates.length > 0) {
          setGates(data.gates);
          updateTerminalFromGates(data.gates);
        }
        if (data.code_files && data.code_files.length > 0) {
          setCodeFiles(data.code_files);
        }

        // Stop polling if done
        if (['completed', 'done', 'failed', 'cancelled'].includes(data.status)) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
          // Final terminal message
          if (data.status === 'completed' || data.status === 'done') {
            setTerminalLogs(prev => [...prev, {
              text: '🎉 Pipeline completado exitosamente!',
              color: '#22c55e',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            }]);
          } else if (data.status === 'failed') {
            setTerminalLogs(prev => [...prev, {
              text: '💥 Pipeline falló.',
              color: '#ef4444',
              prefix: `[${new Date().toLocaleTimeString('es')}]`,
            }]);
          }
        }
      } catch {
        // Silently ignore poll errors
      }
    }, 2000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [mission?.id, missionStatus, updateTerminalFromGates]);

  // ─── Actions ────────────────────────────────────────────────────────────────
  const handlePause = useCallback(async () => {
    if (!mission?.id) return;
    try {
      await apiPost(`/missions/${mission.id}/pause`);
      setMissionStatus('paused');
      setTerminalLogs(prev => [...prev, {
        text: '⏸ Pipeline pausado por el usuario',
        color: '#eab308',
        prefix: `[${new Date().toLocaleTimeString('es')}]`,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalLogs(prev => [...prev, { text: `Error al pausar: ${msg}`, color: '#ef4444' }]);
    }
  }, [mission?.id]);

  const handleResume = useCallback(async () => {
    if (!mission?.id) return;
    try {
      await apiPost(`/missions/${mission.id}/resume`);
      setMissionStatus('running');
      setTerminalLogs(prev => [...prev, {
        text: '▶ Pipeline reanudado',
        color: '#22c55e',
        prefix: `[${new Date().toLocaleTimeString('es')}]`,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalLogs(prev => [...prev, { text: `Error al reanudar: ${msg}`, color: '#ef4444' }]);
    }
  }, [mission?.id]);

  const handleCancel = useCallback(async () => {
    if (!mission?.id) return;
    try {
      await apiPost(`/missions/${mission.id}/cancel`);
      setMissionStatus('cancelled');
      setTerminalLogs(prev => [...prev, {
        text: '⏹ Pipeline cancelado por el usuario',
        color: '#ef4444',
        prefix: `[${new Date().toLocaleTimeString('es')}]`,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalLogs(prev => [...prev, { text: `Error al cancelar: ${msg}`, color: '#ef4444' }]);
    }
  }, [mission?.id]);

  const handleApprove = useCallback(async () => {
    if (!mission?.id) return;
    const waitingGate = gates.find(g => g.status === 'waiting_approval');
    if (!waitingGate) return;
    try {
      await apiPost(`/missions/${mission.id}/gates/${waitingGate.gate_number}/approve`);
      setTerminalLogs(prev => [...prev, {
        text: `👤 Gate ${waitingGate.gate_number} aprobado manualmente`,
        color: '#a78bfa',
        prefix: `[${new Date().toLocaleTimeString('es')}]`,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalLogs(prev => [...prev, { text: `Error al aprobar: ${msg}`, color: '#ef4444' }]);
    }
  }, [mission?.id, gates]);

  const handleRerun = useCallback(async () => {
    if (!mission?.id) return;
    try {
      await apiPost(`/missions/${mission.id}/execute`);
      setMissionStatus('running');
      setGates(makeDefaultGates());
      prevGatesRef.current = [];
      setTerminalLogs(prev => [...prev, {
        text: '🔄 Re-ejecutando pipeline...',
        color: '#FF9800',
        prefix: `[${new Date().toLocaleTimeString('es')}]`,
      }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setTerminalLogs(prev => [...prev, { text: `Error al re-ejecutar: ${msg}`, color: '#ef4444' }]);
    }
  }, [mission?.id]);

  const handleMissionCreated = useCallback((newMission: WorkshopMission) => {
    setMission(newMission);
    setMissionStatus('running');
    setShowCreationForm(false);
    setGates(newMission.gates?.length ? newMission.gates : makeDefaultGates());
    setCodeFiles(newMission.code_files || []);
    prevGatesRef.current = [];
    setTerminalLogs([{
      text: `🚀 Misión "${newMission.title}" creada — iniciando pipeline...`,
      color: '#FF9800',
      prefix: `[${new Date().toLocaleTimeString('es')}]`,
    }]);
  }, []);

  // ─── Creation form view ─────────────────────────────────────────────────────
  if (showCreationForm) {
    return <MissionCreationForm onCreated={handleMissionCreated} />;
  }

  // ─── Loading error ──────────────────────────────────────────────────────────
  if (loadError && !mission) {
    return (
      <div style={{
        width: '100%',
        height: '100%',
        background: '#111827',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        color: '#ef4444',
        fontFamily: 'monospace',
      }}>
        <span style={{ fontSize: 32 }}>❌</span>
        <span style={{ fontSize: 14 }}>Error cargando misión</span>
        <span style={{ fontSize: 12, color: '#9ca3af', maxWidth: 400, textAlign: 'center' }}>{loadError}</span>
        <button
          onClick={() => { setLoadError(''); setShowCreationForm(true); }}
          style={{
            marginTop: 8,
            background: '#FF9800',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            padding: '8px 20px',
            cursor: 'pointer',
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          Crear nueva misión
        </button>
      </div>
    );
  }

  // ─── Main layout ────────────────────────────────────────────────────────────
  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#111827',
      overflow: 'hidden',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
    }}>
      {/* Title bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 12px',
        background: '#0d1117',
        borderBottom: '1px solid #1f2937',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>🏗️</span>
          <span style={{ color: '#f9fafb', fontSize: 13, fontWeight: 700 }}>Workshop</span>
          {mission && (
            <span style={{ color: '#9ca3af', fontSize: 12 }}>
              — {mission.title}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Status badge */}
          <span style={{
            padding: '2px 8px',
            borderRadius: 10,
            fontSize: 11,
            fontWeight: 600,
            background: missionStatus === 'running' || missionStatus === 'executing'
              ? 'rgba(245,158,11,0.15)'
              : missionStatus === 'completed' || missionStatus === 'done'
                ? 'rgba(34,197,94,0.15)'
                : missionStatus === 'failed'
                  ? 'rgba(239,68,68,0.15)'
                  : missionStatus === 'paused'
                    ? 'rgba(234,179,8,0.15)'
                    : 'rgba(107,114,128,0.15)',
            color: missionStatus === 'running' || missionStatus === 'executing'
              ? '#f59e0b'
              : missionStatus === 'completed' || missionStatus === 'done'
                ? '#22c55e'
                : missionStatus === 'failed'
                  ? '#ef4444'
                  : missionStatus === 'paused'
                    ? '#eab308'
                    : '#6b7280',
          }}>
            {missionStatus === 'running' || missionStatus === 'executing' ? '⏳ Ejecutando'
              : missionStatus === 'completed' || missionStatus === 'done' ? '✅ Completado'
              : missionStatus === 'failed' ? '❌ Fallido'
              : missionStatus === 'paused' ? '⏸ Pausado'
              : missionStatus === 'cancelled' ? '⏹ Cancelado'
              : '💤 Idle'}
          </span>
          {/* New mission button */}
          <button
            onClick={() => {
              setShowCreationForm(true);
              setMission(null);
              setGates(makeDefaultGates());
              setCodeFiles([]);
              setTerminalLogs([]);
              setSelectedGate(null);
              setMissionStatus('idle');
              prevGatesRef.current = [];
            }}
            style={{
              background: '#1f2937',
              border: '1px solid #374151',
              borderRadius: 4,
              color: '#d1d5db',
              padding: '3px 10px',
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            + Nueva Misión
          </button>
        </div>
      </div>

      {/* 3-panel layout */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left — Gates Pipeline */}
        <GatesPipelinePanel
          gates={gates}
          selectedGate={selectedGate}
          onSelectGate={setSelectedGate}
        />

        {/* Center — Code Editor */}
        <CodeEditorPanel
          codeFiles={codeFiles}
          selectedGate={selectedGate}
          gates={gates}
        />

        {/* Right — Terminal + Preview (split vertical) */}
        <div style={{
          width: 320,
          minWidth: 280,
          display: 'flex',
          flexDirection: 'column',
          borderLeft: '1px solid #1f2937',
          overflow: 'hidden',
        }}>
          {/* Terminal header */}
          <div style={{
            padding: '6px 10px',
            background: '#0d1117',
            borderBottom: '1px solid #1f2937',
            flexShrink: 0,
          }}>
            <span style={{ color: '#9ca3af', fontSize: 11, fontWeight: 600 }}>TERMINAL</span>
          </div>
          {/* Terminal */}
          <TerminalPanel logs={terminalLogs} />
          {/* Preview */}
          <PreviewPanel
            codeFiles={codeFiles}
            onRerun={mission?.id ? handleRerun : undefined}
          />
        </div>
      </div>

      {/* Bottom Bar */}
      <BottomBar
        gates={gates}
        missionStatus={missionStatus}
        onPause={handlePause}
        onResume={handleResume}
        onCancel={handleCancel}
        onApprove={handleApprove}
      />
    </div>
  );
}

// ─── Exports ────────────────────────────────────────────────────────────────────

export { WorkshopNodeLayout };
export default WorkshopNodeLayout;
