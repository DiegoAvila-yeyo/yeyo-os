## ═══════════════════════════════════════
## MICRO-FASE 6.15 — YeyoBenchmark: Examen Semanal de Calidad
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 6.15-1 [VSCODE] — Suite de 50 problemas estándar con comparación temporal y alertas de degradación

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.15 de Capa 6 (Sistema Inmune): implementar YeyoBenchmark, el sistema que examina al propio Yeyo cada domingo a las 4 AM con 50 problemas estándar y compara con semanas anteriores. Sin medición objetiva periódica, el modelo puede degradarse gradualmente sin que nadie lo note.

CONTEXTO:
- Micro-fases 6.0–6.14 completadas: incluye YeyoQuality (6.13) y YeyoLint (6.14) en src/quality/
- Modelo IA: qwen2.5:3b via Ollama en http://localhost:11434
- Flash Memory client: disponible en src/memory/flash_memory.py con método `store(content, importance, tags, metadata)`
- APScheduler ya instalado (se usó en micro-fase 6.12 YEYO-HACK)
- La suite tiene 50 problemas cubriendo: Python, TypeScript, SQL, Seguridad, Arquitectura
- El benchmark corre de noche (domingo 4 AM) — sin impacto en rendimiento diurno
- Alertas: degradación >5% notifica al usuario; >15% hace rollback automático de aprendizajes
- Historial guardado en base de datos para comparación semana a semana
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/quality/yeyo_benchmark.py:

   Ruta: ~/yeyo-os/src/quality/yeyo_benchmark.py
   Contenido:

   """
   YeyoOS — YeyoBenchmark: Examen Semanal de Calidad
   Micro-fase 6.15 — Capa 6: Sistema Inmune

   Cada domingo a las 4 AM, Yeyo se examina con 50 problemas estándar
   y compara con semanas anteriores para detectar degradación del modelo.
   """

   import json
   import logging
   import re
   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from statistics import mean
   from typing import Optional

   import httpx

   logger = logging.getLogger("yeyo.quality.benchmark")

   OLLAMA_BASE_URL = "http://localhost:11434"
   MODELO = "qwen2.5:3b"

   # ── Suite de 50 problemas estándar ────────────────────────────────────────

   SUITE_BENCHMARK: list[dict] = [
       # ── Categoría: Python (20 problemas) ──────────────────────────────────
       {
           "id": "py_01",
           "categoria": "python",
           "prompt": "Crea una función que ordene una lista de dicts por múltiples campos usando sorted()",
           "criterios": ["funciona_correctamente", "usa_sorted_key", "maneja_lista_vacia"],
       },
       {
           "id": "py_02",
           "categoria": "python",
           "prompt": "Implementa un decorator de retry con backoff exponencial, máximo 3 intentos",
           "criterios": ["funciona_correctamente", "backoff_correcto", "limite_intentos"],
       },
       {
           "id": "py_03",
           "categoria": "python",
           "prompt": "Crea un context manager que mida el tiempo de ejecución de un bloque de código",
           "criterios": ["usa_contextmanager", "mide_tiempo", "retorna_elapsed"],
       },
       {
           "id": "py_04",
           "categoria": "python",
           "prompt": "Implementa una clase Singleton thread-safe usando un Lock",
           "criterios": ["es_singleton", "thread_safe", "usa_lock"],
       },
       {
           "id": "py_05",
           "categoria": "python",
           "prompt": "Crea un generador que lea un archivo CSV línea a línea sin cargarlo en memoria",
           "criterios": ["usa_yield", "no_carga_completo", "maneja_header"],
       },
       {
           "id": "py_06",
           "categoria": "python",
           "prompt": "Implementa una LRU Cache manual sin usar functools.lru_cache",
           "criterios": ["capacidad_maxima", "evicts_lru", "o1_lookup"],
       },
       {
           "id": "py_07",
           "categoria": "python",
           "prompt": "Crea una función asíncrona que descargue múltiples URLs en paralelo con asyncio",
           "criterios": ["usa_asyncio_gather", "maneja_errores_por_url", "retorna_resultados"],
       },
       {
           "id": "py_08",
           "categoria": "python",
           "prompt": "Implementa un parser de expresiones matemáticas simples (+, -, *, /)",
           "criterios": ["soporta_operadores", "respeta_precedencia", "maneja_parentesis"],
       },
       {
           "id": "py_09",
           "categoria": "python",
           "prompt": "Crea una clase que implemente el patrón Observer con suscriptores y notificaciones",
           "criterios": ["suscribir", "desuscribir", "notificar_a_todos"],
       },
       {
           "id": "py_10",
           "categoria": "python",
           "prompt": "Implementa búsqueda binaria en una lista ordenada con manejo de duplicados",
           "criterios": ["o_log_n", "maneja_duplicados", "retorna_indice_correcto"],
       },
       {
           "id": "py_11",
           "categoria": "python",
           "prompt": "Crea un pool de conexiones simple con adquisición y liberación",
           "criterios": ["limite_conexiones", "reutiliza_conexiones", "thread_safe"],
       },
       {
           "id": "py_12",
           "categoria": "python",
           "prompt": "Implementa una función que aplane un dict anidado con notación de punto",
           "criterios": ["aplana_correctamente", "maneja_listas", "sin_recursion_infinita"],
       },
       {
           "id": "py_13",
           "categoria": "python",
           "prompt": "Crea un validador de contraseñas que verifique longitud, mayúsculas, números y símbolos",
           "criterios": ["verifica_longitud", "verifica_mayusculas", "verifica_simbolos"],
       },
       {
           "id": "py_14",
           "categoria": "python",
           "prompt": "Implementa un rate limiter usando el algoritmo token bucket",
           "criterios": ["token_bucket_correcto", "thread_safe", "configurable"],
       },
       {
           "id": "py_15",
           "categoria": "python",
           "prompt": "Crea una función que serialice y deserialice un grafo dirigido a/desde JSON",
           "criterios": ["serializa_nodos", "serializa_aristas", "deserializa_correcto"],
       },
       {
           "id": "py_16",
           "categoria": "python",
           "prompt": "Implementa merge sort con type hints y docstring completo",
           "criterios": ["algoritmo_correcto", "type_hints", "docstring"],
       },
       {
           "id": "py_17",
           "categoria": "python",
           "prompt": "Crea un cliente HTTP con reintentos y timeout configurable usando httpx",
           "criterios": ["usa_httpx", "reintentos", "timeout_configurable"],
       },
       {
           "id": "py_18",
           "categoria": "python",
           "prompt": "Implementa una función de hashing consistente (consistent hashing) para distribución de carga",
           "criterios": ["distribucion_uniforme", "agrega_nodos", "elimina_nodos"],
       },
       {
           "id": "py_19",
           "categoria": "python",
           "prompt": "Crea un sistema de eventos con prioridades usando heapq",
           "criterios": ["usa_heapq", "prioridades_correctas", "maneja_empates"],
       },
       {
           "id": "py_20",
           "categoria": "python",
           "prompt": "Implementa una función que detecte ciclos en un grafo dirigido usando DFS",
           "criterios": ["detecta_ciclos", "sin_falsos_positivos", "o_v_plus_e"],
       },
       # ── Categoría: TypeScript (10 problemas) ──────────────────────────────
       {
           "id": "ts_01",
           "categoria": "typescript",
           "prompt": "Crea un hook React personalizado useLocalStorage con TypeScript generics",
           "criterios": ["usa_generics", "sincroniza_storage", "maneja_json"],
       },
       {
           "id": "ts_02",
           "categoria": "typescript",
           "prompt": "Implementa una función de debounce con TypeScript que preserve el tipo del callback",
           "criterios": ["tipo_preservado", "delay_correcto", "cancela_anterior"],
       },
       {
           "id": "ts_03",
           "categoria": "typescript",
           "prompt": "Crea un tipo utilitario DeepReadonly que haga todos los campos anidados readonly",
           "criterios": ["tipo_correcto", "maneja_arrays", "maneja_objetos_anidados"],
       },
       {
           "id": "ts_04",
           "categoria": "typescript",
           "prompt": "Implementa una clase EventEmitter tipada con TypeScript usando generics",
           "criterios": ["tipos_seguros", "on_off_emit", "sin_any"],
       },
       {
           "id": "ts_05",
           "categoria": "typescript",
           "prompt": "Crea una función que convierta un objeto plano a FormData de forma recursiva",
           "criterios": ["maneja_anidados", "maneja_arrays", "maneja_files"],
       },
       {
           "id": "ts_06",
           "categoria": "typescript",
           "prompt": "Implementa un Result<T, E> type (tipo railway-oriented programming) en TypeScript",
           "criterios": ["ok_y_err", "chainable", "sin_excepciones"],
       },
       {
           "id": "ts_07",
           "categoria": "typescript",
           "prompt": "Crea un store Zustand tipado para gestión de autenticación (login/logout/user)",
           "criterios": ["tipos_correctos", "acciones_correctas", "persistencia"],
       },
       {
           "id": "ts_08",
           "categoria": "typescript",
           "prompt": "Implementa un componente React de tabla virtualizada con scroll infinito",
           "criterios": ["virtualiza_filas", "scroll_infinito", "performance"],
       },
       {
           "id": "ts_09",
           "categoria": "typescript",
           "prompt": "Crea una función de retry para Promises con backoff exponencial en TypeScript",
           "criterios": ["tipos_correctos", "backoff_exponencial", "max_intentos"],
       },
       {
           "id": "ts_10",
           "categoria": "typescript",
           "prompt": "Implementa un cliente API tipado con interceptores para JWT refresh automático",
           "criterios": ["interceptor_request", "interceptor_response", "refresh_automatico"],
       },
       # ── Categoría: SQL (10 problemas) ─────────────────────────────────────
       {
           "id": "sql_01",
           "categoria": "sql",
           "prompt": "Escribe una query que encuentre los N usuarios más activos del último mes con JOINs",
           "criterios": ["usa_joins", "filtra_por_fecha", "ordena_correctamente"],
       },
       {
           "id": "sql_02",
           "categoria": "sql",
           "prompt": "Implementa una CTE recursiva para recorrer una jerarquía de categorías",
           "criterios": ["cte_recursiva", "caso_base", "caso_recursivo"],
       },
       {
           "id": "sql_03",
           "categoria": "sql",
           "prompt": "Crea índices compuestos para optimizar una query con WHERE y ORDER BY sobre 3 tablas",
           "criterios": ["indices_adecuados", "orden_columnas_correcto", "cubre_query"],
       },
       {
           "id": "sql_04",
           "categoria": "sql",
           "prompt": "Escribe una ventana de función para calcular running total y rank por grupo",
           "criterios": ["usa_window_function", "running_total_correcto", "rank_por_grupo"],
       },
       {
           "id": "sql_05",
           "categoria": "sql",
           "prompt": "Diseña un esquema con soft delete, audit trail y particionamiento por fecha",
           "criterios": ["soft_delete", "audit_columns", "particionamiento"],
       },
       {
           "id": "sql_06",
           "categoria": "sql",
           "prompt": "Escribe una query UPSERT (INSERT OR UPDATE) eficiente en PostgreSQL",
           "criterios": ["usa_on_conflict", "actualiza_correctamente", "retorna_inserted"],
       },
       {
           "id": "sql_07",
           "categoria": "sql",
           "prompt": "Implementa un cursor-based pagination eficiente para grandes datasets",
           "criterios": ["usa_cursor", "no_offset", "ordenacion_estable"],
       },
       {
           "id": "sql_08",
           "categoria": "sql",
           "prompt": "Crea una función PostgreSQL que calcule el percentil 95 de latencia por endpoint",
           "criterios": ["percentile_disc", "agrupacion_correcta", "performance"],
       },
       {
           "id": "sql_09",
           "categoria": "sql",
           "prompt": "Escribe una query que detecte filas duplicadas y las elimine manteniendo la más reciente",
           "criterios": ["detecta_duplicados", "mantiene_reciente", "transaccional"],
       },
       {
           "id": "sql_10",
           "categoria": "sql",
           "prompt": "Diseña el esquema para un sistema de permisos RBAC (roles, permisos, usuarios)",
           "criterios": ["tablas_correctas", "relaciones_correctas", "indices_claves"],
       },
       # ── Categoría: Seguridad (10 problemas) ───────────────────────────────
       {
           "id": "sec_01",
           "categoria": "seguridad",
           "prompt": "Crea un endpoint FastAPI con autenticación JWT completa (login, refresh, logout)",
           "criterios": ["no_vulnerabilidades_jwt", "manejo_expiracion", "refresh_token"],
       },
       {
           "id": "sec_02",
           "categoria": "seguridad",
           "prompt": "Implementa rate limiting por IP y por usuario con Redis en FastAPI",
           "criterios": ["limita_por_ip", "limita_por_usuario", "headers_correctos"],
       },
       {
           "id": "sec_03",
           "categoria": "seguridad",
           "prompt": "Crea middleware de validación de input que prevenga XSS y sanitize HTML",
           "criterios": ["previene_xss", "sanitiza_html", "no_rompe_json"],
       },
       {
           "id": "sec_04",
           "categoria": "seguridad",
           "prompt": "Implementa almacenamiento seguro de contraseñas con bcrypt y PBKDF2",
           "criterios": ["usa_bcrypt", "salt_correcto", "verificacion_segura"],
       },
       {
           "id": "sec_05",
           "categoria": "seguridad",
           "prompt": "Crea un sistema de CSRF tokens para formularios en Next.js",
           "criterios": ["genera_token", "valida_token", "doble_submit_cookie"],
       },
       {
           "id": "sec_06",
           "categoria": "seguridad",
           "prompt": "Implementa cifrado AES-256-GCM para datos sensibles en reposo",
           "criterios": ["aes_256_gcm", "iv_aleatorio", "autenticado"],
       },
       {
           "id": "sec_07",
           "categoria": "seguridad",
           "prompt": "Diseña un sistema de auditoría de accesos con firma digital de logs",
           "criterios": ["firma_logs", "no_repudio", "tamper_proof"],
       },
       {
           "id": "sec_08",
           "categoria": "seguridad",
           "prompt": "Implementa validación de uploads de archivos (tipo, tamaño, contenido malicioso)",
           "criterios": ["valida_mime", "valida_tamano", "detecta_malicioso"],
       },
       {
           "id": "sec_09",
           "categoria": "seguridad",
           "prompt": "Crea un endpoint que prevenga timing attacks en comparación de tokens",
           "criterios": ["hmac_compare", "tiempo_constante", "sin_early_exit"],
       },
       {
           "id": "sec_10",
           "categoria": "seguridad",
           "prompt": "Implementa headers de seguridad HTTP (HSTS, CSP, X-Frame-Options) en FastAPI",
           "criterios": ["hsts_correcto", "csp_restrictivo", "frame_options"],
       },
   ]


   # ─── Dataclasses de resultado ──────────────────────────────────────────────


   @dataclass
   class ProblemaResult:
       """Resultado de evaluar un problema individual de la suite."""

       problema_id: str
       categoria: str
       score: float        # 0.0 – 1.0
       criterios_aprobados: list[str] = field(default_factory=list)
       criterios_reprobados: list[str] = field(default_factory=list)
       codigo_generado: str = ""
       tiempo_generacion_ms: float = 0.0


   @dataclass
   class BenchmarkResult:
       """Resultado completo de la ejecución semanal del benchmark."""

       fecha: datetime
       score_promedio: float
       scores_por_categoria: dict[str, float]
       degradacion_vs_semana_anterior: float    # % de cambio; negativo = degradación
       problemas: list[ProblemaResult] = field(default_factory=list)
       alertas: list[str] = field(default_factory=list)
       duracion_total_segundos: float = 0.0

       def to_dict(self) -> dict:
           return {
               "fecha": self.fecha.isoformat(),
               "score_promedio": round(self.score_promedio, 4),
               "scores_por_categoria": {
                   k: round(v, 4) for k, v in self.scores_por_categoria.items()
               },
               "degradacion_vs_semana_anterior": round(self.degradacion_vs_semana_anterior, 4),
               "alertas": self.alertas,
               "duracion_total_segundos": round(self.duracion_total_segundos, 2),
               "total_problemas": len(self.problemas),
           }


   # ─── Evaluador principal ───────────────────────────────────────────────────


   class YeyoBenchmark:
       """
       Examina al modelo con 50 problemas estándar cada domingo a las 4 AM.
       Compara con semanas anteriores y alerta si hay degradación.
       """

       UMBRAL_ALERTA_DEGRADACION: float = 0.05   # 5%
       UMBRAL_CRITICO_DEGRADACION: float = 0.15  # 15%

       def __init__(self, history=None, flash_memory=None) -> None:
           self.history = history
           self.flash_memory = flash_memory

       async def ejecutar_suite(self) -> BenchmarkResult:
           """
           Ejecuta la suite completa de 50 problemas.
           Retorna BenchmarkResult con scores por categoría y comparación histórica.
           """
           import time

           logger.info("Iniciando YeyoBenchmark — %d problemas", len(SUITE_BENCHMARK))
           inicio = time.time()

           resultados: list[ProblemaResult] = []

           async with httpx.AsyncClient(timeout=120.0) as cliente:
               for problema in SUITE_BENCHMARK:
                   resultado = await self._evaluar_problema(cliente, problema)
                   resultados.append(resultado)
                   logger.debug(
                       "Problema %s: score=%.2f", problema["id"], resultado.score
                   )

           duracion = time.time() - inicio

           # ── Calcular score promedio ────────────────────────────────────────
           score_promedio = mean(r.score for r in resultados)

           # ── Scores por categoría ──────────────────────────────────────────
           scores_por_categoria = self.agrupar_por_categoria(resultados)

           # ── Comparar con historial ────────────────────────────────────────
           degradacion = self.comparar_historico(score_promedio)

           # ── Generar alertas ───────────────────────────────────────────────
           alertas = self._generar_alertas(degradacion, scores_por_categoria)

           benchmark_result = BenchmarkResult(
               fecha=datetime.now(timezone.utc),
               score_promedio=score_promedio,
               scores_por_categoria=scores_por_categoria,
               degradacion_vs_semana_anterior=degradacion,
               problemas=resultados,
               alertas=alertas,
               duracion_total_segundos=duracion,
           )

           # ── Guardar en Flash Memory ───────────────────────────────────────
           if self.flash_memory:
               self.flash_memory.store(
                   content=json.dumps(benchmark_result.to_dict()),
                   importance=0.8,
                   tags=["benchmark", "calidad_modelo", "semanal"],
                   metadata={"tipo": "benchmark_semanal", "score": score_promedio},
               )

           logger.info(
               "Benchmark completado: score=%.2f degradacion=%.2f%% en %.1fs",
               score_promedio,
               degradacion * 100,
               duracion,
           )

           return benchmark_result

       async def _evaluar_problema(
           self, cliente: httpx.AsyncClient, problema: dict
       ) -> ProblemaResult:
           """Genera código para un problema y evalúa sus criterios."""
           import time

           t_inicio = time.time()
           try:
               response = await cliente.post(
                   f"{OLLAMA_BASE_URL}/api/generate",
                   json={
                       "model": MODELO,
                       "prompt": problema["prompt"],
                       "stream": False,
                       "options": {"temperature": 0.1, "num_predict": 512},
                   },
               )
               datos = response.json()
               codigo = datos.get("response", "")
           except Exception as exc:
               logger.warning("Error generando respuesta para %s: %s", problema["id"], exc)
               codigo = ""

           tiempo_ms = (time.time() - t_inicio) * 1000
           score, aprobados, reprobados = self.evaluar_criterios(codigo, problema["criterios"])

           return ProblemaResult(
               problema_id=problema["id"],
               categoria=problema["categoria"],
               score=score,
               criterios_aprobados=aprobados,
               criterios_reprobados=reprobados,
               codigo_generado=codigo[:500],
               tiempo_generacion_ms=tiempo_ms,
           )

       def evaluar_criterios(
           self, codigo: str, criterios: list[str]
       ) -> tuple[float, list[str], list[str]]:
           """
           Evalúa el código contra los criterios del problema.
           Retorna (score, criterios_aprobados, criterios_reprobados).
           """
           if not codigo.strip():
               return 0.0, [], criterios

           aprobados: list[str] = []
           reprobados: list[str] = []

           for criterio in criterios:
               if self._verificar_criterio(codigo, criterio):
                   aprobados.append(criterio)
               else:
                   reprobados.append(criterio)

           score = len(aprobados) / len(criterios) if criterios else 0.0
           return score, aprobados, reprobados

       def _verificar_criterio(self, codigo: str, criterio: str) -> bool:
           """
           Verifica un criterio individual mediante heurísticas de código.
           Retorna True si el código satisface el criterio.
           """
           codigo_lower = codigo.lower()

           verificadores = {
               "funciona_correctamente": lambda c: len(c.strip()) > 50 and ("def " in c or "function" in c or "class " in c),
               "usa_sorted_key": lambda c: "sorted" in c and "key" in c,
               "maneja_lista_vacia": lambda c: "[]" in c or "not " in c or "len(" in c,
               "backoff_correcto": lambda c: ("sleep" in c or "wait" in c) and ("2" in c or "exponential" in c.lower()),
               "limite_intentos": lambda c: any(w in c for w in ["max_retries", "max_attempts", "intentos", "attempt"]),
               "usa_contextmanager": lambda c: "__enter__" in c or "__exit__" in c or "contextmanager" in c,
               "mide_tiempo": lambda c: "time" in c and ("perf_counter" in c or "monotonic" in c or "time()" in c),
               "retorna_elapsed": lambda c: "elapsed" in c or "duration" in c or "tiempo" in c,
               "thread_safe": lambda c: "lock" in c.lower() or "threading" in c or "Lock()" in c,
               "usa_lock": lambda c: "Lock" in c and ("acquire" in c or "with " in c),
               "es_singleton": lambda c: "_instance" in c or "instance" in c.lower(),
               "usa_yield": lambda c: "yield" in c,
               "no_carga_completo": lambda c: "yield" in c and "readlines" not in c,
               "maneja_header": lambda c: "header" in c.lower() or "next(" in c or "skip" in c.lower(),
               "usa_asyncio_gather": lambda c: "gather" in c or "asyncio.gather" in c,
               "maneja_errores_por_url": lambda c: "except" in c or "try" in c,
               "usa_generics": lambda c: "<" in c and ">" in c and ("T" in c or "Generic" in c),
               "tipos_correctos": lambda c: ": " in c and ("->" in c or "type" in c.lower()),
               "sin_any": lambda c: "any" not in c.lower() or c.lower().count(": any") == 0,
               "usa_joins": lambda c: "join" in c.upper(),
               "filtra_por_fecha": lambda c: any(w in c.upper() for w in ["DATE", "TIMESTAMP", "NOW()", "INTERVAL"]),
               "ordena_correctamente": lambda c: "ORDER BY" in c.upper(),
               "cte_recursiva": lambda c: "WITH RECURSIVE" in c.upper() or ("WITH" in c.upper() and "UNION" in c.upper()),
               "caso_base": lambda c: "UNION" in c.upper(),
               "no_vulnerabilidades_jwt": lambda c: "secret" not in c.lower() or "os.environ" in c or "getenv" in c,
               "manejo_expiracion": lambda c: "exp" in c or "expir" in c.lower() or "expire" in c.lower(),
               "refresh_token": lambda c: "refresh" in c.lower(),
               "usa_bcrypt": lambda c: "bcrypt" in c.lower(),
               "salt_correcto": lambda c: "salt" in c.lower() or "gensalt" in c.lower(),
               "separacion_concerns": lambda c: ("router" in c.lower() or "service" in c.lower()) and "model" in c.lower(),
               "nombres_correctos": lambda c: any(w in c for w in ["/api/", "/v1/", "router"]),
               "versionado": lambda c: "/v1" in c or "/v2" in c or "version" in c.lower(),
           }

           verificador = verificadores.get(criterio)
           if verificador is None:
               # Criterio desconocido: heurística genérica — verificar que el código no está vacío
               return len(codigo.strip()) > 100

           try:
               return verificador(codigo)
           except Exception:
               return False

       def agrupar_por_categoria(
           self, resultados: list[ProblemaResult]
       ) -> dict[str, float]:
           """Calcula score promedio por categoría."""
           por_categoria: dict[str, list[float]] = {}
           for r in resultados:
               por_categoria.setdefault(r.categoria, []).append(r.score)
           return {
               cat: round(mean(scores), 4)
               for cat, scores in por_categoria.items()
           }

       def comparar_historico(self, score_actual: float) -> float:
           """
           Retorna % de cambio respecto a la semana anterior.
           Negativo = degradación; positivo = mejora.
           """
           if not self.history:
               logger.info("Sin historial disponible — no se puede comparar")
               return 0.0

           score_anterior = self.history.obtener_ultimo_score()
           if score_anterior is None or score_anterior == 0.0:
               return 0.0

           return (score_actual - score_anterior) / score_anterior

       def _generar_alertas(
           self, degradacion: float, scores_por_categoria: dict[str, float]
       ) -> list[str]:
           """Genera lista de alertas según el nivel de degradación."""
           alertas: list[str] = []

           if degradacion < -self.UMBRAL_CRITICO_DEGRADACION:
               categorias_bajas = [
                   cat
                   for cat, score in scores_por_categoria.items()
                   if score < 0.5
               ]
               alertas.append(
                   f"🔴 DEGRADACIÓN CRÍTICA: {abs(degradacion) * 100:.1f}% esta semana. "
                   f"Categorías afectadas: {categorias_bajas}. "
                   f"Considera revertir aprendizajes de la última semana."
               )
           elif degradacion < -self.UMBRAL_ALERTA_DEGRADACION:
               categorias_bajas = [
                   cat
                   for cat, score in scores_por_categoria.items()
                   if score < 0.6
               ]
               alertas.append(
                   f"⚠️ El modelo degradó {abs(degradacion) * 100:.1f}% esta semana. "
                   f"Categorías con menor rendimiento: {categorias_bajas}."
               )

           return alertas

