# 11 — YEYO Compositor

## Resumen

El YEYO Compositor es un compositor Wayland personalizado construido en **Rust** con la biblioteca **smithay** (alternativa a wlroots en Rust, utilizada por COSMIC/System76). Es el corazón visual de YeyoOS — el Hub **ES** el compositor, no es una aplicación corriendo dentro de uno. Esto significa que el Hub siempre responde, incluso si una aplicación cuelga.

## ¿Por qué Wayland sobre X11?

| Aspecto | X11 | Wayland |
|---------|-----|---------|
| **Seguridad** | Cualquier app puede espiar a otra (keyloggers triviales) | Aislamiento total entre aplicaciones |
| **Rendimiento** | Doble buffer obligatorio a través del compositor | Renderizado directo a GPU, sin intermediarios |
| **Tearing** | Requiere hacks (TearFree, vsync forzado) | Sin tearing por diseño |
| **Arquitectura** | Servidor monolítico de los 80s | Protocolo moderno, extensible |

En YeyoOS, cada nodo es una superficie Wayland aislada. X11 permitiría que un nodo malicioso capture las teclas de otro — inaceptable para un OS con IA.

## Nodos como Superficies Wayland

Cada nodo en el Hub es una **superficie Wayland** con regiones marcadas. El compositor conoce la estructura semántica de cada nodo:

```rust
/// Representa un nodo como superficie Wayland con metadata semántica
struct NodeSurface {
    /// Identificador único del nodo
    node_id: NodeId,
    /// Superficie Wayland (wl_surface)
    surface: WlSurface,
    /// Regiones marcadas dentro de la superficie
    regions: Vec<NodeRegion>,
    /// Estado actual (colapsado, expandido, transición)
    state: NodeState,
    /// Socket Wayland aislado del contenedor
    wayland_socket: PathBuf,  // /run/yeyo/wayland-{node_id}
    /// Buffer DMA-BUF para zero-copy cuando está expandido
    dma_buf: Option<DmaBufHandle>,
}

/// Región semántica dentro de un nodo
struct NodeRegion {
    /// Identificador de la región
    id: String,
    /// Rol de la región (chat, workspace, toolbar, minimap)
    role: RegionRole,
    /// Tipo de contenido (text, image, video, canvas, terminal)
    content_type: ContentType,
    /// Límites dentro de la superficie
    bounds: Rect,
    /// Si esta región usa aceleración GPU directa
    gpu_accelerated: bool,
}

#[derive(Debug)]
enum NodeState {
    Collapsed { position: Point, radius: f32 },
    Expanding { progress: f32, from: Circle, to: Rect },
    Expanded { viewport: Rect },
    Collapsing { progress: f32, from: Rect, to: Circle },
}

enum RegionRole {
    Chat,
    Workspace,
    Toolbar,
    Minimap,
    Custom(String),
}

enum ContentType {
    Text,
    Image,
    Video,
    Canvas,
    Terminal,
    WebView,
    Custom(String),
}
```

## Protocolos Wayland Personalizados

YeyoOS extiende Wayland con dos protocolos propios:

### `yeyo-node-v1` — Protocolo de Nodos

Permite que cada nodo se registre con el compositor, declare sus regiones y actualice las descripciones de su contenido.

```xml
<protocol name="yeyo_node_v1">
  <interface name="yeyo_node_manager" version="1">
    <request name="register_node">
      <arg name="node_id" type="string"/>
      <arg name="icon" type="string"/>
      <arg name="color" type="uint"/>
    </request>

    <request name="declare_region">
      <arg name="region_id" type="string"/>
      <arg name="role" type="string"/>
      <arg name="content_type" type="string"/>
      <arg name="x" type="int"/>
      <arg name="y" type="int"/>
      <arg name="width" type="int"/>
      <arg name="height" type="int"/>
      <arg name="gpu_accelerated" type="uint"/>
    </request>

    <request name="update_content_description">
      <arg name="region_id" type="string"/>
      <arg name="description" type="string"/>
    </request>

    <event name="state_changed">
      <arg name="new_state" type="string"/>
    </event>

    <event name="region_visible">
      <arg name="region_id" type="string"/>
      <arg name="visible" type="uint"/>
    </event>
  </interface>
</protocol>
```

