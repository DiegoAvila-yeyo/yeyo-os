# 12 — YEYO-PKG: Sistema de Paquetes

## Resumen

YEYO-PKG es el sistema de gestión de paquetes de YeyoOS. Los usuarios **nunca** usan la línea de comandos — le hablan a la IA: _"Necesito editar video"_ y la IA se encarga de buscar, recomendar e instalar. YEYO-PKG también permite que la IA **genere nodos completos dinámicamente**.

## Las 3 Capas

```
┌─────────────────────────────────────────────┐
│  Capa 3: YEYO Store (Marketplace)           │
│  Tienda visual, reseñas, IA recomienda      │
├─────────────────────────────────────────────┤
│  Capa 2: YEYO-PKG (.ypkg)                  │
│  Paquetes nativos de YeyoOS, con IA y nodo  │
├─────────────────────────────────────────────┤
│  Capa 1: apt (invisible)                    │
│  Paquetes base de Linux, el usuario no ve   │
└─────────────────────────────────────────────┘
```

| Capa | Tecnología | Visible al usuario | Ejemplo |
|------|-----------|-------------------|---------|
| **Base** | apt (Debian/Ubuntu) | ❌ Invisible | ffmpeg, python3, cuda-toolkit |
| **Nodos** | YEYO-PKG (.ypkg) | ✅ Vía IA | nodo-video, nodo-imagen, nodo-finanzas |
| **Tienda** | YEYO Store | ✅ Marketplace | Explorar, instalar, calificar |

## Formato `.ypkg`

Un paquete `.ypkg` es un archivo comprimido con la siguiente estructura:

```
mi-nodo.ypkg/
├── manifest.yml           # Metadata del paquete
├── signature.sig          # Firma digital del autor
├── checksum.sha256        # Checksum de integridad
├── container/             # Archivos del contenedor
│   ├── Dockerfile         # Imagen del contenedor
│   ├── entrypoint.sh      # Script de inicio
│   └── app/               # Código de la aplicación
├── ui/                    # Interfaz del nodo
│   ├── layout.yml         # Definición del layout
│   ├── theme.yml          # Colores y estilos
│   └── assets/            # Iconos, imágenes
├── api/                   # API del nodo
│   ├── endpoints.yml      # Endpoints expuestos
│   └── schemas/           # Schemas de datos
├── ai/                    # Configuración de IA
│   ├── models.yml         # Modelos requeridos
│   ├── prompts/           # System prompts
│   │   ├── main.txt       # Prompt principal
│   │   └── tools.txt      # Prompts para tools
│   └── tools/             # Herramientas de IA
│       ├── tool1.yml      # Definición de tool
│       └── tool2.yml
├── permissions.yml        # Permisos requeridos
├── hooks/                 # Scripts de ciclo de vida
│   ├── pre-install.sh
│   ├── post-install.sh
│   ├── pre-update.sh
│   ├── post-update.sh
│   └── pre-remove.sh
└── tests/                 # Tests del paquete
    ├── test_install.sh
    ├── test_api.sh
    └── test_ai.sh
```

## `manifest.yml`

