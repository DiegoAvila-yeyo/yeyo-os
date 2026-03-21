## ═══════════════════════════════════════
## MICRO-FASE 6.0 — Guardian Daemon Base
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.0-1 [VSCODE] — Crear Guardian Daemon en Rust

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.0 de Capa 6 (Sistema Inmune): crear el Guardian Daemon en Rust, el proceso centinela que monitorea todo el sistema.

CONTEXTO:
- Capas 0-5 completadas: infraestructura, esqueleto, cerebro, cuerpo/UI, sistema nervioso, órganos
- Capa 6 = el SISTEMA INMUNE de YeyoOS. Guardian es el corazón de la seguridad
- Guardian corre como servicio systemd, arranca ANTES que todo lo demás
- Monitorea: CPU, RAM, disco, GPU, red, procesos
- Escribe logs en /var/log/yeyo/guardian/
- Expone API HTTP en localhost:9090 para consultas de estado
- Usa tokio para async, serde para JSON, axum para HTTP
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p rust/guardian/src
   mkdir -p rust/guardian/tests

2. Crear archivo rust/guardian/Cargo.toml:

   Ruta: ~/yeyo-os/rust/guardian/Cargo.toml
   Contenido:

   [package]
   name = "yeyo-guardian"
   version = "0.1.0"
   edition = "2021"
   description = "YeyoOS Guardian Daemon — Sistema Inmune"

   [dependencies]
   tokio = { version = "1", features = ["full"] }
   serde = { version = "1", features = ["derive"] }
   serde_json = "1"
   axum = "0.7"
   tower-http = { version = "0.5", features = ["cors"] }
   tracing = "0.1"
   tracing-subscriber = { version = "0.3", features = ["env-filter"] }
   chrono = { version = "0.4", features = ["serde"] }
   sysinfo = "0.31"
   uuid = { version = "1", features = ["v4"] }
   thiserror = "1"

   [dev-dependencies]
   reqwest = { version = "0.12", features = ["json"] }
   tokio-test = "0.4"

3. Crear archivo rust/guardian/src/config.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/config.rs
   Contenido:

   //! YeyoOS Guardian — Configuración
   //! Micro-fase 6.0 — Capa 6: Sistema Inmune

   use std::path::PathBuf;

   /// Configuración del Guardian Daemon.
   #[derive(Debug, Clone)]
   pub struct GuardianConfig {
       /// Puerto HTTP para la API de estado
       pub http_port: u16,
       /// Directorio de logs
       pub log_dir: PathBuf,
       /// Intervalo de heartbeat en segundos
       pub heartbeat_interval_secs: u64,
       /// Intervalo de monitoreo de recursos en segundos
       pub monitor_interval_secs: u64,
       /// Umbral de CPU para alertas (porcentaje)
       pub cpu_alert_threshold: f32,
       /// Umbral de RAM para alertas (porcentaje)
       pub ram_alert_threshold: f32,
       /// Umbral de disco para alertas (porcentaje)
       pub disk_alert_threshold: f32,
   }

   impl Default for GuardianConfig {
       fn default() -> Self {
           Self {
               http_port: 9090,
               log_dir: PathBuf::from("/var/log/yeyo/guardian"),
               heartbeat_interval_secs: 5,
               monitor_interval_secs: 10,
               cpu_alert_threshold: 90.0,
               ram_alert_threshold: 90.0,
               disk_alert_threshold: 90.0,
           }
       }
   }

