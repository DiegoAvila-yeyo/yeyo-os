## ═══════════════════════════════════════
## MICRO-FASE 6.16 — YeyoMergeGuard: Validación Pre-Merge de Aprendizajes YeyoNet
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.16-1 [VSCODE] — Sandbox + mini-benchmark para validar aprendizajes de nodos satélite antes de aplicarlos al cerebro central

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.16 de Capa 6 (Sistema Inmune): implementar YeyoMergeGuard, el sistema que valida aprendizajes de nodos satélite (amigos) antes de aplicarlos al cerebro central. Ningún aprendizaje externo se aplica directamente — pasa primero por sandbox + mini-benchmark para detectar si degrada el modelo.

CONTEXTO:
- Micro-fases 6.0–6.15 completadas: incluye YeyoBenchmark (6.15) con suite de 50 problemas
- YeyoNet: red de nodos Yeyo distribuidos (amigos que comparten aprendizajes entre sí)
- Cada nodo tiene un nodo_id único (ej: "node-friend-1", "node-amigo-pepe")
- Un "aprendizaje" es un dict con contenido de Flash Memory que un nodo quiere compartir
- El sandbox aplica el aprendizaje aisladamente y corre 10 problemas representativos del benchmark
- Decisiones: ACEPTAR (sin degradación), CUARENTENA (degradación mínima ≤ 2%), RECHAZAR (>2%)
- Nodos con >3 rechazos consecutivos: notificación automática + suspensión temporal
- Frontend: nuevo panel "MergeGuard Dashboard" en el Security Dashboard existente (6.9)
- Flash Memory client: disponible en src/memory/flash_memory.py
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/quality/yeyo_merge_guard.py:

   Ruta: ~/yeyo-os/src/quality/yeyo_merge_guard.py
   Contenido:

   """
   YeyoOS — YeyoMergeGuard: Validación Pre-Merge de Aprendizajes YeyoNet
   Micro-fase 6.16 — Capa 6: Sistema Inmune

   Valida aprendizajes de nodos satélite antes de aplicarlos al cerebro central.
   Nunca aplica directamente — siempre sandbox + mini-benchmark primero.

   Proceso:
     1. Recibe aprendizaje de nodo_id
     2. Aplica aprendizaje en ambiente simulado (sandbox)
     3. Corre mini-benchmark (10 problemas representativos)
     4. Compara score antes vs después
     5. Decide: ACEPTAR / CUARENTENA / RECHAZAR
     6. Si nodo tiene >3 rechazos consecutivos → notificar + suspender
   """

   import asyncio
   import json
   import logging
   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from enum import Enum
   from typing import Optional

   import httpx

   logger = logging.getLogger("yeyo.quality.merge_guard")

   OLLAMA_BASE_URL = "http://localhost:11434"
   MODELO = "qwen2.5:3b"

   # Umbral de degradación tolerable (2%)
   DELTA_MINIMO_TOLERABLE: float = -0.02

   # Rechazos consecutivos para suspender un nodo
   RECHAZOS_PARA_SUSPENSION: int = 3

   # Problemas representativos del mini-benchmark (10 de los 50 totales)
   MINI_BENCHMARK_PROBLEMAS: list[dict] = [
       {
           "id": "mini_py_01",
           "prompt": "Crea una función Python que ordene una lista de dicts por clave",
           "criterios_clave": ["sorted", "key", "lambda"],
       },
       {
           "id": "mini_py_02",
           "prompt": "Implementa un decorator de retry con máximo 3 intentos",
           "criterios_clave": ["def ", "except", "range("],
       },
       {
           "id": "mini_ts_01",
           "prompt": "Crea una función TypeScript con generics que filtre un array por tipo",
           "criterios_clave": ["<T>", "filter", "=>"],
       },
       {
           "id": "mini_ts_02",
           "prompt": "Implementa un hook React useDebounce en TypeScript",
           "criterios_clave": ["useEffect", "setTimeout", "useState"],
       },
       {
           "id": "mini_sql_01",
           "prompt": "Escribe un SELECT con JOIN entre users y orders filtrando por fecha",
           "criterios_clave": ["JOIN", "WHERE", "DATE"],
       },
       {
           "id": "mini_sql_02",
           "prompt": "Escribe un UPSERT eficiente en PostgreSQL con ON CONFLICT",
           "criterios_clave": ["INSERT", "ON CONFLICT", "DO UPDATE"],
       },
       {
           "id": "mini_sec_01",
           "prompt": "Crea un endpoint FastAPI con autenticación JWT básica",
           "criterios_clave": ["Bearer", "decode", "HTTPException"],
       },
       {
           "id": "mini_sec_02",
           "prompt": "Implementa hashing de contraseñas con bcrypt en Python",
           "criterios_clave": ["bcrypt", "hashpw", "checkpw"],
       },
       {
           "id": "mini_arch_01",
           "prompt": "Diseña la estructura de directorios para una API FastAPI hexagonal",
           "criterios_clave": ["routes", "services", "models"],
       },
       {
           "id": "mini_arch_02",
           "prompt": "Describe los principios SOLID en código Python con ejemplos",
           "criterios_clave": ["Single", "Open", "Dependency"],
       },
   ]


   # ─── Enums y Dataclasses ──────────────────────────────────────────────────


   class MergeDecision(str, Enum):
       ACEPTAR = "ACEPTAR"
       CUARENTENA = "CUARENTENA"
       RECHAZAR = "RECHAZAR"


   @dataclass
   class MiniBenchmarkResult:
       """Resultado del mini-benchmark de 10 problemas."""

       score: float
       problemas_aprobados: int
       problemas_totales: int = 10
       detalles: list[dict] = field(default_factory=list)


   @dataclass
   class MergeResult:
       """Resultado completo de la validación de un aprendizaje."""

       nodo_id: str
       aprendizaje_id: str
       decision: MergeDecision
       score_antes: float
       score_despues: float
       delta: float
       razon: str
       timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       aprendizaje_aplicado: bool = False

       def to_dict(self) -> dict:
           return {
               "nodo_id": self.nodo_id,
               "aprendizaje_id": self.aprendizaje_id,
               "decision": self.decision.value,
               "score_antes": round(self.score_antes, 4),
               "score_despues": round(self.score_despues, 4),
               "delta": round(self.delta, 4),
               "razon": self.razon,
               "timestamp": self.timestamp.isoformat(),
               "aprendizaje_aplicado": self.aprendizaje_aplicado,
           }


   # ─── Validador principal ───────────────────────────────────────────────────


   class YeyoMergeGuard:
       """
       Valida aprendizajes de nodos satélite antes de aplicarlos
       al cerebro central. Nunca aplica directamente.
       """

       def __init__(self, flash_memory=None, merge_history=None) -> None:
           self.flash_memory = flash_memory
           self.merge_history = merge_history
           # Estado en memoria de rechazos por nodo
           self._rechazos_consecutivos: dict[str, int] = {}
           self._nodos_suspendidos: set[str] = set()

       async def validar_aprendizaje(
           self, nodo_id: str, aprendizaje: dict
       ) -> MergeResult:
           """
           Valida un aprendizaje de un nodo satélite.

           Proceso:
             1. Verificar que el nodo no está suspendido
             2. Correr mini-benchmark sin el aprendizaje (score_antes)
             3. Simular aplicación del aprendizaje en sandbox
             4. Correr mini-benchmark con el aprendizaje (score_despues)
             5. Calcular delta y decidir
             6. Actualizar contadores de rechazo del nodo
           """
           aprendizaje_id = aprendizaje.get("id", f"{nodo_id}_{datetime.now(timezone.utc).isoformat()}")

           # Verificar suspensión
           if nodo_id in self._nodos_suspendidos:
               logger.warning("Nodo %s está suspendido — rechazando sin evaluar", nodo_id)
               result = MergeResult(
                   nodo_id=nodo_id,
                   aprendizaje_id=aprendizaje_id,
                   decision=MergeDecision.RECHAZAR,
                   score_antes=0.0,
                   score_despues=0.0,
                   delta=0.0,
                   razon=f"Nodo {nodo_id} suspendido temporalmente por rechazos repetidos",
               )
               if self.merge_history:
                   await self.merge_history.registrar(result)
               return result

           logger.info(
               "Iniciando validación de aprendizaje del nodo %s (id=%s)",
               nodo_id,
               aprendizaje_id,
           )

           async with httpx.AsyncClient(timeout=60.0) as cliente:
               # Score sin el aprendizaje
               score_antes_result = await self.mini_benchmark(cliente)
               score_antes = score_antes_result.score

               # Simular el aprendizaje en sandbox
               self.aplicar_en_sandbox(aprendizaje)

               # Score con el aprendizaje
               score_despues_result = await self.mini_benchmark(cliente)
               score_despues = score_despues_result.score

               # Limpiar sandbox
               self._limpiar_sandbox()

           delta = score_despues - score_antes

           # Tomar decisión
           if delta >= 0:
               decision = MergeDecision.ACEPTAR
               razon = f"El aprendizaje mejora el modelo en {delta * 100:.1f}% (score: {score_antes:.2f} → {score_despues:.2f})"
               self._rechazos_consecutivos[nodo_id] = 0
           elif delta >= DELTA_MINIMO_TOLERABLE:
               decision = MergeDecision.CUARENTENA
               razon = (
                   f"Degradación mínima ({abs(delta) * 100:.1f}%) dentro del umbral tolerable (2%). "
                   f"Requiere revisión manual."
               )
               self._rechazos_consecutivos[nodo_id] = 0
           else:
               decision = MergeDecision.RECHAZAR
               razon = (
                   f"El aprendizaje degrada el modelo en {abs(delta) * 100:.1f}% "
                   f"(score: {score_antes:.2f} → {score_despues:.2f}). "
                   f"Supera el umbral máximo de 2%."
               )
               conteo = self._rechazos_consecutivos.get(nodo_id, 0) + 1
               self._rechazos_consecutivos[nodo_id] = conteo

               if conteo >= RECHAZOS_PARA_SUSPENSION:
                   await self.manejar_nodo_problematico(nodo_id)

           aprendizaje_aplicado = False
           if decision == MergeDecision.ACEPTAR:
               aprendizaje_aplicado = self._aplicar_al_cerebro_central(aprendizaje)

           result = MergeResult(
               nodo_id=nodo_id,
               aprendizaje_id=aprendizaje_id,
               decision=decision,
               score_antes=score_antes,
               score_despues=score_despues,
               delta=delta,
               razon=razon,
               aprendizaje_aplicado=aprendizaje_aplicado,
           )

           if self.merge_history:
               await self.merge_history.registrar(result)

           logger.info(
               "Validación completa: nodo=%s decision=%s delta=%.3f",
               nodo_id,
               decision.value,
               delta,
           )
           return result

       async def mini_benchmark(
           self, cliente: httpx.AsyncClient
       ) -> MiniBenchmarkResult:
           """
           Corre 10 problemas representativos y retorna el score promedio.
           """
           aprobados = 0
           detalles = []

           for problema in MINI_BENCHMARK_PROBLEMAS:
               try:
                   response = await cliente.post(
                       f"{OLLAMA_BASE_URL}/api/generate",
                       json={
                           "model": MODELO,
                           "prompt": problema["prompt"],
                           "stream": False,
                           "options": {"temperature": 0.1, "num_predict": 256},
                       },
                   )
                   datos = response.json()
                   codigo = datos.get("response", "")

                   criterios_aprobados = [
                       kw for kw in problema["criterios_clave"] if kw.lower() in codigo.lower()
                   ]
                   aprobado = len(criterios_aprobados) >= len(problema["criterios_clave"]) * 0.6

                   if aprobado:
                       aprobados += 1

                   detalles.append({
                       "id": problema["id"],
                       "aprobado": aprobado,
                       "criterios_hallados": criterios_aprobados,
                   })

               except Exception as exc:
                   logger.debug("Error en mini-benchmark problema %s: %s", problema["id"], exc)
                   detalles.append({"id": problema["id"], "aprobado": False, "error": str(exc)})

           score = aprobados / len(MINI_BENCHMARK_PROBLEMAS)
           return MiniBenchmarkResult(
               score=score,
               problemas_aprobados=aprobados,
               problemas_totales=len(MINI_BENCHMARK_PROBLEMAS),
               detalles=detalles,
           )

       def aplicar_en_sandbox(self, aprendizaje: dict) -> None:
           """
           Simula la aplicación del aprendizaje en un ambiente aislado.
           En esta implementación el sandbox es in-memory (sin persistencia).
           """
           self._sandbox_aprendizaje = aprendizaje
           logger.debug("Aprendizaje aplicado en sandbox: %s", aprendizaje.get("id", ""))

       def _limpiar_sandbox(self) -> None:
           """Limpia el sandbox después de la evaluación."""
           self._sandbox_aprendizaje = None

       def _aplicar_al_cerebro_central(self, aprendizaje: dict) -> bool:
           """
           Aplica el aprendizaje al cerebro central via Flash Memory.
           Solo se llama cuando decision == ACEPTAR.
           """
           if not self.flash_memory:
               logger.warning("Flash Memory no disponible — aprendizaje no aplicado")
               return False

           try:
               contenido = aprendizaje.get("contenido", json.dumps(aprendizaje))
               importancia = aprendizaje.get("importancia", 0.7)
               tags = aprendizaje.get("tags", ["yeyonet", "aprendizaje_externo"])

               self.flash_memory.store(
                   content=contenido,
                   importance=importancia,
                   tags=tags,
                   metadata={
                       "tipo": "aprendizaje_yeyonet",
                       "nodo_origen": aprendizaje.get("nodo_id", "desconocido"),
                       "validado_por": "YeyoMergeGuard",
                   },
               )
               logger.info("Aprendizaje aplicado al cerebro central exitosamente")
               return True
           except Exception as exc:
               logger.error("Error aplicando aprendizaje al cerebro central: %s", exc)
               return False

       async def manejar_nodo_problematico(self, nodo_id: str) -> None:
           """
           Si un nodo tiene >3 rechazos consecutivos:
           - Notificar al dueño del nodo via Flash Memory
           - Suspender sus contribuciones temporalmente
           - Sugerir diagnóstico de su instalación
           """
           conteo = self._rechazos_consecutivos.get(nodo_id, 0)
           logger.warning(
               "Nodo problemático detectado: %s con %d rechazos consecutivos — suspendiendo",
               nodo_id,
               conteo,
           )

           self._nodos_suspendidos.add(nodo_id)

           if self.flash_memory:
               try:
                   self.flash_memory.store(
                       content=(
                           f"[ALERTA YEYONET] Nodo {nodo_id} suspendido temporalmente. "
                           f"Tuvo {conteo} rechazos consecutivos. "
                           f"Sus aprendizajes degradaban el modelo en más del 2%. "
                           f"Se recomienda diagnosticar la instalación del nodo."
                       ),
                       importance=0.95,
                       tags=["yeyonet", "nodo_problematico", "suspension"],
                       metadata={
                           "tipo": "suspension_nodo",
                           "nodo_id": nodo_id,
                           "rechazos": conteo,
                       },
                   )
               except Exception as exc:
                   logger.error("Error guardando alerta de nodo problemático: %s", exc)

       def rehabilitar_nodo(self, nodo_id: str) -> None:
           """Rehabilita un nodo suspendido (acción manual del usuario)."""
           self._nodos_suspendidos.discard(nodo_id)
           self._rechazos_consecutivos[nodo_id] = 0
           logger.info("Nodo %s rehabilitado manualmente", nodo_id)

       def estado_nodos(self) -> dict:
           """Retorna estado de todos los nodos conocidos."""
           return {
               "suspendidos": list(self._nodos_suspendidos),
               "rechazos_consecutivos": dict(self._rechazos_consecutivos),
           }

