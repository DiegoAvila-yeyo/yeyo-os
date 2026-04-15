# 02 — Arquitectura del Sistema

## Resumen Ejecutivo

La arquitectura de YeyoOS se unifica alrededor de una idea simple:

> **Primero una plataforma local-first de agentes con memoria, verificación y aprendizaje. Después, si hace sentido, una experiencia tipo OS.**

Esta versión reemplaza la arquitectura anterior centrada en `OpenClaw`, memoria de "5 capas" y prioridad temprana de empaquetado tipo sistema operativo.

Hoy, YeyoOS se define por seis núcleos conectados:

1. **YeyoOrquestador** — kernel de agentes y grafos.
2. **Flash Memory** — memoria unificada y persistente.
3. **Investigador + Quality Kernel** — búsqueda, evaluación, ensamblaje y verificación.
4. **YeyoDojo + YeyoHack** — auto-mejora, agentes especializados y entrenamiento.
5. **YeyoNet** — red privada de cómputo y sincronización.
6. **Nodos + `.ypkg`** — capacidades empaquetables y extensibles.

---

## Qué cambió respecto a la arquitectura anterior

| Antes | Ahora |
|---|---|
| `OpenClaw` como orquestador inicial | `YeyoOrquestador` como kernel nativo |
| Memoria de 5 capas separadas | `Flash Memory` como memoria unificada |
| Roadmap `OS-first` | Roadmap `agents-first` |
| UI fullscreen como prioridad temprana | Núcleo de agentes, memoria y calidad como prioridad |
| Generación primero, verificación después | Investigación/verificación antes de aceptar resultados |

---

## Principios de Arquitectura

### 1. Kernel propio, adaptadores externos

YeyoOS no debe depender de un framework externo para su identidad. Toma ideas de otros repos, pero el centro sigue siendo propio:

- `src/orquestador/`
- `src/core/interfaces.py`
- `src/core/config.py`

### 2. Memoria útil, no acumulación ciega

No todo se guarda. Se guarda lo que aporta continuidad, personalización y aprendizaje:

- preferencias;
- hechos verificados;
- decisiones;
- soluciones validadas;
- archivos y resultados con contexto.

### 3. Anti-slop por diseño

El sistema no debe "sonar bien". Debe:

- buscar;
- ejecutar herramientas;
- verificar;
- medir;
- aprender solo de outputs buenos.

### 4. Contexto mínimo, continuidad máxima

La continuidad vive en la base de datos, no en la ventana de contexto del modelo.

### 5. Evolución continua

El sistema mejora con:

- feedback explícito;
- historial de errores;
- quality gates;
- benchmarks;
- entrenamiento y adapters.

### 6. Distribución progresiva

Primero una máquina. Después múltiples máquinas coordinadas por `YeyoNet`.

---

## Diagrama General

```text
                           ┌────────────────────┐
                           │   Usuario / UI     │
                           │ Next.js / Chat /   │
                           │ Hub / Node layouts │
                           └─────────┬──────────┘
                                     │
                           ┌─────────▼──────────┐
                           │   API / WebSocket  │
                           │   FastAPI Router   │
                           └─────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
          ┌─────────▼───────┐ ┌──────▼─────────┐ ┌───▼─────────────┐
          │ YeyoOrquestador │ │ Flash Memory   │ │ Investigador +  │
          │ Kernel de agentes│ │ Contexto útil │ │ Quality Kernel  │
          └─────────┬───────┘ └──────┬─────────┘ └───┬─────────────┘
                    │                │                │
          ┌─────────▼────────────────▼────────────────▼──────────┐
          │                Runtime de ejecución                  │
          │ Ollama · Tools · Sandbox · Nodos · Checkpoints      │
          └─────────┬──────────────────────┬─────────────────────┘
                    │                      │
         ┌──────────▼──────────┐  ┌───────▼────────────────┐
         │ YeyoDojo / YeyoHack │  │ YeyoNet                │
         │ entrenamiento, eval │  │ central + satélites    │
         └─────────────────────┘  └────────────────────────┘
```

