Usa la skill interactive-session para esta tarea.

# 🧪 YeyoOS — QA Completo: Mini-Proyecto por Nodo

## REGLAS GLOBALES

1. **Fix-until-works**: Cuando algo falle, analiza el error, repara el código (backend o frontend), reinicia el servidor si es necesario, y vuelve a intentar. Repite hasta que funcione. NO avances al siguiente nodo hasta que TODOS los pasos del actual pasen.

2. **Evidencia**: Guarda TODO en `tests/qa-results/nodo-NOMBRE/`:
   - Screenshots (Playwright) de cada paso del flujo
   - Logs de errores encontrados y cómo se resolvieron (archivo `fixes.md`)
   - Resultado final: `REPORT.md` con PASS/FAIL por funcionalidad
   - Los mini-proyectos creados (JSON exports, archivos generados)

3. **Orden**: Ejecutar nodos en este orden: Video → Storyboard → Laboratorio → Observatory → Workshop → Arena → Integración

4. **Servidores**: Backend en :8000 (uvicorn con el .venv del worktree), Frontend en :3000 (pnpm dev). Verificar que están corriendo antes de cada nodo. Si no, arrancarlos:
   - Backend: `/Users/eltitoyeyo/YEYO/yeyo-os.worktrees/copilot-worktree-2026-04-05T05-46-52/.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload`
   - Frontend: `cd frontend && pnpm dev`
   Onboarding del frontend: escribir "Yeyo" + Enter, luego "Testing" + Enter para llegar al Hub.

5. **Commits**: Un commit después de cada nodo arreglado + verificado, con mensaje descriptivo.

6. **Base de datos**: PostgreSQL en `postgresql://eltitoyeyo@localhost:5432/yeyoos`. Las migraciones 009-013 ya están aplicadas.

7. **Ollama**: localhost:11434. Si no responde, los agentes/IA deben funcionar con fallbacks (templates, simulación).

## CONTEXTO

Repo: /Users/eltitoyeyo/YEYO/yeyo-os
Branch: main
Stack: Python 3.11 + FastAPI + Next.js 16 + TypeScript + Zustand + TailwindCSS
Venv: /Users/eltitoyeyo/YEYO/yeyo-os.worktrees/copilot-worktree-2026-04-05T05-46-52/.venv/bin/python
Playwright: Ya instalado (python3 -m playwright, headless chromium)

---

## NODO 1: 🎬 Video Editor — Mini-Proyecto "Trailer de 15 segundos"

### Flujo completo a probar:

**Paso 1 — Abrir nodo Video desde Hub**
- Playwright: navegar a localhost:3000, completar onboarding, abrir nodo Video
- Screenshot: `01_video_abierto.png`
- Verificar: existen los 3 tabs (Efectos, Texto, IA) y 5 tracks (V1, V2, T, A1, A2)

**Paso 2 — APIs de video**
- GET /api/v1/video/filters → debe retornar 4 filtros (sepia, bw, vintage, cinematic)
- GET /api/v1/video/transitions → debe retornar 5 transiciones (fade, dissolve, wipe, zoom, slide)
- Si alguno falla → arreglar el backend, reiniciar, reintentar

**Paso 3 — Tab Efectos**
- Verificar que los 4 filtros son clickeables
- Verificar que las 5 transiciones son clickeables
- Verificar que los 4 botones de velocidad (0.5x, 1x, 2x, 4x) existen
- Screenshot: `02_tab_efectos.png`

**Paso 4 — Tab Texto**
- Verificar botón "Auto-subtítulos" existe
- Verificar que se puede escribir texto overlay (textarea, posición, color, duración)
- Verificar 3 templates de título (Intro, Outro, Lower Third)
- Screenshot: `03_tab_texto.png`

**Paso 5 — Tab IA**
- Verificar chat input existe
- Verificar chips de sugerencias ("Añade subtítulos", etc.)
- Enviar mensaje al chat: "¿qué puedo hacer con este editor?"
- Screenshot: `04_tab_ia.png`

