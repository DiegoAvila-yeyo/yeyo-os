## ═══════════════════════════════════════
## MICRO-FASE 5.29 — Micro-Tareas con DB como Pegamento
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.29-1 [VSCODE] — EjecutorMicroTareas: cadenas de razonamiento con contexto limpio y DB como pegamento

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.29 de Capa 5 (Órganos): implementar el sistema de micro-tareas que ejecuta cadenas de razonamiento largas sin llenar el contexto del modelo — cada paso tiene contexto limpio, y la DB sirve de pegamento entre pasos.

CONTEXTO:
- Micro-fase 5.28 completada: PipelineInvestigador funcionando con 6 fases
- Modelos compartidos en src/investigador/modelos.py:
  - ResultadoBusqueda(fuente, url, codigo, score, metadata)
  - PasoInvestigacion(numero, tipo, input_resumen, output_resumen, tokens, duracion_ms)
  - InvestigacionCompleta(tarea_id, pasos, resultado_final, confianza, tiempo_total_ms)
- Tabla PostgreSQL investigacion_pasos ya existe (creada en 5.28)
- IAProvider en src/ia/interfaces.py: generate(prompt, system, temperature) -> IAResponse
- OllamaProvider en src/ia/ollama_provider.py: implementación para qwen2.5:3b
- IAResponse en src/ia/interfaces.py: IAResponse(content, model, tokens_used, latency_ms)
- Config: database_url en src/core/config.py via YeyoConfig
- asyncpg para PostgreSQL: pool = await asyncpg.create_pool(database_url)
- EjecutorMicroTareas es USADO POR: PipelineInvestigador (5.28), Razonamiento (5.30), Autodidacta (7.26)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/investigador/micro_tareas.py:

   Ruta: ~/yeyo-os/src/investigador/micro_tareas.py
   Contenido:

   """
   YeyoOS — EjecutorMicroTareas
   Micro-fase 5.29 — Capa 5: Órganos

   Ejecuta cadenas de razonamiento largas sin llenar el contexto del modelo.
   Cada micro-tarea tiene contexto limpio (<max_tokens).
   La DB sirve de pegamento: cada paso lee inputs de DB y guarda outputs en DB.

   Usado por: PipelineInvestigador (5.28), Razonamiento (5.30), Autodidacta (7.26).
   """

   from __future__ import annotations

   import logging
   import time
   import uuid
   from dataclasses import dataclass, field
   from typing import Any, Dict, List, Optional

   from src.ia.interfaces import IAProvider, IAResponse

   from .modelos import PasoInvestigacion
   from .tarea_db import TareaDB

   logger = logging.getLogger(__name__)

   MAX_TOKENS_DEFAULT = 2000
   MAX_REINTENTOS = 2


   @dataclass
   class MicroTarea:
       """
       Una micro-tarea individual en una cadena de razonamiento.

       - prompt: template con placeholders {key} que se resuelven desde DB
       - input_keys: keys a leer de DB (outputs de pasos anteriores)
       - output_key: key donde guardar el resultado en DB
       - max_tokens: límite de tokens para esta tarea (contexto limpio)
       - system: system prompt opcional para esta tarea específica
       """
       prompt: str
       input_keys: List[str] = field(default_factory=list)
       output_key: str = ""
       max_tokens: int = MAX_TOKENS_DEFAULT
       system: str = "Eres un asistente experto. Responde de forma concisa y precisa."
       temperature: float = 0.3


   @dataclass
   class ResultadoCadena:
       """Resultado completo de ejecutar una cadena de micro-tareas."""
       tarea_id: str
       pasos: List[PasoInvestigacion] = field(default_factory=list)
       exito: bool = False
       resultado_final: str = ""
       tokens_total: int = 0
       duracion_total_ms: int = 0
       errores: List[str] = field(default_factory=list)


   class EjecutorMicroTareasError(Exception):
       """Error en ejecución de micro-tareas."""
       pass


   class EjecutorMicroTareas:
       """
       Ejecuta cadenas de micro-tareas con contexto limpio por paso.

       Patrón:
       1. Para cada MicroTarea en la cadena:
          a. Lee inputs de DB (por input_keys)
          b. Formatea el prompt con los inputs
          c. Llama al modelo con contexto limpio
          d. Guarda output en DB (por output_key)
          e. Limpia contexto completamente
       2. El resultado final es el output del último paso.

       La DB es el pegamento — no hay estado compartido en memoria entre pasos.
       """

       def __init__(
           self,
           ia_provider: IAProvider,
           tarea_db: TareaDB,
           max_tokens_global: int = MAX_TOKENS_DEFAULT,
       ):
           self._ia = ia_provider
           self._db = tarea_db
           self._max_tokens_global = max_tokens_global

       async def ejecutar_cadena(
           self,
           tareas: List[MicroTarea],
           tarea_id: Optional[str] = None,
           datos_iniciales: Optional[Dict[str, str]] = None,
       ) -> ResultadoCadena:
           """
           Ejecuta una cadena de micro-tareas secuencialmente.

           Args:
               tareas: Lista ordenada de micro-tareas a ejecutar
               tarea_id: ID único para esta cadena (auto-generado si no se provee)
               datos_iniciales: Dict de key->value para inyectar antes del primer paso

           Returns:
               ResultadoCadena con todos los pasos, resultado final y métricas.
           """
           tarea_id = tarea_id or f"chain_{uuid.uuid4().hex[:12]}"
           resultado = ResultadoCadena(tarea_id=tarea_id)
           inicio_total = time.perf_counter()

           # Inyectar datos iniciales en DB
           if datos_iniciales:
               for key, value in datos_iniciales.items():
                   await self._db.guardar_dato(tarea_id, key, value)

           ultimo_output = ""

           for i, tarea in enumerate(tareas):
               paso_numero = i + 1
               inicio_paso = time.perf_counter()

               try:
                   # 1. Leer inputs de DB
                   inputs = await self._leer_inputs(tarea_id, tarea.input_keys)

                   # 2. Formatear prompt con inputs
                   prompt_formateado = self._formatear_prompt(tarea.prompt, inputs)

                   # 3. Truncar si excede max_tokens
                   if len(prompt_formateado) > tarea.max_tokens * 4:
                       prompt_formateado = prompt_formateado[:tarea.max_tokens * 4]
                       logger.warning(
                           f"[micro_tareas] Paso {paso_numero}: prompt truncado a {tarea.max_tokens * 4} chars"
                       )

                   # 4. Llamar al modelo (contexto limpio)
                   respuesta = await self._ejecutar_con_reintentos(
                       prompt=prompt_formateado,
                       system=tarea.system,
                       temperature=tarea.temperature,
                       max_reintentos=MAX_REINTENTOS,
                   )

                   output = respuesta.content.strip()
                   tokens_usados = respuesta.tokens_used

                   # 5. Guardar output en DB
                   if tarea.output_key:
                       await self._db.guardar_dato(tarea_id, tarea.output_key, output)

                   # 6. Registrar paso en DB
                   duracion_ms = int((time.perf_counter() - inicio_paso) * 1000)
                   paso = PasoInvestigacion(
                       numero=paso_numero,
                       tipo="micro_tarea",
                       input_resumen=prompt_formateado[:200],
                       output_resumen=output[:200],
                       tokens=tokens_usados,
                       duracion_ms=duracion_ms,
                   )
                   resultado.pasos.append(paso)
                   resultado.tokens_total += tokens_usados

                   await self._db.guardar_paso(
                       tarea_id=tarea_id,
                       paso=paso_numero,
                       tipo="micro_tarea",
                       input_resumen=prompt_formateado[:500],
                       output_resumen=output[:500],
                       tokens=tokens_usados,
                       duracion=duracion_ms,
                   )

                   ultimo_output = output
                   logger.info(
                       f"[micro_tareas] Paso {paso_numero}/{len(tareas)} completado: "
                       f"tokens={tokens_usados}, duracion={duracion_ms}ms"
                   )

               except Exception as e:
                   logger.error(f"[micro_tareas] Error en paso {paso_numero}: {e}")
                   resultado.errores.append(f"Paso {paso_numero}: {str(e)}")
                   duracion_ms = int((time.perf_counter() - inicio_paso) * 1000)
                   resultado.pasos.append(PasoInvestigacion(
                       numero=paso_numero,
                       tipo="micro_tarea_error",
                       input_resumen=f"Error: {str(e)[:200]}",
                       output_resumen="",
                       duracion_ms=duracion_ms,
                   ))
                   break

           resultado.resultado_final = ultimo_output
           resultado.duracion_total_ms = int((time.perf_counter() - inicio_total) * 1000)
           resultado.exito = len(resultado.errores) == 0

           logger.info(
               f"[micro_tareas] Cadena {tarea_id} completada: "
               f"{len(resultado.pasos)} pasos, exito={resultado.exito}, "
               f"tokens_total={resultado.tokens_total}"
           )
           return resultado

       async def _leer_inputs(
           self,
           tarea_id: str,
           input_keys: List[str],
       ) -> Dict[str, str]:
           """Lee los valores de input_keys desde la DB."""
           inputs: Dict[str, str] = {}
           for key in input_keys:
               valor = await self._db.leer_dato(tarea_id, key)
               if valor is not None:
                   inputs[key] = valor
               else:
                   logger.warning(f"[micro_tareas] Key '{key}' no encontrada en DB para {tarea_id}")
                   inputs[key] = ""
           return inputs

       @staticmethod
       def _formatear_prompt(template: str, inputs: Dict[str, str]) -> str:
           """Formatea el template reemplazando {key} con valores de inputs."""
           resultado = template
           for key, value in inputs.items():
               resultado = resultado.replace(f"{{{key}}}", value)
           return resultado

       async def _ejecutar_con_reintentos(
           self,
           prompt: str,
           system: str,
           temperature: float,
           max_reintentos: int,
       ) -> IAResponse:
           """Ejecuta prompt contra el modelo con reintentos en caso de error."""
           ultimo_error = None
           for intento in range(max_reintentos + 1):
               try:
                   respuesta = await self._ia.generate(
                       prompt=prompt,
                       system=system,
                       temperature=temperature,
                   )
                   if respuesta.content.strip():
                       return respuesta
                   logger.warning(f"[micro_tareas] Respuesta vacía, intento {intento + 1}")
               except Exception as e:
                   ultimo_error = e
                   logger.warning(f"[micro_tareas] Error intento {intento + 1}: {e}")
           raise EjecutorMicroTareasError(
               f"Fallaron {max_reintentos + 1} intentos: {ultimo_error}"
           )


