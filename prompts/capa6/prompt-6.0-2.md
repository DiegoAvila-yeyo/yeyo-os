## ═══════════════════════════════════════
## MICRO-FASE 6.0 — Guardian Daemon Tests
## Tipo: VSCODE | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.0-2 [VSCODE] — Tests del Guardian Daemon

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la parte 2 de micro-fase 6.0 de Capa 6 (Sistema Inmune): crear los tests del Guardian Daemon en Rust.

CONTEXTO:
- Micro-fase 6.0-1 completada: Guardian Daemon base compilando
- rust/guardian/src/main.rs, config.rs, monitor.rs, heartbeat.rs, api.rs existen
- Necesitamos tests unitarios e integración para verificar que Guardian funciona
- Tests en Rust con #[tokio::test] para async

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo rust/guardian/tests/monitor_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/monitor_test.rs
   Contenido:

   //! Tests para ResourceMonitor — Micro-fase 6.0
   //! Verifica monitoreo de CPU, RAM, disco, alertas.

   use yeyo_guardian::config::GuardianConfig;
   use yeyo_guardian::monitor::{ResourceMonitor, AlertLevel};

   #[tokio::test]
   async fn test_take_snapshot_returns_data() {
       let config = GuardianConfig::default();
       let monitor = ResourceMonitor::new(config);
       let snapshot = monitor.take_snapshot().await;

       assert!(snapshot.cpu_usage_percent >= 0.0);
       assert!(snapshot.ram_total_mb > 0);
       assert!(snapshot.process_count > 0);
   }

   #[tokio::test]
   async fn test_snapshot_stored_as_latest() {
       let config = GuardianConfig::default();
       let monitor = ResourceMonitor::new(config);

       assert!(monitor.get_latest_snapshot().await.is_none());

       monitor.take_snapshot().await;

       assert!(monitor.get_latest_snapshot().await.is_some());
   }

   #[tokio::test]
   async fn test_alerts_empty_initially() {
       let config = GuardianConfig::default();
       let monitor = ResourceMonitor::new(config);

       let alerts = monitor.get_alerts().await;
       assert!(alerts.is_empty());
   }

   #[tokio::test]
   async fn test_low_threshold_triggers_alert() {
       let mut config = GuardianConfig::default();
       // Umbrales muy bajos para forzar alertas
       config.cpu_alert_threshold = 0.1;
       config.ram_alert_threshold = 0.1;
       config.disk_alert_threshold = 0.1;

       let monitor = ResourceMonitor::new(config);
       monitor.take_snapshot().await;

       let alerts = monitor.get_alerts().await;
       // Debería haber al menos una alerta (RAM o disco casi siempre >0.1%)
       assert!(!alerts.is_empty());
       assert_eq!(alerts[0].level, AlertLevel::Critical);
   }

   #[tokio::test]
   async fn test_cleanup_alerts_keeps_max_100() {
       let mut config = GuardianConfig::default();
       config.cpu_alert_threshold = 0.1;
       config.ram_alert_threshold = 0.1;
       config.disk_alert_threshold = 0.1;

       let monitor = ResourceMonitor::new(config);

       // Generar muchas alertas
       for _ in 0..50 {
           monitor.take_snapshot().await;
       }

       monitor.cleanup_alerts().await;

       let alerts = monitor.get_alerts().await;
       assert!(alerts.len() <= 100);
   }

2. Crear archivo rust/guardian/tests/heartbeat_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/heartbeat_test.rs
   Contenido:

   //! Tests para Heartbeat — Micro-fase 6.0
   //! Verifica que el heartbeat funciona correctamente.

   use yeyo_guardian::heartbeat::Heartbeat;

   #[tokio::test]
   async fn test_heartbeat_initial_state() {
       let hb = Heartbeat::new();
       assert_eq!(hb.get_beat_count().await, 0);
       assert!(hb.get_latest().await.is_none());
   }

   #[tokio::test]
   async fn test_heartbeat_increments() {
       let hb = Heartbeat::new();

       hb.beat().await;
       assert_eq!(hb.get_beat_count().await, 1);

       hb.beat().await;
       assert_eq!(hb.get_beat_count().await, 2);

       hb.beat().await;
       assert_eq!(hb.get_beat_count().await, 3);
   }

   #[tokio::test]
   async fn test_heartbeat_stores_latest() {
       let hb = Heartbeat::new();

       let info = hb.beat().await;
       assert_eq!(info.status, "alive");
       assert_eq!(info.beat_count, 1);

       let latest = hb.get_latest().await.unwrap();
       assert_eq!(latest.beat_count, 1);
   }

   #[tokio::test]
   async fn test_heartbeat_uptime_increases() {
       let hb = Heartbeat::new();

       let first = hb.beat().await;
       tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
       let second = hb.beat().await;

       assert!(second.uptime_secs >= first.uptime_secs);
   }

