# 06 — Seguridad (Referencia)

> **La documentación completa de seguridad está en el repositorio privado `yeyo-os-security`.**

## Resumen

YeyoOS cuenta con **31+ capas de seguridad** distribuidas en múltiples niveles. Por su naturaleza sensible, los detalles de implementación se mantienen en un repositorio separado y privado.

## Concepto de Zonas

El sistema clasifica toda acción de la IA en tres zonas:

- 🟢 **Verde** — Acciones seguras, se ejecutan automáticamente (generar archivos, consultar memoria)
- 🟡 **Amarilla** — Requiere confirmación del usuario (publicar en redes, instalar paquetes)
- 🔴 **Roja** — Bloqueado siempre, sin excepciones (modificar sistema, ejecutar como root)

## Kill Switch: Ctrl+Alt+K

Existe un botón de pánico (`Ctrl+Alt+K`) que mata todos los procesos de IA instantáneamente, congela el filesystem y abre modo de recuperación. Funciona a nivel de kernel — la IA no puede desactivarlo.

## Temas Cubiertos en `yeyo-os-security`

1. **Seguridad base** — Sandbox, zonas de acceso, usuarios Linux separados
2. **Kernel security** — Protecciones a nivel de kernel y bootloader
3. **YEYO-HACK** — Sistema ofensivo de pentesting y auditoría
4. **YEYO Guardian** — Monitoreo activo y detección de anomalías
5. **Análisis de brechas** — Protocolos de respuesta ante incidentes
6. **Privilegios** — Escalación controlada, permisos mínimos, auditoría
7. **Corporativo** — Seguridad multi-usuario, compliance, aislamiento
8. **Protección de memoria** — Encriptación de Flash Memory, acceso controlado

## Acceso

```
git clone git@github.com:eltitoyeyo/yeyo-os-security.git
```

Solo accesible con permisos explícitos.
