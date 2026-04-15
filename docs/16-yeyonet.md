# 16 — YeyoNet: Cerebro Distribuido

## Concepto

YeyoNet convierte múltiples instalaciones de YeyoOS en una **red privada inteligente** controlada por el dueño del Cerebro Central. El Central es el maestro: decide quién se conecta, qué datos se comparten, y coordina el aprendizaje distribuido. Los satélites son clientes: funcionan de forma autónoma y sincronizan con el Central cuando está disponible.

El resultado: tu IA personal aprende de todo lo que haces en todos tus dispositivos, y los dispositivos con menos potencia delegan las tareas pesadas al que tiene más GPU.

## Los 3 Modos de Satélite

### Tabla Comparativa

| | **Modo 1 — Completo** | **Modo 2 — Ligero** | **Modo 3 — Mínimo** |
|:---|:---:|:---:|:---:|
| **CPU** | i5+ | i3+ | Cualquiera |
| **RAM** | 16 GB | 8 GB | 4 GB |
| **GPU** | GTX 1060+ | Sin GPU | Sin GPU |
| **Modelos locales** | Todos | qwen2.5:0.5b | Ninguno |
| **Imágenes/Video** | Local | Delega al Central | Delega al Central |
| **Sin Central** | Totalmente independiente | Funciona (sin tareas pesadas) | Modo muy limitado |
| **Caso de uso** | PC principal de trabajo | Laptop de viaje | PC vieja / emergencia |

### Modo 1 — Completo
Todo corre localmente. Usa los mismos modelos y capacidades que el Central. Si el Central se apaga, el satélite sigue funcionando al 100% con su propia Flash Memory y modelos.

### Modo 2 — Ligero
Modelos pequeños corren local (qwen2.5:0.5b para chat rápido). Tareas que requieren GPU — generación de imágenes, procesamiento de video, modelos grandes — se delegan al Central via WebSocket. El Central procesa y regresa el resultado. Latencia adicional de red pero sin necesidad de hardware potente.

### Modo 3 — Mínimo
Solo UI + chat. Toda la inferencia va al Central. Si el Central está offline, el satélite entra en modo degradado: puede leer Flash Memory local pero no genera nuevo contenido con IA. Útil para PCs muy viejas o como terminal ligero.

## Flujo de Conexión (3 Pasos)

```
┌─────────────────────────────────────────────────────────────┐
│  PASO 1: Central genera invitación                          │
│                                                             │
│  El dueño del Central configura:                            │
│  • Nombre del satélite (ej: "Laptop Viaje")                 │
│  • Permisos: chat / grafos / memoria / control              │
│  • Expiración: 7 días (default), 1 día, 30 días             │
│  • Un solo uso                                              │
│                                                             │
│  Sistema genera → código YEYO-XXXX-XXXX-XXXX + QR          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 2: Satélite se conecta                                │
│                                                             │
│  El usuario del satélite:                                   │
│  • Instala YeyoOS                                           │
│  • Entra el código YEYO-XXXX o escanea el QR                │
│  • Descarga modelos y config base del Central               │
│  • El código queda marcado como usado (no reutilizable)     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  PASO 3: Sincronización automática                          │
│                                                             │
│  Ambos nodos quedan vinculados.                             │
│  Sync automático cuando Central está online.                │
│  Cambios en offline → se guardan en cola → se aplican       │
│  al reconectar.                                             │
└─────────────────────────────────────────────────────────────┘
```

## Niveles de Visibilidad y Privacidad

El Central puede solicitar diferentes niveles de acceso a cada satélite. El usuario del satélite acepta (o no) al momento de conectar.

| Nivel | Nombre | Qué ve el Central |
|:---:|:---|:---|
| 1 | **Solo resultados** | Grafos creados, qué aprendió YEYO |
| 2 | **Actividad** | Qué tareas corrió, cuándo, qué generó |
| 3 | **Memoria completa** | Toda la Flash Memory del satélite |
| 4 | **Control total** | Todo lo anterior + ejecutar tareas remotamente |

### Lo que NUNCA se comparte (sin permiso explícito)
- Archivos del sistema operativo host
- Pantalla en tiempo real (screenshare)
- Contraseñas o tokens almacenados fuera de YeyoOS
- Datos de aplicaciones externas a YeyoOS