4. Crear archivo rust/guardian/src/monitor.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/monitor.rs
   Contenido:

   //! YeyoOS Guardian — Monitor de Recursos
   //! Micro-fase 6.0 — Capa 6: Sistema Inmune
   //!
   //! Monitorea CPU, RAM, disco, GPU, red y procesos.
   //! Genera alertas cuando los recursos superan umbrales.

   use chrono::{DateTime, Utc};
   use serde::{Deserialize, Serialize};
   use sysinfo::{System, Disks, Networks};
   use std::sync::Arc;
   use tokio::sync::RwLock;
   use tracing::{info, warn};

   use crate::config::GuardianConfig;

   // ═══════════════════════════════════
   // TIPOS DE DATOS
   // ═══════════════════════════════════

   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct ResourceSnapshot {
       pub timestamp: DateTime<Utc>,
       pub cpu_usage_percent: f32,
       pub ram_used_mb: u64,
       pub ram_total_mb: u64,
       pub ram_usage_percent: f32,
       pub disk_used_gb: f64,
       pub disk_total_gb: f64,
       pub disk_usage_percent: f32,
       pub process_count: usize,
       pub network_rx_bytes: u64,
       pub network_tx_bytes: u64,
   }

   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub enum AlertLevel {
       Info,
       Warning,
       Critical,
   }

   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct ResourceAlert {
       pub timestamp: DateTime<Utc>,
       pub level: AlertLevel,
       pub resource: String,
       pub message: String,
       pub value: f32,
       pub threshold: f32,
   }

   // ═══════════════════════════════════
   // MONITOR DE RECURSOS
   // ═══════════════════════════════════

   pub struct ResourceMonitor {
       config: GuardianConfig,
       system: Arc<RwLock<System>>,
       latest_snapshot: Arc<RwLock<Option<ResourceSnapshot>>>,
       alerts: Arc<RwLock<Vec<ResourceAlert>>>,
   }

   impl ResourceMonitor {
       pub fn new(config: GuardianConfig) -> Self {
           Self {
               config,
               system: Arc::new(RwLock::new(System::new_all())),
               latest_snapshot: Arc::new(RwLock::new(None)),
               alerts: Arc::new(RwLock::new(Vec::new())),
           }
       }

       /// Toma un snapshot de todos los recursos del sistema.
       pub async fn take_snapshot(&self) -> ResourceSnapshot {
           let mut sys = self.system.write().await;
           sys.refresh_all();

           let cpu_usage = sys.global_cpu_usage();

           let ram_used = sys.used_memory() / 1024 / 1024;
           let ram_total = sys.total_memory() / 1024 / 1024;
           let ram_percent = if ram_total > 0 {
               (ram_used as f32 / ram_total as f32) * 100.0
           } else {
               0.0
           };

           let disks = Disks::new_with_refreshed_list();
           let (disk_used, disk_total) = disks.iter().fold((0u64, 0u64), |(used, total), d| {
               (used + (d.total_space() - d.available_space()), total + d.total_space())
           });
           let disk_used_gb = disk_used as f64 / 1_073_741_824.0;
           let disk_total_gb = disk_total as f64 / 1_073_741_824.0;
           let disk_percent = if disk_total > 0 {
               (disk_used as f32 / disk_total as f32) * 100.0
           } else {
               0.0
           };

           let networks = Networks::new_with_refreshed_list();
           let (rx, tx) = networks.iter().fold((0u64, 0u64), |(rx, tx), (_name, data)| {
               (rx + data.total_received(), tx + data.total_transmitted())
           });

           let process_count = sys.processes().len();

           let snapshot = ResourceSnapshot {
               timestamp: Utc::now(),
               cpu_usage_percent: cpu_usage,
               ram_used_mb: ram_used,
               ram_total_mb: ram_total,
               ram_usage_percent: ram_percent,
               disk_used_gb,
               disk_total_gb,
               disk_usage_percent: disk_percent,
               process_count,
               network_rx_bytes: rx,
               network_tx_bytes: tx,
           };

           // Almacenar snapshot
           let mut latest = self.latest_snapshot.write().await;
           *latest = Some(snapshot.clone());

           // Verificar umbrales y generar alertas
           self.check_thresholds(&snapshot).await;

           info!(
               cpu = %snapshot.cpu_usage_percent,
               ram = %snapshot.ram_usage_percent,
               disk = %snapshot.disk_usage_percent,
               procs = %snapshot.process_count,
               "Resource snapshot taken"
           );

           snapshot
       }

       /// Verifica umbrales y genera alertas si se superan.
       async fn check_thresholds(&self, snapshot: &ResourceSnapshot) {
           let mut alerts = self.alerts.write().await;

           if snapshot.cpu_usage_percent > self.config.cpu_alert_threshold {
               let alert = ResourceAlert {
                   timestamp: Utc::now(),
                   level: AlertLevel::Critical,
                   resource: "cpu".to_string(),
                   message: format!(
                       "CPU al {:.1}% — supera umbral de {:.1}%",
                       snapshot.cpu_usage_percent, self.config.cpu_alert_threshold
                   ),
                   value: snapshot.cpu_usage_percent,
                   threshold: self.config.cpu_alert_threshold,
               };
               warn!("{}", alert.message);
               alerts.push(alert);
           }

           if snapshot.ram_usage_percent > self.config.ram_alert_threshold {
               let alert = ResourceAlert {
                   timestamp: Utc::now(),
                   level: AlertLevel::Critical,
                   resource: "ram".to_string(),
                   message: format!(
                       "RAM al {:.1}% — supera umbral de {:.1}%",
                       snapshot.ram_usage_percent, self.config.ram_alert_threshold
                   ),
                   value: snapshot.ram_usage_percent,
                   threshold: self.config.ram_alert_threshold,
               };
               warn!("{}", alert.message);
               alerts.push(alert);
           }

           if snapshot.disk_usage_percent > self.config.disk_alert_threshold {
               let alert = ResourceAlert {
                   timestamp: Utc::now(),
                   level: AlertLevel::Critical,
                   resource: "disk".to_string(),
                   message: format!(
                       "Disco al {:.1}% — supera umbral de {:.1}%",
                       snapshot.disk_usage_percent, self.config.disk_alert_threshold
                   ),
                   value: snapshot.disk_usage_percent,
                   threshold: self.config.disk_alert_threshold,
               };
               warn!("{}", alert.message);
               alerts.push(alert);
           }
       }

       /// Retorna el snapshot más reciente.
       pub async fn get_latest_snapshot(&self) -> Option<ResourceSnapshot> {
           self.latest_snapshot.read().await.clone()
       }

       /// Retorna todas las alertas.
       pub async fn get_alerts(&self) -> Vec<ResourceAlert> {
           self.alerts.read().await.clone()
       }

       /// Limpia alertas antiguas (mantiene las últimas 100).
       pub async fn cleanup_alerts(&self) {
           let mut alerts = self.alerts.write().await;
           if alerts.len() > 100 {
               let drain_count = alerts.len() - 100;
               alerts.drain(0..drain_count);
           }
       }
   }