```yaml
# manifest.yml — Metadata completa del paquete
name: "Editor de Video"
id: "nodo-video"
version: "1.2.0"
author:
  name: "YeyoOS Team"
  email: "team@yeyoos.dev"
  key_id: "YEYO-OFFICIAL-2024"
icon: "🎬"
color: "#FF6B35"
category: "multimedia"
description: "Editor de video potenciado por IA con timeline, efectos y exportación"

# Requisitos del sistema
requires:
  yeyoos: ">=1.0.0"
  gpu_vram: "4GB"     # Mínimo de VRAM
  ram: "8GB"           # Mínimo de RAM
  disk: "2GB"          # Espacio requerido

# Dependencias
dependencies:
  nodos:
    - "nodo-archivos"        # Para acceder a archivos del usuario
  system_packages:
    - "ffmpeg>=6.0"
    - "python3>=3.11"
  ai_models:
    - name: "llava"
      size: "4.7GB"
      optional: false        # Requerido para funcionar
    - name: "whisper-large"
      size: "2.9GB"
      optional: true         # Para transcripción de audio (funcionalidad extra)

# Permisos
permissions:
  filesystem:
    read:
      - "~/Videos"
      - "~/Descargas"
      - "/tmp/yeyo-video"
    write:
      - "~/Videos/exports"
      - "/tmp/yeyo-video"
  network: false             # No necesita internet
  gpu: true                  # Necesita acceso a GPU
  mic: true                  # Para grabar narración
  camera: false

# Configuración de IA para este nodo
ai:
  system_prompt: "prompts/main.txt"
  tools:
    - "tools/cut_video.yml"
    - "tools/add_effect.yml"
    - "tools/export.yml"
    - "tools/add_music.yml"
  max_tokens: 4096

# Configuración visual del nodo
node_ui:
  layout: "chat_workspace"   # chat_workspace | full_canvas | dashboard | custom
  position: "auto"           # auto | {x, y}
  size:
    collapsed_radius: 45
    expanded: "fullscreen"   # fullscreen | {width, height}
```

## `permissions.yml`

```yaml
# permissions.yml — Detalle granular de permisos
version: 1

filesystem:
  read:
    - path: "~/Videos"
      reason: "Acceder a videos existentes del usuario"
    - path: "~/Descargas"
      reason: "Importar archivos descargados"
    - path: "/tmp/yeyo-video"
      reason: "Archivos temporales de procesamiento"
  write:
    - path: "~/Videos/exports"
      reason: "Guardar videos exportados"
    - path: "/tmp/yeyo-video"
      reason: "Archivos temporales de procesamiento"

network:
  enabled: false

gpu:
  enabled: true
  reason: "Renderizado de video y efectos en tiempo real"
  max_vram: "2GB"

audio:
  mic:
    enabled: true
    reason: "Grabar narración para el video"
  speakers:
    enabled: true
    reason: "Previsualizar audio del video"

camera:
  enabled: false

ipc:
  allowed_nodes:
    - "nodo-archivos"    # Para abrir/guardar archivos
    - "nodo-imagen"      # Para importar imágenes al video
```

## `ai/models.yml`

```yaml
# ai/models.yml — Modelos de IA requeridos
models:
  - name: "llava"
    provider: "ollama"
    purpose: "Entender frames de video, sugerir ediciones"
    required: true
    min_vram: "4GB"

  - name: "whisper-large"
    provider: "ollama"
    purpose: "Transcribir audio del video"
    required: false
    min_vram: "1.5GB"
    fallback: "whisper-small"   # Si no hay suficiente VRAM
```

## Flujo de Instalación

```
┌──────────────┐
│  1. Download │ ← Descargar .ypkg del Store o generado por IA
└──────┬───────┘
       │
┌──────▼──────────────┐
│  2. Verificar firma │ ← signature.sig + checksum.sha256
│     + checksum      │   Si falla → RECHAZAR
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  3. Check requisitos│ ← GPU, RAM, disco, versión YeyoOS
│                     │   Si no cumple → informar al usuario
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  4. Mostrar permisos│ ← El usuario ve exactamente qué accede
│     al usuario      │   "Este nodo quiere acceso a ~/Videos"
│                     │   Usuario acepta o rechaza
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  5. Snapshot BTRFS  │ ← Punto de restauración antes de cambios
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  6. Instalar        │ ← Crear contenedor, configurar socket
│     contenedor      │   Wayland, montar volúmenes
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  7. Descargar       │ ← ollama pull para cada modelo requerido
│     modelos IA      │   (los opcionales se preguntan al usuario)
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  8. Registrar en    │ ← Notificar al compositor
│     Hub             │   Crear superficie Wayland
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  9. Nodo aparece    │ ← Animación de entrada en el Hub
│     con animación   │   ¡Listo para usar!
└──────────────────────┘

⚠️  Si CUALQUIER paso falla → Rollback automático al snapshot BTRFS
```