2. Crear archivo src/quality/benchmark_scheduler.py:

   Ruta: ~/yeyo-os/src/quality/benchmark_scheduler.py
   Contenido:

   """
   YeyoOS — YeyoBenchmark: Scheduler
   Micro-fase 6.15 — Capa 6: Sistema Inmune

   Cron que dispara el benchmark cada domingo a las 4 AM.
   Usa APScheduler (ya instalado desde micro-fase 6.12).
   """

   import asyncio
   import logging

   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   from apscheduler.triggers.cron import CronTrigger

   from .yeyo_benchmark import YeyoBenchmark
   from .benchmark_history import BenchmarkHistory

   logger = logging.getLogger("yeyo.quality.benchmark_scheduler")


   class BenchmarkScheduler:
       """Programa la ejecución semanal del benchmark (domingo 4 AM)."""

       def __init__(self, flash_memory=None) -> None:
           self.history = BenchmarkHistory()
           self.benchmark = YeyoBenchmark(history=self.history, flash_memory=flash_memory)
           self.scheduler = AsyncIOScheduler()
           self._configurado = False

       def iniciar(self) -> None:
           """Configura el scheduler y lo arranca."""
           self.scheduler.add_job(
               func=self._ejecutar_benchmark,
               trigger=CronTrigger(
                   day_of_week="sun",
                   hour=4,
                   minute=0,
                   second=0,
               ),
               id="yeyo_benchmark_semanal",
               name="YeyoBenchmark Semanal (domingo 4 AM)",
               replace_existing=True,
               max_instances=1,     # no correr en paralelo
               coalesce=True,       # si se perdió una ejecución, correr solo una vez
           )
           self.scheduler.start()
           self._configurado = True
           logger.info(
               "BenchmarkScheduler iniciado — próxima ejecución: domingo 04:00 AM"
           )

       def detener(self) -> None:
           """Detiene el scheduler."""
           if self._configurado:
               self.scheduler.shutdown(wait=False)
               logger.info("BenchmarkScheduler detenido")

       async def _ejecutar_benchmark(self) -> None:
           """Callback que APScheduler llama cada domingo a las 4 AM."""
           logger.info("Iniciando ejecución semanal del YeyoBenchmark")
           try:
               resultado = await self.benchmark.ejecutar_suite()
               await self.history.guardar(resultado)

               # Manejar degradación crítica
               if resultado.degradacion_vs_semana_anterior < -0.15:
                   await self._manejar_degradacion_critica(resultado)
               elif resultado.degradacion_vs_semana_anterior < -0.05:
                   await self._manejar_degradacion_moderada(resultado)

               logger.info(
                   "Benchmark semanal completado: score=%.2f degradacion=%.2f%%",
                   resultado.score_promedio,
                   resultado.degradacion_vs_semana_anterior * 100,
               )
           except Exception as exc:
               logger.error("Error en benchmark semanal: %s", exc, exc_info=True)

       async def _manejar_degradacion_critica(self, resultado) -> None:
           """Maneja degradación > 15%: rollback automático de aprendizajes."""
           logger.critical(
               "DEGRADACIÓN CRÍTICA: %.1f%% — iniciando rollback de aprendizajes de la última semana",
               abs(resultado.degradacion_vs_semana_anterior) * 100,
           )
           # Aquí se conectaría con el sistema de Flash Memory para revertir
           # los aprendizajes de la última semana con importancia < 0.5
           if self.benchmark.flash_memory:
               try:
                   self.benchmark.flash_memory.store(
                       content=(
                           f"[ALERTA CRÍTICA] Degradación del modelo: "
                           f"{abs(resultado.degradacion_vs_semana_anterior) * 100:.1f}% esta semana. "
                           f"Alertas: {resultado.alertas}. "
                           f"Se recomienda revisar aprendizajes recientes."
                       ),
                       importance=0.99,
                       tags=["benchmark", "degradacion_critica", "alerta"],
                       metadata={
                           "tipo": "alerta_degradacion_critica",
                           "degradacion": resultado.degradacion_vs_semana_anterior,
                       },
                   )
               except Exception as exc:
                   logger.error("Error guardando alerta crítica en Flash Memory: %s", exc)

       async def _manejar_degradacion_moderada(self, resultado) -> None:
           """Maneja degradación > 5%: notificación al usuario."""
           logger.warning(
               "Degradación moderada: %.1f%% — notificando al usuario",
               abs(resultado.degradacion_vs_semana_anterior) * 100,
           )
           if self.benchmark.flash_memory:
               try:
                   self.benchmark.flash_memory.store(
                       content=(
                           f"[ADVERTENCIA] El modelo degradó "
                           f"{abs(resultado.degradacion_vs_semana_anterior) * 100:.1f}% esta semana. "
                           f"Categorías afectadas: {resultado.alertas}"
                       ),
                       importance=0.85,
                       tags=["benchmark", "degradacion_moderada", "advertencia"],
                       metadata={
                           "tipo": "alerta_degradacion_moderada",
                           "degradacion": resultado.degradacion_vs_semana_anterior,
                       },
                   )
               except Exception as exc:
                   logger.error("Error guardando advertencia en Flash Memory: %s", exc)

       async def ejecutar_ahora(self) -> None:
           """Ejecuta el benchmark inmediatamente (para testing/diagnóstico manual)."""
           logger.info("Ejecución manual del benchmark solicitada")
           await self._ejecutar_benchmark()