5. Crear archivo rust/guardian/src/heartbeat.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/heartbeat.rs
   Contenido:

   //! YeyoOS Guardian — Heartbeat
   //! Micro-fase 6.0 — Capa 6: Sistema Inmune
   //!
   //! Heartbeat cada 5 segundos para verificar que Guardian sigue vivo.

   use chrono::{DateTime, Utc};
   use serde::{Deserialize, Serialize};
   use std::sync::Arc;
   use tokio::sync::RwLock;
   use tracing::debug;

   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct HeartbeatInfo {
       pub timestamp: DateTime<Utc>,
       pub uptime_secs: u64,
       pub beat_count: u64,
       pub status: String,
   }

   pub struct Heartbeat {
       start_time: DateTime<Utc>,
       beat_count: Arc<RwLock<u64>>,
       latest: Arc<RwLock<Option<HeartbeatInfo>>>,
   }

   impl Heartbeat {
       pub fn new() -> Self {
           Self {
               start_time: Utc::now(),
               beat_count: Arc::new(RwLock::new(0)),
               latest: Arc::new(RwLock::new(None)),
           }
       }

       /// Ejecuta un beat: actualiza contador y timestamp.
       pub async fn beat(&self) -> HeartbeatInfo {
           let mut count = self.beat_count.write().await;
           *count += 1;

           let now = Utc::now();
           let uptime = (now - self.start_time).num_seconds() as u64;

           let info = HeartbeatInfo {
               timestamp: now,
               uptime_secs: uptime,
               beat_count: *count,
               status: "alive".to_string(),
           };

           let mut latest = self.latest.write().await;
           *latest = Some(info.clone());

           debug!(beat = *count, uptime = uptime, "Guardian heartbeat");

           info
       }

       /// Retorna el último heartbeat.
       pub async fn get_latest(&self) -> Option<HeartbeatInfo> {
           self.latest.read().await.clone()
       }

       /// Retorna el número de beats.
       pub async fn get_beat_count(&self) -> u64 {
           *self.beat_count.read().await
       }
   }

   impl Default for Heartbeat {
       fn default() -> Self {
           Self::new()
       }
   }

