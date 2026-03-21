# 10 — Fases de Desarrollo

## Visión General

El proyecto se divide en fases incrementales. Cada fase produce algo funcional y usable. No se avanza a la siguiente fase hasta que la actual esté estable.

---

## Fase 0: Fundación

**Objetivo:** Tener el proyecto estructurado y el entorno listo para desarrollar.

- [ ] Crear repositorio Git para YeyoOS
- [ ] Crear estructura de carpetas (backend/, frontend/, system/, docs/)
- [ ] Configurar Docker Compose con servicios base (Postgres, Redis, Ollama)
- [ ] Verificar que Ollama corre y responde
- [ ] Verificar que PostgreSQL + pgvector funciona
- [ ] Crear proyecto Next.js base
- [ ] Crear proyecto FastAPI base
- [ ] Configurar CI/CD básico (GitHub Actions: lint + test)

**Resultado:** `docker-compose up` levanta todos los servicios.

---

## Fase 1: Interfaces y Contratos

**Objetivo:** Crear las interfaces genéricas que permiten intercambiar cualquier pieza.

- [ ] Implementar interfaz `IAProvider`
- [ ] Implementar `OllamaProvider` (primera implementación)
- [ ] Implementar interfaz `Orquestador`
- [ ] Implementar `OpenClawOrquestador` (primera implementación)
- [ ] Implementar interfaz `MemoriaProvider`
- [ ] Implementar `PostgresMemoria` (primera implementación)
- [ ] Crear `config.py` central para seleccionar implementaciones
- [ ] Tests unitarios para cada interfaz

**Resultado:** Las piezas intercambiables están listas. Cambiar de Ollama a GPT-5 = cambiar 1 línea.

---

## Fase 2: Sistema de Memoria

**Objetivo:** Implementar las 5 capas de memoria.

- [ ] Capa 1 (Flash): Variables en memoria para conversación actual
- [ ] Capa 2 (Trabajo): Sesiones en Redis con TTL de 48 horas
- [ ] Capa 3 (Episódica): Conversaciones en PostgreSQL con embeddings (pgvector)
- [ ] Capa 4 (Conocimiento): Tabla de hechos en PostgreSQL con actualización automática
- [ ] Capa 5 (Archivos): Storage con metadata y embeddings
- [ ] Flujo de búsqueda: Flash → Trabajo → Episódica → Conocimiento → Archivos
- [ ] Modelo de embeddings configurado (nomic-embed-text en Ollama)
- [ ] Tests de integración para el flujo completo de memoria

**Resultado:** La IA recuerda todo. "¿Qué hicimos ayer?" funciona.

---

## Fase 3: Seguridad

**Objetivo:** Implementar todas las capas de seguridad.

- [ ] Sistema de zonas (verde/amarillo/rojo)
- [ ] Sandbox para ejecución de acciones de IA
- [ ] Usuarios Linux separados (yeyo, ia-worker)
- [ ] Log de auditoría en PostgreSQL (inmutable)
- [ ] Atajo Ctrl+Alt+K (kill switch) — script de sistema
- [ ] Configurar BTRFS y snapshots automáticos (cada 6 horas)
- [ ] Tests de seguridad: verificar que zona roja bloquea siempre

**Resultado:** La IA no puede dañar el sistema. Ctrl+Alt+K la detiene.

---

## Fase 4: Interfaz — Hub de Nodos

**Objetivo:** La pantalla principal con los nodos flotantes.

- [ ] Canvas principal con PixiJS (fondo oscuro, partículas sutiles)
- [ ] Nodo central YEYO (rojo neón, glow)
- [ ] Nodos satélite (estáticos, arrastrables, conectados con líneas)
- [ ] Doble click → navegar a la vista del nodo
- [ ] Creación dinámica de nodos (agregar/quitar desde la interfaz)
- [ ] Persistencia de posiciones (guardar dónde dejaste cada nodo)
- [ ] Responsive (funciona en diferentes resoluciones)

**Resultado:** Al abrir el sistema, ves tu interfaz neural. Puedes navegar a cada nodo.

