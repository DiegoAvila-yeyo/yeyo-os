"""
YeyoOS — Seed: 100 funciones Python de buenas prácticas
Se cargan como memorias en codigo:conocimiento para que el Code Dojo genere mejor código.
"""

import httpx
import time
import sys

API = "http://localhost:8000/api/v1/memory/manual"

PRACTICES = [
    # ── 1-10: Funciones matemáticas puras ─────────────────────────────────────
    {
        "content": """Python best practice — función simple, docstring conciso:
```python
def sumar(a: float, b: float) -> float:
    \"\"\"Suma dos números.\"\"\"
    return a + b
```
Regla: para funciones simples, docstring de 1 línea. Usar float para números genéricos.""",
        "tags": ["python", "math", "docstring"],
    },
    {
        "content": """Python best practice — fibonacci iterativo con type hints:
```python
def fibonacci(n: int) -> int:
    \"\"\"Retorna el n-ésimo número de Fibonacci. Raise ValueError si n < 0.\"\"\"
    if n < 0:
        raise ValueError("n debe ser >= 0")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```
Regla: validar inputs al inicio. Usar iteración, no recursión para fibonacci.""",
        "tags": ["python", "math", "fibonacci"],
    },
    {
        "content": """Python best practice — factorial con guard clause:
```python
def factorial(n: int) -> int:
    \"\"\"Calcula n!. Raise ValueError si n < 0.\"\"\"
    if n < 0:
        raise ValueError("n debe ser >= 0")
    resultado = 1
    for i in range(2, n + 1):
        resultado *= i
    return resultado
```
Regla: guard clause al inicio para inputs inválidos. Iterativo > recursivo para evitar stack overflow.""",
        "tags": ["python", "math", "factorial"],
    },
    {
        "content": """Python best practice — máximo común divisor:
```python
def mcd(a: int, b: int) -> int:
    \"\"\"Máximo común divisor usando algoritmo de Euclides.\"\"\"
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a
```
Regla: usar algoritmos conocidos. abs() para manejar negativos.""",
        "tags": ["python", "math", "algorithms"],
    },
    {
        "content": """Python best practice — es_primo eficiente:
```python
def es_primo(n: int) -> bool:
    \"\"\"Determina si n es primo.\"\"\"
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
```
Regla: optimizar con early returns. Solo checar hasta sqrt(n). Cubrir edge cases.""",
        "tags": ["python", "math", "prime"],
    },
    {
        "content": """Python best practice — potencia con exponente negativo:
```python
def potencia(base: float, exp: int) -> float:
    \"\"\"Calcula base^exp. Soporta exponentes negativos.\"\"\"
    if exp == 0:
        return 1.0
    if exp < 0:
        return 1.0 / potencia(base, -exp)
    resultado = 1.0
    for _ in range(exp):
        resultado *= base
    return resultado
```
Regla: manejar todos los casos edge (0, negativo). Retornar float para consistencia.""",
        "tags": ["python", "math", "power"],
    },
    {
        "content": """Python best practice — clamp (limitar rango):
```python
def clamp(valor: float, minimo: float, maximo: float) -> float:
    \"\"\"Limita valor al rango [minimo, maximo].\"\"\"
    return max(minimo, min(valor, maximo))
```
Regla: funciones de una línea son OK si son claras. No agregar docstring de 10 líneas a algo trivial.""",
        "tags": ["python", "math", "utility"],
    },
    {
        "content": """Python best practice — promedio con manejo de lista vacía:
```python
def promedio(numeros: list[float]) -> float:
    \"\"\"Promedio aritmético. Raise ValueError si la lista está vacía.\"\"\"
    if not numeros:
        raise ValueError("La lista no puede estar vacía")
    return sum(numeros) / len(numeros)
```
Regla: siempre validar colecciones vacías. Usar funciones built-in (sum, len).""",
        "tags": ["python", "math", "statistics"],
    },
    {
        "content": """Python best practice — distancia euclidiana:
```python
from math import sqrt

def distancia(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    \"\"\"Distancia euclidiana entre dos puntos 2D.\"\"\"
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return sqrt(dx * dx + dy * dy)
```
Regla: usar math.sqrt, no ** 0.5. Variables intermedias mejoran legibilidad.""",
        "tags": ["python", "math", "geometry"],
    },
    {
        "content": """Python best practice — interpolación lineal:
```python
def lerp(a: float, b: float, t: float) -> float:
    \"\"\"Interpolación lineal entre a y b. t=0 retorna a, t=1 retorna b.\"\"\"
    return a + (b - a) * t
```
Regla: nombres cortos son OK para funciones matemáticas estándar (lerp, clamp, dot).""",
        "tags": ["python", "math", "interpolation"],
    },

    # ── 11-20: Strings y texto ────────────────────────────────────────────────
    {
        "content": """Python best practice — invertir string sin slicing mágico:
```python
def invertir(texto: str) -> str:
    \"\"\"Invierte un string.\"\"\"
    return texto[::-1]
```
Regla: el slice [::-1] es idiomático en Python. No reinventar la rueda con loops.""",
        "tags": ["python", "string", "idiom"],
    },
    {
        "content": """Python best practice — es_palindromo:
```python
def es_palindromo(texto: str) -> bool:
    \"\"\"Verifica si texto es palíndromo (ignora mayúsculas y espacios).\"\"\"
    limpio = texto.lower().replace(" ", "")
    return limpio == limpio[::-1]
```
Regla: normalizar input antes de comparar. Encadenar métodos de string.""",
        "tags": ["python", "string", "palindrome"],
    },
    {
        "content": """Python best practice — contar palabras:
```python
def contar_palabras(texto: str) -> dict[str, int]:
    \"\"\"Cuenta frecuencia de cada palabra en el texto.\"\"\"
    from collections import Counter
    return dict(Counter(texto.lower().split()))
```
Regla: usar Counter de collections, no loops manuales. Import dentro de función OK para dependencias ligeras.""",
        "tags": ["python", "string", "collections"],
    },
    {
        "content": """Python best practice — truncar texto con ellipsis:
```python
def truncar(texto: str, max_len: int = 80) -> str:
    \"\"\"Trunca texto a max_len caracteres, agregando '...' si es necesario.\"\"\"
    if len(texto) <= max_len:
        return texto
    return texto[:max_len - 3] + "..."
```
Regla: valores default razonables. Early return para el caso simple.""",
        "tags": ["python", "string", "utility"],
    },
    {
        "content": """Python best practice — slugify:
```python
import re
import unicodedata

def slugify(texto: str) -> str:
    \"\"\"Convierte texto a slug URL-friendly: 'Hola Mundo!' -> 'hola-mundo'.\"\"\"
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^\\w\\s-]", "", texto).strip().lower()
    return re.sub(r"[-\\s]+", "-", texto)
```
Regla: normalizar unicode antes de procesar. Usar regex para limpieza de strings.""",
        "tags": ["python", "string", "web"],
    },
    {
        "content": """Python best practice — capitalizar cada palabra:
```python
def titulo(texto: str) -> str:
    \"\"\"Capitaliza la primera letra de cada palabra.\"\"\"
    return texto.title()
```
Regla: conocer los métodos built-in de str. No reimplementar lo que ya existe.""",
        "tags": ["python", "string", "builtin"],
    },
    {
        "content": """Python best practice — extraer emails con regex:
```python
import re

def extraer_emails(texto: str) -> list[str]:
    \"\"\"Extrae todas las direcciones de email del texto.\"\"\"
    patron = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    return re.findall(patron, texto)
```
Regla: regex para extracción de patrones. Retornar lista, no generador, para uso general.""",
        "tags": ["python", "string", "regex"],
    },
    {
        "content": """Python best practice — cesar cipher:
```python
def cifrar_cesar(texto: str, desplazamiento: int = 3) -> str:
    \"\"\"Cifrado César: desplaza cada letra por n posiciones.\"\"\"
    resultado = []
    for c in texto:
        if c.isalpha():
            base = ord('A') if c.isupper() else ord('a')
            resultado.append(chr((ord(c) - base + desplazamiento) % 26 + base))
        else:
            resultado.append(c)
    return "".join(resultado)
```
Regla: list append + join es más eficiente que concatenar strings con +.""",
        "tags": ["python", "string", "crypto"],
    },
    {
        "content": """Python best practice — validar email simple:
```python
import re

def es_email_valido(email: str) -> bool:
    \"\"\"Validación básica de formato de email.\"\"\"
    patron = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    return bool(re.match(patron, email))
```
Regla: para validación, usar re.match con ^ y $. Retornar bool explícito.""",
        "tags": ["python", "string", "validation"],
    },
    {
        "content": """Python best practice — formato de moneda:
```python
def formato_moneda(cantidad: float, moneda: str = "MXN") -> str:
    \"\"\"Formatea número como moneda: 1234.5 -> '$1,234.50 MXN'.\"\"\"
    return f"${cantidad:,.2f} {moneda}"
```
Regla: usar f-strings con formato. Valores default para parámetros opcionales.""",
        "tags": ["python", "string", "format"],
    },

    # ── 21-30: Listas y colecciones ───────────────────────────────────────────
    {
        "content": """Python best practice — aplanar lista anidada:
```python
def aplanar(lista: list) -> list:
    \"\"\"Aplana una lista anidada a un solo nivel.\"\"\"
    resultado = []
    for item in lista:
        if isinstance(item, list):
            resultado.extend(aplanar(item))
        else:
            resultado.append(item)
    return resultado
```
Regla: recursión es OK para estructuras anidadas de profundidad variable.""",
        "tags": ["python", "list", "recursion"],
    },
    {
        "content": """Python best practice — chunk list:
```python
def chunks(lista: list, tamaño: int) -> list[list]:
    \"\"\"Divide lista en sublistas de tamaño dado.\"\"\"
    return [lista[i:i + tamaño] for i in range(0, len(lista), tamaño)]
```
Regla: list comprehension con slicing para dividir. Nombre claro del parámetro.""",
        "tags": ["python", "list", "utility"],
    },
    {
        "content": """Python best practice — eliminar duplicados manteniendo orden:
```python
def unicos(lista: list) -> list:
    \"\"\"Elimina duplicados manteniendo el orden original.\"\"\"
    vistos = set()
    resultado = []
    for item in lista:
        if item not in vistos:
            vistos.add(item)
            resultado.append(item)
    return resultado
```
Regla: set() para lookup O(1). No usar list(set(x)) porque pierde el orden.""",
        "tags": ["python", "list", "dedup"],
    },
    {
        "content": """Python best practice — buscar en lista de dicts:
```python
def buscar(items: list[dict], clave: str, valor) -> dict | None:
    \"\"\"Busca el primer dict donde dict[clave] == valor. Retorna None si no existe.\"\"\"
    return next((item for item in items if item.get(clave) == valor), None)
```
Regla: next() con generador y default=None es más pythónico que loop + break.""",
        "tags": ["python", "list", "search"],
    },
    {
        "content": """Python best practice — zip con nombres:
```python
def combinar_dicts(claves: list[str], valores: list) -> dict:
    \"\"\"Combina dos listas en un diccionario.\"\"\"
    return dict(zip(claves, valores))
```
Regla: dict(zip(...)) es la forma idiomática. No usar loop con enumerate.""",
        "tags": ["python", "dict", "idiom"],
    },
    {
        "content": """Python best practice — agrupar por clave:
```python
from collections import defaultdict

def agrupar_por(items: list[dict], clave: str) -> dict[str, list[dict]]:
    \"\"\"Agrupa una lista de dicts por el valor de una clave.\"\"\"
    grupos = defaultdict(list)
    for item in items:
        grupos[item[clave]].append(item)
    return dict(grupos)
```
Regla: defaultdict es más limpio que setdefault() o if/else.""",
        "tags": ["python", "dict", "groupby"],
    },
    {
        "content": """Python best practice — merge de diccionarios:
```python
def merge_dicts(*dicts: dict) -> dict:
    \"\"\"Combina múltiples diccionarios. Los últimos tienen prioridad.\"\"\"
    resultado = {}
    for d in dicts:
        resultado |= d
    return resultado
```
Regla: operador |= para merge (Python 3.9+). *args para aceptar N diccionarios.""",
        "tags": ["python", "dict", "merge"],
    },
    {
        "content": """Python best practice — top N elementos:
```python
import heapq

def top_n(items: list[float], n: int = 5) -> list[float]:
    \"\"\"Retorna los n elementos más grandes, ordenados de mayor a menor.\"\"\"
    return sorted(heapq.nlargest(n, items), reverse=True)
```
Regla: heapq.nlargest es O(n log k), más eficiente que sorted() para k << n.""",
        "tags": ["python", "list", "performance"],
    },
    {
        "content": """Python best practice — rotar lista:
```python
from collections import deque

def rotar(lista: list, n: int) -> list:
    \"\"\"Rota lista n posiciones a la derecha.\"\"\"
    d = deque(lista)
    d.rotate(n)
    return list(d)
```
Regla: deque.rotate() es O(n) y más legible que slicing doble.""",
        "tags": ["python", "list", "deque"],
    },
    {
        "content": """Python best practice — matrix transpose:
```python
def transponer(matrix: list[list]) -> list[list]:
    \"\"\"Transpone una matriz (filas ↔ columnas).\"\"\"
    return [list(fila) for fila in zip(*matrix)]
```
Regla: zip(*matrix) es la transposición idiomática en Python.""",
        "tags": ["python", "list", "matrix"],
    },

    # ── 31-40: Archivos y I/O ─────────────────────────────────────────────────
    {
        "content": """Python best practice — leer archivo completo:
```python
from pathlib import Path

def leer_archivo(ruta: str | Path) -> str:
    \"\"\"Lee el contenido completo de un archivo de texto.\"\"\"
    return Path(ruta).read_text(encoding="utf-8")
```
Regla: usar pathlib, no open(). Siempre especificar encoding='utf-8'.""",
        "tags": ["python", "file", "pathlib"],
    },
    {
        "content": """Python best practice — escribir archivo seguro:
```python
from pathlib import Path

def escribir_archivo(ruta: str | Path, contenido: str) -> None:
    \"\"\"Escribe contenido a archivo, creando directorios si es necesario.\"\"\"
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contenido, encoding="utf-8")
```
Regla: crear directorios padre automáticamente. None return type para side effects.""",
        "tags": ["python", "file", "pathlib"],
    },
    {
        "content": """Python best practice — leer JSON:
```python
import json
from pathlib import Path

def leer_json(ruta: str | Path) -> dict:
    \"\"\"Lee y parsea un archivo JSON.\"\"\"
    return json.loads(Path(ruta).read_text(encoding="utf-8"))
```
Regla: json.loads(path.read_text()) es más simple que json.load(open(...)).""",
        "tags": ["python", "file", "json"],
    },
    {
        "content": """Python best practice — escribir JSON formateado:
```python
import json
from pathlib import Path

def escribir_json(ruta: str | Path, data: dict, indent: int = 2) -> None:
    \"\"\"Escribe data como JSON formateado.\"\"\"
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
```
Regla: ensure_ascii=False para soportar español/unicode. indent=2 para legibilidad.""",
        "tags": ["python", "file", "json"],
    },
    {
        "content": """Python best practice — leer CSV como lista de dicts:
```python
import csv
from pathlib import Path

def leer_csv(ruta: str | Path) -> list[dict]:
    \"\"\"Lee CSV y retorna lista de diccionarios (headers como keys).\"\"\"
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
```
Regla: DictReader > reader para CSVs con headers. newline='' para CSV correcto.""",
        "tags": ["python", "file", "csv"],
    },
    {
        "content": """Python best practice — listar archivos por extensión:
```python
from pathlib import Path

def listar_archivos(directorio: str | Path, extension: str = ".py") -> list[Path]:
    \"\"\"Lista recursivamente todos los archivos con la extensión dada.\"\"\"
    return sorted(Path(directorio).rglob(f"*{extension}"))
```
Regla: rglob() para búsqueda recursiva. sorted() para orden determinístico.""",
        "tags": ["python", "file", "pathlib"],
    },
    {
        "content": """Python best practice — context manager para archivo temporal:
```python
import tempfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def archivo_temporal(sufijo: str = ".txt"):
    \"\"\"Context manager que crea un archivo temporal y lo elimina al salir.\"\"\"
    path = Path(tempfile.mktemp(suffix=sufijo))
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
```
Regla: context managers para recursos que necesitan cleanup. missing_ok=True para seguridad.""",
        "tags": ["python", "file", "contextmanager"],
    },
    {
        "content": """Python best practice — copiar archivo:
```python
import shutil
from pathlib import Path

def copiar(origen: str | Path, destino: str | Path) -> Path:
    \"\"\"Copia archivo de origen a destino. Retorna Path del destino.\"\"\"
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.copy2(origen, destino))
```
Regla: shutil.copy2 preserva metadata. Crear directorios padre.""",
        "tags": ["python", "file", "shutil"],
    },
    {
        "content": """Python best practice — hash de archivo:
```python
import hashlib
from pathlib import Path

def hash_archivo(ruta: str | Path, algo: str = "sha256") -> str:
    \"\"\"Calcula el hash hexadecimal de un archivo.\"\"\"
    h = hashlib.new(algo)
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```
Regla: leer en chunks para archivos grandes. rb mode para hash binario.""",
        "tags": ["python", "file", "hash"],
    },
    {
        "content": """Python best practice — tamaño de archivo legible:
```python
def tamaño_legible(bytes: int) -> str:
    \"\"\"Convierte bytes a formato legible: 1536 -> '1.5 KB'.\"\"\"
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if bytes < 1024:
            return f"{bytes:.1f} {unidad}"
        bytes /= 1024
    return f"{bytes:.1f} PB"
```
Regla: loop sobre unidades es más limpio que if/elif chain.""",
        "tags": ["python", "utility", "format"],
    },

    # ── 41-50: Async y concurrencia ───────────────────────────────────────────
    {
        "content": """Python best practice — async HTTP request:
```python
import httpx

async def fetch_json(url: str, timeout: float = 10.0) -> dict:
    \"\"\"Hace GET request y retorna JSON. Raise HTTPError si falla.\"\"\"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```
Regla: httpx > aiohttp para async HTTP. Siempre timeout. raise_for_status().""",
        "tags": ["python", "async", "http"],
    },
    {
        "content": """Python best practice — ejecutar tareas en paralelo:
```python
import asyncio

async def ejecutar_paralelo(*coroutines) -> list:
    \"\"\"Ejecuta múltiples coroutines en paralelo y retorna resultados.\"\"\"
    return await asyncio.gather(*coroutines, return_exceptions=True)
```
Regla: gather con return_exceptions=True para no perder resultados por una excepción.""",
        "tags": ["python", "async", "parallel"],
    },
    {
        "content": """Python best practice — retry con backoff exponencial:
```python
import asyncio

async def retry(coro_factory, max_intentos: int = 3, base_delay: float = 1.0):
    \"\"\"Reintenta una coroutine con backoff exponencial.\"\"\"
    for intento in range(max_intentos):
        try:
            return await coro_factory()
        except Exception:
            if intento == max_intentos - 1:
                raise
            await asyncio.sleep(base_delay * (2 ** intento))
```
Regla: recibir factory (callable), no coroutine ya creada. Backoff exponencial para APIs.""",
        "tags": ["python", "async", "retry"],
    },
    {
        "content": """Python best practice — semáforo para limitar concurrencia:
```python
import asyncio

async def procesar_con_limite(items: list, func, max_concurrent: int = 5) -> list:
    \"\"\"Procesa items con máximo max_concurrent tareas simultáneas.\"\"\"
    sem = asyncio.Semaphore(max_concurrent)
    async def _wrapper(item):
        async with sem:
            return await func(item)
    return await asyncio.gather(*[_wrapper(i) for i in items])
```
Regla: Semaphore para evitar saturar APIs o recursos. gather para recolectar resultados.""",
        "tags": ["python", "async", "semaphore"],
    },
    {
        "content": """Python best practice — timeout para operaciones async:
```python
import asyncio

async def con_timeout(coro, segundos: float = 5.0, default=None):
    \"\"\"Ejecuta coroutine con timeout. Retorna default si se excede.\"\"\"
    try:
        return await asyncio.wait_for(coro, timeout=segundos)
    except asyncio.TimeoutError:
        return default
```
Regla: wait_for para timeouts. Default value en vez de exception para UX suave.""",
        "tags": ["python", "async", "timeout"],
    },
    {
        "content": """Python best practice — producer/consumer con queue:
```python
import asyncio

async def producer(queue: asyncio.Queue, items: list) -> None:
    \"\"\"Pone items en la queue y señaliza fin con None.\"\"\"
    for item in items:
        await queue.put(item)
    await queue.put(None)  # señal de fin

async def consumer(queue: asyncio.Queue, handler) -> list:
    \"\"\"Consume items de la queue hasta recibir None.\"\"\"
    resultados = []
    while True:
        item = await queue.get()
        if item is None:
            break
        resultados.append(await handler(item))
    return resultados
```
Regla: None como sentinel para señalizar fin. Separar producer/consumer.""",
        "tags": ["python", "async", "queue"],
    },
    {
        "content": """Python best practice — debounce para llamadas frecuentes:
```python
import asyncio
from typing import Callable

def debounce(delay: float) -> Callable:
    \"\"\"Decorador que retrasa ejecución hasta que no haya llamadas por `delay` segundos.\"\"\"
    def decorator(func):
        task = None
        async def wrapper(*args, **kwargs):
            nonlocal task
            if task:
                task.cancel()
            async def _delayed():
                await asyncio.sleep(delay)
                await func(*args, **kwargs)
            task = asyncio.create_task(_delayed())
        return wrapper
    return decorator
```
Regla: cancelar task anterior en cada llamada. Útil para auto-save, búsqueda en tiempo real.""",
        "tags": ["python", "async", "debounce"],
    },
    {
        "content": """Python best practice — async context manager:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_transaction(pool):
    \"\"\"Context manager para transacción de base de datos.\"\"\"
    conn = await pool.acquire()
    tx = conn.transaction()
    await tx.start()
    try:
        yield conn
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise
    finally:
        await pool.release(conn)
```
Regla: asynccontextmanager para recursos async. try/except/finally para cleanup.""",
        "tags": ["python", "async", "database"],
    },
    {
        "content": """Python best practice — cache async con TTL:
```python
import time
from functools import wraps

def cache_async(ttl_seconds: float = 60.0):
    \"\"\"Decorador que cachea resultado de función async por ttl_seconds.\"\"\"
    def decorator(func):
        _cache = {}
        @wraps(func)
        async def wrapper(*args):
            now = time.monotonic()
            if args in _cache:
                result, timestamp = _cache[args]
                if now - timestamp < ttl_seconds:
                    return result
            result = await func(*args)
            _cache[args] = (result, now)
            return result
        return wrapper
    return decorator
```
Regla: time.monotonic() para medición, no time.time(). Cache key = args.""",
        "tags": ["python", "async", "cache"],
    },
    {
        "content": """Python best practice — event emitter simple:
```python
from collections import defaultdict
from typing import Callable

class EventEmitter:
    \"\"\"Event emitter sencillo estilo Node.js.\"\"\"
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: str, *args, **kwargs) -> None:
        for handler in self._handlers[event]:
            handler(*args, **kwargs)
```
Regla: defaultdict para evitar KeyError. Interfaz mínima: on + emit.""",
        "tags": ["python", "patterns", "events"],
    },

    # ── 51-60: Decoradores y patrones ─────────────────────────────────────────
    {
        "content": """Python best practice — decorador timer:
```python
import time
import logging
from functools import wraps

def timer(func):
    \"\"\"Decorador que logea el tiempo de ejecución.\"\"\"
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logging.debug(f"{func.__name__} tomó {elapsed:.3f}s")
        return result
    return wrapper
```
Regla: siempre usar @wraps. perf_counter > time() para medir duración.""",
        "tags": ["python", "decorator", "performance"],
    },
    {
        "content": """Python best practice — singleton con decorator:
```python
def singleton(cls):
    \"\"\"Decorador que convierte una clase en singleton.\"\"\"
    instances = {}
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance
```
Regla: dict para almacenar instancias. Patrón limpio sin metaclass.""",
        "tags": ["python", "patterns", "singleton"],
    },
    {
        "content": """Python best practice — validar tipos en runtime:
```python
from functools import wraps

def validar_tipos(**tipos):
    \"\"\"Decorador que valida tipos de argumentos en runtime.\"\"\"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for nombre, tipo in tipos.items():
                valor = kwargs.get(nombre)
                if valor is not None and not isinstance(valor, tipo):
                    raise TypeError(f"{nombre} debe ser {tipo.__name__}, recibió {type(valor).__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
```
Regla: **kwargs en decorador para nombrar parámetros. TypeError con mensaje descriptivo.""",
        "tags": ["python", "decorator", "validation"],
    },
    {
        "content": """Python best practice — registry pattern:
```python
class Registry:
    \"\"\"Registro de plugins/handlers por nombre.\"\"\"
    def __init__(self):
        self._registry: dict[str, type] = {}

    def register(self, name: str):
        def decorator(cls):
            self._registry[name] = cls
            return cls
        return decorator

    def create(self, name: str, *args, **kwargs):
        if name not in self._registry:
            raise KeyError(f"No registrado: {name}")
        return self._registry[name](*args, **kwargs)
```
Regla: decorador que retorna la clase sin modificar. Útil para plugins.""",
        "tags": ["python", "patterns", "registry"],
    },
    {
        "content": """Python best practice — builder pattern:
```python
class QueryBuilder:
    \"\"\"Builder para construir queries SQL de forma fluida.\"\"\"
    def __init__(self, tabla: str):
        self._tabla = tabla
        self._wheres: list[str] = []
        self._limit: int | None = None

    def where(self, condicion: str) -> "QueryBuilder":
        self._wheres.append(condicion)
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self

    def build(self) -> str:
        sql = f"SELECT * FROM {self._tabla}"
        if self._wheres:
            sql += " WHERE " + " AND ".join(self._wheres)
        if self._limit:
            sql += f" LIMIT {self._limit}"
        return sql
```
Regla: retornar self para method chaining. build() al final materializa.""",
        "tags": ["python", "patterns", "builder"],
    },
    {
        "content": """Python best practice — strategy pattern con funciones:
```python
from typing import Callable

def ordenar(items: list, estrategia: Callable[[list], list] = sorted) -> list:
    \"\"\"Ordena items usando la estrategia dada (default: sorted).\"\"\"
    return estrategia(items)

# Uso:
# ordenar([3,1,2])  -> [1,2,3]
# ordenar([3,1,2], estrategia=lambda x: sorted(x, reverse=True))  -> [3,2,1]
```
Regla: en Python, funciones de primer orden reemplazan el Strategy pattern de OOP.""",
        "tags": ["python", "patterns", "functional"],
    },
    {
        "content": """Python best practice — dataclass para DTOs:
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Usuario:
    \"\"\"Modelo de usuario.\"\"\"
    nombre: str
    email: str
    edad: int = 0
    activo: bool = True
    creado: datetime = field(default_factory=datetime.now)
```
Regla: @dataclass > dict para datos estructurados. field(default_factory=...) para mutables.""",
        "tags": ["python", "dataclass", "model"],
    },
    {
        "content": """Python best practice — enum para estados:
```python
from enum import Enum, auto

class Estado(Enum):
    PENDIENTE = auto()
    EN_PROCESO = auto()
    COMPLETADO = auto()
    ERROR = auto()

    @property
    def es_final(self) -> bool:
        return self in (Estado.COMPLETADO, Estado.ERROR)
```
Regla: Enum > strings para estados. auto() para valores automáticos. Properties para lógica.""",
        "tags": ["python", "enum", "patterns"],
    },
    {
        "content": """Python best practice — pipeline de transformaciones:
```python
from typing import Callable
from functools import reduce

def pipeline(*funciones: Callable) -> Callable:
    \"\"\"Compone funciones en un pipeline: pipeline(f, g, h)(x) == h(g(f(x))).\"\"\"
    return lambda x: reduce(lambda acc, fn: fn(acc), funciones, x)

# Uso:
# procesar = pipeline(str.strip, str.lower, str.split)
# procesar("  HOLA MUNDO  ")  -> ['hola', 'mundo']
```
Regla: reduce para composición funcional. Lambda OK para combinadores simples.""",
        "tags": ["python", "functional", "pipeline"],
    },
    {
        "content": """Python best practice — memoize genérico:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci_memo(n: int) -> int:
    \"\"\"Fibonacci con memoización automática.\"\"\"
    if n < 2:
        return n
    return fibonacci_memo(n - 1) + fibonacci_memo(n - 2)
```
Regla: lru_cache para memoización. Solo funciona con args hashables. maxsize=128 es buen default.""",
        "tags": ["python", "cache", "performance"],
    },

    # ── 61-70: Error handling ─────────────────────────────────────────────────
    {
        "content": """Python best practice — excepciones custom:
```python
class AppError(Exception):
    \"\"\"Error base de la aplicación.\"\"\"
    def __init__(self, mensaje: str, codigo: str = "UNKNOWN"):
        super().__init__(mensaje)
        self.codigo = codigo

class NotFoundError(AppError):
    def __init__(self, recurso: str, id: str):
        super().__init__(f"{recurso} no encontrado: {id}", codigo="NOT_FOUND")

class ValidationError(AppError):
    def __init__(self, campo: str, detalle: str):
        super().__init__(f"Validación fallida en {campo}: {detalle}", codigo="VALIDATION")
```
Regla: jerarquía de excepciones. Incluir código de error para APIs. super().__init__() siempre.""",
        "tags": ["python", "errors", "patterns"],
    },
    {
        "content": """Python best practice — result type (sin excepciones):
```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass
class Result(Generic[T]):
    \"\"\"Encapsula éxito o error sin usar excepciones.\"\"\"
    ok: bool
    value: T | None = None
    error: str | None = None

    @staticmethod
    def success(value: T) -> "Result[T]":
        return Result(ok=True, value=value)

    @staticmethod
    def failure(error: str) -> "Result[T]":
        return Result(ok=False, error=error)
```
Regla: Result type para funciones que pueden fallar de forma esperada. Static methods como constructores.""",
        "tags": ["python", "errors", "functional"],
    },
    {
        "content": """Python best practice — safe division:
```python
def dividir(a: float, b: float) -> float | None:
    \"\"\"División segura. Retorna None si b es 0.\"\"\"
    if b == 0:
        return None
    return a / b
```
Regla: retornar None > raise Exception para errores esperados en funciones puras.""",
        "tags": ["python", "errors", "safety"],
    },
    {
        "content": """Python best practice — log + re-raise:
```python
import logging

logger = logging.getLogger(__name__)

def operacion_critica(data: dict) -> dict:
    \"\"\"Operación que logea errores antes de re-lanzar.\"\"\"
    try:
        return procesar(data)
    except ValueError as e:
        logger.error(f"Datos inválidos: {e}", extra={"data": data})
        raise
    except Exception as e:
        logger.exception(f"Error inesperado procesando data")
        raise
```
Regla: logger.exception incluye traceback. Re-raise con 'raise' sin argumento preserva stack.""",
        "tags": ["python", "errors", "logging"],
    },
    {
        "content": """Python best practice — suppress para errores ignorables:
```python
from contextlib import suppress

def obtener_valor(config: dict, clave: str, default=None):
    \"\"\"Obtiene valor de config con default seguro.\"\"\"
    with suppress(KeyError, TypeError):
        return config[clave]
    return default
```
Regla: suppress() es más limpio que try/except/pass para errores ignorables.""",
        "tags": ["python", "errors", "contextlib"],
    },
    {
        "content": """Python best practice — validación con múltiples errores:
```python
def validar_usuario(data: dict) -> list[str]:
    \"\"\"Valida datos de usuario. Retorna lista de errores (vacía si todo OK).\"\"\"
    errores = []
    if not data.get("nombre"):
        errores.append("nombre es requerido")
    if not data.get("email"):
        errores.append("email es requerido")
    elif "@" not in data["email"]:
        errores.append("email inválido")
    if data.get("edad", 0) < 0:
        errores.append("edad no puede ser negativa")
    return errores
```
Regla: retornar lista de errores para mostrar todos a la vez, no fallar en el primero.""",
        "tags": ["python", "validation", "patterns"],
    },
    {
        "content": """Python best practice — ensure cleanup con atexit:
```python
import atexit
import tempfile
from pathlib import Path

_temp_files: list[Path] = []

def crear_temp(sufijo: str = ".tmp") -> Path:
    \"\"\"Crea archivo temporal que se limpia al salir del programa.\"\"\"
    path = Path(tempfile.mktemp(suffix=sufijo))
    _temp_files.append(path)
    return path

@atexit.register
def _cleanup():
    for path in _temp_files:
        path.unlink(missing_ok=True)
```
Regla: atexit para cleanup de recursos globales. missing_ok para idempotencia.""",
        "tags": ["python", "cleanup", "atexit"],
    },
    {
        "content": """Python best practice — assertion con mensaje:
```python
def transferir(cuenta_origen: dict, cuenta_destino: dict, monto: float) -> None:
    \"\"\"Transfiere monto entre cuentas.\"\"\"
    assert monto > 0, f"Monto debe ser positivo, recibió: {monto}"
    assert cuenta_origen["saldo"] >= monto, "Saldo insuficiente"
    cuenta_origen["saldo"] -= monto
    cuenta_destino["saldo"] += monto
```
Regla: assert con mensaje descriptivo para precondiciones. Solo en dev, no en producción.""",
        "tags": ["python", "errors", "assertions"],
    },
    {
        "content": """Python best practice — error boundary para APIs:
```python
from fastapi import HTTPException

async def safe_handler(func, *args, **kwargs):
    \"\"\"Ejecuta handler convirtiendo excepciones a HTTPException.\"\"\"
    try:
        return await func(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Sin permisos")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno")
```
Regla: mapear excepciones de dominio a HTTP status codes. No exponer detalles internos en 500.""",
        "tags": ["python", "errors", "api"],
    },
    {
        "content": """Python best practice — circuit breaker:
```python
import time

class CircuitBreaker:
    \"\"\"Patrón circuit breaker para llamadas externas.\"\"\"
    def __init__(self, max_fallos: int = 5, reset_seconds: float = 60.0):
        self.max_fallos = max_fallos
        self.reset_seconds = reset_seconds
        self._fallos = 0
        self._ultimo_fallo = 0.0

    @property
    def abierto(self) -> bool:
        if self._fallos >= self.max_fallos:
            if time.monotonic() - self._ultimo_fallo > self.reset_seconds:
                self._fallos = 0
                return False
            return True
        return False

    def registrar_fallo(self):
        self._fallos += 1
        self._ultimo_fallo = time.monotonic()

    def registrar_exito(self):
        self._fallos = 0
```
Regla: circuit breaker para servicios externos. Reset automático después de timeout.""",
        "tags": ["python", "patterns", "resilience"],
    },

    # ── 71-80: Testing ────────────────────────────────────────────────────────
    {
        "content": """Python best practice — test con pytest:
```python
import pytest

def test_sumar():
    assert sumar(2, 3) == 5
    assert sumar(-1, 1) == 0
    assert sumar(0, 0) == 0

def test_sumar_floats():
    assert abs(sumar(0.1, 0.2) - 0.3) < 1e-9
```
Regla: un assert por comportamiento. Nombre descriptivo. Para floats, comparar con tolerancia.""",
        "tags": ["python", "testing", "pytest"],
    },
    {
        "content": """Python best practice — test parametrizado:
```python
import pytest

@pytest.mark.parametrize("n,expected", [
    (0, 0), (1, 1), (2, 1), (5, 5), (10, 55),
])
def test_fibonacci(n, expected):
    assert fibonacci(n) == expected

def test_fibonacci_negativo():
    with pytest.raises(ValueError):
        fibonacci(-1)
```
Regla: parametrize para múltiples inputs. Test separado para excepciones.""",
        "tags": ["python", "testing", "parametrize"],
    },
    {
        "content": """Python best practice — fixtures:
```python
import pytest

@pytest.fixture
def usuario_ejemplo():
    return {"nombre": "Diego", "email": "diego@test.com", "edad": 25}

@pytest.fixture
def db_temporal(tmp_path):
    db_path = tmp_path / "test.db"
    yield db_path
    # cleanup automático por tmp_path
```
Regla: fixtures para setup reutilizable. yield para setup + teardown. tmp_path para archivos temporales.""",
        "tags": ["python", "testing", "fixtures"],
    },
    {
        "content": """Python best practice — mock de dependencias externas:
```python
from unittest.mock import AsyncMock, patch

async def test_fetch_usuario():
    mock_response = AsyncMock()
    mock_response.json.return_value = {"nombre": "Diego"}
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        resultado = await fetch_usuario("123")
        assert resultado["nombre"] == "Diego"
```
Regla: mock solo dependencias externas (HTTP, DB), nunca lógica interna. AsyncMock para funciones async.""",
        "tags": ["python", "testing", "mock"],
    },
    {
        "content": """Python best practice — test de excepciones:
```python
import pytest

def test_division_por_cero():
    with pytest.raises(ZeroDivisionError):
        dividir_estricto(1, 0)

def test_validacion_mensaje():
    with pytest.raises(ValueError, match="no puede estar vacío"):
        validar_nombre("")
```
Regla: pytest.raises con match para verificar el mensaje. Más preciso que solo el tipo.""",
        "tags": ["python", "testing", "exceptions"],
    },
    {
        "content": """Python best practice — test de performance:
```python
import time

def test_busqueda_rapida():
    datos = list(range(100_000))
    start = time.perf_counter()
    resultado = buscar_binario(datos, 99_999)
    elapsed = time.perf_counter() - start
    assert resultado == 99_999
    assert elapsed < 0.01, f"Búsqueda muy lenta: {elapsed:.3f}s"
```
Regla: assertions de tiempo para detectar regresiones de performance.""",
        "tags": ["python", "testing", "performance"],
    },
    {
        "content": """Python best practice — test de integración con base de datos:
```python
import pytest
import asyncpg

@pytest.fixture
async def db_pool():
    pool = await asyncpg.create_pool("postgresql://test@localhost/test_db")
    yield pool
    await pool.close()

async def test_crear_usuario(db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO users (name) VALUES ($1)", "Test")
        count = await conn.fetchval("SELECT count(*) FROM users WHERE name = $1", "Test")
        assert count == 1
```
Regla: fixture async para pool. DB de test separada. Cleanup automático.""",
        "tags": ["python", "testing", "database"],
    },
    {
        "content": """Python best practice — snapshot testing:
```python
def test_generar_reporte(snapshot):
    reporte = generar_reporte(datos_ejemplo)
    assert reporte == snapshot
    # La primera vez guarda el snapshot, luego lo compara
```
Regla: snapshot tests para outputs grandes/complejos (HTML, JSON, reportes). Instalar pytest-snapshot.""",
        "tags": ["python", "testing", "snapshot"],
    },
    {
        "content": """Python best practice — property-based testing:
```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_sumar_conmutativa(a, b):
    assert sumar(a, b) == sumar(b, a)

@given(st.lists(st.integers(), min_size=1))
def test_ordenar_mantiene_elementos(lista):
    ordenada = sorted(lista)
    assert len(ordenada) == len(lista)
    assert set(ordenada) == set(lista)
```
Regla: hypothesis genera inputs aleatorios. Testear propiedades, no valores específicos.""",
        "tags": ["python", "testing", "hypothesis"],
    },
    {
        "content": """Python best practice — estructura de tests:
```python
# tests/
# ├── conftest.py          <- fixtures compartidas
# ├── test_models.py       <- tests de modelos/lógica
# ├── test_api.py          <- tests de endpoints
# └── test_integration.py  <- tests de integración

# conftest.py:
import pytest

@pytest.fixture(scope="session")
def app():
    from main import create_app
    return create_app(testing=True)
```
Regla: un archivo de test por módulo. conftest.py para fixtures globales. scope="session" para recursos costosos.""",
        "tags": ["python", "testing", "structure"],
    },

    # ── 81-90: APIs y web ─────────────────────────────────────────────────────
    {
        "content": """Python best practice — endpoint FastAPI con validación:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

class CrearProducto(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    precio: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

router = APIRouter(prefix="/productos", tags=["productos"])

@router.post("/", status_code=201)
async def crear(req: CrearProducto) -> dict:
    producto = await db.insert(req.model_dump())
    return {"id": producto.id, "message": "Creado"}
```
Regla: Pydantic para validación. Field con constraints. status_code=201 para creación.""",
        "tags": ["python", "api", "fastapi"],
    },
    {
        "content": """Python best practice — paginación de resultados:
```python
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    has_next: bool

async def listar_paginado(page: int = 1, per_page: int = 20) -> PaginatedResponse:
    offset = (page - 1) * per_page
    items = await db.fetch(f"SELECT * FROM items LIMIT {per_page} OFFSET {offset}")
    total = await db.fetchval("SELECT count(*) FROM items")
    return PaginatedResponse(
        items=items, total=total, page=page,
        per_page=per_page, has_next=offset + per_page < total,
    )
```
Regla: respuesta de paginación con total y has_next. LIMIT/OFFSET para SQL.""",
        "tags": ["python", "api", "pagination"],
    },
    {
        "content": """Python best practice — middleware de logging:
```python
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.3f}s)")
        return response
```
Regla: middleware para cross-cutting concerns. Logear método, path, status y duración.""",
        "tags": ["python", "api", "middleware"],
    },
    {
        "content": """Python best practice — rate limiter simple:
```python
import time
from collections import defaultdict

class RateLimiter:
    \"\"\"Limita requests por IP/key.\"\"\"
    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def permitir(self, key: str) -> bool:
        now = time.monotonic()
        reqs = self._requests[key]
        self._requests[key] = [t for t in reqs if now - t < self.window]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True
```
Regla: sliding window por key. Limpiar requests viejos en cada check.""",
        "tags": ["python", "api", "ratelimit"],
    },
    {
        "content": """Python best practice — CORS configuration:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def configurar_cors(app: FastAPI, origins: list[str] | None = None) -> None:
    \"\"\"Configura CORS. Default: solo localhost en dev.\"\"\"
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```
Regla: función separada para configuración. Restringir origins en producción.""",
        "tags": ["python", "api", "cors"],
    },
    {
        "content": """Python best practice — health check endpoint:
```python
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])
_start_time = datetime.now()

@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "uptime": str(datetime.now() - _start_time),
        "version": "1.0.0",
    }
```
Regla: /health siempre disponible. Incluir uptime y versión.""",
        "tags": ["python", "api", "health"],
    },
    {
        "content": """Python best practice — dependency injection con FastAPI:
```python
from fastapi import Depends

async def get_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn

async def get_current_user(token: str = Header(...)):
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401)
    return user

@router.get("/perfil")
async def perfil(user=Depends(get_current_user), db=Depends(get_db)):
    return await db.fetchrow("SELECT * FROM users WHERE id=$1", user.id)
```
Regla: Depends() para inyección. yield para recursos con cleanup. Composable.""",
        "tags": ["python", "api", "di"],
    },
    {
        "content": """Python best practice — websocket handler:
```python
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: str):
        for ws in self.active:
            await ws.send_text(message)
```
Regla: ConnectionManager centraliza WebSockets. Lista simple para broadcast.""",
        "tags": ["python", "api", "websocket"],
    },
    {
        "content": """Python best practice — response model con ejemplo:
```python
from pydantic import BaseModel, Field

class ProductoResponse(BaseModel):
    id: int
    nombre: str
    precio: float
    disponible: bool

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": 1,
                "nombre": "Laptop",
                "precio": 15999.99,
                "disponible": True,
            }]
        }
    }
```
Regla: model_config con examples para auto-documentación en Swagger.""",
        "tags": ["python", "api", "pydantic"],
    },
    {
        "content": """Python best practice — background task en FastAPI:
```python
from fastapi import BackgroundTasks

async def enviar_email_bienvenida(email: str):
    # Lógica de envío...
    pass

@router.post("/registrar")
async def registrar(usuario: UsuarioCreate, tasks: BackgroundTasks):
    nuevo = await crear_usuario(usuario)
    tasks.add_task(enviar_email_bienvenida, nuevo.email)
    return {"id": nuevo.id, "message": "Registrado"}
```
Regla: BackgroundTasks para operaciones no-bloqueantes. Responder inmediatamente al usuario.""",
        "tags": ["python", "api", "background"],
    },

    # ── 91-100: Reglas generales de estilo ────────────────────────────────────
    {
        "content": """Python regla de estilo: funciones simples = docstring de 1 línea.
```python
# ✅ Bien:
def sumar(a: float, b: float) -> float:
    \"\"\"Suma dos números.\"\"\"
    return a + b

# ❌ Mal:
def sumar(a: int, b: int) -> int:
    \"\"\"
    Suma dos números enteros y devuelve el resultado.
    
    :param a: El primer número entero.
    :type a: int
    :param b: El segundo número entero.
    :type b: int
    :return: La suma de los dos números.
    :rtype: int
    \"\"\"
    return a + b
```
Regla: no repetir info que ya está en los type hints. Docstrings largos solo para funciones complejas.""",
        "tags": ["python", "style", "docstring"],
    },
    {
        "content": """Python regla de estilo: usar float para 'números' genéricos.
```python
# ✅ Bien — acepta int y float:
def calcular(valor: float) -> float: ...

# ❌ Mal — rechaza floats:
def calcular(valor: int) -> int: ...
```
Regla: si la función dice 'números' sin especificar, usar float (int es subset de float en Python).""",
        "tags": ["python", "style", "types"],
    },
    {
        "content": """Python regla de estilo: guard clauses al inicio.
```python
# ✅ Bien — early return:
def procesar(data):
    if not data:
        return None
    if not data.get("id"):
        raise ValueError("id requerido")
    # lógica principal...

# ❌ Mal — nesting profundo:
def procesar(data):
    if data:
        if data.get("id"):
            # lógica principal...
```
Regla: validar y salir temprano. Nunca anidar más de 3 niveles.""",
        "tags": ["python", "style", "guard-clause"],
    },
    {
        "content": """Python regla de estilo: nombres descriptivos en español o inglés, pero consistente.
```python
# ✅ Bien — todo en español:
def calcular_impuesto(subtotal: float, tasa: float = 0.16) -> float:
    return subtotal * tasa

# ✅ Bien — todo en inglés:
def calculate_tax(subtotal: float, rate: float = 0.16) -> float:
    return subtotal * rate

# ❌ Mal — mezclado:
def calcular_tax(subtotal: float, rate: float = 0.16) -> float:
    return subtotal * rate
```
Regla: elegir un idioma y ser consistente. No mezclar.""",
        "tags": ["python", "style", "naming"],
    },
    {
        "content": """Python regla de estilo: usar funciones built-in antes de loops.
```python
# ✅ Bien:
total = sum(precios)
maximo = max(valores)
existe = any(x > 10 for x in datos)
todos = all(x > 0 for x in datos)

# ❌ Mal:
total = 0
for p in precios:
    total += p
```
Regla: sum, max, min, any, all, map, filter son más rápidos y legibles que loops.""",
        "tags": ["python", "style", "builtins"],
    },
    {
        "content": """Python regla de estilo: comprehensions > loops para transformar.
```python
# ✅ Bien:
nombres = [u["nombre"] for u in usuarios]
activos = {u["id"]: u for u in usuarios if u["activo"]}

# ❌ Mal:
nombres = []
for u in usuarios:
    nombres.append(u["nombre"])
```
Regla: list/dict comprehension para transformaciones simples. Loop para lógica compleja.""",
        "tags": ["python", "style", "comprehension"],
    },
    {
        "content": """Python regla de estilo: una función = una responsabilidad.
```python
# ✅ Bien — separadas:
def validar_email(email: str) -> bool: ...
def normalizar_email(email: str) -> str: ...
def enviar_email(email: str, mensaje: str) -> None: ...

# ❌ Mal — todo junto:
def manejar_email(email, mensaje=None, validar=True, enviar=True): ...
```
Regla: funciones pequeñas con un solo propósito. Parámetros booleanos son code smell.""",
        "tags": ["python", "style", "srp"],
    },
    {
        "content": """Python regla de estilo: imports organizados.
```python
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. Third party
import httpx
from fastapi import FastAPI

# 3. Local
from src.models import Usuario
from src.utils import validar
```
Regla: 3 grupos separados por línea en blanco. Orden alfabético dentro de cada grupo.""",
        "tags": ["python", "style", "imports"],
    },
    {
        "content": """Python regla de estilo: constantes en MAYÚSCULAS al inicio del módulo.
```python
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0
API_BASE_URL = "https://api.ejemplo.com/v1"
VALID_STATUSES = frozenset({"active", "pending", "completed"})
```
Regla: UPPER_SNAKE_CASE. frozenset para constantes de colección. Al inicio del archivo después de imports.""",
        "tags": ["python", "style", "constants"],
    },
    {
        "content": """Python regla de estilo: type hints siempre, return type siempre.
```python
# ✅ Bien:
def buscar(nombre: str, limite: int = 10) -> list[dict]:
def es_valido(data: dict) -> bool:
def procesar(items: list[str]) -> None:

# ❌ Mal:
def buscar(nombre, limite=10):
def es_valido(data):
def procesar(items):
```
Regla: type hints son documentación ejecutable. Siempre incluir return type, incluso -> None.""",
        "tags": ["python", "style", "typehints"],
    },
]

