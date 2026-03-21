## ═══════════════════════════════════════
## MICRO-FASE 6.2 — Guardian Auto-Response
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.2-1 [VSCODE] — Respuestas automáticas a eventos de seguridad

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.2 de Capa 6 (Sistema Inmune): implementar respuestas automáticas a eventos de seguridad dentro del Guardian Daemon.

CONTEXTO:
- Micro-fases 6.0-6.1 completadas: Guardian Daemon + Anomaly Detection
- Guardian ya detecta anomalías con scoring 0.0-1.0
- Ahora necesitamos respuestas AUTOMÁTICAS según el nivel de alerta
- CRITICAL: aislar container → pausar → alertar usuario
- WARNING: log + aumentar frecuencia de monitoreo
- INFO: solo log
- NUNCA auto-borrar nada (especialmente Flash Memory)
- Crear snapshot antes de cualquier acción destructiva

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo rust/guardian/src/response.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/response.rs
   Contenido:

   //! YeyoOS Guardian — Auto-Response
   //! Micro-fase 6.2 — Capa 6: Sistema Inmune
   //!
   //! Respuestas automáticas a eventos de seguridad.
   //! CRITICAL: aislar → pausar → alertar
   //! WARNING: log + aumentar monitoreo
   //! INFO: solo log
   //! REGLA: NUNCA auto-borrar nada.

   use chrono::{DateTime, Utc};
   use serde::{Deserialize, Serialize};
   use std::sync::Arc;
   use tokio::sync::RwLock;
   use tracing::{info, warn, error};

   use crate::anomaly::AnomalyLevel;

   // ═══════════════════════════════════
   // TIPOS DE DATOS
   // ═══════════════════════════════════

   /// Acción ejecutada por el auto-response.
   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub enum ResponseAction {
       /// Solo registrar en log
       LogOnly { message: String },
       /// Aumentar frecuencia de monitoreo
       IncreaseMonitoring { new_interval_secs: u64 },
       /// Bloquear IP sospechosa
       BlockIp { ip: String, reason: String },
       /// Pausar container sospechoso (PAUSAR, no matar)
       PauseContainer { container_id: String, reason: String },
       /// Aislar container de la red
       IsolateContainer { container_id: String, reason: String },
       /// Crear snapshot antes de acción
       CreateSnapshot { label: String },
       /// Alertar al usuario
       AlertUser { title: String, message: String, level: AnomalyLevel },
   }

   /// Registro de una respuesta ejecutada.
   #[derive(Debug, Clone, Serialize, Deserialize)]
   pub struct ResponseRecord {
       pub timestamp: DateTime<Utc>,
       pub trigger_level: AnomalyLevel,
       pub trigger_metric: String,
       pub trigger_score: f64,
       pub actions_taken: Vec<ResponseAction>,
       pub success: bool,
   }

   // ═══════════════════════════════════
   // AUTO-RESPONDER
   // ═══════════════════════════════════

   pub struct AutoResponder {
       /// Historial de respuestas
       records: Arc<RwLock<Vec<ResponseRecord>>>,
       /// Máximo de registros a mantener
       max_records: usize,
       /// ¿Está habilitado el auto-response?
       enabled: Arc<RwLock<bool>>,
   }

   impl AutoResponder {
       pub fn new() -> Self {
           Self {
               records: Arc::new(RwLock::new(Vec::new())),
               max_records: 500,
               enabled: Arc::new(RwLock::new(true)),
           }
       }

       /// Determina las acciones a tomar según el nivel de anomalía.
       pub fn determine_actions(
           &self,
           level: &AnomalyLevel,
           metric: &str,
           score: f64,
           container_id: Option<&str>,
           suspicious_ip: Option<&str>,
       ) -> Vec<ResponseAction> {
           let mut actions = Vec::new();

           match level {
               AnomalyLevel::Normal => {
                   // No se requiere acción
               }

               AnomalyLevel::Info => {
                   actions.push(ResponseAction::LogOnly {
                       message: format!(
                           "Actividad ligeramente inusual en {}: score {:.2}",
                           metric, score
                       ),
                   });
               }

               AnomalyLevel::Warning => {
                   actions.push(ResponseAction::LogOnly {
                       message: format!(
                           "⚠️ Anomalía WARNING en {}: score {:.2}",
                           metric, score
                       ),
                   });

                   actions.push(ResponseAction::IncreaseMonitoring {
                       new_interval_secs: 2, // De 10s a 2s
                   });

                   if let Some(ip) = suspicious_ip {
                       actions.push(ResponseAction::BlockIp {
                           ip: ip.to_string(),
                           reason: format!("Anomalía en {} con score {:.2}", metric, score),
                       });
                   }
               }

               AnomalyLevel::Critical => {
                   // 1. Snapshot PRIMERO (antes de cualquier acción)
                   actions.push(ResponseAction::CreateSnapshot {
                       label: format!(
                           "pre-critical-{}-{}",
                           metric,
                           Utc::now().format("%Y%m%d-%H%M%S")
                       ),
                   });

                   // 2. Aislar container si aplica
                   if let Some(cid) = container_id {
                       actions.push(ResponseAction::IsolateContainer {
                           container_id: cid.to_string(),
                           reason: format!("CRITICAL en {}: score {:.2}", metric, score),
                       });

                       actions.push(ResponseAction::PauseContainer {
                           container_id: cid.to_string(),
                           reason: format!("CRITICAL en {}: score {:.2}", metric, score),
                       });
                   }

                   // 3. Bloquear IP si aplica
                   if let Some(ip) = suspicious_ip {
                       actions.push(ResponseAction::BlockIp {
                           ip: ip.to_string(),
                           reason: format!("CRITICAL en {}: score {:.2}", metric, score),
                       });
                   }

                   // 4. Alertar al usuario SIEMPRE en CRITICAL
                   actions.push(ResponseAction::AlertUser {
                       title: format!("🚨 ALERTA CRÍTICA: {}", metric),
                       message: format!(
                           "Se detectó anomalía crítica en {} con score {:.2}. \
                            Se han tomado acciones automáticas de protección.",
                           metric, score
                       ),
                       level: AnomalyLevel::Critical,
                   });

                   actions.push(ResponseAction::IncreaseMonitoring {
                       new_interval_secs: 1, // Monitoreo máximo
                   });
               }
           }

           actions
       }

       /// Ejecuta las acciones determinadas y registra el resultado.
       pub async fn respond(
           &self,
           level: AnomalyLevel,
           metric: &str,
           score: f64,
           container_id: Option<&str>,
           suspicious_ip: Option<&str>,
       ) -> ResponseRecord {
           let enabled = *self.enabled.read().await;

           let actions = if enabled {
               self.determine_actions(&level, metric, score, container_id, suspicious_ip)
           } else {
               vec![ResponseAction::LogOnly {
                   message: "Auto-response deshabilitado".to_string(),
               }]
           };

           // Ejecutar cada acción
           for action in &actions {
               match action {
                   ResponseAction::LogOnly { message } => {
                       info!("[AUTO-RESPONSE] {}", message);
                   }
                   ResponseAction::IncreaseMonitoring { new_interval_secs } => {
                       warn!(
                           "[AUTO-RESPONSE] Aumentando monitoreo a cada {}s",
                           new_interval_secs
                       );
                   }
                   ResponseAction::BlockIp { ip, reason } => {
                       warn!("[AUTO-RESPONSE] Bloqueando IP {}: {}", ip, reason);
                       // TODO: Integrar con nftables (6.8)
                   }
                   ResponseAction::PauseContainer { container_id, reason } => {
                       error!(
                           "[AUTO-RESPONSE] PAUSANDO container {}: {}",
                           container_id, reason
                       );
                       // TODO: Integrar con Docker/containerd
                   }
                   ResponseAction::IsolateContainer { container_id, reason } => {
                       error!(
                           "[AUTO-RESPONSE] AISLANDO container {}: {}",
                           container_id, reason
                       );
                       // TODO: Integrar con network namespace
                   }
                   ResponseAction::CreateSnapshot { label } => {
                       info!("[AUTO-RESPONSE] Creando snapshot: {}", label);
                       // TODO: Integrar con Btrfs snapshots (6.4)
                   }
                   ResponseAction::AlertUser { title, message, .. } => {
                       error!("[AUTO-RESPONSE] ALERTA USUARIO: {} — {}", title, message);
                       // TODO: Integrar con notificaciones del frontend (6.9)
                   }
               }
           }

           let record = ResponseRecord {
               timestamp: Utc::now(),
               trigger_level: level,
               trigger_metric: metric.to_string(),
               trigger_score: score,
               actions_taken: actions,
               success: true,
           };

           // Almacenar registro
           let mut records = self.records.write().await;
           records.push(record.clone());
           if records.len() > self.max_records {
               records.remove(0);
           }

           record
       }

       /// Habilitar/deshabilitar auto-response.
       pub async fn set_enabled(&self, enabled: bool) {
           let mut e = self.enabled.write().await;
           *e = enabled;
           info!("[AUTO-RESPONSE] Habilitado: {}", enabled);
       }

       /// Retorna si está habilitado.
       pub async fn is_enabled(&self) -> bool {
           *self.enabled.read().await
       }

       /// Retorna historial de respuestas.
       pub async fn get_records(&self) -> Vec<ResponseRecord> {
           self.records.read().await.clone()
       }
   }

   impl Default for AutoResponder {
       fn default() -> Self {
           Self::new()
       }
   }