### `yeyo-ai-v1` — Protocolo de IA

Permite que el sistema de IA (Ollama) lea el contexto visual de las superficies, manipule nodos y reciba notificaciones de cambios.

```xml
<protocol name="yeyo_ai_v1">
  <interface name="yeyo_ai_controller" version="1">
    <!-- La IA puede leer el contenido visual de una región -->
    <request name="read_visual_context">
      <arg name="node_id" type="string"/>
      <arg name="region_id" type="string"/>
    </request>

    <!-- La IA puede manipular superficies -->
    <request name="manipulate_surface">
      <arg name="node_id" type="string"/>
      <arg name="action" type="string"/>
      <arg name="params_json" type="string"/>
    </request>

    <!-- Notificación cuando algo cambia visualmente -->
    <event name="visual_change">
      <arg name="node_id" type="string"/>
      <arg name="region_id" type="string"/>
      <arg name="change_type" type="string"/>
      <arg name="description" type="string"/>
    </event>

    <!-- Respuesta con contexto visual -->
    <event name="visual_context_response">
      <arg name="node_id" type="string"/>
      <arg name="region_id" type="string"/>
      <arg name="context_json" type="string"/>
    </event>
  </interface>
</protocol>
```

## Scene Graph (Capas de Renderizado)

El compositor organiza el contenido visual en capas ordenadas de atrás hacia adelante:

```
┌─────────────────────────────────────────────────┐
│  5. System         │ Kill switch UI, panic mode  │  ← Siempre encima
├─────────────────────────────────────────────────┤
│  4. Overlays       │ Notificaciones, tooltips    │
├─────────────────────────────────────────────────┤
│  3. Expanded Node  │ Nodo expandido (zero-copy)  │  ← Solo 1 a la vez
├─────────────────────────────────────────────────┤
│  2. Hub            │ Nodos colapsados, líneas    │  ← Vista principal
├─────────────────────────────────────────────────┤
│  1. Background     │ Fondo con blur              │  ← Base
└─────────────────────────────────────────────────┘
```

```rust
/// Capas del scene graph del compositor
struct SceneGraph {
    background: BackgroundLayer,
    hub: HubLayer,
    expanded_node: Option<ExpandedNodeLayer>,
    overlays: OverlayLayer,
    system: SystemLayer,  // Kill switch — SIEMPRE renderiza
}

struct HubLayer {
    /// Nodos colapsados como círculos con glow
    collapsed_nodes: Vec<CollapsedNode>,
    /// Líneas de conexión entre nodos
    connections: Vec<Connection>,
    /// Nodo central YEYO
    central_node: CentralNode,
}
```

## Pipeline de Renderizado

### Damage Tracking

El compositor solo redibuja lo que cambió. En una escena típica con nodos estáticos, esto reduce el trabajo de GPU en **~40x**.

```rust
/// Sistema de damage tracking
struct DamageTracker {
    /// Regiones que cambiaron desde el último frame
    damaged_regions: Vec<Rect>,
    /// Frame anterior para comparación
    previous_frame: Option<FrameBuffer>,
}

impl DamageTracker {
    fn submit_damage(&mut self, region: Rect) {
        self.damaged_regions.push(region);
    }

    fn needs_redraw(&self) -> bool {
        !self.damaged_regions.is_empty()
    }

    fn optimized_redraw_area(&self) -> Option<Rect> {
        if self.damaged_regions.is_empty() {
            return None;
        }
        // Unir todas las regiones dañadas en un rectángulo mínimo
        Some(self.damaged_regions.iter().fold(Rect::ZERO, |acc, r| acc.union(r)))
    }
}
```

