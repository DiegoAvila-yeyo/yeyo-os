# 04 — Nodos y Funcionalidades

## Resumen de Nodos

| Nodo | Función | Herramientas Backend |
|------|---------|---------------------|
| 🔴 YEYO (Centro) | Hub visual, chat general | Ollama, OpenClaw |
| 🎨 Imagen | Generación y edición de imágenes con IA | Stable Diffusion, LLaVA |
| 🎬 Video | Creación y edición de videos con IA | FFmpeg, moviepy |
| 🤖 Automatización | Pipeline de contenido para redes sociales | APIs sociales, Celery |
| 💻 Código | Programación con IA (vibe coding) | Terminal, VS Code, Git |
| 📁 Archivos | Explorador inteligente de archivos | Storage, pgvector |
| 🌐 Navegador | Navegación web | Chromium embebido |
| ⚙️ Configuración | Ajustes del sistema | Sistema |

## Detalle por Nodo

---

### 🔴 YEYO (Nodo Central)

**Propósito:** Es el corazón del sistema. Desde aquí puedes hablar con la IA de forma general y el sistema decide a qué nodo derivar tu petición.

**Interacción:**
- Chat general: "Genera un logo" → Te redirige al nodo Imagen
- Preguntas: "¿Qué hice ayer?" → Busca en memoria
- Comandos: "Abre el editor de video" → Abre el nodo Video
- Creación de nodos: "Crea un nodo para música" → Genera nuevo nodo

**Capacidades:**
- Entender intención del usuario
- Routing inteligente a nodos específicos
- Crear nuevos nodos dinámicamente
- Chat conversacional general

---

### 🎨 Nodo Imagen

**Propósito:** Generar, editar y refinar imágenes usando IA.

**Layout:** Chat (izquierda) + Pizarrón/Galería (derecha)

**Flujo de trabajo:**
1. Usuario describe la imagen deseada en el chat
2. Puede adjuntar imágenes de referencia (drag & drop)
3. La IA genera opciones → Aparecen en el pizarrón
4. Click en una imagen → Mini-chat para refinarla
5. Iteración hasta lograr el resultado deseado
6. Guardar versión final → Se almacena con metadata completa

**Herramientas Backend:**
- **Stable Diffusion:** Generación de imágenes (text-to-image, image-to-image)
- **LLaVA:** Entender imágenes de referencia ("hazla como esta pero...")
- **Ollama:** Mejorar prompts automáticamente
- **Storage:** Guardar versiones con metadata y tags

**Limitaciones actuales (GTX 1060 3GB):**
- Resoluciones bajas (~512x512)
- Generación lenta (~30-60 seg por imagen)
- Con upgrade de GPU → resoluciones altas, generación rápida

---

### 🎬 Nodo Video

**Propósito:** Crear y editar videos con asistencia de IA.

**Layout:** Chat (izquierda) + Timeline (derecha)

**Flujo de trabajo:**
1. Usuario describe el video deseado
2. Puede adjuntar imágenes/videos de referencia para guiar el estilo
3. La IA genera clips individuales → Aparecen en la timeline
4. Click en un clip → Mini-chat para refinarlo (más lento, más oscuro, etc.)
5. Conectar clips en secuencia
6. "Únelos" → Video final exportado

**Herramientas Backend:**
- **FFmpeg:** Procesamiento de video (cortes, transiciones, codificación)
- **moviepy:** Edición programática de video
- **Whisper:** Transcripción de audio (subtítulos automáticos)
- **Bark/XTTS:** Generación de voz para narración
- **Ollama:** Dirección creativa, guiones

**Características:**
- Subtítulos automáticos (Whisper)
- Narración por IA (Bark/XTTS)
- Música de fondo (integración futura)
- Exportación en múltiples formatos y resoluciones

---

### 🤖 Nodo Automatización

**Propósito:** Pipeline automatizado de creación y publicación de contenido para redes sociales.

**Layout:** Analytics + Chat (izquierda) + Pipeline Visual (derecha)

**Pipeline de Estaciones:**
```
[Análisis] → [Guiones] → [Edición] → [Publicación]
     ↑                                      │
     └──────── feedback loop ────────────────┘
```

**Estación: Análisis**
- Conecta a APIs de YouTube, TikTok, Instagram
- Muestra métricas en tiempo real
- Detecta tendencias automáticamente
- Sugiere tipo de contenido basado en datos

**Estación: Guiones**
- Genera guiones optimizados para cada plataforma
- Considera tendencias detectadas
- Personalizable por estilo del creador

**Estación: Edición**
- Edición automática de video (cortes, subtítulos, música)
- Usa el nodo Video internamente
- Formatos adaptados a cada plataforma (vertical para TikTok, horizontal para YouTube)

**Estación: Publicación**
- Sube videos a múltiples plataformas
- Genera títulos y descripciones optimizados
- Programa publicaciones en horarios óptimos

**APIs Necesarias:**
- YouTube Data API v3
- TikTok API
- Instagram Graph API

