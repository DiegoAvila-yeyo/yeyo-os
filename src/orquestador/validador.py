"""
YeyoOS — GrafoValidador
Micro-fase 5.25 — Capa 5: Órganos

Análisis AST de código Python generado por IA.
Detecta patrones peligrosos antes de ejecutar el código.
"""

import ast
from dataclasses import dataclass, field
from typing import Optional


IMPORTS_PROHIBIDOS = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "urllib",
    "http", "ftplib", "smtplib", "paramiko", "requests",
    "importlib", "ctypes", "cffi", "multiprocessing", "threading",
    "pickle", "shelve", "marshal", "tempfile",
})

BUILTINS_PELIGROSOS = frozenset({
    "eval", "exec", "compile", "__import__", "open",
    "input", "breakpoint", "memoryview",
})

ATRIBUTOS_PELIGROSOS = frozenset({
    "__class__", "__subclasses__", "__bases__", "__mro__",
    "__globals__", "__locals__", "__builtins__", "__code__",
    "__func__", "__closure__", "__dict__",
})

IMPORTS_PERMITIDOS = frozenset({
    "src.orquestador", "src.orquestador.nodo",
    "src.orquestador.edge", "src.orquestador.grafo",
    "src.orquestador.estado",
})


@dataclass
class ValidationResult:
    """Resultado de la validación de código de grafo."""
    is_valid: bool
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    def agregar_error(self, mensaje: str) -> None:
        self.errores.append(mensaje)
        self.is_valid = False

    def agregar_advertencia(self, mensaje: str) -> None:
        self.advertencias.append(mensaje)

    def __repr__(self) -> str:
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"errores={len(self.errores)}, "
            f"advertencias={len(self.advertencias)})"
        )


class GrafoValidador:
    """
    Valida código Python de grafos generados por IA usando análisis AST.
    """

    def __init__(self, nodos_permitidos: Optional[list[str]] = None):
        self.nodos_permitidos = nodos_permitidos

    def validar(self, codigo: str) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if not codigo.strip():
            result.agregar_error("El código está vacío")
            return result

        try:
            arbol = ast.parse(codigo)
        except SyntaxError as e:
            result.agregar_error(f"Error de sintaxis: {e}")
            return result

        self._analizar_imports(arbol, result)
        self._analizar_builtins(arbol, result)
        self._analizar_atributos_peligrosos(arbol, result)
        self._analizar_estructura(arbol, result)

        if self.nodos_permitidos:
            self._analizar_uso_de_nodos(arbol, result)

        return result

    def _analizar_imports(self, arbol: ast.AST, result: ValidationResult) -> None:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    modulo_raiz = alias.name.split(".")[0]
                    if modulo_raiz in IMPORTS_PROHIBIDOS:
                        result.agregar_error(
                            f"Import prohibido: '{alias.name}'. "
                            f"Los módulos del sistema no están permitidos."
                        )

            elif isinstance(nodo, ast.ImportFrom):
                if nodo.module is None:
                    continue
                modulo_raiz = nodo.module.split(".")[0]
                if modulo_raiz in IMPORTS_PROHIBIDOS:
                    result.agregar_error(
                        f"Import prohibido: 'from {nodo.module} import ...'. "
                        f"Los módulos del sistema no están permitidos."
                    )
                elif not any(nodo.module.startswith(p) for p in IMPORTS_PERMITIDOS):
                    result.agregar_advertencia(
                        f"Import externo detectado: 'from {nodo.module} import ...'. "
                        f"Solo se permiten imports del orquestador."
                    )

    def _analizar_builtins(self, arbol: ast.AST, result: ValidationResult) -> None:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                if isinstance(nodo.func, ast.Name):
                    if nodo.func.id in BUILTINS_PELIGROSOS:
                        result.agregar_error(
                            f"Función peligrosa detectada: '{nodo.func.id}()'. "
                            f"No está permitida en grafos generados."
                        )
                elif isinstance(nodo.func, ast.Attribute):
                    if nodo.func.attr in BUILTINS_PELIGROSOS:
                        result.agregar_error(
                            f"Atributo peligroso en llamada: '.{nodo.func.attr}()'"
                        )

    def _analizar_atributos_peligrosos(self, arbol: ast.AST, result: ValidationResult) -> None:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Attribute):
                if nodo.attr in ATRIBUTOS_PELIGROSOS:
                    result.agregar_error(
                        f"Atributo peligroso detectado: '.{nodo.attr}'. "
                        f"Acceso a internos de Python no está permitido."
                    )

    def _analizar_estructura(self, arbol: ast.AST, result: ValidationResult) -> None:
        tiene_variable_grafo = False

        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign):
                for target in nodo.targets:
                    if isinstance(target, ast.Name) and target.id == "grafo":
                        tiene_variable_grafo = True
                        break

        if not tiene_variable_grafo:
            result.agregar_error(
                "El código no define la variable 'grafo'. "
                "Debe asignar el YeyoGrafo a una variable llamada exactamente 'grafo'."
            )

    def _analizar_uso_de_nodos(self, arbol: ast.AST, result: ValidationResult) -> None:
        if not self.nodos_permitidos:
            return

        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr == "obtener"
                    and nodo.args):
                arg = nodo.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    nodo_id = arg.value
                    if nodo_id not in self.nodos_permitidos:
                        result.agregar_error(
                            f"Nodo '{nodo_id}' no está en el catálogo permitido. "
                            f"Disponibles: {self.nodos_permitidos}"
                        )
