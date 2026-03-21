## ═══════════════════════════════════════
## MICRO-FASE 5.32 — Selección Automática de Modelo por Complejidad
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.32-1 [VSCODE] — SelectorModelo: elige modelo local/YeyoNet/API según complejidad estimada

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.32 de Capa 5 (Órganos): implementar SelectorModelo que elige automáticamente el modelo correcto (local, YeyoNet remoto, API externa) según la complejidad estimada de cada tarea.

CONTEXTO:
- Micro-fases 5.28-5.31 completadas: Investigador, MicroTareas, Razonamiento, CachePatrones
- IAProvider en src/ia/interfaces.py: generate(), chat(), get_embedding(), health_check()
- OllamaProvider en src/ia/ollama_provider.py: host, model, client httpx.AsyncClient
- YeyoConfig en src/core/config.py: ollama_host, ollama_model
- YeyoOrquestador en src/orquestador/orquestador.py: consulta SelectorModelo antes de cada nodo
- YeyoNet Core (7.17) provee nodos remotos con GPU (cuando disponible)
- Modelos Ollama locales: qwen2.5:3b (default), qwen2.5-coder:7b (si hay VRAM)
- SelectorModelo es CONSULTADO POR: YeyoOrquestador (4.19) antes de cada nodo del grafo
- Cada nodo del grafo puede overridear con modelo: "qwen2.5-coder:7b" explícitamente

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/investigador/modelos_selector.py:

   Ruta: ~/yeyo-os/src/investigador/modelos_selector.py
   Contenido:

   """
   YeyoOS — Modelos para SelectorModelo
   Micro-fase 5.32 — Capa 5: Órganos

   Dataclasses para configuración de modelos y selección.
   """

   from __future__ import annotations

   from dataclasses import dataclass, field
   from typing import Optional


   @dataclass
   class ModeloConfig:
       """Configuración de un modelo disponible."""
       nombre: str  # Nombre del modelo (e.g., "qwen2.5:3b")
       tipo: str  # "local" | "yeyonet" | "api"
       vram_requerida_mb: int = 0  # VRAM necesaria en MB
       velocidad_estimada: float = 1.0  # tokens/segundo estimados
       calidad_estimada: float = 0.7  # 0.0-1.0 calidad esperada
       disponible: bool = True
       endpoint: Optional[str] = None  # URL si es remoto/API
       max_tokens: int = 4096
       costo_por_token: float = 0.0  # Solo para APIs externas


   # Modelos predefinidos
   MODELO_LOCAL_SMALL = ModeloConfig(
       nombre="qwen2.5:3b",
       tipo="local",
       vram_requerida_mb=2048,
       velocidad_estimada=30.0,
       calidad_estimada=0.7,
       max_tokens=4096,
   )

   MODELO_LOCAL_CODER = ModeloConfig(
       nombre="qwen2.5-coder:7b",
       tipo="local",
       vram_requerida_mb=5120,
       velocidad_estimada=15.0,
       calidad_estimada=0.85,
       max_tokens=8192,
   )

   MODELO_YEYONET_DEFAULT = ModeloConfig(
       nombre="yeyonet:best",
       tipo="yeyonet",
       vram_requerida_mb=0,
       velocidad_estimada=20.0,
       calidad_estimada=0.9,
       max_tokens=8192,
   )

   MODELO_API_FALLBACK = ModeloConfig(
       nombre="api:fallback",
       tipo="api",
       vram_requerida_mb=0,
       velocidad_estimada=50.0,
       calidad_estimada=0.95,
       max_tokens=16384,
       costo_por_token=0.00001,
   )