La privacidad es arquitectural, no solo por política: el relay solo transmite los datos del nivel acordado, no tiene acceso a lo demás.

## Datos Sincronizados

```
Satélite ──── Flash Memory entries ────► Central
             (aprendizaje fluye hacia arriba)

Central  ──── LoRA weights ────────────► Satélites
             (mejoras fluyen hacia abajo)

Ambos    ◄─── Grafos de IA ─────────────► Ambos
             (grafos útiles se comparten)
```

| Dato | Dirección | Descripción |
|:---|:---:|:---|
| Flash Memory entries | Satélite → Central | El Central absorbe el aprendizaje del satélite |
| LoRA weights | Central → Satélite | Satélites reciben fine-tuning mejorado |
| Grafos de IA | Bidireccional | Grafos marcados como útiles se replican |

## Arquitectura Técnica

### Diagrama de Conexión

```
┌──────────────────────────────────────────────────────────────┐
│                    CENTRAL                                   │
│  YeyoOS completo + SatelliteManager + InviteManager         │
│  YeyoNetRelay (WebSocket server)                             │
└────────────────────────┬─────────────────────────────────────┘
                         │  Tailscale (Capa 7)
                         │  WebRTC P2P (futuro)
          ┌──────────────┼──────────────┐
          │              │              │
┌─────────▼──┐  ┌────────▼───┐  ┌──────▼─────┐
│ Satélite 1 │  │ Satélite 2 │  │ Satélite 3 │
│ Modo 1     │  │ Modo 2     │  │ Modo 3     │
│ (Completo) │  │ (Ligero)   │  │ (Mínimo)   │
└────────────┘  └────────────┘  └────────────┘
```

### Relay (Capa 7 actual)
- **Tailscale** como VPN mesh: cada nodo tiene una IP estable en la red privada
- WebSocket persistente sobre Tailscale para mensajes en tiempo real
- Reconexión automática con exponential backoff (1s, 2s, 4s, 8s, máx 60s)
- Heartbeat ping/pong cada 30 segundos para detectar caídas

### Relay (Futuro: P2P WebRTC)
- Sin relay central: conexión directa nodo a nodo
- STUN/TURN para traversal de NAT
- Elimina dependencia de Tailscale
- Requiere señalización inicial (un servidor mínimo de señalización)

### Cifrado
- E2E siempre: todo tráfico va cifrado punto a punto
- En Tailscale: WireGuard (nativo, FIPS-compliant)
- En WebRTC futuro: DTLS-SRTP nativo
- Claves de sesión: generadas por nodo, nunca transmitidas en claro

### Offline-First
```
Satélite offline:
  1. Flash Memory entries se acumulan en SQLite local
  2. LoRA requests se encolan en Redis local
  3. Grafos nuevos se marcan pending_sync

Satélite reconecta:
  1. SyncManager procesa offline queue
  2. Conflictos resueltos por timestamp (más reciente gana)
  3. Central recibe batch de cambios acumulados
  4. Central envía LoRA weights actualizados si hay nuevos
```

## Comandos Cross-Device

YeyoNet habilita comandos que cruzan dispositivos de forma natural:

```bash
# Consultar Flash Memory de otro nodo
"Yeyo, ¿qué hice ayer en mi PC principal?"
→ Consulta Flash Memory del Central (nivel 3+)

# Delegar tarea pesada al nodo con más GPU
"Yeyo, ejecuta el grafo de hacer_reel en mi PC"
→ Serializa el grafo, lo envía al Central, espera resultado

# Transferir archivos generados entre nodos
"Yeyo, pasa el archivo que generaste hoy al satélite"
→ Transferencia directa cifrada vía relay

# Ejecutar tarea remota (nivel 4)
"Yeyo, inicia el pipeline de YouTube en la PC de casa"
→ Central ejecuta grafo en satélite especificado
```

## Panel de Satélites (UI del Central)

El Central tiene un panel dedicado en su Hub con:

```
╔════════════════════════════════════════════════════════╗
║  YeyoNet — Satélites                    [+ Invitar]    ║
╠════════════════════════════════════════════════════════╣
║  🟢 Laptop Viaje       Hace 2 min    chat, grafos [✎] [✕] ║
║  🟡 PC Estudio         Hace 1h       memoria, control [✎] [✕] ║
║  ⭘  PC Mamá           Hace 3 días   chat          [✎] [✕] ║
╚════════════════════════════════════════════════════════╝
```

