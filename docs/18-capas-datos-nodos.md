# 18 — Arquitectura de Datos por Nodo: Las Capas de Aprendizaje

## Resumen

Cada nodo de YeyoOS tiene su propio sistema de aprendizaje organizado en capas.
No es una IA genérica que busca en internet — es una IA que aprende de datos
curados manualmente por el usuario y mejora con cada interacción.

**Principio fundamental:** La IA no busca en internet. Busca en tu biblioteca.
Es la diferencia entre aprender de cualquier fuente vs aprender de los mejores ejemplos
que tú mismo seleccionaste.

---

## Nodo Video — 6 Capas

### CAPA 1: Referencia de Acciones
**Qué es:** Videos de personas reales haciendo acciones en el mundo real.
**Para qué:** La IA aprende qué ES cada acción visualmente.
**Ejemplos:** personas minando, cocinando, bailando, escribiendo en computadora.
**Cómo se carga:** Tú los subes manualmente.
**Base de datos:**
```sql
video_referencia_acciones
  id, titulo, accion_descripcion, categoria,
  duracion_segundos, archivo_path, fecha_subida
```

### CAPA 2: Estilo Viral
**Qué es:** Videos virales de TikTok y Reels que tú subes para que la IA
aprenda patrones de edición dinámica, ganchos y engagement.
**Para qué:** La IA aprende CÓMO editar para que enganche, no solo QUÉ mostrar.
**La IA extrae automáticamente:**
- Velocidad de cortes (cortes por segundo)
- Tipos de transiciones usadas
- Gancho inicial — las primeras 3 palabras/frases
- Tipo de gancho: pregunta / afirmación / shock / humor
- Cuándo aparece texto en pantalla (segundo exacto)
- Sincronización audio-video (tempo vs frecuencia de cortes)
- Patrones de frases de enganche ("POV:", "Nadie habla de esto", etc.)

**Cómo se carga:** Tú subes los videos manualmente, opcionalmente con likes/vistas.
**Base de datos:**
```sql
video_viral_referencia
  id, titulo, categoria, duracion_segundos,
  likes, vistas, archivo_path, analizado (bool)

video_viral_patrones  -- lo que extrae la IA
  referencia_id, gancho_texto, gancho_tipo,
  cortes_por_segundo, primer_texto_en_segundo,
  transicion_principal, tempo_musica,
  score_engagement (calculado de likes/vistas)

video_viral_frases
  referencia_id, frase, segundo_aparicion,
  tipo (gancho / cta / transicion / cierre)
```

### CAPA 3: Assets
**Qué es:** Los materiales de trabajo para construir videos.
**Incluye:** Clips B-roll, música libre de derechos, efectos de sonido,
           fuentes tipográficas, overlays, transiciones.
**Cómo se carga:** Tú los subes manualmente y los categorizas.
**Base de datos:**
```sql
video_assets
  id, nombre, tipo (clip/musica/efecto/fuente/overlay),
  categoria, duracion, archivo_path, tags, fecha_subida
```

### CAPA 4: Contexto Activo
**Qué es:** El estado de la sesión actual de generación.
**Incluye:** Qué se pidió, estilo elegido, duración objetivo,
           referencias seleccionadas, progreso de generación.
**Almacenamiento:** Redis (tiempo real, no persiste largo plazo).

### CAPA 5: Feedback
**Qué es:** Tu opinión sobre cada video generado.
**Cómo funciona:** Después de ver el video, calificas aspectos específicos.
**Ejemplos:** "muy lento", "perfecto", "cambia la música", "el gancho no engancha".
**Base de datos:**
```sql
video_feedback
  id, generacion_id, rating (1-5), comentario,
  aspecto (edicion/gancho/musica/duracion/calidad_visual),
  fecha
```

### CAPA 6: Aprendizaje
**Qué es:** Patrones que la IA destila sola de las capas 1-5.
**Qué aprende:**
- "Los videos de cripto con cortes rápidos + hook de pregunta tienen más engagement"
- "Tu audiencia responde mejor a vulnerabilidad + aprendizaje + solución práctica"
- "Los martes a las 7pm es tu mejor horario"
**Base de datos:**
```sql
video_patrones_aprendidos
  id, categoria, patron_descripcion, confianza (0.0-1.0),
  basado_en_n_videos, ultima_actualizacion
```

