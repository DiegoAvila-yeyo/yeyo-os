# 06 — Seguridad

## Principio Fundamental

> **La IA propone, tú dispones.**

La IA nunca tiene acceso directo al sistema. Todas las acciones pasan por una capa de seguridad que valida permisos antes de ejecutar cualquier cosa.

## Capas de Seguridad

### 1. Sandbox (Jaula)

La IA opera dentro de un contenedor aislado. No puede tocar el sistema operativo host directamente.

```
IA dice: "quiero borrar archivo X"
    │
    ▼
[Capa de Permisos] → ¿Tiene permiso? ¿Es peligroso?
    │
    ▼
Si es zona verde → Ejecuta automáticamente
Si es zona amarilla → Te pregunta primero
Si es zona roja → Bloqueado. Punto.
```

### 2. Zonas de Acceso

#### 🟢 Zona Verde (Libre, sin preguntar)
Acciones seguras que no pueden dañar nada:
- Crear/editar archivos dentro de `/storage/`
- Generar imágenes, videos, texto
- Leer datos de APIs (YouTube, TikTok)
- Buscar en internet
- Consultar memoria
- Ejecutar código dentro del sandbox

#### 🟡 Zona Amarilla (Pide tu confirmación)
Acciones con impacto externo o potencialmente riesgosas:
- Publicar en redes sociales
- Enviar correos o mensajes
- Instalar paquetes o dependencias nuevas
- Modificar configuración del OS
- Acceder a archivos fuera de `/storage/`
- Hacer requests HTTP a servicios externos
- Ejecutar scripts que toquen el filesystem

#### 🔴 Zona Roja (Bloqueado siempre, sin excepciones)
Acciones que podrían destruir el sistema:
- Borrar archivos del sistema operativo
- Modificar el kernel o bootloader
- Cambiar contraseñas o permisos de root
- Desactivar su propia capa de seguridad
- Acceder a credenciales encriptadas directamente
- Ejecutar comandos como root/sudo
- Modificar la configuración de Docker/containers
- Matar procesos del sistema
- Formatear discos
- Cambiar configuración de red a nivel sistema

### 3. Usuarios Linux Separados

El sistema usa tres usuarios de Linux con diferentes privilegios:

```
root (superusuario)
├── Solo accesible con contraseña física
├── Para: mantenimiento del sistema
└── La IA NUNCA puede usar este usuario

yeyo (usuario normal)
├── El sistema operativo visual corre aquí
├── Tiene acceso a Docker, servicios
└── Controlado por el usuario humano

ia-worker (usuario restringido)
├── Los procesos de IA corren aquí
├── NO tiene sudo
├── NO puede escribir fuera de /storage/
├── NO puede matar procesos del sistema
├── NO puede cambiar sus propios permisos
├── NO puede acceder a /etc/, /boot/, /sys/
└── Permisos mínimos necesarios para operar
```

### 4. Registro de Auditoría

Cada acción de la IA se registra permanentemente:

```json
{
  "timestamp": "2026-03-18T06:40:00Z",
  "agente": "imagen",
  "accion": "crear_archivo",
  "detalle": "img_0847.png",
  "zona": "verde",
  "resultado": "ejecutado",
  "razon": "usuario pidió generar logo cyberpunk",
  "conversacion_id": 4523
}
```

```json
{
  "timestamp": "2026-03-18T06:45:00Z",
  "agente": "automatizacion",
  "accion": "publicar_video",
  "detalle": "video_123.mp4 → YouTube",
  "zona": "amarilla",
  "resultado": "pendiente_aprobacion",
  "razon": "pipeline de publicación automática"
}
```

```json
{
  "timestamp": "2026-03-18T06:50:00Z",
  "agente": "codigo",
  "accion": "borrar_archivo_sistema",
  "detalle": "/etc/hosts",
  "zona": "roja",
  "resultado": "BLOQUEADO",
  "razon": "intento de modificar archivo del sistema"
}
```

El log de auditoría:
- Se guarda en PostgreSQL (Capa 3 de memoria)
- Es inmutable (no se puede borrar ni modificar)
- Consultable: "¿Qué hizo la IA en las últimas 24 horas?"
- Alertas automáticas si hay muchos intentos zona roja

### 5. Botón de Pánico: Ctrl+Alt+K

Un atajo de teclado de emergencia que:

```
Ctrl+Alt+K presionado:

  1. Mata TODOS los procesos de IA inmediatamente
     (Ollama, OpenClaw, Celery workers, agentes)
  
  2. Congela el sistema de archivos de /storage/
     (Previene escrituras adicionales)
  
  3. Muestra una terminal limpia SIN IA
     (Modo de recuperación)
  
  4. Muestra las últimas 50 acciones del log
     (Para ver qué pasó)
  
  5. Opciones de recuperación:
     a) Restaurar snapshot anterior
     b) Reiniciar servicios de IA
     c) Revertir últimos cambios
     d) Apagar el sistema
```

**Implementación:**
- Interceptado a nivel de kernel/systemd (no depende de la IA)
- Funciona SIEMPRE, incluso si la interfaz gráfica está colgada
- La IA no puede desactivarlo ni interceptarlo

### 6. Snapshots Automáticos

El sistema hace copias de seguridad automáticas del disco:

```
Cada 6 horas:
  → Snapshot del filesystem completo (BTRFS o ZFS)
  → Backup de PostgreSQL
  → Backup de /storage/

Si la IA hace algo raro:
  → Restauras al snapshot anterior
  → Pierdes máximo 6 horas, no todo
```

**Tecnología recomendada:** BTRFS (filesystem con snapshots nativos en Linux)

**Política de retención:**
- Últimas 24 horas: 1 snapshot cada 6 horas (4 snapshots)
- Última semana: 1 snapshot diario (7 snapshots)
- Último mes: 1 snapshot semanal (4 snapshots)

## Seguridad de Datos

### Encriptación
- **Credenciales:** AES-256 (ya en el stack)
- **Contraseñas:** bcrypt (ya en el stack)
- **Autenticación:** JWT (ya en el stack)
- **Disco completo:** LUKS (encriptación de disco en Linux)

### Acceso a Internet
- La IA solo puede acceder a internet a través de endpoints aprobados
- Lista blanca de dominios permitidos (APIs de redes sociales, búsqueda)
- No puede hacer requests arbitrarios a cualquier URL sin aprobación

## Resumen de Protecciones

| Capa | Protección | Contra qué |
|------|-----------|------------|
| Sandbox | Aislamiento de procesos | IA tocando el sistema |
| Zonas | Permisos por nivel de riesgo | Acciones peligrosas |
| Usuarios Linux | Privilegios mínimos | Escalación de permisos |
| Auditoría | Registro de todo | No saber qué pasó |
| Ctrl+Alt+K | Kill switch instantáneo | IA fuera de control |
| Snapshots | Backup cada 6 horas | Pérdida de datos |
| Encriptación | Datos encriptados | Acceso no autorizado |
