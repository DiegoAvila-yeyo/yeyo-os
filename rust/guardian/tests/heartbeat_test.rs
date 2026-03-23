//! Tests para Heartbeat — Micro-fase 6.0

use yeyo_guardian::heartbeat::Heartbeat;

#[tokio::test]
async fn test_heartbeat_initial_state() {
    let hb = Heartbeat::new();
    assert_eq!(hb.get_beat_count().await, 0);
    assert!(hb.get_latest().await.is_none());
}

#[tokio::test]
async fn test_heartbeat_increments() {
    let hb = Heartbeat::new();
    hb.beat().await;
    assert_eq!(hb.get_beat_count().await, 1);
    hb.beat().await;
    assert_eq!(hb.get_beat_count().await, 2);
    hb.beat().await;
    assert_eq!(hb.get_beat_count().await, 3);
}

#[tokio::test]
async fn test_heartbeat_stores_latest() {
    let hb = Heartbeat::new();
    let info = hb.beat().await;
    assert_eq!(info.status, "alive");
    assert_eq!(info.beat_count, 1);

    let latest = hb.get_latest().await.unwrap();
    assert_eq!(latest.beat_count, 1);
}

#[tokio::test]
async fn test_heartbeat_uptime_increases() {
    let hb = Heartbeat::new();
    let first = hb.beat().await;
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    let second = hb.beat().await;
    assert!(second.uptime_secs >= first.uptime_secs);
}