def main():
    print(f"🚀 Cargando {len(PRACTICES)} memorias de buenas prácticas Python...")
    loaded = 0
    errors = 0

    with httpx.Client(timeout=30.0) as client:
        for i, p in enumerate(PRACTICES, 1):
            payload = {
                "content": p["content"],
                "namespace": "codigo:conocimiento",
                "type": "skill",
                "tier": "WARM",
                "source": "seed_code_practices",
                "importance": 0.85,
                "tags": p.get("tags", []),
                "metadata": {"category": "best_practice"},
            }
            try:
                resp = client.post(API, json=payload)
                if resp.status_code == 200:
                    loaded += 1
                    tags = ", ".join(p.get("tags", []))
                    print(f"  [{i:3d}/100] ✅ [{tags}]")
                else:
                    errors += 1
                    print(f"  [{i:3d}/100] ❌ HTTP {resp.status_code}: {resp.text[:100]}")
            except Exception as e:
                errors += 1
                print(f"  [{i:3d}/100] ❌ Error: {e}")

            # Small delay to not overwhelm embedding generation
            if i % 10 == 0:
                print(f"  --- {i}/100 procesadas ---")
                time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"✅ Cargadas: {loaded}")
    print(f"❌ Errores: {errors}")
    print(f"Total: {len(PRACTICES)}")

if __name__ == "__main__":
    main()
