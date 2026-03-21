## ═══════════════════════════════════════
## MICRO-FASE 6.3 — Kill Switch
## Tipo: VSCODE+CLI | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.3-1 [VSCODE+CLI] — Kill Switch: pausa de emergencia de toda la IA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.3 de Capa 6 (Sistema Inmune): implementar el Kill Switch, el botón de emergencia que PAUSA toda la IA del sistema.

CONTEXTO:
- Micro-fases 6.0-6.2 completadas: Guardian + Anomaly + Auto-Response
- Kill Switch: Ctrl+Alt+K — PAUSA toda la IA (no mata, PAUSA)
- Debe funcionar incluso si: UI está congelada, Python backend crasheó
- Solo necesita que Guardian Daemon esté corriendo
- Captura de teclas a nivel kernel (evdev en Linux)
- También accesible via: guardian-cli kill-switch
- Indicador visual: borde de pantalla se pone rojo
- Resume: mismo atajo o via Guardian API
- Estado persiste entre reinicios

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo rust/guardian/src/kill_switch.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/kill_switch.rs
   Contenido:

   //! YeyoOS Guardian — Kill Switch
   //! Micro-fase 6.3 — Capa 6: Sistema Inmune
   //!
   //! PAUSA DE EMERGENCIA de toda la IA.
   //! Ctrl+Alt+K — capturado a nivel kernel (evdev).
   //! PAUSA, no MATA: todos los procesos IA se pausan y pueden resumirse.
   //!
   //! CRÍTICO: Debe funcionar incluso si:
   //! - La UI está congelada
   //! - El backend Python crasheó
   //! - Solo Guardian Daemon está corriendo

   use chrono::{DateTime, Utc};
   use serde::{Deserialize, Serialize};
   use std::path::PathBuf;
   use std::sync::Arc;
   use tokio::sync::RwLock;
   use tracing::{info, warn, error};

   // ═══════════════════════════════════
   // TIPOS DE DATOS
   // ═══════════════════════════════════

   /// Estado del Kill Switch.
   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub enum KillSwitchState {
       /// IA corriendo normalmente
       Active,
       /// IA pausada por Kill Switch
       Paused,
   }

   /// Información de un proceso IA pausado.
   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct PausedProcess {
       pub name: String,
       pub pid: Option<u32>,
       pub container_id: Option<String>,
       pub paused_at: DateTime<Utc>,
   }

   /// Evento de Kill Switch en el log.
   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct KillSwitchEvent {
       pub timestamp: DateTime<Utc>,
       pub action: String,
       pub triggered_by: String,
       pub processes_affected: usize,
   }

   // ═══════════════════════════════════
   // TARGETS — Procesos IA a pausar
   // ═══════════════════════════════════

   /// Todos los procesos IA que el Kill Switch debe pausar.
   const AI_TARGETS: &[&str] = &[
       "ollama",
       "yeyo-backend",
       "stable-diffusion",
       "whisper",
       "tts-server",
   ];

   /// Prefijos de containers IA a pausar.
   const AI_CONTAINER_PREFIXES: &[&str] = &[
       "yeyo-ai-",
       "yeyo-node-",
       "yeyo-sandbox-",
   ];

   // ═══════════════════════════════════
   // KILL SWITCH
   // ═══════════════════════════════════

   pub struct KillSwitch {
       state: Arc<RwLock<KillSwitchState>>,
       paused_processes: Arc<RwLock<Vec<PausedProcess>>>,
       events: Arc<RwLock<Vec<KillSwitchEvent>>>,
       state_file: PathBuf,
   }

   impl KillSwitch {
       pub fn new(state_dir: PathBuf) -> Self {
           let state_file = state_dir.join("kill_switch_state.json");

           // Restaurar estado previo si existe
           let initial_state = Self::load_state(&state_file)
               .unwrap_or(KillSwitchState::Active);

           Self {
               state: Arc::new(RwLock::new(initial_state)),
               paused_processes: Arc::new(RwLock::new(Vec::new())),
               events: Arc::new(RwLock::new(Vec::new())),
               state_file,
           }
       }

       /// Carga el estado persistido del Kill Switch.
       fn load_state(path: &PathBuf) -> Option<KillSwitchState> {
           let content = std::fs::read_to_string(path).ok()?;
           serde_json::from_str(&content).ok()
       }

       /// Persiste el estado actual del Kill Switch.
       async fn save_state(&self) {
           let state = self.state.read().await;
           if let Ok(json) = serde_json::to_string_pretty(&*state) {
               if let Some(parent) = self.state_file.parent() {
                   let _ = std::fs::create_dir_all(parent);
               }
               if let Err(e) = std::fs::write(&self.state_file, json) {
                   error!("No se pudo persistir estado del Kill Switch: {}", e);
               }
           }
       }

       /// Toggle: si está Active → Paused, si está Paused → Active.
       pub async fn toggle(&self, triggered_by: &str) -> KillSwitchState {
           let current = self.get_state().await;
           match current {
               KillSwitchState::Active => self.pause(triggered_by).await,
               KillSwitchState::Paused => self.resume(triggered_by).await,
           }
       }

       // ═══════════════════════════════════
       // PAUSAR — Ctrl+Alt+K o API
       // ═══════════════════════════════════

       /// PAUSA toda la IA del sistema.
       pub async fn pause(&self, triggered_by: &str) -> KillSwitchState {
           let mut state = self.state.write().await;

           if *state == KillSwitchState::Paused {
               warn!("[KILL SWITCH] Ya está en pausa");
               return KillSwitchState::Paused;
           }

           error!("═══════════════════════════════════════");
           error!("  🔴 KILL SWITCH ACTIVADO");
           error!("  Pausando TODA la IA del sistema...");
           error!("  Trigger: {}", triggered_by);
           error!("═══════════════════════════════════════");

           let mut paused = Vec::new();

           // 1. Pausar procesos IA por nombre
           for target in AI_TARGETS {
               match Self::pause_process_by_name(target).await {
                   Ok(pid) => {
                       info!("[KILL SWITCH] Pausado: {} (PID: {:?})", target, pid);
                       paused.push(PausedProcess {
                           name: target.to_string(),
                           pid,
                           container_id: None,
                           paused_at: Utc::now(),
                       });
                   }
                   Err(e) => {
                       warn!("[KILL SWITCH] No se pudo pausar {}: {}", target, e);
                   }
               }
           }

           // 2. Pausar containers IA
           for prefix in AI_CONTAINER_PREFIXES {
               match Self::pause_containers_by_prefix(prefix).await {
                   Ok(containers) => {
                       for cid in containers {
                           info!("[KILL SWITCH] Container pausado: {}", cid);
                           paused.push(PausedProcess {
                               name: format!("container:{}", cid),
                               pid: None,
                               container_id: Some(cid),
                               paused_at: Utc::now(),
                           });
                       }
                   }
                   Err(e) => {
                       warn!("[KILL SWITCH] Error pausando containers {}: {}", prefix, e);
                   }
               }
           }

           let processes_affected = paused.len();

           *state = KillSwitchState::Paused;
           drop(state); // Liberar lock antes de save

           // Persistir estado
           self.save_state().await;

           // Guardar procesos pausados
           let mut pp = self.paused_processes.write().await;
           *pp = paused;

           // Registrar evento
           let event = KillSwitchEvent {
               timestamp: Utc::now(),
               action: "PAUSE".to_string(),
               triggered_by: triggered_by.to_string(),
               processes_affected,
           };
           self.events.write().await.push(event);

           error!(
               "[KILL SWITCH] {} procesos IA pausados. Resume: Ctrl+Alt+K o API.",
               processes_affected
           );

           KillSwitchState::Paused
       }

       // ═══════════════════════════════════
       // RESUMIR
       // ═══════════════════════════════════

       /// Reanuda toda la IA del sistema.
       pub async fn resume(&self, triggered_by: &str) -> KillSwitchState {
           let mut state = self.state.write().await;

           if *state == KillSwitchState::Active {
               info!("[KILL SWITCH] Ya está activo");
               return KillSwitchState::Active;
           }

           info!("═══════════════════════════════════════");
           info!("  🟢 KILL SWITCH DESACTIVADO");
           info!("  Reanudando IA del sistema...");
           info!("  Trigger: {}", triggered_by);
           info!("═══════════════════════════════════════");

           let paused = self.paused_processes.read().await.clone();
           let mut resumed_count = 0;

           for process in &paused {
               // Reanudar proceso por PID
               if let Some(pid) = process.pid {
                   if Self::resume_process(pid).await.is_ok() {
                       info!("[KILL SWITCH] Reanudado: {} (PID: {})", process.name, pid);
                       resumed_count += 1;
                   }
               }

               // Reanudar container
               if let Some(ref cid) = process.container_id {
                   if Self::resume_container(cid).await.is_ok() {
                       info!("[KILL SWITCH] Container reanudado: {}", cid);
                       resumed_count += 1;
                   }
               }
           }

           *state = KillSwitchState::Active;
           drop(state);

           self.save_state().await;

           // Limpiar procesos pausados
           self.paused_processes.write().await.clear();

           // Registrar evento
           let event = KillSwitchEvent {
               timestamp: Utc::now(),
               action: "RESUME".to_string(),
               triggered_by: triggered_by.to_string(),
               processes_affected: resumed_count,
           };
           self.events.write().await.push(event);

           info!("[KILL SWITCH] {} procesos reanudados.", resumed_count);

           KillSwitchState::Active
       }

       // ═══════════════════════════════════
       // HELPERS — Interacción con sistema
       // ═══════════════════════════════════

       /// Pausa un proceso por nombre (SIGSTOP).
       async fn pause_process_by_name(name: &str) -> Result<Option<u32>, String> {
           let output = tokio::process::Command::new("pgrep")
               .arg("-f")
               .arg(name)
               .output()
               .await
               .map_err(|e| format!("pgrep falló: {}", e))?;

           if !output.status.success() {
               return Err(format!("Proceso '{}' no encontrado", name));
           }

           let pids: Vec<u32> = String::from_utf8_lossy(&output.stdout)
               .lines()
               .filter_map(|l| l.trim().parse().ok())
               .collect();

           for pid in &pids {
               // SIGSTOP pausa el proceso (SIGCONT lo reanuda)
               let _ = tokio::process::Command::new("kill")
                   .args(["-STOP", &pid.to_string()])
                   .output()
                   .await;
           }

           Ok(pids.first().copied())
       }

       /// Pausa containers con un prefijo dado.
       async fn pause_containers_by_prefix(prefix: &str) -> Result<Vec<String>, String> {
           let output = tokio::process::Command::new("docker")
               .args(["ps", "-q", "--filter", &format!("name={}", prefix)])
               .output()
               .await
               .map_err(|e| format!("docker ps falló: {}", e))?;

           let container_ids: Vec<String> = String::from_utf8_lossy(&output.stdout)
               .lines()
               .filter(|l| !l.trim().is_empty())
               .map(|l| l.trim().to_string())
               .collect();

           for cid in &container_ids {
               let _ = tokio::process::Command::new("docker")
                   .args(["pause", cid])
                   .output()
                   .await;
           }

           Ok(container_ids)
       }

       /// Reanuda un proceso por PID (SIGCONT).
       async fn resume_process(pid: u32) -> Result<(), String> {
           tokio::process::Command::new("kill")
               .args(["-CONT", &pid.to_string()])
               .output()
               .await
               .map_err(|e| format!("kill -CONT falló: {}", e))?;
           Ok(())
       }

       /// Reanuda un container.
       async fn resume_container(container_id: &str) -> Result<(), String> {
           tokio::process::Command::new("docker")
               .args(["unpause", container_id])
               .output()
               .await
               .map_err(|e| format!("docker unpause falló: {}", e))?;
           Ok(())
       }

       // ═══════════════════════════════════
       // CONSULTAS
       // ═══════════════════════════════════

       /// Retorna el estado actual del Kill Switch.
       pub async fn get_state(&self) -> KillSwitchState {
           self.state.read().await.clone()
       }

       /// Retorna los procesos actualmente pausados.
       pub async fn get_paused_processes(&self) -> Vec<PausedProcess> {
           self.paused_processes.read().await.clone()
       }

       /// Retorna el historial de eventos del Kill Switch.
       pub async fn get_events(&self) -> Vec<KillSwitchEvent> {
           self.events.read().await.clone()
       }
   }

