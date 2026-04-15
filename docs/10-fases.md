# 10 — Fases de Desarrollo

## Nuevo orden de prioridad

Este roadmap reemplaza la versión anterior centrada en `OpenClaw`, memoria de "5 capas" y una prioridad demasiado temprana sobre ISO/kiosk/empaquetado tipo OS.

La regla nueva es:

> **Primero agentes útiles, memoria útil y calidad real. Después experiencia tipo OS.**

---

## Estado actual resumido

| Área | Estado |
|---|---|
| Interfaces base | Parcial/avanzado |
| `OllamaProvider` | Existe |
| `YeyoOrquestador` | Existe base sólida |
| `Flash Memory` | Existe base, falta consolidación |
| `Investigador` | Existe base, falta cierre de pipeline |
| `Quality` | Existe base, falta volverla obligatoria |
| `YeyoDojo` / `YeyoHack` | Diseño fuerte, implementación pendiente |
| `YeyoNet` | Diseñado, pendiente |
| UI visual completa | Parcial |
| Experiencia tipo OS | Diferida |

---

## Fase 0 — Alineación del repositorio

**Objetivo:** limpiar la visión y hacer consistente el proyecto.

- [x] Unificar arquitectura en torno a `YeyoOrquestador` + `Flash Memory`
- [x] Eliminar la dependencia conceptual de `OpenClaw`
- [x] Reordenar el roadmap hacia agentes primero
- [x] Documentar el procedimiento oficial para adoptar código de repos externos
- [ ] Alinear el resto de los docs secundarios con la nueva arquitectura

**Resultado:** ya no hay dos visiones compitiendo dentro del repo.

---

## Fase 1 — Kernel mínimo estable

**Objetivo:** tener un runtime confiable para agentes locales.

- [x] Interfaces base (`src/core/interfaces.py`)
- [x] Configuración central (`src/core/config.py`)
- [x] `OllamaProvider` inicial
- [x] Base de `YeyoOrquestador`
- [ ] Tests de contratos e integración entre providers
- [ ] Tool calling estable
- [ ] Trazabilidad consistente por ejecución

**Resultado:** el sistema puede recibir una tarea y ejecutarla con rutas claras.

---

## Fase 2 — Flash Memory v1

**Objetivo:** convertir la memoria en una capa realmente útil para continuidad y personalización.

- [x] Base de `Flash Memory`
- [x] Tiers HOT/WARM/COLD
- [x] Búsqueda semántica inicial
- [ ] Ingestión inteligente inspirada en `mem0`
- [ ] Reglas de qué recordar y qué no
- [ ] Asociaciones más fuertes entre recuerdos
- [ ] Retrieval compartido para chat, investigador y nodos
- [ ] Tests de memoria end-to-end

**Resultado:** la IA recuerda lo correcto sin meter basura en contexto.

---

## Fase 3 — Investigador + anti-slop

**Objetivo:** que Yeyo investigue, adapte y verifique antes de responder.

- [x] Base del pipeline de investigación
- [x] Modelo de micro-tareas con DB
- [ ] Búsqueda interna sólida
- [ ] Búsqueda externa sólida
- [ ] Ranking de candidatos
- [ ] Ensamblaje adaptado al repo
- [ ] Verificación obligatoria con ejecución real
- [ ] Almacenamiento solo de soluciones verificadas

**Resultado:** se reduce drásticamente el slop y la alucinación práctica.

---

## Fase 4 — Quality Kernel

**Objetivo:** que ninguna salida importante se considere válida sin pasar quality gates.

- [x] Base de utilidades en `src/quality/`
- [ ] Score de correctitud
- [ ] Score de seguridad
- [ ] Score de compatibilidad con el repo
- [ ] Indicador de confianza visible
- [ ] Benchmarks de regresión
- [ ] Política de rechazo si no hay evidencia suficiente

**Resultado:** el sistema deja de "parecer correcto" y empieza a "ser correcto".

---

## Fase 5 — YeyoDojo

**Objetivo:** equipo de agentes especializados para código, análisis y mejora continua.

- [x] Diseño conceptual del Dojo
- [ ] Arquitecto, Backend, Frontend, Testing, Seguridad, Performance
- [ ] Pipeline de crítica y corrección
- [ ] Evaluación por score
- [ ] Curación de biblioteca de referencia
- [ ] Historial de errores aprendidos
- [ ] Integración con benchmark