---

## Nodo Imagen — 5 Capas

### CAPA 1: Referencia Visual
Fotos reales de alta calidad organizadas por categoría, estilo y temática.
La IA aprende qué aspecto visual tiene cada concepto.

### CAPA 2: Assets Visuales
Texturas, fondos, paletas de color, elementos gráficos, estilos artísticos.
Los materiales con los que compone las imágenes.

### CAPA 3: Contexto Activo
El prompt actual, resolución, modelo elegido, parámetros de generación.
Redis para acceso instantáneo.

### CAPA 4: Feedback
Rating de cada imagen generada. Aspectos: composición, colores, fidelidad al prompt.

### CAPA 5: Aprendizaje
Patrones de qué prompts dan mejores resultados para tu estilo específico.
"Cuando añades 'dramatic lighting' este usuario siempre acepta la imagen."

**Base de datos:**
```sql
imagen_referencia
  id, titulo, categoria, estilo, archivo_path, tags

imagen_assets
  id, nombre, tipo (textura/fondo/elemento), archivo_path, tags

imagen_generaciones
  id, prompt, prompt_mejorado, estilo, resolucion,
  imagen_path, fecha

imagen_feedback
  id, generacion_id, rating, comentario, aspecto

imagen_patrones
  id, patron, confianza, ejemplos_n
```

---

## Nodo Código — 6 Capas + Code Dojo

El nodo de código es el más complejo porque involucra calidad técnica objetiva
(el código o funciona o no funciona) y el **Code Dojo** — un sistema de
12 agentes especializados que trabajan juntos.

### Los 12 Agentes del Code Dojo
Todos usan el mismo modelo base, cambian solo el system prompt (0ms de overhead):

| Agente | Especialidad | Output |
|--------|-------------|--------|
| Arquitecto | Diseño de sistemas | Plan de arquitectura |
| Backend | Lógica de servidor | Código funcional |
| Frontend | Interfaces de usuario | Componentes UI |
| Mobile | Apps nativas/cross-platform | Código móvil |
| Base Datos | Esquemas y queries | SQL optimizado |
| Seguridad | OWASP, vulnerabilidades | Reporte de seguridad |
| IA/ML | Modelos y pipelines | Código de ML |
| Performance | Optimización | Código optimizado |
| Testing | Tests y cobertura | Suite de tests |
| DevOps | CI/CD, containers | Pipelines |
| Datos | ETL, data engineering | Pipelines de datos |
| Sistemas | Bajo nivel, kernel | Código de sistema |

### Pipeline de Generación
```
Usuario pide código
  → ARQUITECTO planifica
  → BACKEND escribe
  → CRÍTICO puntúa 0-10 (si < 8.0, vuelve a BACKEND)
  → BACKEND corrige
  → TESTER genera y ejecuta tests REALES (pytest/jest)
  → PERFORMANCE analiza complejidad
  → SEGURIDAD revisa OWASP
  → Todos aprueban → usuario recibe código
```

### CAPA 1: Biblioteca de Referencia
**Principio clave:** NO se usa código de GitHub (90% vibe coding, sin tests).
**Fuentes confiables:**
- Documentación oficial de cada lenguaje/framework
- Tu propio código de YeyoOS (ya testeado y revisado)
- Librerías famosas y bien mantenidas (FastAPI, Next.js, SQLAlchemy)
- Código que tú pegas manualmente y consideras de alta calidad

**Curación automática:** Cada archivo subido pasa por el Agente de Curación:
```
¿Tiene tests?           → +2 puntos
¿Tiene type hints?      → +1 punto
¿Maneja errores?        → +2 puntos
¿Nombres descriptivos?  → +1 punto
¿Vulnerabilidades OWASP? → -5 puntos
¿Complejidad excesiva?  → -2 puntos

≥ 8.0 → entra a biblioteca ✅
5-7.9 → entra con advertencia ⚠️
< 5.0 → rechazado con explicación ❌
```

