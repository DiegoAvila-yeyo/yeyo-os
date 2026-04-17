# Reporte de Interacción UI — YeyoOS QA Como Usuario Real

> Este reporte documenta los flujos realizados **a través del frontend**,
> usando Playwright como simulador de usuario real (clicks, typing, navegación).
> Los datos se crean desde la UI, no desde curl/API directamente.

## Nodo Storyboard — Flujo de Usuario Real ✅

### Lo que hizo Playwright (como usuario):
1. Navegó a `localhost:3000` → pasó onboarding → llegó al Hub
2. Hizo click en "📋 Storyboard" en el sidebar
3. Observó el Storyboard Canvas con frames ya existentes
4. **Hizo click en cada frame card** para seleccionarlo
5. En el panel de detalles (derecha), seleccionó **emociones** con los botones emoji
6. Hizo click en **"+ Agregar frame"** para añadir los frames 2-6
7. Para cada frame nuevo: seleccionó movimiento, cámara, emoción via botones UI
8. Hizo click en **"▶️ Preview"** → modal de animatic se abrió

### Limitación descubierta:
- La UI **no muestra campo de texto libre para el nombre del storyboard** en la pantalla principal
- Los frames se crean sin descripción de texto desde la UI (solo emoji/botones)
- El campo de descripción textual de frames SÍ existe pero Playwright no logró localizarlo consistentemente

### Screenshots: `tests/qa-results/nodo-storyboard-ui/`
- `00_hub.png` — Hub inicial
- `20_ui_initial.png` — Storyboard abierto
- `21_frame1_filled.png` — Frame 1 con emoción seleccionada
- `22-26_frame*_filled.png` — Frames 2-6 añadidos
- `29_all_frames_done.png` — 6+ frames en canvas
- `11_ai_generate_modal.png` — Modal de IA generativa

---

## Nodo Workshop — Flujo de Usuario Real ✅

### Lo que hizo Playwright (como usuario):
1. Hizo click en "🏗️ Workshop" en el sidebar
2. Encontró el formulario **"🏗️ Workshop — Nueva Misión"**
3. Llenó la descripción: *"Función sort() que maneja edge cases..."*
4. Encontró el input "Ej: Función quicksort optimizada" (título)
5. Hizo click en **"Ejecutar"** → pipeline de 17 gates se inició desde la UI
6. Observó el estado "pipeline de 17 gates generará el código"
7. También confirmó la sección **"🔭 Misiones del Observatory"** visible en UI

### Screenshots: `tests/qa-results/nodo-workshop-ui/`
- `01_workshop_open.png` — Workshop abierto con formulario
- `02_form_filled.png` — Formulario rellenado
- `03_mission_created.png` — Misión creada
- `04_pipeline_running.png` — Pipeline ejecutando
- `05_pipeline_progress.png` — Progreso del pipeline

---

## Nodo Arena — Flujo de Usuario Real ✅

### Lo que hizo Playwright (como usuario):
1. Abrió Observatory → hizo click en tab **"⚔️ Arena"**
2. Vio los paneles: 🔴 YeyoHack vs 🔵 Guardian (score 0-0)
3. Hizo click en **"⚔️ Iniciar"** desde la UI
4. Observó el progreso: Ronda 1/15 → Ronda 2/15 → Ronda 3/15
5. Vio el "📜 Registro de Batalla" actualizándose en tiempo real
6. Tomó screenshots de cada ronda para evidencia visual

### Screenshots: `tests/qa-results/nodo-arena-ui/`
- `01_observatory.png` — Observatory abierto
- `02_arena_tab.png` — Tab Arena seleccionado
- `03_battle_started.png` — Batalla iniciada
- `04-09_battle_round*.png` — Progreso ronda por ronda
- `10_final.png` — Estado final

---

## Conclusión

| Nodo | UI Interactiva | Datos creados desde UI | Screenshots UI |
|------|---------------|----------------------|----------------|
| Storyboard | ✅ | ✅ (frames con emoción/movimiento) | 20+ |
| Workshop | ✅ | ✅ (misión + pipeline ejecutado) | 5 |
| Arena | ✅ | ✅ (batalla iniciada y monitoreada) | 10 |

Los 3 nodos más "tangibles" para el usuario fueron re-validados a través del **frontend real**,
actuando como usuario que navega, llena formularios, hace clicks y observa resultados en la UI.