2. Crear archivo rust/guardian/tests/response_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/response_test.rs
   Contenido:

   //! Tests para AutoResponder — Micro-fase 6.2

   use yeyo_guardian::anomaly::AnomalyLevel;
   use yeyo_guardian::response::{AutoResponder, ResponseAction};

   #[tokio::test]
   async fn test_critical_triggers_isolation() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Critical,
           "cpu_usage",
           0.95,
           Some("container-abc123"),
           None,
       ).await;

       let has_isolate = record.actions_taken.iter().any(|a| {
           matches!(a, ResponseAction::IsolateContainer { .. })
       });
       assert!(has_isolate, "CRITICAL debe aislar container");
   }

   #[tokio::test]
   async fn test_critical_creates_snapshot_first() {
       let responder = AutoResponder::new();
       let actions = responder.determine_actions(
           &AnomalyLevel::Critical,
           "cpu_usage",
           0.95,
           Some("container-abc"),
           None,
       );

       // Snapshot debe ser la PRIMERA acción
       assert!(matches!(&actions[0], ResponseAction::CreateSnapshot { .. }));
   }

   #[tokio::test]
   async fn test_critical_pauses_container() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Critical,
           "cpu_usage",
           0.95,
           Some("container-abc123"),
           None,
       ).await;

       let has_pause = record.actions_taken.iter().any(|a| {
           matches!(a, ResponseAction::PauseContainer { .. })
       });
       assert!(has_pause, "CRITICAL debe pausar container");
   }

   #[tokio::test]
   async fn test_warning_increases_monitoring() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Warning,
           "network_rx",
           0.75,
           None,
           None,
       ).await;

       let has_increase = record.actions_taken.iter().any(|a| {
           matches!(a, ResponseAction::IncreaseMonitoring { .. })
       });
       assert!(has_increase, "WARNING debe aumentar monitoreo");
   }

   #[tokio::test]
   async fn test_warning_blocks_suspicious_ip() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Warning,
           "network_rx",
           0.75,
           None,
           Some("192.168.1.100"),
       ).await;

       let has_block = record.actions_taken.iter().any(|a| {
           matches!(a, ResponseAction::BlockIp { .. })
       });
       assert!(has_block, "WARNING con IP debe bloquear IP");
   }

   #[tokio::test]
   async fn test_info_only_logs() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Info,
           "cpu_usage",
           0.55,
           None,
           None,
       ).await;

       assert_eq!(record.actions_taken.len(), 1);
       assert!(matches!(&record.actions_taken[0], ResponseAction::LogOnly { .. }));
   }

   #[tokio::test]
   async fn test_normal_no_actions() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Normal,
           "cpu_usage",
           0.2,
           None,
           None,
       ).await;

       assert!(record.actions_taken.is_empty());
   }

   #[tokio::test]
   async fn test_nothing_auto_deleted() {
       let responder = AutoResponder::new();
       let record = responder.respond(
           AnomalyLevel::Critical,
           "disk_usage",
           0.99,
           Some("container-xyz"),
           Some("10.0.0.1"),
       ).await;

       // Verificar que NINGUNA acción sea de borrado
       for action in &record.actions_taken {
           let is_delete = match action {
               ResponseAction::LogOnly { message } => message.contains("delete") || message.contains("borrar"),
               _ => false,
           };
           assert!(!is_delete, "NUNCA auto-borrar nada");
       }
   }

   #[tokio::test]
   async fn test_disabled_responder() {
       let responder = AutoResponder::new();
       responder.set_enabled(false).await;

       let record = responder.respond(
           AnomalyLevel::Critical,
           "cpu_usage",
           0.99,
           Some("container-abc"),
           None,
       ).await;

       // Solo debería loguear que está deshabilitado
       assert_eq!(record.actions_taken.len(), 1);
       assert!(matches!(&record.actions_taken[0], ResponseAction::LogOnly { .. }));
   }

3. Actualizar rust/guardian/src/lib.rs:

   Agregar: pub mod response;

4. Ejecutar tests:
   cd ~/yeyo-os/rust/guardian
   cargo test 2>&1

VERIFICAR:
- [ ] Archivo rust/guardian/src/response.rs existe con AutoResponder
- [ ] CRITICAL: snapshot primero → aislar → pausar → alertar usuario
- [ ] WARNING: log + aumentar monitoreo + bloquear IP si hay
- [ ] INFO: solo log
- [ ] Normal: sin acciones
- [ ] NUNCA se auto-borra nada
- [ ] Deshabilitado solo loguea
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar que lib.rs incluya `pub mod response;`
- Enum variants: verificar AnomalyLevel importado correctamente

NO HACER:
- No implementar la ejecución real de Docker pause/isolate (solo la lógica)
- No implementar borrado automático de ningún tipo
- No borrar Flash Memory bajo NINGUNA circunstancia
- No conectar con Kill Switch aún (eso es 6.3)

GATE: AutoResponder determina acciones correctas por nivel, CRITICAL siempre crea snapshot primero, NUNCA borra nada, responder deshabilitado solo loguea, todos los tests pasan.
```