```yaml
# Ejemplo de log de instalación exitosa
install_log:
  package: "nodo-video"
  version: "1.2.0"
  steps:
    - step: "download"
      status: "ok"
      duration: "3.2s"
    - step: "verify_signature"
      status: "ok"
      signer: "YeyoOS Team (YEYO-OFFICIAL-2024)"
    - step: "verify_checksum"
      status: "ok"
      hash: "sha256:a1b2c3d4..."
    - step: "check_requirements"
      status: "ok"
      gpu_vram: "8GB >= 4GB ✓"
      ram: "32GB >= 8GB ✓"
      disk: "120GB free >= 2GB ✓"
    - step: "user_permissions"
      status: "accepted"
    - step: "snapshot"
      status: "ok"
      snapshot_id: "pre-install-nodo-video-1.2.0"
    - step: "install_container"
      status: "ok"
      socket: "/run/yeyo/wayland-video"
    - step: "download_models"
      status: "ok"
      models:
        - "llava (4.7GB) ✓"
        - "whisper-large (2.9GB) - skipped (optional)"
    - step: "register_hub"
      status: "ok"
    - step: "animation"
      status: "ok"
  total_duration: "47s"
  result: "success"
```

## Pipeline de Seguridad (YEYO Store)

Antes de que un paquete aparezca en la tienda, pasa por un pipeline completo:

```
Subir .ypkg al Store
       │
┌──────▼──────────────┐
│  1. Verificación    │ ← ¿Firma válida? ¿Autor registrado?
│     de firma        │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  2. Análisis        │ ← Escaneo estático de código
│     estático        │   Detectar: malware, backdoors, mineros,
│                     │   accesos no declarados en permisos
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  3. Testing en      │ ← Ejecutar en sandbox aislado
│     sandbox         │   Monitorear: syscalls, red, disco
│                     │   ¿Hace lo que dice que hace?
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  4. Revisión de     │ ← ¿Los permisos son razonables?
│     permisos        │   ¿Un editor de texto pide acceso a cámara?
│                     │   → RECHAZAR
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  5. Aprobación      │ ← Automática o manual según nivel de riesgo
└──────────────────────┘
```

## Niveles de Confianza

| Nivel | Icono | Significado | Instalación |
|-------|-------|-------------|-------------|
| **Official** | 🟢 | Creado por el equipo de YeyoOS | Auto-install, sin confirmación |
| **Verified** | 🔵 | Desarrollador conocido y verificado | Confirmación rápida |
| **Community** | 🟡 | Pasó el escaneo automático | Muestra permisos detallados |
| **Unverified** | 🔴 | No está en el Store | Advertencia fuerte, doble confirmación |

```yaml
# Ejemplo de metadata de confianza
trust:
  level: "verified"
  author_verified: true
  signature_valid: true
  store_approved: true
  last_audit: "2024-11-15"
  scan_results:
    malware: "clean"
    permissions: "reasonable"
    sandbox_test: "passed"
```

## Protección de Cadena de Suministro

Cada versión nueva de un paquete pasa por el pipeline completo, sin excepciones:

```
┌─────────────────────────────────────────────────────┐
│  Supply Chain Protection                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Cada versión pasa el pipeline completo          │
│     (no hay "fast-track" para autores conocidos)    │
│                                                     │
│  2. Diff automático entre versiones                 │
│     - ¿Qué archivos cambiaron?                     │
│     - ¿Se añadieron nuevos permisos?                │
│     - ¿Nuevas dependencias sospechosas?             │
│                                                     │
│  3. Cambios sospechosos → bloqueado                 │
│     - Nuevo permiso de red en app offline           │
│     - Acceso a rutas fuera de lo declarado          │
│     - Binarios no compilados desde el source        │
│     - Dependencias con vulnerabilidades conocidas   │
│                                                     │
│  4. Alertas al usuario si un paquete instalado      │
│     tiene una nueva versión con más permisos        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

```yaml
# Ejemplo de diff entre versiones
version_diff:
  from: "1.1.0"
  to: "1.2.0"
  changes:
    files_added: 3
    files_modified: 7
    files_removed: 0
    permissions_changes:
      added:
        - "mic: true (razón: grabar narración)"
      removed: []
    new_dependencies:
      - "whisper-large (modelo IA, optional)"
    risk_assessment: "low"
    auto_approved: true