2. Crear archivo rust/guardian/src/evdev_listener.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/evdev_listener.rs
   Contenido:

   //! YeyoOS Guardian — Captura de teclado a nivel kernel
   //! Micro-fase 6.3 — Capa 6: Sistema Inmune
   //!
   //! Captura Ctrl+Alt+K a nivel evdev (Linux).
   //! Funciona incluso si la UI está muerta.
   //! Solo Guardian necesita estar corriendo.

   use std::sync::Arc;
   use tokio::sync::Notify;
   use tracing::{info, warn, error};

   /// Listener de teclado que captura Ctrl+Alt+K vía evdev.
   pub struct EvdevListener {
       /// Notificador para cuando se detecta el atajo
       trigger: Arc<Notify>,
   }

   impl EvdevListener {
       pub fn new() -> Self {
           Self {
               trigger: Arc::new(Notify::new()),
           }
       }

       /// Retorna un clone del notificador para escuchar triggers.
       pub fn get_trigger(&self) -> Arc<Notify> {
           self.trigger.clone()
       }

       /// Inicia el listener de evdev.
       /// En producción lee /dev/input/eventX.
       /// NOTA: Requiere permisos root o grupo input.
       pub async fn start(&self) {
           info!("[EVDEV] Iniciando listener de teclado para Kill Switch (Ctrl+Alt+K)");

           // En producción, esto leería /dev/input/eventX
           // Por ahora, listener placeholder que se integra en el build final
           #[cfg(target_os = "linux")]
           {
               self.start_linux_listener().await;
           }

           #[cfg(not(target_os = "linux"))]
           {
               warn!("[EVDEV] No es Linux — Kill Switch solo disponible via API/CLI");
               // En desarrollo (macOS/Windows), el Kill Switch se usa via API
               // Esperar indefinidamente para no terminar el task
               tokio::signal::ctrl_c().await.ok();
           }
       }

       #[cfg(target_os = "linux")]
       async fn start_linux_listener(&self) {
           use std::fs::File;
           use std::io::Read;
           use std::mem;

           // Estructura de evento de input de Linux
           #[repr(C)]
           struct InputEvent {
               tv_sec: i64,
               tv_usec: i64,
               type_: u16,
               code: u16,
               value: i32,
           }

           // Buscar dispositivo de teclado
           let kbd_path = Self::find_keyboard_device().unwrap_or_else(|| {
               warn!("[EVDEV] No se encontró teclado, usando /dev/input/event0");
               "/dev/input/event0".to_string()
           });

           info!("[EVDEV] Escuchando en: {}", kbd_path);

           let trigger = self.trigger.clone();

           // Ejecutar en thread separado (I/O bloqueante)
           tokio::task::spawn_blocking(move || {
               let mut file = match File::open(&kbd_path) {
                   Ok(f) => f,
                   Err(e) => {
                       error!("[EVDEV] No se pudo abrir {}: {}", kbd_path, e);
                       error!("[EVDEV] ¿Tiene permisos? Ejecute: sudo usermod -aG input $USER");
                       return;
                   }
               };

               let event_size = mem::size_of::<InputEvent>();
               let mut buf = vec![0u8; event_size];
               let mut ctrl_pressed = false;
               let mut alt_pressed = false;

               // KEY codes
               const EV_KEY: u16 = 1;
               const KEY_K: u16 = 37;
               const KEY_LEFTCTRL: u16 = 29;
               const KEY_RIGHTCTRL: u16 = 97;
               const KEY_LEFTALT: u16 = 56;
               const KEY_RIGHTALT: u16 = 100;

               loop {
                   if file.read_exact(&mut buf).is_err() {
                       break;
                   }

                   let event: InputEvent = unsafe {
                       std::ptr::read(buf.as_ptr() as *const InputEvent)
                   };

                   if event.type_ != EV_KEY {
                       continue;
                   }

                   let pressed = event.value == 1; // 1 = pressed, 0 = released

                   match event.code {
                       KEY_LEFTCTRL | KEY_RIGHTCTRL => ctrl_pressed = pressed,
                       KEY_LEFTALT | KEY_RIGHTALT => alt_pressed = pressed,
                       KEY_K if pressed && ctrl_pressed && alt_pressed => {
                           info!("[EVDEV] 🔴 Ctrl+Alt+K detectado — Kill Switch!");
                           trigger.notify_one();
                       }
                       _ => {}
                   }
               }
           });
       }

       #[cfg(target_os = "linux")]
       fn find_keyboard_device() -> Option<String> {
           let proc_devices = std::fs::read_to_string("/proc/bus/input/devices").ok()?;
           let mut current_handlers = String::new();
           let mut is_keyboard = false;

           for line in proc_devices.lines() {
               if line.starts_with("H: Handlers=") {
                   current_handlers = line.to_string();
               }
               if line.contains("EV=120013") || line.contains("keyboard") {
                   is_keyboard = true;
               }
               if line.is_empty() {
                   if is_keyboard {
                       for part in current_handlers.split_whitespace() {
                           if part.starts_with("event") {
                               return Some(format!("/dev/input/{}", part));
                           }
                       }
                   }
                   is_keyboard = false;
               }
           }

           None
       }
   }

   impl Default for EvdevListener {
       fn default() -> Self {
           Self::new()
       }
   }