**Base de datos:**
```sql
code_biblioteca
  id, titulo, lenguaje, tipo (funcion/clase/modulo/app),
  categoria (frontend/backend/db/auth/api...),
  codigo_texto, score_calidad (0-10),
  fuente (manual/docs_oficial/yeyo_proyecto),
  aprobado_manualmente (bool)
```

### CAPA 2: Patrones y Reglas
Lo que los agentes extraen de la biblioteca: reglas de buenas prácticas.
No es código completo — son reglas que se consultan antes de escribir.

**Ejemplos:**
- "En Python: siempre usar type hints"
- "En React: componentes < 100 líneas"
- "En SQL: nunca SELECT *, siempre especificar columnas"
- "En APIs: siempre validar input antes de tocar la DB"

```sql
code_patrones
  id, lenguaje, regla, ejemplo_bueno, ejemplo_malo, peso (1-10)
```

### CAPA 3: Estilo Personal
La forma específica en que TÚ escribes código.
Se aprende automáticamente del código de YeyoOS.
Nomenclatura, estructura, convenciones de comentarios.

### CAPA 4: Contexto Activo
El proyecto actual: archivos abiertos, imports, funciones existentes.
Para que el código nuevo encaje con lo que ya tienes.
Redis para acceso instantáneo.

### CAPA 5: Historial de Errores
Cada error que ocurrió, cómo se detectó y cómo se corrigió.
La IA aprende a NO repetir los mismos errores.

```sql
code_errores_aprendidos
  id, patron_que_fallo, error_resultante,
  correccion_aplicada, veces_ocurrido, lenguaje
```

### CAPA 6: Métricas de Calidad
Score acumulado de cada código generado + tu feedback directo.

```sql
code_metricas
  id, generacion_id, score_critico (0-10),
  tests_pasados, tests_total,
  vulnerabilidades_encontradas, tu_feedback, fecha
```

---

## Nodo Automatización — 7 Capas

### CAPA 1: Fuentes y Conectores
APIs configuradas para monitoreo del mundo exterior.
**APIs disponibles (gratuitas):**
- Google Trends → tendencias en tiempo real
- YouTube Data API → videos con más crecimiento hoy
- Reddit API → posts trending por categoría
- CoinGecko → precios y movimientos cripto
- NewsAPI → noticias por tema
- Twitter/X API → hashtags virales

```sql
automatizacion_conectores
  id, nombre, tipo, api_key_ref, estado (activo/inactivo),
  rate_limit, ultima_llamada
```

### CAPA 2: Biblioteca de Tendencias
Historial de qué fue tendencia y cuándo. Evita repetir temas.
Detecta temporalidad: "este tema es recurrente en diciembre".

```sql
automatizacion_tendencias
  id, tema, categoria, fecha_detectada, score_relevancia,
  cubierto_por_mi (bool), fecha_cubierto
```

### CAPA 3: Contexto Activo
Pipelines corriendo en tiempo real. En qué paso va cada uno.
Datos pasados entre nodos. Redis.

### CAPA 4: Resultados de Publicaciones
Métricas de cada contenido publicado.
Tú introduces manualmente: vistas, likes, shares.

```sql
automatizacion_publicaciones
  id, tipo_contenido, plataforma, fecha_publicacion,
  hora_publicacion, dia_semana, estilo_edicion,
  vistas, likes, comentarios, shares, completion_rate
```

### CAPA 5: Patrones Aprendidos
Insights específicos para TU audiencia (no promedios globales).

**Ejemplos:**
- "Martes 7pm + hook de pregunta + cripto = mejor rendimiento"
- "Videos < 45s tienen 2x más completion rate en tu canal"
- "El estilo 'error personal' genera 3x más shares que análisis técnico"

```sql
automatizacion_patrones
  id, plataforma, categoria, patron_descripcion,
  confianza (0.0-1.0), basado_en_n_publicaciones,
  ultima_actualizacion
```