```

## Comandos CLI

> **Nota:** Los usuarios normales nunca usan estos comandos. Le hablan a la IA.
> Estos comandos existen para desarrolladores y administradores.

```bash
# Buscar paquetes
yeyo-pkg search "video editor"
yeyo-pkg search --category multimedia

# Instalar un paquete
yeyo-pkg install nodo-video
yeyo-pkg install nodo-video --version 1.2.0
yeyo-pkg install ./mi-nodo-custom.ypkg    # Instalar local

# Actualizar
yeyo-pkg update nodo-video                 # Actualizar uno
yeyo-pkg update --all                      # Actualizar todos

# Desinstalar
yeyo-pkg remove nodo-video
yeyo-pkg remove nodo-video --keep-data     # Mantener datos del usuario

# Información
yeyo-pkg info nodo-video                   # Ver metadata completa
yeyo-pkg list                              # Listar nodos instalados
yeyo-pkg list --updates                    # Ver actualizaciones disponibles

# Desarrollo
yeyo-pkg create mi-nodo                    # Scaffold de un nuevo paquete
yeyo-pkg build                             # Construir .ypkg desde el directorio actual
yeyo-pkg test                              # Ejecutar tests del paquete
yeyo-pkg publish                           # Publicar al YEYO Store
```

```bash
# Ejemplo: yeyo-pkg info nodo-video
$ yeyo-pkg info nodo-video

📦 Editor de Video (nodo-video)
   Versión:    1.2.0
   Autor:      YeyoOS Team 🟢
   Categoría:  multimedia
   Tamaño:     245MB (+ 4.7GB modelos IA)
   Instalado:  2024-11-20

   Permisos:
   ├── 📁 Leer: ~/Videos, ~/Descargas
   ├── 📁 Escribir: ~/Videos/exports
   ├── 🎮 GPU: Sí
   ├── 🎤 Micrófono: Sí
   └── 🌐 Red: No

   Modelos IA:
   ├── llava (4.7GB) ✅ instalado
   └── whisper-large (2.9GB) ⬜ opcional, no instalado

   Dependencias:
   ├── nodo-archivos ✅
   ├── ffmpeg 6.1.1 ✅
   └── python3 3.12.0 ✅
```

## Interacción vía IA (Lo que el usuario realmente hace)

Los usuarios **nunca** escriben `yeyo-pkg install`. Hablan con la IA:

```
👤 "Necesito editar un video"

🤖 "Veo que no tienes un editor de video instalado.
    Te recomiendo el nodo 'Editor de Video' (🟢 Official):
    - Edición con timeline
    - Efectos con IA
    - Exportación a múltiples formatos
    Necesita 4GB de VRAM y acceso a ~/Videos.
    ¿Lo instalo?"

👤 "Dale"

🤖 "Instalando... ████████████ 100%
    ¡Listo! El nodo 'Editor de Video' ya apareció en tu Hub.
    ¿Quieres que lo abra?"
```

```
👤 "¿Hay algo para hacer música?"

🤖 "Encontré 3 opciones en el YEYO Store:

    1. 🎵 YEYO Music Studio (🟢 Official)
       DAW completo con IA — 6GB VRAM
    2. 🎹 BeatMaker (🔵 Verified)
       Creación de beats con IA — 2GB VRAM
    3. 🎼 SimpleAudio (🟡 Community)
       Editor de audio básico — 1GB VRAM

    ¿Cuál te interesa?"