---

## Capas del sistema

## Capa 1 — Interfaces de entrada

Responsabilidad:

- recibir solicitudes del usuario;
- mostrar estados, confianza y resultados;
- visualizar nodos, trazas y progreso.

Repositorio actual:

- `frontend/`
- `src/api/routes/`
- `src/api/websocket.py`

Estado:

- **parcialmente implementada**

No es el cerebro. Es la cara visible del sistema.

---

## Capa 2 — API y coordinación

Responsabilidad:

- traducir eventos UI/API hacia el kernel;
- exponer chat, nodos, memoria, media y paquetes;
- emitir eventos en tiempo real.

Repositorio actual:

- `src/api/main.py`
- `src/api/routes/chat.py`
- `src/api/routes/nodes.py`
- `src/api/routes/memory.py`
- `src/api/routes/media.py`
- `src/api/routes/packages.py`
- `src/api/websocket.py`

Estado:

- **parcialmente implementada**

---

## Capa 3 — Agent Kernel (`YeyoOrquestador`)

Responsabilidad:

- modelar la ejecución como grafos;
- rutear entre nodos/agentes;
- ejecutar pasos secuenciales y paralelos;
- manejar reintentos, timeouts, checkpoints y eventos;
- integrar tool calling con Ollama;
- convertir grafos útiles en capacidades reutilizables.

Repositorio actual:

- `src/orquestador/estado.py`
- `src/orquestador/nodo.py`
- `src/orquestador/grafo.py`
- `src/orquestador/edge.py`
- `src/orquestador/paralelo.py`
- `src/orquestador/checkpoint.py`
- `src/orquestador/eventos.py`
- `src/orquestador/validador.py`

Estado:

- **ya existe una base sólida**

Inspiración externa:

- `agiresearch/AIOS`
- `microsoft/JARVIS`
- `langchain-ai/langchain` (solo ideas de abstracción)

---

## Capa 4 — Flash Memory

Responsabilidad:

- almacenar conversaciones, hechos, decisiones, preferencias, archivos y resultados;
- puntuar relevancia;
- mover recuerdos entre HOT/WARM/COLD;
- asociar recuerdos;
- servir contexto útil a chat, investigador, nodos y agentes.

Repositorio actual:

- `src/memory/flash_memory.py`
- `src/memory/tier_manager.py`
- `src/memory/cache.py`
- `src/memory/models.py`
- `src/memory/associations.py`

Estado:

- **base real existente, falta consolidación**

Inspiración externa:

- `mem0ai/mem0`
- `chroma-core/chroma` (solo como apoyo/prototipo)

---

## Capa 5 — Investigador + Quality Kernel

Responsabilidad:

- buscar primero;
- evaluar candidatos;
- ensamblar soluciones al contexto del repo;
- verificar con ejecución real;
- almacenar solo lo que pasó quality gates.

Repositorio actual:

- `src/investigador/pipeline.py`
- `src/investigador/buscador_externo.py`
- `src/investigador/evaluador.py`
- `src/investigador/ensamblador.py`
- `src/investigador/verificador.py`
- `src/investigador/micro_tareas.py`
- `src/investigador/cache_patrones.py`

Estado:

- **parcial, pero bien orientado**

Inspiración externa:

- `prabureddy/ai-research-agent-mcp`
- `OD-SWE-bench`

---

## Capa 6 — Runtime de ejecución

Responsabilidad:

- hablar con modelos locales;
- ejecutar herramientas;
- correr código en sandbox;
- coordinar nodos y procesos largos;
- operar en background.

Repositorio actual:

- `src/ia/ollama_provider.py`
- `src/ia/interfaces.py`
- `src/chat/`
- `src/nodes/`
- `src/security/`

Estado:

- **mixto: base existente + integración pendiente**

Inspiración externa:

- `ollama/ollama`
- `kortix-ai/suna`
- `Angeles-HO/Telvyn`

---

## Capa 7 — YeyoDojo + YeyoHack

Responsabilidad:

- agentes especializados por rol;
- score automático de calidad;
- aprendizaje desde feedback y benchmarks;
- entrenamiento, LoRA, adapters y datasets curados.

Repositorio actual:

- documentado en `docs/13-code-dojo.md`
- modelado en `docs/18-capas-datos-nodos.md`
- piezas parciales en `src/quality/`

Estado:

- **concepto fuerte, implementación inicial**

Inspiración externa:

- `pytorch/pytorch`
- `huggingface/transformers`
- `TauricResearch/TradingAgents`

---

## Capa 8 — YeyoNet

Responsabilidad:

- compartir potencia entre máquinas;
- delegar tareas pesadas;
- sincronizar resultados y memorias seleccionadas;
- operar en modo central/satélite.

Repositorio actual:

- documentado en `docs/16-yeyonet.md`

Estado:

- **diseñado, no implementado**

Inspiración externa:

- `agiresearch/AIOS`
- runtimes locales distribuidos y sandboxes persistentes

---

## Capa 9 — Nodos y paquetes

Responsabilidad:

- encapsular capacidades como nodos;
- definir permisos y manifiestos;
- instalar/exportar paquetes `.ypkg`;
- reutilizar grafos como capacidades instalables.

Repositorio actual:

- `src/nodes/`
- `src/pkg/manifest.py`
- `src/pkg/builder.py`
- `src/pkg/installer.py`
- `src/pkg/updater.py`

Estado:

- **base lista para crecer**

---

## Cómo se conecta con lo que ya existe

| Área | Ya existe | Se conserva | Se refuerza con |
|---|---|---|---|
| Interfaces | `src/core/interfaces.py`, `src/core/config.py` | Sí | adapters nuevos |
| Orquestación | `src/orquestador/` | Sí | quality gates, tool routing |
| IA local | `src/ia/ollama_provider.py` | Sí | tool calling estable |
| Memoria | `src/memory/` | Sí | heurísticas tipo `mem0` |
| Investigador | `src/investigador/` | Sí | búsqueda + verificación reales |
| Nodos | `src/nodes/` | Sí | runtime y permisos más fuertes |
| Seguridad | `src/security/` | Sí | sandbox operativo |
| Calidad | `src/quality/` | Sí | benchmark + scoring |
| UI/API | `frontend/`, `src/api/` | Sí | estados, trazas y confianza |

---

## Flujo de una petición

### Caso 1 — Pregunta simple con memoria

```text
Usuario -> API -> YeyoOrquestador
        -> recuperar contexto útil desde Flash Memory
        -> Ollama responde
        -> guardar solo lo relevante
        -> UI muestra respuesta + confianza
```

### Caso 2 — Tarea compleja de código o investigación

```text
Usuario -> API -> YeyoOrquestador
        -> Investigador formula búsqueda
        -> busca en memoria + fuentes externas
        -> evalúa candidatos
        -> ensambla solución al repo actual
        -> ejecuta tests / lint / verificación
        -> si pasa, guarda como memoria útil
        -> si no pasa, reintenta con otro candidato
```

### Caso 3 — Tarea pesada

```text
Usuario -> YeyoOrquestador -> decide trabajo pesado
        -> YeyoNet delega a central o satélite potente
        -> runtime remoto ejecuta
        -> resultado vuelve
        -> se guarda metadata, feedback y aprendizaje
```

---

## Arquitectura anti-slop

YeyoOS reduce slop con reglas de sistema, no con prompts bonitos:

1. **Investigar antes de generar**
2. **Usar tools antes que prose**
3. **Verificar antes de aceptar**
4. **Guardar solo recuerdos útiles**
5. **Aprender solo desde outputs buenos**
6. **Medir con quality gates y benchmarks**
7. **Mostrar nivel de confianza**