Estados de satélite:
- 🟢 **online**: Conectado y activo (último ping <5 min)
- 🟡 **idle**: Conectado pero sin actividad reciente (5-60 min)
- ⭘ **offline**: Sin conexión (>60 min sin ping)

## Roadmap

### Capa 7 — Implementación Inicial (Tailscale)

| Micro-fase | Componente | Estado |
|:---|:---|:---:|
| 7.17 | YeyoNet Core (Backend) | ⬜ |
| 7.18 | YeyoNet UI (Frontend) | ⬜ |

Funcionalidades de Capa 7:
- ✅ Generación de códigos de invitación YEYO-XXXX-XXXX-XXXX
- ✅ Flujo de conexión de 3 pasos
- ✅ Relay WebSocket sobre Tailscale
- ✅ Sync de Flash Memory (satélite → Central)
- ✅ Sync de LoRA weights (Central → satélite)
- ✅ Offline queue con procesamiento al reconectar
- ✅ Panel de satélites con estado en tiempo real
- ✅ 4 niveles de visibilidad configurables por satélite
- ✅ Delegación de tareas pesadas (Modo 2 → Central)

### Futuro — P2P Puro

- 🔲 Reemplazar Tailscale con WebRTC P2P directo
- 🔲 Servidor de señalización mínimo (solo para iniciar conexión)
- 🔲 Satélites especializados públicos (GPU compartida de pago)
- 🔲 Red de computación distribuida personal
- 🔲 YeyoOS como red P2P de IA personal (cada usuario = nodo)
- 🔲 Mercado de recursos: ofrecer GPU idle a otros nodos de confianza

## Relación con Otras Capas

- **Requiere**: Flash Memory (Capa 2), LoRA Training (Capa 7 — 7.0-7.2), Guardian (Capa 6)
- **Extiende**: Flash Memory con sync bidireccional y resolución de conflictos
- **Protegido por**: Guardian — todos los datos que entran/salen pasan por el sistema de seguridad
- **Integrado en**: Hub principal via NetworkStatus indicator y panel de satélites

---

## YeyoNet Render Farm Distribuida

### La Visión

Conectar múltiples computadoras normales para que hagan juntas
lo que ninguna podría sola en tiempo razonable.

No se necesitan data centers ni GPUs caras.
Cada PC de la red aporta lo que tiene: CPU, RAM, algo de GPU.
Juntas forman una render farm privada de bajo costo.

```
Ejemplo real:
  Generar 20 variaciones de un thumbnail

  Sin YeyoNet (Mac M solo):
    20 imágenes × 20 min = 400 minutos (6.6 horas) ❌

  Con YeyoNet (Mac + Desktop i5):
    Cada uno genera 10 imágenes en paralelo
    Tiempo total: ~40 minutos ✅

  Con YeyoNet (5 PCs normales):
    Cada uno genera 4 imágenes
    Tiempo total: ~16 minutos ✅

  Con YeyoNet (20 nodos en red de confianza):
    Tiempo total: ~4 minutos 🚀

  Con YeyoNet (100 nodos — red pública futura):
    Tiempo total: ~24 segundos 🚀🚀
```

### Los 4 Tipos de Trabajo Distribuible

#### TIPO 1 — Generación de Imágenes (Stable Diffusion)

```
Modo A — Cola de variantes (recomendado, simple):
  Tú pides 10 variaciones
  YeyoNet asigna: nodo1→img1,2,3 / nodo2→img4,5,6 / nodo3→img7,8,9,10
  Cada nodo genera sus imágenes de forma independiente
  YeyoNet recolecta y presenta todas al usuario
  Ganancia: lineal (N nodos = N veces más imágenes por hora)

Modo B — Pasos alternados (avanzado, experimental):
  Una sola imagen dividida entre 2 nodos
  Nodo A: pasos impares (1,3,5,7,9,11,13,15,17,19)
  Nodo B: pasos pares (2,4,6,8,10,12,14,16,18,20)
  Sincronización entre cada paso via red local
  Ganancia: ~2x en imágenes individuales
  Requiere: latencia de red < 50ms (red local)
  Tecnología: DistriFusion / AsyncDiff (MIT 2024)
```