3. Crear archivo rust/guardian/tests/kill_switch_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/kill_switch_test.rs
   Contenido:

   //! Tests para Kill Switch — Micro-fase 6.3

   use std::path::PathBuf;
   use yeyo_guardian::kill_switch::{KillSwitch, KillSwitchState};

   fn temp_state_dir() -> PathBuf {
       let dir = std::env::temp_dir().join(format!("yeyo-ks-test-{}", uuid::Uuid::new_v4()));
       std::fs::create_dir_all(&dir).unwrap();
       dir
   }

   #[tokio::test]
   async fn test_initial_state_is_active() {
       let ks = KillSwitch::new(temp_state_dir());
       assert_eq!(ks.get_state().await, KillSwitchState::Active);
   }

   #[tokio::test]
   async fn test_pause_changes_state() {
       let ks = KillSwitch::new(temp_state_dir());
       let state = ks.pause("test").await;
       assert_eq!(state, KillSwitchState::Paused);
       assert_eq!(ks.get_state().await, KillSwitchState::Paused);
   }

   #[tokio::test]
   async fn test_resume_changes_state() {
       let ks = KillSwitch::new(temp_state_dir());
       ks.pause("test").await;
       let state = ks.resume("test").await;
       assert_eq!(state, KillSwitchState::Active);
   }

   #[tokio::test]
   async fn test_toggle_works() {
       let ks = KillSwitch::new(temp_state_dir());

       let state = ks.toggle("test").await;
       assert_eq!(state, KillSwitchState::Paused);

       let state = ks.toggle("test").await;
       assert_eq!(state, KillSwitchState::Active);
   }

   #[tokio::test]
   async fn test_events_recorded() {
       let ks = KillSwitch::new(temp_state_dir());
       ks.pause("keyboard-shortcut").await;
       ks.resume("keyboard-shortcut").await;

       let events = ks.get_events().await;
       assert_eq!(events.len(), 2);
       assert_eq!(events[0].action, "PAUSE");
       assert_eq!(events[1].action, "RESUME");
       assert_eq!(events[0].triggered_by, "keyboard-shortcut");
   }

   #[tokio::test]
   async fn test_state_persists_to_file() {
       let dir = temp_state_dir();
       {
           let ks = KillSwitch::new(dir.clone());
           ks.pause("test").await;
       }
       // Nuevo KillSwitch con mismo directorio debería cargar estado persistido
       let ks2 = KillSwitch::new(dir);
       assert_eq!(ks2.get_state().await, KillSwitchState::Paused);
   }

   #[tokio::test]
   async fn test_double_pause_is_safe() {
       let ks = KillSwitch::new(temp_state_dir());
       ks.pause("test").await;
       let state = ks.pause("test").await;
       assert_eq!(state, KillSwitchState::Paused);
   }

   #[tokio::test]
   async fn test_double_resume_is_safe() {
       let ks = KillSwitch::new(temp_state_dir());
       let state = ks.resume("test").await;
       assert_eq!(state, KillSwitchState::Active);
   }