### CAPA 6: Estrategia Evolutiva
La estrategia de contenido que el sistema forma solo.
Se actualiza cada semana con nuevos datos.
"Este mes los videos de análisis funcionan mejor que los tutoriales."

```sql
automatizacion_estrategia
  id, semana, resumen_estrategia, cambios_respecto_semana_anterior,
  metricas_promedio_semana, generado_en
```

### CAPA 7: Turno de Noche (Mantenimiento del Sistema)
Todas las tareas que el sistema hace mientras tú no estás.
**Completamente configurable** — tú decides qué corre, cuándo y con qué intensidad.

**Tareas disponibles:**

#### Code Dojo (ver docs/13-code-dojo.md)
- Practica ~1,800 desafíos de código por noche
- Los que pasan tests → se guardan en la biblioteca
- Los que fallan → se guardan como errores aprendidos

#### YEYO-HACK Red Team
- El Red Team ataca YeyoOS internamente
- El Guardian (Blue Team) lo defiende
- Documenta vulnerabilidades encontradas
- Las parchea automáticamente o notifica

#### Entrenamiento de Patrones
- Procesa videos virales nuevos que subiste
- Actualiza patrones de todos los nodos
- Recalcula scores de engagement

#### Mantenimiento del Sistema
- Backup de la base de datos
- VACUUM y reindexación PostgreSQL
- Limpieza de logs viejos
- Generación del reporte semanal

**Configuración:**
```json
{
  "horario_inicio": "23:00",
  "horario_fin": "06:00",
  "dias_activos": ["lunes", "martes", "miercoles", "jueves", "viernes"],
  "tareas": {
    "code_dojo": {
      "activo": true,
      "intensidad": "media",
      "desafios_por_noche": 500
    },
    "yeyo_hack": {
      "activo": true,
      "modo": "normal"
    },
    "entrenamiento_patrones": {
      "activo": true
    },
    "backup": {
      "activo": true
    },
    "reporte_semanal": {
      "activo": true,
      "dia": "lunes"
    }
  },
  "reglas_emergencia": {
    "pausar_si_cpu_mayor_a": 95,
    "pausar_si_ram_libre_menor_a_gb": 2,
    "pausar_si_usuario_activo": true
  }
}
```

**Base de datos:**
```sql
turno_noche_ejecuciones
  id, fecha, tarea, duracion_minutos,
  resultado (exitoso/fallido/saltado), detalles_json

turno_noche_config
  tarea, activo, configuracion_json, ultima_modificacion
```

---

## Nodo Chat — 7 Capas

El Chat es el componente más ambicioso: un asistente que te conoce
mejor que nadie, es tu socio creativo y en el futuro ejecuta acciones
por ti con un solo mensaje.

### CAPA 1: Memoria de Largo Plazo
**Todo lo que le has dicho, para siempre. Sin olvidar.**
No es una lista plana — es una red de conexiones entre conceptos.

```sql
chat_memoria
  id, contenido, tipo (hecho/decision/preferencia/meta/idea),
  importancia (1-10), contexto_emocional,
  referencias_relacionadas (array de ids),
  fecha, ultima_accesada

chat_metas
  id, descripcion, plazo (corto/mediano/largo),
  progreso (0-100), activa (bool),
  hitos_json, fecha_creacion
```

### CAPA 2: Modelo de Ti
**Quién eres tú, construido con el tiempo.**
Se construye automáticamente observando cómo hablas e interactúas.

```sql
chat_perfil_usuario
  -- Una sola fila que se actualiza continuamente
  vocabulario_frecuente (json array),
  tono_predominante (formal/casual/técnico/creativo),
  temas_interes (json array con nivel 1-10 cada uno),
  horarios_productivos (json),
  estilo_comunicacion, valores_detectados (json),
  ultima_actualizacion

chat_habitos
  id, patron_descripcion, frecuencia,
  contexto, detectado_en, confianza
```

### CAPA 3: Biblioteca Creativa
Ideas, guiones, hooks y estructuras que funcionaron.
El chat los usa como base para generar nuevas ideas.