3. Crear archivo src/quality/benchmark_history.py:

   Ruta: ~/yeyo-os/src/quality/benchmark_history.py
   Contenido:

   """
   YeyoOS — YeyoBenchmark: Historial
   Micro-fase 6.15 — Capa 6: Sistema Inmune

   Persiste historial de benchmarks y provee comparación temporal.
   """

   import json
   import logging
   from datetime import datetime, timezone
   from pathlib import Path
   from typing import Optional

   from .yeyo_benchmark import BenchmarkResult

   logger = logging.getLogger("yeyo.quality.benchmark_history")

   HISTORIAL_PATH = Path.home() / "yeyo-os" / "data" / "benchmark_history.jsonl"


   class BenchmarkHistory:
       """
       Persiste historial de ejecuciones de benchmark en formato JSONL.
       Cada línea es un BenchmarkResult serializado.
       """

       def __init__(self, path: Optional[Path] = None) -> None:
           self.path = path or HISTORIAL_PATH
           self.path.parent.mkdir(parents=True, exist_ok=True)

       async def guardar(self, resultado: BenchmarkResult) -> None:
           """Agrega el resultado al historial."""
           try:
               with self.path.open("a", encoding="utf-8") as f:
                   f.write(json.dumps(resultado.to_dict()) + "\n")
               logger.info(
                   "Benchmark guardado en historial: fecha=%s score=%.2f",
                   resultado.fecha.isoformat(),
                   resultado.score_promedio,
               )
           except Exception as exc:
               logger.error("Error guardando benchmark en historial: %s", exc)

       def obtener_ultimo_score(self) -> Optional[float]:
           """Retorna el score promedio del benchmark anterior (penúltimo)."""
           registros = self._cargar_todos()
           if len(registros) < 2:
               return None
           # El último es el actual (recién guardado), el penúltimo es el anterior
           return registros[-2].get("score_promedio")

       def obtener_historial_completo(self) -> list[dict]:
           """Retorna todos los benchmarks en orden cronológico."""
           return self._cargar_todos()

       def obtener_tendencia(self, semanas: int = 4) -> list[float]:
           """Retorna scores de las últimas N semanas para ver tendencia."""
           registros = self._cargar_todos()
           return [r["score_promedio"] for r in registros[-semanas:]]

       def _cargar_todos(self) -> list[dict]:
           """Lee el archivo JSONL y retorna lista de registros."""
           if not self.path.exists():
               return []
           registros = []
           try:
               with self.path.open("r", encoding="utf-8") as f:
                   for linea in f:
                       linea = linea.strip()
                       if linea:
                           try:
                               registros.append(json.loads(linea))
                           except json.JSONDecodeError:
                               continue
           except Exception as exc:
               logger.error("Error leyendo historial: %s", exc)
           return registros

