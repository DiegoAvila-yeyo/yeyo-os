# Manual Test Guide — YeyoOS Frontend Features

Comprehensive manual test guide for all new frontend features. For each test:
- ✅ What should happen (expected result)
- ❌ What indicates a bug (failure indicator)
- 🔧 How to debug (debugging steps)

---

## Workflow Orchestrator Tests

### WF-01: Create New Workflow
**Steps:** Open Workflow node → Click "📋 Mis Workflows" tab → Click "➕ New Workflow"

✅ New workflow appears in list with default name, designer tab opens

❌ Nothing happens, error in console, or tab doesn't switch

🔧 Check browser console for API errors, verify backend is running at :8000, check `/api/v1/workflows` endpoint

### WF-02: Add Nodes to Designer
**Steps:** Open designer tab → Drag a "💬 Chat AI" node from palette → Drag a "🖼️ Image Generation" node

✅ Nodes appear on canvas at drop position, showing label and colored border

❌ Nodes don't appear, snap to wrong position, or palette is empty

🔧 Check `fetchNodeTypes()` response in Network tab, verify `/api/v1/workflows/node-types` returns data

### WF-03: Connect Nodes
**Steps:** Click output dot on Chat node → Click input dot on Image node

✅ SVG bezier edge appears connecting the two nodes

❌ No edge appears, edge goes to wrong position, or clicking doesn't register

🔧 Check console for errors in FlowEdge render, verify edge state in React DevTools

### WF-04: Save Workflow
**Steps:** Add nodes and edges → Click "💾 Save"

✅ Workflow saved, success feedback shown, appears in list tab

❌ Error toast, workflow not in list, or data lost on tab switch

🔧 Check Network tab for POST/PUT `/api/v1/workflows`, verify request body has nodes/edges

### WF-05: Execute Workflow
**Steps:** Open a saved workflow → Click "▶️ Run"

✅ Execution starts, progress bar appears in Executions tab, nodes light up as they execute

❌ Nothing happens, error message, or progress stuck at 0%

🔧 Check POST `/api/v1/workflows/{id}/execute` response, verify WebSocket connects to `/ws/{exec_id}`

### WF-06: View Execution Progress (Live)
**Steps:** Start a workflow execution → Switch to "📊 Ejecuciones" tab

✅ Live execution shows progress bar, node-by-node results appear in real-time

❌ No live updates, WebSocket disconnects, or results don't appear

🔧 Check WebSocket connection in Network tab, verify `ws://localhost:8000/api/v1/workflows/ws/{exec_id}`

### WF-07: Delete Workflow
**Steps:** In list tab → Click "🗑️ Delete" on a workflow → Confirm

✅ Workflow removed from list, confirmation dialog shown first

❌ Workflow still appears, no confirmation, or error

🔧 Check DELETE `/api/v1/workflows/{id}` response

### WF-08: Node Configuration
**Steps:** Click on a node in designer → Check right panel

✅ Config panel shows editable fields for that node type (prompt, model, timeout, etc.)

❌ Panel empty, wrong fields shown, or changes not saved

🔧 Check `selectedNodeId` in store, verify config panel renders based on `node_type`

---

## Observatory Tests

### OBS-01: Town View Renders
**Steps:** Open Observatory node → "🏭 Town" tab should be active

✅ Canvas shows tile-based town with 7 colored buildings, 8 animated characters

❌ Black canvas, no characters, or buildings missing

🔧 Check browser console for sprite loading errors, verify `/sprites/characters/` paths exist

### OBS-02: Characters Animate
**Steps:** Watch characters in town view

✅ Characters play idle animation (4 frames cycling), smooth pixel art at 3x scale

❌ Characters frozen, flickering, or blurry (`imageSmoothingEnabled` should be false)

🔧 Check GameEngine init for `imageSmoothingEnabled=false`, verify `SpriteSheet.load()` succeeds

### OBS-03: Character Click
**Steps:** Click on a character sprite

✅ CharacterInfo panel slides in from right showing name, status, building, recent events

❌ Click doesn't register, wrong character selected, or panel empty

🔧 Check `getBounds()` in `Character.ts`, verify click coordinate conversion in GameEngine

### OBS-04: Building Click
**Steps:** Click on a building (e.g., "🏭 Workflow Factory")

✅ Popup shows building name, icon, description, and recent activities

❌ Click doesn't register, popup appears in wrong position, or no activity data

🔧 Check `Building.containsPoint()` method, verify building is highlighted on hover

### OBS-05: Live Events via WebSocket
**Steps:** Start a workflow execution while Observatory is open

