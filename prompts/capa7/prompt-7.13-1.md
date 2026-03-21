## ═══════════════════════════════════════
## MICRO-FASE 7.13 — YEYO Observer
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.13-1 [VSCODE] — Crear sistema de monitoreo a largo plazo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.13 de Capa 7 (Evolución): crear el YEYO Observer, un sistema de monitoreo a largo plazo que vigila la salud del sistema.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.12
- Observer recolecta métricas a lo largo del tiempo
- Dashboard de tendencias: memoria, GPU, salud general
- Alertas proactivas: detecta degradación ANTES de que sea problema
- Reporte semanal de salud
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/observer.py:

   Ruta: ~/yeyo-os/src/core/observer.py
   Contenido:

   """
   YeyoOS — YEYO Observer
   Micro-fase 7.13 — Capa 7: Evolución

   Sistema de monitoreo a largo plazo.
   Recolecta métricas, detecta tendencias,
   alerta antes de que los problemas ocurran.
   """

   import json
   import logging
   import statistics
   from collections import deque
   from datetime import datetime, timedelta
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.core.observer")


   class MetricSnapshot(BaseModel):
       """Snapshot de métricas del sistema en un momento."""
       timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
       cpu_pct: float = Field(ge=0.0, le=100.0)
       memory_rss_mb: float = Field(ge=0.0)
       memory_total_mb: float = Field(ge=0.0)
       gpu_vram_used_mb: int = Field(ge=0)
       gpu_vram_total_mb: int = Field(default=3072, ge=0)
       gpu_utilization_pct: float = Field(ge=0.0, le=100.0)
       disk_used_pct: float = Field(ge=0.0, le=100.0)
       cache_hit_rate: float = Field(ge=0.0, le=1.0)
       active_sessions: int = Field(ge=0)
       ollama_latency_ms: float = Field(ge=0.0)
       error_count: int = Field(ge=0)


   class TrendAnalysis(BaseModel):
       """Análisis de tendencia de una métrica."""
       metric_name: str
       direction: str = Field(pattern="^(increasing|decreasing|stable)$")
       rate_per_hour: float
       current_value: float
       avg_value: float
       min_value: float
       max_value: float
       stddev: float
       data_points: int


   class Alert(BaseModel):
       """Alerta generada por el observer."""
       alert_id: str = ""
       severity: str = Field(pattern="^(critical|warning|info)$")
       category: str
       message: str
       metric_name: str = ""
       current_value: float = 0.0
       threshold: float = 0.0
       trend: Optional[TrendAnalysis] = None
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
       acknowledged: bool = False


   class WeeklyReport(BaseModel):
       """Reporte semanal de salud."""
       period_start: str
       period_end: str
       total_snapshots: int
       avg_cpu_pct: float
       avg_memory_mb: float
       avg_gpu_utilization: float
       avg_cache_hit_rate: float
       total_errors: int
       alerts_generated: int
       trends: list[TrendAnalysis] = []
       health_score: float = Field(ge=0.0, le=100.0)
       summary: str = ""


   # Thresholds para alertas
   ALERT_THRESHOLDS = {
       "memory_rss_mb": {"warning": 12000, "critical": 14000},
       "gpu_vram_used_mb": {"warning": 2800, "critical": 3000},
       "disk_used_pct": {"warning": 85.0, "critical": 95.0},
       "cpu_pct": {"warning": 90.0, "critical": 98.0},
       "cache_hit_rate": {"warning": 0.60, "critical": 0.40},
       "ollama_latency_ms": {"warning": 5000, "critical": 10000},
       "error_count": {"warning": 10, "critical": 50},
   }


   class YeyoObserver:
       """Sistema de monitoreo a largo plazo de YeyoOS."""

       MAX_HISTORY_SIZE = 10080  # 1 semana a 1 snapshot/minuto

       def __init__(self, data_dir: str = "data/observer"):
           self.data_dir = Path(data_dir)
           self.data_dir.mkdir(parents=True, exist_ok=True)
           self._history: deque[MetricSnapshot] = deque(maxlen=self.MAX_HISTORY_SIZE)
           self._alerts: list[Alert] = []
           self._alert_counter = 0

       def record_snapshot(self, snapshot: MetricSnapshot) -> list[Alert]:
           """Registra un snapshot y genera alertas si es necesario."""
           self._history.append(snapshot)
           new_alerts = self._check_thresholds(snapshot)
           self._alerts.extend(new_alerts)
           return new_alerts

       def _check_thresholds(self, snapshot: MetricSnapshot) -> list[Alert]:
           """Verifica thresholds y genera alertas."""
           alerts = []
           checks = {
               "memory_rss_mb": snapshot.memory_rss_mb,
               "gpu_vram_used_mb": snapshot.gpu_vram_used_mb,
               "disk_used_pct": snapshot.disk_used_pct,
               "cpu_pct": snapshot.cpu_pct,
               "ollama_latency_ms": snapshot.ollama_latency_ms,
               "error_count": snapshot.error_count,
           }

           for metric, value in checks.items():
               thresholds = ALERT_THRESHOLDS.get(metric, {})
               critical = thresholds.get("critical")
               warning = thresholds.get("warning")

               if critical is not None and value >= critical:
                   self._alert_counter += 1
                   alerts.append(Alert(
                       alert_id=f"alert-{self._alert_counter}",
                       severity="critical",
                       category=metric.split("_")[0],
                       message=f"{metric} en nivel crítico: {value}",
                       metric_name=metric,
                       current_value=value,
                       threshold=critical,
                   ))
               elif warning is not None and value >= warning:
                   self._alert_counter += 1
                   alerts.append(Alert(
                       alert_id=f"alert-{self._alert_counter}",
                       severity="warning",
                       category=metric.split("_")[0],
                       message=f"{metric} en nivel warning: {value}",
                       metric_name=metric,
                       current_value=value,
                       threshold=warning,
                   ))

           # Cache hit rate (umbral invertido — alerta cuando BAJA)
           cache_thresholds = ALERT_THRESHOLDS.get("cache_hit_rate", {})
           if snapshot.cache_hit_rate <= cache_thresholds.get("critical", 0):
               self._alert_counter += 1
               alerts.append(Alert(
                   alert_id=f"alert-{self._alert_counter}",
                   severity="critical",
                   category="cache",
                   message=f"Cache hit rate crítico: {snapshot.cache_hit_rate:.0%}",
                   metric_name="cache_hit_rate",
                   current_value=snapshot.cache_hit_rate,
                   threshold=cache_thresholds["critical"],
               ))
           elif snapshot.cache_hit_rate <= cache_thresholds.get("warning", 0):
               self._alert_counter += 1
               alerts.append(Alert(
                   alert_id=f"alert-{self._alert_counter}",
                   severity="warning",
                   category="cache",
                   message=f"Cache hit rate bajo: {snapshot.cache_hit_rate:.0%}",
                   metric_name="cache_hit_rate",
                   current_value=snapshot.cache_hit_rate,
                   threshold=cache_thresholds["warning"],
               ))

           return alerts

       def analyze_trend(self, metric_name: str, window_hours: int = 1) -> Optional[TrendAnalysis]:
           """Analiza tendencia de una métrica en una ventana de tiempo."""
           if len(self._history) < 3:
               return None

           values = []
           now = datetime.now()
           cutoff = now - timedelta(hours=window_hours)

           for snapshot in self._history:
               ts = datetime.fromisoformat(snapshot.timestamp)
               if ts >= cutoff:
                   value = getattr(snapshot, metric_name, None)
                   if value is not None:
                       values.append((ts, float(value)))

           if len(values) < 3:
               return None

           numeric_values = [v for _, v in values]
           time_span_hours = (values[-1][0] - values[0][0]).total_seconds() / 3600
           if time_span_hours <= 0:
               time_span_hours = 0.001

           first_half = numeric_values[:len(numeric_values) // 2]
           second_half = numeric_values[len(numeric_values) // 2:]
           avg_first = statistics.mean(first_half) if first_half else 0
           avg_second = statistics.mean(second_half) if second_half else 0

           diff = avg_second - avg_first
           rate = diff / time_span_hours

           if abs(rate) < 0.01 * statistics.mean(numeric_values):
               direction = "stable"
           elif rate > 0:
               direction = "increasing"
           else:
               direction = "decreasing"

           return TrendAnalysis(
               metric_name=metric_name,
               direction=direction,
               rate_per_hour=round(rate, 4),
               current_value=numeric_values[-1],
               avg_value=round(statistics.mean(numeric_values), 4),
               min_value=min(numeric_values),
               max_value=max(numeric_values),
               stddev=round(statistics.stdev(numeric_values), 4) if len(numeric_values) > 1 else 0.0,
               data_points=len(numeric_values),
           )

       def detect_degradation(self) -> list[Alert]:
           """Detecta tendencias de degradación antes de que sean problemas."""
           degradation_alerts = []
           metrics_to_watch = [
               "memory_rss_mb", "gpu_vram_used_mb", "cpu_pct",
               "ollama_latency_ms", "error_count",
           ]

           for metric in metrics_to_watch:
               trend = self.analyze_trend(metric, window_hours=6)
               if trend and trend.direction == "increasing":
                   threshold = ALERT_THRESHOLDS.get(metric, {}).get("warning", float('inf'))
                   # Si la tendencia proyecta alcanzar el threshold en <12h
                   projected = trend.current_value + (trend.rate_per_hour * 12)
                   if projected >= threshold and trend.current_value < threshold:
                       self._alert_counter += 1
                       alert = Alert(
                           alert_id=f"alert-{self._alert_counter}",
                           severity="warning",
                           category="degradation",
                           message=f"{metric} trending up: proyección {projected:.0f} en 12h (threshold: {threshold})",
                           metric_name=metric,
                           current_value=trend.current_value,
                           threshold=threshold,
                           trend=trend,
                       )
                       degradation_alerts.append(alert)

           return degradation_alerts

       def generate_weekly_report(self) -> WeeklyReport:
           """Genera reporte semanal de salud."""
           if not self._history:
               return WeeklyReport(
                   period_start=datetime.now().isoformat(),
                   period_end=datetime.now().isoformat(),
                   total_snapshots=0,
                   avg_cpu_pct=0, avg_memory_mb=0,
                   avg_gpu_utilization=0, avg_cache_hit_rate=0,
                   total_errors=0, alerts_generated=0,
                   health_score=0, summary="Sin datos",
               )

           snapshots = list(self._history)
           cpu_vals = [s.cpu_pct for s in snapshots]
           mem_vals = [s.memory_rss_mb for s in snapshots]
           gpu_vals = [s.gpu_utilization_pct for s in snapshots]
           cache_vals = [s.cache_hit_rate for s in snapshots]
           total_errors = sum(s.error_count for s in snapshots)

           # Health score basado en métricas promedio
           health = 100.0
           avg_cache = statistics.mean(cache_vals)
           if avg_cache < 0.80:
               health -= (0.80 - avg_cache) * 50
           avg_cpu = statistics.mean(cpu_vals)
           if avg_cpu > 80:
               health -= (avg_cpu - 80) * 1
           if total_errors > 100:
               health -= min(20, total_errors / 10)

           health = max(0.0, round(health, 2))

           # Trends
           trends = []
           for metric in ["memory_rss_mb", "cpu_pct", "gpu_vram_used_mb"]:
               trend = self.analyze_trend(metric, window_hours=168)  # 1 semana
               if trend:
                   trends.append(trend)

           # Summary
           if health >= 90:
               summary = "🟢 Excelente: YeyoOS funciona como un reloj suizo"
           elif health >= 75:
               summary = "🟡 Bueno: rendimiento aceptable con áreas de mejora"
           elif health >= 50:
               summary = "🟠 Regular: se requiere atención en varias áreas"
           else:
               summary = "🔴 Crítico: se requiere intervención inmediata"

           return WeeklyReport(
               period_start=snapshots[0].timestamp,
               period_end=snapshots[-1].timestamp,
               total_snapshots=len(snapshots),
               avg_cpu_pct=round(avg_cpu, 2),
               avg_memory_mb=round(statistics.mean(mem_vals), 2),
               avg_gpu_utilization=round(statistics.mean(gpu_vals), 2),
               avg_cache_hit_rate=round(avg_cache, 4),
               total_errors=total_errors,
               alerts_generated=len(self._alerts),
               trends=trends,
               health_score=health,
               summary=summary,
           )

       def get_alerts(self, unacknowledged_only: bool = False) -> list[Alert]:
           if unacknowledged_only:
               return [a for a in self._alerts if not a.acknowledged]
           return list(self._alerts)

       def acknowledge_alert(self, alert_id: str) -> bool:
           for alert in self._alerts:
               if alert.alert_id == alert_id:
                   alert.acknowledged = True
                   return True
           return False

       @property
       def snapshot_count(self) -> int:
           return len(self._history)

2. Crear archivo tests/unit/core/test_observer.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_observer.py
   Contenido:

   """Tests para YEYO Observer — Micro-fase 7.13"""

   import pytest
   from datetime import datetime, timedelta
   from src.core.observer import (
       YeyoObserver, MetricSnapshot, Alert,
       ALERT_THRESHOLDS, TrendAnalysis,
   )


   def _good_snapshot(**kwargs) -> MetricSnapshot:
       defaults = dict(
           cpu_pct=30.0, memory_rss_mb=4000.0, memory_total_mb=16000.0,
           gpu_vram_used_mb=1500, gpu_utilization_pct=50.0,
           disk_used_pct=40.0, cache_hit_rate=0.90,
           active_sessions=1, ollama_latency_ms=200.0, error_count=0,
       )
       defaults.update(kwargs)
       return MetricSnapshot(**defaults)


   def _bad_snapshot(**kwargs) -> MetricSnapshot:
       defaults = dict(
           cpu_pct=95.0, memory_rss_mb=15000.0, memory_total_mb=16000.0,
           gpu_vram_used_mb=3050, gpu_utilization_pct=99.0,
           disk_used_pct=96.0, cache_hit_rate=0.30,
           active_sessions=10, ollama_latency_ms=12000.0, error_count=100,
       )
       defaults.update(kwargs)
       return MetricSnapshot(**defaults)


   class TestYeyoObserver:
       """Tests para YeyoObserver."""

       def setup_method(self):
           self.observer = YeyoObserver(data_dir="/tmp/yeyo-observer-test")

       def test_record_snapshot(self):
           alerts = self.observer.record_snapshot(_good_snapshot())
           assert self.observer.snapshot_count == 1
           assert len(alerts) == 0

       def test_bad_snapshot_generates_alerts(self):
           alerts = self.observer.record_snapshot(_bad_snapshot())
           assert len(alerts) > 0

       def test_critical_memory_alert(self):
           alerts = self.observer.record_snapshot(_good_snapshot(memory_rss_mb=15000))
           critical = [a for a in alerts if a.severity == "critical"]
           assert len(critical) > 0

       def test_warning_cpu_alert(self):
           alerts = self.observer.record_snapshot(_good_snapshot(cpu_pct=92.0))
           warnings = [a for a in alerts if a.severity == "warning"]
           assert len(warnings) > 0

       def test_critical_disk_alert(self):
           alerts = self.observer.record_snapshot(_good_snapshot(disk_used_pct=96.0))
           critical = [a for a in alerts if a.severity == "critical"]
           assert len(critical) > 0

       def test_low_cache_alert(self):
           alerts = self.observer.record_snapshot(_good_snapshot(cache_hit_rate=0.35))
           cache_alerts = [a for a in alerts if a.category == "cache"]
           assert len(cache_alerts) > 0

       def test_trend_analysis_stable(self):
           for _ in range(10):
               self.observer.record_snapshot(_good_snapshot(memory_rss_mb=4000.0))
           trend = self.observer.analyze_trend("memory_rss_mb", window_hours=24)
           if trend:
               assert trend.direction == "stable"

       def test_trend_analysis_increasing(self):
           now = datetime.now()
           for i in range(20):
               snapshot = _good_snapshot(memory_rss_mb=4000.0 + i * 100)
               snapshot.timestamp = (now + timedelta(minutes=i * 3)).isoformat()
               self.observer._history.append(snapshot)
           trend = self.observer.analyze_trend("memory_rss_mb", window_hours=24)
           assert trend is not None
           assert trend.direction == "increasing"

       def test_trend_analysis_insufficient_data(self):
           self.observer.record_snapshot(_good_snapshot())
           trend = self.observer.analyze_trend("memory_rss_mb")
           assert trend is None

       def test_weekly_report_no_data(self):
           report = self.observer.generate_weekly_report()
           assert report.total_snapshots == 0
           assert report.summary == "Sin datos"

       def test_weekly_report_healthy(self):
           for _ in range(100):
               self.observer.record_snapshot(_good_snapshot())
           report = self.observer.generate_weekly_report()
           assert report.total_snapshots == 100
           assert report.health_score >= 75.0
           assert "🟢" in report.summary or "🟡" in report.summary

       def test_weekly_report_unhealthy(self):
           for _ in range(100):
               self.observer.record_snapshot(_good_snapshot(
                   cache_hit_rate=0.30, cpu_pct=95.0, error_count=50,
               ))
           report = self.observer.generate_weekly_report()
           assert report.health_score < 75.0

       def test_acknowledge_alert(self):
           self.observer.record_snapshot(_bad_snapshot())
           alerts = self.observer.get_alerts()
           assert len(alerts) > 0
           result = self.observer.acknowledge_alert(alerts[0].alert_id)
           assert result is True
           unack = self.observer.get_alerts(unacknowledged_only=True)
           assert alerts[0].alert_id not in [a.alert_id for a in unack]

       def test_thresholds_defined(self):
           assert "memory_rss_mb" in ALERT_THRESHOLDS
           assert "gpu_vram_used_mb" in ALERT_THRESHOLDS
           assert "cache_hit_rate" in ALERT_THRESHOLDS

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_observer.py -v

VERIFICAR:
- [ ] Archivo src/core/observer.py existe con YeyoObserver
- [ ] Snapshots registrados con métricas completas
- [ ] Alertas generadas al superar thresholds
- [ ] Trend analysis: increasing/decreasing/stable
- [ ] Degradation detection: proyecta tendencias futuras
- [ ] Weekly report con health score y summary
- [ ] Alert acknowledge funciona
- [ ] TODOS los tests pasan

NO HACER:
- No ejecutar monitoring real en tests
- No acceder a hardware en tests unitarios

GATE: Observer recolecta métricas, analiza tendencias, genera alertas de degradación, reporte semanal, todos los tests pasan.
```
