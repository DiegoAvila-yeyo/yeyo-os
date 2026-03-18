# 05 — Sistema de Memoria (5 Capas)

## Principio

**YeyoOS nunca olvida nada.** Cada conversación, cada imagen, cada decisión se almacena y es recuperable. La IA siempre tiene contexto completo sobre quién eres, qué has hecho y qué te gusta.

## Las 5 Capas

```
┌─────────────────────────────────────────────────────┐
│  Capa 1: FLASH          │ RAM          │ Instantáneo │
├─────────────────────────────────────────────────────┤
│  Capa 2: TRABAJO        │ Redis        │ Rápido      │
├─────────────────────────────────────────────────────┤
│  Capa 3: EPISÓDICA      │ PostgreSQL   │ Permanente  │
│                         │ + pgvector   │             │
├─────────────────────────────────────────────────────┤
│  Capa 4: CONOCIMIENTO   │ PostgreSQL   │ Permanente  │
├─────────────────────────────────────────────────────┤
│  Capa 5: ARCHIVOS       │ Storage +    │ Permanente  │
│                         │ PostgreSQL   │             │
└─────────────────────────────────────────────────────┘
```

---

### Capa 1: Memoria Flash (RAM)

**¿Qué guarda?** Los últimos 10-20 mensajes de la conversación actual.

**¿Dónde?** Variable en memoria del proceso.

**Velocidad:** Instantánea (0ms).

**Duración:** Se pierde al cerrar el nodo o reiniciar.

**Pregunta que responde:** *"¿Qué acabas de decir hace 2 segundos?"*

**Ejemplo:**
```
Tú: "Hazme un logo azul"
IA: "Aquí tienes 3 opciones"
Tú: "Me gusta la segunda"        ← Capa Flash sabe cuál es "la segunda"
```

---

### Capa 2: Memoria de Trabajo (Redis)

**¿Qué guarda?** Contexto de la sesión activa: qué nodos abriste, qué archivos tocaste, qué estás haciendo hoy.

**¿Dónde?** Redis (cache en memoria con persistencia).

**Velocidad:** Muy rápida (1-5ms).

**Duración:** Expira en 24-48 horas.

**Pregunta que responde:** *"¿Qué estuvimos haciendo hace rato?"*

**Ejemplo:**
```
(Hace 2 horas generaste imágenes de logos)
Tú: "Sigue con lo del logo"
IA: "Claro, retomamos el logo cyberpunk azul. La última versión fue esta..."
```

**Datos almacenados:**
```json
{
  "session_id": "abc123",
  "nodos_abiertos": ["imagen", "video"],
  "ultimo_archivo": "img_0847.png",
  "contexto_actual": "Trabajando en logo cyberpunk para marca X",
  "inicio_sesion": "2026-03-18T06:00:00Z"
}
```

---

### Capa 3: Memoria Episódica (PostgreSQL + pgvector)

**¿Qué guarda?** Cada conversación completa, con embeddings para búsqueda semántica.

**¿Dónde?** PostgreSQL con extensión pgvector.

**Velocidad:** Rápida (10-50ms).

**Duración:** Permanente.

**Pregunta que responde:** *"¿Qué pasó la semana pasada? ¿Y hace 3 meses?"*

**Ejemplo:**
```
Tú: "¿Qué logos hicimos en febrero?"
IA: "En febrero hiciste 23 logos. Los principales fueron:
     - Logo minimalista para el proyecto X (3 feb)
     - Logo cyberpunk para la marca Y (15 feb)
     - Variaciones del logo de tu canal (22 feb)"
```

**Datos almacenados:**
```json
{
  "conversacion_id": 4523,
  "nodo": "imagen",
  "mensajes": [...],
  "resumen": "Usuario creó logo cyberpunk azul para marca X",
  "embedding": [0.23, 0.45, 0.12, ...],
  "archivos_generados": ["img_0845.png", "img_0846.png", "img_0847.png"],
  "fecha": "2026-03-18T06:30:00Z"
}
```

**Búsqueda semántica (pgvector):**
```sql
-- Buscar conversaciones similares a "logo para empresa"
SELECT * FROM conversaciones
ORDER BY embedding <-> pgvector('logo para empresa')
LIMIT 10;
```

---

### Capa 4: Memoria de Conocimiento (PostgreSQL)

**¿Qué guarda?** Hechos concretos extraídos automáticamente de las conversaciones. Es lo que la IA "sabe" sobre ti.

**¿Dónde?** PostgreSQL (tabla dedicada).

**Velocidad:** Rápida (5-20ms).

**Duración:** Permanente. Se actualiza automáticamente.

