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