### GPU Render Passes

Cada frame se construye en este orden:

```
Pass 1: Background
  └─ Renderizar fondo estático (solo si cambió)

Pass 2: Blur
  └─ Gaussian blur sobre el background (shader blur)

Pass 3: Collapsed Nodes
  └─ Dibujar círculos de nodos colapsados
  └─ Aplicar shader node_glow (efecto pulsante)

Pass 4: Connection Lines
  └─ Dibujar líneas entre nodos (shader connection_lines)
  └─ Partículas de flujo de energía

Pass 5: Expanded Node (si hay uno activo)
  └─ Zero-copy DMA-BUF — la superficie del nodo va directo al framebuffer
  └─ Sin copia de memoria, rendimiento máximo

Pass 6: Overlays
  └─ Notificaciones, tooltips, menús contextuales

Pass 7: Accessibility Post-processing
  └─ Corrección de daltonismo (shader accessibility)
  └─ Ajustes de contraste

Pass 8: Cursor
  └─ Hardware cursor — sin costo de GPU
```

### Backend Gráfico

| Prioridad | API | Uso |
|-----------|-----|-----|
| Primario | **Vulkan** | GPUs modernas, rendimiento óptimo |
| Fallback | **GLES2** | GPUs antiguas, compatibilidad máxima |

```rust
/// Selección de backend gráfico
enum GraphicsBackend {
    Vulkan(VulkanRenderer),
    Gles2(Gles2Renderer),
}

impl GraphicsBackend {
    fn auto_detect() -> Self {
        match VulkanRenderer::new() {
            Ok(renderer) => {
                log::info!("Usando backend Vulkan");
                GraphicsBackend::Vulkan(renderer)
            }
            Err(_) => {
                log::warn!("Vulkan no disponible, usando GLES2 como fallback");
                GraphicsBackend::Gles2(Gles2Renderer::new().expect("GLES2 requerido"))
            }
        }
    }
}
```

## Shaders (GLSL)

### `node_glow` — Efecto Pulsante de Nodos

Círculos que pulsan suavemente indicando el estado del nodo.

```glsl
// node_glow.frag — Efecto de glow pulsante para nodos colapsados
#version 300 es
precision mediump float;

uniform vec3 u_node_color;
uniform float u_time;
uniform float u_activity;  // 0.0 = inactivo, 1.0 = procesando
uniform vec2 u_center;
uniform float u_radius;

out vec4 frag_color;

void main() {
    float dist = distance(gl_FragCoord.xy, u_center);
    float normalized = dist / u_radius;

    // Pulso suave basado en tiempo y actividad
    float pulse = 0.5 + 0.5 * sin(u_time * 2.0 + u_activity * 4.0);
    float glow_intensity = smoothstep(1.0, 0.3, normalized) * (0.6 + 0.4 * pulse * u_activity);

    // Glow exterior más difuso
    float outer_glow = smoothstep(2.0, 1.0, normalized) * 0.15 * u_activity;

    vec3 color = u_node_color * (glow_intensity + outer_glow);
    float alpha = glow_intensity + outer_glow;

    frag_color = vec4(color, alpha);
}
```

### `blur` — Gaussian Blur para Background

```glsl
// blur.frag — Gaussian blur de dos pasadas para el fondo
#version 300 es
precision mediump float;

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform bool u_horizontal;  // true = pasada horizontal, false = vertical
uniform float u_blur_radius;

out vec4 frag_color;

const float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

void main() {
    vec2 tex_offset = 1.0 / u_resolution * u_blur_radius;
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 result = texture(u_texture, uv).rgb * weights[0];

    vec2 direction = u_horizontal ? vec2(tex_offset.x, 0.0) : vec2(0.0, tex_offset.y);

    for (int i = 1; i < 5; i++) {
        result += texture(u_texture, uv + direction * float(i)).rgb * weights[i];
        result += texture(u_texture, uv - direction * float(i)).rgb * weights[i];
    }

    frag_color = vec4(result, 1.0);
}
```

