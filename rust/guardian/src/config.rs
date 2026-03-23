//! YeyoOS Guardian — Configuración
//! Micro-fase 6.0 — Capa 6: Sistema Inmune

use std::path::PathBuf;

/// Configuración del Guardian Daemon.
#[derive(Debug, Clone)]
pub struct GuardianConfig {
    pub http_port: u16,
    pub log_dir: PathBuf,
    pub heartbeat_interval_secs: u64,
    pub monitor_interval_secs: u64,
    pub cpu_alert_threshold: f32,
    pub ram_alert_threshold: f32,
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
