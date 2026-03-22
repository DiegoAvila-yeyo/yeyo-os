# 15 — YeyoOrquestador

## Resumen

YeyoOrquestador es el motor de orquestación nativo de YeyoOS. En lugar de depender de frameworks externos (OpenClaw, LangChain, CrewAI), YeyoOS construye su propio orquestador diseñado para encajar perfectamente con la arquitectura hexagonal, la Flash Memory, el Hub visual y Ollama tool calling.

El diseño es **híbrido**: código Python puro para la lógica, con una capa declarativa (YAML o decoradores) encima para flujos simples.

---

## ¿Por qué un orquestador propio?

| Criterio | OpenClaw/LangChain | YeyoOrquestador |
|---|---|---|
| Integración con Flash Memory | Manual, adaptador necesario | Nativa — checkpoints automáticos |
| Visualización en Hub | Imposible sin hackeo | Nativa — eventos WebSocket first-class |
| Generación dinámica de grafos | No diseñado para eso | Core feature con sandbox seguro |
| Nodos como .ypkg instalables | No aplica | Los grafos generados se empaquetan |
| Ollama tool calling | Adaptador externo | Integración directa |
| Control total del código | No | Sí — sin dependencias ocultas |

La decisión clave: **los grafos generados por IA se convierten en nodos .ypkg instalables**. Ningún framework externo tiene esta capacidad de forma nativa.

---

## Concepto 1: EstadoGrafo

El `EstadoGrafo` es el objeto que fluye entre todos los nodos. Contiene la entrada, la salida acumulada, contexto arbitrario, historial de nodos ejecutados, conteo de intentos por nodo, timestamps y errores.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class EstadoGrafo:
    entrada: dict                          # Input original del usuario/sistema
    salida: dict = field(default_factory=dict)       # Output acumulado
    contexto: dict = field(default_factory=dict)     # Contexto compartido entre nodos
    nodo_actual: str = ""                  # ID del nodo que se está ejecutando ahora
    historial: list[str] = field(default_factory=list)  # IDs de nodos ejecutados en orden
    intentos: dict = field(default_factory=dict)    # {nodo_id: conteo_de_intentos}
    inicio: datetime = None                # Timestamp de inicio de ejecución
    errores: list[dict] = field(default_factory=list)   # Lista de errores con contexto
    memoria_ids: list[str] = field(default_factory=list) # IDs de memorias creadas
```

El `EstadoGrafo` es **serializable a JSON** para soportar checkpoints en Flash Memory.

---

## Concepto 2: Nodo

Un Nodo es la unidad mínima de trabajo. Recibe un `EstadoGrafo`, lo modifica (o crea uno nuevo), y retorna el estado actualizado.

### Tres formas de definir nodos

**1. Decorador** — para funciones async simples:

```python
@nodo(id="generar_imagen", timeout=60, max_intentos=3)
async def generar_imagen(estado: EstadoGrafo) -> EstadoGrafo:
    prompt = estado.entrada["prompt"]
    imagen = await ia.generar_imagen(prompt)
    estado.salida["imagen_url"] = imagen.url
    return estado
```

**2. Clase** — para nodos complejos con estado interno:

```python
class NodoEvaluarCalidad(Nodo):
    id = "evaluar_calidad"
    timeout = 30
    max_intentos = 2

    async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
        imagen_url = estado.salida.get("imagen_url")
        score = await self._evaluar(imagen_url)
        estado.contexto["score_calidad"] = score
        return estado

    async def _evaluar(self, url: str) -> float:
        # Lógica de evaluación con LLaVA
        ...
```

**3. Inline** — para nodos triviales sin lógica compleja:

```python
nodo_log = Nodo(
    id="log",
    fn=lambda estado: estado,  # Pass-through, solo para logging
    timeout=5
)
```

### Propiedades de un Nodo

| Propiedad | Descripción | Default |
|---|---|---|
| `id` | Identificador único dentro del grafo | Requerido |
| `timeout` | Segundos máximos de ejecución | 30 |
| `max_intentos` | Reintentos en caso de error | 1 |
| `fn` | Función async a ejecutar | Requerido (o sobreescribir `ejecutar`) |

---

## Concepto 3: Edge

Un Edge define cómo fluye el `EstadoGrafo` entre nodos.

### Cuatro formas de definir edges

**1. Directo** — siempre va al mismo nodo:

```python
grafo.edge("generar_imagen", "evaluar_calidad")
```

**2. Condicional con función** — la función decide el siguiente nodo:

```python
@edge(desde="evaluar_calidad")
def siguiente_nodo(estado: EstadoGrafo) -> str:
    score = estado.contexto.get("score_calidad", 0)
    if score >= 0.8:
        return "upscale"
    elif score >= 0.5:
        return "refinar"
    else:
        return "generar_imagen"  # Reintentar
