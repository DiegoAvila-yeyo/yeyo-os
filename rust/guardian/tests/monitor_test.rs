//! Tests para ResourceMonitor — Micro-fase 6.0

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
    config.cpu_alert_threshold = 0.1;
    config.ram_alert_threshold = 0.1;
    config.disk_alert_threshold = 0.1;

    let monitor = ResourceMonitor::new(config);
    monitor.take_snapshot().await;

    let alerts = monitor.get_alerts().await;
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

    for _ in 0..50 {
        monitor.take_snapshot().await;
    }

    monitor.cleanup_alerts().await;

    let alerts = monitor.get_alerts().await;
    assert!(alerts.len() <= 100);
}