```sql
chat_ideas
  id, titulo, tipo (idea/guion/hook/estructura),
  contenido_texto, categoria, rendimiento_real,
  generada_en, aprobada_por_usuario (bool)

chat_guiones
  id, titulo, estructura_json, palabras_gancho (array),
  vistas_obtenidas, fecha_uso, calificacion
```

### CAPA 4: Contexto de Conversación
Estado de la conversación actual. Qué nodos están activos.
Qué proyectos están abiertos. Para no repetir información.
Redis.

### CAPA 5: Patrones Psicológicos
**Observaciones objetivas de tus patrones de trabajo.**
No diagnósticos — solo datos para que tomes mejores decisiones.

```sql
chat_patrones_trabajo
  id, patron_descripcion, tipo (bloqueo/pico_energia/tendencia),
  frecuencia, condicion_observada, confianza,
  primera_observacion, ultima_observacion

  -- Ejemplos reales:
  -- "Los viernes 4pm genera las mejores ideas"
  -- "Cuando dice 'no sé por dónde empezar' está bloqueado"
  -- "Su energía baja cuando habla de métricas sin contexto creativo"
```

### CAPA 6: Historial de Acciones
Qué instrucciones le diste y cómo las interpretó.
Aprende qué significan TUS palabras específicamente.

```sql
chat_acciones
  id, instruccion_original, interpretacion, nodos_usados (array),
  resultado, exitoso (bool), tu_feedback,
  -- Ejemplo: "algo dinámico" → "el usuario siempre quiere cortes rápidos"
  aprendizaje_extraido, fecha
```

### CAPA 7: Puente con Otros Nodos
**La capa que convierte palabras en acciones.**
Entiende: "haz X con estilo Y usando Z de la semana pasada"
Traduce instrucciones en lenguaje natural a llamadas específicas
a los otros nodos. Reporta el resultado de vuelta.

```sql
chat_pipelines
  id, instruccion_usuario, nodos_invocados (json),
  parametros_json, estado (pendiente/ejecutando/completo/error),
  resultado_resumen, fecha_inicio, fecha_fin
```

---

## Cómo crecen juntos (Meta-Aprendizaje Cross-Nodo)

Con el tiempo, los nodos aprenden entre sí:

```
"Cuando el usuario pide un video Y una imagen del mismo tema,
 siempre usa el mismo estilo visual en ambos."
→ Coherencia automática entre nodos

"Cuando hay una tendencia de cripto detectada por Automatización,
 el Chat la propone proactivamente antes de que el usuario la pida."
→ Anticipación

"Los guiones generados por Chat que luego Video convierte
 en contenido con > 10k vistas, se guardan como
 referencias de alta calidad en ambos nodos."
→ Feedback circular entre nodos
```

```sql
cross_nodo_aprendizaje
  id, nodos_involucrados (array), patron_descripcion,
  confianza, n_observaciones, ultima_actualizacion
```

---

## Resumen del Mapa Completo

| Nodo | Capas | Característica única |
|------|-------|---------------------|
| Video | 6 | Aprende de edición viral por análisis de TikToks |
| Imagen | 5 | Biblioteca curada de estilo visual |
| Código | 6 + Code Dojo | 12 agentes + tests reales, sin GitHub |
| Automatización | 7 | Turno de noche configurable + APIs de tendencias |
| Chat | 7 | Te conoce completamente + ejecuta acciones por voz |

---

## Estado de Implementación

- [ ] Migraciones SQL para todas las tablas
- [ ] Módulos Python por nodo (`src/data/video/`, `src/data/codigo/`, etc.)
- [ ] APIs de ingesta (subir referencias, assets, feedback)
- [ ] Integración con nodos existentes
- [ ] UI de configuración del Turno de Noche
- [ ] Puente Chat → Nodos (Capa 7 del Chat)
- [ ] Meta-aprendizaje cross-nodo

---

*Documento creado: 2026-03-24*
*Ver también: docs/13-code-dojo.md, docs/04-nodos.md, docs/05-memoria.md*
