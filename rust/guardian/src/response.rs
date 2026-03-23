//! YeyoOS Guardian — Auto-Response
//! Micro-fase 6.2 — Capa 6: Sistema Inmune
//!
//! REGLA: NUNCA auto-borrar nada.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};

use crate::anomaly::AnomalyLevel;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ResponseAction {
    LogOnly { message: String },
    IncreaseMonitoring { new_interval_secs: u64 },
    BlockIp { ip: String, reason: String },
    PauseContainer { container_id: String, reason: String },
    IsolateContainer { container_id: String, reason: String },
    CreateSnapshot { label: String },
    AlertUser { title: String, message: String, level: AnomalyLevel },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseRecord {
    pub timestamp: DateTime<Utc>,
    pub trigger_level: AnomalyLevel,
    pub trigger_metric: String,
    pub trigger_score: f64,
    pub actions_taken: Vec<ResponseAction>,
    pub success: bool,
}

pub struct AutoResponder {
    records: Arc<RwLock<Vec<ResponseRecord>>>,
    max_records: usize,
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
            AnomalyLevel::Normal => {}

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
                    new_interval_secs: 2,
                });

                if let Some(ip) = suspicious_ip {
                    actions.push(ResponseAction::BlockIp {
                        ip: ip.to_string(),
                        reason: format!("Anomalía en {} con score {:.2}", metric, score),
                    });
                }
            }

            AnomalyLevel::Critical => {
                actions.push(ResponseAction::CreateSnapshot {
                    label: format!(
                        "pre-critical-{}-{}",
                        metric,
                        Utc::now().format("%Y%m%d-%H%M%S")
                    ),
                });

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

                if let Some(ip) = suspicious_ip {
                    actions.push(ResponseAction::BlockIp {
                        ip: ip.to_string(),
                        reason: format!("CRITICAL en {}: score {:.2}", metric, score),
                    });
                }

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
                    new_interval_secs: 1,
                });
            }
        }

        actions
    }

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

        for action in &actions {
            match action {
                ResponseAction::LogOnly { message } => {
                    info!("[AUTO-RESPONSE] {}", message);
                }
                ResponseAction::IncreaseMonitoring { new_interval_secs } => {
                    warn!("[AUTO-RESPONSE] Aumentando monitoreo a cada {}s", new_interval_secs);
                }
                ResponseAction::BlockIp { ip, reason } => {
                    warn!("[AUTO-RESPONSE] Bloqueando IP {}: {}", ip, reason);
                }
                ResponseAction::PauseContainer { container_id, reason } => {
                    error!("[AUTO-RESPONSE] PAUSANDO container {}: {}", container_id, reason);
                }
                ResponseAction::IsolateContainer { container_id, reason } => {
                    error!("[AUTO-RESPONSE] AISLANDO container {}: {}", container_id, reason);
                }
                ResponseAction::CreateSnapshot { label } => {
                    info!("[AUTO-RESPONSE] Creando snapshot: {}", label);
                }
                ResponseAction::AlertUser { title, message, .. } => {
                    error!("[AUTO-RESPONSE] ALERTA USUARIO: {} — {}", title, message);
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

        let mut records = self.records.write().await;
        records.push(record.clone());
        if records.len() > self.max_records {
            records.remove(0);
        }

        record
    }

    pub async fn set_enabled(&self, enabled: bool) {
        let mut e = self.enabled.write().await;
        *e = enabled;
        info!("[AUTO-RESPONSE] Habilitado: {}", enabled);
    }

    pub async fn is_enabled(&self) -> bool {
        *self.enabled.read().await
    }

    pub async fn get_records(&self) -> Vec<ResponseRecord> {
        self.records.read().await.clone()
    }
}

impl Default for AutoResponder {
    fn default() -> Self {
        Self::new()
    }
}