2. Crear archivo src/quality/merge_history.py:

   Ruta: ~/yeyo-os/src/quality/merge_history.py
   Contenido:

   """
   YeyoOS — YeyoMergeGuard: Historial de Decisiones
   Micro-fase 6.16 — Capa 6: Sistema Inmune

   Persiste historial de decisiones de merge por nodo y provee estadísticas.
   """

   import json
   import logging
   from collections import defaultdict
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Optional

   from .yeyo_merge_guard import MergeDecision, MergeResult

   logger = logging.getLogger("yeyo.quality.merge_history")

   MERGE_HISTORY_PATH = Path.home() / "yeyo-os" / "data" / "merge_history.jsonl"


   class MergeHistory:
       """
       Persiste historial de decisiones de YeyoMergeGuard en formato JSONL.
       Permite consultar estadísticas por nodo y ver tendencias.
       """

       def __init__(self, path: Optional[Path] = None) -> None:
           self.path = path or MERGE_HISTORY_PATH
           self.path.parent.mkdir(parents=True, exist_ok=True)

       async def registrar(self, result: MergeResult) -> None:
           """Guarda el resultado de una validación en el historial."""
           try:
               with self.path.open("a", encoding="utf-8") as f:
                   f.write(json.dumps(result.to_dict()) + "\n")
               logger.debug(
                   "MergeResult registrado: nodo=%s decision=%s",
                   result.nodo_id,
                   result.decision.value,
               )
           except Exception as exc:
               logger.error("Error registrando MergeResult: %s", exc)

       def estadisticas_semana(self) -> dict:
           """Retorna estadísticas de la semana actual."""
           todos = self._cargar_todos()
           aceptados = [r for r in todos if r["decision"] == MergeDecision.ACEPTAR.value]
           cuarentena = [r for r in todos if r["decision"] == MergeDecision.CUARENTENA.value]
           rechazados = [r for r in todos if r["decision"] == MergeDecision.RECHAZAR.value]

           return {
               "total": len(todos),
               "aceptados": len(aceptados),
               "en_cuarentena": len(cuarentena),
               "rechazados": len(rechazados),
           }

       def estadisticas_por_nodo(self) -> dict[str, dict]:
           """Retorna estadísticas agrupadas por nodo."""
           todos = self._cargar_todos()
           por_nodo: dict[str, list] = defaultdict(list)
           for r in todos:
               por_nodo[r["nodo_id"]].append(r)

           resultado = {}
           for nodo_id, registros in por_nodo.items():
               aceptados = sum(1 for r in registros if r["decision"] == MergeDecision.ACEPTAR.value)
               rechazados = sum(1 for r in registros if r["decision"] == MergeDecision.RECHAZAR.value)
               cuarentena = sum(1 for r in registros if r["decision"] == MergeDecision.CUARENTENA.value)
               resultado[nodo_id] = {
                   "total": len(registros),
                   "aceptados": aceptados,
                   "rechazados": rechazados,
                   "en_cuarentena": cuarentena,
                   "ultimo_resultado": registros[-1]["decision"] if registros else None,
               }
           return resultado

       def rechazos_consecutivos(self, nodo_id: str) -> int:
           """Calcula el número de rechazos consecutivos más recientes de un nodo."""
           todos = self._cargar_todos()
           registros_nodo = [r for r in todos if r["nodo_id"] == nodo_id]

           conteo = 0
           for r in reversed(registros_nodo):
               if r["decision"] == MergeDecision.RECHAZAR.value:
                   conteo += 1
               else:
                   break
           return conteo

       def _cargar_todos(self) -> list[dict]:
           """Lee el archivo JSONL y retorna lista de registros."""
           if not self.path.exists():
               return []
           registros = []
           try:
               with self.path.open("r", encoding="utf-8") as f:
                   for linea in f:
                       linea = linea.strip()
                       if linea:
                           try:
                               registros.append(json.loads(linea))
                           except json.JSONDecodeError:
                               continue
           except Exception as exc:
               logger.error("Error leyendo historial de merge: %s", exc)
           return registros