### `transition` — Morfismo Círculo a Rectángulo

Animación cuando un nodo se expande (círculo colapsado → rectángulo expandido).

```glsl
// transition.frag — Morph de círculo a rectángulo
#version 300 es
precision mediump float;

uniform float u_progress;   // 0.0 = círculo, 1.0 = rectángulo
uniform vec2 u_circle_center;
uniform float u_circle_radius;
uniform vec4 u_rect_bounds;  // x, y, width, height
uniform vec3 u_node_color;

out vec4 frag_color;

float rounded_rect_sdf(vec2 p, vec2 center, vec2 half_size, float radius) {
    vec2 d = abs(p - center) - half_size + radius;
    return length(max(d, 0.0)) - radius;
}

void main() {
    vec2 pos = gl_FragCoord.xy;

    // Interpolar entre círculo y rectángulo
    float circle_dist = distance(pos, u_circle_center) - u_circle_radius;

    vec2 rect_center = u_rect_bounds.xy + u_rect_bounds.zw * 0.5;
    vec2 rect_half = u_rect_bounds.zw * 0.5;
    float corner_radius = mix(u_circle_radius, 12.0, u_progress);
    float rect_dist = rounded_rect_sdf(pos, rect_center, rect_half, corner_radius);

    float dist = mix(circle_dist, rect_dist, u_progress);

    float alpha = 1.0 - smoothstep(-1.0, 1.0, dist);
    frag_color = vec4(u_node_color, alpha);
}
```

### `connection_lines` — Líneas con Flujo de Energía

```glsl
// connection_lines.frag — Líneas de conexión con partículas de energía
#version 300 es
precision mediump float;

uniform vec2 u_start;
uniform vec2 u_end;
uniform float u_time;
uniform vec3 u_color;
uniform float u_line_width;

out vec4 frag_color;

float line_sdf(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    vec2 pos = gl_FragCoord.xy;
    float dist = line_sdf(pos, u_start, u_end);

    // Línea base
    float line_alpha = smoothstep(u_line_width, u_line_width - 1.5, dist);

    // Partículas de energía viajando por la línea
    vec2 dir = normalize(u_end - u_start);
    float line_length = distance(u_start, u_end);
    float proj = dot(pos - u_start, dir);
    float t = proj / line_length;

    // Múltiples partículas con diferentes velocidades
    float particle1 = smoothstep(0.02, 0.0, abs(fract(t - u_time * 0.3) - 0.5) - 0.02);
    float particle2 = smoothstep(0.02, 0.0, abs(fract(t - u_time * 0.3 + 0.33) - 0.5) - 0.02);
    float particle3 = smoothstep(0.02, 0.0, abs(fract(t - u_time * 0.3 + 0.66) - 0.5) - 0.02);
    float particles = (particle1 + particle2 + particle3) * smoothstep(u_line_width + 2.0, u_line_width - 1.0, dist);

    vec3 color = u_color * (line_alpha * 0.4 + particles);
    float alpha = line_alpha * 0.4 + particles;

    frag_color = vec4(color, alpha);
}
```

### `accessibility` — Corrección de Daltonismo

```glsl
// accessibility.frag — Post-procesado de accesibilidad
#version 300 es
precision mediump float;

uniform sampler2D u_screen;
uniform vec2 u_resolution;
uniform int u_mode;  // 0 = normal, 1 = protanopia, 2 = deuteranopia, 3 = tritanopia

out vec4 frag_color;

// Matrices de corrección de daltonismo (simulación + corrección)
mat3 protanopia_correction = mat3(
    0.567, 0.433, 0.0,
    0.558, 0.442, 0.0,
    0.0,   0.242, 0.758
);

mat3 deuteranopia_correction = mat3(
    0.625, 0.375, 0.0,
    0.7,   0.3,   0.0,
    0.0,   0.3,   0.7
);

mat3 tritanopia_correction = mat3(
    0.95, 0.05, 0.0,
    0.0,  0.433, 0.567,
    0.0,  0.475, 0.525
);

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 color = texture(u_screen, uv).rgb;

    if (u_mode == 1) {
        color = protanopia_correction * color;
    } else if (u_mode == 2) {
        color = deuteranopia_correction * color;
    } else if (u_mode == 3) {
        color = tritanopia_correction * color;
    }

    frag_color = vec4(color, 1.0);
}
```