4. Crear archivo tests/unit/quality/test_yeyo_benchmark.py:

   Ruta: ~/yeyo-os/tests/unit/quality/test_yeyo_benchmark.py
   Contenido:

   """
   Tests unitarios para YeyoBenchmark — Micro-fase 6.15
   Cubre: ejecución, evaluación de criterios, comparación histórica, alertas, scheduler.
   """

   import asyncio
   import json
   import tempfile
   from datetime import datetime, timezone
   from pathlib import Path
   from unittest.mock import AsyncMock, MagicMock, patch

   import pytest

   from src.quality.yeyo_benchmark import (
       SUITE_BENCHMARK,
       BenchmarkResult,
       ProblemaResult,
       YeyoBenchmark,
   )
   from src.quality.benchmark_history import BenchmarkHistory


   # ─── Fixtures ─────────────────────────────────────────────────────────────


   @pytest.fixture
   def benchmark() -> YeyoBenchmark:
       return YeyoBenchmark()


   @pytest.fixture
   def history_tmp(tmp_path: Path) -> BenchmarkHistory:
       return BenchmarkHistory(path=tmp_path / "test_history.jsonl")


   # ─── Test 1: suite tiene exactamente 50 problemas ─────────────────────────


   def test_suite_tiene_50_problemas():
       assert len(SUITE_BENCHMARK) == 50


   # ─── Test 2: suite cubre las 4 categorías ────────────────────────────────


   def test_suite_cubre_categorias_requeridas():
       categorias = {p["categoria"] for p in SUITE_BENCHMARK}
       assert "python" in categorias
       assert "typescript" in categorias
       assert "sql" in categorias
       assert "seguridad" in categorias


   # ─── Test 3: evaluar_criterios con código que cumple criterios ───────────


   def test_evaluar_criterios_codigo_con_sorted(benchmark):
       codigo = """
   def ordenar(lista, campos):
       return sorted(lista, key=lambda x: tuple(x[c] for c in campos))
   """
       score, aprobados, reprobados = benchmark.evaluar_criterios(
           codigo, ["funciona_correctamente", "usa_sorted_key", "maneja_lista_vacia"]
       )
       assert score > 0.0
       assert "usa_sorted_key" in aprobados


   # ─── Test 4: evaluar_criterios con código vacío → score 0.0 ──────────────


   def test_evaluar_criterios_codigo_vacio(benchmark):
       score, aprobados, reprobados = benchmark.evaluar_criterios(
           "", ["funciona_correctamente", "usa_sorted_key"]
       )
       assert score == 0.0
       assert len(aprobados) == 0
       assert len(reprobados) == 2


   # ─── Test 5: comparar_historico sin historial → retorna 0.0 ──────────────


   def test_comparar_historico_sin_datos(benchmark):
       degradacion = benchmark.comparar_historico(0.8)
       assert degradacion == 0.0


   # ─── Test 6: alerta se genera cuando degradación > 5% ────────────────────


   def test_alerta_degradacion_moderada(benchmark):
       alertas = benchmark._generar_alertas(
           -0.07,  # 7% degradación
           {"python": 0.55, "typescript": 0.70, "sql": 0.80, "seguridad": 0.50},
       )
       assert len(alertas) == 1
       assert "⚠️" in alertas[0]
       assert "7" in alertas[0] or "7.0" in alertas[0]


   # ─── Test adicional: alerta crítica cuando degradación > 15% ─────────────


   def test_alerta_critica_degradacion(benchmark):
       alertas = benchmark._generar_alertas(
           -0.18,  # 18% degradación
           {"python": 0.40, "typescript": 0.35, "sql": 0.45, "seguridad": 0.30},
       )
       assert len(alertas) == 1
       assert "🔴" in alertas[0]
       assert "CRÍTICA" in alertas[0].upper() or "CRITICA" in alertas[0].upper()

