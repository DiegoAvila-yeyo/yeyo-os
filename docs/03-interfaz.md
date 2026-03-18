# 03 — Interfaz de Usuario

## Concepto Visual: "Neural Hub"

Al iniciar YeyoOS, el sistema lanza una única aplicación a pantalla completa (Kiosk Mode). No hay escritorio, no hay barra de tareas, no hay iconos. Solo tu interfaz de nodos.

## Pantalla Principal

Un "Círculo Central" (YEYO) rodeado de "Nodos Satélite" flotantes, conectados por líneas.

```
                    ┌─────────┐
           ┌────────│ Imagen  │
           │        │  (IA)   │
           │        └─────────┘
           │
     ┌─────┴─────┐         ┌──────────┐
     │           │─────────│  Video   │
     │   YEYO   │         │ (Editor) │
     │           │─────────│          │
     └─────┬─────┘         └──────────┘
           │
           │        ┌───────────┐
           ├────────│  Código   │
           │        │  (Dev)    │
           │        └───────────┘
           │
           │        ┌───────────┐
           └────────│Automati-  │
                    │ zación    │
                    └───────────┘
```

### Comportamiento de los Nodos
- **Estáticos:** Los nodos NO se mueven solos. Se quedan donde los pongas.
- **Arrastrables:** Puedes mover cualquier nodo a donde quieras (drag & drop).
- **Conectados:** Líneas visibles conectan cada nodo al centro (YEYO).
- **Expandibles:** Puedes crear nuevos nodos dinámicamente.
- **Doble click:** Abre el nodo y entra a su interfaz dedicada.

### Tecnología de Renderizado
- **PixiJS** para el canvas de nodos (ya está en el stack del proyecto de estaciones)
- Renderizado a 60fps, fluido
- Efectos visuales: glow, partículas sutiles en las conexiones

## Patrón Universal: Chat + Área de Trabajo

Todos los nodos siguen el mismo patrón de interfaz:

```
┌──────────────────────────────────────────────┐
│                                              │
│  Chat (izquierda)    │  Área de Trabajo (der)│
│                      │                        │
│  Conversación con    │  Contenido específico  │
│  la IA sobre esta    │  del nodo:             │
│  tarea               │  - Imágenes (pizarrón) │
│                      │  - Videos (timeline)   │
│  📎 Subir referencias│  - Código (editor)     │
│                      │  - Datos (gráficos)    │
│                      │                        │
│                      │  Click en elemento →   │
│                      │  Mini-chat contextual  │
│                      │  para refinarlo        │
└──────────────────────────────────────────────┘
```

### Componentes Reutilizables
Estos componentes se escriben UNA vez y se usan en todos los nodos:

1. **ChatPanel:** Interfaz de chat con soporte para archivos adjuntos (referencias)
2. **MiniChat:** Chat contextual que aparece sobre un elemento específico
3. **FileDrop:** Zona para arrastrar/pegar imágenes y videos de referencia

## Layout por Nodo

### Nodo Imagen: Chat + Pizarrón

```
┌──────────────────────────────────────────────┐
│  Chat                │  Pizarrón              │
│                      │                        │
│  "Hazme un logo      │  [img1] [img2] [img3]  │
│   cyberpunk"         │                        │
│                      │  [img4] [img5]          │
│  📎 [referencia.jpg] │                        │
│  "Usa este estilo"   │  * Click en img2 *     │
│                      │  ┌─────────────┐       │
│  IA: "Aquí tienes    │  │ Mini-chat:  │       │
│  3 opciones..."      │  │ "Hazla más  │       │
│                      │  │  oscura"    │       │
│                      │  │ 📎 [ref2]   │       │
│                      │  └─────────────┘       │
└──────────────────────────────────────────────┘
```

**Flujo:**
1. Escribes prompt en el chat
2. Arrastras imágenes de referencia
3. La IA genera opciones → aparecen en el pizarrón (grid)
4. Click en una imagen → mini-chat para refinarla
5. Las variaciones se agregan al pizarrón

### Nodo Video: Chat + Timeline

