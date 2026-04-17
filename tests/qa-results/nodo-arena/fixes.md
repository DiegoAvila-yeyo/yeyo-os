# Fixes — Nodo Arena

## Bug 1: Arena battle rounds took 120s+ per round (hanging on Ollama)
**Causa**: `YeyoHack.generate_attack()` y `Guardian.detect_and_defend()` llamaban a 
  `self.ia.generate()` con timeout de 120s (httpx default). Ollama no tenía el modelo
  `qwen2.5:3b` → esperaba 120s por round antes de fallback.
**Síntoma**: Ronda 1 tardaba 4 minutos; batalla de 15 rondas tomaría ~1 hora.
**Fix**: Wrapping con `asyncio.wait_for(..., timeout=8.0)` en ambos métodos.
  Al fallar el timeout, la excepción es capturada y se usan templates (fallback).
**Archivo**: `src/arena/battle.py`

## Resultado después del fix
- Cada ronda: ~14 segundos (8s timeout + fallback + lógica)
- Batalla de 15 rondas: ~210 segundos (~3.5 min)
- red_score: 1, blue_score: 14 (Guardian ganó)