6. Crear archivo rust/guardian/src/api.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/api.rs
   Contenido:

   //! YeyoOS Guardian — API HTTP
   //! Micro-fase 6.0 — Capa 6: Sistema Inmune
   //!
   //! API REST en localhost:9090 para consultas de estado.
   //! Endpoints:
   //!   GET /health          — Health check
   //!   GET /status          — Estado completo de Guardian
   //!   GET /resources       — Último snapshot de recursos
   //!   GET /alerts          — Lista de alertas activas
   //!   GET /heartbeat       — Último heartbeat

   use axum::{
       extract::State,
       http::StatusCode,
       response::Json,
       routing::get,
       Router,
   };
   use serde::Serialize;
   use std::sync::Arc;

   use crate::heartbeat::Heartbeat;
   use crate::monitor::ResourceMonitor;

   // ═══════════════════════════════════
   // ESTADO COMPARTIDO
   // ═══════════════════════════════════

   #[derive(Clone)]
   pub struct AppState {
       pub monitor: Arc<ResourceMonitor>,
       pub heartbeat: Arc<Heartbeat>,
   }

   // ═══════════════════════════════════
   // RESPUESTAS
   // ═══════════════════════════════════

   #[derive(Serialize)]
   struct HealthResponse {
       status: String,
       service: String,
       version: String,
   }

   #[derive(Serialize)]
   struct StatusResponse {
       guardian: String,
       uptime_secs: u64,
       heartbeat_count: u64,
       resource_snapshot: Option<crate::monitor::ResourceSnapshot>,
       active_alerts: usize,
   }

   // ═══════════════════════════════════
   // HANDLERS
   // ═══════════════════════════════════

   async fn health() -> Json<HealthResponse> {
       Json(HealthResponse {
           status: "ok".to_string(),
           service: "yeyo-guardian".to_string(),
           version: env!("CARGO_PKG_VERSION").to_string(),
       })
   }

   async fn status(State(state): State<AppState>) -> Json<StatusResponse> {
       let heartbeat = state.heartbeat.get_latest().await;
       let snapshot = state.monitor.get_latest_snapshot().await;
       let alerts = state.monitor.get_alerts().await;

       Json(StatusResponse {
           guardian: "running".to_string(),
           uptime_secs: heartbeat.as_ref().map(|h| h.uptime_secs).unwrap_or(0),
           heartbeat_count: heartbeat.as_ref().map(|h| h.beat_count).unwrap_or(0),
           resource_snapshot: snapshot,
           active_alerts: alerts.len(),
       })
   }

   async fn resources(
       State(state): State<AppState>,
   ) -> Result<Json<crate::monitor::ResourceSnapshot>, StatusCode> {
       match state.monitor.get_latest_snapshot().await {
           Some(snapshot) => Ok(Json(snapshot)),
           None => Err(StatusCode::SERVICE_UNAVAILABLE),
       }
   }

   async fn alerts(
       State(state): State<AppState>,
   ) -> Json<Vec<crate::monitor::ResourceAlert>> {
       Json(state.monitor.get_alerts().await)
   }

   async fn heartbeat_endpoint(
       State(state): State<AppState>,
   ) -> Result<Json<crate::heartbeat::HeartbeatInfo>, StatusCode> {
       match state.heartbeat.get_latest().await {
           Some(info) => Ok(Json(info)),
           None => Err(StatusCode::SERVICE_UNAVAILABLE),
       }
   }

   // ═══════════════════════════════════
   // ROUTER
   // ═══════════════════════════════════

   pub fn create_router(state: AppState) -> Router {
       Router::new()
           .route("/health", get(health))
           .route("/status", get(status))
           .route("/resources", get(resources))
           .route("/alerts", get(alerts))
           .route("/heartbeat", get(heartbeat_endpoint))
           .with_state(state)
   }

