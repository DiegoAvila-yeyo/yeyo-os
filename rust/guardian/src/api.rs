//! YeyoOS Guardian — API HTTP
//! Micro-fase 6.0 — Capa 6: Sistema Inmune

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

#[derive(Clone)]
pub struct AppState {
    pub monitor: Arc<ResourceMonitor>,
    pub heartbeat: Arc<Heartbeat>,
}

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

pub fn create_router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/status", get(status))
        .route("/resources", get(resources))
        .route("/alerts", get(alerts))
        .route("/heartbeat", get(heartbeat_endpoint))
        .with_state(state)
}