**Paso 6 — Undo/Redo**
- Verificar botones Undo/Redo existen en controles
- Screenshot: `05_controles.png`

**Paso 7 — Export Modal**
- Click en botón Export
- Verificar modal aparece con opciones (resolución, FPS, subtítulos checkbox)
- Screenshot: `06_export_modal.png`

**Paso 8 — API Export**
- POST /api/v1/video/subtitles/generate con un archivo de audio/video de test → verificar respuesta
- POST /api/v1/video/filter/apply con un video de test → verificar respuesta
- Si no hay video de test disponible, verificar que el endpoint responde con error descriptivo (422, no 500)

**Resultado esperado**: Todas las funcionalidades visibles y APIs respondiendo correctamente.

---

## NODO 2: 📋 Storyboard — Mini-Proyecto "Historia de un Robot en 6 Frames"

### Flujo completo:

**Paso 1 — Abrir nodo Storyboard desde Hub**
- Screenshot: `01_storyboard_abierto.png`
- Verificar: fondo crema (#F5F0E8), panel assets (izq), canvas (centro), detalles (der)

**Paso 2 — Crear storyboard**
- POST /api/v1/storyboard/ con name="Robot Adventure", description="Un robot explora una ciudad abandonada"
- Guardar el ID retornado
- Si falla → revisar backend, arreglar, reintentar

**Paso 3 — Agregar 6 frames al storyboard**
- POST /api/v1/storyboard/{id}/frames × 6:
  1. "Robot despierta en un laboratorio abandonado" (movimiento: sit, duración: 4s, cámara: zoom_in, emoción: surprised)
  2. "Robot camina por un pasillo oscuro" (walk, 3s, pan_right, neutral)
  3. "Robot encuentra una puerta cerrada" (static, 4s, static, neutral)
  4. "Robot abre la puerta y ve la ciudad" (gesture, 5s, zoom_out, surprised)
  5. "Robot baja las escaleras hacia la ciudad" (walk, 3s, dolly, neutral)
  6. "Robot mira el atardecer desde un edificio alto" (static, 6s, pan_left, happy)
- Verificar GET /api/v1/storyboard/{id} retorna 6 frames ordenados

**Paso 4 — Verificar UI muestra los frames**
- Playwright: abrir el storyboard creado
- Verificar que se ven los 6 frames en el canvas (grid 3×2)
- Screenshot: `02_6_frames.png`

**Paso 5 — Editar un frame**
- PUT /api/v1/storyboard/{id}/frames/{frame3_id} cambiar duración a 6s, cámara a zoom_in
- Verificar GET retorna datos actualizados

**Paso 6 — Reordenar frames**
- PUT /api/v1/storyboard/{id}/frames/reorder → mover frame 6 a posición 1
- Verificar nuevo orden

**Paso 7 — Export JSON**
- POST /api/v1/storyboard/{id}/export
- Guardar resultado como `robot_storyboard_export.json` en la carpeta de resultados
- Verificar que contiene los 6 frames con todos los campos

**Paso 8 — Preview Animatic en UI**
- Playwright: click botón "▶️ Preview"
- Verificar que modal aparece
- Screenshot: `03_animatic_preview.png`

**Paso 9 — AI Generate (si Ollama disponible)**
- POST /api/v1/storyboard/generate con prompt="Una historia de 4 frames sobre un gato que aprende a programar"
- Si Ollama no responde, verificar que el endpoint retorna error descriptivo (no crash)

**Resultado**: Storyboard "Robot Adventure" guardado con 6 frames, export JSON funcional.

---

## NODO 3: 🧪 Laboratorio — Mini-Proyecto "Generar Video del Robot"

### Flujo completo:

**Paso 1 — Crear proyecto desde storyboard**
- POST /api/v1/lab/projects con storyboard_id del Robot Adventure
- Verificar: retorna proyecto con 6 clips (uno por frame), todos en status "idle"

**Paso 2 — Abrir nodo Laboratorio desde Hub**
- Screenshot: `01_lab_abierto.png`
- Verificar: pantallas flotantes, plataforma central, config panel

**Paso 3 — Verificar pantallas muestran keyframes**
- GET /api/v1/lab/projects/{id} → verificar 6 clips
- Screenshot: `02_pantallas_keyframes.png`

**Paso 4 — Configurar proyecto**
- PUT /api/v1/lab/projects/{id}/config con {"provider": "fal", "quality": "draft", "fps": 24, "resolution": "720p"}
- Verificar config guardada

**Paso 5 — Generar 1 clip individual**
- POST /api/v1/lab/projects/{id}/clips/0/generate
- Esperar que complete (poll cada 2s)
- Verificar: clip 0 status cambia a "completed" (o "error" con mensaje descriptivo)
- Screenshot: `03_clip_generado.png`

**Paso 6 — Generar todos**
- POST /api/v1/lab/projects/{id}/generate
- Poll GET /api/v1/lab/projects/{id} cada 3s
- Verificar: clips van cambiando de idle → generating → completed
- Screenshot: `04_generacion_progreso.png`

**Paso 7 — Pause/Resume**
- POST /api/v1/lab/projects/{id}/pause → verificar status "paused"
- POST /api/v1/lab/projects/{id}/resume → verificar status "generating"

**Paso 8 — Estado final del proyecto**
- GET /api/v1/lab/projects/{id}
- Guardar respuesta como `lab_project_final.json`
- Screenshot: `05_lab_final.png`

**Resultado**: Proyecto de Lab creado desde storyboard, generación probada.

---

## NODO 4: 🔭 Observatory — Mini-Proyecto "Auditoría del Sistema YeyoOS"

### Flujo completo:

**Paso 1 — Abrir Observatory desde Hub**
- Screenshot: `01_observatory_abierto.png`
- Verificar: 8 edificios visibles con sus emojis y nombres

**Paso 2 — Listar agentes via API**
- GET /api/v1/observatory/agents → debe retornar 8 agentes con emoji, building, description, quick_tasks

**Paso 3 — Asignar tarea al Scientist**
- POST /api/v1/observatory/task con agent_name="scientist", description="Analiza la arquitectura del módulo de memoria de YeyoOS"
- Esperar resultado (poll GET /api/v1/observatory/tasks/{id} cada 3s, max 30s)
- Verificar: status "completed", result_output no vacío
- Guardar resultado como `scientist_result.txt`
- Screenshot: `02_scientist_tarea.png`

**Paso 4 — Asignar tarea al Writer**
- POST /api/v1/observatory/task con agent_name="writer", description="Escribe un README corto para el módulo de video de YeyoOS"
- Esperar resultado
- Guardar como `writer_result.txt`
- Screenshot: `03_writer_tarea.png`

**Paso 5 — Asignar tarea al Guard**
- POST /api/v1/observatory/task con agent_name="guard", description="Verifica la seguridad de la configuración CORS del backend"
- Esperar resultado
- Guardar como `guard_result.txt`
- Screenshot: `04_guard_tarea.png`

**Paso 6 — Asignar tarea al Tester**
- POST /api/v1/observatory/task con agent_name="tester", description="Verifica que el endpoint /api/v1/memory/stats responde correctamente"
- Esperar resultado
- Screenshot: `05_tester_tarea.png`

**Paso 7 — CREW Mission**
- POST /api/v1/observatory/crew con:
  - title="Auditoría de seguridad YeyoOS"
  - description="Analiza la seguridad del sistema completo"
  - agents=["miner", "scientist", "guard", "sage"]
- Poll GET /api/v1/observatory/crew/{id} cada 5s
- Verificar: agentes se ejecutan en secuencia, status avanza
- Guardar resultado como `crew_audit_result.json`
- Screenshot: `06_crew_mission.png`

**Paso 8 — Historial de tareas**
- GET /api/v1/observatory/tasks → debe retornar al menos 4 tareas completadas
- Screenshot: `07_historial.png`

**Resultado**: 4 tareas individuales + 1 misión CREW completadas, resultados guardados.

---

## NODO 5: 🏗️ Workshop — Mini-Proyecto "Función de Ordenamiento Verificada"

### Flujo completo:

**Paso 1 — Abrir Workshop desde Hub**
- Screenshot: `01_workshop_abierto.png`
- Verificar: formulario de creación de misión visible

**Paso 2 — Listar gates**
- GET /api/v1/workshop/gates → debe retornar 17 gates (0-16)

**Paso 3 — Crear misión**
- POST /api/v1/workshop/missions con:
  - title="Función sort segura"
  - description="Función que ordena una lista de enteros manejando edge cases"
  - spec: {
      inputs: [{"name": "arr", "type": "list[int]"}],
      outputs: [{"name": "sorted_arr", "type": "list[int]"}],
      edge_cases: ["lista vacía", "un solo elemento", "duplicados", "ya ordenada", "orden inverso"],
      error_handling: ["TypeError si no es lista", "ValueError si contiene no-enteros"],
      constraints: ["O(n log n) promedio", "no modificar lista original"],
      acceptance_criteria: ["Retorna lista ordenada", "Maneja todos los edge cases", "No muta input"]
    }
- Verificar: retorna mission ID con status "pending"

**Paso 4 — Ejecutar pipeline**
- POST /api/v1/workshop/missions/{id}/execute
- Poll GET /api/v1/workshop/missions/{id} cada 3s
- Ir registrando el status de cada gate conforme avanza
- Screenshot en cada cambio de gate: `02_gate_0_spec.png`, `03_gate_1_arch.png`, `04_gate_2_code.png`, etc.

**Paso 5 — Verificar gates clave**
- Gate 0 (Spec-First): debe pasar (spec está completa)
- Gate 3 (AST Parse): debe pasar (código válido)
- Gate 15 (Human Checkpoint): debe pausar en "waiting_approval"

**Paso 6 — Aprobar gate humano**
- POST /api/v1/workshop/missions/{id}/gates/15/approve
- Verificar que pipeline continúa

**Paso 7 — Sandbox state**
- GET /api/v1/workshop/missions/{id}/sandbox
- Guardar código generado como `sort_function.py`
- Guardar estado de gates como `gates_result.json`

**Paso 8 — Pause/Cancel**
- Crear segunda misión simple para probar pause
- POST /missions/{id2}/execute → POST /missions/{id2}/pause → verificar paused
- POST /missions/{id2}/cancel → verificar cancelled

**Paso 9 — Workshop UI**
- Playwright: verificar panel de gates, editor de código, terminal
- Screenshot: `08_workshop_completo.png`

**Resultado**: Misión completada con gates verificados, código guardado.

---

## NODO 6: ⚔️ Arena — Mini-Proyecto "Batalla de 15 Rondas"

### Flujo completo:

**Paso 1 — Abrir Observatory → Tab Arena**
- Playwright: abrir Observatory, click tab "⚔️ Arena"
- Screenshot: `01_arena_vista.png`
- Verificar: paneles YeyoHack (rojo) y Guardian (azul), controles, config

**Paso 2 — Iniciar batalla**
- POST /api/v1/arena/start con max_rounds=15
- Guardar session_id

**Paso 3 — Monitorear progreso**
- Poll GET /api/v1/arena/sessions/{id} cada 2s
- Verificar: current_round avanza, red_score y blue_score se actualizan
- Screenshot: `02_batalla_en_curso.png`

**Paso 4 — Esperar a que termine**
- Esperar hasta status="completed" (max 60s)
- Verificar: current_round == 15 (o menos si hubo auto-pausa)

**Paso 5 — Obtener scripts**
- GET /api/v1/arena/sessions/{id}/scripts
- Verificar: hay scripts de ataque y defensa reales (no vacíos)
- Guardar como `battle_scripts.json`

**Paso 6 — Verificar resultado final**
- GET /api/v1/arena/sessions/{id}
- Verificar: red_score + blue_score > 0
- Guardar como `battle_final.json`
- Screenshot: `03_batalla_final.png`

**Paso 7 — Pause/Resume**
- POST /api/v1/arena/start con max_rounds=20
- Esperar 5 rondas → POST pause → verificar paused
- POST resume → verificar running de nuevo
- POST stop → verificar completed
- Screenshot: `04_pause_resume.png`

**Paso 8 — Listar sesiones**
- GET /api/v1/arena/sessions → debe retornar al menos 2 sesiones

**Resultado**: Batalla completa, scripts de ataque/defensa guardados.

---

## NODO 7: 🔄 Integración — Mini-Proyecto "Del Observatory al Workshop"

### Flujo completo:

**Paso 1 — Crear misión desde Observatory**
- POST /api/v1/observatory/task con agent_name="scientist", description="Analiza el rendimiento del endpoint /api/v1/memory/search"
- Esperar resultado
- POST /api/v1/observatory/tasks/{task_id}/to-mission → crear misión desde el resultado
- Verificar: misión creada con origin="observatory"

**Paso 2 — Listar misiones**
- GET /api/v1/missions → debe incluir la misión del paso 1
- Verificar campos: finding, analysis, created_by="scientist"
- Screenshot: `01_mision_creada.png`

**Paso 3 — Aprobar misión**
- PUT /api/v1/missions/{id}/approve con spec básica
- Verificar: status cambia a "spec_review"

**Paso 4 — Enviar al Workshop**
- POST /api/v1/missions/{id}/send-to-workshop
- Verificar: misión ahora tiene workshop pipeline asociado

**Paso 5 — Verificar progreso combinado**
- GET /api/v1/missions/{id}/progress
- Guardar como `integration_progress.json`

**Paso 6 — Crear misión manual**
- POST /api/v1/missions con origin="user", title="Optimizar queries de memoria"
- Verificar CRUD completo

**Paso 7 — UI Integration**
- Playwright: Observatory → verificar botón "📋 Misiones" visible
- Playwright: Workshop → verificar sección "🔭 Misiones del Observatory" visible
- Screenshot: `02_observatory_misiones.png`, `03_workshop_misiones.png`

**Resultado**: Flujo completo Observatory → Mission Board → Workshop probado.

---

## REPORTE FINAL

Después de completar TODOS los nodos, generar:

**`tests/qa-results/FINAL_REPORT.md`** con:
```markdown
# QA Report — YeyoOS Mega Plan

## Resumen
- Total nodos testeados: 7
- Funcionalidades probadas: [número]
- Errores encontrados: [número]
- Errores arreglados: [número]
- Errores pendientes: [número]

## Por Nodo
| Nodo | Funcionalidades | Pass | Fail | Fixes |
|------|----------------|------|------|-------|
| Video Editor | 8 | ? | ? | ? |
| Storyboard | 9 | ? | ? | ? |
| Laboratorio | 8 | ? | ? | ? |
| Observatory | 8 | ? | ? | ? |
| Workshop | 9 | ? | ? | ? |
| Arena | 8 | ? | ? | ? |
| Integración | 7 | ? | ? | ? |

## Errores Encontrados y Soluciones
[Lista detallada de cada error, causa raíz, y fix aplicado]

## Mini-Proyectos Guardados
- robot_storyboard_export.json
- lab_project_final.json
- scientist_result.txt / writer_result.txt / guard_result.txt
- crew_audit_result.json
- sort_function.py / gates_result.json
- battle_scripts.json / battle_final.json
- integration_progress.json

## Screenshots
[Lista de todos los screenshots con descripción]
```

Hacer commit final con todos los resultados y push a main.