## Manejo de Input

### Hit Testing por Región

El compositor sabe exactamente qué región de qué nodo está bajo el cursor, gracias a las regiones marcadas:

```rust
/// Hit testing preciso basado en regiones semánticas
fn hit_test(&self, point: Point) -> Option<HitResult> {
    // Orden inverso: capas superiores primero
    if let Some(hit) = self.system_layer.hit_test(point) {
        return Some(hit);  // Kill switch siempre tiene prioridad
    }

    if let Some(hit) = self.overlay_layer.hit_test(point) {
        return Some(hit);
    }

    if let Some(expanded) = &self.expanded_node {
        // Buscar en las regiones del nodo expandido
        for region in &expanded.surface.regions {
            if region.bounds.contains(point) {
                return Some(HitResult {
                    node_id: expanded.surface.node_id,
                    region_id: region.id.clone(),
                    role: region.role.clone(),
                    local_point: point - region.bounds.origin(),
                });
            }
        }
    }

    // Hub: verificar nodos colapsados
    for node in &self.hub.collapsed_nodes {
        if node.circle_contains(point) {
            return Some(HitResult {
                node_id: node.node_id,
                region_id: "collapsed".into(),
                role: RegionRole::Custom("collapsed_node".into()),
                local_point: point - node.center,
            });
        }
    }

    None
}
```

### Gestos

| Gesto | Acción |
|-------|--------|
| **3 dedos arriba** | Volver al Hub (desde cualquier nodo expandido) |
| **Pinch zoom** | Zoom in/out en el Hub |
| **Doble tap en nodo** | Expandir nodo |
| **Drag en Hub** | Mover nodos colapsados |
| **Ctrl+Alt+K** | Kill switch — a nivel de compositor, **NUNCA** pasa a la IA |

```rust
/// Manejo de gestos a nivel de compositor
fn handle_gesture(&mut self, gesture: Gesture) {
    match gesture {
        Gesture::ThreeFingerSwipeUp => {
            if let Some(expanded) = &self.expanded_node {
                self.collapse_node(expanded.surface.node_id);
            }
        }
        Gesture::PinchZoom { scale } => {
            self.hub.set_zoom(self.hub.zoom * scale);
        }
        Gesture::DoubleTap { position } => {
            if let Some(hit) = self.hit_test(position) {
                self.expand_node(hit.node_id);
            }
        }
        _ => {}
    }
}
```

### Kill Switch: `Ctrl+Alt+K`

Este atajo se intercepta en el **nivel más bajo del compositor**, antes de que cualquier evento de teclado llegue a las superficies de los nodos o al sistema de IA:

```rust
/// Interceptar kill switch ANTES de cualquier procesamiento
fn handle_keyboard_input(&mut self, key_event: KeyEvent) {
    // PRIMERO: verificar kill switch — esto NUNCA se pasa a ningún cliente
    if key_event.modifiers.ctrl
        && key_event.modifiers.alt
        && key_event.key == Key::K
    {
        self.activate_kill_switch();
        return;  // No propagar NADA
    }

    // Solo después de verificar kill switch, enviar a la superficie activa
    if let Some(focused) = &self.focused_surface {
        focused.send_key_event(key_event);
    }
}

fn activate_kill_switch(&mut self) {
    log::error!("🚨 KILL SWITCH ACTIVADO");
    // 1. Matar todos los procesos de IA
    self.kill_all_ai_processes();
    // 2. Congelar filesystem
    self.freeze_filesystem();
    // 3. Mostrar UI de recuperación (en la capa System, siempre visible)
    self.system_layer.show_recovery_ui();
}
```

