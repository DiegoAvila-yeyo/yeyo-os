# YeyoOS — Plataforma Local-First de Agentes

> *"Una bola de nieve cayendo por la colina — conforme avanza, se vuelve más grande."*

## ¿Qué es YeyoOS?

YeyoOS es una **plataforma local-first de agentes con memoria, aprendizaje y ejecución real**. Corre sobre Windows, Mac o Linux, y su forma final podrá sentirse como un shell de IA fullscreen, pero la prioridad actual no es "ser un OS", sino construir el núcleo que hace útil a esa experiencia:

- agentes especializados;
- memoria persistente útil;
- investigación y verificación reales;
- calidad automática;
- aprendizaje continuo;
- cómputo distribuido entre máquinas (`YeyoNet`).

## Visión

Crear un sistema que:

- **Aprende** de cada interacción y consolida lo verificado
- **Piensa** antes de responder, buscando y comprobando con herramientas reales
- **Crea** imágenes, videos, código y contenido sin depender de humo ni slop
- **Mejora** progresivamente mediante feedback, benchmarks y entrenamiento
- **Escala** desde una laptop local hasta una red privada de cómputo

## Documentación

| # | Documento | Descripción |
|---|-----------|-------------|
| 01 | [Visión y Concepto](docs/01-vision.md) | La idea central, filosofía y objetivos |
| 02 | [Arquitectura del Sistema](docs/02-arquitectura.md) | Arquitectura unificada: kernel de agentes, memoria, investigador, Dojo, YeyoNet |
| 03 | [Interfaz de Usuario](docs/03-interfaz.md) | Diseño visual: nodos flotantes, layouts de cada módulo |
| 04 | [Nodos y Funcionalidades](docs/04-nodos.md) | Detalle de cada nodo: Imagen, Video, Código, etc. |
| 05 | [Sistema de Memoria](docs/05-memoria.md) | Flash Memory: memoria unificada sin olvido |
| 06 | [Seguridad](docs/06-seguridad.md) | Sandbox, zonas de acceso, botón de pánico |
| 07 | [Anti-Alucinación](docs/07-anti-alucinacion.md) | Sistema multi-agente de verificación |
| 08 | [Escalabilidad](docs/08-escalabilidad.md) | De PC personal a servidores |
| 09 | [Stack Tecnológico](docs/09-stack-tecnologico.md) | Stack actualizado por capas: runtime, memoria, aprendizaje, distribución |
| 10 | [Fases de Desarrollo](docs/10-fases.md) | Roadmap reordenado: agentes primero, OS-like al final |
| 12 | [Sistema de Paquetes](docs/12-yeyo-pkg.md) | YEYO-PKG: formato .ypkg, Store, instalación de nodos |
| 13 | [Code Dojo](docs/13-code-dojo.md) | Agentes de código, RAG, LoRA, entrenamiento automático |
| 14 | [Hardware](docs/14-hardware.md) | Compatibilidad, GPU Scheduler, estrategias de optimización |
| 15 | [YeyoOrquestador](docs/15-yeyo-orquestador.md) | Orquestación nativa, grafos, checkpoints, tools y ejecución |
| 16 | [YeyoNet](docs/16-yeyonet.md) | Red privada de cómputo y sincronización entre máquinas |
| 17 | [Investigador Model](docs/17-modelo-investigador.md) | Pipeline de búsqueda, micro-tareas, razonamiento extendido |
| 18 | [Capas de Datos por Nodo](docs/18-capas-datos-nodos.md) | Cómo aprende cada nodo con datos, feedback y patrones |

> 🔒 **Nota:** La documentación de seguridad se encuentra en un repositorio privado separado (`yeyo-os-security`) con 8 documentos detallados y 31+ capas de protección.

## Hardware Disponible

| Máquina | Rol | Specs |
|---------|-----|-------|
| **PC Windows** (GTX 1060 3GB + 16GB RAM) | Desarrollo principal + destino inicial | Ollama ✅, Docker ✅, GPU ✅ |
| **Mac M1** | Secundaria (código, diseño, backup) | Ollama ✅, Docker ✅ |

### Estrategia de Desarrollo
- **Desarrollo principal:** PC Windows con WSL2 (Ubuntu dentro de Windows)
- **Mac M1:** Edición de código, diseño de interfaz, documentación, backup del repositorio
- **Distribución:** Instaladores multiplataforma (.exe, .dmg, .deb/.rpm) y Docker containers

## Estado del Proyecto

🟡 **En definición activa** — La base del repo ya contiene piezas del kernel (`orquestador`, `memory`, `investigador`, `ia`, `pkg`), y la documentación ahora prioriza la unificación hacia agentes + memoria + calidad + aprendizaje + YeyoNet.