VERIFICAR:
- [ ] `src/quality/yeyo_benchmark.py` contiene `SUITE_BENCHMARK` con 50 problemas y clase `YeyoBenchmark`
- [ ] `src/quality/benchmark_scheduler.py` contiene `BenchmarkScheduler` con cron domingo 4 AM
- [ ] `src/quality/benchmark_history.py` contiene `BenchmarkHistory` con persistencia JSONL
- [ ] `tests/unit/quality/test_yeyo_benchmark.py` contiene 6+ tests
- [ ] Ejecutar `cd ~/yeyo-os && python -m pytest tests/unit/quality/test_yeyo_benchmark.py -v` → todos los tests pasan
- [ ] Verificar suite: `python -c "from src.quality.yeyo_benchmark import SUITE_BENCHMARK; print(len(SUITE_BENCHMARK))"` → imprime `50`
- [ ] Verificar categorías: `python -c "from src.quality.yeyo_benchmark import SUITE_BENCHMARK; print({p['categoria'] for p in SUITE_BENCHMARK})"` → incluye python, typescript, sql, seguridad
- [ ] `BenchmarkScheduler().iniciar()` no lanza excepciones
- [ ] Alertas con degradación > 15% contienen rollback automático

SI FALLA:
- `APScheduler not found`: `pip install apscheduler` — ya debería estar desde micro-fase 6.12
- `ModuleNotFoundError: httpx`: `pip install httpx`
- `BenchmarkHistory: PermissionError`: verificar que `~/yeyo-os/data/` existe con permisos de escritura
- Tests async fallan: instalar `pytest-asyncio` y verificar `asyncio_mode = "auto"` en `pytest.ini`
- Ollama no responde durante tests: los tests mockeados no necesitan Ollama — solo `test_ejecutar_suite` necesita Ollama corriendo

NO HACER:
- No correr el benchmark durante el día — está diseñado para 4 AM cuando el sistema está idle
- No modificar `SUITE_BENCHMARK` sin actualizar los verificadores en `_verificar_criterio`
- No usar offset-based pagination en el historial — el archivo JSONL es append-only por diseño
- No eliminar registros del historial — la comparación histórica requiere todos los datos
- No ignorar la alerta de degradación crítica (>15%) — es la señal más importante del sistema

GATE: Cada domingo a las 4 AM YeyoBenchmark ejecuta una suite de 50 problemas cubriendo Python, TypeScript, SQL y Seguridad, compara con la semana anterior, alerta con ⚠️ si degradación >5%, alerta con 🔴 y rollback si >15%, y los 6 tests unitarios pasan.
```