---

## Fase 5: Componentes Compartidos

**Objetivo:** Crear los componentes reutilizables que usan todos los nodos.

- [ ] `ChatPanel`: Interfaz de chat con historial y adjuntos
- [ ] `MiniChat`: Chat contextual que aparece sobre un elemento
- [ ] `FileDrop`: Zona para arrastrar imágenes/videos de referencia
- [ ] `Pizarron`: Grid de imágenes/archivos con selección
- [ ] `Timeline`: Línea de tiempo para video (clips arrastrables)
- [ ] `Terminal`: Terminal embebida
- [ ] Integración con FastAPI (WebSocket para chat en tiempo real)

**Resultado:** Los bloques LEGO listos para armar cualquier nodo.

---

## Fase 6: Nodo Imagen

**Objetivo:** El primer nodo funcional completo.

- [ ] Layout: Chat (izq) + Pizarrón (der)
- [ ] Generación de imágenes con Stable Diffusion
- [ ] Soporte para imágenes de referencia (image-to-image)
- [ ] Mini-chat por imagen para refinamiento
- [ ] Versionado de imágenes (v1 → v2 → v3)
- [ ] Guardar en Capa 5 (Archivos) con metadata completa
- [ ] LLaVA para entender referencias visuales

**Resultado:** Puedes generar y refinar imágenes conversando con la IA.

---

## Fase 7: Nodo Video

**Objetivo:** Creación y edición de video con IA.

- [ ] Layout: Chat (izq) + Timeline (der)
- [ ] Generación de clips con FFmpeg + moviepy
- [ ] Soporte para video de referencia
- [ ] Mini-chat por clip para refinamiento
- [ ] Subtítulos automáticos (Whisper)
- [ ] Narración por IA (Bark/XTTS)
- [ ] Exportación en múltiples formatos
- [ ] Unión de clips en video final

**Resultado:** Describes un video → la IA lo genera por clips → lo refinas → exportas.

---

## Fase 8: Nodo Automatización

**Objetivo:** Pipeline de contenido para redes sociales.

- [ ] Integrar el código de estaciones existente
- [ ] Visualización de pipeline (estaciones conectadas)
- [ ] Estación Análisis (APIs de YouTube, TikTok, Instagram)
- [ ] Estación Guiones (generación con Ollama)
- [ ] Estación Edición (integración con Nodo Video)
- [ ] Estación Publicación (APIs de subida)
- [ ] Dashboard de analytics
- [ ] Programación de publicaciones

**Resultado:** Pipeline completo: análisis → guión → edición → publicación.

---

## Fase 9: Nodo Código

**Objetivo:** Programación con IA dentro del OS.

- [ ] Terminal embebida (xterm.js)
- [ ] VS Code Server (code-server) integrado
- [ ] Chat con contexto del código actual
- [ ] Soporte para múltiples lenguajes
- [ ] Git integrado
- [ ] Ejecución de código en sandbox
- [ ] Capacidad de mejorar el propio YeyoOS desde dentro

**Resultado:** Vibe coding completo dentro del OS.

---

## Fase 10: Nodos Auxiliares

**Objetivo:** Completar los nodos restantes.

- [ ] Nodo Archivos: Explorador inteligente con búsqueda semántica
- [ ] Nodo Navegador: Chromium embebido
- [ ] Nodo Configuración: Ajustes del sistema, selección de modelos, gestión de usuarios

**Resultado:** Todos los nodos planeados funcionan.

---

## Fase 11: Anti-Alucinación

**Objetivo:** Implementar el sistema completo de verificación.

- [ ] Verificación en cadena (cada respuesta se intenta verificar)
- [ ] Sistema multi-agente (Creador + Crítico + Verificador)
- [ ] Memoria como ancla de coherencia
- [ ] Niveles de confianza visibles (🟢🟡🔴)
- [ ] Feedback loop (corrección de errores → aprendizaje)
- [ ] Ejecución real de código en vez de "imaginar" resultados

**Resultado:** La IA es honesta sobre lo que sabe y no sabe.

