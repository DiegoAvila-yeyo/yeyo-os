## ═══════════════════════════════════════
## MICRO-FASE 4.14 — EstadoGrafo Core
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.14-1 [VSCODE] — Dataclass EstadoGrafo con serialización para checkpoints

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.14 de Capa 4 (Sistema Nervioso): crear el dataclass EstadoGrafo que es el objeto central que fluye entre todos los nodos del YeyoOrquestador.

CONTEXTO:
- Micro-fases 4.0-4.13 completadas: YEYO-PKG, instalador, permisos, containers, pipelines, etc.
- YeyoOrquestador es el orquestador nativo de YeyoOS (reemplaza OpenClaw)
- EstadoGrafo fluye entre todos los nodos: entrada → procesamiento → salida
- Debe ser serializable a JSON para checkpoints en Flash Memory
- El orquestador completo se implementará en micro-fases 4.14 a 4.23

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio:
   mkdir -p src/orquestador
   mkdir -p tests/unit/orquestador

2. Crear archivo src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 — Capa 4: Sistema Nervioso
   """
   from .estado import EstadoGrafo, EstadoGrafoError

3. Crear archivo src/orquestador/estado.py:

   Ruta: ~/yeyo-os/src/orquestador/estado.py
   Contenido:

   """
   YeyoOS — EstadoGrafo
   Micro-fase 4.14 — Capa 4: Sistema Nervioso

   Objeto central que fluye entre todos los nodos del YeyoOrquestador.
   Serializable a JSON para checkpoints en Flash Memory.
   """

   import json
   from dataclasses import dataclass, field, asdict
   from datetime import datetime, timezone
   from typing import Any, Optional
   from copy import deepcopy


   class EstadoGrafoError(Exception):
       """Error en la gestión de EstadoGrafo."""
       pass


   @dataclass
   class EstadoGrafo:
       """
       Objeto que fluye entre todos los nodos del YeyoOrquestador.

       - entrada: Input original (inmutable conceptualmente)
       - salida: Output acumulado por los nodos
       - contexto: Datos compartidos entre nodos (metadatos, scores, etc.)
       - nodo_actual: ID del nodo que se está ejecutando ahora mismo
       - historial: Lista ordenada de IDs de nodos ejecutados exitosamente
       - intentos: Conteo de intentos por nodo {nodo_id: n}
       - inicio: Timestamp de inicio de la ejecución del grafo
       - errores: Lista de errores con contexto {nodo_id, mensaje, timestamp}
       - memoria_ids: IDs de memorias creadas en Flash Memory durante la ejecución
       """

       entrada: dict
       salida: dict = field(default_factory=dict)
       contexto: dict = field(default_factory=dict)
       nodo_actual: str = ""
       historial: list = field(default_factory=list)
       intentos: dict = field(default_factory=dict)
       inicio: Optional[datetime] = field(default=None)
       errores: list = field(default_factory=list)
       memoria_ids: list = field(default_factory=list)

       def __post_init__(self):
           if self.inicio is None:
               self.inicio = datetime.now(timezone.utc)
           if not isinstance(self.entrada, dict):
               raise EstadoGrafoError("'entrada' debe ser un diccionario")

       # ─── Gestión de historial ────────────────────────────────────────────────

       def registrar_nodo_completado(self, nodo_id: str) -> None:
           """Registra un nodo como completado en el historial."""
           if not nodo_id:
               raise EstadoGrafoError("nodo_id no puede estar vacío")
           self.historial.append(nodo_id)

       def marcar_nodo_actual(self, nodo_id: str) -> None:
           """Marca el nodo que se está ejecutando actualmente."""
           self.nodo_actual = nodo_id

       def nodo_fue_ejecutado(self, nodo_id: str) -> bool:
           """Retorna True si el nodo ya fue ejecutado exitosamente."""
           return nodo_id in self.historial

       # ─── Gestión de intentos ─────────────────────────────────────────────────

       def incrementar_intento(self, nodo_id: str) -> int:
           """Incrementa el contador de intentos para un nodo. Retorna el nuevo conteo."""
           self.intentos[nodo_id] = self.intentos.get(nodo_id, 0) + 1
           return self.intentos[nodo_id]

       def obtener_intentos(self, nodo_id: str) -> int:
           """Retorna el número de intentos para un nodo (0 si nunca intentado)."""
           return self.intentos.get(nodo_id, 0)

       # ─── Gestión de errores ──────────────────────────────────────────────────

       def registrar_error(self, nodo_id: str, mensaje: str, detalle: Any = None) -> None:
           """Registra un error ocurrido en un nodo."""
           self.errores.append({
               "nodo_id": nodo_id,
               "mensaje": str(mensaje),
               "detalle": str(detalle) if detalle is not None else None,
               "timestamp": datetime.now(timezone.utc).isoformat(),
           })

       def tiene_errores(self) -> bool:
           """Retorna True si hay algún error registrado."""
           return len(self.errores) > 0

       def ultimo_error(self) -> Optional[dict]:
           """Retorna el último error registrado, o None si no hay errores."""
           return self.errores[-1] if self.errores else None

       # ─── Gestión de memoria ──────────────────────────────────────────────────

       def registrar_memoria(self, memoria_id: str) -> None:
           """Registra el ID de una memoria creada en Flash Memory."""
           if memoria_id not in self.memoria_ids:
               self.memoria_ids.append(memoria_id)

       # ─── Serialización ───────────────────────────────────────────────────────

       def a_dict(self) -> dict:
           """Serializa el estado a un diccionario JSON-compatible."""
           data = asdict(self)
           if self.inicio is not None:
               data["inicio"] = self.inicio.isoformat()
           return data

       def a_json(self) -> str:
           """Serializa el estado a JSON string."""
           return json.dumps(self.a_dict(), ensure_ascii=False, indent=2)

       @classmethod
       def desde_dict(cls, data: dict) -> "EstadoGrafo":
           """Reconstruye un EstadoGrafo desde un diccionario (checkpoint)."""
           data = dict(data)  # no mutar el original
           inicio_raw = data.pop("inicio", None)
           estado = cls(**data)
           if inicio_raw:
               if isinstance(inicio_raw, str):
                   estado.inicio = datetime.fromisoformat(inicio_raw)
               elif isinstance(inicio_raw, datetime):
                   estado.inicio = inicio_raw
           return estado

       @classmethod
       def desde_json(cls, json_str: str) -> "EstadoGrafo":
           """Reconstruye un EstadoGrafo desde un JSON string (checkpoint)."""
           data = json.loads(json_str)
           if not isinstance(data, dict):
               raise EstadoGrafoError("El JSON debe representar un diccionario")
           return cls.desde_dict(data)

       def clonar(self) -> "EstadoGrafo":
           """Retorna una copia profunda del estado."""
           return self.desde_dict(self.a_dict())

       # ─── Helpers ─────────────────────────────────────────────────────────────

       def duracion_segundos(self) -> float:
           """Retorna la duración en segundos desde el inicio."""
           if self.inicio is None:
               return 0.0
           ahora = datetime.now(timezone.utc)
           delta = ahora - self.inicio
           return delta.total_seconds()

       def __repr__(self) -> str:
           return (
               f"EstadoGrafo(nodo_actual={self.nodo_actual!r}, "
               f"historial={self.historial}, "
               f"errores={len(self.errores)})"
           )

4. Crear archivo tests/unit/orquestador/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/orquestador/test_estado.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_estado.py
   Contenido:

   """Tests para EstadoGrafo — Micro-fase 4.14"""

   import json
   import pytest
   from datetime import datetime, timezone
   from src.orquestador.estado import EstadoGrafo, EstadoGrafoError


   class TestEstadoGrafoCreacion:
       """Tests de creación del EstadoGrafo."""

       def test_creacion_minima(self):
           estado = EstadoGrafo(entrada={"texto": "hola"})
           assert estado.entrada == {"texto": "hola"}
           assert estado.salida == {}
           assert estado.contexto == {}
           assert estado.nodo_actual == ""
           assert estado.historial == []
           assert estado.intentos == {}
           assert estado.inicio is not None
           assert estado.errores == []
           assert estado.memoria_ids == []

       def test_creacion_con_todos_los_campos(self):
           inicio = datetime.now(timezone.utc)
           estado = EstadoGrafo(
               entrada={"texto": "hola"},
               salida={"respuesta": "mundo"},
               contexto={"usuario": "u1"},
               nodo_actual="nodo_chat",
               historial=["nodo_a", "nodo_b"],
               intentos={"nodo_a": 1},
               inicio=inicio,
               errores=[],
               memoria_ids=["mem-1"],
           )
           assert estado.salida == {"respuesta": "mundo"}
           assert estado.historial == ["nodo_a", "nodo_b"]
           assert estado.intentos == {"nodo_a": 1}
           assert estado.inicio == inicio

       def test_entrada_no_dict_falla(self):
           with pytest.raises(EstadoGrafoError):
               EstadoGrafo(entrada="no es un dict")

       def test_inicio_se_asigna_automaticamente(self):
           estado = EstadoGrafo(entrada={})
           assert isinstance(estado.inicio, datetime)
           assert estado.inicio.tzinfo is not None  # aware datetime

   class TestEstadoGrafoHistorial:
       """Tests de gestión del historial."""

       def test_registrar_nodo_completado(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_nodo_completado("nodo_a")
           assert "nodo_a" in estado.historial

       def test_historial_mantiene_orden(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_nodo_completado("nodo_a")
           estado.registrar_nodo_completado("nodo_b")
           estado.registrar_nodo_completado("nodo_c")
           assert estado.historial == ["nodo_a", "nodo_b", "nodo_c"]

       def test_nodo_vacio_falla(self):
           estado = EstadoGrafo(entrada={})
           with pytest.raises(EstadoGrafoError):
               estado.registrar_nodo_completado("")

       def test_nodo_fue_ejecutado_true(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_nodo_completado("nodo_a")
           assert estado.nodo_fue_ejecutado("nodo_a") is True

       def test_nodo_fue_ejecutado_false(self):
           estado = EstadoGrafo(entrada={})
           assert estado.nodo_fue_ejecutado("nodo_inexistente") is False

       def test_marcar_nodo_actual(self):
           estado = EstadoGrafo(entrada={})
           estado.marcar_nodo_actual("nodo_generador")
           assert estado.nodo_actual == "nodo_generador"

   class TestEstadoGrafoIntentos:
       """Tests de gestión de intentos."""

       def test_primer_intento_retorna_1(self):
           estado = EstadoGrafo(entrada={})
           assert estado.incrementar_intento("nodo_a") == 1

       def test_segundo_intento_retorna_2(self):
           estado = EstadoGrafo(entrada={})
           estado.incrementar_intento("nodo_a")
           assert estado.incrementar_intento("nodo_a") == 2

       def test_obtener_intentos_sin_intento_retorna_0(self):
           estado = EstadoGrafo(entrada={})
           assert estado.obtener_intentos("nodo_nuevo") == 0

       def test_obtener_intentos_despues_de_incrementar(self):
           estado = EstadoGrafo(entrada={})
           estado.incrementar_intento("nodo_a")
           estado.incrementar_intento("nodo_a")
           assert estado.obtener_intentos("nodo_a") == 2

       def test_intentos_independientes_por_nodo(self):
           estado = EstadoGrafo(entrada={})
           estado.incrementar_intento("nodo_a")
           estado.incrementar_intento("nodo_a")
           estado.incrementar_intento("nodo_b")
           assert estado.obtener_intentos("nodo_a") == 2
           assert estado.obtener_intentos("nodo_b") == 1

   class TestEstadoGrafoErrores:
       """Tests de gestión de errores."""

       def test_registrar_error(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_error("nodo_a", "Timeout")
           assert estado.tiene_errores() is True
           assert len(estado.errores) == 1

       def test_error_tiene_campos_correctos(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_error("nodo_a", "Error de red", {"codigo": 500})
           error = estado.errores[0]
           assert error["nodo_id"] == "nodo_a"
           assert error["mensaje"] == "Error de red"
           assert "timestamp" in error

       def test_sin_errores_tiene_errores_false(self):
           estado = EstadoGrafo(entrada={})
           assert estado.tiene_errores() is False

       def test_ultimo_error_none_si_no_hay_errores(self):
           estado = EstadoGrafo(entrada={})
           assert estado.ultimo_error() is None

       def test_ultimo_error_retorna_el_mas_reciente(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_error("nodo_a", "Error 1")
           estado.registrar_error("nodo_b", "Error 2")
           assert estado.ultimo_error()["nodo_id"] == "nodo_b"

   class TestEstadoGrafoSerializacion:
       """Tests de serialización/deserialización."""

       def test_a_dict_produce_diccionario(self):
           estado = EstadoGrafo(entrada={"texto": "hola"})
           d = estado.a_dict()
           assert isinstance(d, dict)
           assert d["entrada"] == {"texto": "hola"}

       def test_inicio_se_serializa_como_string(self):
           estado = EstadoGrafo(entrada={})
           d = estado.a_dict()
           assert isinstance(d["inicio"], str)

       def test_a_json_produce_string(self):
           estado = EstadoGrafo(entrada={"x": 1})
           j = estado.a_json()
           assert isinstance(j, str)
           data = json.loads(j)
           assert data["entrada"] == {"x": 1}

       def test_desde_dict_reconstruye_correctamente(self):
           original = EstadoGrafo(entrada={"texto": "test"})
           original.registrar_nodo_completado("nodo_a")
           original.incrementar_intento("nodo_a")
           original.salida["resultado"] = "ok"

           d = original.a_dict()
           reconstruido = EstadoGrafo.desde_dict(d)

           assert reconstruido.entrada == original.entrada
           assert reconstruido.salida == original.salida
           assert reconstruido.historial == original.historial
           assert reconstruido.intentos == original.intentos

       def test_desde_json_roundtrip(self):
           original = EstadoGrafo(entrada={"msg": "hola mundo"})
           original.registrar_nodo_completado("nodo_chat")
           original.registrar_error("nodo_b", "falló")

           json_str = original.a_json()
           reconstruido = EstadoGrafo.desde_json(json_str)

           assert reconstruido.entrada == original.entrada
           assert reconstruido.historial == original.historial
           assert len(reconstruido.errores) == 1

       def test_clonar_produce_copia_independiente(self):
           original = EstadoGrafo(entrada={"x": 1})
           clon = original.clonar()
           clon.salida["nuevo"] = "dato"
           assert "nuevo" not in original.salida

       def test_desde_json_invalido_falla(self):
           with pytest.raises(Exception):
               EstadoGrafo.desde_json('"solo un string"')

   class TestEstadoGrafoHelpers:
       """Tests de métodos helper."""

       def test_duracion_segundos(self):
           estado = EstadoGrafo(entrada={})
           import time
           time.sleep(0.01)
           duracion = estado.duracion_segundos()
           assert duracion >= 0.01
           assert duracion < 5.0  # no más de 5s

       def test_registrar_memoria(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_memoria("mem-abc123")
           assert "mem-abc123" in estado.memoria_ids

       def test_registrar_memoria_no_duplica(self):
           estado = EstadoGrafo(entrada={})
           estado.registrar_memoria("mem-abc123")
           estado.registrar_memoria("mem-abc123")
           assert estado.memoria_ids.count("mem-abc123") == 1

       def test_repr_informativo(self):
           estado = EstadoGrafo(entrada={})
           estado.marcar_nodo_actual("nodo_chat")
           repr_str = repr(estado)
           assert "nodo_chat" in repr_str

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_estado.py -v

VERIFICAR:
- [ ] Directorio src/orquestador/ existe con __init__.py y estado.py
- [ ] EstadoGrafo se crea con valores por defecto correctos
- [ ] inicio se asigna automáticamente como datetime UTC
- [ ] historial mantiene orden de ejecución
- [ ] intentos se cuentan por nodo independientemente
- [ ] errores incluyen nodo_id, mensaje, timestamp
- [ ] a_json() / desde_json() roundtrip funciona
- [ ] clonar() produce copia independiente (deep copy)
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar que src/orquestador/__init__.py importa EstadoGrafo
- datetime timezone: usar datetime.now(timezone.utc) no datetime.utcnow()
- JSON serialization: asdict() de dataclass puede requerir manejo especial de datetime

NO HACER:
- No implementar Nodo aún (eso es micro-fase 4.15)
- No conectar con Flash Memory aún (eso es micro-fase 5.22)
- No implementar el ejecutor del grafo (eso es micro-fase 4.17)

GATE: EstadoGrafo serializa/deserializa correctamente vía JSON, registra historial en orden, cuenta intentos por nodo independientemente, errores tienen contexto completo, todos los tests pasan.
```
