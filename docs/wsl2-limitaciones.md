# 🔧 WSL2 — Limitaciones y Decisiones de Desarrollo

> **Documento de referencia** para entender qué funciona diferente en WSL2 vs hardware real,
> por qué se tomaron ciertas decisiones, y cuándo se resuelve cada limitación.

---

## Contexto

YeyoOS se desarrolla en **WSL2 (Ubuntu sobre Windows)** durante las Fases 0-11.
En la **Fase 12**, se formatea la PC y se instala YeyoOS en hardware real (bare metal).

WSL2 corre Linux dentro de un hypervisor Hyper-V de Windows. Esto impone restricciones
en ciertas llamadas al kernel que no existen en Linux nativo.

---

## Limitaciones Encontradas

### 1. `auditd` — Kernel audit netlink bloqueado

**Estado:** `XFAIL` en tests — se resuelve en **Capa 6**

**Error exacto:**
```
Error sending enable request (Operation not permitted)
Error setting audit daemon pid (Operation not permitted)
```

**Por qué ocurre:**
Hyper-V bloquea las llamadas `netlink` al subsistema de audit del kernel.
El kernel de WSL2 tiene el código compilado pero Microsoft lo deshabilita
a nivel de hypervisor por seguridad del host Windows.

**Decisión tomada:**
No se implementa un sustituto en Capa 0. La razón es que el proyecto ya tiene
la solución correcta planificada: el **Guardian daemon (Capa 6)** es el sistema
de monitoreo/auditoría nativo de YeyoOS. Usar `auditd` es una herramienta
prestada de Linux genérico — Guardian la reemplazará con una implementación
propia en Rust, diseñada específicamente para YeyoOS.

**Resolución:**
- **Capa 6:** Guardian daemon implementa auditoría nativa → el XFAIL desaparece
- **Fase 12:** `auditd` también funcionará en bare metal (por si se necesita como backup)

---

### 2. Permisos NTFS en `/mnt/c/`

**Estado:** ✅ **RESUELTO** — `/etc/wsl.conf` actualizado

**Problema:**
El filesystem Windows (NTFS) no soporta permisos Unix nativamente.
Sin configuración especial, todos los archivos en `/mnt/c/` muestran `777`
independientemente del `chmod` aplicado. Tests que verifican `chmod 600 .env`
fallarían siempre.

**Fix aplicado:**
Se agregó a `/etc/wsl.conf`:
```ini
[automount]
options = "metadata"
```

Esto activa **metadata POSIX en NTFS** — WSL2 almacena los permisos Unix
como extended attributes del filesystem Windows. `chmod` funciona correctamente.

**⚠️ Requiere reinicio de WSL2 para activarse:**
```powershell
wsl --shutdown
# Luego abrir WSL2 nuevamente
```

---

### 3. Wayland Compositor como display server nativo

**Estado:** Desarrollo en modo **nested compositor** — se resuelve en **Fase 12**

**Limitación:**
En WSL2 no se puede ser el "dueño" del framebuffer real (DRM/KMS).
El compositor no puede tomar control directo del hardware de display.

**Decisión tomada:**
Desarrollar el YEYO Compositor como **nested compositor** desde el primer commit.
Esto significa que durante desarrollo, el compositor corre dentro de WSLg
(el compositor Wayland que Microsoft incluye en WSL2).

**¿Es esto un workaround?** No — es el **método estándar de la industria**.
Todos los compositores modernos (Hyprland, Sway, KDE KWin) se desarrollan y
prueban en modo nested antes de correr en bare metal. El código es el mismo,
solo cambia el backend de display.

**Resolución:**
- **Capa 3:** Diseñar el compositor con backend `nested` (WSLg) y backend `drm` (bare metal)
- **Fase 12:** Activar backend DRM — el 95% del código ya funciona

---

### 4. `seccomp` y capabilities avanzadas

**Estado:** Tests de funcionalidad con `--privileged` durante desarrollo

**Limitación:**
Algunas llamadas de sistema protegidas por seccomp o que requieren capabilities
avanzadas están bloqueadas por Hyper-V.

**Decisión tomada:**
- Durante Capas 0-11: containers con capabilities mínimas necesarias
- Capa 6 (Guardian): definir perfiles de seccomp del proyecto
- Fase 12: aplicar perfiles estrictos en hardware real

---

## Tabla de Resolución

| Limitación | Fase actual | Se resuelve en | Método |
|---|:---:|:---:|---|
| `auditd` kernel netlink | XFAIL | **Capa 6** | Guardian daemon reemplaza auditd |
| Permisos NTFS | ✅ Resuelto | — | WSL metadata activado |
| Compositor display nativo | Nested | **Fase 12** | Backend DRM en bare metal |
| `seccomp` estricto | Funcional | **Fase 12** | Perfiles definidos en Capa 6 |

---

## Tests Afectados y Su Estado

| Test | Archivo | Estado | Razón |
|---|---|:---:|---|
| `test_audit_running` | `tests/test_security.py` | `XFAIL` | auditd no puede conectar al kernel WSL2 |
| `test_env_not_world_readable` | (futuro) | Pendiente | Requiere reinicio WSL para metadata NTFS |

---

## Instrucciones para Colaboradores

Si clonas este repo y trabajas en WSL2:

1. **Activa metadata NTFS** (ya está en `/etc/wsl.conf` del proyecto):
   ```powershell
   wsl --shutdown
   ```
   Luego abre WSL2 nuevamente.

2. **El XFAIL de auditd es esperado** — no intentes "arreglarlo" en Capa 0.
   Está documentado y tiene una solución correcta planificada en Capa 6.

3. **Para el compositor** — cuando llegues a Capa 3, usa el backend `nested` por defecto.
   El switch a DRM es un flag de compilación, no un rewrite.

---

## Filosofía

> *"Un reloj suizo no pone todas las piezas en el primer tornillo.*
> *Las pone en el orden correcto, en el momento correcto."*

Las limitaciones de WSL2 no son deuda técnica — son parte del plan.
Cada una tiene una resolución específica en la fase correcta del proyecto.
El XFAIL documentado es más honesto y mantenible que un parche apresurado.

---

*Documento creado durante Capa 0 — Micro-fase 0.11*
*Última actualización: 2026-03-21*