```

**3. YAML declarativo** — para flujos simples sin condicionales:

```yaml
edges:
  - desde: normalizar_input
    hasta: generar_embedding
  - desde: generar_embedding
    hasta: buscar_memoria
  - desde: buscar_memoria
    hasta: generar_respuesta
  - desde: generar_respuesta
    hasta: guardar_memoria
```

**4. IA decide (Ollama tool calling)** — la IA elige el siguiente nodo basándose en el estado:

```python
grafo.edge_ia("evaluar_resultado", candidatos=["aprobar", "rechazar", "refinar"])
# Ollama analiza estado.contexto y decide qué nodo ejecutar siguiente
```

---

## Concepto 4: YeyoGrafo

`YeyoGrafo` es el coordinador. Orquesta la ejecución de nodos en secuencia, maneja errores, timeouts y reintentos.

### API de construcción (método chaining)

```python
grafo = (
    YeyoGrafo("generacion_imagen", "Genera y evalúa imágenes con calidad garantizada")
        .agregar_nodo(nodo_normalizar)
        .agregar_nodo(nodo_generar_imagen)
        .agregar_nodo(nodo_evaluar_calidad)
        .agregar_nodo(nodo_upscale)
        .inicio("normalizar")
        .edge("normalizar", "generar_imagen")
        .edge_condicional("evaluar_calidad", fn_siguiente)
        .edge("upscale", "__fin__")
        .fin("upscale")
)

resultado = await grafo.ejecutar({"prompt": "logo cyberpunk azul"})
print(resultado.estado_final.salida["imagen_url"])
print(resultado.duracion_total_ms)
print(resultado.nodos_ejecutados)
```

### ResultadoGrafo

```python
@dataclass
class ResultadoGrafo:
    grafo_id: str
    estado_final: EstadoGrafo
    exito: bool
    duracion_total_ms: float
    nodos_ejecutados: list[str]
    errores: list[dict]
```

### Sub-grafos como nodos

Un grafo puede usarse como nodo dentro de otro grafo:

```python
grafo_busqueda = YeyoGrafo("busqueda", "Búsqueda semántica")...
grafo_principal = (
    YeyoGrafo("asistente_completo", "Asistente con memoria")
        .agregar_nodo(grafo_busqueda.como_nodo())  # ← sub-grafo
        .agregar_nodo(nodo_generar_respuesta)
        ...
)
```

---

## Paralelismo: NodoParalelo

`NodoParalelo` ejecuta múltiples nodos simultáneamente con `asyncio.gather` y combina los resultados.

```python
nodo_gen_variaciones = NodoParalelo(
    id="generar_3_variaciones",
    nodos=[
        nodo_gen_estilo_realista,
        nodo_gen_estilo_anime,
        nodo_gen_estilo_sketch,
    ],
    combinar=lambda resultados: {
        "variaciones": [r.salida["imagen_url"] for r in resultados],
        "mejor": max(resultados, key=lambda r: r.contexto.get("score", 0)).salida["imagen_url"]
    },
    modo_error="fail_fast"  # o "continue_on_error"
)
```

Los nodos paralelos se ejecutan **exactamente al mismo tiempo** (no secuencialmente). El tiempo total es el del nodo más lento, no la suma.

---

## Integración con Ollama Tool Calling

`YeyoOrquestador` registra grafos como tools de Ollama. Cuando el usuario envía un mensaje, Ollama analiza qué grafo es el más adecuado y lo invoca automáticamente.

```python
orquestador = YeyoOrquestador(ollama_provider=ollama)

# Registrar grafos como tools disponibles para Ollama
orquestador.registrar_grafo_como_tool(grafo_chat_contextual)
orquestador.registrar_grafo_como_tool(grafo_generacion_imagen)
orquestador.registrar_grafo_como_tool(grafo_busqueda_semantica)

