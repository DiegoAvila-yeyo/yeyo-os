//! YeyoOS Guardian — Monitor de Recursos
//! Micro-fase 6.0 — Capa 6: Sistema Inmune

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sysinfo::{System, Disks, Networks};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn};

use crate::config::GuardianConfig;

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

        let mut latest = self.latest_snapshot.write().await;
        *latest = Some(snapshot.clone());

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

    pub async fn get_latest_snapshot(&self) -> Option<ResourceSnapshot> {
        self.latest_snapshot.read().await.clone()
    }

    pub async fn get_alerts(&self) -> Vec<ResourceAlert> {
        self.alerts.read().await.clone()
    }

    pub async fn cleanup_alerts(&self) {
        let mut alerts = self.alerts.write().await;
        if alerts.len() > 100 {
            let drain_count = alerts.len() - 100;
            alerts.drain(0..drain_count);
        }
    }
}