3. Crear archivo rust/guardian/tests/api_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/api_test.rs
   Contenido:

   //! Tests para la API HTTP — Micro-fase 6.0
   //! Verifica que los endpoints responden correctamente.

   use axum::body::Body;
   use axum::http::{Request, StatusCode};
   use tower::ServiceExt;
   use std::sync::Arc;

   use yeyo_guardian::api::{AppState, create_router};
   use yeyo_guardian::config::GuardianConfig;
   use yeyo_guardian::heartbeat::Heartbeat;
   use yeyo_guardian::monitor::ResourceMonitor;

   fn create_test_state() -> AppState {
       let config = GuardianConfig::default();
       AppState {
           monitor: Arc::new(ResourceMonitor::new(config)),
           heartbeat: Arc::new(Heartbeat::new()),
       }
   }

   #[tokio::test]
   async fn test_health_endpoint() {
       let state = create_test_state();
       let app = create_router(state);

       let response = app
           .oneshot(
               Request::builder()
                   .uri("/health")
                   .body(Body::empty())
                   .unwrap(),
           )
           .await
           .unwrap();

       assert_eq!(response.status(), StatusCode::OK);
   }

   #[tokio::test]
   async fn test_status_endpoint() {
       let state = create_test_state();
       let app = create_router(state);

       let response = app
           .oneshot(
               Request::builder()
                   .uri("/status")
                   .body(Body::empty())
                   .unwrap(),
           )
           .await
           .unwrap();

       assert_eq!(response.status(), StatusCode::OK);
   }

   #[tokio::test]
   async fn test_resources_returns_503_when_no_snapshot() {
       let state = create_test_state();
       let app = create_router(state);

       let response = app
           .oneshot(
               Request::builder()
                   .uri("/resources")
                   .body(Body::empty())
                   .unwrap(),
           )
           .await
           .unwrap();

       assert_eq!(response.status(), StatusCode::SERVICE_UNAVAILABLE);
   }

   #[tokio::test]
   async fn test_resources_returns_200_after_snapshot() {
       let state = create_test_state();
       state.monitor.take_snapshot().await;

       let app = create_router(state);

       let response = app
           .oneshot(
               Request::builder()
                   .uri("/resources")
                   .body(Body::empty())
                   .unwrap(),
           )
           .await
           .unwrap();

       assert_eq!(response.status(), StatusCode::OK);
   }

   #[tokio::test]
   async fn test_alerts_endpoint() {
       let state = create_test_state();
       let app = create_router(state);

       let response = app
           .oneshot(
               Request::builder()
                   .uri("/alerts")
                   .body(Body::empty())
                   .unwrap(),
           )
           .await
           .unwrap();

       assert_eq!(response.status(), StatusCode::OK);
   }

4. Actualizar rust/guardian/src/main.rs para exponer módulos como lib:

   Crear archivo rust/guardian/src/lib.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/lib.rs
   Contenido:

   //! YeyoOS Guardian — Biblioteca
   //! Expone módulos para tests de integración.

   pub mod api;
   pub mod config;
   pub mod heartbeat;
   pub mod monitor;

5. Ejecutar tests:
   cd ~/yeyo-os/rust/guardian
   cargo test 2>&1

VERIFICAR:
- [ ] Archivo tests/monitor_test.rs existe
- [ ] Archivo tests/heartbeat_test.rs existe
- [ ] Archivo tests/api_test.rs existe
- [ ] Archivo src/lib.rs existe y expone módulos públicos
- [ ] cargo test compila sin errores
- [ ] TODOS los tests pasan
- [ ] Snapshot devuelve datos reales del sistema
- [ ] Heartbeat incrementa correctamente
- [ ] API /health responde 200
- [ ] API /resources responde 503 sin snapshot, 200 con snapshot

SI FALLA:
- Módulos no encontrados: verificar que src/lib.rs expone todos los módulos
- Tests async fallan: verificar que se usa #[tokio::test]
- tower no encontrado: agregar tower = { version = "0.4", features = ["util"] } a dev-dependencies

NO HACER:
- No modificar el código del daemon (solo agregar tests y lib.rs)
- No crear tests de anomaly detection (eso es 6.1)
- No ejecutar el daemon en producción aún

GATE: Todos los tests pasan (monitor, heartbeat, API), lib.rs expone módulos, cargo test muestra 0 failed.
```