# Procesar mensaje — Ollama elige qué grafo ejecutar
respuesta = await orquestador.procesar(
    mensaje="Genera un logo para mi startup de IA",
    contexto={"usuario_id": "u1", "historial": [...]}
)
# Ollama llama a grafo_generacion_imagen automáticamente
```

### Cómo funciona internamente

```
Usuario: "Genera un logo para mi startup"
    ↓
YeyoOrquestador.procesar()
    ↓
Ollama recibe mensaje + tools [chat, imagen, busqueda]
    ↓
Ollama responde: tool_call = {name: "grafo_generacion_imagen", args: {prompt: "logo startup IA"}}
    ↓
YeyoOrquestador ejecuta grafo_generacion_imagen
    ↓
Resultado → respuesta al usuario
```

---

## IA que genera grafos dinámicamente

`GeneradorGrafos` permite que la IA cree nuevos grafos en tiempo de ejecución a partir de una descripción en lenguaje natural.

### Flujo de generación

```
Usuario: "Quiero un pipeline que tome una URL, descargue la página,
          extraiga el texto, lo traduzca al inglés y lo resuma."
    ↓
GeneradorGrafos.generar(descripcion, usuario_id)
    ↓
Ollama genera código Python del grafo (usando nodos del catálogo)
    ↓
GrafoValidador valida: imports permitidos, sin eval/exec peligroso,
                       solo nodos del catálogo registrado
    ↓
Compilar en sandbox (RestrictedPython / exec con globals limitados)
    ↓
Guardar en Flash Memory (tipo="grafo_generado", importancia=0.9)
    ↓
Retornar YeyoGrafo listo para ejecutar
    ↓
(Opcional) Empaquetar como .ypkg instalable
```

### CatalogoNodos — los bloques de construcción

La IA solo puede usar nodos del catálogo registrado:

| Nodo | Descripción | Permisos requeridos |
|---|---|---|
| `nodo_chat` | Conversación con LLM via Ollama | — |
| `nodo_embeddings` | Genera embeddings de texto | — |
| `nodo_guardar_memoria` | Guarda en Flash Memory | memory.write |
| `nodo_buscar_memoria` | Busca en Flash Memory | memory.read |
| `nodo_log` | Registra en logs del sistema | — |

Los grafos generados se ejecutan en **nivel de privilegio L5 (SANDBOX)** siempre.

---

## Flash Memory para checkpoints

Cada nodo completado genera un checkpoint automático en Flash Memory.

```
Nodo A ejecutado ✓  →  checkpoint guardado (tipo="grafo_checkpoint")
Nodo B ejecutado ✓  →  checkpoint guardado
Sistema se interrumpe ✗
    ↓
Usuario reanuda tarea
    ↓
GrafoCheckpoint.reanudar("grafo_id", flash_memory)
    →  Busca último checkpoint en Flash Memory
    →  Reconstruye EstadoGrafo desde el checkpoint
    →  Ejecuta desde Nodo C (saltando A y B)
```

### Cache de resultados

`NodoCache` evita re-ejecutar nodos con el mismo input:

```
Primera ejecución:
  Input: {"texto": "hola mundo"} → hash: abc123
  Ejecuta nodo → Guarda resultado en Flash Memory (tipo="resultado_nodo")

Segunda ejecución (mismo input, < 24h):
  Input: {"texto": "hola mundo"} → hash: abc123
  Cache HIT → devuelve resultado guardado, marca nodo como "saltado"
  → Emite evento WebSocket con estado="saltado"
```

---

## Visualización en Hub (tiempo real)

Cuando un grafo ejecuta, el nodo del Hub muestra un **mini-grafo animado** dentro del SatelliteNode expandido.

### Estados visuales de nodos

| Estado | Color | Animación |
|---|---|---|
| `pendiente` | `#555555` | Ninguna |
| `activo` | `#F5A623` | Pulso suave continuo |
| `completado` | `#4CAF50` | Flash breve al completar |
| `error` | `#F44336` | Shake/vibración |
| `saltado` | `#777777` | Ninguna (transparencia reducida) |

### Protocolo de eventos WebSocket

```json
{
  "type": "graph_event",
  "grafo_id": "generacion_imagen",
  "nodo_id": "evaluar_calidad",
  "estado": "activo",
  "progreso": 0.6,
  "mensaje": "Evaluando calidad con LLaVA...",
  "timestamp": "2025-01-15T12:34:56.789Z"
}
```

