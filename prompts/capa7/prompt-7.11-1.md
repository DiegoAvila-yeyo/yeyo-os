## ═══════════════════════════════════════
## MICRO-FASE 7.11 — Performance Optimization
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.11-1 [VSCODE] — Crear sistema de optimización de rendimiento

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.11 de Capa 7 (Evolución): optimización final de rendimiento en todas las capas del sistema.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.10
- Profiling de bottlenecks en todo el sistema
- Targets: cache hit rate >80%, DB queries <50ms, frontend <3s, GPU idle mínimo
- Verificar Redis, GPU scheduler, memoria por tiers, queries lentas
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/optimizer.py:

   Ruta: ~/yeyo-os/src/core/optimizer.py
   Contenido:

   """
   YeyoOS — Performance Optimizer
   Micro-fase 7.11 — Capa 7: Evolución

   Optimización final de rendimiento en todas las capas.
   Targets: cache >80%, DB <50ms, frontend <3s, GPU idle mínimo.
   """

   import asyncio
   import logging
   import time
   from datetime import datetime
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.core.optimizer")


   class PerformanceMetrics(BaseModel):
       """Métricas de rendimiento del sistema."""
       cache_hit_rate: float = Field(ge=0.0, le=1.0)
       cache_total_keys: int = Field(ge=0)
       db_avg_query_ms: float = Field(ge=0.0)
       db_slow_queries: int = Field(ge=0)
       db_missing_indexes: list[str] = []
       gpu_utilization_pct: float = Field(ge=0.0, le=100.0)
       gpu_idle_pct: float = Field(ge=0.0, le=100.0)
       gpu_vram_used_mb: int = Field(ge=0)
       gpu_vram_total_mb: int = Field(ge=0)
       memory_rss_mb: float = Field(ge=0.0)
       memory_tier_hot_pct: float = Field(ge=0.0, le=100.0)
       memory_tier_warm_pct: float = Field(ge=0.0, le=100.0)
       memory_tier_cold_pct: float = Field(ge=0.0, le=100.0)
       frontend_load_time_ms: float = Field(ge=0.0)
       frontend_bundle_size_kb: float = Field(ge=0.0)
       timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


   class OptimizationSuggestion(BaseModel):
       """Sugerencia de optimización."""
       category: str
       severity: str = Field(pattern="^(critical|warning|info)$")
       message: str
       current_value: str = ""
       target_value: str = ""
       action: str = ""


   class OptimizationReport(BaseModel):
       """Reporte de optimización."""
       metrics: PerformanceMetrics
       suggestions: list[OptimizationSuggestion] = []
       score: float = Field(ge=0.0, le=100.0)
       passed: bool = False
       timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


   # Targets de rendimiento
   PERFORMANCE_TARGETS = {
       "cache_hit_rate": 0.80,
       "db_avg_query_ms": 50.0,
       "gpu_idle_pct_max": 30.0,
       "frontend_load_time_ms": 3000.0,
       "memory_rss_max_mb": 4096.0,
   }


   class PerformanceOptimizer:
       """Optimizador de rendimiento de YeyoOS."""

       def __init__(self):
           self._metrics_history: list[PerformanceMetrics] = []

       async def profile_cache(self) -> dict:
           """Perfila rendimiento de Redis cache."""
           try:
               import redis
               r = redis.Redis(host='localhost', port=6379, decode_responses=True)
               info = r.info("stats")
               hits = info.get("keyspace_hits", 0)
               misses = info.get("keyspace_misses", 0)
               total = hits + misses
               hit_rate = hits / max(total, 1)

               db_info = r.info("keyspace")
               total_keys = sum(
                   v.get("keys", 0) for v in db_info.values() if isinstance(v, dict)
               )

               return {
                   "hit_rate": round(hit_rate, 4),
                   "total_keys": total_keys,
                   "hits": hits,
                   "misses": misses,
               }
           except Exception as e:
               logger.warning(f"Error profiling cache: {e}")
               return {"hit_rate": 0.0, "total_keys": 0, "hits": 0, "misses": 0}

       async def profile_database(self) -> dict:
           """Perfila rendimiento de PostgreSQL."""
           try:
               import asyncpg
               conn = await asyncpg.connect(
                   host='localhost', port=5432,
                   user='yeyo', database='yeyo_os',
               )

               # Query promedio
               rows = await conn.fetch("""
                   SELECT mean_exec_time, query
                   FROM pg_stat_statements
                   ORDER BY mean_exec_time DESC
                   LIMIT 20
               """)

               slow_queries = [
                   r for r in rows if r["mean_exec_time"] > PERFORMANCE_TARGETS["db_avg_query_ms"]
               ]

               # Indexes faltantes
               missing_indexes = await conn.fetch("""
                   SELECT schemaname, tablename, attname
                   FROM pg_stats
                   WHERE n_distinct > 100 AND tablename NOT LIKE 'pg_%'
                   LIMIT 10
               """)

               avg_time = sum(r["mean_exec_time"] for r in rows) / max(len(rows), 1)

               await conn.close()

               return {
                   "avg_query_ms": round(avg_time, 2),
                   "slow_queries": len(slow_queries),
                   "missing_indexes": [f"{r['tablename']}.{r['attname']}" for r in missing_indexes],
               }
           except Exception as e:
               logger.warning(f"Error profiling database: {e}")
               return {"avg_query_ms": 0.0, "slow_queries": 0, "missing_indexes": []}

       async def profile_gpu(self) -> dict:
           """Perfila uso de GPU."""
           try:
               import subprocess
               result = subprocess.run(
                   ["nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total",
                    "--format=csv,noheader,nounits"],
                   capture_output=True, text=True, timeout=10,
               )
               if result.returncode == 0:
                   parts = result.stdout.strip().split(', ')
                   gpu_util = float(parts[0])
                   vram_used = int(parts[2])
                   vram_total = int(parts[3])
                   return {
                       "utilization_pct": gpu_util,
                       "idle_pct": 100.0 - gpu_util,
                       "vram_used_mb": vram_used,
                       "vram_total_mb": vram_total,
                   }
           except Exception as e:
               logger.warning(f"Error profiling GPU: {e}")
           return {"utilization_pct": 0.0, "idle_pct": 100.0, "vram_used_mb": 0, "vram_total_mb": 3072}

       async def profile_memory(self) -> dict:
           """Perfila uso de memoria del sistema."""
           try:
               import psutil
               process = psutil.Process()
               rss_mb = process.memory_info().rss / (1024 * 1024)
               return {"rss_mb": round(rss_mb, 2)}
           except Exception:
               return {"rss_mb": 0.0}

       async def profile_frontend(self) -> dict:
           """Perfila rendimiento del frontend."""
           try:
               import httpx
               start = time.time()
               async with httpx.AsyncClient(timeout=10.0) as client:
                   resp = await client.get("http://localhost:8000")
                   load_time_ms = (time.time() - start) * 1000
                   return {
                       "load_time_ms": round(load_time_ms, 2),
                       "bundle_size_kb": len(resp.content) / 1024,
                   }
           except Exception as e:
               logger.warning(f"Error profiling frontend: {e}")
               return {"load_time_ms": 0.0, "bundle_size_kb": 0.0}

       async def run_full_profile(self) -> PerformanceMetrics:
           """Ejecuta profiling completo del sistema."""
           cache_data = await self.profile_cache()
           db_data = await self.profile_database()
           gpu_data = await self.profile_gpu()
           mem_data = await self.profile_memory()
           fe_data = await self.profile_frontend()

           metrics = PerformanceMetrics(
               cache_hit_rate=cache_data["hit_rate"],
               cache_total_keys=cache_data["total_keys"],
               db_avg_query_ms=db_data["avg_query_ms"],
               db_slow_queries=db_data["slow_queries"],
               db_missing_indexes=db_data["missing_indexes"],
               gpu_utilization_pct=gpu_data["utilization_pct"],
               gpu_idle_pct=gpu_data["idle_pct"],
               gpu_vram_used_mb=gpu_data["vram_used_mb"],
               gpu_vram_total_mb=gpu_data["vram_total_mb"],
               memory_rss_mb=mem_data["rss_mb"],
               memory_tier_hot_pct=30.0,
               memory_tier_warm_pct=50.0,
               memory_tier_cold_pct=20.0,
               frontend_load_time_ms=fe_data["load_time_ms"],
               frontend_bundle_size_kb=fe_data["bundle_size_kb"],
           )

           self._metrics_history.append(metrics)
           return metrics

       def generate_suggestions(self, metrics: PerformanceMetrics) -> list[OptimizationSuggestion]:
           """Genera sugerencias de optimización basadas en métricas."""
           suggestions = []

           if metrics.cache_hit_rate < PERFORMANCE_TARGETS["cache_hit_rate"]:
               suggestions.append(OptimizationSuggestion(
                   category="cache",
                   severity="warning",
                   message="Cache hit rate por debajo del target",
                   current_value=f"{metrics.cache_hit_rate:.0%}",
                   target_value=f"{PERFORMANCE_TARGETS['cache_hit_rate']:.0%}",
                   action="Revisar TTL de cache, precalentar queries frecuentes",
               ))

           if metrics.db_avg_query_ms > PERFORMANCE_TARGETS["db_avg_query_ms"]:
               suggestions.append(OptimizationSuggestion(
                   category="database",
                   severity="warning",
                   message="Queries de DB por encima del target",
                   current_value=f"{metrics.db_avg_query_ms:.0f}ms",
                   target_value=f"{PERFORMANCE_TARGETS['db_avg_query_ms']:.0f}ms",
                   action="Agregar indexes faltantes, optimizar queries lentas",
               ))

           if metrics.db_missing_indexes:
               suggestions.append(OptimizationSuggestion(
                   category="database",
                   severity="info",
                   message=f"Indexes posiblemente faltantes: {', '.join(metrics.db_missing_indexes[:5])}",
                   action="Analizar y crear indexes necesarios",
               ))

           if metrics.gpu_idle_pct > PERFORMANCE_TARGETS["gpu_idle_pct_max"]:
               suggestions.append(OptimizationSuggestion(
                   category="gpu",
                   severity="info",
                   message="GPU idle alto — considerar scheduling más agresivo",
                   current_value=f"{metrics.gpu_idle_pct:.0f}% idle",
                   target_value=f"<{PERFORMANCE_TARGETS['gpu_idle_pct_max']:.0f}% idle",
               ))

           if metrics.frontend_load_time_ms > PERFORMANCE_TARGETS["frontend_load_time_ms"]:
               suggestions.append(OptimizationSuggestion(
                   category="frontend",
                   severity="warning",
                   message="Frontend carga lento",
                   current_value=f"{metrics.frontend_load_time_ms:.0f}ms",
                   target_value=f"<{PERFORMANCE_TARGETS['frontend_load_time_ms']:.0f}ms",
                   action="Optimizar bundle, lazy loading, CDN",
               ))

           if metrics.memory_rss_mb > PERFORMANCE_TARGETS["memory_rss_max_mb"]:
               suggestions.append(OptimizationSuggestion(
                   category="memory",
                   severity="critical",
                   message="Uso de memoria excesivo",
                   current_value=f"{metrics.memory_rss_mb:.0f}MB",
                   target_value=f"<{PERFORMANCE_TARGETS['memory_rss_max_mb']:.0f}MB",
                   action="Buscar memory leaks, optimizar buffers",
               ))

           return suggestions

       def calculate_score(self, metrics: PerformanceMetrics) -> float:
           """Calcula score de rendimiento (0-100)."""
           score = 100.0

           # Cache
           if metrics.cache_hit_rate < PERFORMANCE_TARGETS["cache_hit_rate"]:
               gap = PERFORMANCE_TARGETS["cache_hit_rate"] - metrics.cache_hit_rate
               score -= gap * 30

           # DB
           if metrics.db_avg_query_ms > PERFORMANCE_TARGETS["db_avg_query_ms"]:
               ratio = metrics.db_avg_query_ms / PERFORMANCE_TARGETS["db_avg_query_ms"]
               score -= min(20, (ratio - 1) * 10)

           # Frontend
           if metrics.frontend_load_time_ms > PERFORMANCE_TARGETS["frontend_load_time_ms"]:
               ratio = metrics.frontend_load_time_ms / PERFORMANCE_TARGETS["frontend_load_time_ms"]
               score -= min(20, (ratio - 1) * 15)

           # Memory
           if metrics.memory_rss_mb > PERFORMANCE_TARGETS["memory_rss_max_mb"]:
               score -= 15

           return max(0.0, round(score, 2))

       async def optimize(self) -> OptimizationReport:
           """Ejecuta profiling completo y genera reporte."""
           metrics = await self.run_full_profile()
           suggestions = self.generate_suggestions(metrics)
           score = self.calculate_score(metrics)

           report = OptimizationReport(
               metrics=metrics,
               suggestions=suggestions,
               score=score,
               passed=score >= 75.0,
           )

           logger.info(f"Optimization report: score={score:.1f}, "
                       f"suggestions={len(suggestions)}, passed={report.passed}")

           return report