Esto conecta directamente con:

- `docs/07-anti-alucinacion.md`
- `docs/17-modelo-investigador.md`
- `docs/18-capas-datos-nodos.md`

---

## Qué queda explícitamente diferido

Estas piezas no desaparecen, pero ya no son prioridad temprana:

- ISO instalable;
- arranque kiosk;
- capa "OS completo";
- packaging Linux-first;
- enterprise/multiusuario;
- hardware exótico.

La razón es simple: primero debe existir un sistema útil, verificable y evolutivo.

---

## Procedimiento oficial para sacar código de otros repos

Esta sección existe para que futuras sesiones no improvisen. Cuando YeyoOS reutilice ideas o código externo, debe seguir este flujo exacto.

## Regla base

> **Nunca importar un repo completo al núcleo de YeyoOS. Siempre extraer módulo por módulo, con adaptación y validación.**

## Paso 1 — Elegir el objetivo exacto

Antes de tocar código externo, se debe responder:

1. ¿Qué problema concreto resuelve?
2. ¿En qué fase del roadmap cae?
3. ¿Qué carpeta local lo recibirá?
4. ¿Es referencia conceptual, adapter reutilizable o código portable?

Ejemplos:

- `mem0` -> heurísticas de ingestión de memoria -> `src/memory/`
- `Telvyn` -> `session_runtime` / `task_memory` / routing -> `src/chat/`, `src/orquestador/`, `src/memory/`
- `AIOS` -> arquitectura de kernel -> referencia para `src/orquestador/` y `src/core/`
- `ai-research-agent-mcp` -> investigator patterns -> `src/investigador/`
- `Suna` -> sandbox/runtime de tools -> `src/security/`, `src/tools/`, `src/nodes/code/`
- `PyTorch` / `Transformers` -> entrenamiento -> `src/ia/`, futuro `src/dojo/` o módulo equivalente

## Paso 2 — Clasificar el repo externo

Todo repo externo debe caer en una de estas categorías:

### A. Referencia solamente

Se usa para arquitectura, patrones o ideas, pero no se copia código textual.

Casos típicos:

- `AIOS`
- `microsoft/JARVIS`
- `AutoGPT`
- `TradingAgents`

### B. Adaptación parcial

Se estudia un módulo puntual y se reimplementa en estilo YeyoOS.

Casos típicos:

- `mem0`
- `Telvyn`
- `ai-research-agent-mcp`
- `Suna`

### C. Integración directa por dependencia o API

No se copia código; se integra el sistema externo como runtime o librería.

Casos típicos:

- `ollama/ollama`
- `pytorch/pytorch`
- `huggingface/transformers`
- `chroma-core/chroma` (si se usa en dev o fallback)

## Paso 3 — Validar licencia antes de copiar texto

Antes de copiar un archivo o fragmento grande:

1. revisar licencia del repo;
2. revisar si el archivo tiene condiciones adicionales;
3. decidir si:
   - se puede reutilizar con atribución;
   - conviene reescribir;
   - solo debe usarse como referencia.

Regla práctica:

- licencia clara y permisiva -> se puede adaptar con cuidado;
- licencia dudosa o restrictiva -> solo referencia hasta verificar.

## Paso 4 — Aislar el módulo exacto

Nunca traer un repo entero. Solo:

- archivo exacto;
- clase exacta;
- función exacta;
- patrón exacto.

Ejemplo correcto:

- tomar la lógica de scoring o extracción de memorias de `mem0`

Ejemplo incorrecto:

- clonar `mem0` completo y mezclarlo dentro de `src/`

## Paso 5 — Crear adapter o reimplementación local

El código externo no entra "tal cual" al corazón del sistema. Debe entrar por estas rutas:

- `src/core/interfaces.py`
- `src/core/config.py`
- `src/ia/`
- `src/memory/`
- `src/orquestador/`
- `src/investigador/`
- `src/security/`
- `src/tools/`

La prioridad es:

1. conservar interfaces internas;
2. adaptar el módulo externo;
3. mantener la dependencia encapsulada.

## Paso 6 — Conectarlo al sistema existente

Todo código adaptado debe declarar claramente:

- qué entra;
- qué sale;
- qué memoria usa;
- qué tools necesita;
- qué quality gates debe pasar.

Ejemplos de conexión:

### `mem0` -> `Flash Memory`

```text
chat/agente
  -> extractor de recuerdos
  -> reglas de qué guardar
  -> store/search en Flash Memory
  -> retrieval para contexto útil
```

### `Telvyn` -> runtime local-first

```text
entrada usuario
  -> routing semántico
  -> session runtime
  -> task memory
  -> subgrafo/agente adecuado
```

### `ai-research-agent-mcp` -> investigador

```text
tarea compleja
  -> buscar
  -> resumir candidatos
  -> evaluar
  -> ensamblar al repo actual
  -> verificar
  -> guardar solución válida
```

### `Suna` -> runtime seguro de tools

```text
YeyoOrquestador
  -> pide ejecución real
  -> sandbox / tools / procesos
  -> resultado estructurado
  -> quality gate
```

## Paso 7 — Validación obligatoria

Ningún código adaptado queda “aceptado” hasta pasar:

1. pruebas unitarias o integración relevantes;
2. verificación de compatibilidad con interfaces internas;
3. revisión de seguridad si toca tools, red, archivos o ejecución;
4. prueba real en el flujo donde se usará.

## Paso 8 — Registrar la procedencia

Cada adopción relevante debe dejar constancia en el mismo commit o en el doc tocado:

- repo fuente;
- módulo tomado;
- si fue referencia, adaptación o integración;
- carpeta destino en YeyoOS.

Esto permite que otra sesión continúe sin volver a descubrir el trabajo.

## Mapa inicial de extracción por repo

| Repo | Qué sacar | Tipo | Destino en YeyoOS |
|---|---|---|---|
| `mem0ai/mem0` | extracción/actualización de recuerdos | adaptación parcial | `src/memory/` |
| `ollama/ollama` | runtime por API | integración directa | `src/ia/` |
| `unslothai/unsloth` | fine-tuning eficiente, LoRA/QLoRA, RL liviano, recetas de datos | integración directa | futuro módulo de entrenamiento / `YeyoDojo` |
| `axolotl-ai-cloud/axolotl` | fine-tuning robusto, configs YAML, QLoRA/DPO/RL, multi-GPU | integración directa | futuro módulo de entrenamiento / `YeyoDojo` / `YeyoHack` |
| `Angeles-HO/Telvyn` | `session_runtime`, `task_memory`, routing | adaptación parcial | `src/chat/`, `src/orquestador/`, `src/memory/` |
| `prabureddy/ai-research-agent-mcp` | research pipeline patterns | adaptación parcial | `src/investigador/` |
| `kortix-ai/suna` | sandbox/runtime de tools | adaptación parcial | `src/security/`, `src/tools/`, `src/nodes/code/` |
| `agiresearch/AIOS` | patrón de kernel | referencia | `src/orquestador/`, `src/core/` |
| `Significant-Gravitas/AutoGPT` | workflows/block builder | referencia | `src/orquestador/`, `frontend/` |
| `TauricResearch/TradingAgents` | roles especializados | referencia | `docs/13`, futuro Dojo |
| `pytorch/pytorch` | training runtime | integración directa | futuro módulo de entrenamiento |
| `huggingface/transformers` | fine-tuning/adapters/eval | integración directa | futuro módulo de entrenamiento |

## Regla final

Si una sesión futura duda qué hacer, el orden es:

1. leer `docs/02-arquitectura.md`;
2. leer `docs/10-fases.md`;
3. elegir fase activa;
4. elegir repo externo por necesidad concreta;
5. extraer solo el módulo necesario;
6. adaptarlo a interfaces de YeyoOS;
7. verificarlo antes de integrarlo.