## Expansión de Nodos

Cuando el usuario expande un nodo, el compositor ejecuta una transición animada y reconfigura el render pipeline:

```rust
/// Expandir un nodo: transición de círculo a pantalla completa
fn expand_node(&mut self, node_id: NodeId) {
    let node = self.hub.get_node(node_id);

    // Capturar estado inicial (posición del círculo en el Hub)
    let circle = Circle {
        center: node.position,
        radius: node.collapsed_radius,
    };

    // Estado final (viewport completo o área expandida)
    let target_rect = self.calculate_expanded_viewport(node_id);

    // Iniciar animación de transición (usa shader transition)
    node.surface.state = NodeState::Expanding {
        progress: 0.0,
        from: circle,
        to: target_rect,
    };

    // Activar el DMA-BUF para zero-copy rendering
    if let Some(dma_buf) = &node.surface.dma_buf {
        self.renderer.enable_direct_scanout(dma_buf);
    }

    // Notificar al nodo que ahora está expandido (para que redimensione su contenido)
    node.surface.send_configure(target_rect.width, target_rect.height);

    // Mover a la capa de nodo expandido
    self.expanded_node = Some(ExpandedNodeLayer {
        surface: node.surface.clone(),
        viewport: target_rect,
    });
}
```

## Loop de Renderizado Principal

```rust
/// Loop principal del compositor
fn render_loop(&mut self) {
    loop {
        // 1. Procesar eventos de input
        self.process_input_events();

        // 2. Procesar eventos Wayland de los clientes
        self.process_wayland_events();

        // 3. Actualizar animaciones
        self.update_animations();

        // 4. Verificar si hay daño que redibujar
        if !self.damage_tracker.needs_redraw() {
            // Nada cambió — dormir hasta el próximo evento
            self.wait_for_event();
            continue;
        }

        // 5. Render passes
        let damage_area = self.damage_tracker.optimized_redraw_area().unwrap();

        self.renderer.begin_frame();

        // Pass 1: Background (solo si está dañado)
        if self.background.intersects_damage(&damage_area) {
            self.renderer.render_background(&self.background);
        }

        // Pass 2: Blur
        self.renderer.apply_blur(&self.blur_shader);

        // Pass 3: Collapsed nodes con glow
        for node in &self.hub.collapsed_nodes {
            if node.intersects_damage(&damage_area) {
                self.renderer.render_collapsed_node(node, &self.glow_shader);
            }
        }

        // Pass 4: Connection lines
        for connection in &self.hub.connections {
            if connection.intersects_damage(&damage_area) {
                self.renderer.render_connection(connection, &self.connection_shader);
            }
        }

        // Pass 5: Expanded node (zero-copy DMA-BUF)
        if let Some(expanded) = &self.expanded_node {
            self.renderer.render_expanded_node(expanded);
        }

        // Pass 6: Overlays
        self.renderer.render_overlays(&self.overlays);

        // Pass 7: Accessibility post-processing
        if self.accessibility.enabled {
            self.renderer.apply_accessibility(&self.accessibility_shader);
        }

        // Pass 8: Cursor (hardware — sin costo GPU)
        self.renderer.set_hardware_cursor(&self.cursor);

        self.renderer.end_frame();
        self.damage_tracker.clear();
    }
}
```

## Integración con el Ecosistema YeyoOS

### Ollama (IA — Contexto Visual)

A través del protocolo `yeyo-ai-v1`, la IA puede:
- Leer qué hay en pantalla (regiones, contenido, estado)
- Manipular superficies (abrir nodos, reposicionar, expandir)
- Recibir notificaciones de cambios visuales

### Sistema de Memoria

El compositor reporta eventos al sistema de memoria:
- Qué nodos se usaron y cuándo
- Transiciones entre nodos
- Tiempo de uso por nodo