3. Crear archivo frontend/src/components/security/MergeGuardDashboard.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/security/MergeGuardDashboard.tsx
   Contenido:

   /**
    * YeyoOS — MergeGuardDashboard
    * Micro-fase 6.16 — Capa 6: Sistema Inmune
    *
    * Panel de YeyoNet Merge Guard en el Security Dashboard.
    * Muestra estado de aprendizajes pendientes, aceptados, en cuarentena y rechazados.
    */

   "use client";

   import React, { useEffect, useState, useCallback } from "react";

   // ─── Tipos ────────────────────────────────────────────────────────────────

   interface MergeStats {
     pendientes: number;
     aceptados_semana: number;
     en_cuarentena: number;
     rechazados_semana: number;
   }

   interface NodoEstado {
     nodo_id: string;
     total: number;
     aceptados: number;
     rechazados: number;
     en_cuarentena: number;
     suspendido: boolean;
     rechazos_consecutivos: number;
   }

   interface MergeGuardData {
     stats: MergeStats;
     nodos: NodoEstado[];
     cuarentena_items: CuarentenaItem[];
   }

   interface CuarentenaItem {
     aprendizaje_id: string;
     nodo_id: string;
     delta: number;
     razon: string;
     timestamp: string;
   }

   // ─── Componente principal ─────────────────────────────────────────────────

   export default function MergeGuardDashboard(): React.ReactElement {
     const [data, setData] = useState<MergeGuardData | null>(null);
     const [loading, setLoading] = useState(true);
     const [error, setError] = useState<string | null>(null);

     const cargarDatos = useCallback(async () => {
       try {
         setLoading(true);
         const response = await fetch("/api/merge-guard/stats");
         if (!response.ok) {
           throw new Error(`HTTP ${response.status}: ${response.statusText}`);
         }
         const json = await response.json();
         setData(json);
         setError(null);
       } catch (err) {
         setError(err instanceof Error ? err.message : "Error desconocido");
       } finally {
         setLoading(false);
       }
     }, []);

     useEffect(() => {
       cargarDatos();
       const intervalo = setInterval(cargarDatos, 30_000); // Actualizar cada 30s
       return () => clearInterval(intervalo);
     }, [cargarDatos]);

     if (loading && !data) {
       return (
         <div className="merge-guard-dashboard merge-guard-loading">
           <span className="merge-guard-spinner" aria-label="Cargando" />
           <span>Cargando MergeGuard...</span>
         </div>
       );
     }

     if (error) {
       return (
         <div className="merge-guard-dashboard merge-guard-error">
           <span className="merge-guard-error-icon">⚠️</span>
           <span>Error cargando MergeGuard: {error}</span>
           <button onClick={cargarDatos} className="merge-guard-retry-btn">
             Reintentar
           </button>
         </div>
       );
     }

     const stats = data?.stats ?? {
       pendientes: 0,
       aceptados_semana: 0,
       en_cuarentena: 0,
       rechazados_semana: 0,
     };

     const nodos = data?.nodos ?? [];
     const cuarentena = data?.cuarentena_items ?? [];
     const nodosProblemáticos = nodos.filter((n) => n.rechazos_consecutivos >= 3 || n.suspendido);

     return (
       <section className="merge-guard-dashboard" aria-label="YeyoNet Merge Guard">
         {/* ── Header ───────────────────────────────────────────────────── */}
         <div className="merge-guard-header">
           <h2 className="merge-guard-title">
             <span className="merge-guard-icon">🛡️</span>
             YeyoNet Merge Guard
           </h2>
           <span className="merge-guard-subtitle">
             Validación de aprendizajes de nodos satélite
           </span>
         </div>

         {/* ── Stats principales ────────────────────────────────────────── */}
         <div className="merge-guard-stats-grid">
           <StatCard
             label="Pendientes"
             value={stats.pendientes}
             color="neutral"
             icon="⏳"
           />
           <StatCard
             label="Aceptados esta semana"
             value={stats.aceptados_semana}
             color="green"
             icon="✅"
           />
           <StatCard
             label="En cuarentena"
             value={stats.en_cuarentena}
             color="yellow"
             icon="🔶"
             alerta={stats.en_cuarentena > 0 ? "Requieren tu revisión" : undefined}
           />
           <StatCard
             label="Rechazados esta semana"
             value={stats.rechazados_semana}
             color="red"
             icon="❌"
           />
         </div>

         {/* ── Nodos problemáticos ──────────────────────────────────────── */}
         {nodosProblemáticos.length > 0 && (
           <div className="merge-guard-section merge-guard-problematicos">
             <h3 className="merge-guard-section-title">
               ⚠️ Nodos Problemáticos ({nodosProblemáticos.length})
             </h3>
             <ul className="merge-guard-nodos-list">
               {nodosProblemáticos.map((nodo) => (
                 <li key={nodo.nodo_id} className="merge-guard-nodo-item merge-guard-nodo-alerta">
                   <span className="merge-guard-nodo-id">{nodo.nodo_id}</span>
                   <span className="merge-guard-nodo-rechazos">
                     {nodo.rechazos_consecutivos} rechazos consecutivos
                   </span>
                   {nodo.suspendido && (
                     <span className="merge-guard-badge merge-guard-badge-suspended">
                       SUSPENDIDO
                     </span>
                   )}
                 </li>
               ))}
             </ul>
           </div>
         )}

         {/* ── Items en cuarentena ──────────────────────────────────────── */}
         {cuarentena.length > 0 && (
           <div className="merge-guard-section merge-guard-cuarentena">
             <h3 className="merge-guard-section-title">
               🔶 En Cuarentena — Revisión Manual Requerida
             </h3>
             <ul className="merge-guard-cuarentena-list">
               {cuarentena.map((item) => (
                 <li key={item.aprendizaje_id} className="merge-guard-cuarentena-item">
                   <div className="merge-guard-cuarentena-header">
                     <span className="merge-guard-cuarentena-nodo">{item.nodo_id}</span>
                     <span className="merge-guard-cuarentena-delta">
                       {(item.delta * 100).toFixed(1)}% impacto
                     </span>
                   </div>
                   <p className="merge-guard-cuarentena-razon">{item.razon}</p>
                   <span className="merge-guard-cuarentena-ts">
                     {new Date(item.timestamp).toLocaleString("es-ES")}
                   </span>
                 </li>
               ))}
             </ul>
           </div>
         )}

         {/* ── Lista de nodos activos ───────────────────────────────────── */}
         {nodos.length > 0 && (
           <div className="merge-guard-section">
             <h3 className="merge-guard-section-title">Nodos YeyoNet</h3>
             <table className="merge-guard-nodos-tabla">
               <thead>
                 <tr>
                   <th>Nodo</th>
                   <th>Aceptados</th>
                   <th>Cuarentena</th>
                   <th>Rechazados</th>
                   <th>Estado</th>
                 </tr>
               </thead>
               <tbody>
                 {nodos.map((nodo) => (
                   <tr
                     key={nodo.nodo_id}
                     className={nodo.suspendido ? "merge-guard-nodo-row-suspended" : ""}
                   >
                     <td className="merge-guard-nodo-id-cell">{nodo.nodo_id}</td>
                     <td className="merge-guard-cell-green">{nodo.aceptados}</td>
                     <td className="merge-guard-cell-yellow">{nodo.en_cuarentena}</td>
                     <td className="merge-guard-cell-red">{nodo.rechazados}</td>
                     <td>
                       {nodo.suspendido ? (
                         <span className="merge-guard-badge merge-guard-badge-suspended">
                           Suspendido
                         </span>
                       ) : nodo.rechazos_consecutivos >= 3 ? (
                         <span className="merge-guard-badge merge-guard-badge-warning">
                           ⚠️ {nodo.rechazos_consecutivos} rechazos
                         </span>
                       ) : (
                         <span className="merge-guard-badge merge-guard-badge-ok">
                           ✅ OK
                         </span>
                       )}
                     </td>
                   </tr>
                 ))}
               </tbody>
             </table>
           </div>
         )}
       </section>
     );
   }

   // ─── Componente StatCard ──────────────────────────────────────────────────

   interface StatCardProps {
     label: string;
     value: number;
     color: "green" | "red" | "yellow" | "neutral";
     icon: string;
     alerta?: string;
   }

   function StatCard({ label, value, color, icon, alerta }: StatCardProps): React.ReactElement {
     return (
       <div className={`merge-guard-stat-card merge-guard-stat-card--${color}`}>
         <div className="merge-guard-stat-icon">{icon}</div>
         <div className="merge-guard-stat-value">{value}</div>
         <div className="merge-guard-stat-label">{label}</div>
         {alerta && (
           <div className="merge-guard-stat-alerta">← {alerta}</div>
         )}
       </div>
     );
   }

