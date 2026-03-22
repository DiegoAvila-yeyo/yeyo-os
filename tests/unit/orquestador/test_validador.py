"""Tests para GrafoValidador con análisis AST — Micro-fase 5.25"""

import pytest
from src.orquestador.validador import GrafoValidador, ValidationResult


CODIGO_VALIDO = '''
async def fn_nodo(estado):
    estado.salida["resultado"] = "ok"
    return estado

nodo_test = NodoFuncion(id="paso1", fn=fn_nodo, timeout=30.0)
grafo = (
    YeyoGrafo("grafo_valido", "Grafo de prueba")
    .agregar_nodo(nodo_test)
    .inicio("paso1")
    .fin("paso1")
)
'''


class TestValidacionCodeValido:

    def test_codigo_valido_pasa(self):
        v = GrafoValidador()
        result = v.validar(CODIGO_VALIDO)
        assert result.is_valid is True
        assert len(result.errores) == 0

    def test_codigo_vacio_falla(self):
        v = GrafoValidador()
        result = v.validar("")
        assert result.is_valid is False

    def test_codigo_con_solo_espacio_falla(self):
        v = GrafoValidador()
        result = v.validar("   \n  ")
        assert result.is_valid is False

    def test_validation_result_tiene_errores(self):
        v = GrafoValidador()
        result = v.validar("")
        assert isinstance(result.errores, list)
        assert isinstance(result.advertencias, list)


class TestValidacionImports:

    def test_import_os_rechazado(self):
        v = GrafoValidador()
        result = v.validar("import os\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False
        assert any("os" in e for e in result.errores)

    def test_import_sys_rechazado(self):
        v = GrafoValidador()
        result = v.validar("import sys\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_import_subprocess_rechazado(self):
        v = GrafoValidador()
        result = v.validar("import subprocess\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_from_os_import_rechazado(self):
        v = GrafoValidador()
        result = v.validar("from os import system\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_import_orquestador_permitido(self):
        v = GrafoValidador()
        result = v.validar(
            "from src.orquestador.nodo import NodoFuncion\n"
            "grafo = YeyoGrafo('x', 'y')"
        )
        errores_import = [e for e in result.errores if "Import prohibido" in e]
        assert len(errores_import) == 0

    def test_import_socket_rechazado(self):
        v = GrafoValidador()
        result = v.validar("import socket\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_import_requests_rechazado(self):
        v = GrafoValidador()
        result = v.validar("import requests\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False


class TestValidacionBuiltins:

    def test_eval_rechazado(self):
        v = GrafoValidador()
        result = v.validar("x = eval('1+1')\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False
        assert any("eval" in e for e in result.errores)

    def test_exec_rechazado(self):
        v = GrafoValidador()
        result = v.validar("exec('print(1)')\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False
        assert any("exec" in e for e in result.errores)

    def test_compile_rechazado(self):
        v = GrafoValidador()
        result = v.validar("c = compile('x=1', '', 'exec')\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_open_rechazado(self):
        v = GrafoValidador()
        result = v.validar("f = open('/etc/passwd')\ngrafo = YeyoGrafo('x', 'y')")
        assert result.is_valid is False

    def test_dunder_import_rechazado(self):
        v = GrafoValidador()
        result = v.validar(
            "m = __import__('os')\ngrafo = YeyoGrafo('x', 'y')"
        )
        assert result.is_valid is False


class TestValidacionAtributos:

    def test_dunder_class_rechazado(self):
        v = GrafoValidador()
        result = v.validar(
            "x = YeyoGrafo.__class__\ngrafo = YeyoGrafo('x', 'y')"
        )
        assert result.is_valid is False

    def test_dunder_subclasses_rechazado(self):
        v = GrafoValidador()
        result = v.validar(
            "x = object.__subclasses__()\ngrafo = YeyoGrafo('x', 'y')"
        )
        assert result.is_valid is False

    def test_dunder_globals_rechazado(self):
        v = GrafoValidador()
        result = v.validar(
            "x = fn.__globals__\ngrafo = YeyoGrafo('x', 'y')"
        )
        assert result.is_valid is False


class TestValidacionEstructura:

    def test_sin_variable_grafo_falla(self):
        v = GrafoValidador()
        result = v.validar("x = 42\ny = 'hola'")
        assert result.is_valid is False
        assert any("grafo" in e.lower() for e in result.errores)

    def test_con_variable_grafo_pasa(self):
        v = GrafoValidador()
        result = v.validar("grafo = YeyoGrafo('mi_grafo', 'desc')")
        assert result.is_valid is True

    def test_error_sintaxis_falla(self):
        v = GrafoValidador()
        result = v.validar("def fn(:\n    pass")
        assert result.is_valid is False
        assert any("sintaxis" in e.lower() for e in result.errores)


class TestValidacionNodosCatalogo:

    def test_nodo_del_catalogo_aceptado(self):
        v = GrafoValidador(nodos_permitidos=["nodo_chat", "nodo_log"])
        result = v.validar(
            'nodo = catalogo.obtener("nodo_chat")\n'
            'grafo = YeyoGrafo("g", "d")'
        )
        assert result.is_valid is True

    def test_nodo_fuera_del_catalogo_rechazado(self):
        v = GrafoValidador(nodos_permitidos=["nodo_chat"])
        result = v.validar(
            'nodo = catalogo.obtener("nodo_secreto")\n'
            'grafo = YeyoGrafo("g", "d")'
        )
        assert result.is_valid is False
        assert any("nodo_secreto" in e for e in result.errores)

    def test_sin_nodos_permitidos_no_valida_nodos(self):
        v = GrafoValidador(nodos_permitidos=None)
        result = v.validar(
            'nodo = catalogo.obtener("cualquier_nodo")\n'
            'grafo = YeyoGrafo("g", "d")'
        )
        assert result.is_valid is True

    def test_multiples_errores_reportados(self):
        v = GrafoValidador()
        result = v.validar("import os\nimport sys\nx = eval('1')\ngrafo = YeyoGrafo('g','d')")
        assert result.is_valid is False
        assert len(result.errores) >= 3