2. Crear archivo src/investigador/selector_modelo.py:

   Ruta: ~/yeyo-os/src/investigador/selector_modelo.py
   Contenido:

   """
   YeyoOS — SelectorModelo
   Micro-fase 5.32 — Capa 5: Órganos

   Elige automáticamente el modelo correcto para cada tarea basándose en:
   1. Complejidad estimada de la tarea
   2. Modelos disponibles (Ollama local, YeyoNet remoto, API externa)
   3. VRAM disponible en la máquina local
   4. Historial de tiempos para tareas similares

   Consultado por YeyoOrquestador (4.19) antes de ejecutar cada nodo.
   Cada nodo puede overridear con modelo explícito.
   """

   from __future__ import annotations

   import logging
   import os
   from typing import Any, Dict, List, Optional

   import httpx

   from .modelos_selector import (
       MODELO_API_FALLBACK,
       MODELO_LOCAL_CODER,
       MODELO_LOCAL_SMALL,
       MODELO_YEYONET_DEFAULT,
       ModeloConfig,
   )

   logger = logging.getLogger(__name__)

   KEYWORDS_ALTA_COMPLEJIDAD = {
       "distributed", "concurrent", "microservices", "machine learning",
       "neural network", "optimization", "security", "encryption",
       "compiler", "kernel", "parser", "real-time",
       "compilador", "distribuido", "concurrencia", "seguridad",
       "aprendizaje automático", "optimización",
   }

   KEYWORDS_MEDIA_COMPLEJIDAD = {
       "api", "database", "cache", "websocket", "middleware",
       "authentication", "migration", "pipeline", "docker",
       "base de datos", "autenticación", "migración",
   }


   class SelectorModeloError(Exception):
       """Error en selección de modelo."""
       pass


   class SelectorModelo:
       """
       Selector automático de modelo por complejidad.

       Umbrales de selección:
       - complejidad < 0.3 → qwen2.5:3b (local, rápido)
       - complejidad 0.3-0.6 → qwen2.5-coder:7b (si hay VRAM)
       - complejidad 0.6-0.8 → delegar a YeyoNet (nodo con mejor GPU)
       - complejidad > 0.8 → API externa como fallback

       Fallback graceful: si el modelo elegido no está disponible,
       baja al siguiente nivel.
       """

       def __init__(
           self,
           ollama_host: str = "http://localhost:11434",
           yeyonet_endpoint: Optional[str] = None,
           api_key: Optional[str] = None,
           api_endpoint: Optional[str] = None,
       ):
           self._ollama_host = ollama_host
           self._yeyonet_endpoint = yeyonet_endpoint
           self._api_key = api_key or os.getenv("YEYO_API_KEY")
           self._api_endpoint = api_endpoint or os.getenv("YEYO_API_ENDPOINT")
           self._modelos_cache: Optional[List[ModeloConfig]] = None
           self._historial_tiempos: Dict[str, List[float]] = {}

       async def elegir(self, tarea: str, modelo_override: Optional[str] = None) -> ModeloConfig:
           """
           Elige el modelo óptimo para la tarea dada.

           Args:
               tarea: Descripción de la tarea
               modelo_override: Modelo explícito (overridea la selección automática)

           Returns:
               ModeloConfig con el modelo elegido
           """
           # Override explícito
           if modelo_override:
               modelos = await self.modelos_disponibles()
               for m in modelos:
                   if m.nombre == modelo_override and m.disponible:
                       logger.info(f"[selector_modelo] Override: {modelo_override}")
                       return m
               logger.warning(f"[selector_modelo] Override '{modelo_override}' no disponible, auto-seleccionando")

           complejidad = self.estimar_complejidad(tarea)
           logger.info(f"[selector_modelo] Complejidad estimada: {complejidad}")

           # Selección por complejidad con fallback
           if complejidad < 0.3:
               candidatos = [MODELO_LOCAL_SMALL, MODELO_LOCAL_CODER, MODELO_YEYONET_DEFAULT, MODELO_API_FALLBACK]
           elif complejidad < 0.6:
               candidatos = [MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL, MODELO_YEYONET_DEFAULT, MODELO_API_FALLBACK]
           elif complejidad < 0.8:
               candidatos = [MODELO_YEYONET_DEFAULT, MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL, MODELO_API_FALLBACK]
           else:
               candidatos = [MODELO_API_FALLBACK, MODELO_YEYONET_DEFAULT, MODELO_LOCAL_CODER, MODELO_LOCAL_SMALL]

           # Intentar cada candidato en orden (fallback graceful)
           for candidato in candidatos:
               if await self._esta_disponible(candidato):
                   logger.info(
                       f"[selector_modelo] Elegido: {candidato.nombre} "
                       f"(tipo={candidato.tipo}, complejidad={complejidad})"
                   )
                   return candidato

           # Último recurso: devolver el local pequeño aunque no responda
           logger.warning("[selector_modelo] Ningún modelo disponible, usando default")
           return MODELO_LOCAL_SMALL

       async def modelos_disponibles(self) -> List[ModeloConfig]:
           """
           Detecta qué modelos están disponibles:
           1. Modelos Ollama instalados localmente
           2. Nodos YeyoNet con GPU disponible
           3. APIs externas configuradas
           """
           if self._modelos_cache:
               return self._modelos_cache

           modelos: List[ModeloConfig] = []

           # 1. Modelos Ollama locales
           ollama_modelos = await self._detectar_ollama()
           modelos.extend(ollama_modelos)

           # 2. Nodos YeyoNet
           if self._yeyonet_endpoint:
               yeyonet = MODELO_YEYONET_DEFAULT
               yeyonet.endpoint = self._yeyonet_endpoint
               yeyonet.disponible = await self._check_yeyonet()
               modelos.append(yeyonet)

           # 3. API externa
           if self._api_key and self._api_endpoint:
               api = MODELO_API_FALLBACK
               api.endpoint = self._api_endpoint
               api.disponible = True
               modelos.append(api)

           self._modelos_cache = modelos
           logger.info(f"[selector_modelo] {len(modelos)} modelos detectados")
           return modelos

       def estimar_complejidad(self, tarea: str) -> float:
           """
           Estima complejidad 0.0-1.0 de una tarea.
           Factores: longitud, keywords técnicas, historial de tiempos.
           """
           tarea_lower = tarea.lower()

           # Factor 1: Longitud (0.0-0.3)
           longitud = len(tarea)
           if longitud > 1000:
               score_longitud = 0.3
           elif longitud > 500:
               score_longitud = 0.2
           elif longitud > 200:
               score_longitud = 0.1
           else:
               score_longitud = 0.05

           # Factor 2: Keywords (0.0-0.5)
           hits_alta = sum(1 for kw in KEYWORDS_ALTA_COMPLEJIDAD if kw in tarea_lower)
           hits_media = sum(1 for kw in KEYWORDS_MEDIA_COMPLEJIDAD if kw in tarea_lower)
           score_keywords = min((hits_alta * 0.15 + hits_media * 0.05), 0.5)

           # Factor 3: Historial de tiempos (0.0-0.2)
           score_historial = 0.0
           for key, tiempos in self._historial_tiempos.items():
               if any(word in tarea_lower for word in key.split()):
                   avg_time = sum(tiempos) / len(tiempos)
                   if avg_time > 10000:
                       score_historial = max(score_historial, 0.2)
                   elif avg_time > 5000:
                       score_historial = max(score_historial, 0.1)

           return round(min(score_longitud + score_keywords + score_historial, 1.0), 3)

       def registrar_tiempo(self, tarea_key: str, tiempo_ms: float) -> None:
           """Registra el tiempo de ejecución para mejorar estimaciones futuras."""
           if tarea_key not in self._historial_tiempos:
               self._historial_tiempos[tarea_key] = []
           self._historial_tiempos[tarea_key].append(tiempo_ms)
           if len(self._historial_tiempos[tarea_key]) > 20:
               self._historial_tiempos[tarea_key] = self._historial_tiempos[tarea_key][-20:]

       async def invalidar_cache(self) -> None:
           """Fuerza re-detección de modelos en la próxima llamada."""
           self._modelos_cache = None

       async def _detectar_ollama(self) -> List[ModeloConfig]:
           """Detecta modelos instalados en Ollama local."""
           modelos: List[ModeloConfig] = []
           try:
               async with httpx.AsyncClient(timeout=5.0) as client:
                   resp = await client.get(f"{self._ollama_host}/api/tags")
                   if resp.status_code == 200:
                       data = resp.json()
                       for model in data.get("models", []):
                           nombre = model.get("name", "")
                           size_bytes = model.get("size", 0)
                           vram_mb = int(size_bytes / (1024 * 1024)) if size_bytes else 2048

                           config = ModeloConfig(
                               nombre=nombre,
                               tipo="local",
                               vram_requerida_mb=vram_mb,
                               velocidad_estimada=30.0 if "3b" in nombre else 15.0,
                               calidad_estimada=0.7 if "3b" in nombre else 0.85,
                               disponible=True,
                               endpoint=self._ollama_host,
                           )
                           modelos.append(config)

                       logger.info(f"[selector_modelo] Ollama: {len(modelos)} modelos detectados")
           except Exception as e:
               logger.warning(f"[selector_modelo] Ollama no accesible: {e}")

           # Si no detectó nada, agregar defaults
           if not modelos:
               modelos.append(MODELO_LOCAL_SMALL)

           return modelos

       async def _check_yeyonet(self) -> bool:
           """Verifica si YeyoNet tiene nodos disponibles."""
           if not self._yeyonet_endpoint:
               return False
           try:
               async with httpx.AsyncClient(timeout=5.0) as client:
                   resp = await client.get(f"{self._yeyonet_endpoint}/health")
                   return resp.status_code == 200
           except Exception:
               return False

       async def _esta_disponible(self, modelo: ModeloConfig) -> bool:
           """Verifica si un modelo específico está disponible."""
           if modelo.tipo == "local":
               try:
                   async with httpx.AsyncClient(timeout=3.0) as client:
                       resp = await client.get(f"{self._ollama_host}/api/tags")
                       if resp.status_code == 200:
                           modelos = [m["name"] for m in resp.json().get("models", [])]
                           return modelo.nombre in modelos
               except Exception:
                   return False
           elif modelo.tipo == "yeyonet":
               return await self._check_yeyonet()
           elif modelo.tipo == "api":
               return bool(self._api_key and self._api_endpoint)
           return False


