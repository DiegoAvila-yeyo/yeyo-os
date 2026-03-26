# Plan para Sistema Operativo AI-Nativo (YeyoOS)

## Objetivo
Crear un sistema operativo donde la interfaz principal y el núcleo de la experiencia sea **OpenClaw + Ollama**.

## Arquitectura (Enfoque Pragmático)
Para ejecutar Ollama (que requiere drivers complejos de GPU, networking, stack de Go/Python), no es viable escribir un kernel desde cero. Usaremos un **Kernel Linux minimalista** como base.

**Estructura del OS:**
1.  **Hardware** (PC Local con GPU)
2.  **Kernel:** Linux (Optimizado, sin bloatware)
3.  **Init System:** Systemd o script simple
4.  **User Space:**
    *   Drivers GPU (Nvidia/AMD)
    *   Ollama Service (Backend IA)
    *   OpenClaw (Interfaz/Frontend)
5.  **UI:** Sin escritorio tradicional (Gnome/KDE). Directo a una terminal o interfaz web (kiosk mode).

## Interfaz de Usuario: "Neural Hub" (Círculos Conectados)
**Concepto:** Al iniciar, el sistema lanza una única aplicación a pantalla completa (Kiosk Mode).
- **Diseño:** Un "Círculo Central" (Núcleo/Ollama/OpenClaw) rodeado de "Nodos Satélite" flotantes.
- **Nodos:** Cada nodo es una app o funcionalidad (Generación Imágenes, Edición Video, Navegador, Automatización).
- **Interacción:**
    - Crear nuevos nodos dinámicamente ("Oye, crea un nodo para resumir noticias").
    - Conectar nodos para crear flujos de trabajo (ej. Nodo Noticias -> Nodo Resumen -> Nodo Email).
- **Tecnología UI:**
    - Opción A: **Web Stack** (Electron/Tauri + React/Three.js) -> *Recomendado por flexibilidad y belleza visual.*
    - Opción B: **Game Engine** (Godot) -> *Mejor rendimiento gráfico 3D, pero más difícil de integrar con apps externas.*

## Fases del Proyecto

- [ ] **Fase 1: Entorno de Desarrollo (Desde tu Mac)**
    *   [ ] Instalar herramientas de virtualización (QEMU/Docker) para probar sin reiniciar.
    *   [ ] Elegir la base: ¿Alpine Linux? ¿ArchISO? ¿Buildroot? -> *Recomendado: ArchISO o Alpine por ligereza.*

- [ ] **Fase 2: Prototipo en Virtual Machine**
    *   [ ] Crear una imagen ISO básica.
    *   [ ] Lograr que arranque y tenga red.
    *   [ ] Instalar Ollama y drivers en la imagen.

- [ ] **Fase 3: La Experiencia "AI First"**
    *   [ ] Configurar OpenClaw para iniciar al arranque (auto-start).
    *   [ ] Eliminar login/prompts innecesarios.

- [ ] **Fase 4: Instalación en Hardware Real**
    *   [ ] Flashear ISO a USB.
    *   [ ] Instalar en la PC destino.