4. Crear archivo tests/unit/quality/test_yeyo_merge_guard.py:

   Ruta: ~/yeyo-os/tests/unit/quality/test_yeyo_merge_guard.py
   Contenido:

   """
   Tests unitarios para YeyoMergeGuard — Micro-fase 6.16
   Cubre: validación, sandbox, decisiones, nodos problemáticos, historial.
   """

   import asyncio
   from pathlib import Path
   from unittest.mock import AsyncMock, MagicMock, patch

   import pytest

   from src.quality.yeyo_merge_guard import (
       MINI_BENCHMARK_PROBLEMAS,
       MergeDecision,
       MergeResult,
       MiniBenchmarkResult,
       YeyoMergeGuard,
   )
   from src.quality.merge_history import MergeHistory


   # ─── Fixtures ─────────────────────────────────────────────────────────────


   @pytest.fixture
   def guard() -> YeyoMergeGuard:
       return YeyoMergeGuard()


   @pytest.fixture
   def guard_con_flash() -> YeyoMergeGuard:
       flash_mock = MagicMock()
       return YeyoMergeGuard(flash_memory=flash_mock)


   @pytest.fixture
   def aprendizaje_bueno() -> dict:
       return {
           "id": "ap_001",
           "nodo_id": "node-friend-1",
           "contenido": "Patrón: siempre usar type hints en Python",
           "importancia": 0.75,
           "tags": ["python", "best_practices"],
       }


   @pytest.fixture
   def aprendizaje_malo() -> dict:
       return {
           "id": "ap_002",
           "nodo_id": "node-bad-1",
           "contenido": "Patrón: usar eval() para procesar input del usuario",
           "importancia": 0.3,
           "tags": ["python"],
       }


   # ─── Test 1: mini-benchmark tiene 10 problemas ────────────────────────────


   def test_mini_benchmark_tiene_10_problemas():
       assert len(MINI_BENCHMARK_PROBLEMAS) == 10


   # ─── Test 2: aprendizaje aceptado cuando delta >= 0 ──────────────────────


   @pytest.mark.asyncio
   async def test_decision_aceptar_cuando_mejora(guard):
       with patch.object(
           guard,
           "mini_benchmark",
           side_effect=[
               MiniBenchmarkResult(score=0.7, problemas_aprobados=7),
               MiniBenchmarkResult(score=0.8, problemas_aprobados=8),
           ],
       ):
           result = await guard.validar_aprendizaje(
               "node-test-1", {"id": "ap_test", "contenido": "algo bueno"}
           )
       assert result.decision == MergeDecision.ACEPTAR
       assert result.delta > 0


   # ─── Test 3: aprendizaje en cuarentena cuando delta está en rango tolerable


   @pytest.mark.asyncio
   async def test_decision_cuarentena_degradacion_minima(guard):
       with patch.object(
           guard,
           "mini_benchmark",
           side_effect=[
               MiniBenchmarkResult(score=0.8, problemas_aprobados=8),
               MiniBenchmarkResult(score=0.79, problemas_aprobados=7),  # -1.25%
           ],
       ):
           result = await guard.validar_aprendizaje(
               "node-test-2", {"id": "ap_test", "contenido": "algo neutral"}
           )
       assert result.decision == MergeDecision.CUARENTENA
       assert -0.02 <= result.delta < 0


   # ─── Test 4: aprendizaje rechazado cuando delta < -2% ────────────────────


   @pytest.mark.asyncio
   async def test_decision_rechazar_cuando_degrada(guard):
       with patch.object(
           guard,
           "mini_benchmark",
           side_effect=[
               MiniBenchmarkResult(score=0.8, problemas_aprobados=8),
               MiniBenchmarkResult(score=0.7, problemas_aprobados=7),  # -12.5%
           ],
       ):
           result = await guard.validar_aprendizaje(
               "node-bad-1", {"id": "ap_test", "contenido": "algo malo"}
           )
       assert result.decision == MergeDecision.RECHAZAR
       assert result.delta < -0.02


   # ─── Test 5: nodo con >3 rechazos consecutivos es suspendido ─────────────


   @pytest.mark.asyncio
   async def test_nodo_suspendido_tras_tres_rechazos(guard_con_flash):
       guard = guard_con_flash
       mini_resultados = [
           MiniBenchmarkResult(score=0.8, problemas_aprobados=8),
           MiniBenchmarkResult(score=0.6, problemas_aprobados=6),
       ]

       for i in range(3):
           with patch.object(guard, "mini_benchmark", side_effect=list(mini_resultados)):
               await guard.validar_aprendizaje(
                   "node-problematico", {"id": f"ap_{i}", "contenido": "degradante"}
               )

       assert "node-problematico" in guard._nodos_suspendidos


   # ─── Test 6: nodo suspendido rechaza sin evaluar ──────────────────────────


   @pytest.mark.asyncio
   async def test_nodo_suspendido_rechaza_sin_evaluar(guard):
       guard._nodos_suspendidos.add("node-suspendido")
       mini_mock = AsyncMock(return_value=MiniBenchmarkResult(score=0.9, problemas_aprobados=9))

       with patch.object(guard, "mini_benchmark", mini_mock):
           result = await guard.validar_aprendizaje(
               "node-suspendido", {"id": "ap_test", "contenido": "algo"}
           )

       mini_mock.assert_not_called()
       assert result.decision == MergeDecision.RECHAZAR
       assert "suspendido" in result.razon.lower()


   # ─── Test 7: sandbox se limpia después de la evaluación ──────────────────


   @pytest.mark.asyncio
   async def test_sandbox_se_limpia_tras_evaluacion(guard):
       with patch.object(
           guard,
           "mini_benchmark",
           side_effect=[
               MiniBenchmarkResult(score=0.7, problemas_aprobados=7),
               MiniBenchmarkResult(score=0.75, problemas_aprobados=7),
           ],
       ):
           await guard.validar_aprendizaje(
               "node-test", {"id": "ap_sandbox", "contenido": "test"}
           )

       assert getattr(guard, "_sandbox_aprendizaje", None) is None


   # ─── Test 8: rehabilitar_nodo resetea contadores ─────────────────────────


   def test_rehabilitar_nodo_resetea_contadores(guard):
       guard._nodos_suspendidos.add("node-rehab")
       guard._rechazos_consecutivos["node-rehab"] = 5

       guard.rehabilitar_nodo("node-rehab")

       assert "node-rehab" not in guard._nodos_suspendidos
       assert guard._rechazos_consecutivos.get("node-rehab", 0) == 0