---

### 💻 Nodo Código

**Propósito:** Desarrollo de software con IA integrada (vibe coding).

**Layout:** Chat (izquierda) + Editor/Terminal (derecha)

**Herramientas Disponibles:**
- **Terminal embebida:** Acceso completo al sistema (dentro del sandbox)
- **VS Code Server:** Editor completo que corre en el browser
- **Git:** Control de versiones integrado
- **Docker:** Levantar servicios de prueba

**Capacidades:**
- Programar en cualquier lenguaje (Python, JS, Go, Rust, etc.)
- Vibe coding: describir lo que quieres → la IA genera el código
- Debugging asistido por IA
- Tests automáticos
- Deploy de aplicaciones

**Integración con IA:**
- Copilot-like: sugerencias mientras escribes
- Chat contextual: preguntar sobre el código actual
- Refactoring asistido
- Generación de tests

**Uso especial:** Mejorar el propio YeyoOS y OpenClaw desde dentro del sistema.

---

### 📁 Nodo Archivos

**Propósito:** Explorador inteligente de todos los archivos generados por el sistema.

**Layout:** Chat (izquierda) + Explorador con filtros (derecha)

**Búsqueda Inteligente:**
- Por texto: "logo cyberpunk" → Busca en metadata
- Por significado: "imágenes oscuras" → Busca por embeddings (pgvector)
- Por relación: "lo que usé en el video de cocina" → Busca por conversación vinculada
- Por fecha: "todo lo de esta semana"
- Por tipo: "solo videos"
- Por nodo de origen: "lo que generé en el nodo Imagen"

**Metadata Automática:**
Cada archivo se guarda con:
```json
{
  "archivo": "img_0847.png",
  "tipo": "imagen",
  "creado_por": "nodo-imagen",
  "prompt": "logo cyberpunk azul",
  "conversacion_id": 4523,
  "tags": ["logo", "cyberpunk", "azul", "marca"],
  "version": 3,
  "versiones_anteriores": ["img_0845.png", "img_0846.png"],
  "embedding": [0.23, 0.45, ...],
  "fecha": "2026-03-18T06:00:00Z"
}
```

---

### 🌐 Nodo Navegador

**Propósito:** Navegación web completa.

**Implementación:** Chromium embebido dentro de la interfaz del nodo.

**Características:**
- Navegación estándar (cualquier sitio web)
- Capacidad de instalar aplicaciones web
- Integración con la IA: "resume esta página" → La IA lee y resume

---

### ⚙️ Nodo Configuración

**Propósito:** Ajustes del sistema.

**Incluye:**
- Selección de modelo IA (qué modelo usar en Ollama)
- Configuración de APIs (YouTube, TikTok, etc.)
- Gestión de memoria (ver/limpiar capas)
- Configuración de seguridad (zonas verde/amarilla/roja)
- Temas visuales
- Gestión de usuarios (futuro)
- Información del sistema (GPU, RAM, disco)

---

### ⛏️ Nodo Minería

**Propósito:** Gestión inteligente de ASICs de minería de criptomonedas.

**Layout:** Chat (izquierda) + Dashboard de minería (derecha)

**Importante:** La GPU NUNCA se usa para minería — es exclusivamente para IA.

**Cómo funciona:**
- ASICs se conectan a YeyoOS vía red local (mismo router)
- ASICs están en una VLAN separada (no pueden acceder a YeyoOS, solo YeyoOS los controla)
- La IA optimiza:
  - Qué criptomoneda minar (según precio/dificultad/electricidad)
  - Cuándo minar (horarios de electricidad barata)
  - Pool de minería óptimo
  - Temperatura y vida útil de los ASICs

**Herramientas Backend:**
- APIs de pools de minería
- APIs de precio de criptomonedas
- Monitoreo de hardware ASIC vía red local
- Dashboard de rentabilidad

**Seguridad:**
- Control unidireccional: YeyoOS → ASICs (nunca al revés)
- VLAN aislada
- Los ASICs no tienen acceso a la red principal ni a los datos del sistema

---

## Creación Dinámica de Nodos

El sistema permite crear nuevos nodos desde el YEYO central:

**Proceso:**
1. "Crea un nodo para generar música"
2. La IA analiza qué herramientas necesita
3. Genera la estructura frontend + backend del nodo
4. El nodo aparece en la pantalla principal
5. Se puede usar inmediatamente

**Esto es posible porque:**
- Todos los nodos siguen el mismo patrón (Chat + Área de trabajo)
- Los componentes compartidos (ChatPanel, MiniChat) se reutilizan
- El backend de FastAPI puede registrar nuevas rutas dinámicamente

**YEYO-PKG:** Los nodos se distribuyen como paquetes `.ypkg` a través de la YEYO Store. Los usuarios pueden instalar nodos creados por la comunidad o crear los suyos propios simplemente describiéndolos a la IA. Ver [12-yeyo-pkg.md](12-yeyo-pkg.md) para más detalles.