**Pregunta que responde:** *"¿Quién soy y qué me gusta?"*

**Ejemplo:**
```
La IA sabe sin que le digas cada vez:
- Te gusta el estilo cyberpunk
- Tu canal de YouTube se llama "X"
- Prefieres videos cortos de 60 segundos
- Tu stack es Next.js + FastAPI
- Tu GPU es una GTX 1060 (ajusta calidad automáticamente)
- Los martes publicas en TikTok
```

**Datos almacenados:**
```json
{
  "hechos": [
    {
      "categoria": "preferencia_visual",
      "hecho": "El usuario prefiere estilo cyberpunk oscuro",
      "confianza": 0.95,
      "fuente": "conversaciones 4501, 4512, 4523",
      "actualizado": "2026-03-18"
    },
    {
      "categoria": "dato_personal",
      "hecho": "Canal de YouTube: MiCanal",
      "confianza": 1.0,
      "fuente": "conversacion 4100",
      "actualizado": "2026-02-10"
    }
  ]
}
```

**Actualización automática:**
```
Conversación detecta nuevo hecho:
  Tú: "Cambié el nombre de mi canal a NuevoNombre"
  
  → Sistema actualiza Capa 4:
    "Canal de YouTube: MiCanal" → "Canal de YouTube: NuevoNombre"
    confianza: 1.0 (dicho explícitamente)
```

---

### Capa 5: Memoria de Archivos (Storage + PostgreSQL)

**¿Qué guarda?** Cada archivo generado por el sistema, con metadata completa, tags automáticos y versionado.

**¿Dónde?** 
- Archivos físicos: `/storage/archivos/`
- Metadata: PostgreSQL
- Embeddings: pgvector

**Velocidad:** Variable (depende del tamaño del archivo).

**Duración:** Permanente.

**Pregunta que responde:** *"¿Dónde está lo que creamos?"*

**Estructura de almacenamiento:**
```
/storage/
├── archivos/
│   ├── 2026/
│   │   ├── 03/
│   │   │   ├── img_0847.png
│   │   │   ├── video_0123.mp4
│   │   │   └── guion_0456.txt
│   │   └── 02/
│   │       └── ...
│   └── ...
└── backups/
```

**Metadata por archivo:**
```json
{
  "id": "file_0847",
  "archivo": "img_0847.png",
  "ruta": "/storage/archivos/2026/03/img_0847.png",
  "tipo": "imagen",
  "formato": "png",
  "tamaño": "2.3MB",
  "creado_por_nodo": "imagen",
  "conversacion_id": 4523,
  "prompt_original": "logo cyberpunk azul con neon",
  "tags_automaticos": ["logo", "cyberpunk", "azul", "neon", "marca"],
  "version": 3,
  "versiones_anteriores": ["file_0845", "file_0846"],
  "embedding": [0.34, 0.56, ...],
  "fecha_creacion": "2026-03-18T06:30:00Z"
}
```

---

## Flujo Completo: Cómo Trabajan las 5 Capas Juntas

```
Tú dices: "Modifica el logo que hicimos ayer"

1. Capa 1 (Flash): No tiene info de ayer → Pasa a Capa 2

2. Capa 2 (Trabajo): ¿Hay algo de logos en la sesión de hoy?
   → No → Pasa a Capa 3

3. Capa 3 (Episódica): Busca conversaciones sobre logos de ayer
   → Encontró: conversación #4523, logo cyberpunk azul

4. Capa 4 (Conocimiento): ¿Qué sabemos del usuario?
   → Le gusta estilo cyberpunk, prefiere tonos oscuros

5. Capa 5 (Archivos): ¿Dónde está el archivo?
   → img_0847.png, versión 3

6. Se construye el contexto para Ollama:
   [Conocimiento del usuario] +
   [Conversación de ayer resumida] +
   [Archivo encontrado] +
   [Tu mensaje actual]

7. Ollama responde: "Claro, aquí está el logo de ayer (img_0847.png).
   ¿Qué modificación quieres hacerle?"
```

## Modelo de Embeddings

Para la búsqueda semántica (Capas 3 y 5) se usa un modelo de embeddings local:

- **Modelo:** `nomic-embed-text` (corre en Ollama, ligero)
- **Función:** Convierte texto en vectores numéricos para buscar por significado
- **Ejemplo:** "logo oscuro" encontrará "imagen cyberpunk con tonos nocturnos" aunque no compartan palabras exactas

## Backups Automáticos

PostgreSQL se respalda automáticamente:
- Backup incremental cada 6 horas
- Backup completo diario
- Retención de 30 días
- Los archivos de `/storage/` también se respaldan