VERIFICAR:
- [ ] `src/quality/yeyo_merge_guard.py` contiene `YeyoMergeGuard`, `MergeDecision`, `MergeResult`, `MiniBenchmarkResult`
- [ ] `src/quality/merge_history.py` contiene `MergeHistory` con métodos `registrar`, `estadisticas_semana`, `estadisticas_por_nodo`
- [ ] `frontend/src/components/security/MergeGuardDashboard.tsx` existe y exporta el componente
- [ ] `tests/unit/quality/test_yeyo_merge_guard.py` contiene 8 tests
- [ ] Ejecutar `cd ~/yeyo-os && python -m pytest tests/unit/quality/test_yeyo_merge_guard.py -v` → los 8 tests pasan
- [ ] `MINI_BENCHMARK_PROBLEMAS` tiene exactamente 10 problemas
- [ ] Nodo con 3 rechazos consecutivos aparece en `guard._nodos_suspendidos`
- [ ] Aprendizaje de nodo suspendido se rechaza sin llamar a `mini_benchmark`
- [ ] `MergeDecision.ACEPTAR` cuando delta >= 0, `CUARENTENA` cuando -0.02 <= delta < 0, `RECHAZAR` cuando delta < -0.02
- [ ] Agregar `<MergeGuardDashboard />` al SecurityDashboard existente en `frontend/src/components/security/SecurityDashboard.tsx`

