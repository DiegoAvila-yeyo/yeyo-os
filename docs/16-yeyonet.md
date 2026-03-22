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