2. Crear archivo tests/unit/core/test_optimizer.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_optimizer.py
   Contenido:

   """Tests para Performance Optimizer — Micro-fase 7.11"""

   import pytest
   from src.core.optimizer import (
       PerformanceOptimizer, PerformanceMetrics,
       OptimizationSuggestion, PERFORMANCE_TARGETS,
   )


   class TestPerformanceOptimizer:
       """Tests para PerformanceOptimizer."""

       def setup_method(self):
           self.optimizer = PerformanceOptimizer()

       def _good_metrics(self) -> PerformanceMetrics:
           return PerformanceMetrics(
               cache_hit_rate=0.90,
               cache_total_keys=1000,
               db_avg_query_ms=20.0,
               db_slow_queries=0,
               gpu_utilization_pct=70.0,
               gpu_idle_pct=30.0,
               gpu_vram_used_mb=2500,
               gpu_vram_total_mb=3072,
               memory_rss_mb=2048.0,
               memory_tier_hot_pct=30.0,
               memory_tier_warm_pct=50.0,
               memory_tier_cold_pct=20.0,
               frontend_load_time_ms=1500.0,
               frontend_bundle_size_kb=500.0,
           )

       def _bad_metrics(self) -> PerformanceMetrics:
           return PerformanceMetrics(
               cache_hit_rate=0.50,
               cache_total_keys=100,
               db_avg_query_ms=200.0,
               db_slow_queries=15,
               db_missing_indexes=["users.email", "memories.created_at"],
               gpu_utilization_pct=20.0,
               gpu_idle_pct=80.0,
               gpu_vram_used_mb=500,
               gpu_vram_total_mb=3072,
               memory_rss_mb=6000.0,
               memory_tier_hot_pct=30.0,
               memory_tier_warm_pct=50.0,
               memory_tier_cold_pct=20.0,
               frontend_load_time_ms=8000.0,
               frontend_bundle_size_kb=3000.0,
           )

       def test_good_metrics_high_score(self):
           score = self.optimizer.calculate_score(self._good_metrics())
           assert score >= 75.0

       def test_bad_metrics_low_score(self):
           score = self.optimizer.calculate_score(self._bad_metrics())
           assert score < 75.0

       def test_good_metrics_no_critical_suggestions(self):
           suggestions = self.optimizer.generate_suggestions(self._good_metrics())
           critical = [s for s in suggestions if s.severity == "critical"]
           assert len(critical) == 0

       def test_bad_metrics_has_suggestions(self):
           suggestions = self.optimizer.generate_suggestions(self._bad_metrics())
           assert len(suggestions) > 0

       def test_low_cache_generates_suggestion(self):
           metrics = self._good_metrics()
           metrics.cache_hit_rate = 0.50
           suggestions = self.optimizer.generate_suggestions(metrics)
           cache_suggestions = [s for s in suggestions if s.category == "cache"]
           assert len(cache_suggestions) > 0

       def test_slow_db_generates_suggestion(self):
           metrics = self._good_metrics()
           metrics.db_avg_query_ms = 200.0
           suggestions = self.optimizer.generate_suggestions(metrics)
           db_suggestions = [s for s in suggestions if s.category == "database"]
           assert len(db_suggestions) > 0

       def test_high_memory_generates_critical(self):
           metrics = self._good_metrics()
           metrics.memory_rss_mb = 5000.0
           suggestions = self.optimizer.generate_suggestions(metrics)
           memory_critical = [
               s for s in suggestions
               if s.category == "memory" and s.severity == "critical"
           ]
           assert len(memory_critical) > 0

       def test_performance_targets_defined(self):
           assert "cache_hit_rate" in PERFORMANCE_TARGETS
           assert PERFORMANCE_TARGETS["cache_hit_rate"] == 0.80
           assert PERFORMANCE_TARGETS["db_avg_query_ms"] == 50.0
           assert PERFORMANCE_TARGETS["frontend_load_time_ms"] == 3000.0

       def test_score_bounds(self):
           score_good = self.optimizer.calculate_score(self._good_metrics())
           score_bad = self.optimizer.calculate_score(self._bad_metrics())
           assert 0.0 <= score_good <= 100.0
           assert 0.0 <= score_bad <= 100.0

       def test_metrics_history_tracked(self):
           assert len(self.optimizer._metrics_history) == 0

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_optimizer.py -v

VERIFICAR:
- [ ] Archivo src/core/optimizer.py existe con PerformanceOptimizer
- [ ] Profiling: cache, DB, GPU, memory, frontend
- [ ] Targets: cache >80%, DB <50ms, frontend <3s, memory <4GB
- [ ] Sugerencias generadas para cada categoría
- [ ] Score 0-100 con threshold 75 para pass
- [ ] Métricas buenas → score alto, sin critical
- [ ] Métricas malas → score bajo, con sugerencias
- [ ] TODOS los tests pasan

SI FALLA:
- psutil: pip install psutil
- redis/asyncpg: pip install redis asyncpg

NO HACER:
- No ejecutar profiling real en tests unitarios
- No modificar el sistema durante profiling

GATE: Optimizer perfila todo el sistema, genera sugerencias, calcula score, todos los tests pasan.
```