---

## Cómo tratamos el problema de los modelos pequeños

Los modelos pequeños no se "arreglan" solo con prompts. En YeyoOS el enfoque correcto es combinar:

1. **menos carga cognitiva al modelo**;
2. **mejor contexto y memoria**;
3. **verificación real**;
4. **fine-tuning/adapters cuando el hardware lo permita**.

### Qué resuelve cada repositorio

#### `unslothai/unsloth`

Sirve para:

- sacar más rendimiento de modelos chicos con menos VRAM;
- LoRA y QLoRA más rápidas;
- RL más eficiente;
- creación y curación de datasets;
- exportación de modelos/adapters.

En YeyoOS encaja como:

- stack de entrenamiento rápido para `YeyoDojo`;
- laboratorio de experimentación para mejorar modelos chicos;
- opción preferida cuando el hardware es limitado y se quiere iterar rápido.

**Conclusión:** es la mejor opción para prototipar y exprimir modelos pequeños en entorno de recursos ajustados.

#### `axolotl-ai-cloud/axolotl`

Sirve para:

- pipelines de fine-tuning más serios y reproducibles;
- configuraciones YAML reutilizables;
- LoRA, QLoRA, DPO, RL, reward modelling;
- entrenamiento multi-GPU y multi-nodo;
- evaluación/quantización/inferencia dentro del mismo flujo.

En YeyoOS encaja como:

- stack de entrenamiento robusto para el nodo central de `YeyoNet`;
- backend de entrenamiento formal para `YeyoDojo` y `YeyoHack`;
- opción preferida para runs largos, repetibles y escalables.

**Conclusión:** es la mejor opción para entrenamientos "de producción" o cuando YeyoNet ya tenga una máquina central potente.

### Regla operativa

- si queremos **iterar rápido y barato** -> `Unsloth`
- si queremos **pipeline serio, repetible y escalable** -> `Axolotl`
- si el hardware local no alcanza -> usar `YeyoNet` o delegar entrenamiento

### Cómo se conecta con YeyoOS

```text
Flash Memory + feedback + errores aprendidos + benchmark
    -> dataset curado
    -> Unsloth o Axolotl
    -> LoRA / adapter / modelo refinado
    -> evaluación
    -> exportación
    -> runtime de inferencia (Ollama o formato compatible)
```

### Qué NO hace ninguno de los dos

Ni `Unsloth` ni `Axolotl` convierten por sí solos un modelo pequeño en un genio.

Lo que sí hacen es:

- aprovechar mejor datos buenos;
- reducir costo de ajuste;
- volver el entrenamiento más sistemático;
- mejorar un modelo dentro de un dominio concreto.

Por eso en YeyoOS siguen siendo obligatorios:

- `Flash Memory`
- `Investigador`
- `Quality Kernel`
- `YeyoDojo`
- benchmarks y feedback real

---

## Arquitectura objetivo por carpetas

```text
src/
├── api/            # entrada HTTP/WebSocket
├── chat/           # conversación y token budget
├── core/           # interfaces y config central
├── ia/             # providers LLM/embeddings/streaming
├── investigador/   # buscar, evaluar, ensamblar, verificar
├── memory/         # Flash Memory y tiers
├── nodes/          # capacidades de dominio
├── orquestador/    # kernel de grafos
├── pkg/            # manifiestos e instalación de nodos
├── quality/        # quality gates, benchmark, lint
├── security/       # permisos, sandbox, auditoría
└── tools/          # herramientas ejecutables por agentes
```

---

## Documento fuente de verdad

Después de esta unificación:

- `docs/02-arquitectura.md` es el documento maestro;
- `docs/05`, `15`, `16`, `17`, `18` son especializaciones;
- `docs/09` y `docs/10` quedan alineados con esta arquitectura;
- las referencias viejas a `OpenClaw`, memoria de "5 capas" y prioridad `OS-first` se consideran obsoletas.
