//! Tests para AutoResponder — Micro-fase 6.2

use yeyo_guardian::anomaly::AnomalyLevel;
use yeyo_guardian::response::{AutoResponder, ResponseAction};

#[tokio::test]
async fn test_critical_triggers_isolation() {
    let responder = AutoResponder::new();
    let record = responder.respond(
        AnomalyLevel::Critical, "cpu_usage", 0.95, Some("container-abc123"), None,
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
        &AnomalyLevel::Critical, "cpu_usage", 0.95, Some("container-abc"), None,
    );
    assert!(matches!(&actions[0], ResponseAction::CreateSnapshot { .. }));
}

#[tokio::test]
async fn test_critical_pauses_container() {
    let responder = AutoResponder::new();
    let record = responder.respond(
        AnomalyLevel::Critical, "cpu_usage", 0.95, Some("container-abc123"), None,
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
        AnomalyLevel::Warning, "network_rx", 0.75, None, None,
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
        AnomalyLevel::Warning, "network_rx", 0.75, None, Some("192.168.1.100"),
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
        AnomalyLevel::Info, "cpu_usage", 0.55, None, None,
    ).await;
    assert_eq!(record.actions_taken.len(), 1);
    assert!(matches!(&record.actions_taken[0], ResponseAction::LogOnly { .. }));
}

#[tokio::test]
async fn test_normal_no_actions() {
    let responder = AutoResponder::new();
    let record = responder.respond(
        AnomalyLevel::Normal, "cpu_usage", 0.2, None, None,
    ).await;
    assert!(record.actions_taken.is_empty());
}

#[tokio::test]
async fn test_nothing_auto_deleted() {
    let responder = AutoResponder::new();
    let record = responder.respond(
        AnomalyLevel::Critical, "disk_usage", 0.99, Some("container-xyz"), Some("10.0.0.1"),
    ).await;
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
        AnomalyLevel::Critical, "cpu_usage", 0.99, Some("container-abc"), None,
    ).await;
    assert_eq!(record.actions_taken.len(), 1);
    assert!(matches!(&record.actions_taken[0], ResponseAction::LogOnly { .. }));
}
