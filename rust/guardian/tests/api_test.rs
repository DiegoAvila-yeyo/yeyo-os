//! Tests para la API HTTP — Micro-fase 6.0

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