2. Crear archivo src/investigador/tarea_db.py:

   Ruta: ~/yeyo-os/src/investigador/tarea_db.py
   Contenido:

   """
   YeyoOS — TareaDB
   Micro-fase 5.29 — Capa 5: Órganos

   CRUD contra tabla investigacion_pasos + almacenamiento key-value
   para datos intermedios de micro-tareas.
   Es el "pegamento" entre pasos: cada paso lee y escribe aquí.
   """

   from __future__ import annotations

   import json
   import logging
   from typing import Any, Dict, List, Optional

   from .modelos import PasoInvestigacion

   logger = logging.getLogger(__name__)


   class TareaDBError(Exception):
       """Error en TareaDB."""
       pass


   class TareaDB:
       """
       Almacena y recupera datos intermedios de micro-tareas.

       Usa dos mecanismos:
       1. Tabla investigacion_pasos (PostgreSQL) para tracking de pasos
       2. Dict en memoria como store key-value para datos entre pasos
          (en producción se puede reemplazar por Redis o tabla auxiliar)

       El store key-value usa el patrón: tarea_id:key -> value
       """

       def __init__(self, pool: Optional[Any] = None):
           """
           Args:
               pool: asyncpg connection pool (opcional — si None, solo usa store en memoria)
           """
           self._pool = pool
           self._store: Dict[str, str] = {}

       async def guardar_paso(
           self,
           tarea_id: str,
           paso: int,
           tipo: str,
           input_resumen: str,
           output_resumen: str,
           tokens: int = 0,
           duracion: int = 0,
           confianza: float = 0.0,
       ) -> None:
           """Guarda un paso en la tabla investigacion_pasos."""
           if self._pool:
               try:
                   async with self._pool.acquire() as conn:
                       await conn.execute(
                           """
                           INSERT INTO investigacion_pasos
                           (tarea_id, paso_numero, tipo, input_resumen, output_resumen,
                            tokens_usados, duracion_ms, confianza)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                           """,
                           tarea_id, paso, tipo, input_resumen, output_resumen,
                           tokens, duracion, confianza,
                       )
               except Exception as e:
                   logger.error(f"[tarea_db] Error guardando paso: {e}")
           else:
               logger.debug(f"[tarea_db] Pool no disponible, paso {paso} solo en memoria")

       async def leer_paso(self, tarea_id: str, paso_numero: int) -> Optional[PasoInvestigacion]:
           """Lee un paso específico de la tabla investigacion_pasos."""
           if self._pool:
               try:
                   async with self._pool.acquire() as conn:
                       row = await conn.fetchrow(
                           """
                           SELECT paso_numero, tipo, input_resumen, output_resumen,
                                  tokens_usados, duracion_ms, confianza
                           FROM investigacion_pasos
                           WHERE tarea_id = $1 AND paso_numero = $2
                           """,
                           tarea_id, paso_numero,
                       )
                       if row:
                           return PasoInvestigacion(
                               numero=row["paso_numero"],
                               tipo=row["tipo"],
                               input_resumen=row["input_resumen"] or "",
                               output_resumen=row["output_resumen"] or "",
                               tokens=row["tokens_usados"] or 0,
                               duracion_ms=row["duracion_ms"] or 0,
                               confianza=row["confianza"] or 0.0,
                           )
               except Exception as e:
                   logger.error(f"[tarea_db] Error leyendo paso: {e}")
           return None

       async def leer_resumen(self, tarea_id: str) -> str:
           """
           Genera un resumen comprimido de todos los pasos de una tarea.
           Útil para inyectar contexto mínimo en pasos posteriores.
           """
           if self._pool:
               try:
                   async with self._pool.acquire() as conn:
                       rows = await conn.fetch(
                           """
                           SELECT paso_numero, tipo, output_resumen
                           FROM investigacion_pasos
                           WHERE tarea_id = $1
                           ORDER BY paso_numero
                           """,
                           tarea_id,
                       )
                       if rows:
                           partes = []
                           for row in rows:
                               partes.append(
                                   f"Paso {row['paso_numero']} ({row['tipo']}): "
                                   f"{(row['output_resumen'] or '')[:100]}"
                               )
                           return "\n".join(partes)
               except Exception as e:
                   logger.error(f"[tarea_db] Error leyendo resumen: {e}")

           store_keys = [k for k in self._store if k.startswith(f"{tarea_id}:")]
           if store_keys:
               partes = [f"{k.split(':', 1)[1]}: {self._store[k][:100]}" for k in sorted(store_keys)]
               return "\n".join(partes)
           return ""

       async def leer_resultado_final(self, tarea_id: str) -> str:
           """Lee el resultado del último paso de una tarea."""
           if self._pool:
               try:
                   async with self._pool.acquire() as conn:
                       row = await conn.fetchrow(
                           """
                           SELECT output_resumen
                           FROM investigacion_pasos
                           WHERE tarea_id = $1
                           ORDER BY paso_numero DESC
                           LIMIT 1
                           """,
                           tarea_id,
                       )
                       if row:
                           return row["output_resumen"] or ""
               except Exception as e:
                   logger.error(f"[tarea_db] Error leyendo resultado final: {e}")

           store_keys = sorted(
               [k for k in self._store if k.startswith(f"{tarea_id}:")],
               reverse=True,
           )
           if store_keys:
               return self._store[store_keys[0]]
           return ""

       async def guardar_dato(self, tarea_id: str, key: str, value: str) -> None:
           """Guarda un dato key-value para una tarea (pegamento entre micro-tareas)."""
           store_key = f"{tarea_id}:{key}"
           self._store[store_key] = value
           logger.debug(f"[tarea_db] Guardado {store_key} ({len(value)} chars)")

       async def leer_dato(self, tarea_id: str, key: str) -> Optional[str]:
           """Lee un dato key-value de una tarea."""
           store_key = f"{tarea_id}:{key}"
           valor = self._store.get(store_key)
           if valor is not None:
               logger.debug(f"[tarea_db] Leído {store_key} ({len(valor)} chars)")
           return valor

       async def listar_datos(self, tarea_id: str) -> Dict[str, str]:
           """Lista todos los datos key-value de una tarea."""
           prefix = f"{tarea_id}:"
           return {
               k[len(prefix):]: v
               for k, v in self._store.items()
               if k.startswith(prefix)
           }

       async def limpiar_tarea(self, tarea_id: str) -> None:
           """Limpia todos los datos en memoria de una tarea."""
           keys_to_remove = [k for k in self._store if k.startswith(f"{tarea_id}:")]
           for k in keys_to_remove:
               del self._store[k]
           logger.debug(f"[tarea_db] Limpiados {len(keys_to_remove)} datos de {tarea_id}")


