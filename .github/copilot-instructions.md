# YeyoOS — Instrucciones para Copilot

## Leer primero
Antes de cualquier acción, lee el hilo conductor del ecosistema:
`/Users/eltitoyeyo/YEYO/YEYO_ESTADO.md`

## Rol de este repo
Este es el repo central de YeyoOS: contiene la visión, toda la documentación,
el frontend shell y define la arquitectura de los otros 3 repos del ecosistema.

## Fuente de verdad
- Visión y filosofía: `docs/01-vision.md`
- Arquitectura: `docs/02-arquitectura.md`
- Stack tecnológico: `docs/09-stack-tecnologico.md`
- Fases de desarrollo: `docs/10-fases.md` ← leer antes de implementar cualquier cosa
- Seguridad: `../yeyo-os-security/` (repo separado)

## Estado actual
🟡 En definición activa. Docs completos, implementación del kernel pendiente.
Ver YEYO_ESTADO.md para estado detallado.

## Reglas
- Roadmap prioriza: agentes + memoria + calidad PRIMERO, OS-like shell AL FINAL
- Filosofía: local-first, anti-alucinación, nunca olvidar
- Si código y docs no coinciden → reconciliar antes de continuar
- Stack: Next.js + TS frontend, FastAPI + Python kernel, Ollama, PostgreSQL + pgvector
- Responder siempre en español
