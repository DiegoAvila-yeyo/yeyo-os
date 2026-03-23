//! YeyoOS Guardian — Detección de Anomalías
//! Micro-fase 6.1 — Capa 6: Sistema Inmune
//!
//! z-score estadístico. Aprende patrones normales y detecta desviaciones.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AnomalyLevel {
    Normal,
    Info,
    Warning,
    Critical,
}

impl AnomalyLevel {
    pub fn from_score(score: f64) -> Self {
        match score {
            s if s > 0.9 => AnomalyLevel::Critical,
            s if s > 0.7 => AnomalyLevel::Warning,
            s if s > 0.5 => AnomalyLevel::Info,
            _ => AnomalyLevel::Normal,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyResult {
    pub metric: String,
    pub value: f64,
    pub mean: f64,
    pub stddev: f64,
    pub z_score: f64,
    pub anomaly_score: f64,
    pub level: AnomalyLevel,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
struct MetricStats {
    values: Vec<f64>,
    max_values: usize,
    baseline_ready: bool,
    min_samples: usize,
}

impl MetricStats {
    fn new(max_values: usize, min_samples: usize) -> Self {
        Self {
            values: Vec::with_capacity(max_values),
            max_values,
            baseline_ready: false,
            min_samples,
        }
    }

    fn push(&mut self, value: f64) {
        self.values.push(value);
        if self.values.len() > self.max_values {
            self.values.remove(0);
        }
        if self.values.len() >= self.min_samples {
            self.baseline_ready = true;
        }
    }

    fn mean(&self) -> f64 {
        if self.values.is_empty() {
            return 0.0;
        }
        self.values.iter().sum::<f64>() / self.values.len() as f64
    }

    fn stddev(&self) -> f64 {
        if self.values.len() < 2 {
            return 0.0;
        }
        let mean = self.mean();
        let variance = self.values.iter()
            .map(|v| (v - mean).powi(2))
            .sum::<f64>() / (self.values.len() - 1) as f64;
        variance.sqrt()
    }

    fn z_score(&self, value: f64) -> f64 {
        let stddev = self.stddev();
        if stddev < f64::EPSILON {
            return 0.0;
        }
        ((value - self.mean()) / stddev).abs()
    }
}

pub struct AnomalyDetector {
    metrics: Arc<RwLock<HashMap<String, MetricStats>>>,
    recent_results: Arc<RwLock<Vec<AnomalyResult>>>,
    max_results: usize,
    samples_per_day: usize,
    min_baseline_samples: usize,
}

impl AnomalyDetector {
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(RwLock::new(HashMap::new())),
            recent_results: Arc::new(RwLock::new(Vec::new())),
            max_results: 1000,
            samples_per_day: 8640,
            min_baseline_samples: 360,
        }
    }

    pub async fn observe(&self, metric: &str, value: f64) -> AnomalyResult {
        let mut metrics = self.metrics.write().await;

        let stats = metrics
            .entry(metric.to_string())
            .or_insert_with(|| MetricStats::new(
                self.samples_per_day,
                self.min_baseline_samples,
            ));

        let mean = stats.mean();
        let stddev = stats.stddev();
        let z_score = stats.z_score(value);

        let anomaly_score = if !stats.baseline_ready {
            0.0
        } else {
            (1.0 - (-z_score / 3.0).exp()).clamp(0.0, 1.0)
        };

        let level = AnomalyLevel::from_score(anomaly_score);

        stats.push(value);

        let result = AnomalyResult {
            metric: metric.to_string(),
            value,
            mean,
            stddev,
            z_score,
            anomaly_score,
            level: level.clone(),
            timestamp: Utc::now(),
        };

        match &level {
            AnomalyLevel::Critical => {
                error!(
                    metric = metric,
                    score = anomaly_score,
                    z = z_score,
                    "🚨 ANOMALÍA CRÍTICA detectada"
                );
            }
            AnomalyLevel::Warning => {
                warn!(
                    metric = metric,
                    score = anomaly_score,
                    z = z_score,
                    "⚠️ Anomalía WARNING detectada"
                );
            }
            AnomalyLevel::Info => {
                info!(
                    metric = metric,
                    score = anomaly_score,
                    "ℹ️ Actividad ligeramente inusual"
                );
            }
            AnomalyLevel::Normal => {}
        }

        let mut results = self.recent_results.write().await;
        results.push(result.clone());
        if results.len() > self.max_results {
            results.remove(0);
        }

        result
    }

    pub async fn analyze_snapshot(
        &self,
        cpu: f64,
        ram: f64,
        disk: f64,
        processes: f64,
        net_rx: f64,
        net_tx: f64,
    ) -> Vec<AnomalyResult> {
        let mut results = Vec::new();
        results.push(self.observe("cpu_usage", cpu).await);
        results.push(self.observe("ram_usage", ram).await);
        results.push(self.observe("disk_usage", disk).await);
        results.push(self.observe("process_count", processes).await);
        results.push(self.observe("network_rx", net_rx).await);
        results.push(self.observe("network_tx", net_tx).await);
        results
    }

    pub async fn is_baseline_ready(&self, metric: &str) -> bool {
        let metrics = self.metrics.read().await;
        metrics.get(metric).map(|s| s.baseline_ready).unwrap_or(false)
    }

    pub async fn get_recent_results(&self) -> Vec<AnomalyResult> {
        self.recent_results.read().await.clone()
    }

    pub async fn get_anomalies(&self) -> Vec<AnomalyResult> {
        self.recent_results.read().await
            .iter()
            .filter(|r| r.level != AnomalyLevel::Normal)
            .cloned()
            .collect()
    }

    pub async fn get_sample_count(&self, metric: &str) -> usize {
        let metrics = self.metrics.read().await;
        metrics.get(metric).map(|s| s.values.len()).unwrap_or(0)
    }
}

impl Default for AnomalyDetector {
    fn default() -> Self {
        Self::new()
    }
}