### YEYO Guardian (Seguridad)

Guardian monitorea el compositor para detectar:
- Intentos de captura de pantalla no autorizados
- Procesos que intenten acceder a sockets Wayland ajenos
- Anomalías en el uso de GPU

### YEYO-PKG (Nuevo Nodo → Nueva Superficie)

Cuando se instala un paquete nuevo:
1. YEYO-PKG crea el contenedor
2. El contenedor recibe su propio socket Wayland: `/run/yeyo/wayland-{node_id}`
3. El compositor registra la nueva superficie
4. El nodo aparece en el Hub con animación de entrada

### Contenedores (Aislamiento)

Cada nodo corre en su propio contenedor con un socket Wayland aislado:

```
/run/yeyo/wayland-imagen     ← Solo el nodo Imagen puede conectar aquí
/run/yeyo/wayland-video      ← Solo el nodo Video puede conectar aquí
/run/yeyo/wayland-codigo     ← Solo el nodo Código puede conectar aquí
/run/yeyo/wayland-yeyo       ← Nodo central YEYO
```

Los nodos **no pueden ver las superficies de otros nodos**. El compositor es el único que tiene visibilidad total.

## Presupuesto de Memoria GPU

El compositor tiene un presupuesto fijo de **~155MB** de VRAM. El resto se reserva para la IA (Ollama, modelos, inferencia):

```
┌───────────────────────────────────────────┐
│         GPU VRAM (ejemplo: 8GB)           │
├───────────────────────────────────────────┤
│  Compositor: ~155MB                       │
│  ├── Framebuffers: ~50MB                  │
│  ├── Shaders compilados: ~5MB             │
│  ├── Texturas de nodos: ~60MB             │
│  ├── Blur buffers: ~25MB                  │
│  └── Reserva transiciones: ~15MB          │
├───────────────────────────────────────────┤
│  IA (Ollama + modelos): ~7.8GB            │
│  └── SIEMPRE tiene prioridad              │
└───────────────────────────────────────────┘
```

### Auto-degradación de Efectos

Cuando la GPU está bajo presión (por inferencia de IA), el compositor degrada efectos automáticamente:

```rust
/// Sistema de degradación automática de efectos visuales
fn check_gpu_budget(&mut self) {
    let available_vram = self.gpu.available_vram_mb();

    if available_vram < 100 {
        // Nivel crítico: desactivar blur y glow
        self.blur_enabled = false;
        self.glow_enabled = false;
        self.particle_count = 0;
        log::warn!("GPU crítica: efectos visuales desactivados");
    } else if available_vram < 200 {
        // Nivel bajo: reducir calidad
        self.blur_quality = BlurQuality::Low;
        self.glow_enabled = true;
        self.particle_count = self.max_particles / 4;
        log::info!("GPU baja: efectos reducidos");
    } else {
        // Normal: todos los efectos
        self.blur_quality = BlurQuality::High;
        self.glow_enabled = true;
        self.particle_count = self.max_particles;
    }
}
```

**La IA siempre tiene prioridad sobre los efectos visuales.** El compositor sacrifica su propia calidad visual antes de quitarle VRAM a la inferencia.

## El Hub ES el Compositor

A diferencia de un escritorio tradicional donde el compositor y el shell son cosas separadas, en YeyoOS **el Hub es el compositor**. No hay una aplicación "Hub" corriendo como cliente — la vista de nodos, las líneas de conexión, las animaciones de transición, todo es renderizado directamente por el compositor.

Esto garantiza:
- **Siempre responde**: si una app (nodo) cuelga, el Hub sigue funcionando porque es el compositor
- **Sin latencia**: no hay IPC entre Hub y compositor, es el mismo proceso
- **Kill switch confiable**: Ctrl+Alt+K funciona siempre porque está en el compositor, no en una app
- **Rendimiento óptimo**: las animaciones del Hub no compiten con las apps por recursos del compositor