Las `ConnectionLines` entre nodos del mini-grafo también cambian de color según el estado: gris (pendiente), amarillo (activo), verde (completado).

---

## Distribución por capas

### Capa 3 — UI del mini-grafo (TypeScript/React/PixiJS)

| Micro-fase | Descripción |
|---|---|
| **3.16** | `GraphExecutionView` — componente que renderiza el mini-grafo animado |
| **3.17** | `NodeExpandedWithGraph` — integración con SatelliteNode expandido |

Estas micro-fases son **UI pura** y pueden desarrollarse con mocks de WebSocket antes de que el backend esté listo.

### Capa 4 — YeyoOrquestador base (Python/FastAPI)

| Micro-fase | Descripción |
|---|---|
| **4.14** | `EstadoGrafo` — dataclass core con serialización |
| **4.15** | `Nodo` base + decorador `@nodo` + 3 formas de definir nodos |
| **4.16** | `Edge` + `EdgeCondicional` + decorador `@edge` |
| **4.17** | `YeyoGrafo` coordinador con API fluida y sub-grafos |
| **4.18** | `NodoParalelo` con asyncio.gather y manejo de errores |
| **4.19** | `YeyoOrquestador` + Ollama tool calling integration |
| **4.20** | `CatalogoNodos` con 5 nodos base registrados |
| **4.21** | Grafos estáticos principales (chat contextual, búsqueda semántica) |
| **4.22** | WebSocket graph events backend |
| **4.23** | Integration test completo de Capa 4 |

### Capa 5 — Funcionalidades avanzadas (Python/FastAPI)

| Micro-fase | Descripción |
|---|---|
| **5.22** | `GrafoCheckpoint` — checkpoints en Flash Memory + reanudación |
| **5.23** | `NodoCache` — cache de resultados de nodos con hash de input |
| **5.24** | `GeneradorGrafos` — IA genera grafos desde descripción natural |
| **5.25** | `GrafoValidador` — validación AST de seguridad de grafos generados |
| **5.26** | Integration test de grafos avanzados |

---

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────────┐
│                    YeyoOrquestador                       │
│                                                          │
│   registrar_grafo_como_tool()   procesar(msg, ctx)      │
│              ↓                           ↓              │
│   ┌──────────────────┐    ┌──────────────────────────┐  │
│   │  Tool Registry   │    │     Ollama Tool Calling  │  │
│   │  [grafo→tool]    │    │     elige qué grafo      │  │
│   └──────────────────┘    └──────────────────────────┘  │
│                                     ↓                   │
│                          ┌──────────────────────┐       │
│                          │      YeyoGrafo       │       │
│                          │  nodo1 → nodo2 → ... │       │
│                          └──────────────────────┘       │
│                                     ↓                   │
│                    ┌────────────────────────────┐       │
│                    │      EstadoGrafo            │       │
│                    │  entrada / salida / ctx     │       │
│                    └────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
         ↓ eventos                      ↓ checkpoints
┌─────────────────┐           ┌──────────────────────┐
│  WebSocket Hub  │           │    Flash Memory       │
│  graph_events   │           │  checkpoints + cache  │
└─────────────────┘           └──────────────────────┘
         ↓
┌─────────────────┐
│  GraphExecution │
│  View (Hub UI)  │
└─────────────────┘
```

---

## Grafo Multi-Nodo: Coordinación entre Órganos

Un grafo en YeyoOS no solo puede correr **dentro** de un nodo — puede **coordinar varios nodos del Hub** como si cada uno fuera una estación de trabajo especializada. Cada Hub Node expone sus capacidades como bloques en el `CatalogoNodos`, y el `YeyoOrquestador` dirige el trabajo entre ellos. El nodo central **YEYO** actúa como director de orquesta, emitiendo líneas de energía hacia cada nodo activo.

### Ejemplo: `grafo_hacer_reel`

```
[Script Node]  →  [Image Node ×3 paralelo]  →  [Video Node]  →  [Files Node]
"genera guión"    "genera imágenes"              "las une"        "guarda"
```

Cada nodo del Hub es una máquina con GPU, proceso especializado o servicio externo. El grafo los coordina como si fueran nodos locales, pero la ejecución ocurre distribuida:

```python
# src/orquestador/grafos/hacer_reel.py — fragmento ilustrativo