4. Actualizar rust/guardian/src/lib.rs:

   Agregar:
   pub mod kill_switch;
   pub mod evdev_listener;

5. Ejecutar tests:
   cd ~/yeyo-os/rust/guardian
   cargo test 2>&1

VERIFICAR:
- [ ] Archivo rust/guardian/src/kill_switch.rs existe con KillSwitch
- [ ] Archivo rust/guardian/src/evdev_listener.rs existe con captura Ctrl+Alt+K
- [ ] Kill Switch PAUSA (SIGSTOP), no mata (SIGKILL)
- [ ] Toggle funciona: Active → Paused → Active
- [ ] Estado persiste a archivo JSON
- [ ] Eventos registrados con action, triggered_by, timestamp
- [ ] Double pause/resume son seguros
- [ ] Funciona incluso sin UI (solo necesita Guardian)
- [ ] TODOS los tests pasan

SI FALLA:
- uuid no en dev-dependencies: agregar uuid = { version = "1", features = ["v4"] }
- Permisos evdev: necesita grupo input o root
- Docker no disponible: tests pausan procesos, no containers

NO HACER:
- No usar SIGKILL — SIEMPRE SIGSTOP/SIGCONT (pausar, no matar)
- No matar Flash Memory bajo NINGUNA circunstancia
- No implementar la integración con frontend aún (eso es 6.9)
- No capturar otros atajos de teclado

GATE: Kill Switch pausa con SIGSTOP, resume con SIGCONT, toggle funciona, estado persiste, eventos registrados, funciona sin UI, todos los tests pasan.
```