3. Crear archivo tests/unit/investigador/test_selector_modelo.py:

   Ruta: ~/yeyo-os/tests/unit/investigador/test_selector_modelo.py
   Contenido:

   """
   Tests unitarios para SelectorModelo.
   Micro-fase 5.32 — 8 tests.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock, patch

   from src.investigador.selector_modelo import SelectorModelo
   from src.investigador.modelos_selector import (
       ModeloConfig,
       MODELO_LOCAL_SMALL,
       MODELO_LOCAL_CODER,
       MODELO_YEYONET_DEFAULT,
       MODELO_API_FALLBACK,
   )


   @pytest.fixture
   def selector():
       return SelectorModelo(
           ollama_host="http://localhost:11434",
           yeyonet_endpoint=None,
           api_key=None,
       )


   def test_estimar_complejidad_simple(selector):
       comp = selector.estimar_complejidad("hola mundo")
       assert comp < 0.3


   def test_estimar_complejidad_media(selector):
       comp = selector.estimar_complejidad(
           "crear una API REST con database y authentication para middleware"
       )
       assert comp >= 0.15


   def test_estimar_complejidad_alta(selector):
       comp = selector.estimar_complejidad(
           "implementar un sistema distributed con machine learning "
           "concurrent processing y neural network optimization "
           "con security encryption para microservices"
       )
       assert comp >= 0.5


   @pytest.mark.asyncio
   async def test_elegir_modelo_simple(selector):
       with patch.object(selector, '_esta_disponible', return_value=True):
           modelo = await selector.elegir("hola")
           assert isinstance(modelo, ModeloConfig)
           assert modelo.tipo == "local"


   @pytest.mark.asyncio
   async def test_elegir_modelo_con_override(selector):
       modelo_mock = ModeloConfig(nombre="test:model", tipo="local", disponible=True)
       selector._modelos_cache = [modelo_mock]
       with patch.object(selector, '_esta_disponible', return_value=True):
           modelo = await selector.elegir("cualquier tarea", modelo_override="test:model")
           assert modelo.nombre == "test:model"


   @pytest.mark.asyncio
   async def test_fallback_si_no_disponible(selector):
       """Si el modelo preferido no está, baja al siguiente."""
       call_count = [0]

       async def disponible_selectivo(modelo):
           call_count[0] += 1
           return modelo.nombre == "qwen2.5:3b"

       with patch.object(selector, '_esta_disponible', side_effect=disponible_selectivo):
           modelo = await selector.elegir("tarea compleja con machine learning distributed")
           assert modelo.nombre == "qwen2.5:3b"


   def test_registrar_tiempo(selector):
       selector.registrar_tiempo("api_rest", 5000)
       selector.registrar_tiempo("api_rest", 6000)
       assert len(selector._historial_tiempos["api_rest"]) == 2


   @pytest.mark.asyncio
   async def test_invalidar_cache(selector):
       selector._modelos_cache = [MODELO_LOCAL_SMALL]
       await selector.invalidar_cache()
       assert selector._modelos_cache is None


   @pytest.mark.asyncio
   async def test_modelos_disponibles_default(selector):
       """Sin Ollama accesible, retorna al menos el modelo default."""
       modelos = await selector.modelos_disponibles()
       assert len(modelos) >= 1
       nombres = [m.nombre for m in modelos]
       assert "qwen2.5:3b" in nombres


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_selector_modelo.py -v
   Esperado: 8 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.selector_modelo import SelectorModelo; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.modelos_selector import ModeloConfig, MODELO_LOCAL_SMALL; print('OK')"
   Esperado: OK

SI FALLA:
- Si httpx no está instalado: pip install httpx (ya debería estar)
- Si falla la detección de Ollama: verificar que el test mockea correctamente _esta_disponible
- Si falla el import: verificar que modelos_selector.py está en src/investigador/

NO HACER:
- NO modificar src/ia/ollama_provider.py
- NO hardcodear API keys — siempre via env vars (YEYO_API_KEY, YEYO_API_ENDPOINT)
- NO hacer requests reales a Ollama en tests unitarios (mockear)
- NO crear un nuevo IAProvider — usar el existente con el modelo seleccionado

GATE:
✅ SelectorModelo elige automáticamente el modelo por complejidad estimada
✅ Detecta modelos Ollama instalados localmente via /api/tags
✅ Detecta nodos YeyoNet disponibles (si endpoint configurado)
✅ Soporta API externa como fallback (si YEYO_API_KEY configurado)
✅ Fallback graceful: si modelo preferido no disponible, baja al siguiente
✅ Cada nodo del grafo puede overridear con modelo explícito
✅ Historial de tiempos mejora estimaciones futuras
✅ 8 tests pasan
✅ ModeloConfig exportado correctamente para uso en YeyoOrquestador
```