---

## Fase 12: Linux y Empaquetado

**Objetivo:** Convertir todo en un sistema operativo real.

- [ ] Elegir base Linux (Alpine o Arch)
- [ ] Configurar arranque directo a interfaz (Kiosk Mode)
- [ ] Instalar drivers NVIDIA automáticamente
- [ ] Scripts de autostart para todos los servicios (Docker)
- [ ] Generar ISO instalable
- [ ] Probar en QEMU / VM
- [ ] Instalar en hardware real (la PC destino)
- [ ] Verificar Ctrl+Alt+K funciona a nivel sistema
- [ ] Verificar snapshots BTRFS funcionan

**Resultado:** USB booteable → Instala → Arranca directo a YeyoOS.

---

## Fase 13: Pulido y Multi-Usuario

**Objetivo:** Preparar para otros usuarios.

- [ ] Sistema de login / cuentas
- [ ] Aislamiento de datos por usuario
- [ ] Onboarding (primera experiencia)
- [ ] Documentación de usuario
- [ ] Instalador amigable
- [ ] Sistema de actualización automática (pull de nuevas versiones)

**Resultado:** Alguien más puede instalar y usar YeyoOS.

---

## Fase 14: Escalamiento a Servidor

**Objetivo:** Migrar de PC personal a infraestructura de servidor.

- [ ] Migrar docker-compose → Kubernetes
- [ ] Configurar load balancer
- [ ] Auto-scaling de workers
- [ ] Multi-GPU support
- [ ] Monitoreo y alertas (Grafana, Prometheus)
- [ ] Backups externos automatizados

**Resultado:** YeyoOS corre en la nube, múltiples usuarios simultáneos.

---

## Fase 15: YEYO-PKG y Store

**Objetivo:** Sistema de paquetes y marketplace de nodos.

- [ ] Definir formato .ypkg
- [ ] Implementar yeyo-pkg CLI (create, build, install, remove)
- [ ] Sistema de firma digital de paquetes
- [ ] Pipeline de seguridad (análisis estático, sandbox testing)
- [ ] YEYO Store (servidor central de paquetes)
- [ ] Niveles de confianza (Oficial, Verificado, Comunidad)
- [ ] Generación dinámica de nodos por IA
- [ ] Auto-actualización de nodos

**Resultado:** Los usuarios pueden instalar, crear y compartir nodos.

---

## Fase 16: Empresa y Corporativo

**Objetivo:** Despliegue multi-máquina para empresas.

- [ ] Arquitectura de islas independientes (cada PC aislada)
- [ ] Guardian distribuido (seguridad centralizada)
- [ ] Actualizaciones firmadas desde servidor central
- [ ] VLANs y segmentación de red
- [ ] Jerarquía departamental de privilegios
- [ ] Auditoría centralizada
- [ ] Compliance y políticas de retención

**Resultado:** Una empresa puede desplegar YeyoOS en todas sus máquinas de forma segura.

---

## Fase 17: Expansión de Hardware

**Objetivo:** Soporte para hardware especializado de IA.

- [ ] Soporte NPU (Intel, AMD, Qualcomm)
- [ ] Integración con Google Coral y Hailo
- [ ] Soporte Tenstorrent / Groq (cuando estén disponibles)
- [ ] Multi-GPU con balanceo automático
- [ ] Hardware Manager con auto-detección
- [ ] GPU Scheduler con prioridades

**Resultado:** YeyoOS aprovecha automáticamente cualquier hardware de IA disponible.

---

## Orden de Prioridad

```
CRÍTICO (sin esto no funciona nada):
  Fase 0 → Fase 1 → Fase 2 → Fase 4 → Fase 5

IMPORTANTE (funcionalidades core):
  Fase 3 → Fase 6 → Fase 8

VALIOSO (experiencia completa):
  Fase 7 → Fase 9 → Fase 10 → Fase 11

FUTURO (escalamiento):
  Fase 12 → Fase 13 → Fase 14

EXPANSIÓN (ecosistema):
  Fase 15 → Fase 16 → Fase 17
```