#### TIPO 2 — Render de Video (FFmpeg, compositing)

```
División por segmentos temporales:
  Video de 3 minutos → dividido en N chunks

  Nodo 1: renderiza segundos 0-10   → chunk_001.mp4
  Nodo 2: renderiza segundos 10-20  → chunk_002.mp4
  Nodo 3: renderiza segundos 20-30  → chunk_003.mp4
  ...
  Nodo 18: renderiza segundos 170-180 → chunk_018.mp4

  YeyoNet ensambla todos los chunks con FFmpeg:
  → resultado_final.mp4

Tiempos reales estimados (video 3 min, efectos medios):
  1 PC (i5-8xxx):      2 horas
  5 nodos normales:    24 minutos
  20 nodos normales:   6 minutos
  100 nodos:           1.2 minutos
```

#### TIPO 3 — Entrenamiento de IA (LoRA, Fine-tuning)

```
Federated Learning — privacidad total:
  Cada nodo entrena con SUS datos locales
  Solo se comparten los gradientes (no los datos)
  Nadie ve los datos de nadie más
  El modelo central mejora con el aprendizaje de todos

  Ejemplo:
  Nodo 1 (tú): entrena con tus videos de cripto
  Nodo 2 (amigo): entrena con sus videos de fitness
  Nodo 3 (familiar): entrena con sus recetas de cocina

  Resultado: modelo que entiende los 3 temas
  sin que nadie vea los datos de los demás
```

#### TIPO 4 — Inferencia de Texto (LLMs, Ollama)

```
Múltiples usuarios concurrentes:
  Cada nodo atiende a un usuario diferente
  Sin degradación de rendimiento por carga

  O modelo dividido entre nodos (model parallelism):
  Nodo 1: capas 1-16 del modelo
  Nodo 2: capas 17-32 del modelo
  Permite correr modelos más grandes que la VRAM individual
```

### Niveles de la Red

```
NIVEL 1 — Red Privada Personal (disponible hoy)
  Solo tus dispositivos
  Total control, cero privacidad comprometida
  Caso de uso: Mac + Desktop + laptop

NIVEL 2 — Red de Confianza (Capa 7)
  Solo personas que tú invitas (familia, equipo)
  Código de invitación YEYO-XXXX-XXXX-XXXX
  Cada nodo acepta qué tipos de trabajo procesa
  Remuneración: créditos internos

NIVEL 3 — Red Pública Opt-in (futuro)
  Cualquier usuario de YeyoOS
  Opt-in explícito: tú decides si participas
  Los datos se fragmentan y encriptan
  Ningún nodo ve el trabajo completo
  Sistema de créditos: ofreces cómputo, recibes cómputo
```

### El Sistema de Créditos

```
Economía interna de YeyoNet:

GANAR créditos:
  → Tu PC procesa trabajos de la red cuando está idle
  → Mientras duermes, tu CPU trabaja para otros
  → 1 hora de CPU i5 = ~10 créditos
  → 1 hora de GPU GTX 1060 = ~50 créditos

GASTAR créditos:
  → Pides un render pesado a la red
  → La red lo procesa en minutos
  → Generar 100 imágenes = 20 créditos
  → Render video 4K 5 min = 30 créditos

Balance:
  Si tu PC trabaja 8h mientras duermes (i5):
  → Ganas ~80 créditos
  → Puedes generar ~400 imágenes al día sin costo
```

### Especificaciones del Worker

Cualquier PC puede ser nodo worker con:

| Hardware | Tipo de trabajo | Rendimiento estimado |
|----------|----------------|---------------------|
| CPU i3+ / 8GB RAM | Texto, chunks de video cortos | Básico |
| CPU i5+ / 16GB RAM | Imágenes SD, video, texto | Medio |
| CPU i7+ / 32GB RAM | Imágenes SD xl, video 4K | Bueno |
| GPU GTX 1060 3GB | Imágenes rápidas (20s), video | Muy bueno |
| GPU RTX 3060 12GB | Todo, modelos grandes | Excelente |

