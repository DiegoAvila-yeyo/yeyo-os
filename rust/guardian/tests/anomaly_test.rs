//! Tests para AnomalyDetector — Micro-fase 6.1

use yeyo_guardian::anomaly::{AnomalyDetector, AnomalyLevel};

#[tokio::test]
async fn test_no_anomaly_without_baseline() {
    let detector = AnomalyDetector::new();
    let result = detector.observe("cpu", 99.0).await;
    assert_eq!(result.anomaly_score, 0.0);
    assert_eq!(result.level, AnomalyLevel::Normal);
}

#[tokio::test]
async fn test_baseline_learning() {
    let detector = AnomalyDetector::new();
    for _ in 0..360 {
        detector.observe("cpu", 30.0).await;
    }
    assert!(detector.is_baseline_ready("cpu").await);
}

#[tokio::test]
async fn test_normal_activity_scores_low() {
    let detector = AnomalyDetector::new();
    for i in 0..400 {
        let noise = (i as f64 * 0.1).sin() * 2.0;
        detector.observe("cpu", 30.0 + noise).await;
    }
    let result = detector.observe("cpu", 31.0).await;
    assert!(result.anomaly_score < 0.5, "Score normal debería ser <0.5, got {}", result.anomaly_score);
    assert_eq!(result.level, AnomalyLevel::Normal);
}

#[tokio::test]
async fn test_unusual_activity_scores_high() {
    let detector = AnomalyDetector::new();
    for i in 0..400 {
        let noise = (i as f64 * 0.1).sin() * 2.0;
        detector.observe("cpu", 30.0 + noise).await;
    }
    let result = detector.observe("cpu", 99.0).await;
    assert!(result.anomaly_score > 0.7, "Score anómalo debería ser >0.7, got {}", result.anomaly_score);
    assert!(result.level == AnomalyLevel::Warning || result.level == AnomalyLevel::Critical);
}

#[tokio::test]
async fn test_alert_levels_correct() {
    assert_eq!(AnomalyLevel::from_score(0.0), AnomalyLevel::Normal);
    assert_eq!(AnomalyLevel::from_score(0.3), AnomalyLevel::Normal);
    assert_eq!(AnomalyLevel::from_score(0.5), AnomalyLevel::Normal);
    assert_eq!(AnomalyLevel::from_score(0.51), AnomalyLevel::Info);
    assert_eq!(AnomalyLevel::from_score(0.7), AnomalyLevel::Info);
    assert_eq!(AnomalyLevel::from_score(0.71), AnomalyLevel::Warning);
    assert_eq!(AnomalyLevel::from_score(0.9), AnomalyLevel::Warning);
    assert_eq!(AnomalyLevel::from_score(0.91), AnomalyLevel::Critical);
    assert_eq!(AnomalyLevel::from_score(1.0), AnomalyLevel::Critical);
}

#[tokio::test]
async fn test_analyze_snapshot_returns_all_metrics() {
    let detector = AnomalyDetector::new();
    let results = detector.analyze_snapshot(30.0, 50.0, 40.0, 150.0, 1000.0, 500.0).await;
    assert_eq!(results.len(), 6);
    assert_eq!(results[0].metric, "cpu_usage");
    assert_eq!(results[1].metric, "ram_usage");
    assert_eq!(results[2].metric, "disk_usage");
    assert_eq!(results[3].metric, "process_count");
    assert_eq!(results[4].metric, "network_rx");
    assert_eq!(results[5].metric, "network_tx");
}

#[tokio::test]
async fn test_get_anomalies_filters_normal() {
    let detector = AnomalyDetector::new();
    for _ in 0..10 {
        detector.observe("test_metric", 50.0).await;
    }
    let anomalies = detector.get_anomalies().await;
    assert!(anomalies.is_empty());
}

#[tokio::test]
async fn test_sample_count_increments() {
    let detector = AnomalyDetector::new();
    assert_eq!(detector.get_sample_count("cpu").await, 0);
    detector.observe("cpu", 30.0).await;
    assert_eq!(detector.get_sample_count("cpu").await, 1);
    detector.observe("cpu", 31.0).await;
    assert_eq!(detector.get_sample_count("cpu").await, 2);
}
