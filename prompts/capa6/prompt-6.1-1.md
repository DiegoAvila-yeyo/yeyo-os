## ═══════════════════════════════════════
## MICRO-FASE 6.1 — Guardian Anomaly Detection
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.1-1 [VSCODE] — Detección de anomalías estadística en Guardian

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.1 de Capa 6 (Sistema Inmune): implementar detección de anomalías basada en estadísticas (z-score) dentro del Guardian Daemon.

CONTEXTO:
- Micro-fase 6.0 completada: Guardian Daemon base compilando y con tests
- Guardian ya monitorea CPU, RAM, disco, procesos
- Ahora necesitamos que APRENDA patrones normales y detecte anomalías
- Enfoque estadístico: media, desviación estándar, z-score
- NO necesita ML pesado — eficiente y rápido
- Scoring: 0.0 (normal) a 1.0 (anómalo)
- Alert levels: INFO (>0.5), WARNING (>0.7), CRITICAL (>0.9)
- Aprende comportamiento normal durante las primeras 24h

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo rust/guardian/src/anomaly.rs:

   Ruta: ~/yeyo-os/rust/guardian/src/anomaly.rs
   Contenido:

   //! YeyoOS Guardian — Detección de Anomalías
   //! Micro-fase 6.1 — Capa 6: Sistema Inmune
   //!
   //! Detección de anomalías basada en z-score estadístico.
   //! Aprende patrones normales de comportamiento y detecta desviaciones.
   //! Sin ML pesado: usa media y desviación estándar.

   use chrono::{DateTime, Utc};
   use serde::{Deserialize, Serialize};
   use std::collections::HashMap;
   use std::sync::Arc;
   use tokio::sync::RwLock;
   use tracing::{info, warn, error};

   // ═══════════════════════════════════
   // TIPOS DE DATOS
   // ═══════════════════════════════════

   /// Nivel de alerta basado en anomaly score.
   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub enum AnomalyLevel {
       /// Score <= 0.5 — Comportamiento normal
       Normal,
       /// Score > 0.5 — Comportamiento ligeramente inusual
       Info,
       /// Score > 0.7 — Comportamiento sospechoso
       Warning,
       /// Score > 0.9 — Comportamiento altamente anómalo
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

   /// Resultado del análisis de anomalías para una métrica.
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

   /// Estadísticas acumuladas para una métrica.
   #[derive(Debug, Clone)]
   struct MetricStats {
       /// Todos los valores observados (ventana deslizante)
       values: Vec<f64>,
       /// Máximo de valores a mantener (24h de muestras a 10s = 8640)
       max_values: usize,
       /// ¿La baseline está lista? (necesita mínimo min_samples)
       baseline_ready: bool,
       /// Mínimo de muestras para considerar baseline válida
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

       /// Agrega un valor y mantiene la ventana deslizante.
       fn push(&mut self, value: f64) {
           self.values.push(value);
           if self.values.len() > self.max_values {
               self.values.remove(0);
           }
           if self.values.len() >= self.min_samples {
               self.baseline_ready = true;
           }
       }

       /// Calcula la media.
       fn mean(&self) -> f64 {
           if self.values.is_empty() {
               return 0.0;
           }
           self.values.iter().sum::<f64>() / self.values.len() as f64
       }

       /// Calcula la desviación estándar.
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

       /// Calcula el z-score para un valor dado.
       fn z_score(&self, value: f64) -> f64 {
           let stddev = self.stddev();
           if stddev < f64::EPSILON {
               return 0.0;
           }
           ((value - self.mean()) / stddev).abs()
       }
   }

   // ═══════════════════════════════════
   // DETECTOR DE ANOMALÍAS
   // ═══════════════════════════════════

   pub struct AnomalyDetector {
       /// Estadísticas por métrica
       metrics: Arc<RwLock<HashMap<String, MetricStats>>>,
       /// Resultados recientes de análisis
       recent_results: Arc<RwLock<Vec<AnomalyResult>>>,
       /// Máximo de resultados a mantener
       max_results: usize,
       /// Muestras por 24h (a 10s de intervalo = 8640)
       samples_per_day: usize,
       /// Mínimo de muestras para baseline
       min_baseline_samples: usize,
   }

   impl AnomalyDetector {
       pub fn new() -> Self {
           Self {
               metrics: Arc::new(RwLock::new(HashMap::new())),
               recent_results: Arc::new(RwLock::new(Vec::new())),
               max_results: 1000,
               samples_per_day: 8640,
               min_baseline_samples: 360, // 1 hora de muestras mínimo
           }
       }

       /// Registra un valor para una métrica y analiza anomalías.
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

           // Convertir z-score a anomaly_score (0.0 a 1.0)
           // Sigmoid-like: score = 1 - e^(-z/3)
           let anomaly_score = if !stats.baseline_ready {
               0.0 // Sin baseline, no reportar anomalías
           } else {
               (1.0 - (-z_score / 3.0).exp()).clamp(0.0, 1.0)
           };

           let level = AnomalyLevel::from_score(anomaly_score);

           // Registrar el valor DESPUÉS de calcular z-score
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

           // Log según nivel
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

           // Almacenar resultado
           let mut results = self.recent_results.write().await;
           results.push(result.clone());
           if results.len() > self.max_results {
               results.remove(0);
           }

           result
       }

       /// Analiza un snapshot completo de recursos.
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

       /// Verifica si la baseline está lista para una métrica.
       pub async fn is_baseline_ready(&self, metric: &str) -> bool {
           let metrics = self.metrics.read().await;
           metrics.get(metric).map(|s| s.baseline_ready).unwrap_or(false)
       }

       /// Retorna resultados recientes.
       pub async fn get_recent_results(&self) -> Vec<AnomalyResult> {
           self.recent_results.read().await.clone()
       }

       /// Retorna solo resultados con nivel > Normal.
       pub async fn get_anomalies(&self) -> Vec<AnomalyResult> {
           self.recent_results.read().await
               .iter()
               .filter(|r| r.level != AnomalyLevel::Normal)
               .cloned()
               .collect()
       }

       /// Retorna el número de muestras para una métrica.
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

2. Crear archivo rust/guardian/tests/anomaly_test.rs:

   Ruta: ~/yeyo-os/rust/guardian/tests/anomaly_test.rs
   Contenido:

   //! Tests para AnomalyDetector — Micro-fase 6.1
   //! Verifica baseline, scoring, niveles de alerta.

   use yeyo_guardian::anomaly::{AnomalyDetector, AnomalyLevel};

   #[tokio::test]
   async fn test_no_anomaly_without_baseline() {
       let detector = AnomalyDetector::new();

       // Sin baseline, score debe ser 0.0
       let result = detector.observe("cpu", 99.0).await;
       assert_eq!(result.anomaly_score, 0.0);
       assert_eq!(result.level, AnomalyLevel::Normal);
   }

   #[tokio::test]
   async fn test_baseline_learning() {
       let detector = AnomalyDetector::new();

       // Alimentar 360 muestras normales (1 hora)
       for _ in 0..360 {
           detector.observe("cpu", 30.0).await;
       }

       assert!(detector.is_baseline_ready("cpu").await);
   }

   #[tokio::test]
   async fn test_normal_activity_scores_low() {
       let detector = AnomalyDetector::new();

       // Baseline: CPU estable alrededor de 30%
       for i in 0..400 {
           let noise = (i as f64 * 0.1).sin() * 2.0;
           detector.observe("cpu", 30.0 + noise).await;
       }

       // Valor normal: debería tener score bajo
       let result = detector.observe("cpu", 31.0).await;
       assert!(result.anomaly_score < 0.5, "Score normal debería ser <0.5, got {}", result.anomaly_score);
       assert_eq!(result.level, AnomalyLevel::Normal);
   }

   #[tokio::test]
   async fn test_unusual_activity_scores_high() {
       let detector = AnomalyDetector::new();

       // Baseline: CPU estable alrededor de 30%
       for i in 0..400 {
           let noise = (i as f64 * 0.1).sin() * 2.0;
           detector.observe("cpu", 30.0 + noise).await;
       }

       // Valor extremo: CPU al 99% debería ser anómalo
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

       let results = detector.analyze_snapshot(
           30.0, 50.0, 40.0, 150.0, 1000.0, 500.0,
       ).await;

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

       // Sin baseline, todo es Normal
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

3. Actualizar rust/guardian/src/lib.rs para incluir anomaly:

   Agregar al archivo ~/yeyo-os/rust/guardian/src/lib.rs:

   pub mod anomaly;

4. Ejecutar tests:
   cd ~/yeyo-os/rust/guardian
   cargo test 2>&1

VERIFICAR:
- [ ] Archivo rust/guardian/src/anomaly.rs existe con AnomalyDetector
- [ ] Archivo rust/guardian/tests/anomaly_test.rs existe
- [ ] AnomalyLevel: Normal, Info, Warning, Critical
- [ ] Sin baseline (< 360 muestras), score siempre 0.0
- [ ] Actividad normal (CPU ~30%) → score bajo (<0.5)
- [ ] Actividad anómala (CPU 99% cuando normal es 30%) → score alto (>0.7)
- [ ] analyze_snapshot retorna 6 métricas
- [ ] TODOS los tests pasan

SI FALLA:
- z-score siempre 0: verificar que stddev no sea 0 (agregar variación en datos)
- Baseline nunca ready: verificar min_baseline_samples (360)
- Import error: verificar que lib.rs incluya `pub mod anomaly;`

NO HACER:
- No usar modelos ML reales (mantener enfoque estadístico)
- No conectar con auto-response aún (eso es 6.2)
- No modificar el monitor existente

GATE: AnomalyDetector aprende baseline en 360 muestras, valores normales score <0.5, valores anómalos score >0.7, niveles de alerta correctos, todos los tests pasan.
```