7. Crear archivo rust/guardian/src/main.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/main.rs
   Contenido:

   //! YeyoOS Guardian Daemon
   //! Micro-fase 6.0 — Capa 6: Sistema Inmune
   //!
   //! Daemon principal que protege a YeyoOS.
   //! Corre como servicio systemd, arranca antes que todo.
   //! Monitorea: CPU, RAM, disco, GPU, red, procesos.
   //! Expone API HTTP en localhost:9090.

   mod api;
   mod config;
   mod heartbeat;
   mod monitor;

   use std::sync::Arc;
   use tokio::net::TcpListener;
   use tracing::{info, error};

   use api::{AppState, create_router};
   use config::GuardianConfig;
   use heartbeat::Heartbeat;
   use monitor::ResourceMonitor;

   #[tokio::main]
   async fn main() {
       // Inicializar logging
       tracing_subscriber::fmt()
           .with_env_filter(
               tracing_subscriber::EnvFilter::try_from_default_env()
                   .unwrap_or_else(|_| "yeyo_guardian=info".into()),
           )
           .init();

       info!("═══════════════════════════════════════");
       info!("  YeyoOS Guardian Daemon v{}", env!("CARGO_PKG_VERSION"));
       info!("  Capa 6: Sistema Inmune — ACTIVADO");
       info!("═══════════════════════════════════════");

       let config = GuardianConfig::default();
       let monitor = Arc::new(ResourceMonitor::new(config.clone()));
       let heartbeat = Arc::new(Heartbeat::new());

       // Crear directorio de logs
       if let Err(e) = tokio::fs::create_dir_all(&config.log_dir).await {
           error!("No se pudo crear directorio de logs: {}", e);
       }

       let state = AppState {
           monitor: monitor.clone(),
           heartbeat: heartbeat.clone(),
       };

       // Tarea: Heartbeat periódico
       let hb = heartbeat.clone();
       let hb_interval = config.heartbeat_interval_secs;
       tokio::spawn(async move {
           let mut interval = tokio::time::interval(
               tokio::time::Duration::from_secs(hb_interval),
           );
           loop {
               interval.tick().await;
               hb.beat().await;
           }
       });

       // Tarea: Monitoreo de recursos periódico
       let mon = monitor.clone();
       let mon_interval = config.monitor_interval_secs;
       tokio::spawn(async move {
           let mut interval = tokio::time::interval(
               tokio::time::Duration::from_secs(mon_interval),
           );
           loop {
               interval.tick().await;
               mon.take_snapshot().await;
               mon.cleanup_alerts().await;
           }
       });

       // Servidor HTTP
       let addr = format!("127.0.0.1:{}", config.http_port);
       info!("Guardian API escuchando en http://{}", addr);

       let listener = TcpListener::bind(&addr).await.unwrap_or_else(|e| {
           error!("No se pudo bindear al puerto {}: {}", config.http_port, e);
           std::process::exit(1);
       });

       let router = create_router(state);

       if let Err(e) = axum::serve(listener, router).await {
           error!("Error en servidor HTTP: {}", e);
           std::process::exit(1);
       }
   }

8. Crear archivo de servicio systemd rust/guardian/yeyo-guardian.service:

   Ruta: ~/yeyo-os/rust/guardian/yeyo-guardian.service
   Contenido:

   [Unit]
   Description=YeyoOS Guardian Daemon — Sistema Inmune
   After=network.target
   Before=yeyo-backend.service yeyo-ollama.service
   Wants=network-online.target

   [Service]
   Type=simple
   ExecStart=/usr/local/bin/yeyo-guardian
   Restart=always
   RestartSec=3
   StandardOutput=journal
   StandardError=journal
   SyslogIdentifier=yeyo-guardian
   Environment=RUST_LOG=yeyo_guardian=info

   [Install]
   WantedBy=multi-user.target

9. Compilar Guardian:
   cd ~/yeyo-os/rust/guardian
   cargo build 2>&1

VERIFICAR:
- [ ] Archivo rust/guardian/Cargo.toml existe con dependencias correctas
- [ ] Archivo rust/guardian/src/main.rs existe con daemon principal
- [ ] Archivo rust/guardian/src/config.rs existe con GuardianConfig
- [ ] Archivo rust/guardian/src/monitor.rs existe con ResourceMonitor
- [ ] Archivo rust/guardian/src/heartbeat.rs existe con Heartbeat
- [ ] Archivo rust/guardian/src/api.rs existe con endpoints REST
- [ ] Archivo rust/guardian/yeyo-guardian.service existe
- [ ] cargo build compila sin errores
- [ ] API tiene 5 endpoints: /health, /status, /resources, /alerts, /heartbeat

SI FALLA:
- Rust no instalado: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- Error de compilación: verificar versiones de dependencias en Cargo.toml
- Puerto 9090 ocupado: cambiar en GuardianConfig

NO HACER:
- No implementar anomaly detection aún (eso es 6.1)
- No implementar kill switch aún (eso es 6.3)
- No crear containers reales
- No tocar archivos de Capas anteriores
- No usar Python para Guardian (DEBE ser Rust)

GATE: Guardian compila en Rust, ResourceMonitor toma snapshots de CPU/RAM/disco, Heartbeat funciona cada 5s, API HTTP responde en localhost:9090, servicio systemd configurado.
```