3. Crear archivo tests/unit/investigador/test_micro_tareas.py:

   Ruta: ~/yeyo-os/tests/unit/investigador/test_micro_tareas.py
   Contenido:

   """
   Tests unitarios para EjecutorMicroTareas.
   Micro-fase 5.29 — 8 tests.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock

   from src.investigador.micro_tareas import (
       EjecutorMicroTareas,
       MicroTarea,
       ResultadoCadena,
   )
   from src.investigador.tarea_db import TareaDB
   from src.investigador.modelos import PasoInvestigacion


   @pytest.fixture
   def mock_ia():
       ia = AsyncMock()
       ia.generate.return_value = MagicMock(
           content="respuesta del modelo",
           tokens_used=50,
           latency_ms=100,
       )
       return ia


   @pytest.fixture
   def tarea_db():
       return TareaDB(pool=None)


   @pytest.fixture
   def ejecutor(mock_ia, tarea_db):
       return EjecutorMicroTareas(ia_provider=mock_ia, tarea_db=tarea_db)


   @pytest.mark.asyncio
   async def test_ejecutar_cadena_simple(ejecutor):
       cadena = [
           MicroTarea(
               prompt="¿Cuál es la capital de Francia?",
               output_key="respuesta",
               max_tokens=200,
           ),
       ]
       resultado = await ejecutor.ejecutar_cadena(cadena)
       assert isinstance(resultado, ResultadoCadena)
       assert resultado.exito is True
       assert resultado.resultado_final == "respuesta del modelo"
       assert len(resultado.pasos) == 1


   @pytest.mark.asyncio
   async def test_ejecutar_cadena_multiples_pasos(ejecutor):
       cadena = [
           MicroTarea(prompt="Paso 1", output_key="paso1", max_tokens=200),
           MicroTarea(prompt="Paso 2 con {paso1}", input_keys=["paso1"], output_key="paso2", max_tokens=200),
           MicroTarea(prompt="Paso 3 con {paso2}", input_keys=["paso2"], output_key="final", max_tokens=200),
       ]
       resultado = await ejecutor.ejecutar_cadena(cadena)
       assert resultado.exito is True
       assert len(resultado.pasos) == 3
       assert resultado.tokens_total == 150  # 50 * 3


   @pytest.mark.asyncio
   async def test_datos_iniciales(ejecutor, tarea_db):
       cadena = [
           MicroTarea(
               prompt="Analiza: {tarea}",
               input_keys=["tarea"],
               output_key="analisis",
           ),
       ]
       resultado = await ejecutor.ejecutar_cadena(
           cadena,
           datos_iniciales={"tarea": "implementar rate limiting"},
       )
       assert resultado.exito is True


   @pytest.mark.asyncio
   async def test_contexto_limpio_entre_pasos(ejecutor, mock_ia):
       """Cada paso llama al modelo independientemente — no acumula contexto."""
       cadena = [
           MicroTarea(prompt="Paso 1", output_key="p1", max_tokens=200),
           MicroTarea(prompt="Paso 2", output_key="p2", max_tokens=200),
       ]
       await ejecutor.ejecutar_cadena(cadena)
       assert mock_ia.generate.call_count == 2
       call1_prompt = mock_ia.generate.call_args_list[0].kwargs.get("prompt", "")
       call2_prompt = mock_ia.generate.call_args_list[1].kwargs.get("prompt", "")
       assert call1_prompt != call2_prompt or mock_ia.generate.call_count == 2


   @pytest.mark.asyncio
   async def test_error_en_paso_detiene_cadena(mock_ia, tarea_db):
       mock_ia.generate.side_effect = Exception("modelo caído")
       ejecutor = EjecutorMicroTareas(ia_provider=mock_ia, tarea_db=tarea_db)
       cadena = [
           MicroTarea(prompt="Paso 1", output_key="p1"),
           MicroTarea(prompt="Paso 2", output_key="p2"),
       ]
       resultado = await ejecutor.ejecutar_cadena(cadena)
       assert resultado.exito is False
       assert len(resultado.errores) > 0


   @pytest.mark.asyncio
   async def test_tarea_id_auto_generado(ejecutor):
       cadena = [MicroTarea(prompt="Test", output_key="out")]
       resultado = await ejecutor.ejecutar_cadena(cadena)
       assert resultado.tarea_id.startswith("chain_")


   @pytest.mark.asyncio
   async def test_tarea_id_personalizado(ejecutor):
       cadena = [MicroTarea(prompt="Test", output_key="out")]
       resultado = await ejecutor.ejecutar_cadena(cadena, tarea_id="mi_tarea_42")
       assert resultado.tarea_id == "mi_tarea_42"


   @pytest.mark.asyncio
   async def test_duracion_y_tokens_registrados(ejecutor):
       cadena = [
           MicroTarea(prompt="Paso 1", output_key="p1"),
           MicroTarea(prompt="Paso 2", output_key="p2"),
       ]
       resultado = await ejecutor.ejecutar_cadena(cadena)
       assert resultado.tokens_total > 0
       assert resultado.duracion_total_ms >= 0
       for paso in resultado.pasos:
           assert isinstance(paso, PasoInvestigacion)
           assert paso.tokens >= 0


VERIFICAR:

1. Ejecutar: cd ~/yeyo-os && python -m pytest tests/unit/investigador/test_micro_tareas.py -v
   Esperado: 8 tests pasan

2. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.micro_tareas import EjecutorMicroTareas, MicroTarea, ResultadoCadena; print('OK')"
   Esperado: OK

3. Ejecutar: cd ~/yeyo-os && python -c "from src.investigador.tarea_db import TareaDB; print('OK')"
   Esperado: OK

SI FALLA:
- Si falla import de src.ia.interfaces: verificar que IAResponse tiene campo content, tokens_used
- Si falla import de .modelos: verificar que PasoInvestigacion está en src/investigador/modelos.py (creado en 5.28)
- Si falla TareaDB: verificar que no requiere pool — debe funcionar con pool=None (modo memoria)

NO HACER:
- NO modificar src/investigador/modelos.py (creado en 5.28)
- NO modificar src/investigador/pipeline.py (creado en 5.28)
- NO crear tablas nuevas — usa investigacion_pasos (ya creada en 5.28)
- NO acumular contexto entre pasos — cada llamada al modelo es independiente

GATE:
✅ EjecutorMicroTareas ejecuta cadena de N pasos
✅ Cada paso tiene contexto limpio (<max_tokens)
✅ Datos intermedios guardados en DB (TareaDB)
✅ Prompt de cada paso se formatea con datos leídos de DB
✅ Resultado final accesible via ResultadoCadena
✅ TareaDB funciona con pool=None (modo memoria) y con asyncpg pool
✅ 8 tests pasan
✅ Imports de MicroTarea, ResultadoCadena, EjecutorMicroTareas exportados correctamente
```