```

## Generación Dinámica de Nodos

La IA puede **crear nodos completos** sobre la marcha:

```
👤 "Hazme un nodo para llevar mis finanzas personales"

🤖 "Voy a crear un nodo personalizado de finanzas. Dame un momento..."

    [La IA genera internamente:]
    1. manifest.yml con metadata de finanzas
    2. Container con Python + SQLite
    3. UI con layout tipo dashboard
    4. Prompts de IA especializados en finanzas
    5. Tools: registrar gasto, ver balance, gráfico mensual
    6. Permisos: solo ~/Documentos/Finanzas

🤖 "¡Listo! Creé el nodo '💰 Finanzas Personales':
    - Dashboard con gráficos de gastos/ingresos
    - Puedes decirme 'Gasté $50 en comida' y lo registro
    - Gráficos mensuales automáticos
    - Todo se guarda en ~/Documentos/Finanzas
    Ya apareció en tu Hub. ¿Lo abro?"
```

El paquete generado dinámicamente tiene esta estructura:

```yaml
# manifest.yml generado por la IA
name: "Finanzas Personales"
id: "nodo-finanzas-custom"
version: "1.0.0"
author:
  name: "Generado por IA"
  email: "ai@local"
  key_id: "LOCAL-AI-GENERATED"
icon: "💰"
color: "#4CAF50"
category: "productividad"
description: "Nodo personalizado para gestión de finanzas personales"

requires:
  yeyoos: ">=1.0.0"
  gpu_vram: "0"       # No necesita GPU
  ram: "1GB"
  disk: "100MB"

dependencies:
  nodos: []
  system_packages:
    - "python3>=3.11"
    - "sqlite3"
  ai_models: []        # Usa el modelo general del sistema

permissions:
  filesystem:
    read:
      - "~/Documentos/Finanzas"
    write:
      - "~/Documentos/Finanzas"
  network: false
  gpu: false
  mic: false
  camera: false

ai:
  system_prompt: "prompts/main.txt"
  tools:
    - "tools/registrar_gasto.yml"
    - "tools/registrar_ingreso.yml"
    - "tools/ver_balance.yml"
    - "tools/grafico_mensual.yml"
  max_tokens: 2048

node_ui:
  layout: "dashboard"
  position: "auto"
  size:
    collapsed_radius: 40
    expanded: "fullscreen"
```

```yaml
# ai/tools/registrar_gasto.yml generado por la IA
name: "registrar_gasto"
description: "Registrar un nuevo gasto en la base de datos"
parameters:
  - name: "monto"
    type: "number"
    description: "Monto del gasto"
    required: true
  - name: "categoria"
    type: "string"
    description: "Categoría del gasto"
    enum: ["comida", "transporte", "entretenimiento", "salud", "hogar", "educación", "otro"]
    required: true
  - name: "descripcion"
    type: "string"
    description: "Descripción del gasto"
    required: false
  - name: "fecha"
    type: "string"
    description: "Fecha del gasto (YYYY-MM-DD), default: hoy"
    required: false