from src.orquestador.grafo import YeyoGrafo
from src.orquestador.paralelo import NodoParalelo
from src.orquestador.nodo import nodo
from src.orquestador.edge import EdgeCondicional, FIN_GRAFO

# Cada Hub Node registra sus capacidades en el catálogo al conectarse al Hub:
#   catalogo.registrar("hub.imagen.generar", nodo_imagen_generar)
#   catalogo.registrar("hub.video.componer", nodo_video_componer)
#   catalogo.registrar("hub.codigo.ejecutar", nodo_codigo_ejecutar)

def crear_grafo_hacer_reel(ollama_provider=None, hub_imagen=None, hub_video=None):
    """
    GrafoMultiNodo: coordina Script Node → Image Node → Video Node → Files Node.
    Cada nodo puede residir en un Hub Node distinto del mismo Hub.
    """

    @nodo(id="generar_guion")
    async def generar_guion(estado):
        # Llama a nodo_chat para crear guión con escenas numeradas
        guion = await ollama_provider.chat(estado.entrada.get("tema", "reel genérico"))
        estado.salida["guion"] = guion.content
        estado.salida["num_escenas"] = guion.content.count("ESCENA")
        return estado

    # Edge condicional: > 5 escenas → 5 imágenes, si no → 3 imágenes
    def cuantas_imagenes(estado):
        return "muchas" if estado.salida.get("num_escenas", 0) > 5 else "pocas"

    imagenes_x5 = NodoParalelo(
        id="generar_imagenes_x5",
        nodos=[hub_imagen or _mock_imagen(i) for i in range(5)],
    )
    imagenes_x3 = NodoParalelo(
        id="generar_imagenes_x3",
        nodos=[hub_imagen or _mock_imagen(i) for i in range(3)],
    )

    @nodo(id="componer_video")
    async def componer_video(estado):
        imagenes = estado.salida.get("imagenes", [])
        estado.salida["video_path"] = f"reel_{len(imagenes)}_frames.mp4"
        return estado

    @nodo(id="guardar")
    async def guardar(estado):
        estado.salida["guardado"] = True
        return estado

    grafo = (
        YeyoGrafo("grafo_hacer_reel")
        .descripcion("GrafoMultiNodo: guión → imágenes paralelas → video → guardado")
        .agregar_nodo(generar_guion)
        .agregar_nodo(imagenes_x5)
        .agregar_nodo(imagenes_x3)
        .agregar_nodo(componer_video)
        .agregar_nodo(guardar)
        .inicio("generar_guion")
        .edge_condicional("generar_guion", cuantas_imagenes, {
            "muchas": "generar_imagenes_x5",
            "pocas":  "generar_imagenes_x3",
        })
        .edge("generar_imagenes_x5", "componer_video")
        .edge("generar_imagenes_x3", "componer_video")
        .edge("componer_video", "guardar")
        .fin("guardar")
    )
    return grafo
```

### Visualización en el Hub

Cuando un `GrafoMultiNodo` está en ejecución, el Hub UI muestra:

- **YEYO como director**: el nodo central emite **líneas de energía animadas** hacia cada Hub Node activo.
- **Vignette de concentración**: el fondo se oscurece ligeramente en los bordes, focalizando la atención en el grafo activo.
- **Nodos pulsantes**: cada Hub Node pulsa con el color de su dominio (azul → imagen, naranja → video, verde → archivos) mientras procesa su parte del grafo.
- **Progreso distribuido**: el panel `GraphExecutionView` muestra el `nodo_id` real de cada Hub Node junto al porcentaje de avance de la ejecución.

### Registro de Hub Nodes en el Catálogo (Capa 5)

En Capa 5, al conectarse un Hub Node al Hub central, se auto-registra en el `CatalogoNodos`:

```python
# Al conectar Image Node:
catalogo.registrar("hub.imagen.generar",  nodo_imagen_generar)
catalogo.registrar("hub.imagen.editar",   nodo_imagen_editar)

# Al conectar Video Node:
catalogo.registrar("hub.video.componer",  nodo_video_componer)
catalogo.registrar("hub.video.recortar",  nodo_video_recortar)

# Al conectar Code Node:
catalogo.registrar("hub.codigo.ejecutar", nodo_codigo_ejecutar)
```

Esto hace que **cualquier grafo**, tanto manual como generado por IA (`GeneradorGrafos`, micro-fase 5.24), pueda utilizar las capacidades de todos los nodos del Hub de forma transparente.
