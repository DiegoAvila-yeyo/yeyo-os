//! YeyoOS Guardian Daemon
//! Micro-fase 6.0 — Capa 6: Sistema Inmune

mod api;
mod config;
mod heartbeat;
mod monitor;
mod anomaly;
mod response;

use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::{info, error};

use api::{AppState, create_router};
use config::GuardianConfig;
use heartbeat::Heartbeat;
use monitor::ResourceMonitor;

#[tokio::main]
async fn main() {
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

    if let Err(e) = tokio::fs::create_dir_all(&config.log_dir).await {
        error!("No se pudo crear directorio de logs: {}", e);
    }

    let state = AppState {
        monitor: monitor.clone(),
        heartbeat: heartbeat.clone(),
    };

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
