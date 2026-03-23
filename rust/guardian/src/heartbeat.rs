//! YeyoOS Guardian — Heartbeat
//! Micro-fase 6.0 — Capa 6: Sistema Inmune

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::debug;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeartbeatInfo {
    pub timestamp: DateTime<Utc>,
    pub uptime_secs: u64,
    pub beat_count: u64,
    pub status: String,
}

pub struct Heartbeat {
    start_time: DateTime<Utc>,
    beat_count: Arc<RwLock<u64>>,
    latest: Arc<RwLock<Option<HeartbeatInfo>>>,
}

impl Heartbeat {
    pub fn new() -> Self {
        Self {
            start_time: Utc::now(),
            beat_count: Arc::new(RwLock::new(0)),
            latest: Arc::new(RwLock::new(None)),
        }
    }

    pub async fn beat(&self) -> HeartbeatInfo {
        let mut count = self.beat_count.write().await;
        *count += 1;

        let now = Utc::now();
        let uptime = (now - self.start_time).num_seconds() as u64;

        let info = HeartbeatInfo {
            timestamp: now,
            uptime_secs: uptime,
            beat_count: *count,
            status: "alive".to_string(),
        };

        let mut latest = self.latest.write().await;
        *latest = Some(info.clone());

        debug!(beat = *count, uptime = uptime, "Guardian heartbeat");

        info
    }

    pub async fn get_latest(&self) -> Option<HeartbeatInfo> {
        self.latest.read().await.clone()
    }

    pub async fn get_beat_count(&self) -> u64 {
        *self.beat_count.read().await
    }
}

impl Default for Heartbeat {
    fn default() -> Self {
        Self::new()
    }
}