✅ Characters move to relevant buildings, speech bubbles appear, particles spawn

❌ No character movement, WebSocket doesn't connect

🔧 Check `ws://localhost:8000/api/v1/observatory/live` connection, verify events are being tracked

### OBS-06: Day/Night Cycle
**Steps:** Set system clock to 23:30 (or wait until night)

✅ Canvas has dark overlay, buildings and characters glow subtly

❌ No visual change, overlay too dark/light

🔧 Check GameEngine day/night logic, verify local time detection in `drawDayNightOverlay()`

### OBS-07: Metrics Tab
**Steps:** Click "📊 Metrics" tab

✅ Shows dashboard with active workflows, agent counts, event rates

❌ All zeros, loading spinner never stops, or tab is empty

🔧 Check GET `/api/v1/observatory/metrics` response

### OBS-08: Particles
**Steps:** Trigger a workflow completion event

✅ Gold particles spawn at the character's position and fade out

❌ No particles, particles stuck, or wrong position

🔧 Check `spawnParticles()` in GameEngine, verify particle update/draw logic

---

## Arena Tests

### ARENA-01: Start Battle
**Steps:** Open Observatory → "⚔️ Arena" tab → Click "⚔️ Start Battle"

✅ Battle starts, YeyoHack and Guardian sprites appear, status changes to "running"

❌ Error on start, sprites don't load, or status stays "idle"

🔧 Check POST `/api/v1/arena/start` response, verify sprite paths

### ARENA-02: Battle Animations
**Steps:** Watch a running battle

✅ YeyoHack attacks (slash animation), Guardian defends (shield animation), spark effects on hit

❌ No animations, sprites frozen, or effects missing

🔧 Check sprite sheet loading for `Attack.png` and `effects/`, verify animation frame cycling

### ARENA-03: Scoreboard Updates
**Steps:** Watch scoreboard during battle

✅ Red/Blue scores increment as rounds complete, round counter advances

❌ Scores stuck at 0, round counter doesn't move

🔧 Check WebSocket `/api/v1/arena/live` for `round_result` events

### ARENA-04: Battle Log
**Steps:** Check battle log below arena canvas

✅ Each round appears as a color-coded entry (red=attack success, cyan=defense success)

❌ Log empty, wrong colors, or not auto-scrolling

🔧 Verify `rounds` array state updates on WebSocket events

### ARENA-05: Stop Battle
**Steps:** Click "⏹️ Stop" during battle

✅ Battle stops, final scores shown, status returns to "idle"

❌ Battle continues, error on stop

🔧 Check POST `/api/v1/arena/stop` response

### ARENA-06: Battle Metrics
**Steps:** After battle ends, check metrics

✅ GET `/api/v1/arena/metrics` returns total rounds, win rates, most common attack type

❌ All zeros, or endpoint returns 500

🔧 Verify `ArenaMetricsCollector` tracks sessions

---

## Sanity Checks (Existing Features)

### SANITY-01: Chat Node Still Works
**Steps:** Open Chat node → Send a message

✅ Response from Ollama model appears

❌ Error, no response, or chat broken

🔧 Check Ollama is running, verify `/api/v1/chat` endpoint

### SANITY-02: Image Generation Still Works
**Steps:** Open Image node → Enter prompt → Generate

✅ Image generated via fal.ai

❌ Error or timeout

🔧 Check `FAL_KEY` in `.env`, verify `/api/v1/media` endpoints

### SANITY-03: YeyoNet Still Works
**Steps:** Check YeyoNet node connectivity

✅ Node identity shown, satellite connection works

❌ Connection errors

🔧 Check `/api/v1/yeyonet` endpoints

### SANITY-04: Memory Node Still Works
**Steps:** Store a memory → Search for it

✅ Memory stored and retrievable

❌ Store fails or search returns nothing

🔧 Check PostgreSQL connection, verify `/api/v1/memory` endpoints

---

## Cross-Feature Tests

### CROSS-01: Workflow → Observatory Integration
**Steps:** Execute a workflow while Observatory town is open

✅ Robot character moves to Workflow Factory, speech bubble shows activity

❌ No character reaction to workflow events

🔧 Verify `ObservatoryService` is registered as listener on `WorkflowEngine` events

### CROSS-02: Arena → Observatory Integration
**Steps:** Start arena battle while Observatory town is open

✅ YeyoHack and Guardian characters animate in arena tab

❌ Characters don't appear or arena events not flowing

🔧 Check WebSocket connections for both observatory and arena