```
┌──────────────────────────────────────────────────┐
│  Chat                  │  Timeline                │
│                        │                          │
│  "Un video de un       │  [clip1]→[clip2]→[clip3] │
│  robot caminando       │  ───────────────────────  │
│  por la ciudad"        │  00:00   00:03   00:06   │
│                        │                          │
│  📎 [referencia.mp4]   │  * Click en clip2 *      │
│  "Usa este estilo"     │  ┌──────────────┐        │
│                        │  │ Mini-chat:   │        │
│  IA: "Generando 3      │  │ "Hazlo más   │        │
│  clips de 3 seg..."    │  │  lento"      │        │
│                        │  │ 📎 [ref2.mp4]│        │
│                        │  └──────────────┘        │
└──────────────────────────────────────────────────┘
```

**Flujo:**
1. Describes el video en el chat
2. Arrastras imágenes/videos de referencia para guiar el estilo
3. La IA genera clips → aparecen en la timeline
4. Click en cualquier clip → mini-chat para refinarlo con nuevas referencias
5. "Únelos todos" → video final exportado

### Nodo Automatización: Chat + Pipeline Visual

```
┌─────────────────────────────────────────────────────┐
│  📊 Analytics + Chat   │  🔄 Pipeline Visual         │
│                        │                             │
│  YouTube: 15K ↑12%     │  [Analizar] ──→ [Guión]     │
│  TikTok:  50K ↓3%      │      │              │       │
│  Instagram: 8K ↑25%    │      ▼              ▼       │
│                        │  [Tendencias]  [Edición]    │
│  "TikTok pide más      │                     │       │
│   videos cortos de     │                     ▼       │
│   cocina este mes"     │              [Publicar]     │
│                        │               ↙  ↓  ↘      │
│                        │             YT  TT  IG      │
└─────────────────────────────────────────────────────┘
```

**Flujo:**
1. La IA muestra analytics de todas las redes
2. Detecta tendencias automáticamente
3. Cada estación del pipeline es visible y clickeable
4. Click en una estación → mini-chat para ajustar parámetros
5. El pipeline completo: Análisis → Guión → Edición → Publicación

### Nodo Código: Chat + Editor/Terminal

```
┌──────────────────────────────────────────────────┐
│  Chat                  │  Editor / Terminal        │
│                        │                          │
│  "Crea una API en      │  ┌─── VS Code ────────┐  │
│  Go que maneje         │  │ package main        │  │
│  usuarios"             │  │                     │  │
│                        │  │ func main() {       │  │
│  IA: "Creando la       │  │   r := gin.New()    │  │
│  estructura..."        │  │   ...               │  │
│                        │  └─────────────────────┘  │
│  "Agrégale auth        │                          │
│   con JWT"             │  ┌─── Terminal ────────┐  │
│                        │  │ $ go run main.go    │  │
│                        │  │ Server running :8080│  │
│                        │  └─────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Nodo Archivos: Chat + Explorador Inteligente

```
┌─────────────────────────────────────────────┐
│  Chat                │  Explorador            │
│                      │                        │
│  "Muéstrame los      │  ┌─────┐ ┌─────┐      │
│   logos de marzo"    │  │img1 │ │img2 │      │
│                      │  └─────┘ └─────┘      │
│  IA: "Encontré 12    │  ┌─────┐ ┌─────┐      │
│   archivos..."       │  │vid1 │ │doc1 │      │
│                      │  └─────┘ └─────┘      │
│  "Organízalos        │                        │
│   por proyecto"      │  [Filtros: tipo, fecha,│
│                      │   nodo, tags]          │
└─────────────────────────────────────────────┘
```

### Nodo Navegador: Chrome Embebido

Un navegador web completo embebido dentro del nodo, con la capacidad de instalar apps de internet cuando sea necesario.

## Concepto Fractal: Nodos Dentro de Nodos

La interfaz es **fractal** — el mismo patrón se repite a todos los niveles:

```
NIVEL 1 — Pantalla Principal (OS)
    [Imagen] ── [YEYO] ── [Video]
                  │
          [Automatización] ── [Web]

NIVEL 2 — Dentro de Automatización
    [Análisis] → [Guiones] → [Edición] → [Publicar]
         ↑                                    │
         └────── feedback loop ───────────────┘

NIVEL 3 — Dentro de cada estación
    Chat + Área de trabajo + Mini-chats contextuales
```

## Temas Visuales

- **Fondo oscuro** (#0f0f12) — Reduce fatiga visual
- **Nodo central rojo neón** — Gradient radial, glow
- **Nodos satélite** — Fondo semi-transparente, bordes sutiles
- **Líneas de conexión** — Blancas con baja opacidad
- **Estética general** — Futurista, limpia, neural