**Resultado:** agentes especializados que producen menos basura y más trabajo utilizable.

---

## Fase 6 — YeyoHack

**Objetivo:** auto-mejora y hardening del propio sistema.

- [ ] Red-team / blue-team interno
- [ ] Aprendizaje desde fallos reales
- [ ] Detección de patrones de error
- [ ] Reentrenamiento/adapters con datos curados
- [ ] Integración con `PyTorch` + `Transformers`

**Resultado:** el sistema aprende de sus errores sin contaminarse con outputs malos.

---

## Fase 7 — YeyoNet

**Objetivo:** usar múltiples computadoras como una red privada de cómputo.

- [x] Diseño conceptual documentado
- [ ] Nodo central
- [ ] Nodo satélite
- [ ] Cola de trabajos pesados
- [ ] Delegación de inferencia y generación
- [ ] Sincronización selectiva de memoria
- [ ] Políticas de permisos y confianza entre máquinas

**Resultado:** una máquina ligera puede apoyarse en una máquina potente.

---

## Fase 8 — Runtime de nodos y `.ypkg`

**Objetivo:** empaquetar capacidades como nodos instalables y exportables.

- [x] Base de manifiestos y builder
- [ ] Installer real
- [ ] Validación de permisos
- [ ] Runtime de hooks
- [ ] Exportar grafos como nodos
- [ ] Firma y verificación de paquetes

**Resultado:** las capacidades del sistema se vuelven modulares y reutilizables.

---

## Fase 9 — Nodos funcionales prioritarios

**Objetivo:** construir capacidades reales encima del kernel.

### Prioridad alta

- [ ] Nodo Código
- [ ] Nodo Investigador
- [ ] Nodo Archivos
- [ ] Nodo Automatización

### Prioridad media

- [ ] Nodo Imagen
- [ ] Nodo Video

**Resultado:** el sistema ya hace trabajo real en dominios útiles.

---

## Fase 10 — UI visual completa

**Objetivo:** llevar el runtime útil a una experiencia visual potente.

- [x] Base frontend existente
- [ ] Hub visual consolidado
- [ ] Estados y trazas por nodo
- [ ] Visualización de grafos
- [ ] Indicadores de confianza y verificación
- [ ] Gestión visual de memorias y paquetes

**Resultado:** el usuario entiende qué está pasando y qué está verificado.

---

## Fase 11 — Multimedia y aprendizaje por nodo

**Objetivo:** que Imagen y Video aprendan de referencias, feedback y resultados.

- [x] Modelo conceptual de capas por nodo
- [ ] Carga de referencias
- [ ] Extracción de patrones
- [ ] Feedback estructurado
- [ ] Métricas por nodo
- [ ] Aprendizaje específico por dominio

**Resultado:** cada nodo aprende de su propio dominio, no de prompts genéricos.

---

## Fase 12 — Distribución de producto

**Objetivo:** empaquetar y distribuir la plataforma útil.

- [ ] Instaladores multiplataforma
- [ ] Docker/Podman maduros
- [ ] Setup reproducible
- [ ] Actualización segura

**Resultado:** otras máquinas pueden ejecutar YeyoOS con menos fricción.

---

## Fase 13 — Experiencia tipo OS (última)

**Objetivo:** si sigue teniendo sentido, encapsular todo como experiencia tipo shell/OS.

- [ ] Arranque fullscreen
- [ ] Kiosk/shell mode
- [ ] Empaquetado Linux dedicado
- [ ] ISO instalable
- [ ] Integración host más profunda

**Resultado:** YeyoOS se siente como sistema operativo, pero solo después de demostrar que el núcleo vale la pena.

---

## Regla de avance

No se avanza por estética ni por hype. Se avanza cuando una fase:

1. funciona;
2. se puede medir;
3. mejora la calidad real del sistema.

## Regla de adopción de código externo

Cada fase que reutilice código de otros repos debe seguir este orden:

1. identificar necesidad concreta;
2. elegir repo y módulo exacto;
3. validar licencia;
4. adaptar a interfaces de YeyoOS;
5. integrar en la carpeta destino;
6. verificar con tests y ejecución real.

El procedimiento detallado vive en `docs/02-arquitectura.md`.
