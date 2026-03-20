# YeyoOS — Sistema Operativo AI-Nativo

> *"Una bola de nieve cayendo por la colina — conforme avanza, se vuelve más grande."*

## ¿Qué es YeyoOS?

YeyoOS es un sistema operativo donde **la inteligencia artificial es el centro de todo**. No es una computadora con IA añadida — es una IA con computadora. Al encender la PC, no ves un escritorio con iconos. Ves un **"cerebro visual"**: nodos flotantes conectados, cada uno representando una capacidad creativa impulsada por IA.

## Visión

Crear lo inimaginable. Un sistema que:
- **Aprende** de cada interacción y nunca olvida
- **Piensa** antes de responder, verificando datos reales
- **Crea** imágenes, videos, código, contenido — sin alucinar
- **Mejora** progresivamente: cada uso lo hace más inteligente
- **Escala** de una PC personal a un datacenter

## Documentación

| # | Documento | Descripción |
|---|-----------|-------------|
| 01 | [Visión y Concepto](docs/01-vision.md) | La idea central, filosofía y objetivos |
| 02 | [Arquitectura del Sistema](docs/02-arquitectura.md) | Estructura técnica, capas e interfaces intercambiables |
| 03 | [Interfaz de Usuario](docs/03-interfaz.md) | Diseño visual: nodos flotantes, layouts de cada módulo |
| 04 | [Nodos y Funcionalidades](docs/04-nodos.md) | Detalle de cada nodo: Imagen, Video, Código, etc. |
| 05 | [Sistema de Memoria](docs/05-memoria.md) | Flash Memory: memoria unificada sin olvido |
| 06 | [Seguridad](docs/06-seguridad.md) | Sandbox, zonas de acceso, botón de pánico |
| 07 | [Anti-Alucinación](docs/07-anti-alucinacion.md) | Sistema multi-agente de verificación |
| 08 | [Escalabilidad](docs/08-escalabilidad.md) | De PC personal a servidores |
| 09 | [Stack Tecnológico](docs/09-stack-tecnologico.md) | Tecnologías, herramientas y dependencias |
| 10 | [Fases de Desarrollo](docs/10-fases.md) | Roadmap completo del proyecto |
| 11 | [Compositor Visual](docs/11-compositor.md) | YEYO Compositor: Wayland, shaders, integración con IA |
| 12 | [Sistema de Paquetes](docs/12-yeyo-pkg.md) | YEYO-PKG: formato .ypkg, Store, instalación de nodos |
| 13 | [Code Dojo](docs/13-code-dojo.md) | Agentes de código, RAG, LoRA, entrenamiento automático |
| 14 | [Hardware](docs/14-hardware.md) | Compatibilidad, GPU Scheduler, estrategias de optimización |

> 🔒 **Nota:** La documentación de seguridad se encuentra en un repositorio privado separado (`yeyo-os-security`) con 8 documentos detallados y 31+ capas de protección.

## Hardware Disponible

| Máquina | Rol | Specs |
|---------|-----|-------|
| **PC Windows** (GTX 1060 3GB + 16GB RAM) | Desarrollo principal + Destino final | Ollama ✅, OpenClaw ✅, Docker ✅, GPU ✅ |
| **Mac M1** | Secundaria (código, diseño, backup) | Ollama ✅, OpenClaw ❌, Docker ✅ |

### Estrategia de Desarrollo
- **Desarrollo principal:** PC Windows con WSL2 (Ubuntu dentro de Windows)
- **Mac M1:** Edición de código, diseño de interfaz, documentación, backup del repositorio
- **Fase 12:** Se formatea la PC Windows y se instala YeyoOS (Linux) directamente

## Estado del Proyecto

🟡 **En planificación** — Definiendo visión, arquitectura y fases.
