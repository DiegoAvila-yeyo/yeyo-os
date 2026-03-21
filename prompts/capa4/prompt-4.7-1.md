## ═══════════════════════════════════════
## MICRO-FASE 4.7 — Pipeline Engine
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.7-1 [VSCODE] — Motor de pipelines con detección de ciclos

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.7 de Capa 4 (Sistema Nervioso): crear el motor de pipelines visuales que conecta nodos para workflows automatizados.

CONTEXTO:
- Micro-fases 4.0-4.6 completadas: paquetes, permisos, containers, drag & drop
- Pipeline = secuencia de pasos donde cada paso es un nodo con input/output
- Detección de ciclos obligatoria (DAG validation con topological sort)
- Cada paso verifica permisos antes de ejecutar
- Si un paso falla, el pipeline se detiene (fail-fast)
- Status tracking en tiempo real: pending → running → completed | failed

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/pipeline
   mkdir -p tests/unit/pipeline

2. Crear archivo src/pipeline/__init__.py:

   Ruta: ~/yeyo-os/src/pipeline/__init__.py
   Contenido:
   from .engine import PipelineEngine, PipelineStep, PipelineResult, PipelineError, CycleDetectedError

3. Crear archivo src/pipeline/engine.py:

   Ruta: ~/yeyo-os/src/pipeline/engine.py
   Contenido:

   """
   YeyoOS — Pipeline Engine
   Micro-fase 4.7 — Capa 4: Sistema Nervioso

   Motor de pipelines visuales con detección de ciclos (DAG).
   Cada paso = un nodo con input/output. Fail-fast en errores.
   """

   import uuid
   from enum import Enum
   from datetime import datetime, timezone
   from typing import Optional, Any, Callable, Awaitable
   from dataclasses import dataclass, field
   from collections import defaultdict


   class StepStatus(str, Enum):
       PENDING = "pending"
       RUNNING = "running"
       COMPLETED = "completed"
       FAILED = "failed"
       SKIPPED = "skipped"


   class PipelineStatus(str, Enum):
       CREATED = "created"
       VALIDATING = "validating"
       RUNNING = "running"
       COMPLETED = "completed"
       FAILED = "failed"
       CANCELLED = "cancelled"


   class PipelineError(Exception):
       """Error genérico de pipeline."""
       pass


   class CycleDetectedError(PipelineError):
       """Error cuando se detecta un ciclo en el pipeline."""
       pass


   @dataclass
   class PipelineStep:
       """Un paso en el pipeline."""
       id: str
       name: str
       node_type: str
       config: dict = field(default_factory=dict)
       depends_on: list[str] = field(default_factory=list)
       status: StepStatus = StepStatus.PENDING
       output: Any = None
       error: Optional[str] = None
       started_at: Optional[datetime] = None
       completed_at: Optional[datetime] = None


   @dataclass
   class PipelineResult:
       """Resultado de la ejecución de un pipeline."""
       pipeline_id: str
       status: PipelineStatus
       steps: list[PipelineStep]
       output: Any = None
       error: Optional[str] = None
       started_at: Optional[datetime] = None
       completed_at: Optional[datetime] = None


   StepExecutor = Callable[[PipelineStep, dict], Awaitable[Any]]


   class PipelineEngine:
       """Motor de ejecución de pipelines con validación DAG."""

       def __init__(self):
           self._pipelines: dict[str, dict] = {}
           self._step_executors: dict[str, StepExecutor] = {}

       def register_executor(self, node_type: str, executor: StepExecutor) -> None:
           """Registra un ejecutor para un tipo de nodo."""
           self._step_executors[node_type] = executor

       async def create_pipeline(
           self, name: str, steps: list[dict]
       ) -> str:
           """
           Crea un pipeline y retorna su ID.
           Valida que no tenga ciclos (DAG).
           """
           pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"

           parsed_steps = []
           for step_data in steps:
               step = PipelineStep(
                   id=step_data["id"],
                   name=step_data.get("name", step_data["id"]),
                   node_type=step_data.get("node_type", "generic"),
                   config=step_data.get("config", {}),
                   depends_on=step_data.get("depends_on", []),
               )
               parsed_steps.append(step)

           validation = self.validate(parsed_steps)
           if not validation["valid"]:
               raise PipelineError(
                   f"Pipeline inválido: {validation.get('error', 'desconocido')}"
               )

           self._pipelines[pipeline_id] = {
               "id": pipeline_id,
               "name": name,
               "steps": parsed_steps,
               "status": PipelineStatus.CREATED,
               "created_at": datetime.now(timezone.utc),
           }

           return pipeline_id

       async def execute(
           self, pipeline_id: str, input_data: Optional[dict] = None
       ) -> PipelineResult:
           """
           Ejecuta un pipeline paso a paso.
           Fail-fast: si un paso falla, el pipeline se detiene.
           """
           if pipeline_id not in self._pipelines:
               raise PipelineError(f"Pipeline '{pipeline_id}' no encontrado")

           pipeline = self._pipelines[pipeline_id]
           steps: list[PipelineStep] = pipeline["steps"]
           pipeline["status"] = PipelineStatus.RUNNING

           result = PipelineResult(
               pipeline_id=pipeline_id,
               status=PipelineStatus.RUNNING,
               steps=steps,
               started_at=datetime.now(timezone.utc),
           )

           execution_order = self._topological_sort(steps)
           step_outputs: dict[str, Any] = {}

           if input_data:
               step_outputs["__input__"] = input_data

           for step_id in execution_order:
               step = next(s for s in steps if s.id == step_id)

               dep_inputs = {}
               for dep_id in step.depends_on:
                   if dep_id in step_outputs:
                       dep_inputs[dep_id] = step_outputs[dep_id]

               if input_data and not step.depends_on:
                   dep_inputs["__input__"] = input_data

               step.status = StepStatus.RUNNING
               step.started_at = datetime.now(timezone.utc)

               try:
                   executor = self._step_executors.get(step.node_type)
                   if executor:
                       step.output = await executor(step, dep_inputs)
                   else:
                       step.output = dep_inputs

                   step.status = StepStatus.COMPLETED
                   step.completed_at = datetime.now(timezone.utc)
                   step_outputs[step.id] = step.output

               except Exception as e:
                   step.status = StepStatus.FAILED
                   step.error = str(e)
                   step.completed_at = datetime.now(timezone.utc)

                   for remaining_step in steps:
                       if remaining_step.status == StepStatus.PENDING:
                           remaining_step.status = StepStatus.SKIPPED

                   result.status = PipelineStatus.FAILED
                   result.error = f"Paso '{step.name}' falló: {e}"
                   result.completed_at = datetime.now(timezone.utc)
                   pipeline["status"] = PipelineStatus.FAILED
                   return result

           last_step_id = execution_order[-1] if execution_order else None
           result.output = step_outputs.get(last_step_id) if last_step_id else None
           result.status = PipelineStatus.COMPLETED
           result.completed_at = datetime.now(timezone.utc)
           pipeline["status"] = PipelineStatus.COMPLETED

           return result

       def validate(self, steps: list[PipelineStep]) -> dict:
           """
           Valida un pipeline.
           Verifica: sin ciclos (DAG), dependencias existentes, IDs únicos.
           """
           step_ids = {s.id for s in steps}

           if len(step_ids) != len(steps):
               return {"valid": False, "error": "IDs de pasos duplicados"}

           for step in steps:
               for dep in step.depends_on:
                   if dep not in step_ids:
                       return {
                           "valid": False,
                           "error": f"Dependencia '{dep}' no existe para paso '{step.id}'"
                       }

           try:
               self._topological_sort(steps)
           except CycleDetectedError as e:
               return {"valid": False, "error": str(e)}

           return {"valid": True, "execution_order": self._topological_sort(steps)}

       def _topological_sort(self, steps: list[PipelineStep]) -> list[str]:
           """
           Ordena los pasos topológicamente (Kahn's algorithm).
           Lanza CycleDetectedError si detecta un ciclo.
           """
           graph: dict[str, list[str]] = defaultdict(list)
           in_degree: dict[str, int] = {s.id: 0 for s in steps}

           for step in steps:
               for dep in step.depends_on:
                   graph[dep].append(step.id)
                   in_degree[step.id] += 1

           queue = [sid for sid, deg in in_degree.items() if deg == 0]
           order = []

           while queue:
               queue.sort()
               node = queue.pop(0)
               order.append(node)

               for neighbor in graph[node]:
                   in_degree[neighbor] -= 1
                   if in_degree[neighbor] == 0:
                       queue.append(neighbor)

           if len(order) != len(steps):
               raise CycleDetectedError(
                   "Ciclo detectado en el pipeline. "
                   "Los pipelines deben ser grafos acíclicos dirigidos (DAG)."
               )

           return order

       async def get_status(self, pipeline_id: str) -> dict:
           """Obtiene el estado de un pipeline."""
           if pipeline_id not in self._pipelines:
               raise PipelineError(f"Pipeline '{pipeline_id}' no encontrado")

           pipeline = self._pipelines[pipeline_id]
           steps = pipeline["steps"]

           return {
               "pipeline_id": pipeline_id,
               "name": pipeline["name"],
               "status": pipeline["status"].value,
               "steps": [
                   {
                       "id": s.id,
                       "name": s.name,
                       "status": s.status.value,
                       "error": s.error,
                   }
                   for s in steps
               ],
           }

       async def cancel(self, pipeline_id: str) -> None:
           """Cancela un pipeline en ejecución."""
           if pipeline_id not in self._pipelines:
               raise PipelineError(f"Pipeline '{pipeline_id}' no encontrado")

           pipeline = self._pipelines[pipeline_id]
           pipeline["status"] = PipelineStatus.CANCELLED

           for step in pipeline["steps"]:
               if step.status in (StepStatus.PENDING, StepStatus.RUNNING):
                   step.status = StepStatus.SKIPPED

       async def delete(self, pipeline_id: str) -> None:
           """Elimina un pipeline."""
           if pipeline_id not in self._pipelines:
               raise PipelineError(f"Pipeline '{pipeline_id}' no encontrado")
           del self._pipelines[pipeline_id]

       def list_pipelines(self) -> list[dict]:
           """Lista todos los pipelines."""
           return [
               {
                   "id": p["id"],
                   "name": p["name"],
                   "status": p["status"].value,
               }
               for p in self._pipelines.values()
           ]

VERIFICAR:
- [ ] Archivo src/pipeline/engine.py existe con PipelineEngine
- [ ] create_pipeline valida y retorna ID
- [ ] Detección de ciclos con topological sort (Kahn's algorithm)
- [ ] Pipeline ejecuta pasos en orden correcto
- [ ] Fail-fast: si un paso falla, el pipeline se detiene
- [ ] Status tracking: pending → running → completed | failed
- [ ] Pasos restantes se marcan como skipped en fallo

SI FALLA:
- Import error: verificar __init__.py
- Topological sort: verificar implementación de Kahn's algorithm
- Asyncio: verificar que usa async/await correctamente

NO HACER:
- No implementar tests aquí (eso es prompt 4.7-2)
- No conectar con el sistema de permisos aún
- No implementar UI de pipelines

GATE: PipelineEngine creado con validación DAG, topological sort, fail-fast, status tracking. Tests en siguiente prompt.
```