```

## Auto-actualizaciones

YeyoOS actualiza los nodos automáticamente de forma segura:

```
┌─────────────────────────────────────────────────┐
│  Ciclo de Auto-actualización (Nocturno)         │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. Cada noche, verificar actualizaciones       │
│     disponibles para todos los nodos instalados │
│                                                 │
│  2. Descargar actualizaciones en segundo plano  │
│                                                 │
│  3. Crear snapshot BTRFS antes de aplicar       │
│                                                 │
│  4. Aplicar actualizaciones                     │
│     - Si requiere nuevos permisos → posponer    │
│       y preguntar al usuario en la mañana       │
│                                                 │
│  5. Verificar que todo funciona                 │
│     - Ejecutar tests del paquete                │
│     - Verificar que el nodo inicia              │
│                                                 │
│  6. Si algo falla → rollback automático         │
│     al snapshot                                 │
│                                                 │
│  7. Reportar al usuario en la mañana:           │
│     "Actualicé 3 nodos anoche. Todo OK."        │
│     o "La actualización de X falló, revertí."   │
│                                                 │
└─────────────────────────────────────────────────┘
```

```yaml
# Ejemplo de reporte de auto-actualización
auto_update_report:
  date: "2024-11-21 03:00"
  updates:
    - package: "nodo-video"
      from: "1.1.0"
      to: "1.2.0"
      status: "success"
      new_permissions: []
      duration: "12s"

    - package: "nodo-imagen"
      from: "2.0.0"
      to: "2.1.0"
      status: "success"
      new_permissions: []
      duration: "8s"

    - package: "nodo-codigo"
      from: "1.5.0"
      to: "1.6.0"
      status: "pending_permission"
      new_permissions:
        - "network: true (para GitHub Copilot)"
      action: "Preguntará al usuario"

  snapshot_id: "pre-update-2024-11-21"
  rollbacks: 0
```

## Desarrollo de Paquetes

### Scaffold de un nuevo nodo

```bash
$ yeyo-pkg create mi-nodo-musica

📦 Creando scaffold para 'mi-nodo-musica'...

mi-nodo-musica/
├── manifest.yml          ✅ Creado (edita con tu info)
├── signature.sig         ⬜ Se genera al publicar
├── checksum.sha256       ⬜ Se genera al build
├── container/
│   ├── Dockerfile        ✅ Template base
│   └── app/
│       └── main.py       ✅ Hello world
├── ui/
│   └── layout.yml        ✅ Layout por defecto
├── api/
│   └── endpoints.yml     ✅ Endpoints de ejemplo
├── ai/
│   ├── models.yml        ✅ Sin modelos (edita)
│   ├── prompts/
│   │   └── main.txt      ✅ Prompt genérico
│   └── tools/
│       └── example.yml   ✅ Tool de ejemplo
├── permissions.yml       ✅ Permisos mínimos
├── hooks/
│   └── post-install.sh   ✅ Hook vacío
└── tests/
    └── test_basic.sh     ✅ Test básico

✅ Scaffold creado. Edita manifest.yml y empieza a desarrollar.
   Usa 'yeyo-pkg build' para construir y 'yeyo-pkg test' para probar.
```

### Build y test

```bash
# Construir el paquete
$ yeyo-pkg build

🔨 Construyendo mi-nodo-musica...
   ├── Validando manifest.yml... ✅
   ├── Construyendo contenedor... ✅ (imagen: 180MB)
   ├── Empaquetando UI... ✅
   ├── Empaquetando IA config... ✅
   ├── Generando checksum... ✅
   └── Creando mi-nodo-musica-1.0.0.ypkg... ✅

📦 mi-nodo-musica-1.0.0.ypkg (195MB)

# Ejecutar tests
$ yeyo-pkg test

🧪 Testeando mi-nodo-musica...
   ├── test_basic.sh... ✅ PASS
   ├── test_install (sandbox)... ✅ PASS
   ├── test_api... ✅ PASS
   └── test_ai... ✅ PASS

✅ 4/4 tests pasaron

# Publicar al Store
$ yeyo-pkg publish

📤 Publicando mi-nodo-musica-1.0.0...
   ├── Firmando con tu clave... ✅
   ├── Subiendo al YEYO Store... ✅
   ├── Pipeline de seguridad... ⏳ (esto puede tardar)
   │   ├── Verificación de firma... ✅
   │   ├── Análisis estático... ✅
   │   ├── Testing en sandbox... ✅
   │   └── Revisión de permisos... ✅
   └── ¡Aprobado! 🎉

🟡 Tu paquete está disponible como 'Community'.
   Para obtener 🔵 Verified, solicita verificación en yeyo.dev/developers.
```