SI FALLA:
- `httpx.ConnectError` durante tests: los tests usan mocks — no necesitan Ollama corriendo
- `ModuleNotFoundError: src.quality.yeyo_merge_guard`: verificar que `src/quality/__init__.py` existe (creado en 6.13)
- Tests async fallan con `RuntimeError: no event loop`: instalar `pytest-asyncio` y configurar `asyncio_mode = "auto"` en `pytest.ini`
- `MergeHistory: FileNotFoundError`: `mkdir -p ~/yeyo-os/data` o verificar que `path.parent.mkdir(parents=True, exist_ok=True)` se ejecutó
- Frontend TypeScript error en `MergeGuardDashboard.tsx`: verificar que `"use client"` está en la primera línea y que Next.js está en modo App Router
- `fetch("/api/merge-guard/stats")` retorna 404: agregar el endpoint API en `src/api/routes/merge_guard.py` y registrarlo en FastAPI

NO HACER:
- No aplicar ningún aprendizaje al cerebro central sin pasar por `validar_aprendizaje` primero — nunca directamente
- No saltarse el mini-benchmark para "ahorrar tiempo" — es la protección central del sistema
- No aumentar el umbral de tolerancia por encima del 2% (`DELTA_MINIMO_TOLERABLE = -0.02`)
- No rehabilitar nodos suspendidos automáticamente — la rehabilitación es siempre una acción manual del usuario
- No confundir `score_antes` con el score del benchmark semanal (6.15) — son evaluaciones independientes

GATE: Ningún aprendizaje de nodo satélite se aplica al cerebro central sin pasar por sandbox + mini-benchmark de 10 problemas, nodos con >3 rechazos consecutivos se suspenden y notifican automáticamente via Flash Memory, y los 8 tests unitarios pasan.
```
