## ═══════════════════════════════════════
## MICRO-FASE 4.7 — Pipeline Engine Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.7-2 [VSCODE] — Tests del motor de pipelines

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la segunda parte de la micro-fase 4.7 de Capa 4 (Sistema Nervioso): tests para el motor de pipelines.

CONTEXTO:
- Prompt 4.7-1 completado: PipelineEngine con topological sort y DAG validation
- El motor ejecuta pasos en orden topológico
- Detección de ciclos obligatoria
- Fail-fast: si un paso falla, el pipeline se detiene
- Status tracking: pending → running → completed | failed

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo tests/unit/pipeline/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/pipeline/__init__.py
   Contenido: (archivo vacío)

2. Crear archivo tests/unit/pipeline/test_engine.py:

   Ruta: ~/yeyo-os/tests/unit/pipeline/test_engine.py
   Contenido:

   """Tests para Pipeline Engine — Micro-fase 4.7"""

   import pytest
   from src.pipeline.engine import (
       PipelineEngine,
       PipelineStep,
       PipelineError,
       CycleDetectedError,
       StepStatus,
       PipelineStatus,
   )


   @pytest.fixture
   def engine():
       return PipelineEngine()


   def make_steps(step_defs: list[dict]) -> list[dict]:
       """Helper para crear definiciones de pasos."""
       return step_defs


   class TestPipelineCreation:
       """Tests para creación de pipelines."""

       @pytest.mark.asyncio
       async def test_create_pipeline_returns_id(self, engine):
           steps = [
               {"id": "step-1", "name": "Paso 1", "node_type": "generic"},
               {"id": "step-2", "name": "Paso 2", "node_type": "generic", "depends_on": ["step-1"]},
           ]
           pipeline_id = await engine.create_pipeline("test-pipeline", steps)
           assert pipeline_id.startswith("pipeline-")

       @pytest.mark.asyncio
       async def test_create_pipeline_validates_dag(self, engine):
           steps = [
               {"id": "step-1", "name": "Paso 1", "depends_on": ["step-2"]},
               {"id": "step-2", "name": "Paso 2", "depends_on": ["step-1"]},
           ]
           with pytest.raises(PipelineError, match="inválido"):
               await engine.create_pipeline("cycle-test", steps)

       @pytest.mark.asyncio
       async def test_create_empty_pipeline(self, engine):
           pipeline_id = await engine.create_pipeline("empty", [])
           assert pipeline_id.startswith("pipeline-")


   class TestCycleDetection:
       """Tests para detección de ciclos."""

       def test_simple_cycle_detected(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic", depends_on=["b"]),
               PipelineStep(id="b", name="B", node_type="generic", depends_on=["a"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is False
           assert "Ciclo" in result.get("error", "")

       def test_three_node_cycle_detected(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic", depends_on=["c"]),
               PipelineStep(id="b", name="B", node_type="generic", depends_on=["a"]),
               PipelineStep(id="c", name="C", node_type="generic", depends_on=["b"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is False

       def test_self_cycle_detected(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic", depends_on=["a"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is False

       def test_dag_is_valid(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic"),
               PipelineStep(id="b", name="B", node_type="generic", depends_on=["a"]),
               PipelineStep(id="c", name="C", node_type="generic", depends_on=["a"]),
               PipelineStep(id="d", name="D", node_type="generic", depends_on=["b", "c"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is True

       def test_linear_pipeline_valid(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic"),
               PipelineStep(id="b", name="B", node_type="generic", depends_on=["a"]),
               PipelineStep(id="c", name="C", node_type="generic", depends_on=["b"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is True
           assert result["execution_order"] == ["a", "b", "c"]

       def test_missing_dependency_detected(self, engine):
           steps = [
               PipelineStep(id="a", name="A", node_type="generic", depends_on=["nonexistent"]),
           ]
           result = engine.validate(steps)
           assert result["valid"] is False
           assert "no existe" in result.get("error", "")

       def test_duplicate_ids_detected(self, engine):
           steps = [
               PipelineStep(id="a", name="A1", node_type="generic"),
               PipelineStep(id="a", name="A2", node_type="generic"),
           ]
           result = engine.validate(steps)
           assert result["valid"] is False


   class TestPipelineExecution:
       """Tests para ejecución de pipelines."""

       @pytest.mark.asyncio
       async def test_pipeline_executes_steps_in_order(self, engine):
           execution_log = []

           async def log_executor(step, inputs):
               execution_log.append(step.id)
               return f"output-{step.id}"

           engine.register_executor("generic", log_executor)

           steps = [
               {"id": "step-1", "name": "Paso 1", "node_type": "generic"},
               {"id": "step-2", "name": "Paso 2", "node_type": "generic", "depends_on": ["step-1"]},
               {"id": "step-3", "name": "Paso 3", "node_type": "generic", "depends_on": ["step-2"]},
           ]
           pipeline_id = await engine.create_pipeline("test", steps)
           result = await engine.execute(pipeline_id)

           assert execution_log == ["step-1", "step-2", "step-3"]
           assert result.status == PipelineStatus.COMPLETED

       @pytest.mark.asyncio
       async def test_step_failure_stops_pipeline(self, engine):
           call_count = 0

           async def failing_executor(step, inputs):
               nonlocal call_count
               call_count += 1
               if step.id == "step-2":
                   raise RuntimeError("Step 2 falló!")
               return "ok"

           engine.register_executor("generic", failing_executor)

           steps = [
               {"id": "step-1", "name": "Paso 1", "node_type": "generic"},
               {"id": "step-2", "name": "Paso 2", "node_type": "generic", "depends_on": ["step-1"]},
               {"id": "step-3", "name": "Paso 3", "node_type": "generic", "depends_on": ["step-2"]},
           ]
           pipeline_id = await engine.create_pipeline("test", steps)
           result = await engine.execute(pipeline_id)

           assert result.status == PipelineStatus.FAILED
           assert "step-2" in result.error or "Paso 2" in result.error
           assert call_count == 2

           step_3 = next(s for s in result.steps if s.id == "step-3")
           assert step_3.status == StepStatus.SKIPPED

       @pytest.mark.asyncio
       async def test_pipeline_passes_input_data(self, engine):
           received_inputs = {}

           async def capture_executor(step, inputs):
               received_inputs[step.id] = inputs
               return {"processed": True, "step": step.id}

           engine.register_executor("generic", capture_executor)

           steps = [
               {"id": "step-1", "name": "Paso 1", "node_type": "generic"},
           ]
           pipeline_id = await engine.create_pipeline("test", steps)
           result = await engine.execute(pipeline_id, input_data={"key": "value"})

           assert result.status == PipelineStatus.COMPLETED
           assert "__input__" in received_inputs["step-1"]

       @pytest.mark.asyncio
       async def test_pipeline_output_is_last_step(self, engine):
           async def output_executor(step, inputs):
               return f"final-output-{step.id}"

           engine.register_executor("generic", output_executor)

           steps = [
               {"id": "step-1", "name": "Paso 1", "node_type": "generic"},
               {"id": "step-2", "name": "Paso 2", "node_type": "generic", "depends_on": ["step-1"]},
           ]
           pipeline_id = await engine.create_pipeline("test", steps)
           result = await engine.execute(pipeline_id)

           assert result.output == "final-output-step-2"


   class TestPipelineStatus:
       """Tests para status tracking."""

       @pytest.mark.asyncio
       async def test_status_tracking(self, engine):
           async def noop_executor(step, inputs):
               return None

           engine.register_executor("generic", noop_executor)

           steps = [{"id": "step-1", "name": "Paso 1", "node_type": "generic"}]
           pipeline_id = await engine.create_pipeline("test", steps)

           status = await engine.get_status(pipeline_id)
           assert status["status"] == "created"

           await engine.execute(pipeline_id)

           status = await engine.get_status(pipeline_id)
           assert status["status"] == "completed"

       @pytest.mark.asyncio
       async def test_status_nonexistent_raises(self, engine):
           with pytest.raises(PipelineError):
               await engine.get_status("nonexistent-id")

       @pytest.mark.asyncio
       async def test_execute_nonexistent_raises(self, engine):
           with pytest.raises(PipelineError):
               await engine.execute("nonexistent-id")

       @pytest.mark.asyncio
       async def test_cancel_pipeline(self, engine):
           steps = [{"id": "step-1", "name": "Paso 1", "node_type": "generic"}]
           pipeline_id = await engine.create_pipeline("test", steps)
           await engine.cancel(pipeline_id)

           status = await engine.get_status(pipeline_id)
           assert status["status"] == "cancelled"

       @pytest.mark.asyncio
       async def test_delete_pipeline(self, engine):
           steps = [{"id": "step-1", "name": "Paso 1", "node_type": "generic"}]
           pipeline_id = await engine.create_pipeline("test", steps)
           await engine.delete(pipeline_id)

           with pytest.raises(PipelineError):
               await engine.get_status(pipeline_id)

       @pytest.mark.asyncio
       async def test_list_pipelines(self, engine):
           steps = [{"id": "step-1", "name": "Paso 1", "node_type": "generic"}]
           await engine.create_pipeline("pipeline-a", steps)
           await engine.create_pipeline("pipeline-b", steps)

           pipelines = engine.list_pipelines()
           assert len(pipelines) == 2

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pipeline/test_engine.py -v

VERIFICAR:
- [ ] Archivo tests/unit/pipeline/test_engine.py existe
- [ ] Pipeline ejecuta pasos en orden topológico correcto
- [ ] Ciclos simples (A↔B) detectados y rechazados
- [ ] Ciclos de 3 nodos detectados
- [ ] Auto-ciclo (A→A) detectado
- [ ] Pipeline lineal (A→B→C) es válido
- [ ] DAG (diamante: A→B,C→D) es válido
- [ ] Fallo de paso detiene pipeline (fail-fast)
- [ ] Pasos restantes se marcan como SKIPPED
- [ ] Status tracking funciona: created → completed/failed
- [ ] Input data pasa correctamente al primer paso
- [ ] Output del pipeline es el output del último paso
- [ ] Cancel y delete funcionan
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py en src/pipeline/ y tests/unit/pipeline/
- pytest-asyncio: pip install pytest-asyncio
- CycleDetectedError: verificar que topological sort lanza correctamente

NO HACER:
- No modificar el engine (ya está en 4.7-1)
- No implementar UI de pipelines (eso es 4.12)
- No conectar con permisos reales

GATE: Pipeline engine validado exhaustivamente, ciclos detectados, fail-fast funciona, status tracking correcto, todos los tests pasan.
```