**Tu desktop (i5-8xxx, 16GB RAM) como worker:**
```
Generación imágenes SD 512x512:  ~6-8 min/imagen
Generación imágenes LCM 512x512: ~1-2 min/imagen
Render video 1080p (por minuto): ~4-6 min de render
Texto/chat (qwen2.5:3b):         ~15 tokens/seg
```

### Arquitectura del Worker

```
WORKER (desktop u otro nodo):

  yeyo-worker (proceso Python ligero)
  ├── Registro en YeyoNet Central
  ├── Cola de trabajos (Redis local o en memoria)
  ├── Ejecutor de tareas:
  │   ├── image_worker.py    → Stable Diffusion
  │   ├── video_worker.py    → FFmpeg
  │   ├── text_worker.py     → Ollama
  │   └── training_worker.py → LoRA
  ├── Monitor de recursos (CPU, RAM, GPU)
  │   → Solo acepta trabajos si tiene recursos disponibles
  │   → Reporta capacidad al Central cada 30s
  └── Resultado uploader
      → Sube resultado al Central cuando termina

No requiere YeyoOS completo instalado.
Solo Python + las librerías del tipo de trabajo que acepta.
Instalación en un comando:
  pip install yeyo-worker && yeyo-worker --central YEYO-XXXX-XXXX-XXXX
```

### Dashboard de la Red

```
╔══════════════════════════════════════════════════════════════╗
║  YeyoNet — Render Farm                    [+ Añadir nodo]   ║
╠══════════════════════════════════════════════════════════════╣
║  Poder total de la red:                                      ║
║  CPU: 24 cores  │  RAM: 48GB  │  GPU: GTX 1060 3GB          ║
╠══════════════════════════════════════════════════════════════╣
║  NODO              ESTADO    CPU    RAM   TRABAJO ACTUAL     ║
║  ─────────────────────────────────────────────────────────  ║
║  🟢 Mac (tú)       activo    45%    8GB   generando img 3/5  ║
║  🟢 Desktop i5     activo    82%    14GB  generando img 4/5  ║
║  🟡 Laptop viaje   idle      3%     6GB   esperando trabajo  ║
╠══════════════════════════════════════════════════════════════╣
║  COLA DE TRABAJOS                                            ║
║  ─────────────────────────────────────────────────────────  ║
║  ✅ thumbnail_v1.png    Completado   Mac      2m 14s         ║
║  ✅ thumbnail_v2.png    Completado   Desktop  3m 02s         ║
║  ⚙️  thumbnail_v3.png    Generando   Mac      1m 30s...      ║
║  ⚙️  thumbnail_v4.png    Generando   Desktop  0m 45s...      ║
║  ⏳ thumbnail_v5.png    En cola     —         —              ║
╚══════════════════════════════════════════════════════════════╝
```

### Roadmap de Implementación

| Fase | Funcionalidad | Prioridad |
|------|--------------|-----------|
| **Ahora** | Worker básico para desktop (CPU, imágenes, video) | Alta |
| **Capa 7** | YeyoNet Core con cola de trabajos distribuida | Alta |
| **Capa 7** | Dashboard de la red en tiempo real | Media |
| **Capa 7** | Sistema de créditos básico | Media |
| **Futuro** | Pasos alternados (DistriFusion) para imágenes únicas | Baja |
| **Futuro** | Federated Learning entre nodos | Media |
| **Futuro** | Red pública opt-in con créditos | Baja |
| **Futuro** | Instalador de worker en un comando | Alta |

### Lo que se puede hacer HOY (sin implementar Capa 7)

```
Configuración manual para tu Mac + Desktop:

1. En el Desktop instalar:
   pip install diffusers torch accelerate
   pip install fastapi uvicorn

2. Crear un servidor worker mínimo en el Desktop:
   → Expone POST /generate en puerto 8001
   → Recibe prompt, genera imagen, devuelve base64

3. En YeyoOS (Mac), configurar en .env:
   WORKER_NODES=http://192.168.1.X:8001

4. YeyoOS distribuye automáticamente las generaciones
   entre localhost (Mac MPS) y el worker del Desktop (CPU)

Tiempo de implementación: ~2 horas
Mejora inmediata: 2x más imágenes por hora
```

---

*Sección añadida: 2026-03-24 — Render Farm Distribuida*
*Ver también: docs/18-capas-datos-nodos.md (Capa 7 de Automatización)*
